import numpy as np


def _trend_score(ind: dict) -> tuple[float, dict]:
    adx_val = ind.get("adx_14") or 0.0
    plus_val = ind.get("plus_di") or 0.0
    minus_val = ind.get("minus_di") or 0.0

    adx_s = (min(100.0, 50.0 + (adx_val - 25) * 2.0) if adx_val >= 25 else max(0.0, adx_val * 2.0))
    di_s = float(np.clip(50.0 + (plus_val - minus_val), 0.0, 100.0))

    price = ind.get("prev_day_close") or 0.0
    ema_20 = ind.get("ema_20") or 0.0
    ema_50 = ind.get("ema_50") or 0.0
    ema_200 = ind.get("ema_200") or ema_50

    ema_stack = 0.0
    if price > ema_20:
        ema_stack += 25.0
    if ema_20 > ema_50:
        ema_stack += 25.0
    if ema_50 > ema_200:
        ema_stack += 25.0
    if price > ema_200:
        ema_stack += 25.0

    weekly_bias = ind.get("weekly_bias") or "NEUTRAL"
    weekly_bonus = 20.0 if weekly_bias == "BULLISH" else (-10.0 if weekly_bias == "BEARISH" else 0.0)

    score = 0.40 * adx_s + 0.20 * di_s + 0.30 * ema_stack + 0.10 * max(0, 50 + weekly_bonus)
    return round(float(score), 2), {}
