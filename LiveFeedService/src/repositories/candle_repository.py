from __future__ import annotations

import asyncpg

from ..domain.candle import Candle
from ._candle_reads import list_from_1min_aggregated


class CandleRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_from_1min_aggregated(
        self, symbols: list[str], *, candle_min: int = 5, days_back: int = 2,
    ) -> dict[str, list[Candle]]:
        """Aggregate price_data_1min → N-min candles for equity warm-start."""
        return await list_from_1min_aggregated(
            self._pool, symbols, candle_min=candle_min, days_back=days_back,
        )
