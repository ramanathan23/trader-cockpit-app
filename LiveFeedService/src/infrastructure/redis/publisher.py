"""
SignalPublisher: publishes Signal objects to Redis pub/sub and maintains
two levels of signal history:

  signals:history          — rolling last-200 list for SSE catch-up (live session)
  signals:daily:YYYY-MM-DD — per-IST-date list for later review, 7-day TTL

Both lists store JSON blobs newest-first (LPUSH).
"""

from __future__ import annotations

import datetime
import json
import logging

import redis.asyncio as aioredis

from ...domain.models import Signal

logger = logging.getLogger(__name__)

_CHANNEL_ALL    = "signals"
_CHANNEL_PREFIX = "signals:"
_HISTORY_KEY    = "signals:history"
_DAILY_PREFIX   = "signals:daily:"
HISTORY_MAX     = 200           # rolling catch-up list length
DAILY_TTL_S     = 7 * 24 * 3600  # keep daily lists for 7 days

# IST = UTC+05:30 (no pytz needed)
_IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def _ist_date() -> str:
    """Current date in IST as YYYY-MM-DD."""
    return datetime.datetime.now(_IST).strftime("%Y-%m-%d")


class SignalPublisher:
    """
    Async Redis pub/sub publisher with persistent history.

    Usage
    -----
    publisher = SignalPublisher(redis_url)
    await publisher.connect()
    await publisher.publish(signal)
    signals = await publisher.recent_signals()          # SSE catch-up
    signals = await publisher.signals_for_date("2026-04-13")  # review
    """

    def __init__(self, redis_url: str) -> None:
        self._url    = redis_url
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            self._url,
            encoding         = "utf-8",
            decode_responses = True,
        )
        await self._redis.ping()
        logger.info("SignalPublisher connected to Redis at %s", self._url)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    async def publish(self, signal: Signal) -> None:
        """
        Persist signal to rolling + daily history, then broadcast via pub/sub.
        All four operations run in a single pipeline round-trip.
        """
        if self._redis is None:
            raise RuntimeError("SignalPublisher not connected — call connect() first")

        payload   = json.dumps(signal.to_dict())
        daily_key = f"{_DAILY_PREFIX}{_ist_date()}"

        pipe = self._redis.pipeline()
        # Rolling session history (newest first, capped at HISTORY_MAX).
        pipe.lpush(_HISTORY_KEY, payload)
        pipe.ltrim(_HISTORY_KEY, 0, HISTORY_MAX - 1)
        # Daily history (newest first, TTL refreshed on every write).
        pipe.lpush(daily_key, payload)
        pipe.expire(daily_key, DAILY_TTL_S)
        # Pub/sub broadcast.
        pipe.publish(_CHANNEL_ALL, payload)
        pipe.publish(f"{_CHANNEL_PREFIX}{signal.symbol}", payload)
        await pipe.execute()

    async def recent_signals(self) -> list[dict]:
        """
        Recent signals for SSE catch-up (chronological, oldest first).
        Tagged with _catchup=True so the browser skips dedup and sound.
        """
        if self._redis is None:
            return []
        raw = await self._redis.lrange(_HISTORY_KEY, 0, HISTORY_MAX - 1)
        signals = []
        for item in reversed(raw):   # lrange is newest-first; reverse to chronological
            try:
                d = json.loads(item)
                d["_catchup"] = True
                signals.append(d)
            except Exception:
                pass
        return signals

    async def signals_for_date(self, date_str: str) -> list[dict]:
        """
        All signals for a given IST date (YYYY-MM-DD), chronological order.
        Returns [] if nothing recorded or key has expired.
        """
        if self._redis is None:
            return []
        key = f"{_DAILY_PREFIX}{date_str}"
        raw = await self._redis.lrange(key, 0, -1)
        signals = []
        for item in reversed(raw):   # newest-first in Redis; reverse for display
            try:
                signals.append(json.loads(item))
            except Exception:
                pass
        return signals

    async def available_dates(self) -> list[str]:
        """IST dates that have saved signal data, sorted descending."""
        if self._redis is None:
            return []
        keys = await self._redis.keys(f"{_DAILY_PREFIX}*")
        dates = sorted(
            (k.removeprefix(_DAILY_PREFIX) for k in keys),
            reverse=True,
        )
        return dates
