"""
MetricsComputeService — runs after each 1d EOD sync to precompute per-symbol
daily metrics and write them into the symbol_metrics table.

LiveFeedService reads from symbol_metrics at startup instead of computing
these queries itself, so there is no heavy aggregation at market open.
"""
from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger(__name__)


class MetricsComputeService:
    """Computes and persists per-symbol daily metrics into symbol_metrics."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def recompute(self) -> int:
        """
        Recompute metrics for all symbols that have daily price data and
        upsert into symbol_metrics.  Returns the number of rows written.
        """
        logger.info("MetricsComputeService: recomputing symbol metrics…")

        result = await self._pool.execute("""
            INSERT INTO symbol_metrics (
                symbol,
                computed_at,
                week52_high,
                week52_low,
                atr_14,
                adv_20_cr,
                trading_days,
                prev_day_high,
                prev_day_low,
                prev_day_close,
                prev_week_high,
                prev_week_low,
                prev_month_high,
                prev_month_low
            )
            WITH base AS (
                SELECT
                    symbol,
                    time,
                    high::float,
                    low::float,
                    close::float,
                    volume::float,
                    LAG(close::float) OVER (PARTITION BY symbol ORDER BY time ASC) AS prev_close,
                    LAG(high::float)  OVER (PARTITION BY symbol ORDER BY time ASC) AS prev_high,
                    LAG(low::float)   OVER (PARTITION BY symbol ORDER BY time ASC) AS prev_low,
                    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time ASC)      AS rn,
                    COUNT(*)         OVER (PARTITION BY symbol)                    AS total
                FROM price_data_daily
                WHERE time >= NOW() - INTERVAL '366 days'
            ),
            with_tr AS (
                SELECT
                    symbol,
                    time,
                    high, low, close, volume,
                    prev_high, prev_low, prev_close,
                    GREATEST(
                        high - low,
                        ABS(high - COALESCE(prev_close, close)),
                        ABS(low  - COALESCE(prev_close, close))
                    ) AS tr,
                    rn, total
                FROM base
            )
            SELECT
                symbol,
                NOW()                                                    AS computed_at,
                MAX(high)                                                AS week52_high,
                MIN(low)                                                 AS week52_low,
                AVG(tr)          FILTER (WHERE rn > total - 14)         AS atr_14,
                AVG(close * volume / 1e7)
                                 FILTER (WHERE rn > total - 20)         AS adv_20_cr,
                COUNT(*)                                                 AS trading_days,
                MAX(prev_high)   FILTER (WHERE rn = total)              AS prev_day_high,
                MAX(prev_low)    FILTER (WHERE rn = total)              AS prev_day_low,
                MAX(prev_close)  FILTER (WHERE rn = total)              AS prev_day_close,
                MAX(high) FILTER (
                    WHERE time >= date_trunc('week', CURRENT_DATE) - INTERVAL '7 days'
                      AND time  < date_trunc('week', CURRENT_DATE)
                )                                                        AS prev_week_high,
                MIN(low)  FILTER (
                    WHERE time >= date_trunc('week', CURRENT_DATE) - INTERVAL '7 days'
                      AND time  < date_trunc('week', CURRENT_DATE)
                )                                                        AS prev_week_low,
                MAX(high) FILTER (
                    WHERE time >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
                      AND time  < date_trunc('month', CURRENT_DATE)
                )                                                        AS prev_month_high,
                MIN(low)  FILTER (
                    WHERE time >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
                      AND time  < date_trunc('month', CURRENT_DATE)
                )                                                        AS prev_month_low
            FROM with_tr
            GROUP BY symbol
            HAVING COUNT(*) >= 5
            ON CONFLICT (symbol) DO UPDATE SET
                computed_at     = EXCLUDED.computed_at,
                week52_high     = EXCLUDED.week52_high,
                week52_low      = EXCLUDED.week52_low,
                atr_14          = EXCLUDED.atr_14,
                adv_20_cr       = EXCLUDED.adv_20_cr,
                trading_days    = EXCLUDED.trading_days,
                prev_day_high   = EXCLUDED.prev_day_high,
                prev_day_low    = EXCLUDED.prev_day_low,
                prev_day_close  = EXCLUDED.prev_day_close,
                prev_week_high  = EXCLUDED.prev_week_high,
                prev_week_low   = EXCLUDED.prev_week_low,
                prev_month_high = EXCLUDED.prev_month_high,
                prev_month_low  = EXCLUDED.prev_month_low
        """)

        # asyncpg returns e.g. "INSERT 0 42" — parse the count
        try:
            count = int(result.split()[-1])
        except (IndexError, ValueError):
            count = -1

        logger.info("MetricsComputeService: upserted %d symbol_metrics rows", count)
        return count
