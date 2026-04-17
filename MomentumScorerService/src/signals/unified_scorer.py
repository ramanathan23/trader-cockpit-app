"""
Unified balanced scorer — captures momentum, trend quality, volatility
compression, and structural context for all trading styles (option buying,
equity, positional, swing).

Component weights (each normalised to 0–100, equal 25% weight):
  Momentum     — RSI trend zone + MACD histogram acceleration + ROC alignment
  Trend        — ADX trending strength + EMA stack alignment + weekly bias
  Volatility   — BB squeeze active + ATR contraction ratio + NR7
  Structure    — 52-week proximity + relative strength vs benchmark + volume

All parameters are explicit keyword args so callers can inject Settings values.
"""

import logging

import numpy as np
import pandas as pd

from . import indicators
from ..domain.unified_score_breakdown import UnifiedScoreBreakdown

logger = logging.getLogger(__name__)

_ROC_SHORT = 5
_ROC_MID = 20
_ROC_LONG = 60
_PROXIMITY_BARS = 252


# ── Momentum component (0–100) ───────────────────────────────────────────────

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
        rsi_s = 60.0 + (rsi_val - 40) * (40.0 / 30.0)  # 60–100
    elif rsi_val > 70:
        rsi_s = max(20.0, 100.0 - (rsi_val - 70) * 2.5)
    elif rsi_val < 30:
        rsi_s = rsi_val * 1.0  # 0–30
    else:
        rsi_s = 30.0 + (rsi_val - 30) * 3.0  # 30–60

    # MACD histogram z-score
    _, _, histogram = indicators.macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    hist_now = histogram.iloc[-1]
    hist_std = histogram.std()
    if pd.isna(hist_now) or hist_std == 0 or pd.isna(hist_std):
        macd_s = 50.0
    else:
        macd_s = float(np.clip(50.0 + (hist_now / hist_std) * 15.0, 0.0, 100.0))

    # ROC multi-timeframe alignment
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

    # Volume confirmation
    vol_r = indicators.volume_ratio(volume, period=vol_period).iloc[-1]
    vol_s = 50.0 if pd.isna(vol_r) else float(np.clip(vol_r * 40.0, 0.0, 100.0))

    # Weighted: RSI 35%, MACD 30%, ROC 20%, Vol 15%
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


# ── Trend quality component (0–100) ──────────────────────────────────────────

def _trend_score(
    df: pd.DataFrame,
    close: pd.Series,
) -> tuple[float, dict]:
    """ADX trending detection + EMA stack alignment."""
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    # ADX
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
        # ADX > 25 = trending (good), ADX > 50 = very strong trend
        if adx_val >= 25:
            adx_s = min(100.0, 50.0 + (adx_val - 25) * 2.0)
        else:
            adx_s = max(0.0, adx_val * 2.0)  # 0–50 for ADX 0–25

    # DI spread: +DI > -DI for bullish, penalty if mixed
    di_spread = float(plus_val - minus_val) if not pd.isna(plus_val) and not pd.isna(minus_val) else 0.0
    di_s = float(np.clip(50.0 + di_spread, 0.0, 100.0))

    # EMA stack alignment: EMA20 > EMA50 > EMA200 = perfect bullish stack
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

    # Weekly bias from 5-day price action (0% threshold — any positive close = BULLISH)
    roc_5 = indicators.rate_of_change(close, period=5).iloc[-1]
    weekly_bias = "NEUTRAL"
    if not pd.isna(roc_5):
        if roc_5 > 0.0:
            weekly_bias = "BULLISH"
        elif roc_5 < 0.0:
            weekly_bias = "BEARISH"
    weekly_bonus = 20.0 if weekly_bias == "BULLISH" else (-10.0 if weekly_bias == "BEARISH" else 0.0)

    # Weighted: ADX 40%, DI spread 20%, EMA stack 30%, weekly 10%
    score = 0.40 * adx_s + 0.20 * di_s + 0.30 * ema_stack + 0.10 * max(0, 50 + weekly_bonus)

    raw = {
        "adx_14": round(float(adx_val), 2),
        "plus_di": round(float(plus_val), 2),
        "minus_di": round(float(minus_val), 2),
        "weekly_bias": weekly_bias,
    }
    return round(float(score), 2), raw


# ── Volatility compression component (0–100) ─────────────────────────────────

def _volatility_score(
    df: pd.DataFrame,
    close: pd.Series,
) -> tuple[float, dict]:
    """BB squeeze + ATR contraction + NR7 detection. Higher = more compressed (coiled spring)."""
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    # Bollinger Squeeze
    squeeze_series = indicators.bollinger_squeeze(high, low, close)
    is_squeeze = bool(squeeze_series.iloc[-1]) if not pd.isna(squeeze_series.iloc[-1]) else False
    sq_days = indicators.squeeze_days(squeeze_series) if is_squeeze else 0

    # Score: squeeze active = 60 base + 5 per day (max 100)
    squeeze_s = min(100.0, 60.0 + sq_days * 5.0) if is_squeeze else 10.0

    # ATR contraction: ATR(5) / ATR(14) < 0.75 means contracting volatility
    atr_5_series = indicators.atr(high, low, close, period=5)
    atr_14_series = indicators.atr(high, low, close, period=14)
    atr_5_val = atr_5_series.iloc[-1]
    atr_14_val = atr_14_series.iloc[-1]

    if pd.isna(atr_5_val) or pd.isna(atr_14_val) or atr_14_val == 0:
        atr_ratio = 1.0
        atr_s = 30.0
    else:
        atr_ratio = float(atr_5_val / atr_14_val)
        # Lower ratio = more contraction = higher score
        if atr_ratio <= 0.6:
            atr_s = 100.0
        elif atr_ratio <= 0.75:
            atr_s = 70.0 + (0.75 - atr_ratio) / 0.15 * 30.0
        elif atr_ratio <= 1.0:
            atr_s = 30.0 + (1.0 - atr_ratio) / 0.25 * 40.0
        else:
            atr_s = max(0.0, 30.0 - (atr_ratio - 1.0) * 30.0)

    # NR7: today's range is narrowest of last 7
    is_nr7 = indicators.narrowest_range(high, low, window=7)
    nr7_s = 80.0 if is_nr7 else 20.0

    # BB width (lower = tighter)
    bb_w = indicators.bollinger_width(close).iloc[-1]
    kc_w = indicators.keltner_width(high, low, close).iloc[-1]

    # Weighted: squeeze 45%, ATR contraction 30%, NR7 25%
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


# ── Structure component (0–100) ──────────────────────────────────────────────

def _structure_score(
    df: pd.DataFrame,
    close: pd.Series,
    volume: pd.Series,
    *,
    nifty500_roc_60: float | None = None,
) -> tuple[float, dict]:
    """52-week proximity + relative strength + volume profile."""
    lookback = min(len(close), _PROXIMITY_BARS)

    # 52-week proximity: closer to high = stronger structure
    if lookback >= 60:
        high_52w = close.iloc[-lookback:].max()
        proximity = float(close.iloc[-1] / high_52w) if high_52w > 0 else 0.5
    else:
        proximity = 0.5

    if proximity >= 0.90:
        prox_s = 90.0 + (proximity - 0.90) * 100.0  # 90–100
    elif proximity >= 0.75:
        prox_s = 50.0 + (proximity - 0.75) / 0.15 * 40.0  # 50–90
    elif proximity >= 0.60:
        prox_s = 20.0 + (proximity - 0.60) / 0.15 * 30.0  # 20–50
    else:
        prox_s = max(0.0, proximity * 33.0)

    # Relative strength vs NIFTY500
    roc_60 = indicators.rate_of_change(close, period=60).iloc[-1] if len(close) > 60 else None
    if roc_60 is not None and not pd.isna(roc_60) and nifty500_roc_60 is not None:
        excess = float(roc_60) - nifty500_roc_60
        rs_s = float(np.clip(50.0 + excess * 2.0, 0.0, 100.0))
        rs_val = round(excess, 4)
    else:
        rs_s = 50.0
        rs_val = 0.0

    # Volume trend: rising volume over last 5 days vs 20-day average
    vol_r = indicators.volume_ratio(volume, period=20)
    recent_vol_avg = vol_r.iloc[-5:].mean() if len(vol_r) >= 5 else vol_r.iloc[-1]
    if pd.isna(recent_vol_avg):
        vol_trend_s = 40.0
    else:
        vol_trend_s = float(np.clip(recent_vol_avg * 40.0, 0.0, 100.0))

    # Weighted: proximity 40%, RS 35%, volume trend 25%
    score = 0.40 * prox_s + 0.35 * rs_s + 0.25 * vol_trend_s

    raw = {
        "rs_vs_nifty": rs_val,
    }
    return round(float(score), 2), raw


# ── Public entry point ────────────────────────────────────────────────────────

def compute_unified_score(
    df: pd.DataFrame,
    *,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    vol_period: int = 20,
    min_bars: int = 30,
    nifty500_roc_60: float | None = None,
) -> UnifiedScoreBreakdown | None:
    """
    Compute unified balanced score for one symbol's OHLCV DataFrame.

    Returns None when data is insufficient.
    CPU-bound — call via asyncio.to_thread from async contexts.
    """
    if len(df) < min_bars:
        return None

    close = df["close"].astype(float)
    volume = df["volume"].astype(float)

    # 1. Momentum (25%)
    momentum, m_raw = _momentum_score(
        close, volume,
        rsi_period=rsi_period,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        vol_period=vol_period,
    )
    if momentum is None:
        return None

    # 2. Trend quality (25%)
    trend, t_raw = _trend_score(df, close)

    # 3. Volatility compression (25%)
    volatility, v_raw = _volatility_score(df, close)

    # 4. Structure (25%)
    structure, s_raw = _structure_score(df, close, volume, nifty500_roc_60=nifty500_roc_60)

    total = 0.25 * momentum + 0.25 * trend + 0.25 * volatility + 0.25 * structure

    return UnifiedScoreBreakdown(
        total_score=round(total, 2),
        momentum_score=momentum,
        trend_score=trend,
        volatility_score=volatility,
        structure_score=structure,
        # Raw indicator values for symbol_metrics update
        rsi_14=m_raw.get("rsi_14"),
        macd_hist=m_raw.get("macd_hist"),
        roc_5=m_raw.get("roc_5"),
        roc_20=m_raw.get("roc_20"),
        roc_60=m_raw.get("roc_60"),
        vol_ratio_20=m_raw.get("vol_ratio_20"),
        adx_14=t_raw.get("adx_14"),
        plus_di=t_raw.get("plus_di"),
        minus_di=t_raw.get("minus_di"),
        weekly_bias=t_raw.get("weekly_bias", "NEUTRAL"),
        bb_squeeze=v_raw.get("bb_squeeze", False),
        squeeze_days=v_raw.get("squeeze_days", 0),
        nr7=v_raw.get("nr7", False),
        atr_ratio=v_raw.get("atr_ratio"),
        atr_5=v_raw.get("atr_5"),
        bb_width=v_raw.get("bb_width"),
        kc_width=v_raw.get("kc_width"),
        rs_vs_nifty=s_raw.get("rs_vs_nifty"),
    )
