"""ComfortScorer model implementation."""

import json
import logging
import os
import time
from datetime import date, datetime
from typing import Dict, Any, Optional

import numpy as np
import lightgbm as lgb

from ...core.base_model import BaseModel, ModelMetadata
from .features import FeatureExtractor
from .trainer import ComfortScorerTrainer

logger = logging.getLogger(__name__)


class ComfortScorerModel(BaseModel):
    """Predicts hold comfort score (0-100) for stocks."""
    
    def __init__(self, model_base_path: str):
        super().__init__(name="comfort_scorer", model_base_path=model_base_path)
        self.feature_extractor: Optional[FeatureExtractor] = None
    
    async def load(self, version: Optional[str] = None) -> None:
        """Load LightGBM model from disk."""
        if version:
            self.version = version
        else:
            # Try to get active version
            try:
                self.version = self._get_active_version()
            except:
                logger.warning(f"No active version for {self.name}, using v1")
                self.version = "v1"
        
        model_path = self._get_model_path(self.version)
        model_file = os.path.join(model_path, "comfort_model.txt")
        
        if not os.path.exists(model_file):
            logger.warning(f"Model file not found: {model_file}. Model not loaded.")
            return
        
        # Load LightGBM model
        self.model = lgb.Booster(model_file=model_file)
        
        # Load metadata
        metadata_file = os.path.join(model_path, "metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file) as f:
                meta = json.load(f)
                self.metadata = ModelMetadata(
                    name=meta['name'],
                    version=meta['version'],
                    model_type=meta['model_type'],
                    framework=meta['framework'],
                    trained_at=datetime.fromisoformat(meta['trained_at']),
                    feature_names=meta['feature_names'],
                    feature_count=meta['feature_count'],
                    target_metric=meta['target_metric'],
                    performance=meta['performance'],
                    file_path=model_path,
                    is_active=meta.get('is_active', False),
                    is_shadow=meta.get('is_shadow', False),
                )
        
        # Initialize feature extractor
        if self.db_pool:
            self.feature_extractor = FeatureExtractor(self.db_pool)
        
        logger.info(f"Loaded {self.name} {self.version}")
    
    async def extract_features(
        self, 
        symbol: str, 
        date: date,
        context: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """Build feature vector from database."""
        if not self.feature_extractor:
            raise RuntimeError("Feature extractor not initialized (no db_pool)")
        
        return await self.feature_extractor.build_features(symbol, date, context)
    
    async def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict comfort score."""
        if self.model is None:
            raise RuntimeError(f"Model {self.name} not loaded")
        
        comfort_score = self.model.predict([features])[0]
        
        # Confidence based on score range (higher scores = more training data)
        confidence = self._compute_confidence(comfort_score)
        
        return {
            "comfort_score": round(float(comfort_score), 2),
            "confidence": confidence,
            "interpretation": self._interpret_score(comfort_score),
        }
    
    async def train(
        self, 
        start_date: date, 
        end_date: date,
        reason: str = "manual"
    ) -> ModelMetadata:
        """Train new comfort scorer model."""
        logger.info(f"Training {self.name}: {start_date} to {end_date}, reason={reason}")
        
        if not self.db_pool:
            raise RuntimeError("Cannot train without db_pool")
        
        # Build training dataset
        trainer = ComfortScorerTrainer(self.db_pool)
        X, y = await trainer.build_dataset(start_date, end_date)
        
        if len(X) < 1000:
            raise ValueError(f"Insufficient training samples: {len(X)} (need >1000)")
        
        # Train LightGBM
        model, metrics = trainer.train_lightgbm(X, y)
        
        # Save new version
        new_version = f"v{int(time.time())}"
        save_path = os.path.join(self.model_base_path, self.name, new_version)
        os.makedirs(save_path, exist_ok=True)
        
        model.save_model(os.path.join(save_path, "comfort_model.txt"))
        
        # Save metadata
        metadata = ModelMetadata(
            name=self.name,
            version=new_version,
            model_type="regression",
            framework="lightgbm",
            trained_at=datetime.now(),
            feature_names=FeatureExtractor.FEATURE_NAMES,
            feature_count=len(FeatureExtractor.FEATURE_NAMES),
            target_metric="rmse",
            performance=metrics,
            file_path=save_path,
            is_active=False,
            is_shadow=True,  # New models start in shadow mode
        )
        
        with open(os.path.join(save_path, "metadata.json"), "w") as f:
            # Convert metadata to dict
            meta_dict = {
                'name': metadata.name,
                'version': metadata.version,
                'model_type': metadata.model_type,
                'framework': metadata.framework,
                'trained_at': metadata.trained_at.isoformat(),
                'feature_names': metadata.feature_names,
                'feature_count': metadata.feature_count,
                'target_metric': metadata.target_metric,
                'performance': metadata.performance,
                'file_path': metadata.file_path,
                'is_active': metadata.is_active,
                'is_shadow': metadata.is_shadow,
            }
            json.dump(meta_dict, f, indent=2)
        
        logger.info(f"Saved new model: {new_version} at {save_path}")
        
        # TODO: Store in model_registry table
        # TODO: Store in model_training_history table
        
        return metadata
    
    async def evaluate(
        self, 
        predictions: list[float], 
        actuals: list[float]
    ) -> Dict[str, float]:
        """Compute RMSE, MAE, R2 for comfort predictions."""
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        rmse = mean_squared_error(actuals, predictions, squared=False)
        mae = mean_absolute_error(actuals, predictions)
        r2 = r2_score(actuals, predictions)
        
        return {
            "rmse": round(rmse, 2),
            "mae": round(mae, 2),
            "r2": round(r2, 3),
        }
    
    @staticmethod
    def _compute_confidence(comfort_score: float) -> float:
        """
        Compute prediction confidence.
        
        Higher confidence for mid-range scores (more training data).
        Lower confidence for extremes.
        """
        # Bell curve centered at 60
        distance_from_60 = abs(comfort_score - 60.0)
        confidence = max(0.5, 1.0 - (distance_from_60 / 60.0) * 0.5)
        return round(confidence, 2)
    
    @staticmethod
    def _interpret_score(comfort_score: float) -> str:
        """Human-readable interpretation of comfort score."""
        if comfort_score >= 80:
            return "Excellent hold comfort - smooth ride expected"
        elif comfort_score >= 65:
            return "Good comfort - manageable swings"
        elif comfort_score >= 50:
            return "Moderate comfort - some volatility expected"
        elif comfort_score >= 35:
            return "Low comfort - significant swings likely"
        else:
            return "Poor comfort - high psychological stress"
