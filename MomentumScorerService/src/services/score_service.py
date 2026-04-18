"""
ScoreService — orchestrates batch unified score computation and persistence.
"""
import asyncio
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import asyncpg
import pandas as pd

from ..config import settings
from ..domain.filters import is_liquid
from ..repositories.price_repository import PriceRepository
from ..repositories.score_repository import ScoreRepository
from ..signals.unified_scorer import compute_unified_score
from ..signals.watchlist import detect_run_and_tight_base

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")
_WATCHLIST_SIZE = 50


class ScoreService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool      = pool
        self._prices    = PriceRepository(pool)
        self._scores    = ScoreRepository(pool)
        self._semaphore = asyncio.Semaphore(settings.score_concurrency)

    async def compute_unified(self) -> int:
        """
        Compute unified daily scores for all synced symbols and persist
        to daily_scores + update symbol_metrics with indicator values.

        Steps:
          1. Load all synced symbol names.
          2. Batch-fetch OHLCV data in one windowed query.
          3. Apply liquidity filter.
          4. Run CPU-bound unified scoring concurrently.
          5. Rank by total_score, mark top 50 as watchlist.
          6. Persist daily_scores + update symbol_metrics atomically.

        Returns the number of symbols successfully scored.
        """
        symbols = await self._prices.fetch_synced_symbols()
        if not symbols:
            logger.warning("No synced symbols found — run initial sync first")
            return 0

        fno_set = await self._prices.fetch_fno_set()
        logger.info(
            "Computing unified scores for %d symbols (%d FNO, %d equity)",
            len(symbols), len(fno_set & set(symbols)), len(set(symbols) - fno_set),
        )

        price_data = await self._prices.fetch_ohlcv_batch(
            symbols, "1d", settings.score_lookback_bars
        )

        nifty500_roc_60 = self._extract_benchmark_roc(price_data)

        price_data, skipped = self._apply_liquidity_filter(price_data)
        if skipped:
            logger.info("Liquidity filter removed %d symbols", skipped)

        score_kwargs = dict(
            rsi_period=settings.rsi_period,
            macd_fast=settings.macd_fast,
            macd_slow=settings.macd_slow,
            macd_signal=settings.macd_signal,
            vol_period=settings.vol_avg_period,
            min_bars=settings.score_min_bars,
            nifty500_roc_60=nifty500_roc_60,
        )

        async def _score_one(symbol: str, df):
            async with self._semaphore:
                return symbol, await asyncio.to_thread(compute_unified_score, df, **score_kwargs)

        results = await asyncio.gather(
            *[_score_one(sym, df) for sym, df in price_data.items()],
            return_exceptions=True,
        )

        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Scoring task failed: %s", result)
                continue
            symbol, breakdown = result
            if breakdown is not None:
                valid_results.append((symbol, breakdown))

        # Partition into FNO and equity groups; rank each group independently
        # so top-50 of each becomes is_watchlist=True (total ≤100 subscriptions).
        fno_results    = [(s, b) for s, b in valid_results if s in fno_set]
        equity_results = [(s, b) for s, b in valid_results if s not in fno_set]

        for group in (fno_results, equity_results):
            group.sort(key=lambda x: x[1].total_score, reverse=True)

        today = datetime.now(tz=_IST).date()
        scored = 0

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for group in (fno_results, equity_results):
                    for rank_idx, (symbol, breakdown) in enumerate(group, start=1):
                        is_watchlist = rank_idx <= _WATCHLIST_SIZE
                        try:
                            async with conn.transaction():  # savepoint per symbol
                                await self._scores.upsert_daily_score(
                                    conn, symbol, today, breakdown, rank_idx, is_watchlist
                                )
                                await self._scores.update_symbol_metrics_indicators(
                                    conn, symbol, breakdown
                                )
                            scored += 1
                        except Exception:
                            logger.warning("Score persist failed for %s", symbol, exc_info=True)

        fno_wl    = min(_WATCHLIST_SIZE, len(fno_results))
        equity_wl = min(_WATCHLIST_SIZE, len(equity_results))
        logger.info(
            "Unified scoring complete: %d/%d scored — FNO watchlist=%d, equity watchlist=%d (total subs=%d)",
            scored, len(symbols), fno_wl, equity_wl, fno_wl + equity_wl,
        )
        return scored

    async def build_watchlist(
        self,
        *,
        side:               str   = "both",
        limit:              int   = 50,
        run_window:         int   = 5,
        base_window:        int   = 3,
        min_run_move_pct:   float = 8.0,
        max_base_range_pct: float = 3.0,
        max_retracement_pct: float = 0.35,
    ) -> list[dict]:
        symbol_rows = await self._prices.fetch_synced_symbol_details()
        if not symbol_rows:
            return []

        symbols    = [row["symbol"] for row in symbol_rows]
        price_data = await self._prices.fetch_ohlcv_batch(
            symbols, "1d",
            lookback=max(settings.score_lookback_bars, run_window + base_window + 5),
        )
        symbol_meta    = {row["symbol"]: row.get("company_name") for row in symbol_rows}
        requested_sides = [side] if side in {"bull", "bear"} else ["bull", "bear"]

        candidates: list[dict] = []
        for symbol, df in price_data.items():
            if not is_liquid(df, settings.min_avg_daily_turnover):
                continue
            for current_side in requested_sides:
                candidate = detect_run_and_tight_base(
                    symbol,
                    symbol_meta.get(symbol),
                    df,
                    side                = current_side,
                    run_window          = run_window,
                    base_window         = base_window,
                    min_run_move_pct    = min_run_move_pct,
                    max_base_range_pct  = max_base_range_pct,
                    max_retracement_pct = max_retracement_pct,
                )
                if candidate is not None:
                    candidates.append(candidate)

        candidates.sort(
            key=lambda row: (row["pattern_score"], row["run_move_pct"]), reverse=True
        )
        return candidates[:limit]

    # ── Private helpers ────────────────────────────────────────────────────────

    def _extract_benchmark_roc(self, price_data: dict) -> float | None:
        """Pop and evaluate the NIFTY500 benchmark 60-bar ROC. Mutates price_data."""
        benchmark = settings.nifty500_benchmark
        if benchmark not in price_data:
            logger.warning("Benchmark %s not found — RS mult disabled", benchmark)
            return None

        bdf   = price_data.pop(benchmark)
        close = bdf["close"].astype(float)
        if len(close) < 60:
            return None

        from ..signals.indicators import rate_of_change
        val = rate_of_change(close, period=60).iloc[-1]
        if pd.isna(val):
            return None

        nifty500_roc_60 = float(val)
        logger.info("NIFTY500 60-bar ROC: %.2f%%", nifty500_roc_60)
        return nifty500_roc_60

    def _apply_liquidity_filter(self, price_data: dict) -> tuple[dict, int]:
        """Return (filtered_dict, skipped_count) after removing illiquid symbols."""
        filtered: dict = {}
        skipped = 0
        for sym, df in price_data.items():
            if is_liquid(df, settings.min_avg_daily_turnover):
                filtered[sym] = df
            else:
                logger.debug("Skipping %s — below liquidity threshold", sym)
                skipped += 1
        return filtered, skipped
