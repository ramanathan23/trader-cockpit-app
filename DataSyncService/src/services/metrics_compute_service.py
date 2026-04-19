"""
MetricsComputeService — runs after each 1d EOD sync to precompute per-symbol
daily metrics and write them into the symbol_metrics table.

LiveFeedService reads from symbol_metrics at startup instead of computing
these queries itself, so there is no heavy aggregation at market open.
"""
from __future__ import annotations

import logging

import asyncpg

from shared.utils import parse_pg_command_result

from ._metrics_sql import METRICS_UPSERT_SQL

logger = logging.getLogger(__name__)

_UNLIMITED_TIMEOUT_SENTINEL_S = 86400.0


class MetricsComputeService:
    """Computes and persists per-symbol daily metrics into symbol_metrics."""

    def __init__(self, pool: asyncpg.Pool, *, timeout_s: int | float | None = None) -> None:
        self._pool = pool
        self._timeout_s = timeout_s

    def _resolve_timeout(self) -> tuple[float, str]:
        if self._timeout_s in (None, 0):
            return _UNLIMITED_TIMEOUT_SENTINEL_S, "unlimited (24h sentinel)"
        return float(self._timeout_s), f"{float(self._timeout_s)}s"

    async def recompute(self) -> int:
        """
        Recompute metrics for all symbols that have daily price data and
        upsert into symbol_metrics.  Returns the number of rows written.
        """
        timeout_s, timeout_label = self._resolve_timeout()
        logger.info(
            "MetricsComputeService: recomputing symbol metrics (timeout=%s)…",
            timeout_label,
        )

        async with self._pool.acquire() as conn:
            result = await conn.execute(METRICS_UPSERT_SQL, timeout=timeout_s)

        count = parse_pg_command_result(result)
        logger.info("MetricsComputeService: upserted %d symbol_metrics rows", count)
        return count
