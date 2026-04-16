import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pathlib import Path
from pydantic import BaseModel, Field

from ..deps import FeedServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()

_UI_FILE = Path(__file__).parent.parent.parent / "ui" / "index.html"
_JS_FILE = Path(__file__).parent.parent.parent / "ui" / "cockpit.js"


class BatchMetricsRequest(BaseModel):
    symbols: List[str] = Field(..., max_length=3000)


@router.post("/instruments/metrics", summary="Batch metrics for multiple symbols")
async def batch_instrument_metrics(body: BatchMetricsRequest, request: Request):
    data = await request.app.state.metrics.get_batch_with_intraday(body.symbols)
    return data


@router.get("/instrument/{symbol}/metrics", summary="52-week stats, ATR-14, today's range")
async def instrument_metrics(symbol: str, request: Request):
    data = await request.app.state.metrics.get_with_intraday(symbol)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No daily data for {symbol}")
    return data


@router.get("/screener", summary="All instruments with pre-computed daily metrics for screening")
async def screener(request: Request, svc: FeedServiceDep):
    rows = request.app.state.metrics.all_daily()
    live = svc.screener_live_metrics()
    merged = [{**row, **live.get(row["symbol"], {})} for row in rows]
    return {"count": len(merged), "symbols": merged}


@router.get("/chart/{symbol}/daily", summary="Daily OHLCV for TradingView chart")
async def chart_daily(
    symbol: str,
    request: Request,
    days: int = Query(default=365, ge=30, le=1825),
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


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui():
    return HTMLResponse(_UI_FILE.read_text(encoding="utf-8"))


@router.get("/ui/cockpit.js", include_in_schema=False)
async def serve_cockpit_js():
    return PlainTextResponse(
        _JS_FILE.read_text(encoding="utf-8"),
        media_type="application/javascript",
    )
