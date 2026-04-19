"""Training route handlers."""

from fastapi import APIRouter, Depends, HTTPException

from ..core.model_registry import ModelRegistry
from ._route_deps import get_registry

router = APIRouter()


@router.post("/models/{model_name}/retrain")
async def retrain_model(
    model_name: str,
    start_date: str,
    end_date: str,
    reason: str = "manual",
    registry: ModelRegistry = Depends(get_registry),
):
    """Trigger model retraining (background task)."""
    try:
        model = registry.get_model(model_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # TODO: Add to background tasks
    return {
        "status": "not_implemented",
        "message": "Retraining pipeline coming soon",
        "model": model_name,
    }
