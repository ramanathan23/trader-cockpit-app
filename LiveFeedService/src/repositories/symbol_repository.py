"""SymbolRepository: reads mapped instruments from the shared DB (read-only)."""
from __future__ import annotations

import logging

import asyncpg

from ..domain.instrument_meta import InstrumentMeta
from ._symbol_queries import _load_liquid_instruments, _load_all_equity_instruments

logger = logging.getLogger(__name__)

_ACQUIRE_TIMEOUT = 30


class SymbolRepository:
    def __init__(self, pool: asyncpg.Pool, min_adv_cr: float = 5.0) -> None:
        self._pool       = pool
        self._min_adv_cr = min_adv_cr

    async def load_equity_instruments(self) -> list[InstrumentMeta]:
        """Load all liquid equities (adv_20_cr >= min_adv_cr) from scored universe."""
        instruments = await _load_liquid_instruments(self._pool, self._min_adv_cr)
        if instruments:
            return instruments

        logger.warning(
            "No scored liquid instruments found (adv_20_cr >= %.1f) — "
            "falling back to full equity universe. Run scores/compute first.",
            self._min_adv_cr,
        )
        return await _load_all_equity_instruments(self._pool)

    async def load_index_future_instruments(self) -> list[InstrumentMeta]:
        """Return the active front-month index futures (NIFTY, BANKNIFTY, SENSEX)."""
        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            rows = await conn.fetch("""
                SELECT underlying, dhan_security_id, exchange_segment
                FROM   index_futures
                WHERE  is_active = TRUE
                ORDER  BY underlying
            """)
        instruments = [
            InstrumentMeta(
                symbol           = r["underlying"],
                dhan_security_id = r["dhan_security_id"],
                exchange_segment = r["exchange_segment"],
                is_index_future  = True,
                underlying       = r["underlying"],
            )
            for r in rows
        ]
        logger.info("Loaded %d active index future instruments from DB", len(instruments))
        return instruments
