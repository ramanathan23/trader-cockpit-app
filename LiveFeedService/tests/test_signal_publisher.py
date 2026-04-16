import json

import pytest

from src.infrastructure.redis.publisher import HISTORY_MAX, SignalPublisher
from src.infrastructure.redis.publisher import CATCHUP_MAX, HISTORY_MAX, SignalPublisher


class _FakeRedis:
    def __init__(self, items: list[str]) -> None:
        self._items = items

    async def lrange(self, _key: str, start: int, end: int) -> list[str]:
        if end == -1:
            return self._items[start:]
        return self._items[start : end + 1]


@pytest.mark.asyncio
async def test_recent_signals_limits_catchup_and_preserves_chronological_order() -> None:
    items = [json.dumps({"id": str(index), "timestamp": f"t{index}"}) for index in range(HISTORY_MAX + 25, 0, -1)]
    publisher = SignalPublisher("redis://example")
    publisher._redis = _FakeRedis(items)

    signals = await publisher.recent_signals()

    assert len(signals) == CATCHUP_MAX
    assert signals[0]["id"] == str(HISTORY_MAX + 25 - CATCHUP_MAX + 1)
    assert signals[-1]["id"] == str(HISTORY_MAX + 25)
    assert all(signal["_catchup"] is True for signal in signals)