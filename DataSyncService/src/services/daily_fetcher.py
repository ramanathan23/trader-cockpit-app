"""
DailyFetcher — executes the three daily price fetch strategies.

Single responsibility: given a list of symbols and their last timestamps,
download the appropriate price history from yfinance and persist it via
SyncStateWriter.

Strategies
----------
  fetch_full          — INITIAL symbols → pull full N-year history in batches
  fetch_since_uniform — FETCH_TODAY symbols share a since date → batched download
  fetch_gap           — FETCH_GAP symbols each have an individual since date
"""

from datetime import datetime

from ..infrastructure.fetchers.yfinance.fetcher import YFinanceFetcher
from .sync_state_writer import SyncStateWriter
from ._daily_fetch_strategies import (
    fetch_full as _fetch_full,
    fetch_since_uniform as _fetch_since_uniform,
    fetch_gap as _fetch_gap,
)


class DailyFetcher:
    """Executes daily price fetch strategies for DataSyncService."""

    def __init__(self, yf: YFinanceFetcher, writer: SyncStateWriter) -> None:
        self._yf     = yf
        self._writer = writer

    async def fetch_full(self, symbols: list[str]) -> int:
        return await _fetch_full(self._yf, self._writer, symbols)

    async def fetch_since_uniform(self, symbols: list[str], since_dt: datetime) -> int:
        return await _fetch_since_uniform(self._yf, self._writer, symbols, since_dt)

    async def fetch_gap(self, symbols: list[str], last_ts_map: dict) -> int:
        return await _fetch_gap(self._yf, self._writer, symbols, last_ts_map)

