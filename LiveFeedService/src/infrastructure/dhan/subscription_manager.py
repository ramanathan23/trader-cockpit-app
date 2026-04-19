from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from ...domain.instrument_meta import InstrumentMeta
from .websocket_client import DhanWebSocketClient
from ._batch_builder import build_dhan_clients
from ._drain_worker import drain_queue

logger = logging.getLogger(__name__)

WS_BATCH_SIZE = 1000


class SubscriptionManager:
    """Manages multiple Dhan WebSocket connections for the full instrument universe."""

    def __init__(
        self,
        equities:             list[InstrumentMeta],
        index_futures:        list[InstrumentMeta],
        client_id:            str,
        token_getter:         Callable[[], Awaitable[str]],
        reconnect_delay_s:    float = 5.0,
        batch_size:           int   = WS_BATCH_SIZE,
        connection_stagger_s: float = 3.0,
    ) -> None:
        self._client_id            = client_id
        self._token_getter         = token_getter
        self._reconnect_delay_s    = reconnect_delay_s
        self._batch_size           = batch_size
        self._connection_stagger_s = connection_stagger_s
        self._clients: list[DhanWebSocketClient] = []
        self._tasks:   list[asyncio.Task]         = []
        self.tick_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=200_000)
        self._clients = build_dhan_clients(
            equities, index_futures, client_id, token_getter,
            reconnect_delay_s, batch_size,
        )

    async def start(self) -> None:
        """Launch WebSocket clients; wait for each to connect before starting next."""
        for idx, client in enumerate(self._clients):
            drain_task = asyncio.create_task(
                drain_queue(client.queue, self.tick_queue), name=f"dhan-drain-{idx}"
            )
            ws_task = asyncio.create_task(client.run(), name=f"dhan-ws-{idx}")
            self._tasks.extend([ws_task, drain_task])
            logger.info(
                "SubscriptionManager: waiting for connection %d/%d to establish…",
                idx + 1, len(self._clients),
            )
            await client.connected.wait()
            logger.info(
                "SubscriptionManager: connection %d/%d established",
                idx + 1, len(self._clients),
            )
        logger.info(
            "SubscriptionManager: all %d WebSocket connection(s) established",
            len(self._clients),
        )

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("SubscriptionManager: all connections stopped")

    async def reconnect_all(self) -> None:
        """Cancel all WebSocket tasks and restart them (picks up new token)."""
        ws_tasks = [t for t in self._tasks if t.get_name().startswith("dhan-ws-")]
        for t in ws_tasks:
            t.cancel()
        await asyncio.gather(*ws_tasks, return_exceptions=True)
        self._tasks = [t for t in self._tasks if not t.get_name().startswith("dhan-ws-")]
        for idx, client in enumerate(self._clients):
            ws_task = asyncio.create_task(client.run(), name=f"dhan-ws-{idx}")
            self._tasks.append(ws_task)
            logger.info(
                "SubscriptionManager: waiting for connection %d/%d to re-establish…",
                idx + 1, len(self._clients),
            )
            await client.connected.wait()
            logger.info(
                "SubscriptionManager: connection %d/%d re-established",
                idx + 1, len(self._clients),
            )
        logger.info(
            "SubscriptionManager: all %d WebSocket connection(s) reconnected with fresh token",
            len(self._clients),
        )

    def connection_count(self) -> int:
        return len(self._clients)
