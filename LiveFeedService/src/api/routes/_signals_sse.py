from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import Request

logger = logging.getLogger(__name__)

_KEEPALIVE_S = 25


def _open_signal_pubsub(redis_url: str):
    rc = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    return rc, rc.pubsub()


async def sse_event_generator(publisher, request: Request, channel: str):
    redis_client, pubsub = _open_signal_pubsub(publisher._url)
    await pubsub.subscribe(channel)
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
        await pubsub.unsubscribe(channel)
        await redis_client.aclose()
