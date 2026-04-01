import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Symbols ───────────────────────────────────────────────────────────────────

@router.post("/symbols/load", summary="Load/refresh symbols from CSV into DB")
async def load_symbols(request: Request):
    count = await request.app.state.sync_service.bootstrap_symbols()
    return {"symbols_loaded": count}


@router.post("/symbols/refresh-master", summary="Re-download Dhan security master CSV")
async def refresh_security_master(request: Request):
    count = await request.app.state.sync_service._dhan.refresh_security_master()
    return {"symbols_mapped": count}


@router.get("/symbols", summary="List symbols")
async def list_symbols(request: Request, series: str = "EQ"):
    return await request.app.state.symbol_repo.list_by_series(series)


# ── Sync ──────────────────────────────────────────────────────────────────────

@router.post("/sync/initial", summary="Trigger full historical load (background)")
async def initial_sync(background_tasks: BackgroundTasks, request: Request):
    background_tasks.add_task(request.app.state.sync_service.run_initial_sync)
    return {
        "status": "started",
        "message": "Initial sync running in background. "
                   "Monitor progress at GET /api/v1/sync/status",
    }


@router.post("/sync/patch", summary="Trigger incremental patch sync (background)")
async def patch_sync(background_tasks: BackgroundTasks, request: Request):
    background_tasks.add_task(request.app.state.sync_service.run_patch_sync)
    return {"status": "started", "message": "Patch sync running in background"}


@router.get("/sync/status", summary="Overall sync status per interval")
async def sync_status(request: Request):
    return await request.app.state.sync_state_repo.get_summary()


@router.get("/sync/status/{symbol}", summary="Sync status for a specific symbol")
async def symbol_sync_status(symbol: str, request: Request):
    rows = await request.app.state.sync_state_repo.get_for_symbol(symbol.upper())
    if not rows:
        raise HTTPException(404, f"No sync state found for symbol '{symbol}'")
    return rows


# ── Prices ────────────────────────────────────────────────────────────────────

@router.get("/prices/{symbol}/1m", summary="Query 1-minute OHLCV")
async def get_1m_prices(
    symbol: str,
    request: Request,
    limit:   int      = Query(default=500, le=5000),
    from_ts: str | None = Query(default=None, description="ISO-8601 start timestamp"),
    to_ts:   str | None = Query(default=None, description="ISO-8601 end timestamp"),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT time, open, high, low, close, volume
            FROM price_data_1m
            WHERE symbol = $1
              AND ($2::timestamptz IS NULL OR time >= $2::timestamptz)
              AND ($3::timestamptz IS NULL OR time <= $3::timestamptz)
            ORDER BY time DESC
            LIMIT $4
        """, symbol.upper(), from_ts, to_ts, limit)
    return [dict(r) for r in rows]


@router.get("/prices/{symbol}/daily", summary="Query daily OHLCV")
async def get_daily_prices(
    symbol: str,
    request: Request,
    limit: int = Query(default=365, le=3650),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT time, open, high, low, close, volume
            FROM price_data_daily
            WHERE symbol = $1
            ORDER BY time DESC
            LIMIT $2
        """, symbol.upper(), limit)
    return [dict(r) for r in rows]


@router.get("/prices/{symbol}/hourly", summary="Query hourly aggregate")
async def get_hourly_prices(
    symbol: str,
    request: Request,
    limit: int = Query(default=168, le=2000),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT bucket AS time, open, high, low, close, volume
            FROM price_1m_hourly
            WHERE symbol = $1
            ORDER BY bucket DESC
            LIMIT $2
        """, symbol.upper(), limit)
    return [dict(r) for r in rows]
