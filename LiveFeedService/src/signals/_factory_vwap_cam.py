from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.strength import Strength


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


def make_camarilla_signal(
    symbol:      str,
    candle:      Candle,
    signal_type: SignalType,
    level:       float,
    vol_ratio:   float,
    phase:       SessionPhase,
    bias:        IndexBias,
) -> Signal:
    _REVERSAL   = {SignalType.CAM_H3_REVERSAL, SignalType.CAM_L3_REVERSAL}
    is_long     = signal_type in {SignalType.CAM_H4_BREAKOUT, SignalType.CAM_L3_REVERSAL}
    direction   = Direction.BULLISH if is_long else Direction.BEARISH
    is_reversal = signal_type in _REVERSAL
    margin      = candle.close * 0.005
    label_map   = {
        SignalType.CAM_H3_REVERSAL:  "⚡ Cam H3 Reversal ↓",
        SignalType.CAM_H4_BREAKOUT:  "⚡ Cam H4 Breakout ↑",
        SignalType.CAM_L3_REVERSAL:  "⚡ Cam L3 Reversal ↑",
        SignalType.CAM_L4_BREAKDOWN: "⚡ Cam L4 Breakdown ↓",
    }
    base_score    = 1.5 if not is_reversal else 1.0
    index_aligned = bias.majority() in (direction, Direction.NEUTRAL)

    return Signal(
        symbol        = symbol,
        signal_type   = signal_type,
        direction     = direction,
        strength      = Strength.MEDIUM if is_reversal else Strength.HIGH,
        score         = round(base_score + vol_ratio * 0.15 + (0.5 if index_aligned else 0.0), 2),
        session_phase = phase,
        index_bias    = bias.majority(),
        price         = candle.close,
        entry_low     = round(candle.close * (0.999 if is_long else 0.997), 2),
        entry_high    = round(candle.close * (1.003 if is_long else 1.001), 2),
        stop          = round((level - margin) if is_long else (level + margin), 2),
        target_1      = round(candle.close * (1.01 if is_long else 0.99), 2),
        target_2      = round(candle.close * (1.02 if is_long else 0.98), 2),
        volume_ratio  = round(vol_ratio, 2),
        message       = f"{label_map.get(signal_type, signal_type.value)} | Level {level:.2f} | Vol {vol_ratio:.1f}×",
    )
