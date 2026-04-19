from __future__ import annotations

from dataclasses import dataclass

from ..domain.candle import Candle
from ..domain.direction import Direction

DOWNTREND_CANDLES  = 4
VOL_RATIO_MIN      = 2.5
LOWER_LOWS_NEEDED  = 2
WINDOW             = 20


@dataclass(frozen=True)
class ExhaustionCandidate:
    """Stored between candle N (climax) and candle N+1 (confirmation)."""
    climax:        Candle
    direction:     Direction
    volume_ratio:  float
    downtrend_len: int


@dataclass(frozen=True)
class ExhaustionState:
    """Returned when the full 3-part sequence is confirmed."""
    climax:        Candle
    confirmation:  Candle
    direction:     Direction
    volume_ratio:  float
    downtrend_len: int
