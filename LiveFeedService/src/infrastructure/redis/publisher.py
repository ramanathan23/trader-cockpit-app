from __future__ import annotations

import datetime as _dt
import json
import logging

import redis.asyncio as aioredis

from ...domain.signal import Signal
from ._cluster_filter import cluster_check_signal
from ._history_ops import _HistoryOpsMixin, DAILY_TTL_S

logger = logging.getLogger(__name__)

_CHANNEL_ALL    = "signals"
_CHANNEL_PRICES = "prices"
_CHANNEL_PREFIX = "signals:"
_HISTORY_KEY    = "signals:history"
_DAILY_PREFIX   = "signals:daily:"
HISTORY_MAX     = 200
CATCHUP_MAX     = 50
_IST = _dt.timezone(_dt.timedelta(hours=5, minutes=30))


def _ist_date() -> str:
    return _dt.datetime.now(_IST).strftime("%Y-%m-%d")


class SignalPublisher(_HistoryOpsMixin):
    """Async Redis pub/sub publisher with persistent history."""

    def __init__(self, redis_url: str, *, cluster_max: int = 5) -> None:
        self._url         = redis_url
        self._cluster_max = cluster_max
        self._redis: aioredis.Redis | None = None
        self._cluster_counts:   dict[tuple[str, str], int] = {}
        self._cluster_boundary: str = ""

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            self._url, encoding="utf-8", decode_responses=True,
        )
        await self._redis.ping()
        logger.info("SignalPublisher connected to Redis at %s", self._url)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    async def publish_status(self, data: dict) -> None:
        """Broadcast a market-status envelope on the signals channel (no history)."""
        if self._redis is None:
            return
        payload = json.dumps({"type": "market_status", **data})
        await self._redis.publish(_CHANNEL_ALL, payload)

    async def publish_price(self, data: dict) -> None:
        """Broadcast a lightweight live-price envelope (no history)."""
        if self._redis is None:
            return
        payload = json.dumps({"type": "price", **data})
        await self._redis.publish(_CHANNEL_PRICES, payload)

    async def publish_regime_update(self, symbol: str, data: dict) -> None:
        if self._redis is None:
            return
        payload = json.dumps({"type": "regime_update", "symbol": symbol, **data})
        await self._redis.publish(_CHANNEL_ALL, payload)
        await self._redis.publish(f"{_CHANNEL_PREFIX}{symbol}", payload)

    async def publish(self, signal: Signal) -> bool:
        """Persist signal to history and broadcast via pub/sub. Returns False if suppressed."""
        if self._redis is None:
            raise RuntimeError("SignalPublisher not connected — call connect() first")
        ok, self._cluster_counts, self._cluster_boundary = cluster_check_signal(
            signal, self._cluster_counts, self._cluster_boundary, self._cluster_max,
        )
        if not ok:
            logger.debug("[CLUSTER-SUPPRESS] %s %s", signal.signal_type.value, signal.symbol)
            return False
        payload   = json.dumps(signal.to_dict())
        daily_key = f"{_DAILY_PREFIX}{_ist_date()}"
        pipe = self._redis.pipeline()
        pipe.lpush(_HISTORY_KEY, payload)
        pipe.ltrim(_HISTORY_KEY, 0, HISTORY_MAX - 1)
        pipe.lpush(daily_key, payload)
        pipe.expire(daily_key, DAILY_TTL_S)
        pipe.publish(_CHANNEL_ALL, payload)
        pipe.publish(f"{_CHANNEL_PREFIX}{signal.symbol}", payload)
        await pipe.execute()
        return True
