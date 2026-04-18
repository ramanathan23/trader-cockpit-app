"""Base model interface for all ML models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""
    name: str                       # 'comfort_scorer', 'regime_classifier'
    version: str                    # 'v1', 'v20260418'
    model_type: str                 # 'regression', 'classification', 'clustering'
    framework: str                  # 'lightgbm', 'sklearn', 'pytorch'
    trained_at: datetime
    feature_names: List[str]
    feature_count: int
    target_metric: str              # 'rmse', 'accuracy', 'silhouette'
    performance: Dict[str, float]   # Training performance metrics
    file_path: str
    is_active: bool = False
    is_shadow: bool = False


@dataclass
class PredictionRequest:
    """Request for model prediction."""
    model_name: str
    symbols: List[str]
    date: date
    context: Optional[Dict[str, Any]] = None  # Extra params


@dataclass
class PredictionResult:
    """Result from model prediction."""
    model_name: str
    model_version: str
    symbol: str
    prediction_date: date
    predictions: Dict[str, Any]  # Flexible output
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
        self.db_pool: Any = None  # Set by registry
    
    @abstractmethod
    async def load(self, version: Optional[str] = None) -> None:
        """
        Load model from disk.
        
        Args:
            version: Specific version to load, or None for active version
        """
        pass
    
    @abstractmethod
    async def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """
        Run inference on feature vector.
        
        Args:
            features: Feature array for single sample
            
        Returns:
            Dict with model-specific predictions
        """
        pass
    
    @abstractmethod
    async def extract_features(
        self, 
        symbol: str, 
        date: date,
        context: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        Build feature vector from database.
        
        Args:
            symbol: Stock symbol
            date: Prediction date
            context: Additional parameters
            
        Returns:
            Feature array
        """
        pass
    
    @abstractmethod
    async def train(
        self, 
        start_date: date, 
        end_date: date,
        reason: str = "manual"
    ) -> ModelMetadata:
        """
        Train new model version.
        
        Args:
            start_date: Training data start
            end_date: Training data end
            reason: Trigger reason
            
        Returns:
            Metadata for trained model
        """
        pass
    
    @abstractmethod
    async def evaluate(
        self, 
        predictions: List[float], 
        actuals: List[float]
    ) -> Dict[str, float]:
        """
        Compute performance metrics.
        
        Args:
            predictions: Predicted values
            actuals: Actual values
            
        Returns:
            Dict of metrics (rmse, mae, r2, etc)
        """
        pass
    
    def _get_model_path(self, version: Optional[str] = None) -> str:
        """Get path to model directory."""
        import os
        if version:
            return os.path.join(self.model_base_path, self.name, version)
        else:
            # Use 'active' symlink
            return os.path.join(self.model_base_path, self.name, "active")
    
    def _get_active_version(self) -> str:
        """Read active version from symlink or metadata."""
        import os
        active_path = os.path.join(self.model_base_path, self.name, "active")
        
        if os.path.islink(active_path):
            # Read symlink target
            target = os.readlink(active_path)
            return os.path.basename(target)
        elif os.path.isdir(active_path):
            # Fallback: read metadata.json
            import json
            with open(os.path.join(active_path, "metadata.json")) as f:
                meta = json.load(f)
                return meta.get("version", "v1")
        else:
            # Default
            return "v1"
