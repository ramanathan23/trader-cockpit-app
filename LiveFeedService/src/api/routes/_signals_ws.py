from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from ._signals_sse import _open_signal_pubsub

logger = logging.getLogger(__name__)


async def ws_session(websocket: WebSocket, publisher, channel: str) -> None:
    """Handle one WebSocket client: replay history then stream live signals."""
    await websocket.accept()
    redis_client, pubsub = _open_signal_pubsub(publisher._url)
    await pubsub.subscribe(channel)
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

    reader_task     = asyncio.create_task(_redis_reader())
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
        await pubsub.unsubscribe(channel)
        await redis_client.aclose()
