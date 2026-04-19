from __future__ import annotations

import datetime as _dt
import json

_DAILY_PREFIX = "signals:daily:"
CATCHUP_MAX   = 50
DAILY_TTL_S   = 7 * 24 * 3600
_IST = _dt.timezone(_dt.timedelta(hours=5, minutes=30))


def _ist_date() -> str:
    return _dt.datetime.now(_IST).strftime("%Y-%m-%d")


class _HistoryOpsMixin:
    """Mixin providing signal history read methods for SignalPublisher."""

    async def recent_signals(self) -> list[dict]:
        """Recent signals for stream catch-up (chronological, oldest first)."""
        if self._redis is None:
            return []
        today_key = f"{_DAILY_PREFIX}{_ist_date()}"
        raw = await self._redis.lrange(today_key, 0, CATCHUP_MAX - 1)
        signals = []
        for item in reversed(raw):
            try:
                d = json.loads(item)
                d["_catchup"] = True
                signals.append(d)
            except Exception:
                pass
        return signals

    async def signals_for_date(
        self, date_str: str, offset: int = 0, limit: int | None = None,
    ) -> tuple[list[dict], int]:
        """Signals for a given IST date, chronological. Returns (page, total)."""
        if self._redis is None:
            return [], 0
        key   = f"{_DAILY_PREFIX}{date_str}"
        total = await self._redis.llen(key)
        if total == 0:
            return [], 0
        if limit is None:
            raw = await self._redis.lrange(key, 0, -1)
            signals = []
            for item in reversed(raw):
                try:
                    signals.append(json.loads(item))
                except Exception:
                    pass
            return signals, total
        redis_end   = total - 1 - offset
        redis_start = max(0, redis_end - limit + 1)
        if redis_start > redis_end:
            return [], total
        raw = await self._redis.lrange(key, redis_start, redis_end)
        signals = []
        for item in reversed(raw):
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
        return sorted(
            (k.removeprefix(_DAILY_PREFIX) for k in keys), reverse=True,
        )
