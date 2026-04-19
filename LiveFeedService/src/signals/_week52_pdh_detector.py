from __future__ import annotations

import statistics
from typing import Optional

from ..domain.candle import Candle
from ..domain.signal_type import SignalType


def detect_week52(
    candle:        Candle,
    week52_high:   float,
    week52_low:    float,
    history:       list[Candle],
    *,
    vol_window:    int   = 20,
    min_vol_ratio: float = 2.0,
) -> Optional[SignalType]:
    """
    Returns WEEK52_BREAKOUT/WEEK52_BREAKDOWN on double the median volume.
    Callers must enforce the once-per-session guard.
    """
    window = history[-vol_window:] if len(history) >= vol_window else history
    vols   = [c.volume for c in window if c.volume > 0]
    if not vols:
        return None
    median_vol = statistics.median(vols)
    if median_vol == 0 or candle.volume < min_vol_ratio * median_vol:
        return None

    if candle.close > week52_high:
        return SignalType.WEEK52_BREAKOUT
    if candle.close < week52_low:
        return SignalType.WEEK52_BREAKDOWN
    return None


def detect_pdh_pdl(
    candle:        Candle,
    prev_day_high: float,
    prev_day_low:  float,
    history:       list[Candle],
    *,
    vol_window:    int   = 20,
    min_vol_ratio: float = 1.3,
) -> Optional[SignalType]:
    """
    Returns PDH_BREAKOUT / PDL_BREAKDOWN on volume when candle crosses the
    previous day high or low for the first time.
    """
    window = history[-vol_window:] if len(history) >= vol_window else history
    vols   = [c.volume for c in window if c.volume > 0]
    if not vols:
        return None
    median_vol = statistics.median(vols)
    if median_vol == 0 or candle.volume < min_vol_ratio * median_vol:
        return None

    prev_candle = history[-1] if history else None
    if prev_candle is None:
        return None

    if prev_candle.close <= prev_day_high and candle.close > prev_day_high:
        return SignalType.PDH_BREAKOUT
    if prev_candle.close >= prev_day_low and candle.close < prev_day_low:
        return SignalType.PDL_BREAKDOWN
    return None
