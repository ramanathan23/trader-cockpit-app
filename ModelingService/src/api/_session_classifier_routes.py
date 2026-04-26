"""Intraday session classifier endpoints."""

import time
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from ..services.session_classifier_service import SessionClassifierService
from ..services.training_data_service import TrainingDataService
from ._route_deps import get_session_classifier_service, get_training_data_service

router = APIRouter()


@router.post("/models/session_classifier/build-training-data")
async def build_training_data(
    lookback_years: int = 5,
    service: TrainingDataService = Depends(get_training_data_service),
):
    started = time.perf_counter()
    result = await service.build_training_sessions(lookback_years=lookback_years)
    result["duration_s"] = round(time.perf_counter() - started, 2)
    return result


@router.post("/models/session_classifier/train")
async def train_session_classifier(
    service: SessionClassifierService = Depends(get_session_classifier_service),
):
    try:
        return await service.train()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/models/session_classifier/score-all")
async def score_all_sessions(
    score_date: date | None = None,
    service: SessionClassifierService = Depends(get_session_classifier_service),
):
    try:
        return await service.score_all(score_date)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/models/session_classifier/predict/{symbol}")
async def predict_session(
    symbol: str,
    date: date | None = None,
    service: SessionClassifierService = Depends(get_session_classifier_service),
):
    try:
        return await service.predict_one(symbol.upper(), date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
