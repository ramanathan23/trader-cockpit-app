import numpy as np
import pandas as pd

from . import indicators
from ._scorer_constants import _ROC_SHORT, _ROC_MID, _ROC_LONG


def _momentum_score(
    close: pd.Series,
    volume: pd.Series,
    *,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    vol_period: int = 20,
) -> tuple[float | None, dict]:
    """Returns (score, raw_values_dict) or (None, {}) if data insufficient."""
    rsi_val = indicators.rsi(close, period=rsi_period).iloc[-1]
    if pd.isna(rsi_val):
        return None, {}

    # RSI: favour 40–70 zone (momentum sweet spot), penalise extremes
    if 40 <= rsi_val <= 70:
        rsi_s = 60.0 + (rsi_val - 40) * (40.0 / 30.0)
    elif rsi_val > 70:
        rsi_s = max(20.0, 100.0 - (rsi_val - 70) * 2.5)
    elif rsi_val < 30:
        rsi_s = rsi_val * 1.0
    else:
        rsi_s = 30.0 + (rsi_val - 30) * 3.0

    _, _, histogram = indicators.macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    hist_now = histogram.iloc[-1]
    hist_std = histogram.std()
    if pd.isna(hist_now) or hist_std == 0 or pd.isna(hist_std):
        macd_s = 50.0
    else:
        macd_s = float(np.clip(50.0 + (hist_now / hist_std) * 15.0, 0.0, 100.0))

    rocs: dict[int, float] = {}
    for period in (_ROC_SHORT, _ROC_MID, _ROC_LONG):
        if len(close) > period:
            val = indicators.rate_of_change(close, period=period).iloc[-1]
            if not pd.isna(val):
                rocs[period] = float(val)

    if not rocs:
        return None, {}

    positive_tfs = sum(1 for r in rocs.values() if r > 0)
    roc_alignment = (positive_tfs / 3) * 60.0
    roc_20_bonus = float(np.clip(rocs.get(_ROC_MID, 0.0) * 1.5, 0.0, 40.0)) if rocs.get(_ROC_MID, 0) > 0 else 0.0
    roc_s = roc_alignment + roc_20_bonus

    vol_r = indicators.volume_ratio(volume, period=vol_period).iloc[-1]
    vol_s = 50.0 if pd.isna(vol_r) else float(np.clip(vol_r * 40.0, 0.0, 100.0))

    score = 0.35 * rsi_s + 0.30 * macd_s + 0.20 * roc_s + 0.15 * vol_s

    raw = {
        "rsi_14": round(float(rsi_val), 2),
        "macd_hist": round(float(hist_now) if not pd.isna(hist_now) else 0.0, 4),
        "roc_5": round(rocs.get(_ROC_SHORT, 0.0), 4),
        "roc_20": round(rocs.get(_ROC_MID, 0.0), 4),
        "roc_60": round(rocs.get(_ROC_LONG, 0.0), 4),
        "vol_ratio_20": round(float(vol_r) if not pd.isna(vol_r) else 0.0, 2),
    }
    return round(float(score), 2), raw
