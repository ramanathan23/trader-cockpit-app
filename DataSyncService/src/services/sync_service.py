"""
SyncService — orchestrates symbol loading, Dhan master sync, and price fetch dispatch.

Single responsibility: classify symbols by sync need and delegate to DailyFetcher.
Fetch strategies live in daily_fetcher.py; persistence in sync_state_writer.py;
classification logic in domain/daily_action.py.
"""
import logging

import asyncpg

from ..config import settings
from ..infrastructure.fetchers.yfinance.fetcher import YFinanceFetcher
from ..infrastructure.dhan.instrument_master import download_and_parse
from ..infrastructure.dhan.instrument_mapper import (
    apply_equity_mapping,
    apply_index_future_mapping,
    MappingResult,
)
from ..repositories.price_repository import PriceRepository
from ..repositories.symbol_repository import SymbolRepository, load_from_csv
from ..repositories.sync_state_repository import SyncStateRepository
from .daily_fetcher import DailyFetcher
from .sync_state_writer import SyncStateWriter
from .metrics_compute_service import MetricsComputeService
from ._sync_orchestrator import run_daily_sync, build_gap_report

logger = logging.getLogger(__name__)


class SyncService:
    """
    Coordinates symbol loading, price fetching, ingestion, and sync-state updates.
    Configuration comes from Settings; all I/O dependencies injected via pool.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool    = pool
        self._symbols = SymbolRepository(pool)
        self._prices  = PriceRepository(pool)
        self._state   = SyncStateRepository(pool)
        writer        = SyncStateWriter(pool, self._prices, self._state)
        self._fetcher = DailyFetcher(YFinanceFetcher(), writer)
        self._metrics = MetricsComputeService(
            pool,
            timeout_s=settings.db_metrics_recompute_timeout,
        )

    async def bootstrap_symbols(self) -> int:
        return await self._symbols.upsert_many(load_from_csv())

    async def refresh_security_master(self) -> MappingResult:
        """Download the Dhan instrument master CSV and sync security IDs into DB."""
        master = await download_and_parse(
            settings.dhan_master_url,
            timeout_s=settings.dhan_master_timeout_s,
        )
        matched, unmatched = await apply_equity_mapping(self._pool, master.equities)
        upserted, activated = await apply_index_future_mapping(
            self._pool, master.index_futures
        )
        return MappingResult(
            equities_matched        = matched,
            equities_unmatched      = unmatched,
            index_futures_upserted  = upserted,
            index_futures_activated = activated,
        )

    async def run_sync(self) -> dict:
        """Auto-classify every symbol and apply the appropriate fetch action."""
        symbols = load_from_csv()
        await self._symbols.upsert_many(symbols)
        all_symbols = [s.symbol for s in symbols]
        logger.info("run_sync: %d symbols — loading sync state", len(all_symbols))
        daily_snapshots = await self._state.get_snapshots(all_symbols, "1d")
        daily_ts_map    = {s.symbol: s.last_data_ts for s in daily_snapshots}
        logger.info("run_sync: sync state loaded — starting sync")
        return {"1d": await run_daily_sync(
            self._fetcher, self._metrics, all_symbols, daily_ts_map
        )}

    async def recompute_metrics(self) -> dict:
        """Recompute symbol_metrics table from price_data_daily."""
        count = await self._metrics.recompute()
        return {"rows_written": count}

    async def get_gap_report(self) -> dict:
        """Return per-symbol classification without fetching data (diagnostics)."""
        all_symbols = [s.symbol for s in load_from_csv()]
        return await build_gap_report(self._prices, all_symbols)

