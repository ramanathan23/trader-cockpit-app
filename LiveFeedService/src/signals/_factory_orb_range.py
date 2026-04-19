from __future__ import annotations

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.index_bias import IndexBias
from ..domain.session_phase import SessionPhase
from ..domain.signal import Signal
from ..domain.signal_type import SignalType
from ..domain.strength import Strength


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
    is_long   = signal_type == SignalType.ORB_BREAKOUT
    rng       = orb_high - orb_low
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
        t1   = round(candle.close + rng,     2)
        t2   = round(candle.close + rng * 2, 2)
    else:
        stop = range_high
        t1   = round(candle.close - rng,     2)
        t2   = round(candle.close - rng * 2, 2)

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
