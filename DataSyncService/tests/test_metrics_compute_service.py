from unittest.mock import AsyncMock, Mock

import pytest

from src.services.metrics_compute_service import MetricsComputeService


class _AcquireContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_recompute_uses_unlimited_timeout_sentinel_by_default():
    conn = AsyncMock()
    conn.execute.return_value = "INSERT 0 42"
    pool = Mock()
    pool.acquire.return_value = _AcquireContext(conn)

    service = MetricsComputeService(pool)

    rows = await service.recompute()

    assert rows == 42
    conn.execute.assert_awaited_once()
    _, kwargs = conn.execute.await_args
    assert kwargs["timeout"] == 86400.0


@pytest.mark.asyncio
async def test_recompute_uses_configured_timeout():
    conn = AsyncMock()
    conn.execute.return_value = "INSERT 0 7"
    pool = Mock()
    pool.acquire.return_value = _AcquireContext(conn)

    service = MetricsComputeService(pool, timeout_s=900)

    rows = await service.recompute()

    assert rows == 7
    conn.execute.assert_awaited_once()
    _, kwargs = conn.execute.await_args
    assert kwargs["timeout"] == 900.0