"""
MetricsService: bulk-precomputes per-symbol daily metrics at startup.

Daily metrics (52-week H/L, ATR-14, ADV-20) are computed once from
price_data_daily in a single query and cached in memory for the full
trading session — they don't change intraday.

Intraday metrics (day_high, day_low, day_open) are queried per-symbol
from candles_3min with a short TTL so they stay fresh during the session.

Usage
-----
    svc = MetricsService(pool)
    await svc.precompute_daily()          # call once at startup
    m = svc.get("RELIANCE")              # instant dict lookup
    m = await svc.get_with_intraday("RELIANCE")  # daily + today's range
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)

_INTRADAY_TTL = 60   # seconds — refresh day range every minute


class MetricsService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        # symbol → {week52_high, week52_low, atr_14, adv_20_cr, trading_days}
        self._daily: dict[str, dict] = {}
        # symbol → {data: {...}, ts: monotonic}
        self._intraday_cache: dict[str, dict] = {}

    # ── Startup precompute ────────────────────────────────────────────────────

    async def precompute_daily(self) -> int:
        """
        Single bulk query over price_data_daily — computes metrics for every
        symbol with at least 5 days of history. Runs in a few seconds.
        """
        logger.info("MetricsService: precomputing daily metrics for all symbols…")
        rows = await self._pool.fetch("""
            WITH base AS (
                SELECT
                    symbol,
                    high::float,
                    low::float,
                    close::float,
                    volume::float,
                    LAG(close::float) OVER (
                        PARTITION BY symbol ORDER BY time ASC
                    ) AS prev_close,
                    ROW_NUMBER() OVER (
                        PARTITION BY symbol ORDER BY time ASC
                    ) AS rn,
                    COUNT(*) OVER (PARTITION BY symbol) AS total
                FROM price_data_daily
                WHERE time >= NOW() - INTERVAL '366 days'
            ),
            with_tr AS (
                SELECT
                    symbol,
                    high, low, close, volume,
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
                MAX(high)                                        AS week52_high,
                MIN(low)                                         AS week52_low,
                AVG(tr)   FILTER (WHERE rn > total - 14)        AS atr_14,
                AVG(close * volume / 1e7)
                          FILTER (WHERE rn > total - 20)        AS adv_20_cr,
                COUNT(*)                                         AS trading_days
            FROM with_tr
            GROUP BY symbol
            HAVING COUNT(*) >= 5
        """)

        self._daily = {
            row["symbol"]: {
                "week52_high":  round(float(row["week52_high"]), 2),
                "week52_low":   round(float(row["week52_low"]),  2),
                "atr_14":       round(float(row["atr_14"] or 0), 2),
                "adv_20_cr":    round(float(row["adv_20_cr"] or 0), 1),
                "trading_days": int(row["trading_days"]),
            }
            for row in rows
        }
        logger.info("MetricsService: loaded daily metrics for %d symbols", len(self._daily))
        return len(self._daily)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_daily(self, symbol: str) -> Optional[dict]:
        """Instant lookup — no I/O. Returns None if symbol not in daily data."""
        return self._daily.get(symbol)

    async def get_with_intraday(self, symbol: str) -> Optional[dict]:
        """
        Returns daily metrics merged with today's intraday range.
        Intraday portion is cached for _INTRADAY_TTL seconds.
        """
        daily = self._daily.get(symbol)
        if daily is None:
            return None

        intraday = await self._get_intraday(symbol)
        return {**daily, **intraday, "symbol": symbol}

    # ── Intraday helpers ──────────────────────────────────────────────────────

    async def _get_intraday(self, symbol: str) -> dict:
        cached = self._intraday_cache.get(symbol)
        if cached and time.monotonic() - cached["ts"] < _INTRADAY_TTL:
            return cached["data"]

        row = await self._pool.fetchrow("""
            SELECT
                MIN(low)::float          AS day_low,
                MAX(high)::float         AS day_high,
                FIRST(open, time)::float AS day_open
            FROM candles_3min
            WHERE symbol = $1
              AND time >= (NOW() AT TIME ZONE 'Asia/Kolkata')::date
        """, symbol)

        data: dict = {}
        if row and row["day_high"] is not None:
            data = {
                "day_high": round(float(row["day_high"]), 2),
                "day_low":  round(float(row["day_low"]),  2),
                "day_open": round(float(row["day_open"]), 2),
            }

        self._intraday_cache[symbol] = {"data": data, "ts": time.monotonic()}
        return data
