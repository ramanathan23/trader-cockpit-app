from __future__ import annotations

import logging

import asyncpg

from ..domain.candle import Candle
from shared.constants import DEFAULT_ACQUIRE_TIMEOUT
from shared.utils import parse_pg_command_result

logger = logging.getLogger(__name__)

_COLUMNS = ("time", "symbol", "open", "high", "low", "close", "volume", "tick_count")


def _to_record(candle: Candle) -> tuple:
    return (
        candle.boundary, candle.symbol,
        candle.open, candle.high, candle.low, candle.close,
        candle.volume, candle.tick_count,
    )


async def bulk_insert(pool: asyncpg.Pool, candles: list[Candle], table: str) -> int:
    records = [_to_record(c) for c in candles]
    async with pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
        async with conn.transaction():
            await conn.execute(f"""
                CREATE TEMP TABLE _candle_tmp
                    (LIKE {table} INCLUDING DEFAULTS)
                ON COMMIT DROP
            """)
            await conn.copy_records_to_table(
                "_candle_tmp", records=records, columns=list(_COLUMNS),
            )
            result = await conn.execute(f"""
                INSERT INTO {table} ({", ".join(_COLUMNS)})
                SELECT {", ".join(_COLUMNS)} FROM _candle_tmp
                ON CONFLICT (symbol, time) DO NOTHING
            """)
    inserted = parse_pg_command_result(result)
    logger.debug("Inserted %d / %d candles into %s", inserted, len(candles), table)
    return inserted
