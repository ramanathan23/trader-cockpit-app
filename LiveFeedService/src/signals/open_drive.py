"""OpenDriveDetector: evaluate the first N session candles for open drive conviction.

Scoring details in _drive_scorer.py.
"""
from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.drive_state import DriveState
from ..domain.drive_status import DriveStatus
from ._drive_scorer import _score_candles, _MAX_SCORE_PER_CANDLE

DRIVE_CANDLES    = 5
MIN_BODY_RATIO   = 0.5
CONFIRMED_THRESH = 0.70
WEAK_THRESH      = 0.50


def evaluate(
    candles:   list[Candle],
    day_open:  float,
    *,
    drive_candles:    int   = DRIVE_CANDLES,
    min_body_ratio:   float = MIN_BODY_RATIO,
    confirmed_thresh: float = CONFIRMED_THRESH,
    weak_thresh:      float = WEAK_THRESH,
) -> DriveState:
    """Evaluate candles for an open drive pattern."""
    if not candles:
        return DriveState(
            status=DriveStatus.PENDING, direction=Direction.NEUTRAL,
            confidence=0.0, day_open=day_open, candles_evaluated=0,
        )

    direction = candles[0].direction
    if direction == Direction.NEUTRAL:
        return DriveState(
            status=DriveStatus.NO_DRIVE, direction=Direction.NEUTRAL,
            confidence=0.0, day_open=day_open, candles_evaluated=1,
        )

    window           = candles[:drive_candles]
    score, failed_at = _score_candles(window, direction, day_open, min_body_ratio)

    if failed_at is not None:
        return DriveState(
            status=DriveStatus.FAILED, direction=direction,
            confidence=0.0, day_open=day_open, candles_evaluated=failed_at + 1,
        )

    n          = len(window)
    max_score  = n * _MAX_SCORE_PER_CANDLE
    confidence = score / max_score if max_score > 0 else 0.0

    if n < drive_candles:
        status = DriveStatus.PENDING
    elif confidence >= confirmed_thresh:
        status = DriveStatus.CONFIRMED
    elif confidence >= weak_thresh:
        status = DriveStatus.WEAK
    else:
        status = DriveStatus.NO_DRIVE

    return DriveState(
        status=status, direction=direction,
        confidence=round(confidence, 3),
        day_open=day_open, candles_evaluated=n,
    )
