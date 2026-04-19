from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from ._ws_connection import run_feed_loop

_QUEUE_MAXSIZE = 100_000


class DhanWebSocketClient:
    """Wraps dhanhq.marketfeed.DhanFeed for a single WebSocket connection."""

    def __init__(
        self,
        client_id:         str,
        token_getter:      Callable[[], Awaitable[str]],
        instruments:       list[tuple[str, str, int]],
        reconnect_delay_s: float = 5.0,
    ) -> None:
        self._client_id         = client_id
        self._token_getter      = token_getter
        self._instruments       = instruments
        self._reconnect_delay_s = reconnect_delay_s
        self._queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._running = False
        self.connected = asyncio.Event()

    @property
    def queue(self) -> asyncio.Queue[dict]:
        return self._queue

    async def run(self) -> None:
        """Connect and receive ticks indefinitely. Reconnects on any error."""
        self._running = True
        try:
            await run_feed_loop(
                client_id         = self._client_id,
                token_getter      = self._token_getter,
                instruments       = self._instruments,
                reconnect_delay_s = self._reconnect_delay_s,
                queue             = self._queue,
                connected         = self.connected,
                is_running        = lambda: self._running,
            )
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
