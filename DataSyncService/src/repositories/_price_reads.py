import logging
from datetime import datetime

import asyncpg

logger = logging.getLogger(__name__)

_TABLE_MAP: dict[str, str] = {
    "1d": "price_data_daily",
    "1m": "price_data_1min",
}
_QUERY_TABLE: dict[str, str] = {
    "1d": "price_data_daily",
    "1m": "price_data_1min",
}


async def get_last_data_ts_bulk(
    pool: asyncpg.Pool,
    symbols: list[str],
    interval: str,
    *,
    query_timeout: float = 300.0,
) -> dict[str, datetime | None]:
    """
    Single query: returns {symbol: MAX(time)} from the actual price table.

    This is the source of truth for gap detection — not sync_state, which
    can lag if a previous run crashed after ingest but before state update.
    Symbols with no rows at all get None.
    """
    table = _TABLE_MAP.get(interval)
    if not table:
        raise ValueError(f"Unsupported interval: {interval!r}")
    if not symbols:
        return {}
    async with pool.acquire(timeout=30) as conn:
        rows = await conn.fetch(
            f"SELECT DISTINCT ON (symbol) symbol, time AS last_ts "
            f"FROM {table} "
            f"WHERE symbol = ANY($1::text[]) "
            f"ORDER BY symbol, time DESC",
            symbols,
            timeout=query_timeout,
        )
    result = {row["symbol"]: row["last_ts"] for row in rows}
    return {s: result.get(s) for s in symbols}


async def get_ohlcv(
    pool: asyncpg.Pool,
    symbol: str,
    interval: str,
    *,
    limit: int = 500,
    from_ts: str | None = None,
    to_ts: str | None = None,
) -> list[dict]:
    """Query OHLCV rows for a symbol from a static table whitelist."""
    table = _QUERY_TABLE.get(interval)
    if not table:
        raise ValueError(f"Unsupported interval: {interval!r}")
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT time, open, high, low, close, volume "
            f"FROM {table} "
            f"WHERE symbol = $1 "
            f"  AND ($2::timestamptz IS NULL OR time >= $2::timestamptz) "
            f"  AND ($3::timestamptz IS NULL OR time <= $3::timestamptz) "
            f"ORDER BY time DESC LIMIT $4",
            symbol, from_ts, to_ts, limit,
        )
    return [dict(r) for r in rows]
