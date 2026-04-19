"""Tests for ScoreService helper methods."""

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
