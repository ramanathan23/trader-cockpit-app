"""
OpenDriveDetector: evaluates the first N candles of the session for open drive.

Design
------
Stateless — takes a list of candles and the day_open price; returns a DriveState.
The caller (SignalEngine) maintains per-symbol state between calls.

Scoring (max 3 points per candle, DRIVE_CANDLES candles = 15 points total):
  +1  body_ratio > MIN_BODY_RATIO           (candle has conviction, not a doji)
  +1  price did NOT return through day_open (drive is intact)
  +1  close extends the move vs prior candle (momentum continuing)

Confidence = score / max_score (0.0–1.0)
  >= CONFIRMED_THRESH  → CONFIRMED
  >= WEAK_THRESH       → WEAK
  <  WEAK_THRESH       → NO_DRIVE (after all candles evaluated)

Invalidation (overrides scoring):
  Any candle's low (bullish) or high (bearish) trades through day_open → FAILED.
"""

from __future__ import annotations

from ..domain.models import Candle, Direction, DriveState, DriveStatus

# Default thresholds — overridable via SignalEngine config
DRIVE_CANDLES      = 5
MIN_BODY_RATIO     = 0.6
CONFIRMED_THRESH   = 0.70
WEAK_THRESH        = 0.50
_MAX_SCORE_PER_CANDLE = 3


def evaluate(
    candles:    list[Candle],
    day_open:   float,
    *,
    drive_candles:      int   = DRIVE_CANDLES,
    min_body_ratio:     float = MIN_BODY_RATIO,
    confirmed_thresh:   float = CONFIRMED_THRESH,
    weak_thresh:        float = WEAK_THRESH,
) -> DriveState:
    """
    Evaluate candles for an open drive pattern.

    Parameters
    ----------
    candles     : completed session candles so far (oldest first)
    day_open    : open price of the first complete session candle
    """
    if not candles:
        return DriveState(
            status            = DriveStatus.PENDING,
            direction         = Direction.NEUTRAL,
            confidence        = 0.0,
            day_open          = day_open,
            candles_evaluated = 0,
        )

    # Direction established by first candle.
    direction = candles[0].direction
    if direction == Direction.NEUTRAL:
        direction = Direction.BULLISH   # treat doji as bullish for scoring

    max_score = min(len(candles), drive_candles) * _MAX_SCORE_PER_CANDLE
    score     = 0
    window    = candles[:drive_candles]

    for idx, candle in enumerate(window):
        # 1. Invalidation check — price returned through day_open.
        if direction == Direction.BULLISH and candle.low < day_open:
            return DriveState(
                status            = DriveStatus.FAILED,
                direction         = direction,
                confidence        = 0.0,
                day_open          = day_open,
                candles_evaluated = idx + 1,
            )
        if direction == Direction.BEARISH and candle.high > day_open:
            return DriveState(
                status            = DriveStatus.FAILED,
                direction         = direction,
                confidence        = 0.0,
                day_open          = day_open,
                candles_evaluated = idx + 1,
            )

        # 2. Body conviction.
        if candle.body_ratio >= min_body_ratio:
            score += 1

        # 3. Price not returned to day_open.
        if direction == Direction.BULLISH and candle.low >= day_open:
            score += 1
        elif direction == Direction.BEARISH and candle.high <= day_open:
            score += 1

        # 4. Consecutive closes extending the move.
        if idx > 0:
            prev = window[idx - 1]
            if direction == Direction.BULLISH and candle.close > prev.close:
                score += 1
            elif direction == Direction.BEARISH and candle.close < prev.close:
                score += 1
        else:
            # First candle always scores the extension point.
            score += 1

    confidence = score / max_score if max_score > 0 else 0.0
    n          = len(window)

    if n < drive_candles:
        # Not enough candles yet to make a final call.
        status = DriveStatus.PENDING
    elif confidence >= confirmed_thresh:
        status = DriveStatus.CONFIRMED
    elif confidence >= weak_thresh:
        status = DriveStatus.WEAK
    else:
        status = DriveStatus.NO_DRIVE

    return DriveState(
        status            = status,
        direction         = direction,
        confidence        = round(confidence, 3),
        day_open          = day_open,
        candles_evaluated = n,
    )
