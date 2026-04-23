def _volatility_score(ind: dict) -> tuple[float, dict]:
    is_squeeze = bool(ind.get("bb_squeeze") or False)
    sq_days = int(ind.get("squeeze_days") or 0)
    squeeze_s = min(100.0, 60.0 + sq_days * 5.0) if is_squeeze else 10.0

    atr_ratio = ind.get("atr_ratio") or 1.0
    if atr_ratio <= 0.6:
        atr_s = 100.0
    elif atr_ratio <= 0.75:
        atr_s = 70.0 + (0.75 - atr_ratio) / 0.15 * 30.0
    elif atr_ratio <= 1.0:
        atr_s = 30.0 + (1.0 - atr_ratio) / 0.25 * 40.0
    else:
        atr_s = max(0.0, 30.0 - (atr_ratio - 1.0) * 30.0)

    nr7_s = 80.0 if ind.get("nr7") else 20.0

    score = 0.45 * squeeze_s + 0.30 * atr_s + 0.25 * nr7_s
    return round(float(score), 2), {}
