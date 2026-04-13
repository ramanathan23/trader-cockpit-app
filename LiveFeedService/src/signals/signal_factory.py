"""
Signal factory — pure functions that construct Signal objects.

Single responsibility: build Signal instances from trading engine data.
No state is stored here; all required data is passed as arguments,
making each constructor independently testable.
"""
from __future__ import annotations

from ..domain.models import (
    Candle, Direction, DriveState, IndexBias, Signal,
    SessionPhase, SignalType, SpikeState, Strength,
)
from ..signals import exhaustion_reversal as _er


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


def make_spike_signal(
    symbol:      str,
    candle:      Candle,
    spike:       SpikeState,
    signal_type: SignalType,
    strength:    Strength,
    phase:       SessionPhase,
    bias:        IndexBias,
) -> Signal:
    msg_map = {
        SignalType.SPIKE_BREAKOUT: (
            f"Breakout shock | Vol {spike.volume_ratio:.1f}× | "
            f"Move {spike.price_pct_move:.1f}%"
        ),
        SignalType.ABSORPTION: (
            f"Absorption at {candle.close:.2f} | Vol {spike.volume_ratio:.1f}× | "
            "Watch for reversal"
        ),
    }
    return Signal(
        symbol        = symbol,
        signal_type   = signal_type,
        direction     = spike.direction,
        strength      = strength,
        score         = spike.volume_ratio * 0.5,
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = candle.close,
        volume_ratio  = spike.volume_ratio,
        message       = msg_map.get(signal_type, ""),
    )


def make_exhaustion_reversal(
    symbol:    str,
    candle:    Candle,
    state:     _er.ExhaustionState,
    phase:     SessionPhase,
    bias:      IndexBias,
) -> Signal:
    """
    Build a Signal for a confirmed exhaustion reversal.
    Entry is at the confirmation candle's close; stop below the climax low.
    """
    entry  = candle.close
    stop   = round(state.climax.low * 0.999, 2)   # just below climax low
    rng    = entry - stop
    t1     = round(entry + rng,       2)
    t2     = round(entry + rng * 2.5, 2)

    return Signal(
        symbol        = symbol,
        signal_type   = SignalType.EXHAUSTION_REVERSAL,
        direction     = state.direction,
        strength      = Strength.HIGH if state.volume_ratio >= 8 else Strength.MEDIUM,
        score         = round(state.volume_ratio * 0.4, 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = entry,
        entry_low     = entry,
        entry_high    = round(entry * 1.002, 2),   # within 0.2% of confirmation close
        stop          = stop,
        target_1      = t1,
        target_2      = t2,
        volume_ratio  = state.volume_ratio,
        message       = (
            f"Exhaustion reversal | {state.downtrend_len} lower-lows → "
            f"climax {state.volume_ratio:.1f}× vol → held | "
            f"Stop {stop:.2f}"
        ),
    )


def composite_score(
    drive:    DriveState,
    candle:   Candle,
    orb_high: float | None,
    orb_low:  float | None,
    bias:     IndexBias,
) -> float:
    """Composite entry score: drive strength + index alignment + ORB breakout."""
    score = drive.confidence * 2                # 0–2: drive conviction
    if bias.majority() == drive.direction:
        score += 1.0                            # +1: index aligned
    if orb_high and orb_low:                    # +1: ORB breakout
        if drive.direction == Direction.BULLISH and candle.close > orb_high:
            score += 1.0
        elif drive.direction == Direction.BEARISH and candle.close < orb_low:
            score += 1.0
    return round(score, 2)
