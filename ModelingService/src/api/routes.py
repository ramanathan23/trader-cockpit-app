"""API routes for ModelingService."""

from fastapi import APIRouter

from ._predict_routes import router as _predict_router, PredictRequest
from ._score_all_routes import router as _score_all_router
from ._session_classifier_routes import router as _session_classifier_router
from ._status_routes import router as _status_router
from ._train_routes import router as _train_router
from ._config_routes import router as _config_router

router = APIRouter()
router.include_router(_session_classifier_router)
router.include_router(_predict_router)
router.include_router(_score_all_router)
router.include_router(_status_router)
router.include_router(_train_router)
router.include_router(_config_router)

__all__ = ["router", "PredictRequest"]
