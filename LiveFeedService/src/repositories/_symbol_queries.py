from __future__ import annotations

import logging

import asyncpg

from ..domain.instrument_meta import InstrumentMeta

_ACQUIRE_TIMEOUT = 30
logger = logging.getLogger(__name__)


async def _load_watchlist_instruments(pool: asyncpg.Pool, is_fno: bool) -> list[InstrumentMeta]:
    """Load watchlisted symbols for one segment (FNO or equity)."""
    fno_clause = (
        "AND s.is_fno = TRUE"
        if is_fno
        else "AND (s.is_fno = FALSE OR s.is_fno IS NULL)"
    )
    async with pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
        rows = await conn.fetch(f"""
            SELECT s.symbol, s.dhan_security_id, s.exchange_segment
            FROM   daily_scores ds
            JOIN   symbols s ON s.symbol = ds.symbol
            WHERE  ds.score_date = (SELECT MAX(score_date) FROM daily_scores)
              AND  ds.is_watchlist = TRUE
              AND  s.dhan_security_id IS NOT NULL
              AND  s.series = 'EQ'
              {fno_clause}
            ORDER  BY ds.rank ASC
        """)
    return [
        InstrumentMeta(
            symbol           = r["symbol"],
            dhan_security_id = r["dhan_security_id"],
            exchange_segment = r["exchange_segment"],
            is_index_future  = False,
        )
        for r in rows
    ]


async def _load_all_equity_instruments(pool: asyncpg.Pool) -> list[InstrumentMeta]:
    """Fallback: all equities with a Dhan security ID."""
    async with pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
        rows = await conn.fetch("""
            SELECT symbol, dhan_security_id, exchange_segment
            FROM   symbols
            WHERE  dhan_security_id IS NOT NULL
              AND  series = 'EQ'
            ORDER  BY symbol
        """)
    instruments = [
        InstrumentMeta(
            symbol           = r["symbol"],
            dhan_security_id = r["dhan_security_id"],
            exchange_segment = r["exchange_segment"],
            is_index_future  = False,
        )
        for r in rows
    ]
    logger.info("Loaded %d equity instruments from DB (full universe)", len(instruments))
    return instruments
