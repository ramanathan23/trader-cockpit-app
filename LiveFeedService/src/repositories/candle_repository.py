"""CandleRepository: batch-writes completed candles to TimescaleDB."""
from __future__ import annotations

import asyncio
import logging

import asyncpg

from ..domain.candle import Candle
from ._candle_reads import list_recent_by_symbol, list_from_1min_aggregated, _EQUITY_TABLE, _FUTURE_TABLE
from ._candle_writes import bulk_insert

logger = logging.getLogger(__name__)


class CandleRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_recent_by_symbol(
        self, symbols: list[str], *, is_index_future: bool, limit_per_symbol: int,
    ) -> dict[str, list[Candle]]:
        """Load the most recent candles per symbol to warm-start in-memory state."""
        return await list_recent_by_symbol(
            self._pool, symbols,
            is_index_future=is_index_future,
            limit_per_symbol=limit_per_symbol,
        )

    async def list_from_1min_aggregated(
        self, symbols: list[str], *, candle_min: int = 5, days_back: int = 2,
    ) -> dict[str, list[Candle]]:
        """Aggregate price_data_1min → N-min candles for equity warm-start."""
        return await list_from_1min_aggregated(
            self._pool, symbols, candle_min=candle_min, days_back=days_back,
        )

    async def insert_many(self, candles: list[Candle]) -> int:
        """Bulk-insert candles. Conflicts silently ignored. Returns rows inserted."""
        if not candles:
            return 0
        equities = [c for c in candles if not c.is_index_future]
        futures  = [c for c in candles if c.is_index_future]
        inserted = 0
        if equities:
            inserted += await bulk_insert(self._pool, equities, _EQUITY_TABLE)
        if futures:
            inserted += await bulk_insert(self._pool, futures, _FUTURE_TABLE)
        return inserted


class BufferedCandleWriter:
    """Accumulates candles and flushes to DB in batches or on a timer."""

    def __init__(
        self,
        repo:        CandleRepository,
        batch_size:  int   = 100,
        flush_every: float = 5.0,
    ) -> None:
        self._repo        = repo
        self._batch_size  = batch_size
        self._flush_every = flush_every
        self._buffer: list[Candle] = []
        self._lock = asyncio.Lock()

    async def add(self, candle: Candle) -> None:
        async with self._lock:
            self._buffer.append(candle)
            if len(self._buffer) >= self._batch_size:
                await self._flush()

    async def flush(self) -> None:
        async with self._lock:
            await self._flush()

    async def run_periodic_flush(self) -> None:
        """Background task: flush on the timer even if batch_size not reached."""
        while True:
            await asyncio.sleep(self._flush_every)
            await self.flush()

    async def _flush(self) -> None:
        if not self._buffer:
            return
        batch, self._buffer = self._buffer, []
        try:
            await self._repo.insert_many(batch)
        except (asyncpg.PostgresError, OSError) as exc:
            logger.error("CandleWriter flush failed: %s", exc, exc_info=True)
            self._buffer = batch + self._buffer
