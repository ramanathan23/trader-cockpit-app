from __future__ import annotations

import asyncio


async def drain_queue(source: asyncio.Queue[dict], dest: asyncio.Queue[dict]) -> None:
    """Forward ticks from a client queue to the merged tick_queue."""
    while True:
        tick = await source.get()
        try:
            dest.put_nowait(tick)
        except asyncio.QueueFull:
            try:
                dest.get_nowait()
                dest.put_nowait(tick)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass
