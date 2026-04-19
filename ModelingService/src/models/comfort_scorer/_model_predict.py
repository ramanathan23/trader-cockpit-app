"""Prediction inference helpers for ComfortScorerModel."""

from typing import Any, Dict

import numpy as np
import lightgbm as lgb


def predict_comfort(model: lgb.Booster, features: np.ndarray) -> Dict[str, Any]:
    """Predict comfort score from feature vector."""
    comfort_score = model.predict([features])[0]
    return {
        "comfort_score": round(float(comfort_score), 2),
        "confidence": compute_confidence(comfort_score),
        "interpretation": interpret_score(comfort_score),
    }


def compute_confidence(comfort_score: float) -> float:
    """Compute prediction confidence. Higher for mid-range scores (more training data)."""
    distance_from_60 = abs(comfort_score - 60.0)
    return round(max(0.5, 1.0 - (distance_from_60 / 60.0) * 0.5), 2)


def interpret_score(comfort_score: float) -> str:
    """Human-readable interpretation of comfort score."""
    if comfort_score >= 80:
        return "Excellent hold comfort - smooth ride expected"
    elif comfort_score >= 65:
        return "Good comfort - manageable swings"
    elif comfort_score >= 50:
        return "Moderate comfort - some volatility expected"
    elif comfort_score >= 35:
        return "Low comfort - significant swings likely"
    return "Poor comfort - high psychological stress"
