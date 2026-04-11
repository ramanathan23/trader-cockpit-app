"""
Pure momentum score computation — no I/O, no side effects.

Score components (each normalised to 0–100):
  RSI          weight_rsi  — momentum strength; penalises extremes (>80 overbought)
  MACD         weight_macd — trend acceleration; histogram z-score mapped to 0–100
  ROC          weight_roc  — multi-timeframe momentum (5d/20d/60d) + consistency
  Volume ratio weight_vol  — volume confirms the move

Quality multipliers applied after component scoring:
  Trend context     — long-term 60-bar ROC < -5% → downtrend penalty
  ATR% volatility   — excessive daily swings → choppy-stock penalty
  52-week proximity — far below 52-week high → structural weakness penalty
  Relative strength — stock ROC vs NIFTY500 60-bar ROC; underperformance penalised

All parameters are explicit keyword args so callers can inject Settings values
without this module carrying any config dependency.
"""

import logging

import numpy as np
import pandas as pd

from . import indicators
from ..domain.models import ScoreBreakdown

logger = logging.getLogger(__name__)

# Fixed ROC timeframes — weekly / monthly / quarterly.  Not configurable because
# these periods have fundamental meaning; arbitrary tuning would overfit.
_ROC_SHORT        = 5
_ROC_MID          = 20
_ROC_LONG         = 60
_CONSISTENCY_BARS = 20    # look-back for up-day consistency ratio
_PROXIMITY_BARS   = 252   # trading days in one year for 52-week high


# ── Component scorers (each returns 0–100) ────────────────────────────────────

def _rsi_score(close: pd.Series, period: int) -> float | None:
    val = indicators.rsi(close, period=period).iloc[-1]
    if pd.isna(val):
        return None
    if val > 80:
        return max(0.0, 100.0 - (val - 80) * 2)   # penalise overbought
    if val < 20:
        return val * 1.5                            # penalise oversold
    return float(val)


def _macd_score(close: pd.Series, fast: int, slow: int, signal: int) -> float:
    _, _, histogram = indicators.macd(close, fast=fast, slow=slow, signal=signal)
    hist_now = histogram.iloc[-1]
    hist_std = histogram.std()
    if pd.isna(hist_now) or hist_std == 0 or pd.isna(hist_std):
        return 50.0
    return float(np.clip(50.0 + (hist_now / hist_std) * 15.0, 0.0, 100.0))


def _roc_score(close: pd.Series) -> tuple[float | None, dict[int, float]]:
    """
    Multi-timeframe ROC score + alignment.

    Returns (score, rocs_dict).  Score is None when there is insufficient data.
    rocs_dict is passed to quality multipliers so they can reuse the computation.
    """
    rocs: dict[int, float] = {}
    for period in (_ROC_SHORT, _ROC_MID, _ROC_LONG):
        if len(close) > period:
            val = indicators.rate_of_change(close, period=period).iloc[-1]
            if not pd.isna(val):
                rocs[period] = float(val)

    if not rocs:
        return None, {}

    positive_tfs    = sum(1 for r in rocs.values() if r > 0)
    alignment       = (positive_tfs / 3) * 70.0        # max 70 pts from alignment

    roc_20          = rocs.get(_ROC_MID, 0.0)
    magnitude_bonus = float(np.clip(roc_20 * 1.5, 0.0, 30.0)) if roc_20 > 0 else 0.0

    up_days         = int((close.diff() > 0).tail(_CONSISTENCY_BARS).sum())
    consistency     = up_days / _CONSISTENCY_BARS       # fraction of up-close bars
    score           = (alignment + magnitude_bonus) * (0.6 + 0.4 * consistency)
    return float(score), rocs


def _volume_score(volume: pd.Series, period: int) -> float:
    vol_r = indicators.volume_ratio(volume, period=period).iloc[-1]
    return 50.0 if pd.isna(vol_r) else float(np.clip(vol_r * 50.0, 0.0, 100.0))


# ── Quality multipliers (each returns 0.4–1.0) ────────────────────────────────

def _trend_mult(close: pd.Series, trend_lookback: int) -> float:
    if len(close) < trend_lookback:
        return 1.0
    roc = indicators.rate_of_change(close, period=trend_lookback).iloc[-1]
    if pd.isna(roc) or roc >= -5.0:
        return 1.0
    mult = max(0.4, 1.0 + (roc + 5.0) / 35.0)
    logger.debug("Trend penalty: %.1f%% long ROC → mult=%.2f", roc, mult)
    return mult


def _atr_mult(df: pd.DataFrame, close: pd.Series, atr_period: int, atr_pct_max: float) -> float:
    if not {"high", "low"}.issubset(df.columns):
        return 1.0
    atr_val = indicators.atr(
        df["high"].astype(float), df["low"].astype(float), close, period=atr_period
    ).iloc[-1]
    if pd.isna(atr_val) or close.iloc[-1] == 0:
        return 1.0
    atr_pct = atr_val / close.iloc[-1] * 100.0
    if atr_pct <= atr_pct_max:
        return 1.0
    mult = max(0.5, atr_pct_max / atr_pct)
    logger.debug("ATR penalty: ATR=%.1f%% → mult=%.2f", atr_pct, mult)
    return mult


def _proximity_mult(close: pd.Series) -> float:
    lookback = min(len(close), _PROXIMITY_BARS)
    if lookback < 60:
        return 1.0
    high_52w  = close.iloc[-lookback:].max()
    proximity = close.iloc[-1] / high_52w
    if proximity < 0.60:
        mult = max(0.70, proximity)
    elif proximity < 0.75:
        mult = 0.85
    else:
        mult = 1.0
    logger.debug("52w proximity: %.1f%% of high → mult=%.2f", proximity * 100, mult)
    return mult


def _rs_mult(stock_roc_60: float | None, nifty500_roc_60: float | None) -> float:
    if nifty500_roc_60 is None or stock_roc_60 is None:
        return 1.0
    excess = stock_roc_60 - nifty500_roc_60
    mult   = float(np.clip(1.0 + excess / 50.0, 0.4, 1.0))
    logger.debug("RS vs NIFTY500: stock=%.1f%% index=%.1f%% excess=%.1f%% → mult=%.2f",
                 stock_roc_60, nifty500_roc_60, excess, mult)
    return mult


# ── Public entry point ────────────────────────────────────────────────────────

def compute_score(
    df: pd.DataFrame,
    *,
    rsi_period:      int   = 14,
    macd_fast:       int   = 12,
    macd_slow:       int   = 26,
    macd_signal:     int   = 9,
    roc_period:      int   = 10,    # kept for API compat; internal uses fixed periods
    vol_period:      int   = 20,
    min_bars:        int   = 30,
    trend_lookback:  int   = 60,
    atr_period:      int   = 14,
    atr_pct_max:     float = 5.0,
    nifty500_roc_60: float | None = None,
    weights: tuple[float, float, float, float] = (0.30, 0.30, 0.25, 0.15),
) -> ScoreBreakdown | None:
    """
    Compute composite momentum score for one symbol's OHLCV DataFrame.

    Returns None when data is insufficient or any required indicator is NaN.
    CPU-bound — call via asyncio.to_thread from async contexts.
    """
    if len(df) < min_bars:
        return None

    close  = df["close"].astype(float)
    volume = df["volume"].astype(float)

    rsi_s = _rsi_score(close, rsi_period)
    if rsi_s is None:
        return None

    macd_s         = _macd_score(close, macd_fast, macd_slow, macd_signal)
    roc_s, rocs    = _roc_score(close)
    if roc_s is None:
        return None

    vol_s = _volume_score(volume, vol_period)

    w_rsi, w_macd, w_roc, w_vol = weights
    composite = w_rsi * rsi_s + w_macd * macd_s + w_roc * roc_s + w_vol * vol_s

    quality = (
        _trend_mult(close, trend_lookback)
        * _atr_mult(df, close, atr_period, atr_pct_max)
        * _proximity_mult(close)
        * _rs_mult(rocs.get(_ROC_LONG), nifty500_roc_60)
    )

    return ScoreBreakdown(
        score      = round(composite * quality, 2),
        rsi        = round(rsi_s,  2),
        macd_score = round(macd_s, 2),
        roc_score  = round(roc_s,  2),
        vol_score  = round(vol_s,  2),
    )
