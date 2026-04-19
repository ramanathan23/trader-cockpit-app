"""FastAPI dependency functions for API routes."""

from fastapi import Request

from ..core.model_registry import ModelRegistry
from ..repositories.prediction_repository import PredictionRepository
from ..services.scoring_service import ScoringService


def get_registry(request: Request) -> ModelRegistry:
    """Get model registry from app state."""
    return request.app.state.registry


def get_prediction_repo(request: Request) -> PredictionRepository:
    """Get prediction repository from app state."""
    return request.app.state.prediction_repo


def get_scoring_service(request: Request) -> ScoringService:
    """Get scoring service from app state."""
    return request.app.state.scoring_service
