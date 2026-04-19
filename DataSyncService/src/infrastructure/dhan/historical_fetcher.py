"""
DhanHistoricalFetcher — 1-min OHLCV batch fetcher with rate limiting.

Rate limits (per Dhan docs):
  - 10 requests / second  (configurable via settings)
  - 10,000 requests / day (resets at IST midnight)

Each request covers up to 90 calendar days; initial fetch uses the full 90-day window.
Incremental fetch uses last_ts → today per symbol.

Usage:
    fetcher = DhanHistoricalFetcher(client_id, access_token)
    data = await fetcher.fetch_initial(fno_symbols)    # list of (sym, sec_id, seg)
    data = await fetcher.fetch_incremental(stale_syms)  # list of (sym, sec_id, seg, last_ts)
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

import httpx
import pandas as pd

from shared.constants import IST

from ._historical_client import fetch_1min_ohlcv

logger = logging.getLogger(__name__)

_INITIAL_HISTORY_DAYS = 90
_MAX_DAYS_PER_REQUEST = 90

# Type aliases
_InitialEntry     = tuple[str, int, str]              # symbol, security_id, exchange_segment
_IncrementalEntry = tuple[str, int, str, datetime]    # + last_ts


class DhanHistoricalFetcher:
    """
    Fetches 1-min OHLCV from Dhan historical API with built-in rate limiting.

    Rate enforced by processing in batches of `rate_per_sec` and sleeping
    the remainder of each 1-second window between batches.
    Daily budget tracked in-memory; resets at IST midnight.
    """

    def __init__(
        self,
        client_id: str,
        access_token: str,
        url: str = "https://api.dhan.co/v2/charts/historical",
        rate_per_sec: int = 10,
        daily_budget: int = 10_000,
        budget_safety: int = 100,
    ) -> None:
        self._url          = url
        self._headers      = {
            "access-token": access_token,
            "client-id":    client_id,
            "Content-Type": "application/json",
        }
        self._rate         = rate_per_sec
        self._daily_budget = daily_budget
        self._safety       = budget_safety
        self._daily_used   = 0
        self._reset_day: date | None = None

    # ── Budget tracking ───────────────────────────────────────────────────────

    def _maybe_reset(self) -> None:
        today = datetime.now(tz=IST).date()
        if self._reset_day != today:
            self._daily_used = 0
            self._reset_day  = today

    def remaining_budget(self) -> int:
        self._maybe_reset()
        return max(0, self._daily_budget - self._daily_used)

    def _budget_ok(self) -> bool:
        self._maybe_reset()
        return self._daily_used < self._daily_budget - self._safety

    # ── Public API ────────────────────────────────────────────────────────────

    async def fetch_initial(
        self,
        symbols: list[_InitialEntry],
    ) -> dict[str, pd.DataFrame]:
        """Fetch 90 days of 1min history for INITIAL symbols (1 request each)."""
        today     = datetime.now(tz=IST).date()
        from_date = today - timedelta(days=_INITIAL_HISTORY_DAYS - 1)
        tasks = [
            (sym, sec_id, seg, from_date, today)
            for sym, sec_id, seg in symbols
        ]
        return await self._run_batched(tasks)

    async def fetch_incremental(
        self,
        symbols: list[_IncrementalEntry],
    ) -> dict[str, pd.DataFrame]:
        """Fetch since last_ts → today for FETCH_INCREMENTAL symbols (1 request each)."""
        today = datetime.now(tz=IST).date()
        tasks = []
        for sym, sec_id, seg, last_ts in symbols:
            from_date = last_ts.astimezone(IST).date()
            # Guard: never request future dates
            if from_date > today:
                continue
            # Clamp to 90-day window max
            min_from = today - timedelta(days=_MAX_DAYS_PER_REQUEST - 1)
            tasks.append((sym, sec_id, seg, max(from_date, min_from), today))
        return await self._run_batched(tasks)

    # ── Internal batch runner ─────────────────────────────────────────────────

    async def _run_batched(
        self,
        tasks: list[tuple],  # (sym, sec_id, seg, from_date, to_date)
    ) -> dict[str, pd.DataFrame]:
        """
        Execute tasks in batches of `_rate` per second.
        Each batch fires concurrently; we sleep the remainder of the 1-sec window
        between batches to stay within 10 req/sec.
        """
        results: dict[str, pd.DataFrame] = {}
        if not tasks:
            return results

        async with httpx.AsyncClient(headers=self._headers, timeout=30.0) as client:
            for i in range(0, len(tasks), self._rate):
                if not self._budget_ok():
                    logger.warning(
                        "[1m] Dhan daily budget near limit (%d/%d used) — stopping early",
                        self._daily_used, self._daily_budget,
                    )
                    break

                batch    = tasks[i : i + self._rate]
                t_start  = asyncio.get_event_loop().time()

                batch_results = await asyncio.gather(
                    *[
                        fetch_1min_ohlcv(client, self._url, sec_id, seg, from_date, to_date)
                        for _, sec_id, seg, from_date, to_date in batch
                    ],
                    return_exceptions=True,
                )

                self._daily_used += len(batch)

                for (sym, _, _, _, _), result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.warning("[1m] %s unexpected error: %s", sym, result)
                    elif not result.empty:
                        results[sym] = result

                elapsed = asyncio.get_event_loop().time() - t_start
                remaining_tasks = len(tasks) - (i + len(batch))
                if elapsed < 1.0 and remaining_tasks > 0:
                    await asyncio.sleep(1.0 - elapsed)

        logger.debug(
            "[1m] batch done: %d/%d symbols returned data, %d API calls used today",
            len(results), len(tasks), self._daily_used,
        )
        return results
