"""SpikeDetector: identifies price-volume anomalies in a completed candle.

Stateless — pure function: (candle, history, thresholds) -> SpikeState | None.
"""
from __future__ import annotations

from statistics import median

from ..domain.candle import Candle
from ..domain.direction import Direction
from ..domain.spike_state import SpikeState
from ..domain.spike_type import SpikeType
from ._spike_constants import WINDOW, VOL_SPIKE_RATIO, PRICE_SHOCK_PCT, MIN_BODY_RATIO, DRY_UP_RATIO


def evaluate(
    candle:  Candle,
    history: list[Candle],
    *,
    vol_spike_ratio: float = VOL_SPIKE_RATIO,
    price_shock_pct: float = PRICE_SHOCK_PCT,
    min_body_ratio:  float = MIN_BODY_RATIO,
    dry_up_ratio:    float = DRY_UP_RATIO,
    window:          int   = WINDOW,
) -> SpikeState | None:
    """Evaluate candle for price-volume anomalies relative to history.

    Returns None if fewer than 5 history candles (insufficient baseline).
    """
    if len(history) < 5:
        return None

    recent     = history[-window:]
    avg_volume = median(c.volume for c in recent) or 1

    prev_close = history[-1].close
    if prev_close == 0:
        return None

    volume_ratio   = candle.volume / avg_volume
    price_pct_move = abs(candle.close - prev_close) / prev_close * 100
    body_ratio     = candle.body_ratio

    vol_spike   = volume_ratio   >= vol_spike_ratio
    price_shock = price_pct_move >= price_shock_pct
    strong_body = body_ratio     >= min_body_ratio
    direction   = candle.direction

    if vol_spike and price_shock and strong_body:
        spike_type = SpikeType.BREAKOUT_SHOCK
    elif vol_spike and not price_shock:
        spike_type = SpikeType.ABSORPTION
        direction  = _flip(direction)
    elif price_shock and not vol_spike:
        spike_type = SpikeType.WEAK_SHOCK
    else:
        return None

    return SpikeState(
        spike_type     = spike_type,
        direction      = direction,
        volume_ratio   = round(volume_ratio, 2),
        price_pct_move = round(price_pct_move, 2),
        body_ratio     = round(body_ratio, 2),
    )


def is_volume_dry_up(candle: Candle, history: list[Candle], window: int = WINDOW) -> bool:
    """True when candle volume is DRY_UP_RATIO or less of rolling average."""
    if len(history) < 5:
        return False
    avg_volume = median(c.volume for c in history[-window:]) or 1
    return (candle.volume / avg_volume) <= DRY_UP_RATIO


def _flip(direction: Direction) -> Direction:
    if direction == Direction.BULLISH:
        return Direction.BEARISH
    if direction == Direction.BEARISH:
        return Direction.BULLISH
    return Direction.NEUTRAL
