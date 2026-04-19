import numpy as np
import pandas as pd

from . import indicators


def _trend_score(
    df: pd.DataFrame,
    close: pd.Series,
) -> tuple[float, dict]:
    """ADX trending detection + EMA stack alignment."""
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    adx_series, plus_di, minus_di = indicators.adx(high, low, close, period=14)
    adx_val = adx_series.iloc[-1]
    plus_val = plus_di.iloc[-1]
    minus_val = minus_di.iloc[-1]

    if pd.isna(adx_val):
        adx_s = 30.0
        adx_val = 0.0
        plus_val = 0.0
        minus_val = 0.0
    else:
        if adx_val >= 25:
            adx_s = min(100.0, 50.0 + (adx_val - 25) * 2.0)
        else:
            adx_s = max(0.0, adx_val * 2.0)

    di_spread = float(plus_val - minus_val) if not pd.isna(plus_val) and not pd.isna(minus_val) else 0.0
    di_s = float(np.clip(50.0 + di_spread, 0.0, 100.0))

    ema_20 = close.ewm(span=20).mean().iloc[-1]
    ema_50 = close.ewm(span=50).mean().iloc[-1]
    ema_200 = close.ewm(span=200).mean().iloc[-1] if len(close) >= 200 else ema_50

    price = close.iloc[-1]
    ema_stack = 0.0
    if price > ema_20:
        ema_stack += 25.0
    if ema_20 > ema_50:
        ema_stack += 25.0
    if ema_50 > ema_200:
        ema_stack += 25.0
    if price > ema_200:
        ema_stack += 25.0

    roc_5 = indicators.rate_of_change(close, period=5).iloc[-1]
    weekly_bias = "NEUTRAL"
    if not pd.isna(roc_5):
        if roc_5 > 0.0:
            weekly_bias = "BULLISH"
        elif roc_5 < 0.0:
            weekly_bias = "BEARISH"
    weekly_bonus = 20.0 if weekly_bias == "BULLISH" else (-10.0 if weekly_bias == "BEARISH" else 0.0)

    score = 0.40 * adx_s + 0.20 * di_s + 0.30 * ema_stack + 0.10 * max(0, 50 + weekly_bonus)

    raw = {
        "adx_14": round(float(adx_val), 2),
        "plus_di": round(float(plus_val), 2),
        "minus_di": round(float(minus_val), 2),
        "weekly_bias": weekly_bias,
    }
    return round(float(score), 2), raw
