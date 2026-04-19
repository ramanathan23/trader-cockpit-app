"""Watchlist detection and benchmark/liquidity helpers for ScoreService."""

import logging

import pandas as pd

from ..config import settings
from ..domain.filters import is_liquid
from ..signals.watchlist import detect_run_and_tight_base

logger = logging.getLogger(__name__)


class ScoreWatchlistMixin:
    """Mixin providing watchlist building and data-preparation helpers."""

    async def build_watchlist(
        self,
        *,
        side:                str   = "both",
        limit:               int   = 50,
        run_window:          int   = 5,
        base_window:         int   = 3,
        min_run_move_pct:    float = 8.0,
        max_base_range_pct:  float = 3.0,
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
        symbol_meta     = {row["symbol"]: row.get("company_name") for row in symbol_rows}
        requested_sides = [side] if side in {"bull", "bear"} else ["bull", "bear"]

        candidates: list[dict] = []
        for symbol, df in price_data.items():
            if not is_liquid(df, settings.min_avg_daily_turnover):
                continue
            for current_side in requested_sides:
                candidate = detect_run_and_tight_base(
                    symbol, symbol_meta.get(symbol), df,
                    side=current_side, run_window=run_window, base_window=base_window,
                    min_run_move_pct=min_run_move_pct,
                    max_base_range_pct=max_base_range_pct,
                    max_retracement_pct=max_retracement_pct,
                )
                if candidate is not None:
                    candidates.append(candidate)

        candidates.sort(key=lambda row: (row["pattern_score"], row["run_move_pct"]), reverse=True)
        return candidates[:limit]

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
