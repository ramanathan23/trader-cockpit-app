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
    """Generate synthetic OHLCV data for testing."""
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
    service._prices.fetch_ohlcv_batch.return_value = {
        sym: _make_ohlcv() for sym in symbols
    }

    scored = await service.compute_unified()

    assert scored == 60
    calls = service._scores.upsert_daily_score.call_args_list
    assert sum(1 for c in calls if c.args[5] is True) == 50
    assert sum(1 for c in calls if c.args[5] is False) == 10


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