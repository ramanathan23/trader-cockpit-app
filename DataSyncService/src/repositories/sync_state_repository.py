"""
Reads and writes the sync_state table: per-(symbol, timeframe) sync metadata.
"""

import asyncpg

from ._sync_state_reads import get_snapshots, get_summary, get_for_symbol
from ._sync_state_writes import upsert, upsert_many


class SyncStateRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(self, conn, symbol, timeframe, status,
                     last_data_ts=None, error_msg=None):
        return await upsert(conn, symbol, timeframe, status, last_data_ts, error_msg)

    async def upsert_many(self, conn, records):
        return await upsert_many(conn, records)

    async def get_snapshots(self, symbols, timeframe):
        return await get_snapshots(self._pool, symbols, timeframe)

    async def get_summary(self):
        return await get_summary(self._pool)

    async def get_for_symbol(self, symbol):
        return await get_for_symbol(self._pool, symbol)

