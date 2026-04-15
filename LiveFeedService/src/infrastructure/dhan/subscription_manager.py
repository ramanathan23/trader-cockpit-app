"""
SubscriptionManager: chunks 2000+ instruments into batches and manages
one DhanWebSocketClient per batch.

Dhan limit: 1000 instruments per WebSocket connection.

All index future instruments are pinned to the last connection (connection N)
so their ticks always arrive on a dedicated, predictable connection.

On startup:
  1. receive full instrument list
  2. split equities into batches of WS_BATCH_SIZE
  3. append index futures to the last batch (or a new connection if needed)
  4. start one DhanWebSocketClient per batch
  5. merge all queues into a single shared output queue via drain tasks
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Sequence

from dhanhq import marketfeed as mf

from ...domain.models import InstrumentMeta
from .websocket_client import DhanWebSocketClient

logger = logging.getLogger(__name__)

WS_BATCH_SIZE = 1000   # Dhan per-connection instrument limit


def _to_dhan_instrument(meta: InstrumentMeta) -> tuple[str, str, int]:
    """Convert InstrumentMeta to the (exchange_segment, security_id, sub_type) tuple."""
    # Quote mode includes LTQ, which we need to build non-zero candle volume.
    sub_type = mf.Quote
    exchange_segment = _normalise_exchange_segment(meta)
    return (exchange_segment, str(meta.dhan_security_id), sub_type)


def _normalise_exchange_segment(meta: InstrumentMeta) -> str:
    segment = meta.exchange_segment.strip().upper()

    if segment in {"NSE_EQ", "NSE_FNO", "BSE_EQ", "BSE_FNO", "IDX_I"}:
        return segment

    if segment == "E":
        return "NSE_EQ"

    if segment == "D":
        if meta.is_index_future and meta.underlying == "SENSEX":
            return "BSE_FNO"
        return "NSE_FNO"

    logger.warning(
        "Unknown exchange segment '%s' for %s; passing through unchanged",
        meta.exchange_segment,
        meta.symbol,
    )
    return meta.exchange_segment


class SubscriptionManager:
    """
    Manages multiple Dhan WebSocket connections for the full instrument universe.

    Parameters
    ----------
    equities       : all equity InstrumentMeta records with dhan_security_id set
    index_futures  : index future InstrumentMeta records (market proxy)
    client_id      : Dhan client ID
    access_token   : Dhan access token
    reconnect_delay_s    : initial reconnect delay passed to each client
    batch_size           : instruments per WebSocket connection (default 1000)
    connection_stagger_s : seconds to wait between starting successive connections
                           to avoid simultaneous connect bursts that trigger HTTP 429
    """

    def __init__(
        self,
        equities:              list[InstrumentMeta],
        index_futures:         list[InstrumentMeta],
        client_id:             str,
        token_getter:          Callable[[], Awaitable[str]],
        reconnect_delay_s:     float = 5.0,
        batch_size:            int   = WS_BATCH_SIZE,
        connection_stagger_s:  float = 3.0,
    ) -> None:
        self._client_id              = client_id
        self._token_getter           = token_getter
        self._reconnect_delay_s      = reconnect_delay_s
        self._batch_size             = batch_size
        self._connection_stagger_s   = connection_stagger_s

        self._clients: list[DhanWebSocketClient] = []
        self._tasks:   list[asyncio.Task]         = []

        # Merged output queue — all ticks from all connections land here.
        self.tick_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=200_000)

        self._build_clients(equities, index_futures)

    # ── Public interface ───────────────────────────────────────────────────────

    async def start(self) -> None:
        """Launch WebSocket clients one by one, waiting for each to connect before starting the next."""
        for idx, client in enumerate(self._clients):
            drain_task = asyncio.create_task(
                self._drain(client.queue), name=f"dhan-drain-{idx}"
            )
            ws_task = asyncio.create_task(
                client.run(), name=f"dhan-ws-{idx}"
            )
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
        """
        Cancel all active WebSocket tasks and immediately restart them.

        The drain tasks are left running — they keep consuming from the per-client
        queues and will receive ticks again once the new connections are up.
        The fresh token is fetched by each client at the start of its run() loop,
        so this is how a token update takes effect without a service restart.
        """
        ws_tasks = [t for t in self._tasks if t.get_name().startswith("dhan-ws-")]
        for t in ws_tasks:
            t.cancel()
        await asyncio.gather(*ws_tasks, return_exceptions=True)

        self._tasks = [t for t in self._tasks if not t.get_name().startswith("dhan-ws-")]

        for idx, client in enumerate(self._clients):
            ws_task = asyncio.create_task(
                client.run(), name=f"dhan-ws-{idx}"
            )
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

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_clients(
        self,
        equities:      list[InstrumentMeta],
        index_futures: list[InstrumentMeta],
    ) -> None:
        # Split equities into batches.
        equity_batches: list[list[InstrumentMeta]] = []
        for i in range(0, len(equities), self._batch_size):
            equity_batches.append(equities[i: i + self._batch_size])

        if not equity_batches:
            equity_batches = [[]]

        # Append index futures to the last batch (they must always be subscribed
        # regardless of how many equity batches there are).
        remaining = self._batch_size - len(equity_batches[-1])
        if len(index_futures) <= remaining:
            equity_batches[-1].extend(index_futures)
        else:
            equity_batches.append(index_futures)

        for batch in equity_batches:
            instruments = [_to_dhan_instrument(m) for m in batch]
            client = DhanWebSocketClient(
                client_id         = self._client_id,
                token_getter      = self._token_getter,
                instruments       = instruments,
                reconnect_delay_s = self._reconnect_delay_s,
            )
            self._clients.append(client)

        total = sum(len(b) for b in equity_batches)
        logger.info(
            "SubscriptionManager: %d instruments across %d connection(s) "
            "(%d equities, %d index futures)",
            total, len(self._clients), len(equities), len(index_futures),
        )

    async def _delayed_run(self, client: DhanWebSocketClient, delay_s: float) -> None:
        """Sleep for delay_s then run the client (used to stagger connect attempts)."""
        if delay_s > 0:
            logger.debug("Staggering connection start by %.1fs", delay_s)
            await asyncio.sleep(delay_s)
        await client.run()

    async def _drain(self, source: asyncio.Queue[dict]) -> None:
        """Forward ticks from a client queue to the merged tick_queue."""
        while True:
            tick = await source.get()
            try:
                self.tick_queue.put_nowait(tick)
            except asyncio.QueueFull:
                try:
                    self.tick_queue.get_nowait()
                    self.tick_queue.put_nowait(tick)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
