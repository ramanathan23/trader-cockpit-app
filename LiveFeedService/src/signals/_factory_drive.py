from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.drive_state import DriveState
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.strength import Strength


def make_drive_entry(
    symbol:   str,
    candle:   Candle,
    drive:    DriveState,
    score:    float,
    strength: Strength,
    phase:    SessionPhase,
    bias:     IndexBias,
) -> Signal:
    rng = abs(candle.close - drive.day_open)
    if drive.direction == Direction.BULLISH:
        entry_low  = drive.day_open + rng * 0.3
        entry_high = candle.close
        t1 = drive.day_open + rng * 2
        t2 = drive.day_open + rng * 3
    else:
        entry_low  = candle.close
        entry_high = drive.day_open - rng * 0.3
        t1 = drive.day_open - rng * 2
        t2 = drive.day_open - rng * 3

    return Signal(
        symbol           = symbol,
        signal_type      = SignalType.OPEN_DRIVE_ENTRY,
        direction        = drive.direction,
        strength         = strength,
        score            = score,
        session_phase    = phase,
        index_bias       = bias.majority(),
        price            = candle.close,
        entry_low        = round(entry_low,  2),
        entry_high       = round(entry_high, 2),
        stop             = round(drive.day_open, 2),
        target_1         = round(t1, 2),
        target_2         = round(t2, 2),
        drive_confidence = drive.confidence,
        message          = (
            f"Open Drive {drive.status.value} ({drive.confidence:.0%}) | "
            f"Index bias: {bias.majority().value}"
        ),
    )


def make_drive_failed(symbol: str, candle: Candle, phase: SessionPhase) -> Signal:
    return Signal(
        symbol        = symbol,
        signal_type   = SignalType.DRIVE_FAILED,
        direction     = Direction.NEUTRAL,
        strength      = Strength.LOW,
        score         = 0.0,
        session_phase = phase,
        price         = candle.close,
        message       = "Drive failed — price returned through day open. Stand down.",
    )


def make_trail_update(
    symbol:    str,
    candle:    Candle,
    new_stop:  float,
    phase:     SessionPhase,
    direction: Direction,
) -> Signal:
    return Signal(
        symbol        = symbol,
        signal_type   = SignalType.TRAIL_UPDATE,
        direction     = direction,
        strength      = Strength.LOW,
        score         = 0.0,
        session_phase = phase,
        price         = candle.close,
        trail_stop    = round(new_stop, 2),
        message       = f"Trail stop moved → {new_stop:.2f}",
    )


def make_exit(symbol: str, candle: Candle, phase: SessionPhase, *, reason: str) -> Signal:
    return Signal(
        symbol        = symbol,
        signal_type   = SignalType.EXIT,
        direction     = Direction.NEUTRAL,
        strength      = Strength.LOW,
        score         = 0.0,
        session_phase = phase,
        price         = candle.close,
        message       = f"Exit — {reason}",
    )
