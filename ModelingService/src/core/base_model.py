"""Base model interface for all ML models."""

from ._model_abc import BaseModel, ModelMetadata, PredictionRequest, PredictionResult
from ._model_utils import get_model_path, get_active_version

__all__ = [
    "BaseModel",
    "ModelMetadata",
    "PredictionRequest",
    "PredictionResult",
    "get_model_path",
    "get_active_version",
]
