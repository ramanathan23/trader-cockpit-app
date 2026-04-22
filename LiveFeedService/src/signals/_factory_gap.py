from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.strength import Strength


def make_gap_signal(
    symbol:         str,
    candle:         Candle,
    signal_type:    SignalType,
    direction:      Direction,
    gap_pct:        float,
    phase:          SessionPhase,
    prev_day_close: float,
) -> Signal:
    is_up    = signal_type == SignalType.GAP_UP
    strength = Strength.HIGH if abs(gap_pct) >= 3.0 else Strength.MEDIUM
    return Signal(
        symbol        = symbol,
        signal_type   = signal_type,
        direction     = direction,
        strength      = strength,
        score         = round(min(abs(gap_pct) * 0.5, 5.0), 2),
        session_phase = phase,
        index_bias    = Direction.NEUTRAL,
        price         = candle.open,
        message       = (
            f"{'Gap Up ↑' if is_up else 'Gap Down ↓'} | "
            f"{'+' if gap_pct > 0 else ''}{gap_pct:.2f}% from prev close {prev_day_close:.2f}"
        ),
    )
