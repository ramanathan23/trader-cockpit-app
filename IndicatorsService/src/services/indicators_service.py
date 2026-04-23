"""
IndicatorsService — orchestrates batch indicator computation and persistence.

Pipeline per run:
  1. Fetch synced symbols + OHLCV batch from price_data_daily
  2. Extract NIFTY500 benchmark ROC-60 for RS calculation
  3. Compute structural metrics (symbol_metrics) + technical indicators (symbol_indicators)
     + patterns (symbol_patterns) concurrently per symbol
  4. Persist in batches
"""
from __future__ import annotations

import asyncio
import logging

import pandas as pd

from ..config import settings
from ..domain.snapshots import IndicatorSnapshot, MetricsSnapshot, PatternSnapshot
from ..repositories.indicator_repository import IndicatorRepository
from ..repositories.price_repository import PriceRepository
from ._calculator import compute_indicators, compute_metrics
from ._pattern_detector import detect_patterns

logger = logging.getLogger(__name__)


class IndicatorsService:
    def __init__(self, pool) -> None:
        self._prices = PriceRepository(pool)
        self._repo = IndicatorRepository(pool)
        self._sem = asyncio.Semaphore(settings.concurrency)

    async def compute(self) -> dict:
        symbols = await self._prices.fetch_synced_symbols()
        if not symbols:
            logger.warning("No synced symbols — run DataSync first")
            return {"symbols": 0, "metrics": 0, "indicators": 0, "patterns": 0}

        logger.info("Fetching OHLCV for %d symbols (lookback=%d)", len(symbols), settings.lookback_bars)
        all_symbols = list({*symbols, settings.nifty500_benchmark})
        price_data = await self._prices.fetch_ohlcv_batch(all_symbols, settings.lookback_bars)

        nifty500_roc_60 = self._extract_benchmark_roc(price_data)
        price_data = {s: df for s, df in price_data.items() if s in set(symbols)}

        logger.info("Computing indicators for %d symbols", len(price_data))
        results = await asyncio.gather(
            *[self._compute_one(sym, df, nifty500_roc_60) for sym, df in price_data.items()],
            return_exceptions=True,
        )

        metrics_list: list[MetricsSnapshot] = []
        indicators_list: list[IndicatorSnapshot] = []
        patterns_list: list[PatternSnapshot] = []

        for result in results:
            if isinstance(result, Exception):
                logger.warning("Compute failed: %s", result)
                continue
            m, ind, pat = result
            if m:
                metrics_list.append(m)
            if ind:
                indicators_list.append(ind)
            if pat:
                patterns_list.append(pat)

        m_count = await self._repo.upsert_metrics_batch(metrics_list)
        i_count = await self._repo.upsert_indicators_batch(indicators_list)
        p_count = await self._repo.upsert_patterns_batch(patterns_list)

        logger.info(
            "Compute complete — symbols=%d metrics=%d indicators=%d patterns=%d",
            len(price_data), m_count, i_count, p_count,
        )
        return {
            "symbols": len(price_data),
            "metrics": m_count,
            "indicators": i_count,
            "patterns": p_count,
        }

    async def _compute_one(
        self,
        symbol: str,
        df: pd.DataFrame,
        nifty500_roc_60: float | None,
    ) -> tuple[MetricsSnapshot | None, IndicatorSnapshot | None, PatternSnapshot | None]:
        async with self._sem:
            m, ind, pat = await asyncio.to_thread(
                _compute_sync, symbol, df, nifty500_roc_60,
                settings.vcp_min_contractions,
                settings.rect_lookback,
                settings.rect_max_range_pct,
            )
        return m, ind, pat

    def _extract_benchmark_roc(self, price_data: dict) -> float | None:
        bdf = price_data.get(settings.nifty500_benchmark)
        if bdf is None or len(bdf) < 60:
            logger.warning("Benchmark %s missing or insufficient bars — RS disabled", settings.nifty500_benchmark)
            return None
        close = bdf["close"].astype(float)
        if len(close) <= 60:
            return None
        val = close.iloc[-1] / close.iloc[-61] - 1.0
        roc = float(val) * 100.0
        logger.info("NIFTY500 60-bar ROC: %.2f%%", roc)
        return roc


def _compute_sync(
    symbol: str,
    df: pd.DataFrame,
    nifty500_roc_60: float | None,
    vcp_min: int,
    rect_lookback: int,
    rect_max_pct: float,
) -> tuple[MetricsSnapshot | None, IndicatorSnapshot | None, PatternSnapshot | None]:
    m = compute_metrics(symbol, df)
    ind = compute_indicators(symbol, df, nifty500_roc_60=nifty500_roc_60)
    pat = detect_patterns(
        symbol, df,
        vcp_min_contractions=vcp_min,
        rect_lookback=rect_lookback,
        rect_max_range_pct=rect_max_pct,
    )
    return m, ind, pat
