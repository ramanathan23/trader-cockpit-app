import asyncpg

from ..domain.sync_state_snapshot import SyncStateSnapshot
from shared.constants import DEFAULT_ACQUIRE_TIMEOUT


async def get_snapshots(
    pool: asyncpg.Pool,
    symbols: list[str],
    timeframe: str,
) -> list[SyncStateSnapshot]:
    if not symbols:
        return []

    async with pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
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


async def get_summary(pool: asyncpg.Pool) -> list[dict]:
    async with pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
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


async def get_for_symbol(pool: asyncpg.Pool, symbol: str) -> list[dict]:
    async with pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
        rows = await conn.fetch(
            "SELECT * FROM sync_state WHERE symbol = $1 ORDER BY timeframe",
            symbol.upper(),
        )
    return [dict(r) for r in rows]
