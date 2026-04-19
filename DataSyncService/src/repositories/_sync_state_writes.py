import asyncpg


async def upsert(
    conn: asyncpg.Connection,
    symbol: str,
    timeframe: str,
    status: str,
    last_data_ts=None,
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
