"""
DhanWebSocketClient: thin async wrapper around the dhanhq market feed.

Responsibilities:
  - Connect to Dhan's market feed WebSocket.
  - Subscribe a given list of (exchange_segment, security_id) pairs.
  - Push every received tick dict onto an asyncio.Queue.
  - Reconnect automatically on disconnect (with exponential back-off cap).
  - Expose a clean async context manager / run() interface.

The queue is the only coupling point to the rest of the service — callers read
from it at their own pace, providing natural back-pressure.  If the queue fills
(maxsize exceeded) the oldest tick is dropped with a warning rather than
blocking the receive loop (liveness > completeness for real-time feeds).

dhanhq v2 market feed modes
----------------------------
  marketfeed.Ticker  (1) — LTP, LTQ, LTT
  marketfeed.Quote   (2) — LTP, LTQ, LTT, OHLC, volume
  marketfeed.Full    (3) — everything incl. depth

We default to Ticker for equities (minimal bandwidth) and Quote for index
futures (we want daily OHLC as a cross-check).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Sequence

from dhanhq import marketfeed as mf

logger = logging.getLogger(__name__)

_QUEUE_MAXSIZE     = 100_000   # ~100 k ticks buffered before drops
_MIN_RECONNECT_S   = 2.0
_MAX_RECONNECT_S   = 60.0


class DhanWebSocketClient:
    """
    Wraps dhanhq.marketfeed.DhanFeed for a single WebSocket connection.

    Parameters
    ----------
    client_id         : Dhan client ID
    access_token      : Dhan access token
    instruments       : list of (exchange_segment_str, security_id_str, sub_type)
                        e.g. [("NSE_EQ", "1333", mf.Ticker), ...]
    reconnect_delay_s : initial reconnect wait (doubles on each failure, capped)
    """

    def __init__(
        self,
        client_id:         str,
        access_token:      str,
        instruments:       list[tuple[str, str, int]],
        reconnect_delay_s: float = 5.0,
    ) -> None:
        self._client_id         = client_id
        self._access_token      = access_token
        self._instruments       = instruments
        self._reconnect_delay_s = reconnect_delay_s
        self._queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._running = False

    # ── Public interface ───────────────────────────────────────────────────────

    @property
    def queue(self) -> asyncio.Queue[dict]:
        return self._queue

    async def run(self) -> None:
        """
        Connect and receive ticks indefinitely.  Reconnects on any error.
        Call this as an asyncio.Task and cancel() to stop.
        """
        self._running = True
        delay = self._reconnect_delay_s

        while self._running:
            try:
                logger.info(
                    "Connecting to Dhan feed (%d instruments)…",
                    len(self._instruments),
                )
                feed = mf.DhanFeed(
                    client_id    = self._client_id,
                    access_token = self._access_token,
                    instruments  = self._instruments,
                    version      = "v2",
                )
                await feed.connect()
                logger.info("Dhan feed connected — receiving ticks")
                delay = self._reconnect_delay_s   # reset on clean connect

                while self._running:
                    data = await feed.get_instrument_data()
                    if data:
                        self._on_ticks(data)

            except asyncio.CancelledError:
                logger.info("Dhan WebSocket client cancelled")
                break
            except Exception as exc:
                logger.warning(
                    "Dhan feed error: %s — reconnecting in %.0fs", exc, delay
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, _MAX_RECONNECT_S)

        self._running = False

    def stop(self) -> None:
        self._running = False

    # ── Private ───────────────────────────────────────────────────────────────

    def _on_ticks(self, data: dict) -> None:
        """
        Called by dhanhq on each incoming message.
        Pushes tick onto the queue; drops oldest if full.
        """
        if not isinstance(data, dict):
            logger.warning(
                "Unexpected tick type %s (expected dict) — sample: %s",
                type(data).__name__, repr(data)[:200],
            )
            return
        try:
            self._queue.put_nowait(data)
        except asyncio.QueueFull:
            # Drop oldest tick to keep the receive loop alive.
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(data)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass
            logger.warning("Tick queue full — oldest tick dropped")
