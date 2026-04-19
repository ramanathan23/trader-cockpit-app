from __future__ import annotations

from datetime import datetime

from ..domain.candle import Candle


class _ActiveCandle:
    """Mutable accumulator for the candle currently being built."""

    __slots__ = ("boundary", "open", "high", "low", "close", "volume", "tick_count")

    def __init__(self, boundary: datetime, price: float, qty: int) -> None:
        self.boundary   = boundary
        self.open       = price
        self.high       = price
        self.low        = price
        self.close      = price
        self.volume     = qty
        self.tick_count = 1

    def update(self, price: float, qty: int) -> None:
        if price > self.high: self.high = price
        if price < self.low:  self.low  = price
        self.close      = price
        self.volume    += qty
        self.tick_count += 1

    def to_candle(self, symbol: str, is_index_future: bool) -> Candle:
        return Candle(
            symbol          = symbol,
            boundary        = self.boundary,
            open            = self.open,
            high            = self.high,
            low             = self.low,
            close           = self.close,
            volume          = self.volume,
            tick_count      = self.tick_count,
            is_index_future = is_index_future,
        )
