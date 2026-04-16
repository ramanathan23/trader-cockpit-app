import asyncio
import json
import logging
import re

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from ..deps import PublisherDep

logger = logging.getLogger(__name__)
router = APIRouter()

_CHANNEL = "signals"
_KEEPALIVE_S = 25


def _open_signal_pubsub(redis_url: str):
    redis_client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    pubsub = redis_client.pubsub()
    return redis_client, pubsub


@router.get("/signals/stream", summary="SSE stream of trading signals")
async def signal_stream(request: Request, publisher: PublisherDep):
    async def event_generator():
        redis_client, pubsub = _open_signal_pubsub(publisher._url)
        await pubsub.subscribe(_CHANNEL)

        queue: asyncio.Queue[str] = asyncio.Queue()

        async def _redis_reader():
            try:
                async for msg in pubsub.listen():
                    if msg and msg["type"] == "message":
                        await queue.put(msg["data"])
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.warning("SSE reader task crashed: %s", exc)

        reader_task = asyncio.create_task(_redis_reader())

        try:
            for sig_dict in await publisher.recent_signals():
                if await request.is_disconnected():
                    return
                yield f"data: {json.dumps(sig_dict)}\n\n"

            keepalive_ticks = 0
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {data}\n\n"
                    keepalive_ticks = 0
                except asyncio.TimeoutError:
                    keepalive_ticks += 1
                    if keepalive_ticks >= _KEEPALIVE_S:
                        yield ": ping\n\n"
                        keepalive_ticks = 0
        finally:
            reader_task.cancel()
            await pubsub.unsubscribe(_CHANNEL)
            await redis_client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.websocket("/signals/ws")
async def signal_websocket(websocket: WebSocket, publisher: PublisherDep):
    await websocket.accept()

    redis_client, pubsub = _open_signal_pubsub(publisher._url)
    await pubsub.subscribe(_CHANNEL)

    queue: asyncio.Queue[str] = asyncio.Queue()
    disconnected = asyncio.Event()

    async def _redis_reader():
        try:
            async for msg in pubsub.listen():
                if msg and msg["type"] == "message":
                    await queue.put(msg["data"])
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("WebSocket reader task crashed: %s", exc)

    async def _disconnect_watcher():
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            disconnected.set()
        except RuntimeError:
            disconnected.set()

    reader_task = asyncio.create_task(_redis_reader())
    disconnect_task = asyncio.create_task(_disconnect_watcher())

    try:
        for sig_dict in await publisher.recent_signals():
            if disconnected.is_set():
                return
            await websocket.send_text(json.dumps(sig_dict))

        while not disconnected.is_set():
            try:
                data = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_text(data)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        reader_task.cancel()
        disconnect_task.cancel()
        await pubsub.unsubscribe(_CHANNEL)
        await redis_client.aclose()


@router.get("/signals/history", summary="All signals for a given IST date")
async def signal_history(date: str, publisher: PublisherDep):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    signals = await publisher.signals_for_date(date)
    dates = await publisher.available_dates()
    return {"date": date, "count": len(signals), "signals": signals, "available_dates": dates}


@router.get("/signals/history/dates", summary="IST dates with saved signal history")
async def signal_history_dates(publisher: PublisherDep):
    dates = await publisher.available_dates()
    return {"dates": dates}
