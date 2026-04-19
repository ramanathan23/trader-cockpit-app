import logging

from fastapi import APIRouter, BackgroundTasks, Query

from .deps import PriceRepoDep, SyncServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/prices/{symbol}/daily", summary="Query daily OHLCV")
async def get_daily_prices(
    symbol: str,
    repo: PriceRepoDep,
    limit:   int          = Query(default=365, le=3650),
    from_ts: str | None   = Query(default=None, description="ISO-8601 start timestamp"),
    to_ts:   str | None   = Query(default=None, description="ISO-8601 end timestamp"),
):
    return await repo.get_ohlcv(
        symbol.upper(), "1d", limit=limit, from_ts=from_ts, to_ts=to_ts
    )


@router.post("/metrics/recompute",
             summary="Recompute symbol_metrics from price_data_daily")
async def recompute_metrics(background_tasks: BackgroundTasks, svc: SyncServiceDep):
    background_tasks.add_task(svc.recompute_metrics)
    return {"status": "started", "message": "Metrics recompute running in background."}
