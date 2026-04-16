from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .direction import Direction


@dataclass(frozen=True)
class Candle:
    """Completed 3-minute OHLCV candle for a single instrument."""
    symbol:          str
    boundary:        datetime
    open:            float
    high:            float
    low:             float
    close:           float
    volume:          int
    tick_count:      int
    is_index_future: bool = False

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return self.high - self.low or 0.001

    @property
    def body_ratio(self) -> float:
        return self.body / self.range

    @property
    def direction(self) -> Direction:
        if self.close > self.open:
            return Direction.BULLISH
        if self.close < self.open:
            return Direction.BEARISH
        return Direction.NEUTRAL
