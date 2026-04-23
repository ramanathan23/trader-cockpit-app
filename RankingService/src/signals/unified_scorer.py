"""
Unified balanced scorer.

Component weights (each normalised 0–100, equal 25%):
  Momentum   — RSI zone + MACD acceleration + ROC alignment + volume
  Trend      — ADX strength + EMA stack + weekly bias
  Volatility — BB squeeze + ATR contraction + NR7
  Structure  — 52-week proximity + RS vs Nifty + volume profile

Input: pre-computed indicator dict from symbol_indicators + symbol_metrics JOIN.
No raw OHLCV access — IndicatorsService owns all computation.
"""
from ..domain.unified_score_breakdown import UnifiedScoreBreakdown
from ._scorer_momentum import _momentum_score
from ._scorer_structure import _structure_score
from ._scorer_trend import _trend_score
from ._scorer_volatility import _volatility_score


def compute_score_from_indicators(ind: dict) -> UnifiedScoreBreakdown | None:
    """
    Compute unified score from pre-computed indicator dict.
    Returns None when required indicators are missing.
    """
    momentum, _ = _momentum_score(ind)
    if momentum is None:
        return None

    trend, _ = _trend_score(ind)
    volatility, _ = _volatility_score(ind)
    structure, _ = _structure_score(ind)

    total = 0.25 * momentum + 0.25 * trend + 0.25 * volatility + 0.25 * structure

    return UnifiedScoreBreakdown(
        total_score=round(total, 2),
        momentum_score=momentum,
        trend_score=trend,
        volatility_score=volatility,
        structure_score=structure,
        rsi_14=ind.get("rsi_14"),
        macd_hist=ind.get("macd_hist"),
        roc_5=ind.get("roc_5"),
        roc_20=ind.get("roc_20"),
        roc_60=ind.get("roc_60"),
        vol_ratio_20=ind.get("vol_ratio_20"),
        adx_14=ind.get("adx_14"),
        plus_di=ind.get("plus_di"),
        minus_di=ind.get("minus_di"),
        weekly_bias=ind.get("weekly_bias", "NEUTRAL"),
        bb_squeeze=bool(ind.get("bb_squeeze", False)),
        squeeze_days=int(ind.get("squeeze_days", 0)),
        nr7=bool(ind.get("nr7", False)),
        atr_ratio=ind.get("atr_ratio"),
        atr_5=ind.get("atr_5"),
        bb_width=ind.get("bb_width"),
        kc_width=ind.get("kc_width"),
        rs_vs_nifty=ind.get("rs_vs_nifty"),
        stage=ind.get("stage", "UNKNOWN"),
    )
