import logging
from datetime import date

import asyncpg

from .instrument_master import IndexFutureRecord
from shared.constants import DEFAULT_ACQUIRE_TIMEOUT
from shared.utils import parse_pg_command_result

logger = logging.getLogger(__name__)


async def apply_index_future_mapping(
    pool: asyncpg.Pool,
    futures: list[IndexFutureRecord],
    today: date | None = None,
) -> tuple[int, int]:
    """
    Upsert all index future records then mark the nearest active expiry.

    Returns (upserted_count, activated_count).
    """
    if not futures:
        return 0, 0

    today = today or date.today()

    async with pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
        async with conn.transaction():
            await conn.executemany("""
                INSERT INTO index_futures
                    (underlying, dhan_security_id, exchange_segment, lot_size, expiry_date, is_active)
                VALUES ($1, $2, $3, $4, $5, FALSE)
                ON CONFLICT (underlying, expiry_date) DO UPDATE SET
                    dhan_security_id = EXCLUDED.dhan_security_id,
                    exchange_segment = EXCLUDED.exchange_segment,
                    lot_size         = EXCLUDED.lot_size
            """, [
                (f.underlying, f.security_id, f.exchange_segment, f.lot_size, f.expiry_date)
                for f in futures
            ])

            upserted = len(futures)

            await conn.execute("UPDATE index_futures SET is_active = FALSE")

            result = await conn.execute("""
                UPDATE index_futures
                SET    is_active = TRUE
                WHERE  id IN (
                    SELECT DISTINCT ON (underlying) id
                    FROM   index_futures
                    WHERE  expiry_date >= $1
                    ORDER  BY underlying, expiry_date ASC
                )
            """, today)

            activated = parse_pg_command_result(result)

    logger.info(
        "Index futures: %d upserted, %d activated (nearest expiry from %s)",
        upserted, activated, today,
    )
    return upserted, activated
