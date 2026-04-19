from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.strength import Strength
from ._exhaustion_state import ExhaustionState


def make_exhaustion_reversal(
    symbol: str,
    candle: Candle,
    state:  ExhaustionState,
    phase:  SessionPhase,
    bias:   IndexBias,
) -> Signal:
    """
    Build Signal for confirmed exhaustion reversal.
    Entry at confirmation candle close; stop outside climax extreme.
    """
    entry = candle.close

    if state.direction == Direction.BULLISH:
        stop       = round(state.climax.low  * 0.999, 2)
        rng        = entry - stop
        t1         = round(entry + rng,       2)
        t2         = round(entry + rng * 2.5, 2)
        entry_low  = entry
        entry_high = round(entry * 1.002, 2)
        trend_desc = f"{state.downtrend_len} lower-lows"
        arrow      = "↑"
    else:
        stop       = round(state.climax.high * 1.001, 2)
        rng        = stop - entry
        t1         = round(entry - rng,       2)
        t2         = round(entry - rng * 2.5, 2)
        entry_low  = round(entry * 0.998, 2)
        entry_high = entry
        trend_desc = f"{state.downtrend_len} rising-highs"
        arrow      = "↓"

    return Signal(
        symbol        = symbol,
        signal_type   = SignalType.EXHAUSTION_REVERSAL,
        direction     = state.direction,
        strength      = Strength.HIGH if state.volume_ratio >= 8 else Strength.MEDIUM,
        score         = round(state.volume_ratio * 0.4, 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = entry,
        entry_low     = entry_low,
        entry_high    = entry_high,
        stop          = stop,
        target_1      = t1,
        target_2      = t2,
        volume_ratio  = state.volume_ratio,
        message       = (
            f"Exhaustion reversal {arrow} | {trend_desc} → "
            f"climax {state.volume_ratio:.1f}× vol → held | "
            f"Stop {stop:.2f}"
        ),
    )
