import numpy as np

from ._scorer_constants import _ROC_SHORT, _ROC_MID, _ROC_LONG


def _momentum_score(ind: dict) -> tuple[float | None, dict]:
    rsi_val = ind.get("rsi_14")
    if rsi_val is None:
        return None, {}

    if 40 <= rsi_val <= 70:
        rsi_s = 60.0 + (rsi_val - 40) * (40.0 / 30.0)
    elif rsi_val > 70:
        rsi_s = max(20.0, 100.0 - (rsi_val - 70) * 2.5)
    elif rsi_val < 30:
        rsi_s = rsi_val * 1.0
    else:
        rsi_s = 30.0 + (rsi_val - 30) * 3.0

    hist_now = ind.get("macd_hist") or 0.0
    hist_std = ind.get("macd_hist_std") or 0.0
    macd_s = 50.0 if hist_std == 0 else float(np.clip(50.0 + (hist_now / hist_std) * 15.0, 0.0, 100.0))

    rocs = {}
    for period, key in [(_ROC_SHORT, "roc_5"), (_ROC_MID, "roc_20"), (_ROC_LONG, "roc_60")]:
        val = ind.get(key)
        if val is not None:
            rocs[period] = float(val)

    if not rocs:
        return None, {}

    positive_tfs = sum(1 for r in rocs.values() if r > 0)
    roc_alignment = (positive_tfs / 3) * 60.0
    roc_20_val = rocs.get(_ROC_MID, 0.0)
    roc_20_bonus = float(np.clip(roc_20_val * 1.5, 0.0, 40.0)) if roc_20_val > 0 else 0.0
    roc_s = roc_alignment + roc_20_bonus

    vol_r = ind.get("vol_ratio_20") or 0.0
    vol_s = float(np.clip(vol_r * 40.0, 0.0, 100.0))

    score = 0.35 * rsi_s + 0.30 * macd_s + 0.20 * roc_s + 0.15 * vol_s
    return round(float(score), 2), {}
