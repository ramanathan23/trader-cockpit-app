"""
InstrumentLoader — loads instrument metadata and warm-starts candle builders.

Single responsibility: translate DB records into InstrumentMeta objects
and seed each CandleBuilder with recent candle history from storage so that
rolling indicators are immediately usable on the first live tick.
"""
from __future__ import annotations

import logging

from ..core.tick_router import TickRouter
from ..domain.models import InstrumentMeta
from ..repositories.candle_repository import CandleRepository
from ..repositories.symbol_repository import SymbolRepository

logger = logging.getLogger(__name__)


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
    ) -> None:
        self._symbols    = symbol_repo
        self._candles    = candle_repo
        self._warm_limit = warm_limit

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
        equity_history = await self._candles.list_recent_by_symbol(
            [m.symbol for m in equities],
            is_index_future=False,
            limit_per_symbol=self._warm_limit,
        )
        future_history = await self._candles.list_recent_by_symbol(
            [m.symbol for m in index_futures],
            is_index_future=True,
            limit_per_symbol=self._warm_limit,
        )

        seeded = 0
        for meta in equities:
            builder = router.get_builder(meta.dhan_security_id)
            candles = equity_history.get(meta.symbol, [])
            if builder and candles:
                builder.seed_history(candles)
                seeded += 1

        for meta in index_futures:
            builder = router.get_builder(meta.dhan_security_id)
            candles = future_history.get(meta.symbol, [])
            if builder and candles:
                builder.seed_history(candles)
                seeded += 1

        logger.info("Hydrated candle history for %d instruments", seeded)
