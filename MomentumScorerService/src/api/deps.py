"""
FastAPI dependency providers.

Each function extracts an object stored on app.state during lifespan startup.
Using Annotated + Depends keeps route signatures clean and enables easy testing
via dependency overrides.
"""

from typing import Annotated

from fastapi import Depends, Request

from ..repositories.score_repository import ScoreRepository
from ..services.score_service import ScoreService


def _score_repo(request: Request) -> ScoreRepository:
    return request.app.state.score_repo


def _score_service(request: Request) -> ScoreService:
    return request.app.state.score_service


ScoreRepoDep    = Annotated[ScoreRepository, Depends(_score_repo)]
ScoreServiceDep = Annotated[ScoreService,    Depends(_score_service)]
