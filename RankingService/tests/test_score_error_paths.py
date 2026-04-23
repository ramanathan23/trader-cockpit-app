"""Error-path tests for score persistence (part 1)."""

import asyncpg
import numpy as np
import pandas as pd
import pytest
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
async def test_persist_failure_doesnt_crash_batch():
    """If one symbol's persist fails, the rest should still succeed."""
    service = ScoreService(_Pool())
    service._prices = AsyncMock()
    service._scores = AsyncMock()

    symbols = ["GOOD1", "BAD", "GOOD2"]
    service._prices.fetch_synced_symbols.return_value = symbols
    service._prices.fetch_ohlcv_batch.return_value = {sym: _make_ohlcv() for sym in symbols}

    call_count = 0
    original_upsert = service._scores.upsert_daily_score

    async def _failing_upsert(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if args[1] == "BAD":
            raise asyncpg.UniqueViolationError("test error")
        return await original_upsert(*args, **kwargs)

    service._scores.upsert_daily_score = AsyncMock(side_effect=_failing_upsert)
    service._scores.update_symbol_metrics_indicators = AsyncMock()

    scored = await service.compute_unified()

    assert scored == 2
