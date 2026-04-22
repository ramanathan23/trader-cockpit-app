import asyncio
import json
import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import StreamingResponse

from .deps import ScoreRepoDep, ScoreServiceDep
from ._config_routes import router as _config_router

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/scores/compute", summary="Trigger unified daily scoring (background)")
async def trigger_compute(
    background_tasks: BackgroundTasks,
    svc: ScoreServiceDep,
):
    background_tasks.add_task(svc.compute_unified)
    return {"status": "started", "scorer": "unified"}


@router.post("/scores/compute-sse", summary="Unified daily scoring: streams SSE progress until complete (use for pipeline UI)")
async def trigger_compute_sse(svc: ScoreServiceDep):
    async def generate():
        yield f"data: {json.dumps({'status': 'running', 'message': 'Scoring started…'})}\n\n"
        task = asyncio.create_task(svc.compute_unified())
        elapsed = 0
        while not task.done():
            await asyncio.sleep(3)
            elapsed += 3
            yield f"data: {json.dumps({'status': 'running', 'message': f'Scoring symbols… {elapsed}s'})}\n\n"
        try:
            count = task.result()
            yield f"data: {json.dumps({'status': 'ok', 'message': f'Scored {count} symbols'})}\n\n"
        except Exception as exc:
            logger.exception("compute_sse task failed")
            yield f"data: {json.dumps({'status': 'error', 'message': str(exc) or type(exc).__name__})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Dashboard endpoints ───────────────────────────────────────────────────────

@router.get("/dashboard", summary="Scoring dashboard: stats + scored symbols")
async def get_dashboard(
    repo: ScoreRepoDep,
    score_date: date | None = Query(default=None, description="YYYY-MM-DD, latest if omitted"),
    limit: int = Query(default=50, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    watchlist_only: bool = Query(default=False),
    segment: str | None = Query(default=None, pattern="^(fno|equity)$", description="fno | equity — omit for all"),
    balanced: bool = Query(default=True, description="Return top N per bucket (bull/bear × fno/equity)"),
):
    is_fno: bool | None = None
    if segment == "fno":
        is_fno = True
    elif segment == "equity":
        is_fno = False

    stats = await repo.get_dashboard_stats(score_date)

    if balanced and segment is None and offset == 0:
        scores = await repo.get_daily_scores_balanced(score_date, limit, watchlist_only)
    else:
        scores = await repo.get_daily_scores(score_date, limit, watchlist_only, is_fno, offset)

    return {
        "stats": stats,
        "scores": scores,
        "offset": offset,
        "limit": limit,
        "has_more": len(scores) == limit,
    }


@router.get("/dashboard/watchlist", summary="Current watchlist symbols for live feed subscription")
async def get_watchlist(
    repo: ScoreRepoDep,
    score_date: date | None = Query(default=None),
):
    symbols = await repo.get_watchlist_symbols(score_date)
    return {"count": len(symbols), "symbols": symbols}


# ── Watchlist patterns ────────────────────────────────────────────────────────

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


router.include_router(_config_router)
