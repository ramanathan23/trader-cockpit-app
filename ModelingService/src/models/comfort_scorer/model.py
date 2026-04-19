"""ComfortScorer model implementation."""

import logging
from datetime import date
from typing import Dict, Any, List, Optional

import numpy as np

from ...core.base_model import BaseModel, ModelMetadata
from .features import FeatureExtractor
from ._model_io import load_comfort_model
from ._model_predict import predict_comfort
from ._model_train import train_comfort_model

logger = logging.getLogger(__name__)


class ComfortScorerModel(BaseModel):
    """Predicts hold comfort score (0-100) for stocks."""

    def __init__(self, model_base_path: str):
        super().__init__(name="comfort_scorer", model_base_path=model_base_path)
        self.feature_extractor: Optional[FeatureExtractor] = None

    async def load(self, version: Optional[str] = None) -> None:
        """Load LightGBM model from disk."""
        self.model, self.metadata, self.feature_extractor, self.version = (
            await load_comfort_model(self.model_base_path, self.name, version, self.db_pool)
        )

    async def extract_features(
        self, symbol: str, date: date, context: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """Build feature vector from database."""
        if not self.feature_extractor:
            raise RuntimeError("Feature extractor not initialized (no db_pool)")
        return await self.feature_extractor.build_features(symbol, date, context)

    async def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict comfort score."""
        if self.model is None:
            raise RuntimeError(f"Model {self.name} not loaded")
        return predict_comfort(self.model, features)

    async def train(
        self, start_date: date, end_date: date, reason: str = "manual"
    ) -> ModelMetadata:
        """Train new comfort scorer model."""
        if not self.db_pool:
            raise RuntimeError("Cannot train without db_pool")
        return await train_comfort_model(
            self.db_pool, self.model_base_path, self.name, start_date, end_date, reason
        )

    async def evaluate(
        self, predictions: List[float], actuals: List[float]
    ) -> Dict[str, float]:
        """Compute RMSE, MAE, R2 for comfort predictions."""
        from sklearn.metrics import root_mean_squared_error, mean_absolute_error, r2_score
        return {
            "rmse": round(float(root_mean_squared_error(actuals, predictions)), 2),
            "mae": round(float(mean_absolute_error(actuals, predictions)), 2),
            "r2": round(float(r2_score(actuals, predictions)), 3),
        }
