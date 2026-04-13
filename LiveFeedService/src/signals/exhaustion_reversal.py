"""
ExhaustionReversal detector.

Identifies the 3-part sequence that produces high-conviction intraday reversals:

  [downtrend]  →  [volume climax candle]  →  [price holds / recovers]

The signal fires on the CONFIRMATION candle (N+1 after the climax) so all
three conditions are verified before emitting.  This is intentionally one
candle late — the extra 3 minutes eliminates most false triggers.

Stateless evaluate():
    Called each candle. The engine holds the pending candidate between calls.

Candidate detection (candle N):
    - Last `downtrend_candles` had monotonically falling lows (or majority bear bodies)
    - Current candle volume >= `vol_ratio_min` × 20-candle average (climax)
    - Price was already below day_open when climax fired

Confirmation (candle N+1):
    - Low of confirmation candle >= low of climax candle (price held)
    - Close of confirmation candle > close of climax candle (recovering)
    - The climax candle's close was in the upper half of its own range
      (buyers stepped in before the candle even closed)
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Optional

from ..domain.models import Candle, Direction

# ── Thresholds ────────────────────────────────────────────────────────────────
DOWNTREND_CANDLES  = 4      # candles that must show falling lows before climax
VOL_RATIO_MIN      = 6.0   # climax volume vs 20-candle average
LOWER_LOWS_NEEDED  = 3     # at least this many of the prior candles must print a lower low
WINDOW             = 20    # rolling window for avg volume baseline


@dataclass(frozen=True)
class ExhaustionCandidate:
    """Stored between candle N (climax) and candle N+1 (confirmation)."""
    climax:       Candle
    direction:    Direction   # BULLISH — we expect a bounce
    volume_ratio: float
    downtrend_len: int        # how many consecutive lower-low candles preceded this


@dataclass(frozen=True)
class ExhaustionState:
    """Returned when the full 3-part sequence is confirmed."""
    climax:       Candle
    confirmation: Candle
    direction:    Direction
    volume_ratio: float
    downtrend_len: int


# ── Public API ────────────────────────────────────────────────────────────────

def detect_candidate(
    candle:    Candle,
    history:   list[Candle],   # history NOT including current candle
    day_open:  Optional[float],
    *,
    vol_ratio_min:     float = VOL_RATIO_MIN,
    downtrend_candles: int   = DOWNTREND_CANDLES,
    lower_lows_needed: int   = LOWER_LOWS_NEEDED,
    window:            int   = WINDOW,
) -> Optional[ExhaustionCandidate]:
    """
    Evaluate whether *candle* is a volume-climax candidate at the end of a trend.

    Detects both directions:
      BULLISH — sell-off climax (price below day_open, falling lows, close in upper half)
      BEARISH — rally climax   (price above day_open, rising highs,  close in lower half)

    Returns an ExhaustionCandidate if all conditions pass, else None.
    """
    if len(history) < max(downtrend_candles, window):
        return None

    # ── Volume climax ─────────────────────────────────────────────────────────
    avg_vol      = mean(c.volume for c in history[-window:]) or 1
    volume_ratio = candle.volume / avg_vol
    if volume_ratio < vol_ratio_min:
        return None

    candle_mid = (candle.high + candle.low) / 2
    prior      = history[-downtrend_candles:]

    # ── Bullish exhaustion: sell-off climax → expect bounce ───────────────────
    if day_open and candle.close < day_open:
        lower_low_count = sum(
            1 for i in range(1, len(prior))
            if prior[i].low < prior[i - 1].low
        )
        if lower_low_count >= lower_lows_needed and candle.close >= candle_mid:
            # Close in upper half: buyers absorbed the sellers within this candle.
            return ExhaustionCandidate(
                climax        = candle,
                direction     = Direction.BULLISH,
                volume_ratio  = round(volume_ratio, 2),
                downtrend_len = lower_low_count,
            )

    # ── Bearish exhaustion: rally climax → expect selloff ─────────────────────
    if day_open and candle.close > day_open:
        rising_high_count = sum(
            1 for i in range(1, len(prior))
            if prior[i].high > prior[i - 1].high
        )
        if rising_high_count >= lower_lows_needed and candle.close < candle_mid:
            # Close in lower half: sellers stepped in before the candle even closed.
            return ExhaustionCandidate(
                climax        = candle,
                direction     = Direction.BEARISH,
                volume_ratio  = round(volume_ratio, 2),
                downtrend_len = rising_high_count,
            )

    return None


def confirm(
    candle:    Candle,
    candidate: ExhaustionCandidate,
) -> Optional[ExhaustionState]:
    """
    Confirm the exhaustion reversal on the candle AFTER the climax.

    Bullish: low held (no new low) AND close recovered above climax close.
    Bearish: high held (no new high) AND close dropped below climax close.
    """
    climax = candidate.climax

    if candidate.direction == Direction.BULLISH:
        if candle.low < climax.low:
            return None   # printed a new low — sellers still in control
        if candle.close <= climax.close:
            return None   # no recovery
    else:  # BEARISH
        if candle.high > climax.high:
            return None   # printed a new high — buyers still in control
        if candle.close >= climax.close:
            return None   # no decline

    return ExhaustionState(
        climax        = climax,
        confirmation  = candle,
        direction     = candidate.direction,
        volume_ratio  = candidate.volume_ratio,
        downtrend_len = candidate.downtrend_len,
    )
