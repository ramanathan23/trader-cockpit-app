"""
ScoreService — orchestrates batch momentum score computation and persistence.
"""

import asyncio
import logging

import asyncpg
import pandas as pd

from ..config import settings
from ..repositories.price_repository import PriceRepository
from ..repositories.score_repository import ScoreRepository
from ..signals import indicators, scorer
from ..signals.watchlist import detect_run_and_tight_base

logger = logging.getLogger(__name__)


class ScoreService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool      = pool
        self._prices    = PriceRepository(pool)
        self._scores    = ScoreRepository(pool)
        self._semaphore = asyncio.Semaphore(settings.score_concurrency)

    async def compute_all(self, timeframe: str = "1d") -> int:
        """
        Compute and persist momentum scores for all synced symbols.

        Steps:
          1. Load all synced symbol names (single query).
          2. Batch-fetch all OHLCV data in one windowed query (no N+1).
          3. Run CPU-bound scoring concurrently in threads, bounded by semaphore.
          4. Replace the existing timeframe snapshot atomically.
             This keeps one current row per symbol/timeframe, matching the table PK.

        Returns the number of symbols successfully scored.
        """
        symbols = await self._prices.fetch_synced_symbols()
        if not symbols:
            logger.warning("No synced symbols found — run initial sync first")
            return 0

        logger.info("Computing %s momentum scores for %d symbols", timeframe, len(symbols))

        price_data = await self._prices.fetch_ohlcv_batch(
            symbols, timeframe, settings.score_lookback_bars
        )

        # ── Extract NIFTY500 benchmark ROC (60-bar) ──────────────────────────
        # Used by scorer to compute each stock's relative strength vs the index.
        # NIFTY500 itself is not scored — pop it from the data dict.
        nifty500_roc_60: float | None = None
        benchmark = settings.nifty500_benchmark
        if benchmark in price_data:
            bdf   = price_data.pop(benchmark)
            close = bdf["close"].astype(float)
            if len(close) >= 60:
                roc_series = indicators.rate_of_change(close, period=60)
                val = roc_series.iloc[-1]
                if not pd.isna(val):
                    nifty500_roc_60 = float(val)
                    logger.info("NIFTY500 60-bar ROC: %.2f%%", nifty500_roc_60)
        else:
            logger.warning("Benchmark %s not found in price data — RS mult disabled", benchmark)

        # ── Liquidity filter — skip illiquid symbols before scoring ───────────
        min_turnover = settings.min_avg_daily_turnover
        filtered: dict = {}
        skipped = 0
        for sym, df in price_data.items():
            avg_turnover = (df["close"].astype(float) * df["volume"].astype(float)).tail(20).mean()
            if avg_turnover < min_turnover:
                logger.debug(
                    "Skipping %s — avg daily turnover ₹%.0f < threshold ₹%.0f",
                    sym, avg_turnover, min_turnover,
                )
                skipped += 1
            else:
                filtered[sym] = df
        if skipped:
            logger.info("Liquidity filter removed %d / %d symbols", skipped, len(price_data))
        price_data = filtered

        # Build scoring params once from config — avoids repeated attribute lookups
        score_kwargs = dict(
            rsi_period=settings.rsi_period,
            macd_fast=settings.macd_fast,
            macd_slow=settings.macd_slow,
            macd_signal=settings.macd_signal,
            roc_period=settings.roc_period,
            vol_period=settings.vol_avg_period,
            min_bars=settings.score_min_bars,
            trend_lookback=settings.trend_lookback_bars,
            atr_period=settings.atr_period,
            atr_pct_max=settings.atr_pct_max,
            nifty500_roc_60=nifty500_roc_60,
            weights=(
                settings.weight_rsi,
                settings.weight_macd,
                settings.weight_roc,
                settings.weight_vol,
            ),
        )

        async def _score_one(symbol: str, df):
            async with self._semaphore:
                return symbol, await asyncio.to_thread(scorer.compute_score, df, **score_kwargs)

        tasks = [_score_one(sym, df) for sym, df in price_data.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect valid results before touching the DB
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Scoring task failed: %s", result)
                continue
            symbol, breakdown = result
            if breakdown is not None:
                valid_results.append((symbol, breakdown))

        scored = 0
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                deleted = await self._scores.delete_by_timeframe(conn, timeframe)
                if deleted:
                    logger.info("Replacing %d existing %s scores", deleted, timeframe)
                for symbol, breakdown in valid_results:
                    try:
                        await self._scores.insert(conn, symbol, timeframe, breakdown)
                        scored += 1
                    except Exception:
                        logger.warning("Score persist failed for %s", symbol, exc_info=True)

        logger.info("Scored %d / %d symbols (%s)", scored, len(symbols), timeframe)
        return scored

    async def build_watchlist(
        self,
        *,
        side: str = "both",
        limit: int = 50,
        run_window: int = 5,
        base_window: int = 3,
        min_run_move_pct: float = 8.0,
        max_base_range_pct: float = 3.0,
        max_retracement_pct: float = 0.35,
    ) -> list[dict]:
        symbol_rows = await self._prices.fetch_synced_symbol_details()
        if not symbol_rows:
            return []

        symbols = [row["symbol"] for row in symbol_rows]
        price_data = await self._prices.fetch_ohlcv_batch(
            symbols,
            "1d",
            lookback=max(settings.score_lookback_bars, run_window + base_window + 5),
        )
        symbol_meta = {row["symbol"]: row.get("company_name") for row in symbol_rows}
        requested_sides = [side] if side in {"bull", "bear"} else ["bull", "bear"]

        candidates: list[dict] = []
        for symbol, df in price_data.items():
            avg_turnover = (df["close"].astype(float) * df["volume"].astype(float)).tail(20).mean()
            if avg_turnover < settings.min_avg_daily_turnover:
                continue

            for current_side in requested_sides:
                candidate = detect_run_and_tight_base(
                    symbol,
                    symbol_meta.get(symbol),
                    df,
                    side=current_side,
                    run_window=run_window,
                    base_window=base_window,
                    min_run_move_pct=min_run_move_pct,
                    max_base_range_pct=max_base_range_pct,
                    max_retracement_pct=max_retracement_pct,
                )
                if candidate is not None:
                    candidates.append(candidate)

        candidates.sort(key=lambda row: (row["pattern_score"], row["run_move_pct"]), reverse=True)
        return candidates[:limit]
