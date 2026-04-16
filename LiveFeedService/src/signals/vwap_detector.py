"""
VWAP detector: running VWAP with cross / breakout detection.

VWAP is computed from session open using (typical_price × volume) accumulation.
A signal fires when price crosses VWAP AND:
  - The crossing candle has volume ≥ 1.3× 20-candle median volume.
  - Price has stayed on the *new* side for this candle (close-based).
  - Hysteresis: at least 2 consecutive candles on the previous side before
    the cross is considered valid (avoids chop around VWAP).

Usage
-----
    from .vwap_detector import VwapState, update, detect_cross

    state = VwapState()
    for candle in history:
        state = update(state, candle)

    signal_type = detect_cross(latest_candle, state, prior_history)
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.signal_type import SignalType


@dataclass
class VwapState:
    cum_tp_vol: float = 0.0   # sum(typical_price × volume)
    cum_vol:    float = 0.0   # sum(volume)
    last_side:  int   = 0     # +1 above, -1 below, 0 unknown
    side_count: int   = 0     # consecutive candles on last_side (hysteresis)
    signalled:  int   = 0     # +1 bullish breakout fired, -1 bearish, 0 none
                               # prevents re-firing until cross back occurs

    @property
    def vwap(self) -> Optional[float]:
        if self.cum_vol == 0:
            return None
        return self.cum_tp_vol / self.cum_vol


def update(state: VwapState, candle: Candle) -> VwapState:
    """Return a new VwapState with the candle incorporated."""
    tp = (candle.high + candle.low + candle.close) / 3.0
    new_cum_tp_vol = state.cum_tp_vol + tp * candle.volume
    new_cum_vol    = state.cum_vol    + candle.volume
    if new_cum_vol == 0:
        return state

    vwap     = new_cum_tp_vol / new_cum_vol
    new_side = 1 if candle.close > vwap else (-1 if candle.close < vwap else state.last_side)

    if new_side == state.last_side:
        new_count = state.side_count + 1
    else:
        new_count = 1

    return VwapState(
        cum_tp_vol = new_cum_tp_vol,
        cum_vol    = new_cum_vol,
        last_side  = new_side,
        side_count = new_count,
        signalled  = state.signalled,
    )


def detect_cross(
    candle:  Candle,
    state:   VwapState,
    history: list[Candle],
    *,
    vol_window:     int   = 20,
    min_vol_ratio:  float = 1.3,
    hysteresis_min: int   = 2,
) -> Optional[SignalType]:
    """
    Returns SignalType.VWAP_BREAKOUT / VWAP_BREAKDOWN when a valid cross occurs,
    or None if no signal.

    Parameters
    ----------
    candle         : The just-completed 3-min candle.
    state          : VwapState *before* incorporating this candle.
    history        : Prior candles (not including `candle`).
    vol_window     : Number of prior candles for median volume baseline.
    min_vol_ratio  : Minimum volume/median to confirm the cross.
    hysteresis_min : Candles the price must have been on the *previous* side.
    """
    vwap = state.vwap
    if vwap is None:
        return None

    # Determine if this candle crosses VWAP.
    new_side = 1 if candle.close > vwap else (-1 if candle.close < vwap else 0)
    if new_side == 0 or new_side == state.last_side:
        return None  # No cross — side unchanged.

    # Hysteresis guard: must have been on the other side for ≥ hysteresis_min candles.
    if state.side_count < hysteresis_min:
        return None

    # Volume confirmation.
    window = history[-vol_window:] if len(history) >= vol_window else history
    if not window:
        return None
    vols = [c.volume for c in window if c.volume > 0]
    if not vols:
        return None
    median_vol = statistics.median(vols)
    if median_vol == 0 or candle.volume < min_vol_ratio * median_vol:
        return None

    # Don't re-fire in the same direction until price crosses back.
    if new_side == state.signalled:
        return None

    return SignalType.VWAP_BREAKOUT if new_side == 1 else SignalType.VWAP_BREAKDOWN
