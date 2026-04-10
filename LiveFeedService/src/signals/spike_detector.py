"""
SpikeDetector: identifies price-volume anomalies in a completed candle.

Three signal types (see domain/models.py SpikeType):
  BREAKOUT_SHOCK — volume spike AND large directional price move
                   → trade WITH the direction on the next pullback
  ABSORPTION     — volume spike but flat price move
                   → large player absorbing supply/demand; watch for reversal
  WEAK_SHOCK     — large price move but NO volume backing
                   → likely to fade; low conviction

Baselines are computed from a rolling window of prior candles.
Volume dry-up (opposite of spike) is also detected and attached to SpikeState
as a flag for the caller to use in setup detection.

Stateless — pure function: (candle, history, thresholds) → SpikeState | None.
"""

from __future__ import annotations

from statistics import mean

from ..domain.models import Candle, Direction, SpikeState, SpikeType, SessionPhase

# ── Defaults ───────────────────────────────────────────────────────────────────
WINDOW           = 20      # rolling candle window for baselines
VOL_SPIKE_RATIO  = 3.0    # volume / avg_volume >= this → spike
PRICE_SHOCK_PCT  = 1.5    # |% change vs prev close| >= this → shock
MIN_BODY_RATIO   = 0.6    # body / range for directional conviction
DRY_UP_RATIO     = 0.2    # volume / avg_volume <= this → dry-up (coiling)


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
    """
    Evaluate *candle* for price-volume anomalies relative to *history*.

    Returns None if there are fewer than 5 history candles (insufficient baseline).
    """
    if len(history) < 5:
        return None

    # ── Baselines ──────────────────────────────────────────────────────────────
    recent = history[-window:]
    avg_volume = mean(c.volume for c in recent) or 1  # guard div/0

    prev_close = history[-1].close
    if prev_close == 0:
        return None

    # ── Current candle metrics ─────────────────────────────────────────────────
    volume_ratio   = candle.volume / avg_volume
    price_pct_move = abs(candle.close - prev_close) / prev_close * 100
    body_ratio     = candle.body_ratio

    # ── Classification ─────────────────────────────────────────────────────────
    vol_spike   = volume_ratio   >= vol_spike_ratio
    price_shock = price_pct_move >= price_shock_pct
    strong_body = body_ratio     >= min_body_ratio
    direction   = candle.direction

    if vol_spike and price_shock and strong_body:
        spike_type = SpikeType.BREAKOUT_SHOCK

    elif vol_spike and not price_shock:
        # High volume but price barely moved → someone absorbing.
        # The reversal direction is OPPOSITE to the candle's movement.
        spike_type = SpikeType.ABSORPTION
        # Flip direction for absorption: if price tried to go up but was absorbed,
        # the absorber is bearish (and vice versa).
        direction = _flip(direction)

    elif price_shock and not vol_spike:
        spike_type = SpikeType.WEAK_SHOCK

    else:
        return None   # nothing notable

    return SpikeState(
        spike_type     = spike_type,
        direction      = direction,
        volume_ratio   = round(volume_ratio, 2),
        price_pct_move = round(price_pct_move, 2),
        body_ratio     = round(body_ratio, 2),
    )


def is_volume_dry_up(candle: Candle, history: list[Candle], window: int = WINDOW) -> bool:
    """
    True when the candle's volume is DRY_UP_RATIO or less of the rolling average.

    Used to detect coiling / compression setups before a potential breakout.
    """
    if len(history) < 5:
        return False
    recent     = history[-window:]
    avg_volume = mean(c.volume for c in recent) or 1
    return (candle.volume / avg_volume) <= DRY_UP_RATIO


def _flip(direction: Direction) -> Direction:
    if direction == Direction.BULLISH:
        return Direction.BEARISH
    if direction == Direction.BEARISH:
        return Direction.BULLISH
    return Direction.NEUTRAL
