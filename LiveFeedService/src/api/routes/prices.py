from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..deps import PublisherDep
from ._signals_sse import _open_signal_pubsub

logger = logging.getLogger(__name__)
router = APIRouter()
_CHANNEL = "prices"
_KEEPALIVE_S = 25


async def price_sse_generator(publisher, request: Request):
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
            logger.warning("price SSE reader task crashed: %s", exc)

    reader_task = asyncio.create_task(_redis_reader())
    try:
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


@router.get("/prices/stream", summary="SSE stream of live price ticks")
async def price_stream(request: Request, publisher: PublisherDep):
    return StreamingResponse(
        price_sse_generator(publisher, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
