"""
CandleRepository: batch-writes completed 5-min candles to TimescaleDB.

Uses the same COPY → INSERT pattern as DataSyncService for high throughput.
Equity candles → candles_5min
Index future candles → index_future_candles_5min
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime

import asyncpg

from ..domain.models import Candle

logger = logging.getLogger(__name__)

_EQUITY_TABLE  = "candles_5min"
_FUTURE_TABLE  = "index_future_candles_5min"
_COLUMNS       = ("time", "symbol", "open", "high", "low", "close", "volume", "tick_count")
_ACQUIRE_TIMEOUT = 30


def _to_record(candle: Candle) -> tuple:
    return (
        candle.boundary,
        candle.symbol,
        candle.open,
        candle.high,
        candle.low,
        candle.close,
        candle.volume,
        candle.tick_count,
    )


class CandleRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_recent_by_symbol(
        self,
        symbols: list[str],
        *,
        is_index_future: bool,
        limit_per_symbol: int,
    ) -> dict[str, list[Candle]]:
        """Load the most recent candles per symbol to warm-start in-memory state."""
        if not symbols:
            return {}

        table = _FUTURE_TABLE if is_index_future else _EQUITY_TABLE
        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            rows = await conn.fetch(f"""
                WITH ranked AS (
                    SELECT
                        time,
                        symbol,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        tick_count,
                        ROW_NUMBER() OVER (
                            PARTITION BY symbol
                            ORDER BY time DESC
                        ) AS rn
                    FROM {table}
                    WHERE symbol = ANY($1::text[])
                )
                SELECT time, symbol, open, high, low, close, volume, tick_count
                FROM ranked
                WHERE rn <= $2
                ORDER BY symbol, time
            """, symbols, limit_per_symbol)

        history: dict[str, list[Candle]] = {}
        for row in rows:
            candle = Candle(
                symbol=row["symbol"],
                boundary=row["time"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
                tick_count=int(row["tick_count"]),
                is_index_future=is_index_future,
            )
            history.setdefault(row["symbol"], []).append(candle)
        return history

    async def insert_many(self, candles: list[Candle]) -> int:
        """
        Bulk-insert candles. Equity and index future candles are routed to
        their respective tables automatically.

        Conflicts (same symbol + time) are silently ignored — idempotent.
        Returns total rows inserted.
        """
        if not candles:
            return 0

        equities = [c for c in candles if not c.is_index_future]
        futures  = [c for c in candles if c.is_index_future]

        inserted = 0
        if equities:
            inserted += await self._bulk_insert(equities, _EQUITY_TABLE)
        if futures:
            inserted += await self._bulk_insert(futures, _FUTURE_TABLE)
        return inserted

    # ── Private ───────────────────────────────────────────────────────────────

    async def _bulk_insert(self, candles: list[Candle], table: str) -> int:
        records = [_to_record(c) for c in candles]
        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            async with conn.transaction():
                await conn.execute(f"""
                    CREATE TEMP TABLE _candle_tmp
                        (LIKE {table} INCLUDING DEFAULTS)
                    ON COMMIT DROP
                """)
                await conn.copy_records_to_table(
                    "_candle_tmp",
                    records = records,
                    columns = list(_COLUMNS),
                )
                result = await conn.execute(f"""
                    INSERT INTO {table} ({", ".join(_COLUMNS)})
                    SELECT {", ".join(_COLUMNS)} FROM _candle_tmp
                    ON CONFLICT (symbol, time) DO NOTHING
                """)
        inserted = int(result.split()[-1])
        logger.debug("Inserted %d / %d candles into %s", inserted, len(candles), table)
        return inserted


class BufferedCandleWriter:
    """
    Accumulates candles and flushes to DB in batches or on a timer.

    This decouples the hot path (candle emit) from the slower DB write.

    Parameters
    ----------
    repo        : CandleRepository
    batch_size  : flush when buffer reaches this size
    flush_every : flush at least every N seconds (even if batch_size not reached)
    """

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
        except Exception as exc:
            logger.error("CandleWriter flush failed: %s", exc, exc_info=True)
            # Re-queue failed candles so we don't lose them.
            self._buffer = batch + self._buffer
