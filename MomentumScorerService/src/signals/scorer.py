"""
Pure momentum score computation — no I/O, no side effects.

Score components (each normalised to 0–100):
  RSI          weight_rsi  — momentum strength; penalises extremes (>80 overbought)
  MACD         weight_macd — trend acceleration; histogram z-score mapped to 0–100
  ROC (n-bar)  weight_roc  — raw price momentum
  Volume ratio weight_vol  — volume confirms the move

All parameters are explicit keyword args so callers (e.g. ScoreService) can inject
values from Settings without this module having any config dependency.
"""

import logging

import numpy as np
import pandas as pd

from . import indicators
from ..domain.models import ScoreBreakdown

logger = logging.getLogger(__name__)


def compute_score(
    df: pd.DataFrame,
    *,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    roc_period: int = 10,
    vol_period: int = 20,
    min_bars: int = 30,
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
        # Penalise overbought territory — momentum likely to mean-revert
        rsi_score = max(0.0, 100.0 - (rsi_val - 80) * 2)
    elif rsi_val < 20:
        # Oversold: weak but not zero
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

    # ── Rate of Change ────────────────────────────────────────────────────────
    roc = indicators.rate_of_change(close, period=roc_period).iloc[-1]
    if pd.isna(roc):
        return None
    roc_score = float(np.clip(50.0 + roc * 5.0, 0.0, 100.0))

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

    return ScoreBreakdown(
        score=round(composite, 2),
        rsi=round(rsi_score, 2),
        macd_score=round(macd_score, 2),
        roc_score=round(roc_score, 2),
        vol_score=round(vol_score, 2),
    )
