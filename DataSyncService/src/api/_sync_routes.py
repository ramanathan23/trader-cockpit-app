import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse

from .deps import SyncStateRepoDep, SyncServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/sync/run",
             summary="Daily sync: auto-classifies each symbol and fills gaps (background)")
async def run_sync(background_tasks: BackgroundTasks, svc: SyncServiceDep):
    background_tasks.add_task(svc.run_sync)
    return {
        "status": "started",
        "message": "Daily sync running in background. Monitor at GET /api/v1/sync/status",
    }


@router.post("/sync/run-sse",
             summary="Daily sync: streams SSE progress until complete (use for pipeline UI)")
async def run_sync_sse(svc: SyncServiceDep):
    async def generate():
        yield _sse({"status": "running", "message": "Daily sync started"})
        task = asyncio.create_task(svc.run_sync())
        elapsed = 0
        while not task.done():
            await asyncio.sleep(3)
            elapsed += 3
            yield _sse({"status": "running", "message": f"Syncing daily data… {elapsed}s"})
        try:
            result = task.result()
            updated = result.get("1d", {}).get("updated", "?")
            yield _sse({"status": "ok", "message": f"Daily sync complete — {updated} symbols updated"})
        except Exception as exc:
            logger.exception("run_sync_sse task failed")
            yield _sse({"status": "error", "message": str(exc) or type(exc).__name__})

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/sync/run-1min",
             summary="1-min sync: fetch Dhan 1-min OHLCV for all F&O stocks (background)")
async def run_1min_sync(background_tasks: BackgroundTasks, svc: SyncServiceDep):
    background_tasks.add_task(svc.run_1min_sync)
    return {
        "status": "started",
        "message": "1-min F&O sync running in background. Monitor at GET /api/v1/sync/status",
    }


@router.post("/sync/run-1min-sse",
             summary="1-min sync: streams SSE progress until complete (use for pipeline UI)")
async def run_1min_sync_sse(svc: SyncServiceDep):
    async def generate():
        yield _sse({"status": "running", "message": "1-min sync started"})
        task = asyncio.create_task(svc.run_1min_sync())
        elapsed = 0
        while not task.done():
            await asyncio.sleep(3)
            elapsed += 3
            yield _sse({"status": "running", "message": f"Fetching 1-min data… {elapsed}s"})
        try:
            result = task.result()
            updated = result.get("1m", {}).get("updated", "?")
            yield _sse({"status": "ok", "message": f"1-min sync complete — {updated} symbols updated"})
        except Exception as exc:
            logger.exception("run_1min_sync_sse task failed")
            yield _sse({"status": "error", "message": str(exc) or type(exc).__name__})

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/sync/run-all",
             summary="Full sync: daily (yfinance) + 1-min Dhan in parallel (background)")
async def run_full_sync(background_tasks: BackgroundTasks, svc: SyncServiceDep):
    background_tasks.add_task(svc.run_full_sync)
    return {
        "status": "started",
        "message": (
            "Daily + 1-min sync running in parallel in background. "
            "Monitor at GET /api/v1/sync/status"
        ),
    }


@router.get("/sync/status", summary="Overall sync status per interval")
async def sync_status(repo: SyncStateRepoDep):
    return await repo.get_summary()


@router.get("/sync/status/{symbol}", summary="Sync status for a specific symbol")
async def symbol_sync_status(symbol: str, repo: SyncStateRepoDep):
    rows = await repo.get_for_symbol(symbol.upper())
    if not rows:
        raise HTTPException(404, f"No sync state found for symbol '{symbol}'")
    return rows


@router.post("/sync/reset-1min",
             summary="Wipe price_data_1min and reset sync_state — forces full 90-day re-fetch")
async def reset_1min(request: Request):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE price_data_1min")
        await conn.execute("DELETE FROM sync_state WHERE timeframe = '1m'")
    logger.info("[1m] Reset complete — price_data_1min truncated, sync_state cleared")
    return {
        "status": "reset",
        "message": "price_data_1min truncated and 1m sync_state cleared. Run sync-1min to re-fetch.",
    }


@router.get("/sync/gaps",
            summary="Per-symbol gap classification report (no data fetched)")
async def gap_report(svc: SyncServiceDep):
    return await svc.get_gap_report()
