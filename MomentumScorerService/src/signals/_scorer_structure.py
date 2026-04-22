import numpy as np
import pandas as pd

from . import indicators
from ._scorer_constants import _PROXIMITY_BARS


def _structure_score(
    df: pd.DataFrame,
    close: pd.Series,
    volume: pd.Series,
    *,
    nifty500_roc_60: float | None = None,
) -> tuple[float, dict]:
    """52-week proximity + relative strength + volume profile."""
    lookback = min(len(close), _PROXIMITY_BARS)

    if lookback >= 60:
        high_52w = close.iloc[-lookback:].max()
        proximity = float(close.iloc[-1] / high_52w) if high_52w > 0 else 0.5
    else:
        proximity = 0.5

    if proximity >= 0.90:
        prox_s = 90.0 + (proximity - 0.90) * 100.0
    elif proximity >= 0.75:
        prox_s = 50.0 + (proximity - 0.75) / 0.15 * 40.0
    elif proximity >= 0.60:
        prox_s = 20.0 + (proximity - 0.60) / 0.15 * 30.0
    else:
        prox_s = max(0.0, proximity * 33.0)

    roc_60 = indicators.rate_of_change(close, period=60).iloc[-1] if len(close) > 60 else None
    if roc_60 is not None and not pd.isna(roc_60) and nifty500_roc_60 is not None:
        excess = float(roc_60) - nifty500_roc_60
        rs_s = float(np.clip(50.0 + excess * 2.0, 0.0, 100.0))
        rs_val = round(excess, 4)
    else:
        rs_s = 50.0
        rs_val = 0.0

    vol_r = indicators.volume_ratio(volume, period=20)
    recent_vol_avg = vol_r.iloc[-5:].mean() if len(vol_r) >= 5 else vol_r.iloc[-1]
    if pd.isna(recent_vol_avg):
        vol_trend_s = 40.0
    else:
        vol_trend_s = float(np.clip(recent_vol_avg * 40.0, 0.0, 100.0))

    score = 0.20 * prox_s + 0.50 * rs_s + 0.30 * vol_trend_s

    raw = {
        "rs_vs_nifty": rs_val,
    }
    return round(float(score), 2), raw
