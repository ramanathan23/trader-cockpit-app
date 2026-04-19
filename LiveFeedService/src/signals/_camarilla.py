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


def detect_camarilla(
    candle:        Candle,
    levels:        CamarillaLevels,
    prev_candle:   Optional[Candle],
    history:       list[Candle],
    *,
    vol_window:    int   = 20,
    min_vol_ratio: float = 1.2,
    h3_touch_pct:  float = 0.002,
) -> list[CamSignal]:
    """
    Detect Camarilla pivot signals:
      H4 Cross, H3 Reversal, L4 Cross, L3 Reversal.
    """
    window = history[-vol_window:] if len(history) >= vol_window else history
    vols   = [c.volume for c in window if c.volume > 0]
    if not vols:
        return []
    median_vol = statistics.median(vols)
    if median_vol == 0 or candle.volume < min_vol_ratio * median_vol:
        return []

    prev = prev_candle or (history[-1] if history else None)
    sigs: list[CamSignal] = []

    if prev and prev.close <= levels.h4 and candle.close > levels.h4:
        sigs.append(CamSignal(SignalType.CAM_H4_BREAKOUT, levels.h4))
    elif candle.high >= levels.h3 * (1 - h3_touch_pct) and candle.close < levels.h3:
        sigs.append(CamSignal(SignalType.CAM_H3_REVERSAL, levels.h3))

    if prev and prev.close >= levels.l4 and candle.close < levels.l4:
        sigs.append(CamSignal(SignalType.CAM_L4_BREAKDOWN, levels.l4))
    elif candle.low <= levels.l3 * (1 + h3_touch_pct) and candle.close > levels.l3:
        sigs.append(CamSignal(SignalType.CAM_L3_REVERSAL, levels.l3))

    return sigs
