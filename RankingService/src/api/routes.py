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
    async def _run():
        count, msg = await svc.compute_unified()
        logger.info("Background score run: %s", msg)

    background_tasks.add_task(_run)
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
            count, msg = task.result()
            status = "ok" if count > 0 else "error"
            yield f"data: {json.dumps({'status': status, 'message': msg})}\n\n"
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
    balanced: bool = Query(default=True, description="Return top N per bucket (Stage2/Stage4 × fno/equity)"),
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


# ── Stage watchlist ───────────────────────────────────────────────────────────

@router.get("/watchlist/stage", summary="Stage 2 (bull) and Stage 4 (bear) watchlist ranked by total score")
async def get_stage_watchlist(
    svc: ScoreServiceDep,
    side: str = Query(default="both", pattern="^(bull|bear|both)$"),
    limit: int = Query(default=100, ge=1, le=500),
):
    return await svc.build_watchlist(stage=side, limit=limit)


router.include_router(_config_router)
