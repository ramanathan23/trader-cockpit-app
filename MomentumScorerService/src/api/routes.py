import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from .deps import ScoreRepoDep, ScoreServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/scores/compute", summary="Trigger momentum score computation (background)")
async def trigger_compute(
    background_tasks: BackgroundTasks,
    svc: ScoreServiceDep,
    timeframe: str = Query(default="1d", pattern="^(1d|1m)$"),
):
    background_tasks.add_task(svc.compute_all, timeframe)
    return {"status": "started", "timeframe": timeframe}


@router.get("/scores", summary="Top-N symbols by momentum score")
async def get_scores(
    repo: ScoreRepoDep,
    timeframe:  str   = Query(default="1d", pattern="^(1d|1m)$"),
    limit:      int   = Query(default=50, ge=1, le=500),
    min_score:  float = Query(default=0.0, ge=0.0, le=100.0),
):
    return await repo.get_top(timeframe, limit, min_score)


# NOTE: /scores/summary/distribution must be declared before /scores/{symbol}
# to prevent FastAPI matching "summary" as a symbol path parameter.
@router.get("/scores/summary/distribution", summary="Score distribution histogram")
async def score_distribution(
    repo: ScoreRepoDep,
    timeframe: str = Query(default="1d", pattern="^(1d|1m)$"),
    buckets:   int = Query(default=10, ge=2, le=20),
):
    return await repo.get_distribution(timeframe, buckets)


@router.get("/scores/{symbol}", summary="Full score breakdown for a symbol")
async def get_symbol_score(symbol: str, repo: ScoreRepoDep):
    rows = await repo.get_for_symbol(symbol.upper())
    if not rows:
        raise HTTPException(404, f"No scores found for '{symbol}' — run /scores/compute first")
    return rows
