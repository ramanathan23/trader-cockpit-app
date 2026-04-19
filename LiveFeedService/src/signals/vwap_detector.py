"""VWAP detector: running VWAP with cross / breakout detection.

VwapState and update() live in _vwap_state.py.
"""
from __future__ import annotations

import statistics
from typing import Optional

from ..domain.candle import Candle
from ..domain.signal_type import SignalType
from ._vwap_state import VwapState, update

__all__ = ["VwapState", "update", "detect_cross"]


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
    Returns VWAP_BREAKOUT / VWAP_BREAKDOWN when a valid cross occurs, else None.

    state   : VwapState *before* incorporating this candle.
    history : Prior candles (not including `candle`).
    """
    vwap = state.vwap
    if vwap is None:
        return None

    new_side = 1 if candle.close > vwap else (-1 if candle.close < vwap else 0)
    if new_side == 0 or new_side == state.last_side:
        return None

    if state.side_count < hysteresis_min:
        return None

    window = history[-vol_window:] if len(history) >= vol_window else history
    if not window:
        return None
    vols = [c.volume for c in window if c.volume > 0]
    if not vols:
        return None
    median_vol = statistics.median(vols)
    if median_vol == 0 or candle.volume < min_vol_ratio * median_vol:
        return None

    if new_side == state.signalled:
        return None

    return SignalType.VWAP_BREAKOUT if new_side == 1 else SignalType.VWAP_BREAKDOWN
