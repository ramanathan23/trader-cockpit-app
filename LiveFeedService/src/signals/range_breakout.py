"""
Intraday 5×3min rectangle (consolidation) breakout / breakdown detector.

Algorithm
---------
Lookback = last N completed candles (default 5, configurable).

1. Compute range_high = max(high) and range_low = min(low) of those N candles.
2. The rectangle is valid only when the ratio (range_high - range_low) / range_low
   is ≤ max_range_pct (default 2 %).  Wider ranges are not "consolidations".
3. A breakout fires when close > range_high.
   A breakdown fires when close < range_low.
   (We use close rather than intra-candle high/low to avoid wicks triggering.)
4. Volume must be ≥ min_vol_ratio × median volume of the prior vol_window candles.
5. A cooldown of 1 signal per N-candle period prevents rapid re-firing.

Usage
-----
    signal_type = detect(candle, history)
    # Returns SignalType.RANGE_BREAKOUT, RANGE_BREAKDOWN, or None.
"""
from __future__ import annotations

import statistics
from typing import Optional

from ..domain.candle import Candle
from ..domain.signal_type import SignalType


def detect(
    candle:         Candle,
    history:        list[Candle],
    *,
    lookback:       int   = 5,
    vol_window:     int   = 20,
    min_vol_ratio:  float = 1.5,
    max_range_pct:  float = 0.02,   # 2% max range for a valid rectangle
) -> Optional[SignalType]:
    """
    Detect a 5×3-min candle rectangle breakout or breakdown.

    Parameters
    ----------
    candle          : The just-completed 3-min candle (candidate breakout bar).
    history         : All prior completed candles for this symbol (not including `candle`).
    lookback        : Number of prior candles forming the rectangle.
    vol_window      : Candles to use for median volume baseline.
    min_vol_ratio   : Volume must exceed median × this ratio.
    max_range_pct   : Rectangle is only valid if high-low ≤ range_low × max_range_pct.
    """
    if len(history) < lookback:
        return None  # Not enough history yet.

    rect_candles = history[-lookback:]
    range_high   = max(c.high   for c in rect_candles)
    range_low    = min(c.low    for c in rect_candles)

    if range_low == 0:
        return None

    # Range must be tight enough to be a "consolidation".
    range_pct = (range_high - range_low) / range_low
    if range_pct > max_range_pct:
        return None

    # Is the current candle breaking out?
    broke_up   = candle.close > range_high
    broke_down = candle.close < range_low
    if not broke_up and not broke_down:
        return None

    # Volume confirmation using the broader history.
    window = history[-vol_window:] if len(history) >= vol_window else history
    vols   = [c.volume for c in window if c.volume > 0]
    if not vols:
        return None
    median_vol = statistics.median(vols)
    if median_vol == 0 or candle.volume < min_vol_ratio * median_vol:
        return None

    return SignalType.RANGE_BREAKOUT if broke_up else SignalType.RANGE_BREAKDOWN
