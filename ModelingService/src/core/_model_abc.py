"""Abstract base class for all ML models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import numpy as np

from ._model_utils import get_model_path, get_active_version


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""
    name: str
    version: str
    model_type: str
    framework: str
    trained_at: datetime
    feature_names: List[str]
    feature_count: int
    target_metric: str
    performance: Dict[str, float]
    file_path: str
    is_active: bool = False
    is_shadow: bool = False


@dataclass
class PredictionRequest:
    """Request for model prediction."""
    model_name: str
    symbols: List[str]
    date: date
    context: Optional[Dict[str, Any]] = None


@dataclass
class PredictionResult:
    """Result from model prediction."""
    model_name: str
    model_version: str
    symbol: str
    prediction_date: date
    predictions: Dict[str, Any]
    confidence: Optional[float] = None
    metadata: Optional[Dict] = None


class BaseModel(ABC):
    """Abstract base class for all ML models."""

    def __init__(self, name: str, model_base_path: str):
        self.name = name
        self.model_base_path = model_base_path
        self.version: Optional[str] = None
        self.model: Any = None
        self.metadata: Optional[ModelMetadata] = None
        self.db_pool: Any = None

    @abstractmethod
    async def load(self, version: Optional[str] = None) -> None: ...

    @abstractmethod
    async def predict(self, features: np.ndarray) -> Dict[str, Any]: ...

    @abstractmethod
    async def extract_features(
        self, symbol: str, date: date, context: Optional[Dict[str, Any]] = None
    ) -> np.ndarray: ...

    @abstractmethod
    async def train(
        self, start_date: date, end_date: date, reason: str = "manual"
    ) -> "ModelMetadata": ...

    @abstractmethod
    async def evaluate(
        self, predictions: List[float], actuals: List[float]
    ) -> Dict[str, float]: ...

    def _get_model_path(self, version: Optional[str] = None) -> str:
        return get_model_path(self.model_base_path, self.name, version)

    def _get_active_version(self) -> str:
        return get_active_version(self.model_base_path, self.name)
