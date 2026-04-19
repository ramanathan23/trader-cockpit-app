"""Status and metrics route handlers."""

from fastapi import APIRouter, Depends, HTTPException

from ..core.model_registry import ModelRegistry
from ._route_deps import get_registry

router = APIRouter()


@router.get("/models")
async def list_models(registry: ModelRegistry = Depends(get_registry)):
    """List all available models."""
    return {"models": registry.list_models()}


@router.get("/models/{model_name}/metrics")
async def get_model_metrics(
    model_name: str,
    days: int = 30,
    registry: ModelRegistry = Depends(get_registry),
):
    """Get performance metrics for model."""
    try:
        model = registry.get_model(model_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # TODO: Query model_performance table
    return {
        "model": model_name,
        "version": model.version,
        "status": "not_implemented",
        "message": "Metrics tracking coming soon",
    }
