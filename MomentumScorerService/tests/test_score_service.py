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


@pytest.mark.asyncio
async def test_compute_all_returns_zero_when_no_symbols_exist():
    service = ScoreService(_Pool())
    service._prices = AsyncMock()
    service._scores = AsyncMock()
    service._prices.fetch_synced_symbols.return_value = []

    scored = await service.compute_all("1d")

    assert scored == 0
    service._prices.fetch_ohlcv_batch.assert_not_called()
    service._scores.delete_by_timeframe.assert_not_called()


def test_extract_benchmark_roc_pops_benchmark_and_returns_value():
    service = ScoreService(_Pool())
    price_data = {
        "NIFTY500": pd.DataFrame({"close": [100.0 + idx for idx in range(61)]}),
        "ABC": pd.DataFrame({"close": [50.0 + idx for idx in range(61)]}),
    }

    roc = service._extract_benchmark_roc(price_data)

    assert roc is not None
    assert "NIFTY500" not in price_data


def test_apply_liquidity_filter_removes_illiquid_symbols():
    service = ScoreService(_Pool())
    liquid = pd.DataFrame({
        "close": [100.0] * 30,
        "volume": [200000.0] * 30,
    })
    illiquid = pd.DataFrame({
        "close": [10.0] * 30,
        "volume": [100.0] * 30,
    })

    filtered, skipped = service._apply_liquidity_filter({"AAA": liquid, "BBB": illiquid})

    assert list(filtered) == ["AAA"]
    assert skipped == 1