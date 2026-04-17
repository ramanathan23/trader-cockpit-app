"""
SymbolRepository (LiveFeedService): reads mapped instruments from the shared DB.

All writes to symbols / index_futures belong to DataSyncService.
This repository is read-only.

Subscription modes:
  - Watchlist mode (default): subscribe only top-50 scored symbols from daily_scores.
  - Fallback mode: if no daily_scores exist, fall back to all equities.
"""

from __future__ import annotations

import logging

import asyncpg

from ..domain.instrument_meta import InstrumentMeta

logger = logging.getLogger(__name__)

_ACQUIRE_TIMEOUT = 30


class SymbolRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def load_equity_instruments(self) -> list[InstrumentMeta]:
        """
        Load equities to subscribe to Dhan WebSocket.

        Loads the watchlisted FNO instruments (top-50 bull + top-50 bear) and
        watchlisted equity instruments (top-50 bull + top-50 bear), giving up
        to 200 subscriptions split across four buckets.
        Falls back to the full universe if no scores exist.
        """
        fno_instruments    = await self._load_watchlist_instruments(is_fno=True)
        equity_instruments = await self._load_watchlist_instruments(is_fno=False)

        if fno_instruments or equity_instruments:
            logger.info(
                "Watchlist subscriptions — FNO: %d, equity: %d (total: %d)",
                len(fno_instruments), len(equity_instruments),
                len(fno_instruments) + len(equity_instruments),
            )
            # Deduplicate by security_id in case a symbol appears in both lists
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
        return await self._load_all_equity_instruments()

    async def _load_watchlist_instruments(self, is_fno: bool) -> list[InstrumentMeta]:
        """Load watchlisted symbols for one segment (FNO or equity)."""
        fno_clause = "AND s.is_fno = TRUE" if is_fno else "AND (s.is_fno = FALSE OR s.is_fno IS NULL)"
        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
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

    async def _load_all_equity_instruments(self) -> list[InstrumentMeta]:
        """Fallback: all equities with a Dhan security ID."""
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
        logger.info("Loaded %d equity instruments from DB (full universe)", len(instruments))
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
