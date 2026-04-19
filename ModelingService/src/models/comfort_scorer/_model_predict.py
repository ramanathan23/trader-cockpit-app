"""Prediction helpers for ComfortScorerModel.

Comfort is a chart-readability score for momentum trading, not a weak forecast
of the next 5-day return.
"""

from typing import Any, Dict

import numpy as np


def predict_comfort(features: np.ndarray) -> Dict[str, Any]:
    """Return chart comfort score from feature vector.

    ``comfort_score`` follows the current chart state in a way traders can
    reason about visually.
    """
    comfort_score, components = compute_chart_comfort(features)
    return {
        "comfort_score": round(float(comfort_score), 2),
        "confidence": compute_confidence(comfort_score),
        "interpretation": interpret_score(comfort_score),
        "method": "chart_comfort_v2",
        "components": components,
    }


def compute_chart_comfort(features: np.ndarray) -> tuple[float, Dict[str, float]]:
    """Score how comfortable a bullish momentum chart is to trade today."""
    f = _feature_dict(features)

    rsi_quality = _triangular_score(f["rsi_14"], 55.0, 68.0, 78.0)
    roc_alignment = _roc_alignment_score(f["roc_5"], f["roc_20"], f["roc_60"])
    macd_quality = _signed_quality(f["macd_hist"], good=0.0, strong=1.0)
    momentum_quality = (
        0.35 * _clamp(f["momentum_score"])
        + 0.30 * rsi_quality
        + 0.25 * roc_alignment
        + 0.10 * macd_quality
    )

    di_spread = f["plus_di"] - f["minus_di"]
    di_quality = _signed_quality(di_spread, good=4.0, strong=22.0)
    adx_quality = _triangular_score(f["adx_14"], 18.0, 32.0, 48.0)
    trend_quality = (
        0.45 * _clamp(f["trend_score"])
        + 0.30 * di_quality
        + 0.25 * adx_quality
    )

    atr_quality = _triangular_score(f["atr_ratio"], 0.65, 0.90, 1.20)
    width_quality = _bandwidth_quality(f["bb_width"], f["kc_width"])
    compression_bonus = 8.0 if f["bb_squeeze"] or f["nr7"] else 0.0
    risk_quality = _clamp(
        0.55 * atr_quality
        + 0.25 * width_quality
        + 0.20 * _inverse_stress(f["volatility_score"])
        + compression_bonus
    )

    rs_quality = _signed_quality(f["rs_vs_nifty"], good=1.0, strong=12.0)
    volume_quality = _triangular_score(f["vol_ratio_20"], 0.8, 1.6, 3.2)
    structure_quality = (
        0.50 * _clamp(f["structure_score"])
        + 0.30 * rs_quality
        + 0.20 * volume_quality
    )

    penalty = _stress_penalty(f)
    comfort = (
        0.32 * momentum_quality
        + 0.30 * trend_quality
        + 0.23 * risk_quality
        + 0.15 * structure_quality
        - penalty
    )

    components = {
        "momentum": round(momentum_quality, 2),
        "trend": round(trend_quality, 2),
        "risk": round(risk_quality, 2),
        "structure": round(structure_quality, 2),
        "penalty": round(penalty, 2),
    }
    return _clamp(comfort), components


def compute_confidence(comfort_score: float) -> float:
    """Compute rule confidence from distance to decision bands."""
    if comfort_score >= 75 or comfort_score < 35:
        return 0.86
    if comfort_score >= 65 or comfort_score < 50:
        return 0.78
    return 0.70


def interpret_score(comfort_score: float) -> str:
    """Human-readable interpretation of comfort score."""
    if comfort_score >= 80:
        return "Excellent comfort - clean momentum chart"
    elif comfort_score >= 65:
        return "Good comfort - trend is readable"
    elif comfort_score >= 50:
        return "Moderate comfort - trade needs tighter risk"
    elif comfort_score >= 35:
        return "Low comfort - noisy or extended momentum"
    return "Poor comfort - avoid unless setup is exceptional"


def _feature_dict(features: np.ndarray) -> Dict[str, float]:
    vals = [float(x) if np.isfinite(float(x)) else 0.0 for x in features]
    names = [
        "total_score", "momentum_score", "trend_score", "volatility_score",
        "structure_score", "rsi_14", "macd_hist", "roc_5", "roc_20",
        "roc_60", "vol_ratio_20", "adx_14", "plus_di", "minus_di",
        "bb_squeeze", "squeeze_days", "nr7", "atr_ratio", "atr_5",
        "bb_width", "kc_width", "rs_vs_nifty",
    ]
    return dict(zip(names, vals))


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _triangular_score(value: float, low: float, sweet: float, high: float) -> float:
    """100 at sweet; fades toward 0 outside low/high."""
    if value <= low:
        return _clamp((value / low) * 50.0 if low > 0 else 0.0)
    if value <= sweet:
        return 50.0 + (value - low) / (sweet - low) * 50.0
    if value <= high:
        return 100.0 - (value - sweet) / (high - sweet) * 50.0
    return max(0.0, 50.0 - (value - high) * 8.0)


def _signed_quality(value: float, good: float, strong: float) -> float:
    if value <= 0:
        return _clamp(35.0 + value * 3.0)
    if value <= good:
        return 45.0 + (value / good) * 15.0 if good > 0 else 60.0
    if value <= strong:
        return 60.0 + (value - good) / (strong - good) * 40.0
    return 100.0


def _roc_alignment_score(roc_5: float, roc_20: float, roc_60: float) -> float:
    score = 20.0
    if roc_5 > 0:
        score += 20.0
    if roc_20 > 0:
        score += 25.0
    if roc_60 > 0:
        score += 20.0
    if 0 < roc_5 <= max(8.0, abs(roc_20) * 0.7):
        score += 10.0
    if roc_20 > 0 and roc_60 > 0 and roc_20 <= roc_60 * 1.25 + 5.0:
        score += 5.0
    return _clamp(score)


def _bandwidth_quality(bb_width: float, kc_width: float) -> float:
    if bb_width <= 0:
        return 50.0
    ratio = bb_width / kc_width if kc_width > 0 else 1.0
    return _triangular_score(ratio, 0.55, 0.95, 1.85)


def _inverse_stress(volatility_score: float) -> float:
    """Existing volatility_score rewards compression; keep it useful but bounded."""
    return _clamp(35.0 + volatility_score * 0.55)


def _stress_penalty(f: Dict[str, float]) -> float:
    penalty = 0.0
    if f["rsi_14"] > 75:
        penalty += min(16.0, (f["rsi_14"] - 75.0) * 1.6)
    if f["roc_5"] > 9:
        penalty += min(14.0, (f["roc_5"] - 9.0) * 1.2)
    if f["roc_20"] > 24:
        penalty += min(10.0, (f["roc_20"] - 24.0) * 0.5)
    if f["atr_ratio"] > 1.25:
        penalty += min(15.0, (f["atr_ratio"] - 1.25) * 40.0)
    if f["plus_di"] <= f["minus_di"]:
        penalty += 10.0
    if f["roc_20"] <= 0:
        penalty += 12.0
    return penalty
