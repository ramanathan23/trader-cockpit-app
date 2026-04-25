import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pathlib import Path
from pydantic import BaseModel, Field

from ..deps import FeedServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()
_LIVE_SESSION_PHASES = {
    "PRE_SIGNAL",
    "DRIVE_WINDOW",
    "EXECUTION",
    "TRANSITION",
    "MID_SESSION",
    "DEAD_ZONE",
    "CLOSE_MOMENTUM",
    "SESSION_END",
}

_UI_FILE = Path(__file__).parent.parent.parent / "ui" / "index.html"
_JS_FILE = Path(__file__).parent.parent.parent / "ui" / "cockpit.js"


class BatchMetricsRequest(BaseModel):
    symbols: List[str] = Field(..., max_length=3000)


@router.post("/instruments/metrics", summary="Batch metrics for multiple symbols")
async def batch_instrument_metrics(body: BatchMetricsRequest, request: Request, svc: FeedServiceDep):
    data = await request.app.state.metrics.get_batch_with_intraday(body.symbols)
    live = svc.live_price_metrics()
    for symbol, snapshot in live.items():
        if symbol not in data:
            continue
        current_price = snapshot.get("current_price")
        if current_price is None:
            continue
        prev_close = data[symbol].get("prev_day_close")
        data[symbol]["current_price"] = current_price
        data[symbol]["day_close"] = current_price
        if prev_close:
            data[symbol]["day_chg_pct"] = round((current_price - prev_close) / prev_close * 100, 2)
    daily_refs = await request.app.state.metrics.get_daily_reference_closes(body.symbols)
    phase = svc.current_session_phase()
    is_live_session = phase in _LIVE_SESSION_PHASES
    for symbol, refs in daily_refs.items():
        if symbol not in data:
            continue
        latest_close = refs.get("latest_close")
        previous_close = refs.get("previous_close")
        has_live_price = data[symbol].get("current_price") is not None
        price = data[symbol].get("current_price") if is_live_session and has_live_price else latest_close
        if is_live_session and has_live_price:
            reference_close = latest_close or previous_close
        elif previous_close:
            reference_close = previous_close
        else:
            reference_close = latest_close
        if price is None or not reference_close:
            continue
        data[symbol]["prev_day_close"] = reference_close
        data[symbol]["day_close"] = price
        if not is_live_session:
            data[symbol].pop("current_price", None)
        data[symbol]["day_chg_pct"] = round((price - reference_close) / reference_close * 100, 2)
    return data


@router.get("/instrument/{symbol}/metrics", summary="52-week stats, ATR-14, today's range")
async def instrument_metrics(symbol: str, request: Request):
    data = await request.app.state.metrics.get_with_intraday(symbol)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No daily data for {symbol}")
    return data


@router.get("/screener", summary="All instruments with pre-computed daily metrics for screening")
async def screener(
    request: Request,
    svc: FeedServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=2000),
):
    rows, total = request.app.state.metrics.all_daily(offset, limit)
    live = svc.screener_live_metrics()
    merged = [{**row, **live.get(row["symbol"], {})} for row in rows]
    return {
        "count": len(merged),
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(merged) < total,
        "symbols": merged,
    }


@router.get("/chart/{symbol}/daily", summary="Daily OHLCV for TradingView chart")
async def chart_daily(
    symbol: str,
    request: Request,
    days: int = Query(default=365, ge=30, le=3650),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT time, open, high, low, close, volume
            FROM price_data_daily
            WHERE symbol = $1
            ORDER BY time DESC
            LIMIT $2
        """, symbol.upper(), days)

    if not rows:
        raise HTTPException(404, f"No daily data for {symbol}")

    candles = [
        {
            "time": r["time"].strftime("%Y-%m-%d"),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": int(r["volume"]) if r["volume"] else 0,
        }
        for r in reversed(rows)
    ]
    return {"symbol": symbol.upper(), "count": len(candles), "candles": candles}


@router.get("/chart/{symbol}/intraday", summary="Intraday OHLCV with optional server-side resampling")
async def chart_intraday(
    symbol: str,
    request: Request,
    tf: int = Query(default=1, ge=1, le=60, description="Timeframe in minutes"),
    bars: int = Query(default=33750, ge=30, le=40000, description="Number of output bars"),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if tf == 1:
            rows = await conn.fetch("""
                SELECT time, open, high, low, close, volume
                FROM price_data_1min
                WHERE symbol = $1
                ORDER BY time DESC
                LIMIT $2
            """, symbol.upper(), bars)
        else:
            rows = await conn.fetch("""
                SELECT
                    time_bucket(make_interval(mins => $1), time) AS time,
                    first(open, time)  AS open,
                    max(high)          AS high,
                    min(low)           AS low,
                    last(close, time)  AS close,
                    sum(volume)        AS volume
                FROM price_data_1min
                WHERE symbol = $2
                GROUP BY 1
                ORDER BY 1 DESC
                LIMIT $3
            """, tf, symbol.upper(), bars)

    if not rows:
        raise HTTPException(404, f"No intraday data for {symbol}")

    candles = [
        {
            "time":   int(r["time"].timestamp()),
            "open":   float(r["open"]),
            "high":   float(r["high"]),
            "low":    float(r["low"]),
            "close":  float(r["close"]),
            "volume": int(r["volume"]) if r["volume"] else 0,
        }
        for r in reversed(rows)
    ]
    return {"symbol": symbol.upper(), "tf": tf, "count": len(candles), "candles": candles}


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui():
    return HTMLResponse(_UI_FILE.read_text(encoding="utf-8"))


@router.get("/ui/cockpit.js", include_in_schema=False)
async def serve_cockpit_js():
    return PlainTextResponse(
        _JS_FILE.read_text(encoding="utf-8"),
        media_type="application/javascript",
    )
