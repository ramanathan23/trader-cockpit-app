"""
Unified balanced scorer — captures momentum, trend quality, volatility
compression, and structural context for all trading styles.

Component weights (each normalised to 0–100, equal 25% weight):
  Momentum     — RSI trend zone + MACD histogram acceleration + ROC alignment
  Trend        — ADX trending strength + EMA stack alignment + weekly bias
  Volatility   — BB squeeze active + ATR contraction ratio + NR7
  Structure    — 52-week proximity + relative strength vs benchmark + volume
"""

import pandas as pd

from ..domain.unified_score_breakdown import UnifiedScoreBreakdown
from ._scorer_constants import logger  # noqa: F401 — re-exported for tests
from ._scorer_momentum import _momentum_score
from ._scorer_structure import _structure_score
from ._scorer_trend import _trend_score
from ._scorer_volatility import _volatility_score
from ._stage_detector import detect_stage


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

    trend, t_raw = _trend_score(df, close)
    volatility, v_raw = _volatility_score(df, close)
    structure, s_raw = _structure_score(df, close, volume, nifty500_roc_60=nifty500_roc_60)

    total = 0.25 * momentum + 0.25 * trend + 0.25 * volatility + 0.25 * structure
    stage = detect_stage(close)

    return UnifiedScoreBreakdown(
        total_score=round(total, 2),
        momentum_score=momentum,
        trend_score=trend,
        volatility_score=volatility,
        structure_score=structure,
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
        stage=stage,
    )
