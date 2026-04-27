from __future__ import annotations

import logging

from ..core.tick_router import TickRouter
from ..domain.instrument_meta import InstrumentMeta
from ..repositories.candle_repository import CandleRepository
from ..repositories.symbol_repository import SymbolRepository

logger = logging.getLogger(__name__)


class InstrumentLoader:
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
        """Seed equity CandleBuilders with 1-min aggregated history. Index futures start cold."""
        equity_syms = [m.symbol for m in equities]
        equity_history = await self._candles.list_from_1min_aggregated(
            equity_syms, candle_min=self._candle_min, days_back=2,
        )
        seeded = 0
        for meta in equities:
            builder = router.get_builder(meta.dhan_security_id)
            candles = equity_history.get(meta.symbol, [])
            if builder and candles:
                builder.seed_history(candles)
                seeded += 1
        logger.info("Hydrated candle history for %d equities (1min-agg)", seeded)
