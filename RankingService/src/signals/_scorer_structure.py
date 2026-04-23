import numpy as np


def _structure_score(ind: dict) -> tuple[float, dict]:
    price = ind.get("prev_day_close") or 0.0
    week52_high = ind.get("week52_high") or 0.0
    proximity = (price / week52_high) if week52_high > 0 else 0.5

    if proximity >= 0.90:
        prox_s = 90.0 + (proximity - 0.90) * 100.0
    elif proximity >= 0.75:
        prox_s = 50.0 + (proximity - 0.75) / 0.15 * 40.0
    elif proximity >= 0.60:
        prox_s = 20.0 + (proximity - 0.60) / 0.15 * 30.0
    else:
        prox_s = max(0.0, proximity * 33.0)

    rs_val = ind.get("rs_vs_nifty") or 0.0
    rs_s = float(np.clip(50.0 + rs_val * 2.0, 0.0, 100.0))

    vol_r = ind.get("vol_ratio_20") or 0.0
    vol_trend_s = float(np.clip(vol_r * 40.0, 0.0, 100.0))

    score = 0.20 * prox_s + 0.50 * rs_s + 0.30 * vol_trend_s
    return round(float(score), 2), {}
