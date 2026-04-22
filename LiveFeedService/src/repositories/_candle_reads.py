from __future__ import annotations

import asyncpg

from ..domain.candle import Candle
from shared.constants import DEFAULT_ACQUIRE_TIMEOUT

_EQUITY_TABLE = "candles_5min"
_FUTURE_TABLE = "index_future_candles_5min"

# 9:15 IST = 03:45 UTC; 2000-01-03 is Monday → 5-min buckets align to IST open
_ORB_ORIGIN = "TIMESTAMPTZ '2000-01-03 03:45:00+00'"


async def list_from_1min_aggregated(
    pool:            asyncpg.Pool,
    symbols:         list[str],
    *,
    candle_min:      int = 5,
    days_back:       int = 2,
) -> dict[str, list[Candle]]:
    """
    Aggregate price_data_1min → candle_min-minute candles for equities only.
    Returns today's session + prior session (days_back=2) so detectors have
    a valid intra-session volume baseline from the moment the feed starts.
    Index futures have no 1-min source; callers must skip is_index_future=True.
    """
    if not symbols:
        return {}
    interval = f"{candle_min} minutes"
    async with pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
        rows = await conn.fetch(f"""
            SELECT
                time_bucket(
                    INTERVAL '{interval}',
                    time,
                    {_ORB_ORIGIN}
                )                  AS bucket,
                symbol,
                FIRST(open, time)  AS open,
                MAX(high)          AS high,
                MIN(low)           AS low,
                LAST(close, time)  AS close,
                SUM(volume)        AS volume
            FROM price_data_1min
            WHERE symbol = ANY($1::text[])
              AND time >= NOW() - ($2 * INTERVAL '1 day')
              AND (time AT TIME ZONE 'Asia/Kolkata')::time >= '09:14:00'
              AND (time AT TIME ZONE 'Asia/Kolkata')::time <  '15:31:00'
            GROUP BY bucket, symbol
            ORDER BY symbol, bucket
        """, symbols, days_back)
    history: dict[str, list[Candle]] = {}
    for row in rows:
        candle = Candle(
            symbol=row["symbol"], boundary=row["bucket"],
            open=float(row["open"]),  high=float(row["high"]),
            low=float(row["low"]),    close=float(row["close"]),
            volume=int(row["volume"]), tick_count=0,
            is_index_future=False,
        )
        history.setdefault(row["symbol"], []).append(candle)
    return history


async def list_recent_by_symbol(
    pool: asyncpg.Pool,
    symbols: list[str],
    *,
    is_index_future: bool,
    limit_per_symbol: int,
) -> dict[str, list[Candle]]:
    """Load the most recent candles per symbol to warm-start in-memory state."""
    if not symbols:
        return {}
    table = _FUTURE_TABLE if is_index_future else _EQUITY_TABLE
    async with pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
        rows = await conn.fetch(f"""
            WITH ranked AS (
                SELECT
                    time, symbol, open, high, low, close, volume, tick_count,
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
            symbol=row["symbol"], boundary=row["time"],
            open=float(row["open"]),   high=float(row["high"]),
            low=float(row["low"]),     close=float(row["close"]),
            volume=int(row["volume"]), tick_count=int(row["tick_count"]),
            is_index_future=is_index_future,
        )
        history.setdefault(row["symbol"], []).append(candle)
    return history
