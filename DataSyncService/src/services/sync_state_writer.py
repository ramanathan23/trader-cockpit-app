"""
SyncStateWriter — persists price data and records sync state after each batch.

Single responsibility: take a completed download batch, ingest prices into
TimescaleDB, and record the outcome (synced / empty / error) in sync_state.
No classification or fetch logic lives here.
"""
import logging
from datetime import datetime
from datetime import timezone

import asyncpg

from shared.constants import DEFAULT_ACQUIRE_TIMEOUT

from ..repositories.price_repository import PriceRepository
from ..repositories.sync_state_repository import SyncStateRepository

logger = logging.getLogger(__name__)


def _to_utc_datetime(ts) -> datetime:
    """Convert a pandas Timestamp to a UTC-aware Python datetime."""
    if hasattr(ts, "tzinfo") and ts.tzinfo is None:
        return ts.tz_localize("UTC").to_pydatetime()
    return ts.tz_convert("UTC").to_pydatetime().astimezone(timezone.utc)


class SyncStateWriter:
    """
    Writes price rows and sync_state records for one completed download batch.

    Injected into DailyFetcher so fetch strategies never touch the DB directly.
    """

    def __init__(
        self,
        pool:   asyncpg.Pool,
        prices: PriceRepository,
        state:  SyncStateRepository,
    ) -> None:
        self._pool   = pool
        self._prices = prices
        self._state  = state

    async def persist(self, batch: list[str], data: dict, interval: str) -> None:
        """Bulk-ingest price data and update sync state for the whole batch."""
        try:
            if data:
                inserted = await self._prices.bulk_ingest(data, interval)
                logger.debug(
                    "[%s] bulk_ingest: %d new rows for %d symbols",
                    interval, inserted, len(data),
                )
            await self._update_state(batch, data, interval)
        except (asyncpg.PostgresError, OSError) as exc:
            logger.error(
                "[%s] persist failed for batch [%s…]: %s",
                interval, batch[0], exc, exc_info=True,
            )
            await self._mark_error(batch, interval, str(exc))

    async def _update_state(
        self,
        symbols:  list[str],
        data:     dict,
        interval: str,
    ) -> None:
        records: list[tuple] = []
        for symbol, df in data.items():
            records.append((symbol, interval, _to_utc_datetime(df.index.max()), "synced", None))
        for symbol in symbols:
            if symbol not in data:
                records.append((symbol, interval, None, "empty", None))

        async with self._pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
            await self._state.upsert_many(conn, records)

    async def _mark_error(
        self,
        symbols:   list[str],
        interval:  str,
        error_msg: str,
    ) -> None:
        records = [(s, interval, None, "error", error_msg) for s in symbols]
        async with self._pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
            await self._state.upsert_many(conn, records)
