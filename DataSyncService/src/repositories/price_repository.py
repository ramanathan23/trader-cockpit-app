"""
High-performance bulk ingestion into TimescaleDB via asyncpg COPY.

Strategy:
  1. COPY all records into a temporary table (fastest write path).
  2. INSERT INTO target ... SELECT FROM temp ON CONFLICT DO NOTHING
     -> idempotent; re-running the same data is safe.
"""

import asyncpg
import pandas as pd

from ._price_reads import get_last_data_ts_bulk, get_ohlcv
from ._price_writes import _to_records, bulk_ingest


class PriceRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_last_data_ts_bulk(self, symbols, interval, *, query_timeout=300.0):
        return await get_last_data_ts_bulk(
            self._pool, symbols, interval, query_timeout=query_timeout
        )

    async def get_ohlcv(self, symbol, interval, *, limit=500, from_ts=None, to_ts=None):
        return await get_ohlcv(
            self._pool, symbol, interval, limit=limit, from_ts=from_ts, to_ts=to_ts
        )

    async def bulk_ingest(self, symbol_data: dict[str, pd.DataFrame], interval: str) -> int:
        return await bulk_ingest(self._pool, symbol_data, interval)


__all__ = ["PriceRepository", "_to_records"]

