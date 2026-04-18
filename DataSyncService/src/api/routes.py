import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from .deps import PriceRepoDep, SymbolRepoDep, SyncStateRepoDep, SyncServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", summary="Liveness check")
async def health():
    return {"status": "ok", "service": "DataSyncService"}


# ── Symbols ───────────────────────────────────────────────────────────────────

@router.post("/symbols/load", summary="Load/refresh symbols from CSV into DB")
async def load_symbols(svc: SyncServiceDep):
    count = await svc.bootstrap_symbols()
    return {"symbols_loaded": count}


@router.post("/symbols/refresh-master", summary="Re-download Dhan security master CSV and sync security IDs")
async def refresh_security_master(svc: SyncServiceDep):
    result = await svc.refresh_security_master()
    return {
        "equities_matched":        result.equities_matched,
        "equities_unmatched":      result.equities_unmatched,
        "index_futures_upserted":  result.index_futures_upserted,
        "index_futures_activated": result.index_futures_activated,
    }


@router.get("/symbols/dhan-status", summary="Dhan security ID mapping coverage")
async def dhan_mapping_status(repo: SymbolRepoDep):
    return await repo.get_dhan_mapping_stats()


@router.get("/symbols", summary="List symbols")
async def list_symbols(repo: SymbolRepoDep, series: str = "EQ"):
    return await repo.list_by_series(series)


# ── Sync ──────────────────────────────────────────────────────────────────────

@router.post("/sync/run", summary="Unified sync: auto-classifies each symbol and fills gaps (background)")
async def run_sync(background_tasks: BackgroundTasks, svc: SyncServiceDep):
    """
    Single entry point for all sync work.  Per symbol it will:
    - Pull full history if no data exists  (5yr daily)
    - Fill the gap from last price timestamp if data is stale
    - Skip if already up-to-date
    """
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


@router.get("/sync/gaps", summary="Per-symbol gap classification report (no data fetched)")
async def gap_report(svc: SyncServiceDep):
    """
    Dry-run: shows which symbols need work and why.
    Fields per symbol:
      1d.action → INITIAL | FETCH_TODAY | FETCH_GAP | SKIP
    """
    return await svc.get_gap_report()


# ── Prices ────────────────────────────────────────────────────────────────────

@router.get("/prices/{symbol}/daily", summary="Query daily OHLCV")
async def get_daily_prices(
    symbol: str,
    repo: PriceRepoDep,
    limit: int = Query(default=365, le=3650),
    from_ts: str | None = Query(default=None, description="ISO-8601 start timestamp"),
    to_ts:   str | None = Query(default=None, description="ISO-8601 end timestamp"),
):
    return await repo.get_ohlcv(symbol.upper(), "1d", limit=limit, from_ts=from_ts, to_ts=to_ts)


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.post("/metrics/recompute", summary="Recompute symbol_metrics from price_data_daily")
async def recompute_metrics(background_tasks: BackgroundTasks, svc: SyncServiceDep):
    """
    Triggers a full recompute of the symbol_metrics table from price_data_daily.
    Normally this runs automatically after each EOD sync; use this endpoint to
    force a refresh (e.g. after a manual data backfill).
    """
    background_tasks.add_task(svc.recompute_metrics)
    return {"status": "started", "message": "Metrics recompute running in background."}


