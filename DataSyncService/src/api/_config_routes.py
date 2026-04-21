import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from shared.config_store import _EXCLUDED, _coerce, get_tunable, save_overrides

from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
_SERVICE = "datasync"


@router.get("/config", summary="Current tunable config for DataSyncService")
async def get_config() -> dict[str, Any]:
    return get_tunable(settings)


@router.patch("/config", summary="Update tunable config — persists to DB and applies immediately")
async def patch_config(request: Request, updates: dict[str, Any]) -> dict[str, Any]:
    pool = request.app.state.pool
    safe: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for key, value in updates.items():
        if key in _EXCLUDED or not hasattr(settings, key):
            errors[key] = "not tunable"
            continue
        try:
            safe[key] = _coerce(settings, key, value)
        except Exception as exc:
            errors[key] = str(exc)

    if errors:
        raise HTTPException(status_code=422, detail={"invalid_fields": errors})

    await save_overrides(pool, _SERVICE, safe)
    for key, value in safe.items():
        object.__setattr__(settings, key, value)

    return get_tunable(settings)
