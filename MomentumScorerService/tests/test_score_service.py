import pytest
import pandas as pd
from unittest.mock import AsyncMock

from src.domain.models import ScoreBreakdown
from src.services.score_service import ScoreService


class _AcquireContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _TransactionContext:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Conn:
    def transaction(self):
        return _TransactionContext()


class _Pool:
    def __init__(self):
        self.conn = _Conn()

    def acquire(self):
        return _AcquireContext(self.conn)


@pytest.mark.asyncio
async def test_compute_all_replaces_previous_day_scores(monkeypatch):
    service = ScoreService(_Pool())

    service._prices = AsyncMock()
    service._scores = AsyncMock()

    service._prices.fetch_synced_symbols.return_value = ["ABC"]
    service._prices.fetch_ohlcv_batch.return_value = {
        "ABC": pd.DataFrame(
            {
                "close": [100.0] * 30,
                "volume": [200000.0] * 30,
                "high": [101.0] * 30,
                "low": [99.0] * 30,
            }
        )
    }
    service._scores.delete_by_timeframe.return_value = 1

    breakdown = ScoreBreakdown(81.5, 72.0, 80.0, 79.0, 85.0)

    async def fake_to_thread(func, df, **kwargs):
        return breakdown

    monkeypatch.setattr("src.services.score_service.asyncio.to_thread", fake_to_thread)

    scored = await service.compute_all("1d")

    assert scored == 1
    service._scores.delete_by_timeframe.assert_awaited_once_with(service._pool.conn, "1d")
    service._scores.insert.assert_awaited_once_with(service._pool.conn, "ABC", "1d", breakdown)