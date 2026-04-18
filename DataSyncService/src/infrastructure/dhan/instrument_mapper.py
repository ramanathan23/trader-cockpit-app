"""
Maps Dhan instrument master records onto the trader_cockpit database.

Responsibilities:
  1. Update symbols.dhan_security_id + exchange_segment for all matched equities.
  2. Upsert index_futures rows (NIFTY / BANKNIFTY / SENSEX front-month contracts).
  3. Mark exactly one index_futures row per underlying as is_active (nearest expiry
     on or after today).

Returns a MappingResult summary for the caller / API response.
"""

import logging
from dataclasses import dataclass
from datetime import date

import asyncpg

from .instrument_master import EquityRecord, IndexFutureRecord
from shared.constants import DEFAULT_ACQUIRE_TIMEOUT
from shared.utils import parse_pg_command_result

logger = logging.getLogger(__name__)


@dataclass
class MappingResult:
    equities_matched:   int
    equities_unmatched: int
    index_futures_upserted: int
    index_futures_activated: int


async def apply_equity_mapping(
    pool: asyncpg.Pool,
    equities: list[EquityRecord],
) -> tuple[int, int]:
    """
    Bulk-update dhan_security_id + exchange_segment on the symbols table.

    Uses a single unnest() UPDATE — one round-trip regardless of list size.
    Only rows already in symbols are updated; new symbols are NOT inserted here
    (that is DataSyncService's job via symbols.csv).

    Returns (matched_count, unmatched_count).
    """
    if not equities:
        return 0, 0

    sec_ids   = [e.security_id      for e in equities]
    symbols   = [e.trading_symbol   for e in equities]
    segments  = [e.exchange_segment for e in equities]

    async with pool.acquire(timeout=DEFAULT_ACQUIRE_TIMEOUT) as conn:
        result = await conn.execute("""
            UPDATE symbols AS s
            SET
                dhan_security_id = m.security_id,
                exchange_segment = m.exchange_segment
            FROM (
                SELECT
                    unnest($1::bigint[])  AS security_id,
                    unnest($2::text[])    AS trading_symbol,
                    unnest($3::text[])    AS exchange_segment
            ) AS m
            WHERE s.symbol = m.trading_symbol
              AND s.series  = 'EQ'
        """, sec_ids, symbols, segments)

    matched = parse_pg_command_result(result)
    unmatched = len(equities) - matched
    logger.info(
        "Equity mapping: %d matched, %d unmatched (not in symbols table)",
        matched, unmatched,
    )
    return matched, unmatched


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
            # Upsert all contracts.
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

            # Reset all active flags, then set the nearest upcoming expiry.
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
