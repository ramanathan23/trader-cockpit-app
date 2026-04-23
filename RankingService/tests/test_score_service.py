import pytest
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock

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


def _make_ohlcv(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({
        "open":   close - rng.uniform(0.2, 1.0, n),
        "high":   close + rng.uniform(0.5, 2.0, n),
        "low":    close - rng.uniform(0.5, 2.0, n),
        "close":  close,
        "volume": rng.uniform(100_000, 1_000_000, n),
    })


@pytest.mark.asyncio
async def test_compute_unified_scores_and_persists():
    service = ScoreService(_Pool())
    service._prices = AsyncMock()
    service._scores = AsyncMock()

    service._prices.fetch_synced_symbols.return_value = ["ABC", "XYZ"]
    service._prices.fetch_ohlcv_batch.return_value = {
        "ABC": _make_ohlcv(),
        "XYZ": _make_ohlcv(),
    }

    scored = await service.compute_unified()

    assert scored == 2
    assert service._scores.upsert_daily_score.await_count == 2
    assert service._scores.update_symbol_metrics_indicators.await_count == 2


@pytest.mark.asyncio
async def test_compute_unified_returns_zero_when_no_symbols():
    service = ScoreService(_Pool())
    service._prices = AsyncMock()
    service._scores = AsyncMock()
    service._prices.fetch_synced_symbols.return_value = []

    scored = await service.compute_unified()

    assert scored == 0
    service._prices.fetch_ohlcv_batch.assert_not_called()


@pytest.mark.asyncio
async def test_compute_unified_marks_top_50_as_watchlist():
    service = ScoreService(_Pool())
    service._prices = AsyncMock()
    service._scores = AsyncMock()

    symbols = [f"SYM{i:03d}" for i in range(60)]
    service._prices.fetch_synced_symbols.return_value = symbols
    service._prices.fetch_ohlcv_batch.return_value = {sym: _make_ohlcv() for sym in symbols}

    scored = await service.compute_unified()

    assert scored == 60
    calls = service._scores.upsert_daily_score.call_args_list
    assert sum(1 for c in calls if c.args[5] is True) == 50
    assert sum(1 for c in calls if c.args[5] is False) == 10