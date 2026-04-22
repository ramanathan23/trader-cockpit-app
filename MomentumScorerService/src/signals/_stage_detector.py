import pandas as pd

_SMA_PERIOD = 150
_SLOPE_WINDOW = 20
_PRIOR_WINDOW = 50
_PRIOR_COMPARE = 30
_FLAT_THRESHOLD = 1.5  # % change over _SLOPE_WINDOW to be considered flat


def detect_stage(close: pd.Series) -> str:
    """
    Stan Weinstein stage detection via 150-day SMA slope + price position.

    Stage 2 — SMA rising,  price above SMA  (bull uptrend)
    Stage 4 — SMA falling, price below SMA  (bear downtrend)
    Stage 3 — SMA turning down or flat after rise, price above (topping / distribution)
    Stage 1 — SMA turning up  or flat after fall, price below (basing / accumulation)
    UNKNOWN — insufficient data

    Requires 200 bars minimum (150 SMA + 50 prior-trend lookback).
    """
    if len(close) < 200:
        return "UNKNOWN"

    sma = close.rolling(_SMA_PERIOD).mean()

    sma_now = float(sma.iloc[-1])
    sma_prev = float(sma.iloc[-(_SLOPE_WINDOW + 1)])
    if sma_prev <= 0:
        return "UNKNOWN"

    slope_pct = (sma_now / sma_prev - 1.0) * 100.0

    is_rising  = slope_pct >  _FLAT_THRESHOLD
    is_falling = slope_pct < -_FLAT_THRESHOLD
    is_flat    = not is_rising and not is_falling

    price_above = float(close.iloc[-1]) > sma_now

    # Clear directional stages
    if is_rising and price_above:
        return "STAGE_2"
    if is_falling and not price_above:
        return "STAGE_4"

    # Transition states — use price position to assign nearer stage
    if is_rising and not price_above:
        # SMA turned up but price still below — late Stage 1 / early Stage 2 entry
        return "STAGE_1"
    if is_falling and price_above:
        # SMA turned down but price still above — late Stage 3 / early Stage 4 entry
        return "STAGE_3"

    # Flat SMA — use prior trend to distinguish basing (S1) vs topping (S3)
    if is_flat:
        sma_prior_end   = float(sma.iloc[-(_PRIOR_COMPARE + 1)])
        sma_prior_start = float(sma.iloc[-(_PRIOR_WINDOW + 1)])
        if sma_prior_start <= 0:
            return "UNKNOWN"
        prior_slope = (sma_prior_end / sma_prior_start - 1.0) * 100.0
        if prior_slope > _FLAT_THRESHOLD:
            return "STAGE_3"
        if prior_slope < -_FLAT_THRESHOLD:
            return "STAGE_1"
        # Prior also flat — use price position as tiebreaker
        return "STAGE_2" if price_above else "STAGE_1"

    return "UNKNOWN"
