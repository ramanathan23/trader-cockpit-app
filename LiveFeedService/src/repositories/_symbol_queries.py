from __future__ import annotations

import logging

import asyncpg

from ..domain.instrument_meta import InstrumentMeta

_ACQUIRE_TIMEOUT = 30
logger = logging.getLogger(__name__)



async def _load_liquid_instruments(pool: asyncpg.Pool, min_adv_cr: float) -> list[InstrumentMeta]:
    """Load all scored equities with ADV >= min_adv_cr (liquid universe)."""
    async with pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
        rows = await conn.fetch("""
            SELECT s.symbol, s.dhan_security_id, s.exchange_segment
            FROM   daily_scores ds
            JOIN   symbols s       ON s.symbol  = ds.symbol
            JOIN   symbol_metrics sm ON sm.symbol = ds.symbol
            WHERE  ds.score_date = (SELECT MAX(score_date) FROM daily_scores)
              AND  s.dhan_security_id IS NOT NULL
              AND  s.series = 'EQ'
              AND  sm.adv_20_cr >= $1
            ORDER  BY ds.rank ASC
        """, min_adv_cr)
    instruments = [
        InstrumentMeta(
            symbol           = r["symbol"],
            dhan_security_id = r["dhan_security_id"],
            exchange_segment = r["exchange_segment"],
            is_index_future  = False,
        )
        for r in rows
    ]
    logger.info("Loaded %d liquid equity instruments (adv_20_cr >= %.1f)", len(instruments), min_adv_cr)
    return instruments


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
