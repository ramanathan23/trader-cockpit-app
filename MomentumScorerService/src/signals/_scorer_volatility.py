import pandas as pd

from . import indicators


def _volatility_score(
    df: pd.DataFrame,
    close: pd.Series,
) -> tuple[float, dict]:
    """BB squeeze + ATR contraction + NR7 detection. Higher = more compressed (coiled spring)."""
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    squeeze_series = indicators.bollinger_squeeze(high, low, close)
    is_squeeze = bool(squeeze_series.iloc[-1]) if not pd.isna(squeeze_series.iloc[-1]) else False
    sq_days = indicators.squeeze_days(squeeze_series) if is_squeeze else 0
    squeeze_s = min(100.0, 60.0 + sq_days * 5.0) if is_squeeze else 10.0

    atr_5_series = indicators.atr(high, low, close, period=5)
    atr_14_series = indicators.atr(high, low, close, period=14)
    atr_5_val = atr_5_series.iloc[-1]
    atr_14_val = atr_14_series.iloc[-1]

    if pd.isna(atr_5_val) or pd.isna(atr_14_val) or atr_14_val == 0:
        atr_ratio = 1.0
        atr_s = 30.0
    else:
        atr_ratio = float(atr_5_val / atr_14_val)
        if atr_ratio <= 0.6:
            atr_s = 100.0
        elif atr_ratio <= 0.75:
            atr_s = 70.0 + (0.75 - atr_ratio) / 0.15 * 30.0
        elif atr_ratio <= 1.0:
            atr_s = 30.0 + (1.0 - atr_ratio) / 0.25 * 40.0
        else:
            atr_s = max(0.0, 30.0 - (atr_ratio - 1.0) * 30.0)

    is_nr7 = indicators.narrowest_range(high, low, window=7)
    nr7_s = 80.0 if is_nr7 else 20.0

    bb_w = indicators.bollinger_width(close).iloc[-1]
    kc_w = indicators.keltner_width(high, low, close).iloc[-1]

    score = 0.45 * squeeze_s + 0.30 * atr_s + 0.25 * nr7_s

    raw = {
        "bb_squeeze": is_squeeze,
        "squeeze_days": sq_days,
        "nr7": is_nr7,
        "atr_ratio": round(atr_ratio, 4),
        "atr_5": round(float(atr_5_val), 4) if not pd.isna(atr_5_val) else None,
        "bb_width": round(float(bb_w), 6) if not pd.isna(bb_w) else None,
        "kc_width": round(float(kc_w), 6) if not pd.isna(kc_w) else None,
    }
    return round(float(score), 2), raw
