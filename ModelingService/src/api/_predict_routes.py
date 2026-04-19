"""Prediction endpoint handlers."""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel as PydanticBaseModel

from ..core.base_model import PredictionResult
from ..core.model_registry import ModelRegistry
from ..repositories.prediction_repository import PredictionRepository
from ._route_deps import get_registry, get_prediction_repo

logger = logging.getLogger(__name__)
router = APIRouter()


class PredictRequest(PydanticBaseModel):
    symbols: List[str]
    date: str  # ISO date string


@router.post("/models/{model_name}/predict")
async def predict(
    model_name: str,
    request: PredictRequest,
    registry: ModelRegistry = Depends(get_registry),
    prediction_repo: PredictionRepository = Depends(get_prediction_repo),
):
    """
    Unified prediction endpoint.

    Examples:
      POST /models/comfort_scorer/predict
        {"symbols": ["RELIANCE", "TCS"], "date": "2026-04-18"}
    """
    try:
        model = registry.get_model(model_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if model.model is None:
        raise HTTPException(status_code=503, detail=f"Model {model_name} not loaded")

    pred_date = datetime.fromisoformat(request.date).date()
    results = []

    for symbol in request.symbols:
        try:
            features = await model.extract_features(symbol, pred_date)
            prediction = await model.predict(features)
            results.append(PredictionResult(
                model_name=model_name,
                model_version=model.version,
                symbol=symbol,
                prediction_date=pred_date,
                predictions=prediction,
                confidence=prediction.get('confidence'),
            ))
        except Exception as e:
            logger.error(f"Prediction failed for {symbol}: {e}")

    stored_count = await prediction_repo.bulk_insert(results)
    return {
        "model": model_name,
        "version": model.version,
        "predictions": [
            {"symbol": r.symbol, "prediction_date": str(r.prediction_date), **r.predictions}
            for r in results
        ],
        "stored_count": stored_count,
    }
