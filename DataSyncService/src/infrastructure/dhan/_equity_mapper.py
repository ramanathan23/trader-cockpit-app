import logging

import asyncpg

from .instrument_master import EquityRecord
from shared.constants import DEFAULT_ACQUIRE_TIMEOUT
from shared.utils import parse_pg_command_result

logger = logging.getLogger(__name__)


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

    sec_ids  = [e.security_id      for e in equities]
    symbols  = [e.trading_symbol   for e in equities]
    segments = [e.exchange_segment for e in equities]

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

    matched   = parse_pg_command_result(result)
    unmatched = len(equities) - matched
    logger.info(
        "Equity mapping: %d matched, %d unmatched (not in symbols table)",
        matched, unmatched,
    )
    return matched, unmatched
