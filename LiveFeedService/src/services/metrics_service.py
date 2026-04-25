from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, timezone, timedelta
from typing import Optional

import asyncpg

from ._metrics_loader import load_daily_metrics, fetch_intraday_metrics, fetch_daily_reference_closes

_IST = timezone(timedelta(hours=5, minutes=30))
logger = logging.getLogger(__name__)
_INTRADAY_TTL = 60


class MetricsService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._daily: dict[str, dict] = {}
        self._daily_date: date | None = None
        self._intraday_cache: dict[str, dict] = {}

    async def precompute_daily(self, force: bool = False) -> int:
        """Load precomputed daily metrics from symbol_metrics table. Cached per IST day."""
        today_ist: date = date.today()
        if not force and self._daily_date == today_ist and self._daily:
            logger.debug(
                "MetricsService: daily cache is current (%s, %d symbols) — skipping reload",
                today_ist, len(self._daily),
            )
            return len(self._daily)
        logger.info("MetricsService: loading precomputed daily metrics from symbol_metrics…")
        for attempt in range(1, 4):
            try:
                self._daily = await load_daily_metrics(self._pool)
                break
            except Exception as exc:
                if attempt == 3:
                    raise
                wait = attempt * 5
                logger.warning(
                    "MetricsService: load attempt %d/3 failed (%s) — retrying in %ds",
                    attempt, exc, wait,
                )
                await asyncio.sleep(wait)
        self._daily_date = today_ist
        logger.info(
            "MetricsService: loaded daily metrics for %d symbols (date=%s)",
            len(self._daily), today_ist,
        )
        return len(self._daily)

    def get_daily(self, symbol: str) -> Optional[dict]:
        return self._daily.get(symbol)

    def all_daily(self, offset: int = 0, limit: int | None = None) -> tuple[list[dict], int]:
        """Return symbols with daily metrics (in-memory, zero I/O)."""
        items = [{"symbol": s, **m} for s, m in self._daily.items()]
        total = len(items)
        if limit is not None:
            items = items[offset:offset + limit]
        elif offset > 0:
            items = items[offset:]
        return items, total

    async def get_with_intraday(self, symbol: str) -> Optional[dict]:
        daily = self._daily.get(symbol)
        if daily is None:
            return None
        intraday = await self._get_intraday(symbol)
        return {**daily, **intraday, "symbol": symbol}

    async def get_batch_with_intraday(self, symbols: list[str]) -> dict[str, dict]:
        """Return metrics for multiple symbols in a single call."""
        results: dict[str, dict] = {}
        to_fetch: list[str] = []
        for sym in symbols:
            daily = self._daily.get(sym)
            if daily is None:
                continue
            cached = self._intraday_cache.get(sym)
            if cached and time.monotonic() - cached["ts"] < _INTRADAY_TTL:
                results[sym] = {**daily, **cached["data"], "symbol": sym}
            else:
                to_fetch.append(sym)
        if to_fetch:
            tasks = [self._get_intraday(sym) for sym in to_fetch]
            intraday_results = await asyncio.gather(*tasks)
            for sym, intraday in zip(to_fetch, intraday_results):
                results[sym] = {**self._daily[sym], **intraday, "symbol": sym}
        return results

    async def _get_intraday(self, symbol: str) -> dict:
        cached = self._intraday_cache.get(symbol)
        if cached and time.monotonic() - cached["ts"] < _INTRADAY_TTL:
            return cached["data"]
        data = await fetch_intraday_metrics(self._pool, symbol, self._daily)
        self._intraday_cache[symbol] = {"data": data, "ts": time.monotonic()}
        return data

    async def get_daily_reference_closes(self, symbols: list[str]) -> dict[str, dict]:
        return await fetch_daily_reference_closes(self._pool, symbols)
