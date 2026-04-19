from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.strength import Strength


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
    margin    = candle.close * 0.01

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
