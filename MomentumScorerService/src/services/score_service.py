"""
ScoreService — orchestrates batch unified score computation and persistence.
"""
import asyncio
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

import asyncpg

from ..config import settings
from ..repositories.price_repository import PriceRepository
from ..repositories.score_repository import ScoreRepository
from ._score_compute import (
    _collect_valid_results,
    _gather_scores,
    _partition_by_fno,
    _persist_ranked_groups,
)
from ._score_watchlist import ScoreWatchlistMixin

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")
_WATCHLIST_SIZE = 50


def _last_trading_date(price_data: dict[str, pd.DataFrame]) -> date:
    """Return most recent trading date from fetched price data."""
    dates = [df["time"].max() for df in price_data.values() if not df.empty]
    if not dates:
        return datetime.now(tz=_IST).date()
    latest = max(dates)
    return latest.date() if hasattr(latest, "date") else latest


class ScoreService(ScoreWatchlistMixin):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool      = pool
        self._prices    = PriceRepository(pool)
        self._scores    = ScoreRepository(pool)
        self._semaphore = asyncio.Semaphore(settings.score_concurrency)

    async def compute_unified(self) -> int:
        """
        Compute unified daily scores for all synced symbols and persist
        to daily_scores + update symbol_metrics with indicator values.
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

        price_data = await self._prices.fetch_ohlcv_batch(symbols, "1d", settings.score_lookback_bars)
        score_date = _last_trading_date(price_data)
        logger.info("Score date resolved to last trading day: %s", score_date)
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
        results = await _gather_scores(price_data, self._semaphore, score_kwargs)
        valid_results = _collect_valid_results(results)
        fno_results, equity_results = _partition_by_fno(valid_results, fno_set)

        scored = await _persist_ranked_groups(
            self._pool, self._scores, [fno_results, equity_results], score_date, _WATCHLIST_SIZE,
        )
        fno_wl    = min(_WATCHLIST_SIZE, len(fno_results))
        equity_wl = min(_WATCHLIST_SIZE, len(equity_results))
        logger.info(
            "Unified scoring complete: %d/%d scored — FNO watchlist=%d, equity watchlist=%d (total subs=%d)",
            scored, len(symbols), fno_wl, equity_wl, fno_wl + equity_wl,
        )
        return scored
