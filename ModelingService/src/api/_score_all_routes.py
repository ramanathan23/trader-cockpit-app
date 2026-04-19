"""Batch score-all endpoint — runs inference for every symbol in daily_scores."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from ..services.scoring_service import ScoringService
from ._route_deps import get_scoring_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/models/{model_name}/score-all")
async def score_all(
    model_name: str,
    score_date: date | None = None,
    scoring_service: ScoringService = Depends(get_scoring_service),
):
    """
    Run batch inference for all symbols that have daily_scores on score_date
    and persist results to model_predictions.

    If score_date is omitted, uses today's date (IST).

    Example:
      POST /models/comfort_scorer/score-all?score_date=2026-04-18
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if score_date is None:
        score_date = datetime.now(tz=ZoneInfo("Asia/Kolkata")).date()

    try:
        result = await scoring_service.run_all(model_name, score_date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "model": result.model_name,
        "score_date": str(result.score_date),
        "total_symbols": result.total,
        "success": result.success,
        "failed": result.failed,
        "stored": result.stored,
    }
