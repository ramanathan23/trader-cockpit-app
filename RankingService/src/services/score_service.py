"""
ScoreService — reads pre-computed indicators, applies scoring weights, persists rankings.
No raw OHLCV access — IndicatorsService owns all computation.
"""
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import asyncpg

from ..config import settings
from ..repositories.score_repository import ScoreRepository
from ..repositories.symbol_repository import SymbolRepository
from ..signals.unified_scorer import compute_score_from_indicators
from ._score_watchlist import ScoreWatchlistMixin

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")
_STAGE_WATCHLIST_STAGES = {"STAGE_2", "STAGE_4"}


class ScoreService(ScoreWatchlistMixin):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._scores = ScoreRepository(pool)
        self._symbols = SymbolRepository(pool)
        self._sem = asyncio.Semaphore(settings.score_concurrency)

    async def compute_unified(self) -> tuple[int, str]:
        candidates = await self._symbols.fetch_ranked_candidates(
            min_adv_crores=settings.min_adv_crores,
        )
        if not candidates:
            counts = await self._symbols.fetch_candidate_counts(min_adv_crores=settings.min_adv_crores)
            if counts["total_indicators"] == 0:
                msg = "No indicator data — run IndicatorsService first"
            elif counts["joined"] == 0:
                msg = f"symbol_indicators ({counts['total_indicators']}) and symbol_metrics ({counts['total_metrics']}) have no overlapping symbols"
            else:
                msg = f"ADV filter ({settings.min_adv_crores}₹Cr) excluded all {counts['joined']} candidates — lower min_adv_crores or re-sync data"
            logger.warning("Scored 0: %s", msg)
            return 0, msg

        logger.info("Scoring %d candidates", len(candidates))
        score_date = datetime.now(tz=_IST).date()

        results = await asyncio.gather(
            *[self._score_one(row) for row in candidates],
            return_exceptions=True,
        )

        valid = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Score failed: %s", result)
                continue
            if result is not None:
                valid.append(result)

        if not valid:
            msg = f"All {len(candidates)} candidates missing required indicators (rsi_14 or ROC values null)"
            logger.warning("Scored 0: %s", msg)
            return 0, msg

        stage_watchlist = self._build_watchlist_set(valid)
        fno = [(s, b) for s, b, fno in valid if fno]
        equity = [(s, b) for s, b, fno in valid if not fno]
        fno.sort(key=lambda x: x[1].total_score, reverse=True)
        equity.sort(key=lambda x: x[1].total_score, reverse=True)

        scored = await self._persist_ranked([fno, equity], score_date, stage_watchlist)

        s2 = sum(1 for _, b, _ in valid if b.stage == "STAGE_2")
        s4 = sum(1 for _, b, _ in valid if b.stage == "STAGE_4")
        logger.info(
            "Scoring complete: %d/%d scored — Stage2=%d Stage4=%d watchlist=%d",
            scored, len(candidates), s2, s4, len(stage_watchlist),
        )
        msg = f"Scored {scored} symbols"
        return scored, msg

    async def _score_one(self, row: dict):
        async with self._sem:
            breakdown = await asyncio.to_thread(compute_score_from_indicators, row)
        if breakdown is None:
            return None
        return row["symbol"], breakdown, bool(row.get("is_fno", False))

    def _build_watchlist_set(self, valid: list, per_segment: int = 25) -> set[str]:
        trimmed: set[str] = set()
        for is_fno in (True, False):
            for stage in _STAGE_WATCHLIST_STAGES:
                top = sorted(
                    [(s, b) for s, b, fno in valid if fno == is_fno and b.stage == stage],
                    key=lambda x: x[1].total_score,
                    reverse=True,
                )[:per_segment]
                trimmed.update(s for s, _ in top)
        return trimmed

    async def _persist_ranked(
        self,
        groups: list[list],
        score_date,
        watchlist_set: set[str],
    ) -> int:
        scored = 0
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for group in groups:
                    for rank_idx, (symbol, breakdown) in enumerate(group, start=1):
                        try:
                            async with conn.transaction():
                                await self._scores.upsert_daily_score(
                                    conn, symbol, score_date, breakdown,
                                    rank_idx, symbol in watchlist_set,
                                )
                            scored += 1
                        except Exception:
                            logger.warning("Persist failed for %s", symbol, exc_info=True)
        return scored
