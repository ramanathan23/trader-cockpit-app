"""Model registry - central manager for all models."""

import logging
from typing import Dict, List, Optional

from .base_model import BaseModel

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Central registry for all ML models."""
    
    def __init__(self, model_base_path: str, db_pool):
        self.model_base_path = model_base_path
        self.db_pool = db_pool
        self.models: Dict[str, BaseModel] = {}
    
    async def initialize(self) -> None:
        """Auto-discover and load all models."""
        logger.info("Initializing model registry")
        
        # Import and register models
        # NOTE: Add new models here as they're implemented
        try:
            from ..models.comfort_scorer.model import ComfortScorerModel
            await self._register_and_load(ComfortScorerModel(self.model_base_path))
        except ImportError as e:
            logger.warning(f"ComfortScorerModel not available: {e}")
        
        # Future models:
        # from ..models.regime_classifier.model import RegimeClassifierModel
        # from ..models.pattern_detector.model import PatternDetectorModel
        
        logger.info(f"Registry initialized with {len(self.models)} models")
    
    async def _register_and_load(self, model: BaseModel) -> None:
        """Register model and load active version."""
        model.db_pool = self.db_pool
        
        try:
            await model.load()
            self.models[model.name] = model
            logger.info(f"Registered model: {model.name} ({model.version})")
        except Exception as e:
            logger.error(f"Failed to load model {model.name}: {e}")
            # Still register, but without loaded model
            self.models[model.name] = model
    
    def get_model(self, name: str) -> BaseModel:
        """Retrieve model by name."""
        if name not in self.models:
            raise ValueError(f"Model '{name}' not found in registry")
        return self.models[name]
    
    def list_models(self) -> List[Dict]:
        """Return all registered models with status."""
        return [
            {
                "name": m.name,
                "version": m.version or "not_loaded",
                "type": m.metadata.model_type if m.metadata else "unknown",
                "status": "active" if m.model is not None else "not_loaded",
                "trained_at": m.metadata.trained_at.isoformat() if m.metadata else None,
            }
            for m in self.models.values()
        ]
    
    async def reload_model(self, name: str, version: Optional[str] = None) -> None:
        """Hot-reload model with specific version."""
        model = self.get_model(name)
        await model.load(version=version)
        logger.info(f"Reloaded {name} to version {model.version}")
