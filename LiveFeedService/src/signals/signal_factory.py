"""Signal factory — constructs Signal objects from trading engine data.

All public names re-exported here for backward compatibility.
"""
from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.drive_state import DriveState
from ..domain.index_bias import IndexBias
from ..domain.signal_type import SignalType

from ._factory_drive import make_drive_entry, make_drive_failed, make_trail_update, make_exit
from ._factory_spike import make_spike_signal, make_fade_alert, _flip_direction
from ._factory_exhaustion import make_exhaustion_reversal
from ._factory_orb_range import make_orb_signal, make_range_signal
from ._factory_week52_pdh import make_week52_signal, make_pdh_pdl_signal
from ._factory_vwap_cam import make_vwap_signal, make_camarilla_signal
from ._factory_gap import make_gap_signal

__all__ = [
    "make_drive_entry", "make_drive_failed", "make_trail_update", "make_exit",
    "make_spike_signal", "make_fade_alert",
    "make_exhaustion_reversal",
    "make_orb_signal", "make_range_signal",
    "make_week52_signal", "make_pdh_pdl_signal",
    "make_vwap_signal", "make_camarilla_signal",
    "make_gap_signal",
    "composite_score",
]


def composite_score(
    drive:    DriveState,
    candle:   Candle,
    orb_high: float | None,
    orb_low:  float | None,
    bias:     IndexBias,
) -> float:
    """Composite entry score: drive strength + index alignment + ORB breakout."""
    score = drive.confidence * 2                    # 0-2: drive conviction
    if bias.majority() == drive.direction:
        score += 1.0                                # +1: index aligned
    if orb_high and orb_low:                        # +1: ORB breakout
        if drive.direction == Direction.BULLISH and candle.close > orb_high:
            score += 1.0
        elif drive.direction == Direction.BEARISH and candle.close < orb_low:
            score += 1.0
    return round(score, 2)
