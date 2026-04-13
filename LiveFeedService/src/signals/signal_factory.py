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
    Entry is at the confirmation candle's close.
    Stop is just outside the climax extreme (below low for bullish, above high for bearish).
    """
    entry = candle.close

    if state.direction == Direction.BULLISH:
        stop       = round(state.climax.low  * 0.999, 2)  # just below climax low
        rng        = entry - stop
        t1         = round(entry + rng,       2)
        t2         = round(entry + rng * 2.5, 2)
        entry_low  = entry
        entry_high = round(entry * 1.002, 2)
        trend_desc = f"{state.downtrend_len} lower-lows"
        arrow      = "↑"
    else:  # BEARISH
        stop       = round(state.climax.high * 1.001, 2)  # just above climax high
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


def make_fade_alert(
    symbol:   str,
    candle:   Candle,
    spike:    SpikeState,
    phase:    SessionPhase,
    bias:     IndexBias,
) -> Signal:
    """WEAK_SHOCK: large price move with no volume backing — likely to fade."""
    return Signal(
        symbol        = symbol,
        signal_type   = SignalType.FADE_ALERT,
        direction     = _flip_direction(spike.direction),  # fade = trade against the move
        strength      = Strength.LOW,
        score         = round(spike.price_pct_move * 0.3, 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = candle.close,
        volume_ratio  = spike.volume_ratio,
        message       = (
            f"Fade alert | Move {spike.price_pct_move:.1f}% without volume "
            f"({spike.volume_ratio:.1f}×) — likely to reverse"
        ),
    )


def _flip_direction(d: Direction) -> Direction:
    if d == Direction.BULLISH:
        return Direction.BEARISH
    if d == Direction.BEARISH:
        return Direction.BULLISH
    return Direction.NEUTRAL


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


# ── ORB ───────────────────────────────────────────────────────────────────────

def make_orb_signal(
    symbol:      str,
    candle:      Candle,
    signal_type: SignalType,
    orb_high:    float,
    orb_low:     float,
    phase:       SessionPhase,
    bias:        IndexBias,
    vol_ratio:   float = 0.0,
) -> Signal:
    is_long  = signal_type == SignalType.ORB_BREAKOUT
    level    = orb_high if is_long else orb_low
    rng      = orb_high - orb_low
    direction = Direction.BULLISH if is_long else Direction.BEARISH

    if is_long:
        stop = orb_low
        t1   = round(candle.close + rng,       2)
        t2   = round(candle.close + rng * 2.5, 2)
    else:
        stop = orb_high
        t1   = round(candle.close - rng,       2)
        t2   = round(candle.close - rng * 2.5, 2)

    return Signal(
        symbol        = symbol,
        signal_type   = signal_type,
        direction     = direction,
        strength      = Strength.HIGH,
        score         = round(1.5 + vol_ratio * 0.2, 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = candle.close,
        entry_low     = round(candle.close * (0.999 if is_long else 0.997), 2),
        entry_high    = round(candle.close * (1.003 if is_long else 1.001), 2),
        stop          = round(stop, 2),
        target_1      = t1,
        target_2      = t2,
        volume_ratio  = round(vol_ratio, 2),
        message       = (
            f"{'ORB Breakout ↑' if is_long else 'ORB Breakdown ↓'} | "
            f"ORB {orb_low:.2f}–{orb_high:.2f} | "
            f"Vol {vol_ratio:.1f}×"
        ),
    )


# ── Range (5-candle rectangle) ────────────────────────────────────────────────

def make_range_signal(
    symbol:      str,
    candle:      Candle,
    signal_type: SignalType,
    range_high:  float,
    range_low:   float,
    vol_ratio:   float,
    phase:       SessionPhase,
    bias:        IndexBias,
) -> Signal:
    is_long   = signal_type == SignalType.RANGE_BREAKOUT
    direction = Direction.BULLISH if is_long else Direction.BEARISH
    rng       = range_high - range_low

    if is_long:
        stop = range_low
        t1   = round(candle.close + rng,       2)
        t2   = round(candle.close + rng * 2,   2)
    else:
        stop = range_high
        t1   = round(candle.close - rng,       2)
        t2   = round(candle.close - rng * 2,   2)

    return Signal(
        symbol        = symbol,
        signal_type   = signal_type,
        direction     = direction,
        strength      = Strength.MEDIUM,
        score         = round(1.0 + vol_ratio * 0.15, 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = candle.close,
        entry_low     = round(candle.close * (0.999 if is_long else 0.997), 2),
        entry_high    = round(candle.close * (1.003 if is_long else 1.001), 2),
        stop          = round(stop, 2),
        target_1      = t1,
        target_2      = t2,
        volume_ratio  = round(vol_ratio, 2),
        message       = (
            f"{'Range Breakout ↑' if is_long else 'Range Breakdown ↓'} | "
            f"Box {range_low:.2f}–{range_high:.2f} | "
            f"Vol {vol_ratio:.1f}×"
        ),
    )


# ── 52-week ───────────────────────────────────────────────────────────────────

def make_week52_signal(
    symbol:      str,
    candle:      Candle,
    signal_type: SignalType,
    level:       float,
    vol_ratio:   float,
    phase:       SessionPhase,
    bias:        IndexBias,
) -> Signal:
    is_long   = signal_type == SignalType.WEEK52_BREAKOUT
    direction = Direction.BULLISH if is_long else Direction.BEARISH
    margin    = candle.close * 0.01   # 1% buffer for stop

    return Signal(
        symbol        = symbol,
        signal_type   = signal_type,
        direction     = direction,
        strength      = Strength.HIGH,
        score         = round(2.5 + vol_ratio * 0.2, 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = candle.close,
        entry_low     = round(candle.close * (0.998 if is_long else 0.996), 2),
        entry_high    = round(candle.close * (1.004 if is_long else 1.002), 2),
        stop          = round((level - margin) if is_long else (level + margin), 2),
        target_1      = round(candle.close * (1.03 if is_long else 0.97), 2),
        target_2      = round(candle.close * (1.06 if is_long else 0.94), 2),
        volume_ratio  = round(vol_ratio, 2),
        message       = (
            f"{'52-week Breakout ↑' if is_long else '52-week Breakdown ↓'} | "
            f"Level {level:.2f} | Vol {vol_ratio:.1f}×"
        ),
    )


# ── PDH / PDL ─────────────────────────────────────────────────────────────────

def make_pdh_pdl_signal(
    symbol:      str,
    candle:      Candle,
    signal_type: SignalType,
    level:       float,
    vol_ratio:   float,
    phase:       SessionPhase,
    bias:        IndexBias,
) -> Signal:
    is_long   = signal_type == SignalType.PDH_BREAKOUT
    direction = Direction.BULLISH if is_long else Direction.BEARISH
    margin    = candle.close * 0.005

    return Signal(
        symbol        = symbol,
        signal_type   = signal_type,
        direction     = direction,
        strength      = Strength.MEDIUM,
        score         = round(1.2 + vol_ratio * 0.15, 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = candle.close,
        entry_low     = round(candle.close * (0.999 if is_long else 0.997), 2),
        entry_high    = round(candle.close * (1.003 if is_long else 1.001), 2),
        stop          = round((level - margin) if is_long else (level + margin), 2),
        target_1      = round(candle.close * (1.02 if is_long else 0.98), 2),
        target_2      = round(candle.close * (1.04 if is_long else 0.96), 2),
        volume_ratio  = round(vol_ratio, 2),
        message       = (
            f"{'PDH Breakout ↑' if is_long else 'PDL Breakdown ↓'} | "
            f"Prev day {'high' if is_long else 'low'} {level:.2f} | Vol {vol_ratio:.1f}×"
        ),
    )


# ── VWAP ──────────────────────────────────────────────────────────────────────

def make_vwap_signal(
    symbol:      str,
    candle:      Candle,
    signal_type: SignalType,
    vwap:        float,
    vol_ratio:   float,
    phase:       SessionPhase,
    bias:        IndexBias,
) -> Signal:
    is_long   = signal_type == SignalType.VWAP_BREAKOUT
    direction = Direction.BULLISH if is_long else Direction.BEARISH
    margin    = candle.close * 0.005

    return Signal(
        symbol        = symbol,
        signal_type   = signal_type,
        direction     = direction,
        strength      = Strength.MEDIUM,
        score         = round(1.0 + vol_ratio * 0.1, 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = candle.close,
        entry_low     = round(candle.close * (0.999 if is_long else 0.997), 2),
        entry_high    = round(candle.close * (1.003 if is_long else 1.001), 2),
        stop          = round((vwap - margin) if is_long else (vwap + margin), 2),
        target_1      = round(candle.close * (1.015 if is_long else 0.985), 2),
        target_2      = round(candle.close * (1.03  if is_long else 0.97),  2),
        volume_ratio  = round(vol_ratio, 2),
        message       = (
            f"{'VWAP Breakout ↑' if is_long else 'VWAP Breakdown ↓'} | "
            f"VWAP {vwap:.2f} | Vol {vol_ratio:.1f}×"
        ),
    )


# ── Camarilla ─────────────────────────────────────────────────────────────────

def make_camarilla_signal(
    symbol:      str,
    candle:      Candle,
    signal_type: SignalType,
    level:       float,
    vol_ratio:   float,
    phase:       SessionPhase,
    bias:        IndexBias,
) -> Signal:
    _REVERSAL = {SignalType.CAM_H3_REVERSAL, SignalType.CAM_L3_REVERSAL}
    is_long   = signal_type in {SignalType.CAM_H4_BREAKOUT, SignalType.CAM_L3_REVERSAL}
    direction = Direction.BULLISH if is_long else Direction.BEARISH
    is_reversal = signal_type in _REVERSAL
    margin    = candle.close * 0.005

    label_map = {
        SignalType.CAM_H3_REVERSAL:  "Cam H3 Reversal ↓",
        SignalType.CAM_H4_BREAKOUT:  "Cam H4 Breakout ↑",
        SignalType.CAM_L3_REVERSAL:  "Cam L3 Reversal ↑",
        SignalType.CAM_L4_BREAKDOWN: "Cam L4 Breakdown ↓",
    }

    return Signal(
        symbol        = symbol,
        signal_type   = signal_type,
        direction     = direction,
        strength      = Strength.LOW if is_reversal else Strength.MEDIUM,
        score         = round(0.8 + vol_ratio * 0.1, 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = candle.close,
        entry_low     = round(candle.close * (0.999 if is_long else 0.997), 2),
        entry_high    = round(candle.close * (1.003 if is_long else 1.001), 2),
        stop          = round((level - margin) if is_long else (level + margin), 2),
        target_1      = round(candle.close * (1.01 if is_long else 0.99), 2),
        target_2      = round(candle.close * (1.02 if is_long else 0.98), 2),
        volume_ratio  = round(vol_ratio, 2),
        message       = f"{label_map.get(signal_type, signal_type.value)} | Level {level:.2f}",
    )
