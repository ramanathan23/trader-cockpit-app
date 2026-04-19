from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction

_MAX_SCORE_PER_CANDLE = 4


def _score_candles(
    window:         list[Candle],
    direction:      Direction,
    day_open:       float,
    min_body_ratio: float,
) -> tuple[int, int | None]:
    """
    Score the drive window candles.

    Returns (score, failed_at_idx) — failed_at_idx is set if a close returned
    through day_open (invalidation), otherwise None.
    """
    score = 0
    for idx, candle in enumerate(window):
        if direction == Direction.BULLISH and candle.close < day_open:
            return score, idx
        if direction == Direction.BEARISH and candle.close > day_open:
            return score, idx

        if candle.body_ratio >= min_body_ratio:
            score += 1

        if direction == Direction.BULLISH and candle.close >= day_open:
            score += 1
        elif direction == Direction.BEARISH and candle.close <= day_open:
            score += 1

        if idx > 0:
            prev = window[idx - 1]
            if direction == Direction.BULLISH and candle.close > prev.close:
                score += 1
            elif direction == Direction.BEARISH and candle.close < prev.close:
                score += 1
        else:
            score += 1  # first candle always scores the extension point

        if idx > 0:
            prev = window[idx - 1]
            if candle.volume >= prev.volume:
                score += 1
        else:
            score += 1  # first candle: give the point unconditionally

    return score, None
