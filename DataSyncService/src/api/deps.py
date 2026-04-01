"""
FastAPI dependency providers.

Each function extracts an object stored on app.state during lifespan startup.
Using Annotated + Depends keeps route signatures clean and enables easy testing
via dependency overrides.
"""

from typing import Annotated

from fastapi import Depends, Request

from ..repositories.price_repository import PriceRepository
from ..repositories.symbol_repository import SymbolRepository
from ..repositories.sync_state_repository import SyncStateRepository
from ..services.sync_service import SyncService


def _price_repo(request: Request) -> PriceRepository:
    return request.app.state.price_repo


def _symbol_repo(request: Request) -> SymbolRepository:
    return request.app.state.symbol_repo


def _sync_state_repo(request: Request) -> SyncStateRepository:
    return request.app.state.sync_state_repo


def _sync_service(request: Request) -> SyncService:
    return request.app.state.sync_service


PriceRepoDep     = Annotated[PriceRepository,     Depends(_price_repo)]
SymbolRepoDep    = Annotated[SymbolRepository,    Depends(_symbol_repo)]
SyncStateRepoDep = Annotated[SyncStateRepository, Depends(_sync_state_repo)]
SyncServiceDep   = Annotated[SyncService,         Depends(_sync_service)]
