"""
Level-based breakout / breakdown detectors.

Covers:
  - ORB  (Opening Range Breakout): close above/below the first-N-candle range.
  - 52-week  breakout / breakdown: close through 52-week high/low on 2× volume.
  - PDH / PDL: Previous Day High / Low breakout.
  - Camarilla pivots: H3/H4 (resistance) and L3/L4 (support).

All functions are pure: they receive pre-computed level values and return a
list of generated signal-type + metadata tuples (or None).  The signalling
cooldown / deduplication is handled in SignalEngine state, not here.

Camarilla formulas (classic)
-----------------------------
  Range = prev_high - prev_low
  H4 = prev_close + Range * 1.1 / 2
  H3 = prev_close + Range * 1.1 / 4
  L3 = prev_close - Range * 1.1 / 4
  L4 = prev_close - Range * 1.1 / 2
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional, NamedTuple

from ..domain.candle import Candle
from ..domain.signal_type import SignalType


# ── ORB ──────────────────────────────────────────────────────────────────────

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
    Returns ORB_BREAKOUT/ORB_BREAKDOWN when `candle` closes outside the ORB
    with volume confirmation.  Returns None otherwise.

    Callers must enforce the "once per session" guard.
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


# ── 52-week breakout ──────────────────────────────────────────────────────────

def detect_week52(
    candle:        Candle,
    week52_high:   float,
    week52_low:    float,
    history:       list[Candle],
    *,
    vol_window:    int   = 20,
    min_vol_ratio: float = 2.0,   # 52-week breakout requires heavier volume
) -> Optional[SignalType]:
    """
    Returns WEEK52_BREAKOUT/WEEK52_BREAKDOWN when candle closes through the
    52-week boundary on double the median volume.

    Callers must enforce the "once per session" guard.
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


# ── PDH / PDL ────────────────────────────────────────────────────────────────

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
    Returns PDH_BREAKOUT only when the candle crosses above previous day high
    on volume.

    Returns PDL_BREAKDOWN only when the candle crosses below previous day low
    on volume.
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


# ── Camarilla ────────────────────────────────────────────────────────────────

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


def detect_camarilla(
    candle:        Candle,
    levels:        CamarillaLevels,
    prev_candle:   Optional[Candle],
    history:       list[Candle],
    *,
    vol_window:    int   = 20,
    min_vol_ratio: float = 1.2,
    h3_touch_pct:  float = 0.002,   # H3/L3 rejection: candle must have wicked within 0.2% of level
) -> list[CamSignal]:
    """
    Detect Camarilla pivot signals:
      - H3 Reversal: touched/exceeded H3 but closed below it → fade short.
      - H4 Breakout: closed above H4 → momentum long.
      - L3 Reversal: touched/exceeded L3 but closed above it → fade long.
      - L4 Breakdown: closed below L4 → momentum short.
    """
    window = history[-vol_window:] if len(history) >= vol_window else history
    vols   = [c.volume for c in window if c.volume > 0]
    if not vols:
        return []
    median_vol = statistics.median(vols)
    if median_vol == 0 or candle.volume < min_vol_ratio * median_vol:
        return []

    sigs: list[CamSignal] = []

    # H4 full breakout: close above H4.
    if candle.close > levels.h4:
        sigs.append(CamSignal(SignalType.CAM_H4_BREAKOUT, levels.h4))

    # H3 rejection: high touched or exceeded H3 but closed below H3.
    elif candle.high >= levels.h3 * (1 - h3_touch_pct) and candle.close < levels.h3:
        sigs.append(CamSignal(SignalType.CAM_H3_REVERSAL, levels.h3))

    # L4 full breakdown: close below L4.
    if candle.close < levels.l4:
        sigs.append(CamSignal(SignalType.CAM_L4_BREAKDOWN, levels.l4))

    # L3 bounce: low touched or went below L3 but closed above L3.
    elif candle.low <= levels.l3 * (1 + h3_touch_pct) and candle.close > levels.l3:
        sigs.append(CamSignal(SignalType.CAM_L3_REVERSAL, levels.l3))

    return sigs
