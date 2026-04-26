"""Intraday session classifier endpoints."""

import asyncio
import json
import logging
import time
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..services.session_classifier_service import SessionClassifierService
from ..services.training_data_service import TrainingDataService
from ._route_deps import get_session_classifier_service, get_training_data_service

logger = logging.getLogger(__name__)
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


@router.post("/models/session_classifier/pipeline-sse")
async def session_classifier_pipeline_sse(
    score_date: date | None = None,
    lookback_years: int = 5,
    training_service: TrainingDataService = Depends(get_training_data_service),
    session_service: SessionClassifierService = Depends(get_session_classifier_service),
):
    async def generate():
        started = time.perf_counter()

        async def emit(status: str, message: str, result: dict | None = None) -> str:
            payload = {"status": status, "message": message}
            if result is not None:
                payload["result"] = result
            return f"data: {json.dumps(payload)}\n\n"

        async def run_with_progress(label: str, coro):
            task = asyncio.create_task(coro)
            elapsed = 0
            while not task.done():
                await asyncio.sleep(5)
                elapsed += 5
                yield await emit("running", f"{label}... {elapsed}s")
            yield task.result()

        try:
            yield await emit("running", "Scoring session classifier")
            try:
                score_result = None
                async for event in run_with_progress(
                    "Scoring session classifier",
                    session_service.score_all(score_date),
                ):
                    if isinstance(event, str):
                        yield event
                    else:
                        score_result = event
            except RuntimeError as exc:
                if "not trained" not in str(exc).lower():
                    raise

                yield await emit("running", "Building session training data")
                build_result = None
                async for event in run_with_progress(
                    "Building session training data",
                    training_service.build_training_sessions(lookback_years=lookback_years),
                ):
                    if isinstance(event, str):
                        yield event
                    else:
                        build_result = event

                sessions_written = build_result.get("sessions_written", 0) if build_result else 0
                yield await emit("running", f"Training session model ({sessions_written} sessions)")
                async for event in run_with_progress(
                    "Training session model",
                    session_service.train(),
                ):
                    if isinstance(event, str):
                        yield event

                yield await emit("running", "Scoring trained session model")
                score_result = None
                async for event in run_with_progress(
                    "Scoring trained session model",
                    session_service.score_all(score_date),
                ):
                    if isinstance(event, str):
                        yield event
                    else:
                        score_result = event

            score_result = score_result or {}
            scored = score_result.get("symbols_scored", 0)
            comfort = score_result.get("comfort_v3_updated", 0)
            score_result["duration_s"] = round(time.perf_counter() - started, 2)
            yield await emit(
                "ok",
                f"{scored} session predictions, {comfort} comfort v3 updates",
                score_result,
            )
        except Exception as exc:
            logger.exception("session_classifier_pipeline_sse failed")
            yield await emit("error", str(exc) or type(exc).__name__)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
