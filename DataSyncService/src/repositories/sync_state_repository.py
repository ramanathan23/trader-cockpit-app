"""
Reads and writes the sync_state table: per-(symbol, timeframe) sync metadata.
"""

import logging
from datetime import datetime

import asyncpg

logger = logging.getLogger(__name__)

_IST = "Asia/Kolkata"


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

    async def get_stale_daily(
        self, symbols: list[str]
    ) -> list[tuple[str, datetime | None]]:
        """Symbols whose last daily bar (IST date) is before today."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"""
                WITH all_syms AS (SELECT unnest($1::text[]) AS symbol),
                last_bars AS (
                    SELECT symbol, MAX(time) AS last_time
                    FROM   price_data_daily
                    WHERE  symbol = ANY($1::text[])
                    GROUP  BY symbol
                )
                SELECT a.symbol, lb.last_time
                FROM   all_syms a
                LEFT   JOIN last_bars lb ON lb.symbol = a.symbol
                WHERE  lb.last_time IS NULL
                   OR  (lb.last_time AT TIME ZONE '{_IST}')::date
                           < (NOW() AT TIME ZONE '{_IST}')::date
                ORDER  BY lb.last_time ASC NULLS FIRST
            """, symbols)
        return [(r["symbol"], r["last_time"]) for r in rows]

    async def get_stale_1m(
        self, symbols: list[str]
    ) -> list[tuple[str, datetime | None]]:
        """Symbols eligible for 1m patch (last bar > 15 min old, market not yet closed)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"""
                WITH all_syms AS (SELECT unnest($1::text[]) AS symbol),
                last_bars AS (
                    SELECT symbol, MAX(time) AS last_time
                    FROM   price_data_1m
                    WHERE  symbol = ANY($1::text[])
                    GROUP  BY symbol
                )
                SELECT a.symbol, lb.last_time
                FROM   all_syms a
                LEFT   JOIN last_bars lb ON lb.symbol = a.symbol
                WHERE  lb.last_time IS NULL
                   OR  (
                       lb.last_time < NOW() - INTERVAL '15 minutes'
                       AND NOT (
                           (lb.last_time AT TIME ZONE '{_IST}')::date
                               = (NOW() AT TIME ZONE '{_IST}')::date
                           AND (lb.last_time AT TIME ZONE '{_IST}')::time
                               >= TIME '15:30:00'
                       )
                   )
                ORDER  BY lb.last_time ASC NULLS FIRST
            """, symbols)
        return [(r["symbol"], r["last_time"]) for r in rows]

    async def get_summary(self) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    timeframe,
                    COUNT(*)                                    AS total,
                    COUNT(*) FILTER (WHERE status = 'synced')  AS synced,
                    COUNT(*) FILTER (WHERE status = 'empty')   AS empty,
                    COUNT(*) FILTER (WHERE status = 'error')   AS errors,
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                    MAX(last_synced_at)                         AS last_synced_at
                FROM sync_state
                GROUP BY timeframe
                ORDER BY timeframe
            """)
        return [dict(r) for r in rows]

    async def get_for_symbol(self, symbol: str) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM sync_state WHERE symbol = $1 ORDER BY timeframe",
                symbol.upper(),
            )
        return [dict(r) for r in rows]
