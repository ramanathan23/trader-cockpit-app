"""API routes for ModelingService."""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from datetime import date
from pydantic import BaseModel as PydanticBaseModel

from ..core.base_model import PredictionRequest, PredictionResult
from ..core.model_registry import ModelRegistry
from ..repositories.prediction_repository import PredictionRepository

router = APIRouter()


# Request/Response models
class PredictRequest(PydanticBaseModel):
    symbols: List[str]
    date: str  # ISO date string


def get_registry(request: Request) -> ModelRegistry:
    """Dependency to get model registry from app state."""
    return request.app.state.registry


def get_prediction_repo(request: Request) -> PredictionRepository:
    """Dependency to get prediction repository from app state."""
    return request.app.state.prediction_repo


@router.get("/models")
async def list_models(registry: ModelRegistry = Depends(get_registry)):
    """List all available models."""
    return {
        "models": registry.list_models()
    }


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
        raise HTTPException(
            status_code=503, 
            detail=f"Model {model_name} not loaded"
        )
    
    # Parse date
    from datetime import datetime
    pred_date = datetime.fromisoformat(request.date).date()
    
    results = []
    for symbol in request.symbols:
        try:
            features = await model.extract_features(symbol, pred_date)
            prediction = await model.predict(features)
            
            result = PredictionResult(
                model_name=model_name,
                model_version=model.version,
                symbol=symbol,
                prediction_date=pred_date,
                predictions=prediction,
                confidence=prediction.get('confidence'),
            )
            results.append(result)
        except Exception as e:
            # Log error but continue with other symbols
            import logging
            logging.getLogger(__name__).error(
                f"Prediction failed for {symbol}: {e}"
            )
            continue
    
    # Store predictions in DB
    stored_count = await prediction_repo.bulk_insert(results)
    
    return {
        "model": model_name,
        "version": model.version,
        "predictions": [
            {
                "symbol": r.symbol,
                "prediction_date": str(r.prediction_date),
                **r.predictions
            }
            for r in results
        ],
        "stored_count": stored_count,
    }


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
        "message": "Metrics tracking coming soon"
    }


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
