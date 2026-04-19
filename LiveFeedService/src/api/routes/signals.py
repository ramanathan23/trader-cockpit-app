import re

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket
from fastapi.responses import StreamingResponse

from ..deps import PublisherDep
from ._signals_sse import sse_event_generator
from ._signals_ws import ws_session

router = APIRouter()
_CHANNEL = "signals"


@router.get("/signals/stream", summary="SSE stream of trading signals")
async def signal_stream(request: Request, publisher: PublisherDep):
    return StreamingResponse(
        sse_event_generator(publisher, request, _CHANNEL),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.websocket("/signals/ws")
async def signal_websocket(websocket: WebSocket, publisher: PublisherDep):
    await ws_session(websocket, publisher, _CHANNEL)


@router.get("/signals/history", summary="All signals for a given IST date")
async def signal_history(
    date: str,
    publisher: PublisherDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    signals, total = await publisher.signals_for_date(date, offset, limit)
    dates = await publisher.available_dates()
    return {
        "date": date, "count": len(signals), "total": total,
        "offset": offset, "limit": limit,
        "has_more": offset + len(signals) < total,
        "signals": signals,
        "available_dates": dates,
    }


@router.get("/signals/history/dates", summary="IST dates with saved signal history")
async def signal_history_dates(publisher: PublisherDep):
    dates = await publisher.available_dates()
    return {"dates": dates}
