"""
MetricsService: loads per-symbol daily metrics at startup from the
symbol_metrics table, which is precomputed by DataSyncService after each
EOD sync.  No heavy aggregation runs at LiveFeedService startup.

Intraday metrics (day_high, day_low, day_open) are queried per-symbol
from candles_5min with a short TTL so they stay fresh during the session.

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
from datetime import date, timezone, timedelta
from typing import Optional

import asyncpg

_IST = timezone(timedelta(hours=5, minutes=30))

logger = logging.getLogger(__name__)

_INTRADAY_TTL = 60   # seconds — refresh day range every minute


class MetricsService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        # symbol → {week52_high, week52_low, atr_14, adv_20_cr, trading_days, …}
        self._daily: dict[str, dict] = {}
        # IST date on which _daily was last populated — None = never loaded
        self._daily_date: date | None = None
        # symbol → {data: {...}, ts: monotonic}
        self._intraday_cache: dict[str, dict] = {}

    # ── Startup precompute ────────────────────────────────────────────────────

    async def precompute_daily(self, force: bool = False) -> int:
        """
        Reads precomputed daily metrics from the symbol_metrics table.
        DataSyncService writes this table after each EOD sync, so no heavy
        aggregation runs at startup.

        Results are cached for the calendar day (IST).  Subsequent calls on
        the same day are no-ops and return the cached count immediately.
        Pass force=True to bypass the cache (e.g. after a manual recompute).
        """
        today_ist: date = date.today()  # server is assumed IST, or use:
        # today_ist = datetime.now(_IST).date()
        if not force and self._daily_date == today_ist and self._daily:
            logger.debug(
                "MetricsService: daily cache is current (%s, %d symbols) — skipping reload",
                today_ist, len(self._daily),
            )
            return len(self._daily)

        logger.info("MetricsService: loading precomputed daily metrics from symbol_metrics…")
        rows = await self._pool.fetch("""
            SELECT
                symbol,
                week52_high, week52_low,
                atr_14, adv_20_cr, trading_days,
                prev_day_high, prev_day_low, prev_day_close,
                prev_week_high, prev_week_low,
                prev_month_high, prev_month_low
            FROM symbol_metrics
        """)

        self._daily = {
            row["symbol"]: {
                "week52_high":    round(float(row["week52_high"]), 2)   if row["week52_high"]   else None,
                "week52_low":     round(float(row["week52_low"]),  2)   if row["week52_low"]    else None,
                "atr_14":         round(float(row["atr_14"] or 0), 2),
                "adv_20_cr":      round(float(row["adv_20_cr"] or 0), 1),
                "trading_days":   int(row["trading_days"]),
                "prev_day_high":  round(float(row["prev_day_high"]), 2)  if row["prev_day_high"]  else None,
                "prev_day_low":   round(float(row["prev_day_low"]),  2)  if row["prev_day_low"]   else None,
                "prev_day_close": round(float(row["prev_day_close"]),2)  if row["prev_day_close"] else None,
                "prev_week_high": round(float(row["prev_week_high"]),2)  if row["prev_week_high"] else None,
                "prev_week_low":  round(float(row["prev_week_low"]), 2)  if row["prev_week_low"]  else None,
                "prev_month_high":round(float(row["prev_month_high"]),2) if row["prev_month_high"] else None,
                "prev_month_low": round(float(row["prev_month_low"]), 2) if row["prev_month_low"]  else None,
            }
            for row in rows
        }
        self._daily_date = today_ist
        logger.info(
            "MetricsService: loaded daily metrics for %d symbols (date=%s)",
            len(self._daily), today_ist,
        )
        return len(self._daily)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_daily(self, symbol: str) -> Optional[dict]:
        """Instant lookup — no I/O. Returns None if symbol not in daily data."""
        return self._daily.get(symbol)

    def all_daily(self) -> list[dict]:
        """Return all symbols with their daily metrics (in-memory, zero I/O)."""
        return [{"symbol": s, **m} for s, m in self._daily.items()]

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
                FIRST(open, time)::float AS day_open,
                LAST(close, time)::float AS day_close
            FROM candles_5min
            WHERE symbol = $1
              AND time >= (NOW() AT TIME ZONE 'Asia/Kolkata')::date
        """, symbol)

        data: dict = {}
        if row and row["day_high"] is not None:
            day_close   = round(float(row["day_close"]), 2)
            prev_close  = (self._daily.get(symbol) or {}).get("prev_day_close")
            day_chg_pct = (
                round((day_close - prev_close) / prev_close * 100, 2)
                if prev_close else None
            )
            data = {
                "day_high":    round(float(row["day_high"]), 2),
                "day_low":     round(float(row["day_low"]),  2),
                "day_open":    round(float(row["day_open"]), 2),
                "day_close":   day_close,
                "day_chg_pct": day_chg_pct,
            }

        self._intraday_cache[symbol] = {"data": data, "ts": time.monotonic()}
        return data
