"""
SignalPublisher: publishes Signal objects to Redis pub/sub and maintains
a capped recent-signals list for new SSE subscribers catching up.

Channels
--------
  signals          — every signal (all symbols)
  signals:{symbol} — per-symbol channel for focused subscriptions

Recency cache
-------------
  The last RECENCY_MAX signals are stored in memory so that a new SSE client
  can immediately receive recent context without waiting for the next candle.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque

import redis.asyncio as aioredis

from ...domain.models import Signal

logger = logging.getLogger(__name__)

_CHANNEL_ALL    = "signals"
_CHANNEL_PREFIX = "signals:"
RECENCY_MAX     = 50   # signals kept in memory for new subscribers


class SignalPublisher:
    """
    Async Redis pub/sub publisher.

    Usage
    -----
    publisher = SignalPublisher(redis_url)
    await publisher.connect()
    await publisher.publish(signal)
    await publisher.close()
    """

    def __init__(self, redis_url: str) -> None:
        self._url    = redis_url
        self._redis: aioredis.Redis | None = None
        self._recent: deque[dict] = deque(maxlen=RECENCY_MAX)

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            self._url,
            encoding        = "utf-8",
            decode_responses = True,
        )
        await self._redis.ping()
        logger.info("SignalPublisher connected to Redis at %s", self._url)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    async def publish(self, signal: Signal) -> None:
        """Publish a signal to Redis and append to recency cache."""
        if self._redis is None:
            raise RuntimeError("SignalPublisher not connected — call connect() first")

        payload = json.dumps(signal.to_dict())
        self._recent.append(signal.to_dict())

        await asyncio.gather(
            self._redis.publish(_CHANNEL_ALL, payload),
            self._redis.publish(f"{_CHANNEL_PREFIX}{signal.symbol}", payload),
        )

    def recent_signals(self) -> list[dict]:
        """Return recent signals for SSE catch-up (newest last)."""
        return list(self._recent)
