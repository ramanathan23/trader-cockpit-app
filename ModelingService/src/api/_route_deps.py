"""FastAPI dependency functions for API routes."""

from fastapi import Request

from ..core.model_registry import ModelRegistry
from ..repositories.prediction_repository import PredictionRepository


def get_registry(request: Request) -> ModelRegistry:
    """Get model registry from app state."""
    return request.app.state.registry


def get_prediction_repo(request: Request) -> PredictionRepository:
    """Get prediction repository from app state."""
    return request.app.state.prediction_repo
