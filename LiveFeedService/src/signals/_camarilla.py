from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional, NamedTuple

from ..domain.candle import Candle
from ..domain.signal_type import SignalType


@dataclass(frozen=True)
class CamarillaLevels:
    h4: float
    h3: float
    l3: float
    l4: float


def compute_camarilla(
    prev_high:  float,
    prev_low:   float,
    prev_close: float,
) -> CamarillaLevels:
    rng = prev_high - prev_low
    return CamarillaLevels(
        h4 = round(prev_close + rng * 1.1 / 2, 2),
        h3 = round(prev_close + rng * 1.1 / 4, 2),
        l3 = round(prev_close - rng * 1.1 / 4, 2),
        l4 = round(prev_close - rng * 1.1 / 2, 2),
    )


class CamSignal(NamedTuple):
    signal_type: SignalType
    level:       float


def _is_pin_bar_bearish(candle: Candle, wick_ratio: float) -> bool:
    """Upper wick > wick_ratio × body AND bearish close."""
    body = abs(candle.close - candle.open)
    if body == 0:
        return False
    upper_wick = candle.high - max(candle.open, candle.close)
    return candle.close < candle.open and upper_wick >= wick_ratio * body


def _is_pin_bar_bullish(candle: Candle, wick_ratio: float) -> bool:
    """Lower wick > wick_ratio × body AND bullish close."""
    body = abs(candle.close - candle.open)
    if body == 0:
        return False
    lower_wick = min(candle.open, candle.close) - candle.low
    return candle.close > candle.open and lower_wick >= wick_ratio * body


def detect_camarilla(
    candle:           Candle,
    levels:           CamarillaLevels,
    prev_candle:      Optional[Candle],
    history:          list[Candle],
    prev_close:       float,
    *,
    vol_window:       int   = 20,
    min_vol_ratio:    float = 1.2,
    touch_pct:        float = 0.002,
    narrow_range_pct: float = 0.03,
    pin_wick_ratio:   float = 2.0,
) -> list[CamSignal]:
    """
    Narrow pivot range (H4-L4 / prev_close ≤ narrow_range_pct):
      H4 close-cross breakout / L4 close-cross breakdown with volume.

    Wide pivot range (H4-L4 / prev_close > narrow_range_pct):
      Bearish pin bar rejection at H4 or H3 / bullish pin bar bounce at L3 or L4.
    """
    window = history[-vol_window:] if len(history) >= vol_window else history
    vols   = [c.volume for c in window if c.volume > 0]
    if not vols:
        return []
    median_vol = statistics.median(vols)
    if median_vol == 0 or candle.volume < min_vol_ratio * median_vol:
        return []

    pivot_range_pct = (levels.h4 - levels.l4) / prev_close if prev_close else 0.0
    is_narrow = pivot_range_pct <= narrow_range_pct

    prev = prev_candle or (history[-1] if history else None)
    sigs: list[CamSignal] = []

    if is_narrow:
        if prev and prev.close <= levels.h4 and candle.close > levels.h4:
            sigs.append(CamSignal(SignalType.CAM_H4_BREAKOUT, levels.h4))
        if prev and prev.close >= levels.l4 and candle.close < levels.l4:
            sigs.append(CamSignal(SignalType.CAM_L4_BREAKDOWN, levels.l4))
    else:
        # Bearish pin at H4 takes priority over H3
        if candle.high >= levels.h4 * (1 - touch_pct) and _is_pin_bar_bearish(candle, pin_wick_ratio):
            sigs.append(CamSignal(SignalType.CAM_H4_REVERSAL, levels.h4))
        elif candle.high >= levels.h3 * (1 - touch_pct) and _is_pin_bar_bearish(candle, pin_wick_ratio):
            sigs.append(CamSignal(SignalType.CAM_H3_REVERSAL, levels.h3))

        # Bullish pin at L4 takes priority over L3
        if candle.low <= levels.l4 * (1 + touch_pct) and _is_pin_bar_bullish(candle, pin_wick_ratio):
            sigs.append(CamSignal(SignalType.CAM_L4_REVERSAL, levels.l4))
        elif candle.low <= levels.l3 * (1 + touch_pct) and _is_pin_bar_bullish(candle, pin_wick_ratio):
            sigs.append(CamSignal(SignalType.CAM_L3_REVERSAL, levels.l3))

    return sigs
