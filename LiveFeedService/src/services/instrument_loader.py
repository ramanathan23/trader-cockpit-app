"""
InstrumentLoader — loads instrument metadata and warm-starts candle builders.

Single responsibility: translate DB records into InstrumentMeta objects
and seed each CandleBuilder with recent candle history from storage so that
rolling indicators are immediately usable on the first live tick.

Seeding strategy for equities:
  1. Aggregate price_data_1min → N-min candles for today + prior session.
     This provides a valid intraday volume baseline at market open.
  2. Overlay any live candles already in candles_5min (mid-session restarts).
  3. Index futures have no 1-min source — use candles_5min only.
"""
from __future__ import annotations

import logging
from datetime import datetime

from ..core.tick_router import TickRouter
from ..domain.candle import Candle
from ..domain.instrument_meta import InstrumentMeta
from ..repositories.candle_repository import CandleRepository
from ..repositories.symbol_repository import SymbolRepository

logger = logging.getLogger(__name__)


def _merge_histories(base: list[Candle], overlay: list[Candle]) -> list[Candle]:
    """Merge two candle lists by boundary timestamp; overlay wins on conflict."""
    merged = {c.boundary: c for c in base}
    for c in overlay:
        merged[c.boundary] = c
    return sorted(merged.values(), key=lambda c: c.boundary)


class InstrumentLoader:
    """
    Loads equity and index-future instruments from DB and seeds candle history.

    Injected into FeedService so that loading and history hydration can be
    tested independently of the live tick-processing loop.
    """

    def __init__(
        self,
        symbol_repo: SymbolRepository,
        candle_repo: CandleRepository,
        warm_limit:  int,
        candle_min:  int = 5,
    ) -> None:
        self._symbols    = symbol_repo
        self._candles    = candle_repo
        self._warm_limit = warm_limit
        self._candle_min = candle_min

    async def load(self) -> tuple[list[InstrumentMeta], list[InstrumentMeta]]:
        """Return (equities, index_futures) from the symbol repository."""
        equities      = await self._symbols.load_equity_instruments()
        index_futures = await self._symbols.load_index_future_instruments()
        logger.info("Loaded %d equities + %d index futures", len(equities), len(index_futures))
        return equities, index_futures

    async def hydrate(
        self,
        router:        TickRouter,
        equities:      list[InstrumentMeta],
        index_futures: list[InstrumentMeta],
    ) -> None:
        """Seed each instrument's CandleBuilder with recent candle history."""
        equity_syms   = [m.symbol for m in equities]
        future_syms   = [m.symbol for m in index_futures]

        # Equities: aggregate 90d 1-min data → N-min candles (today + prior session)
        equity_1min = await self._candles.list_from_1min_aggregated(
            equity_syms, candle_min=self._candle_min, days_back=2,
        )
        # Overlay live candles already persisted from candles_5min (mid-session restarts)
        equity_live = await self._candles.list_recent_by_symbol(
            equity_syms, is_index_future=False, limit_per_symbol=self._warm_limit,
        )
        # Index futures: no 1-min source, use candles_5min only
        future_history = await self._candles.list_recent_by_symbol(
            future_syms, is_index_future=True, limit_per_symbol=self._warm_limit,
        )

        seeded = 0
        for meta in equities:
            builder = router.get_builder(meta.dhan_security_id)
            base    = equity_1min.get(meta.symbol, [])
            overlay = equity_live.get(meta.symbol, [])
            merged  = _merge_histories(base, overlay)
            if builder and merged:
                builder.seed_history(merged)
                seeded += 1

        for meta in index_futures:
            builder = router.get_builder(meta.dhan_security_id)
            candles = future_history.get(meta.symbol, [])
            if builder and candles:
                builder.seed_history(candles)
                seeded += 1

        logger.info("Hydrated candle history for %d instruments (1min-agg + live merge)", seeded)
