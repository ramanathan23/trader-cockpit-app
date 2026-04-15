"""
LiveFeedService API routes.

GET  /api/v1/status          — feed health, instrument count, index bias
POST /api/v1/token           — update Dhan access token + reconnect feeds
GET  /api/v1/signals/stream  — SSE stream of Signal events
GET  /api/v1/ui              — serve index.html (trading dashboard)
"""

import asyncio
import json
import logging
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from .deps import FeedServiceDep, PublisherDep

logger    = logging.getLogger(__name__)
router    = APIRouter()
_UI_FILE  = Path(__file__).parent.parent / "ui" / "index.html"
_JS_FILE  = Path(__file__).parent.parent / "ui" / "cockpit.js"
_CHANNEL  = "signals"
_KEEPALIVE_S = 25   # send a SSE comment every N seconds to keep connection alive


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status", summary="Feed health and index bias")
async def status(svc: FeedServiceDep):
    return svc.status()


# ── Token hot-reload ──────────────────────────────────────────────────────────

class TokenUpdate(BaseModel):
    access_token: str


@router.post("/token", summary="Update Dhan access token and reconnect WebSocket feeds")
async def update_token(body: TokenUpdate, svc: FeedServiceDep):
    """
    Persist a new Dhan access token to Redis and immediately reconnect all
    WebSocket feeds so the new token is used without restarting the service.

    Call this every morning after generating a fresh Dhan token.
    """
    await svc.update_token(body.access_token)
    return {"status": "ok", "message": "Token updated and WebSocket feeds reconnecting"}


# ── SSE Signal Stream ─────────────────────────────────────────────────────────

@router.get("/signals/stream", summary="SSE stream of trading signals")
async def signal_stream(request: Request, publisher: PublisherDep):
    """
    Server-Sent Events endpoint.

    On connect:
      - Replays recent signals (catch-up) so the UI is not blank.
      - Then streams new signals in real-time from Redis pub/sub.

    SSE format:   data: {json}\n\n
    Keep-alive:   : ping\n\n  (every 25 s)
    """
    redis_url = request.app.state.pool   # we store redis url via publisher
    # We create a fresh pub/sub connection per SSE client so they are independent.

    async def event_generator():
        # 1. Catch-up: replay recent signals from Redis history.
        for sig_dict in await publisher.recent_signals():
            yield f"data: {json.dumps(sig_dict)}\n\n"

        # 2. Subscribe to live signals.
        redis_client = aioredis.from_url(
            request.app.state.publisher._url,
            encoding         = "utf-8",
            decode_responses = True,
        )
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(_CHANNEL)

        try:
            keepalive_task = asyncio.create_task(_keepalive_ticker())
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                else:
                    # Check for keepalive tick.
                    try:
                        keepalive_task.result()   # raises if done
                        keepalive_task = asyncio.create_task(_keepalive_ticker())
                        yield ": ping\n\n"
                    except (asyncio.InvalidStateError, asyncio.CancelledError):
                        pass
        finally:
            keepalive_task.cancel()
            await pubsub.unsubscribe(_CHANNEL)
            await redis_client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type = "text/event-stream",
        headers    = {
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )


# ── Instrument metrics ────────────────────────────────────────────────────────

@router.get("/instrument/{symbol}/metrics", summary="52-week stats, ATR-14, today's range")
async def instrument_metrics(symbol: str, request: Request):
    """
    Daily metrics (52wk H/L, ATR-14, ADV-20) come from MetricsService which
    precomputes them at startup — zero DB cost per call.
    Intraday range (day_high/low/open) is fetched from candles_3min with a
    60-second TTL cache inside MetricsService.
    """
    data = await request.app.state.metrics.get_with_intraday(symbol)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No daily data for {symbol}")
    return data


# ── Watchlist screener — all instruments with daily metrics ───────────────────

@router.get("/screener", summary="All instruments with pre-computed daily metrics for screening")
async def screener(request: Request, svc: FeedServiceDep):
    """
    Returns every tracked instrument with its pre-computed daily metrics
    (ADV-20, ATR-14, EMAs, weekly breadth, 52-week H/L, prev day/week/month
    H/L/C) from the in-memory MetricsService cache.

    The response is also enriched with live session fields where available:
    current price and session VWAP (DVWAP), both sourced from the running
    feed pipeline instead of the database.
    """
    rows = request.app.state.metrics.all_daily()
    live = svc.screener_live_metrics()
    merged = [{**row, **live.get(row["symbol"], {})} for row in rows]
    return {"count": len(merged), "symbols": merged}


# ── Signal history (daily review) ────────────────────────────────────────────

import re as _re

@router.get("/signals/history", summary="All signals for a given IST date")
async def signal_history(date: str, publisher: PublisherDep):
    """
    Returns signals recorded on a given IST date (format: YYYY-MM-DD).
    Data is kept for 7 days. Signals are in chronological order (oldest first).
    Also returns the list of dates that have data available.
    """
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    signals = await publisher.signals_for_date(date)
    dates   = await publisher.available_dates()
    return {"date": date, "count": len(signals), "signals": signals, "available_dates": dates}


@router.get("/signals/history/dates", summary="IST dates with saved signal history")
async def signal_history_dates(publisher: PublisherDep):
    dates = await publisher.available_dates()
    return {"dates": dates}


# ── UI ────────────────────────────────────────────────────────────────────────

@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui():
    return HTMLResponse(_UI_FILE.read_text(encoding="utf-8"))


@router.get("/ui/cockpit.js", include_in_schema=False)
async def serve_cockpit_js():
    return PlainTextResponse(
        _JS_FILE.read_text(encoding="utf-8"),
        media_type="application/javascript",
    )


# ── Helper ────────────────────────────────────────────────────────────────────

async def _keepalive_ticker():
    await asyncio.sleep(_KEEPALIVE_S)
