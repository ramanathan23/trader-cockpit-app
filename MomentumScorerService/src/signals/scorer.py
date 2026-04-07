"""
Pure momentum score computation — no I/O, no side effects.

Score components (each normalised to 0–100):
  RSI          weight_rsi  — momentum strength; penalises extremes (>80 overbought)
  MACD         weight_macd — trend acceleration; histogram z-score mapped to 0–100
  ROC          weight_roc  — multi-timeframe momentum (5d/20d/60d alignment) + consistency
  Volume ratio weight_vol  — volume confirms the move

Quality multipliers applied after component scoring:
  Trend context     — long-term 60-bar ROC < -5% → downtrend penalty (dead-cat bounces)
  ATR% volatility   — excessive daily swings relative to price → choppy stock penalty
  52-week proximity — near 52-week highs → boost; far below → neutral (trend_mult covers downside)
  Relative strength — stock ROC vs NIFTY500 60-bar ROC; underperforming the index is penalised

All parameters are explicit keyword args so callers (e.g. ScoreService) can inject
values from Settings without this module having any config dependency.
"""

import logging

import numpy as np
import pandas as pd

from . import indicators
from ..domain.models import ScoreBreakdown

logger = logging.getLogger(__name__)

# Fixed ROC timeframes — 1 week / 1 month / 1 quarter.  Not configurable because
# these periods have fundamental meaning; arbitrary tuning would overfit.
_ROC_SHORT  = 5
_ROC_MID    = 20
_ROC_LONG   = 60
_CONSISTENCY_BARS = 20   # look-back for up-day consistency
_PROXIMITY_BARS   = 252  # trading days in one year for 52-week high


def compute_score(
    df: pd.DataFrame,
    *,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    roc_period: int = 10,          # kept for API compat; internal logic uses fixed periods
    vol_period: int = 20,
    min_bars: int = 30,
    trend_lookback: int = 60,
    atr_period: int = 14,
    atr_pct_max: float = 5.0,
    nifty500_roc_60: float | None = None,
    weights: tuple[float, float, float, float] = (0.30, 0.30, 0.25, 0.15),
) -> ScoreBreakdown | None:
    """
    Compute composite momentum score for one symbol's OHLCV DataFrame.
    Returns None if data is insufficient or any required indicator is NaN.
    CPU-bound — call via asyncio.to_thread from async contexts.
    """
    if len(df) < min_bars:
        return None

    close  = df["close"].astype(float)
    volume = df["volume"].astype(float)

    # ── RSI ───────────────────────────────────────────────────────────────────
    rsi_val = indicators.rsi(close, period=rsi_period).iloc[-1]
    if pd.isna(rsi_val):
        return None

    if rsi_val > 80:
        rsi_score = max(0.0, 100.0 - (rsi_val - 80) * 2)
    elif rsi_val < 20:
        rsi_score = rsi_val * 1.5
    else:
        rsi_score = float(rsi_val)

    # ── MACD histogram z-score ────────────────────────────────────────────────
    _, _, histogram = indicators.macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    hist_now = histogram.iloc[-1]
    hist_std = histogram.std()

    if pd.isna(hist_now) or hist_std == 0 or pd.isna(hist_std):
        macd_score = 50.0
    else:
        macd_score = float(np.clip(50.0 + (hist_now / hist_std) * 15.0, 0.0, 100.0))

    # ── Multi-timeframe ROC + consistency ─────────────────────────────────────
    # Compute ROC at three fixed horizons (5d / 20d / 60d).
    # Score = alignment (how many timeframes are positive) + 20d magnitude bonus
    #         × consistency adjustment (fraction of recent bars that closed up).
    rocs: dict[int, float] = {}
    for period in (_ROC_SHORT, _ROC_MID, _ROC_LONG):
        if len(close) > period:
            val = indicators.rate_of_change(close, period=period).iloc[-1]
            if not pd.isna(val):
                rocs[period] = float(val)

    if not rocs:
        return None

    # Alignment: 0 / 33 / 67 / 100 depending on how many horizons are trending up
    positive_tfs  = sum(1 for r in rocs.values() if r > 0)
    alignment     = (positive_tfs / 3) * 70.0  # max 70 pts from alignment

    # Magnitude bonus from the 20d ROC (moderate moves rewarded, not capped at max)
    roc_20 = rocs.get(_ROC_MID, 0.0)
    magnitude_bonus = float(np.clip(roc_20 * 1.5, 0.0, 30.0)) if roc_20 > 0 else 0.0

    raw_roc_score = alignment + magnitude_bonus  # 0–100

    # Consistency: fraction of last N bars where close > prior close.
    # Scales roc_score between 0.6× (all down-days, spike stock) and 1.0× (all up-days).
    up_days   = int((close.diff() > 0).tail(_CONSISTENCY_BARS).sum())
    consistency = up_days / _CONSISTENCY_BARS
    roc_score = float(raw_roc_score * (0.6 + 0.4 * consistency))

    # ── Volume ratio ──────────────────────────────────────────────────────────
    vol_r = indicators.volume_ratio(volume, period=vol_period).iloc[-1]
    vol_score = 50.0 if pd.isna(vol_r) else float(np.clip(vol_r * 50.0, 0.0, 100.0))

    # ── Composite (weighted sum) ───────────────────────────────────────────────
    w_rsi, w_macd, w_roc, w_vol = weights
    composite = (
        w_rsi  * rsi_score
        + w_macd * macd_score
        + w_roc  * roc_score
        + w_vol  * vol_score
    )

    # ── Quality multipliers ───────────────────────────────────────────────────

    # 1. Trend context: penalise dead-cat bounces (spike inside a long downtrend).
    #    Steeper slope than before — at -15% ROC the mult is ~0.65 not ~0.8.
    trend_mult = 1.0
    if len(close) >= trend_lookback:
        roc_long = indicators.rate_of_change(close, period=trend_lookback).iloc[-1]
        if not pd.isna(roc_long) and roc_long < -5.0:
            trend_mult = max(0.4, 1.0 + (roc_long + 5.0) / 35.0)
            logger.debug("Trend penalty: %.1f%% long ROC → mult=%.2f", roc_long, trend_mult)

    # 2. ATR% volatility: penalise choppy/illiquid stocks.
    atr_mult = 1.0
    if {"high", "low"}.issubset(df.columns):
        atr_val = indicators.atr(
            df["high"].astype(float), df["low"].astype(float), close, period=atr_period
        ).iloc[-1]
        if not pd.isna(atr_val) and close.iloc[-1] > 0:
            atr_pct = atr_val / close.iloc[-1] * 100.0
            if atr_pct > atr_pct_max:
                atr_mult = max(0.5, atr_pct_max / atr_pct)
                logger.debug("ATR penalty: ATR=%.1f%% → mult=%.2f", atr_pct, atr_mult)

    # 3. 52-week high proximity: stocks far below their 52-week high are structurally
    #    weak — penalise them.  Stocks near or at new highs are not boosted here
    #    because their component scores (multi-ROC, MACD) already reflect the strength.
    #    All multipliers are capped at 1.0 (penalties only) to avoid score inflation.
    proximity_mult = 1.0
    lookback_bars  = min(len(close), _PROXIMITY_BARS)
    if lookback_bars >= 60:
        high_52w  = close.iloc[-lookback_bars:].max()
        proximity = close.iloc[-1] / high_52w          # 1.0 = at 52-week high
        if proximity < 0.60:
            proximity_mult = max(0.70, proximity)       # well below 52w high → notable penalty
        elif proximity < 0.75:
            proximity_mult = 0.85                       # moderately below → mild penalty
        # above 75%: neutral — trend_mult already handles persistent declines
        logger.debug("52w proximity: %.1f%% of high → mult=%.2f", proximity * 100, proximity_mult)

    # 4. Relative strength vs NIFTY500: penalise stocks underperforming the broad market.
    #    Uses EXCESS RETURN (stock_roc - index_roc) so sign is correct in all market
    #    directions — avoids the negative÷negative inversion bug.
    #
    #    A stock up +5% while market is +15% has excess=-10% → penalised (mostly beta).
    #    A stock down -16% while market is -12% has excess=-4% → mild penalty.
    #    A stock up +5% while market is -12% has excess=+17% → no penalty (neutral, 1.0).
    #    Capped at 1.0 — outperformance is already captured in component scores.
    rs_mult = 1.0
    if nifty500_roc_60 is not None:
        stock_roc_60 = rocs.get(_ROC_LONG)
        if stock_roc_60 is not None:
            excess = stock_roc_60 - nifty500_roc_60
            rs_mult = float(np.clip(1.0 + excess / 50.0, 0.4, 1.0))
            logger.debug("RS vs NIFTY500: stock=%.1f%% index=%.1f%% excess=%.1f%% → mult=%.2f",
                         stock_roc_60, nifty500_roc_60, excess, rs_mult)

    quality_mult = trend_mult * atr_mult * proximity_mult * rs_mult
    composite    = composite * quality_mult

    return ScoreBreakdown(
        score=round(composite, 2),
        rsi=round(rsi_score, 2),
        macd_score=round(macd_score, 2),
        roc_score=round(roc_score, 2),
        vol_score=round(vol_score, 2),
    )
