"""
SymbolRepository (LiveFeedService): reads mapped instruments from the shared DB.

All writes to symbols / index_futures belong to DataSyncService.
This repository is read-only.
"""

from __future__ import annotations

import logging

import asyncpg

from ..domain.models import InstrumentMeta

logger = logging.getLogger(__name__)

_ACQUIRE_TIMEOUT = 30


class SymbolRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def load_equity_instruments(self) -> list[InstrumentMeta]:
        """
        Return all equities that have a Dhan security ID.
        These are the 2000+ stocks we subscribe to.
        """
        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
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
        logger.info("Loaded %d equity instruments from DB", len(instruments))
        return instruments

    async def load_index_future_instruments(self) -> list[InstrumentMeta]:
        """
        Return the active front-month index futures (NIFTY, BANKNIFTY, SENSEX).
        Exactly one row per underlying (is_active = TRUE).
        """
        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            rows = await conn.fetch("""
                SELECT underlying, dhan_security_id, exchange_segment
                FROM   index_futures
                WHERE  is_active = TRUE
                ORDER  BY underlying
            """)

        instruments = [
            InstrumentMeta(
                symbol           = r["underlying"],   # e.g. "NIFTY"
                dhan_security_id = r["dhan_security_id"],
                exchange_segment = r["exchange_segment"],
                is_index_future  = True,
                underlying       = r["underlying"],
            )
            for r in rows
        ]
        logger.info("Loaded %d active index future instruments from DB", len(instruments))
        return instruments
