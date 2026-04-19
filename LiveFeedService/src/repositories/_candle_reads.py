from __future__ import annotations

import asyncpg

from ..domain.candle import Candle
from shared.constants import DEFAULT_ACQUIRE_TIMEOUT

_EQUITY_TABLE = "candles_5min"
_FUTURE_TABLE = "index_future_candles_5min"


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
