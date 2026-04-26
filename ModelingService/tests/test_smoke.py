"""Basic smoke test for ModelingService."""

import pytest
from src.core.model_registry import ModelRegistry


def test_imports():
    """Test that core modules can be imported."""
    from src.core.base_model import BaseModel, ModelMetadata
    from src.core.model_registry import ModelRegistry
    from src.models.comfort_scorer.model import ComfortScorerModel
    from src.models.comfort_scorer.features import FeatureExtractor
    
    assert BaseModel is not None
    assert ModelRegistry is not None
    assert ComfortScorerModel is not None


def test_comfort_scorer_instantiation():
    """Test ComfortScorer can be instantiated."""
    from src.models.comfort_scorer.model import ComfortScorerModel
    
    model = ComfortScorerModel(model_base_path="/tmp/models")
    assert model.name == "comfort_scorer"
    assert model.model is None  # Not loaded yet
