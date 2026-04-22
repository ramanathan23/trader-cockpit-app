import logging
from datetime import datetime, time as _time, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Query

from .deps import PriceRepoDep, SymbolRepoDep, SyncServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()

_IST = timezone(timedelta(hours=5, minutes=30))
_MARKET_OPEN_H  = 9
_MARKET_OPEN_M  = 15
_MARKET_CLOSE_H = 15
_MARKET_CLOSE_M = 30
# During market hours: flag if no 1-min data in last 30 min; otherwise 1 day
_INTRADAY_STALE_MIN = 30
_OVERNIGHT_STALE_H  = 26  # covers weekend gap


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


@router.get("/data-quality/1min", summary="Staleness check on price_data_1min per symbol")
async def data_quality_1min(repo: PriceRepoDep, symbol_repo: SymbolRepoDep):
    """
    Returns stale/missing symbols for price_data_1min.
    During market hours (9:15–15:30 IST): stale = no data in last 30 min.
    Outside market hours: stale = no data in last 26 hours.
    """
    mapped = await symbol_repo.list_mapped()
    symbols = [r["symbol"] for r in mapped]
    if not symbols:
        return {"ok_count": 0, "stale": [], "missing": [], "checked_at": datetime.now(timezone.utc).isoformat()}

    last_ts_map = await repo.get_last_data_ts_bulk(symbols, "1m")

    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(_IST)
    ist_time = now_ist.time()
    market_open  = _time(_MARKET_OPEN_H,  _MARKET_OPEN_M)
    market_close = _time(_MARKET_CLOSE_H, _MARKET_CLOSE_M)
    in_market = market_open <= ist_time <= market_close

    stale_threshold = timedelta(minutes=_INTRADAY_STALE_MIN if in_market else 60 * _OVERNIGHT_STALE_H)

    stale: list[dict] = []
    missing: list[str] = []
    ok: list[str] = []

    for sym in symbols:
        ts = last_ts_map.get(sym)
        if ts is None:
            missing.append(sym)
        elif (now_utc - ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else now_utc - ts) > stale_threshold:
            gap = now_utc - (ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts)
            stale.append({
                "symbol":      sym,
                "last_data":   ts.isoformat(),
                "gap_minutes": round(gap.total_seconds() / 60, 1),
            })
        else:
            ok.append(sym)

    return {
        "checked_at":   now_utc.isoformat(),
        "in_market":    in_market,
        "stale_count":  len(stale),
        "missing_count": len(missing),
        "ok_count":     len(ok),
        "stale":        sorted(stale, key=lambda x: x["gap_minutes"], reverse=True),
        "missing":      missing,
    }
