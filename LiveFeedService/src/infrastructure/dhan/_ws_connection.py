from __future__ import annotations

import asyncio
import logging
import random
from typing import Awaitable, Callable

from dhanhq import DhanContext, MarketFeed

logger = logging.getLogger(__name__)

_MIN_RECONNECT_S = 2.0
_MAX_RECONNECT_S = 120.0
_429_MIN_DELAY_S = 60.0


async def run_feed_loop(
    client_id:         str,
    token_getter:      Callable[[], Awaitable[str]],
    instruments:       list[tuple[str, str, int]],
    reconnect_delay_s: float,
    queue:             asyncio.Queue[dict],
    connected:         asyncio.Event,
    is_running:        Callable[[], bool],
) -> None:
    """Run the DhanFeed connect-receive loop with automatic reconnect."""
    delay = reconnect_delay_s
    while is_running():
        try:
            access_token = await token_getter()
            logger.info("Connecting to Dhan feed (%d instruments)…", len(instruments))
            context = DhanContext(client_id=client_id, access_token=access_token)
            feed = MarketFeed(
                dhan_context = context,
                instruments  = instruments,
                version      = "v2",
            )
            await feed.connect()
            logger.info("Dhan feed connected — receiving ticks")
            connected.set()
            delay = reconnect_delay_s
            while is_running():
                data = await feed.get_instrument_data()
                if data:
                    _push_tick(data, queue)
        except asyncio.CancelledError:
            connected.clear()
            logger.info("Dhan WebSocket client cancelled")
            raise
        except Exception as exc:
            connected.clear()
            is_rate_limited = "429" in str(exc)
            if is_rate_limited:
                delay = max(delay, _429_MIN_DELAY_S)
            jitter = delay * 0.20 * (2.0 * random.random() - 1.0)
            effective_delay = delay + jitter
            logger.warning(
                "Dhan feed error: %s — reconnecting in %.0fs%s",
                exc, effective_delay,
                " (rate-limited, backing off)" if is_rate_limited else "",
            )
            await asyncio.sleep(effective_delay)
            delay = min(delay * 2, _MAX_RECONNECT_S)


def _push_tick(data: dict, queue: asyncio.Queue[dict]) -> None:
    if not isinstance(data, dict):
        logger.warning("Unexpected tick type %s — sample: %s", type(data).__name__, repr(data)[:200])
        return
    try:
        queue.put_nowait(data)
    except asyncio.QueueFull:
        try:
            queue.get_nowait()
            queue.put_nowait(data)
        except (asyncio.QueueEmpty, asyncio.QueueFull):
            pass
        logger.warning("Tick queue full — oldest tick dropped")
