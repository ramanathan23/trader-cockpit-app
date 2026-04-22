"""Watchlist building and benchmark/liquidity helpers for ScoreService."""

import logging

import pandas as pd

from ..config import settings
from ..domain.filters import is_liquid

logger = logging.getLogger(__name__)

_STAGE_LABELS = {
    "STAGE_2": "bull",
    "STAGE_4": "bear",
}


class ScoreWatchlistMixin:
    """Mixin providing stage-based watchlist building and data-preparation helpers."""

    async def build_watchlist(
        self,
        *,
        stage: str = "both",
        limit: int = 100,
    ) -> list[dict]:
        """
        Return Stage 2 (bull) and/or Stage 4 (bear) stocks from the latest
        daily_scores, ranked by total_score descending.

        stage: "bull" | "bear" | "both"
        """
        if stage == "bull":
            stage_filter = ("STAGE_2",)
        elif stage == "bear":
            stage_filter = ("STAGE_4",)
        else:
            stage_filter = ("STAGE_2", "STAGE_4")

        placeholders = ", ".join(f"${i + 2}" for i in range(len(stage_filter)))
        query = f"""
            SELECT
                ds.symbol,
                s.company_name,
                s.is_fno,
                ds.score_date,
                ds.total_score,
                ds.momentum_score,
                ds.trend_score,
                ds.volatility_score,
                ds.structure_score,
                ds.rs_vs_nifty,
                ds.vol_ratio_20,
                ds.rsi_14,
                ds.stage,
                ds.rank
            FROM daily_scores ds
            JOIN symbols s ON s.symbol = ds.symbol
            WHERE ds.score_date = (SELECT MAX(score_date) FROM daily_scores)
              AND ds.stage IN ({placeholders})
            ORDER BY ds.total_score DESC
            LIMIT $1
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, limit, *stage_filter)

        return [
            {**dict(r), "side": _STAGE_LABELS.get(r["stage"], r["stage"])}
            for r in rows
        ]

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
