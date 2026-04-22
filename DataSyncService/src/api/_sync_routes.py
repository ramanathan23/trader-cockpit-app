import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from .deps import SyncStateRepoDep, SyncServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sync/run",
             summary="Daily sync: auto-classifies each symbol and fills gaps (background)")
async def run_sync(background_tasks: BackgroundTasks, svc: SyncServiceDep):
    background_tasks.add_task(svc.run_sync)
    return {
        "status": "started",
        "message": "Daily sync running in background. Monitor at GET /api/v1/sync/status",
    }


@router.post("/sync/run-blocking",
             summary="Daily sync: blocks until complete (use for pipeline orchestration)")
async def run_sync_blocking(svc: SyncServiceDep):
    try:
        result = await svc.run_sync()
        updated = result.get("1d", {}).get("updated", "?")
        return {"status": "ok", "message": f"Daily sync complete — {updated} symbols updated"}
    except Exception as exc:
        logger.exception("run_sync_blocking failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sync/run-1min",
             summary="1-min sync: fetch Dhan 1-min OHLCV for all F&O stocks (background)")
async def run_1min_sync(background_tasks: BackgroundTasks, svc: SyncServiceDep):
    background_tasks.add_task(svc.run_1min_sync)
    return {
        "status": "started",
        "message": "1-min F&O sync running in background. Monitor at GET /api/v1/sync/status",
    }


@router.post("/sync/run-1min-blocking",
             summary="1-min sync: blocks until complete (use for pipeline orchestration)")
async def run_1min_sync_blocking(svc: SyncServiceDep):
    try:
        result = await svc.run_1min_sync()
        updated = result.get("1m", {}).get("updated", "?")
        return {"status": "ok", "message": f"1-min sync complete — {updated} symbols updated"}
    except Exception as exc:
        logger.exception("run_1min_sync_blocking failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
