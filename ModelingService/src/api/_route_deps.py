"""FastAPI dependency functions for API routes."""

from fastapi import Request

from ..core.model_registry import ModelRegistry
from ..repositories.prediction_repository import PredictionRepository
from ..services.scoring_service import ScoringService
from ..services.session_classifier_service import SessionClassifierService
from ..services.training_data_service import TrainingDataService


def get_registry(request: Request) -> ModelRegistry:
    """Get model registry from app state."""
    return request.app.state.registry


def get_prediction_repo(request: Request) -> PredictionRepository:
    """Get prediction repository from app state."""
    return request.app.state.prediction_repo


def get_scoring_service(request: Request) -> ScoringService:
    """Get scoring service from app state."""
    return request.app.state.scoring_service


def get_training_data_service(request: Request) -> TrainingDataService:
    return request.app.state.training_data_service


def get_session_classifier_service(request: Request) -> SessionClassifierService:
    return request.app.state.session_classifier_service
