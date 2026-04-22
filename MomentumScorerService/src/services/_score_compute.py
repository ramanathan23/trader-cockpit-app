"""Stateless scoring pipeline helpers extracted from ScoreService."""

import asyncio
import logging

import pandas as pd

from ..signals.unified_scorer import compute_unified_score

logger = logging.getLogger(__name__)

_STAGE_WATCHLIST_STAGES = {"STAGE_2", "STAGE_4"}


async def _gather_scores(
    symbols_data: dict,
    semaphore: asyncio.Semaphore,
    score_kwargs: dict,
) -> list:
    """Run unified scorer concurrently across all symbols."""
    async def _score_one(symbol: str, df: pd.DataFrame):
        async with semaphore:
            return symbol, await asyncio.to_thread(compute_unified_score, df, **score_kwargs)

    return await asyncio.gather(
        *[_score_one(sym, df) for sym, df in symbols_data.items()],
        return_exceptions=True,
    )


def _collect_valid_results(results: list) -> list[tuple]:
    """Filter out exceptions and None scores from gather results."""
    valid = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Scoring task failed: %s", result)
            continue
        symbol, breakdown = result
        if breakdown is not None:
            valid.append((symbol, breakdown))
    return valid


def _partition_by_fno(
    valid_results: list[tuple],
    fno_set: set[str],
) -> tuple[list, list]:
    """Split into (fno, equity), each sorted descending by total_score."""
    fno    = [(s, b) for s, b in valid_results if s in fno_set]
    equity = [(s, b) for s, b in valid_results if s not in fno_set]
    fno.sort(key=lambda x: x[1].total_score, reverse=True)
    equity.sort(key=lambda x: x[1].total_score, reverse=True)
    return fno, equity


def _build_stage_watchlist_set(
    valid_results: list[tuple],
    fno_set: set[str],
    *,
    per_segment: int = 50,
    per_stage: int = 25,
) -> set[str]:
    """
    Top per_stage S2 + per_stage S4 within each segment (FNO / equity).
    Total = 2 segments × 2 stages × per_stage = per_segment × 2.
    """
    watchlist: set[str] = set()
    for is_fno in (True, False):
        seg = [
            (sym, b) for sym, b in valid_results
            if (sym in fno_set) == is_fno and b.stage in _STAGE_WATCHLIST_STAGES
        ]
        for stage in _STAGE_WATCHLIST_STAGES:
            top = sorted(
                [(sym, b) for sym, b in seg if b.stage == stage],
                key=lambda x: x[1].total_score,
                reverse=True,
            )[:per_stage]
            watchlist.update(sym for sym, _ in top)
    return watchlist


async def _persist_ranked_groups(
    pool,
    scores_repo,
    groups: list[list],
    today,
    stage_watchlist_set: set[str],
) -> int:
    """Persist all scored symbols in ranked groups; returns count of successful saves."""
    scored = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            for group in groups:
                for rank_idx, (symbol, breakdown) in enumerate(group, start=1):
                    is_watchlist = symbol in stage_watchlist_set
                    try:
                        async with conn.transaction():
                            await scores_repo.upsert_daily_score(
                                conn, symbol, today, breakdown, rank_idx, is_watchlist
                            )
                            await scores_repo.update_symbol_metrics_indicators(
                                conn, symbol, breakdown
                            )
                        scored += 1
                    except Exception:
                        logger.warning("Score persist failed for %s", symbol, exc_info=True)
    return scored
