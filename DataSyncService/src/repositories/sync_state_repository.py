"""
Reads and writes the sync_state table: per-(symbol, timeframe) sync metadata.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import asyncpg

logger = logging.getLogger(__name__)

_ACQUIRE_TIMEOUT = 30  # seconds to wait for a pool connection before giving up


@dataclass(frozen=True)
class SyncStateSnapshot:
    symbol: str
    timeframe: str
    last_synced_at: datetime | None
    last_data_ts: datetime | None
    status: str | None


class SyncStateRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(
        self,
        conn: asyncpg.Connection,
        symbol: str,
        timeframe: str,
        status: str,
        last_data_ts: datetime | None = None,
        error_msg: str | None = None,
    ) -> None:
        await conn.execute("""
            INSERT INTO sync_state (symbol, timeframe, last_synced_at, last_data_ts, status, error_msg)
            VALUES ($1, $2, NOW(), $3, $4, $5)
            ON CONFLICT (symbol, timeframe) DO UPDATE SET
                last_synced_at = NOW(),
                last_data_ts   = COALESCE($3, sync_state.last_data_ts),
                status         = $4,
                error_msg      = $5
        """, symbol, timeframe, last_data_ts, status, error_msg)

    async def upsert_many(
        self,
        conn: asyncpg.Connection,
        records: list[tuple],
    ) -> None:
        """
        Batch-upsert sync state for multiple (symbol, timeframe) pairs in one
        round-trip, replacing N sequential INSERTs with a single unnest query.

        Each element of *records* is a 5-tuple:
            (symbol, timeframe, last_data_ts | None, status, error_msg | None)
        """
        if not records:
            return

        symbols, timeframes, last_data_tss, statuses, error_msgs = zip(*records)
        await conn.execute("""
            INSERT INTO sync_state
                (symbol, timeframe, last_synced_at, last_data_ts, status, error_msg)
            SELECT
                unnest($1::text[]),
                unnest($2::text[]),
                NOW(),
                unnest($3::timestamptz[]),
                unnest($4::text[]),
                unnest($5::text[])
            ON CONFLICT (symbol, timeframe) DO UPDATE SET
                last_synced_at = NOW(),
                last_data_ts   = COALESCE(EXCLUDED.last_data_ts, sync_state.last_data_ts),
                status         = EXCLUDED.status,
                error_msg      = EXCLUDED.error_msg
        """,
            list(symbols),
            list(timeframes),
            list(last_data_tss),
            list(statuses),
            list(error_msgs),
        )

    async def get_snapshots(
        self,
        symbols: list[str],
        timeframe: str,
    ) -> list[SyncStateSnapshot]:
        if not symbols:
            return []

        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            rows = await conn.fetch("""
                WITH all_syms AS (SELECT unnest($1::text[]) AS symbol),
                states AS (
                    SELECT symbol, timeframe, last_synced_at, last_data_ts, status
                    FROM sync_state
                    WHERE timeframe = $2
                      AND symbol = ANY($1::text[])
                )
                SELECT
                    a.symbol,
                    COALESCE(s.timeframe, $2::text) AS timeframe,
                    s.last_synced_at,
                    s.last_data_ts,
                    s.status
                FROM   all_syms a
                LEFT   JOIN states s ON s.symbol = a.symbol
                ORDER  BY s.last_data_ts ASC NULLS FIRST, a.symbol
            """, symbols, timeframe)

        return [
            SyncStateSnapshot(
                symbol=row["symbol"],
                timeframe=row["timeframe"],
                last_synced_at=row["last_synced_at"],
                last_data_ts=row["last_data_ts"],
                status=row["status"],
            )
            for row in rows
        ]

    async def get_summary(self) -> list[dict]:
        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            rows = await conn.fetch("""
                SELECT
                    timeframe,
                    COUNT(*)                                    AS total,
                    COUNT(*) FILTER (WHERE status = 'synced')  AS synced,
                    COUNT(*) FILTER (WHERE status = 'empty')   AS empty,
                    COUNT(*) FILTER (WHERE status = 'error')   AS errors,
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                    MAX(last_synced_at)                        AS last_synced_at
                FROM sync_state
                GROUP BY timeframe
                ORDER BY timeframe
            """)
        return [dict(r) for r in rows]

    async def get_for_symbol(self, symbol: str) -> list[dict]:
        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            rows = await conn.fetch(
                "SELECT * FROM sync_state WHERE symbol = $1 ORDER BY timeframe",
                symbol.upper(),
            )
        return [dict(r) for r in rows]
