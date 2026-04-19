from __future__ import annotations

import statistics
from typing import Optional

from ..domain.candle import Candle
from ..domain.signal_type import SignalType


def detect_orb(
    candle:        Candle,
    orb_high:      float,
    orb_low:       float,
    history:       list[Candle],
    *,
    vol_window:    int   = 20,
    min_vol_ratio: float = 1.3,
) -> Optional[SignalType]:
    """
    Returns ORB_BREAKOUT/ORB_BREAKDOWN when candle closes outside the ORB
    with volume confirmation. Callers must enforce the once-per-session guard.
    """
    window = history[-vol_window:] if len(history) >= vol_window else history
    vols   = [c.volume for c in window if c.volume > 0]
    if not vols:
        return None
    median_vol = statistics.median(vols)
    if median_vol == 0 or candle.volume < min_vol_ratio * median_vol:
        return None

    if candle.close > orb_high:
        return SignalType.ORB_BREAKOUT
    if candle.close < orb_low:
        return SignalType.ORB_BREAKDOWN
    return None
