"""ExhaustionReversal: 3-part sequence (downtrend -> climax -> confirmation)."""
from __future__ import annotations

from statistics import mean
from typing import Optional

from ..domain.candle import Candle
from ..domain.direction import Direction
from ._exhaustion_state import (
    ExhaustionCandidate, ExhaustionState,
    DOWNTREND_CANDLES, VOL_RATIO_MIN, LOWER_LOWS_NEEDED, WINDOW,
)

__all__ = ["ExhaustionCandidate", "ExhaustionState", "detect_candidate", "confirm"]


def detect_candidate(
    candle:    Candle,
    history:   list[Candle],
    day_open:  Optional[float],
    *,
    vol_ratio_min:     float = VOL_RATIO_MIN,
    downtrend_candles: int   = DOWNTREND_CANDLES,
    lower_lows_needed: int   = LOWER_LOWS_NEEDED,
    window:            int   = WINDOW,
) -> Optional[ExhaustionCandidate]:
    """Evaluate whether candle is a volume-climax candidate at end of trend."""
    if len(history) < max(downtrend_candles, window):
        return None

    avg_vol      = mean(c.volume for c in history[-window:]) or 1
    volume_ratio = candle.volume / avg_vol
    if volume_ratio < vol_ratio_min:
        return None

    candle_range    = candle.high - candle.low or 0.001
    candle_upper_40 = candle.low + candle_range * 0.40
    candle_lower_60 = candle.low + candle_range * 0.60
    prior           = history[-downtrend_candles:]

    lower_low_count = sum(
        1 for i in range(1, len(prior)) if prior[i].low < prior[i - 1].low
    )
    if lower_low_count >= lower_lows_needed and candle.close >= candle_upper_40:
        return ExhaustionCandidate(
            climax=candle, direction=Direction.BULLISH,
            volume_ratio=round(volume_ratio, 2), downtrend_len=lower_low_count,
        )

    rising_high_count = sum(
        1 for i in range(1, len(prior)) if prior[i].high > prior[i - 1].high
    )
    if rising_high_count >= lower_lows_needed and candle.close <= candle_lower_60:
        return ExhaustionCandidate(
            climax=candle, direction=Direction.BEARISH,
            volume_ratio=round(volume_ratio, 2), downtrend_len=rising_high_count,
        )

    return None


def confirm(
    candle:    Candle,
    candidate: ExhaustionCandidate,
) -> Optional[ExhaustionState]:
    """Confirm reversal on the candle AFTER climax: low held + close recovered."""
    climax = candidate.climax

    if candidate.direction == Direction.BULLISH:
        if candle.low < climax.low:
            return None
        if candle.close <= climax.close:
            return None
    else:
        if candle.high > climax.high:
            return None
        if candle.close >= climax.close:
            return None

    return ExhaustionState(
        climax=climax, confirmation=candle,
        direction=candidate.direction,
        volume_ratio=candidate.volume_ratio,
        downtrend_len=candidate.downtrend_len,
    )
