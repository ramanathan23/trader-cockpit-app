from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..domain.candle import Candle


@dataclass
class VwapState:
    cum_tp_vol: float = 0.0   # sum(typical_price × volume)
    cum_vol:    float = 0.0   # sum(volume)
    last_side:  int   = 0     # +1 above, -1 below, 0 unknown
    side_count: int   = 0     # consecutive candles on last_side (hysteresis)
    signalled:  int   = 0     # +1 bullish fired, -1 bearish, 0 none

    @property
    def vwap(self) -> Optional[float]:
        if self.cum_vol == 0:
            return None
        return self.cum_tp_vol / self.cum_vol


def update(state: VwapState, candle: Candle) -> VwapState:
    """Return a new VwapState with the candle incorporated."""
    tp             = (candle.high + candle.low + candle.close) / 3.0
    new_cum_tp_vol = state.cum_tp_vol + tp * candle.volume
    new_cum_vol    = state.cum_vol    + candle.volume
    if new_cum_vol == 0:
        return state

    vwap     = new_cum_tp_vol / new_cum_vol
    new_side = 1 if candle.close > vwap else (-1 if candle.close < vwap else state.last_side)
    new_count = state.side_count + 1 if new_side == state.last_side else 1

    return VwapState(
        cum_tp_vol = new_cum_tp_vol,
        cum_vol    = new_cum_vol,
        last_side  = new_side,
        side_count = new_count,
        signalled  = state.signalled,
    )
