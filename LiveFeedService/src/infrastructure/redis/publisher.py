"""
SignalPublisher: publishes Signal objects to Redis pub/sub and maintains
two levels of signal history:

    signals:history          — rolling last-200 list for stream catch-up (live session)
  signals:daily:YYYY-MM-DD — per-IST-date list for later review, 7-day TTL

Both lists store JSON blobs newest-first (LPUSH).
"""

from __future__ import annotations

import datetime
import json
import logging

import redis.asyncio as aioredis

from ...domain.signal import Signal

logger = logging.getLogger(__name__)

_CHANNEL_ALL    = "signals"
_CHANNEL_PREFIX = "signals:"
_HISTORY_KEY    = "signals:history"
_DAILY_PREFIX   = "signals:daily:"
HISTORY_MAX     = 200           # rolling catch-up list length
CATCHUP_MAX     = 50            # replay window for new streaming subscribers
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
    publisher = SignalPublisher(redis_url, cluster_max=5)
    await publisher.connect()
    await publisher.publish(signal)
    signals = await publisher.recent_signals()          # SSE catch-up
    signals = await publisher.signals_for_date("2026-04-13")  # review
    """

    def __init__(self, redis_url: str, *, cluster_max: int = 5) -> None:
        self._url         = redis_url
        self._cluster_max = cluster_max
        self._redis: aioredis.Redis | None = None
        # Cluster suppression: (signal_type_value, boundary_iso) → count this boundary
        self._cluster_counts: dict[tuple[str, str], int] = {}
        self._cluster_boundary: str = ""   # reset when boundary changes

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

    def _cluster_check(self, signal: Signal) -> bool:
        """
        Returns True if the signal should be published.
        Returns False if this signal_type has already exceeded cluster_max
        for the current 3-min candle boundary.

        Drive-family signals (OPEN_DRIVE_ENTRY, TRAIL_UPDATE, EXIT) are
        never cluster-suppressed — they are stock-specific, not market-wide.
        """
        from ...domain.signal_type import SignalType as _ST
        _EXEMPT = {
            _ST.OPEN_DRIVE_ENTRY, _ST.DRIVE_FAILED, _ST.TRAIL_UPDATE,
            _ST.EXIT, _ST.EXHAUSTION_REVERSAL,
            _ST.CAM_H3_REVERSAL, _ST.CAM_H4_BREAKOUT,
            _ST.CAM_L3_REVERSAL, _ST.CAM_L4_BREAKDOWN,
        }
        if signal.signal_type in _EXEMPT:
            return True

        boundary = signal.timestamp.strftime("%Y-%m-%dT%H:%M")
        key      = (signal.signal_type.value, boundary)
        self._cluster_counts[key] = self._cluster_counts.get(key, 0) + 1

        # Prune stale boundaries (keep only the current minute)
        if boundary != self._cluster_boundary:
            self._cluster_counts = {k: v for k, v in self._cluster_counts.items() if k[1] == boundary}
            self._cluster_boundary = boundary

        return self._cluster_counts[key] <= self._cluster_max

    async def publish_status(self, data: dict) -> None:
        """Broadcast a market-status envelope on the signals channel (no history)."""
        if self._redis is None:
            return
        payload = json.dumps({"type": "market_status", **data})
        await self._redis.publish(_CHANNEL_ALL, payload)

    async def publish(self, signal: Signal) -> bool:
        """
        Persist signal to rolling + daily history, then broadcast via pub/sub.
        Returns True if published, False if cluster-suppressed.
        """
        if self._redis is None:
            raise RuntimeError("SignalPublisher not connected — call connect() first")

        if not self._cluster_check(signal):
            logger.debug("[CLUSTER-SUPPRESS] %s %s", signal.signal_type.value, signal.symbol)
            return False

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
        return True

    async def recent_signals(self) -> list[dict]:
        """
        Recent signals for stream catch-up (chronological, oldest first).
        Reads only the most recent CATCHUP_MAX items from today's IST-date
        daily key so a mid-session subscriber does not have to drain the
        entire day's backlog before reaching live pub/sub.
        Tagged with _catchup=True so the browser skips dedup and sound.
        """
        if self._redis is None:
            return []
        today_key = f"{_DAILY_PREFIX}{_ist_date()}"
        raw = await self._redis.lrange(today_key, 0, CATCHUP_MAX - 1)
        signals = []
        for item in reversed(raw):   # lrange is newest-first; reverse to chronological
            try:
                d = json.loads(item)
                d["_catchup"] = True
                signals.append(d)
            except Exception:
                pass
        return signals

    async def signals_for_date(self, date_str: str, offset: int = 0, limit: int | None = None) -> tuple[list[dict], int]:
        """
        Signals for a given IST date (YYYY-MM-DD), chronological order.
        Returns (page, total_count).
        Returns ([], 0) if nothing recorded or key has expired.
        """
        if self._redis is None:
            return [], 0
        key = f"{_DAILY_PREFIX}{date_str}"
        total = await self._redis.llen(key)
        if total == 0:
            return [], 0

        # Redis list is newest-first (LPUSH). We want chronological (oldest-first).
        # To paginate chronologically: reverse the index mapping.
        # offset=0 → oldest items, which are at the end of the list.
        if limit is None:
            # Return all, reversed
            raw = await self._redis.lrange(key, 0, -1)
            signals = []
            for item in reversed(raw):
                try:
                    signals.append(json.loads(item))
                except Exception:
                    pass
            return signals, total

        # Paginated: map chronological offset to Redis indices (newest-first order)
        redis_end   = total - 1 - offset
        redis_start = max(0, redis_end - limit + 1)
        if redis_start > redis_end:
            return [], total

        raw = await self._redis.lrange(key, redis_start, redis_end)
        signals = []
        for item in reversed(raw):   # reverse back to chronological
            try:
                signals.append(json.loads(item))
            except Exception:
                pass
        return signals, total

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
