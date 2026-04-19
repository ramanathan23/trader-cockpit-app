import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from .deps import SyncStateRepoDep, SyncServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sync/run",
             summary="Unified sync: auto-classifies each symbol and fills gaps (background)")
async def run_sync(background_tasks: BackgroundTasks, svc: SyncServiceDep):
    background_tasks.add_task(svc.run_sync)
    return {
        "status": "started",
        "message": "Sync running in background. Monitor progress at GET /api/v1/sync/status",
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


@router.get("/sync/gaps",
            summary="Per-symbol gap classification report (no data fetched)")
async def gap_report(svc: SyncServiceDep):
    return await svc.get_gap_report()
