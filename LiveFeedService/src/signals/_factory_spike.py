from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.spike_state import SpikeState
from ..domain.strength import Strength


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


def make_fade_alert(
    symbol: str,
    candle: Candle,
    spike:  SpikeState,
    phase:  SessionPhase,
    bias:   IndexBias,
) -> Signal:
    """WEAK_SHOCK: large price move with no volume backing — likely to fade."""
    return Signal(
        symbol        = symbol,
        signal_type   = SignalType.FADE_ALERT,
        direction     = _flip_direction(spike.direction),
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
