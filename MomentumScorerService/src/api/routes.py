import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from .deps import ScoreRepoDep, ScoreServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/scores/compute", summary="Trigger momentum score computation (background)")
async def trigger_compute(
    background_tasks: BackgroundTasks,
    svc: ScoreServiceDep,
    timeframe: str = Query(default="1d", pattern="^1d$"),
):
    background_tasks.add_task(svc.compute_all, timeframe)
    return {"status": "started", "timeframe": timeframe}


@router.get("/scores", summary="Top-N symbols by momentum score")
async def get_scores(
    repo: ScoreRepoDep,
    timeframe:  str   = Query(default="1d", pattern="^1d$"),
    limit:      int   = Query(default=50, ge=1, le=500),
    min_score:  float = Query(default=0.0, ge=0.0, le=100.0),
):
    return await repo.get_top(timeframe, limit, min_score)


@router.get("/watchlist/run-tight-base", summary="Watchlist for 4-5 day runs followed by tight consolidation")
async def get_run_tight_base_watchlist(
    svc: ScoreServiceDep,
    side: str = Query(default="both", pattern="^(bull|bear|both)$"),
    limit: int = Query(default=50, ge=1, le=500),
    run_window: int = Query(default=5, ge=4, le=10),
    base_window: int = Query(default=3, ge=2, le=5),
    min_run_move_pct: float = Query(default=8.0, ge=1.0, le=50.0),
    max_base_range_pct: float = Query(default=3.0, ge=0.5, le=10.0),
    max_retracement_pct: float = Query(default=0.35, ge=0.05, le=1.0),
):
    return await svc.build_watchlist(
        side=side,
        limit=limit,
        run_window=run_window,
        base_window=base_window,
        min_run_move_pct=min_run_move_pct,
        max_base_range_pct=max_base_range_pct,
        max_retracement_pct=max_retracement_pct,
    )


# NOTE: /scores/summary/distribution must be declared before /scores/{symbol}
# to prevent FastAPI matching "summary" as a symbol path parameter.
@router.get("/scores/summary/distribution", summary="Score distribution histogram")
async def score_distribution(
    repo: ScoreRepoDep,
    timeframe: str = Query(default="1d", pattern="^1d$"),
    buckets:   int = Query(default=10, ge=2, le=20),
):
    return await repo.get_distribution(timeframe, buckets)


@router.get("/scores/{symbol}", summary="Full score breakdown for a symbol")
async def get_symbol_score(symbol: str, repo: ScoreRepoDep):
    rows = await repo.get_for_symbol(symbol.upper())
    if not rows:
        raise HTTPException(404, f"No scores found for '{symbol}' — run /scores/compute first")
    return rows
