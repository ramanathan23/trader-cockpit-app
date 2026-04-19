"""SymbolRepository: reads mapped instruments from the shared DB (read-only)."""
from __future__ import annotations

import logging

import asyncpg

from ..domain.instrument_meta import InstrumentMeta
from ._symbol_queries import _load_watchlist_instruments, _load_all_equity_instruments

logger = logging.getLogger(__name__)

_ACQUIRE_TIMEOUT = 30


class SymbolRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def load_equity_instruments(self) -> list[InstrumentMeta]:
        """Load equities to subscribe to Dhan WebSocket (watchlist or full fallback)."""
        fno_instruments    = await _load_watchlist_instruments(self._pool, is_fno=True)
        equity_instruments = await _load_watchlist_instruments(self._pool, is_fno=False)

        if fno_instruments or equity_instruments:
            logger.info(
                "Watchlist subscriptions — FNO: %d, equity: %d (total: %d)",
                len(fno_instruments), len(equity_instruments),
                len(fno_instruments) + len(equity_instruments),
            )
            seen: set[str] = set()
            merged: list[InstrumentMeta] = []
            for inst in fno_instruments + equity_instruments:
                if inst.dhan_security_id not in seen:
                    seen.add(inst.dhan_security_id)
                    merged.append(inst)
            return merged

        logger.warning(
            "No daily_scores found — falling back to full equity universe. "
            "Run POST /api/v1/scores/compute-unified on MomentumScorerService first."
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
