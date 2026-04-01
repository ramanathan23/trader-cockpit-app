"""
Pure momentum score computation — no I/O, no side effects.

Score components (each normalised to 0–100):
  RSI          30% — momentum strength; penalises extremes (>80 overbought)
  MACD         30% — trend acceleration; histogram z-score maps to 0–100
  ROC (10-bar) 25% — raw price momentum
  Volume ratio 15% — volume confirms the move
"""

import logging

import numpy as np
import pandas as pd

from . import indicators
from ..domain.models import ScoreBreakdown

logger = logging.getLogger(__name__)


def compute_score(df: pd.DataFrame) -> ScoreBreakdown | None:
    """
    Compute composite momentum score for one symbol's OHLCV DataFrame.
    Requires at least 30 rows; returns None if data is insufficient.
    CPU-bound — call via asyncio.to_thread from async contexts.
    """
    if len(df) < 30:
        return None

    close  = df["close"].astype(float)
    volume = df["volume"].astype(float)

    # ── RSI ───────────────────────────────────────────────────────────────────
    rsi_val = indicators.rsi(close).iloc[-1]
    if pd.isna(rsi_val):
        return None

    if rsi_val > 80:
        rsi_score = max(0.0, 100.0 - (rsi_val - 80) * 2)
    elif rsi_val < 20:
        rsi_score = rsi_val * 1.5
    else:
        rsi_score = float(rsi_val)

    # ── MACD histogram z-score ────────────────────────────────────────────────
    _, _, histogram = indicators.macd(close)
    hist_now = histogram.iloc[-1]
    hist_std = histogram.std()

    if pd.isna(hist_now) or hist_std == 0 or pd.isna(hist_std):
        macd_score = 50.0
    else:
        macd_score = float(np.clip(50.0 + (hist_now / hist_std) * 15.0, 0.0, 100.0))

    # ── Rate of Change ────────────────────────────────────────────────────────
    roc = indicators.rate_of_change(close, period=10).iloc[-1]
    if pd.isna(roc):
        return None
    roc_score = float(np.clip(50.0 + roc * 5.0, 0.0, 100.0))

    # ── Volume ratio ──────────────────────────────────────────────────────────
    vol_r = indicators.volume_ratio(volume).iloc[-1]
    vol_score = 50.0 if pd.isna(vol_r) else float(np.clip(vol_r * 50.0, 0.0, 100.0))

    # ── Composite ─────────────────────────────────────────────────────────────
    composite = 0.30 * rsi_score + 0.30 * macd_score + 0.25 * roc_score + 0.15 * vol_score

    return ScoreBreakdown(
        score=round(composite, 2),
        rsi=round(rsi_score, 2),
        macd_score=round(macd_score, 2),
        roc_score=round(roc_score, 2),
        vol_score=round(vol_score, 2),
    )
