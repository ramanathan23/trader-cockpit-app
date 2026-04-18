"""
SyncService — orchestrates symbol loading, Dhan master sync, and price fetch dispatch.

Single responsibility: classify symbols by sync need and delegate to DailyFetcher.
Fetch strategies live in daily_fetcher.py; persistence in sync_state_writer.py;
classification logic in domain/daily_action.py.
"""
import logging
from datetime import datetime, time, timedelta

import asyncpg

from shared.constants import IST, MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE
from shared.utils import ensure_utc

from ..config import settings
from ..domain.daily_action import DailyAction, classify_daily
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

logger = logging.getLogger(__name__)

_MARKET_CLOSE = time(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE)


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

        return {"1d": await self._run_daily_sync(all_symbols, daily_ts_map)}

    async def recompute_metrics(self) -> dict:
        """Recompute symbol_metrics table from price_data_daily."""
        count = await self._metrics.recompute()
        return {"rows_written": count}

    async def get_gap_report(self) -> dict:
        """Return per-symbol classification without fetching data (diagnostics)."""
        all_symbols = [s.symbol for s in load_from_csv()]
        now_ist     = datetime.now(tz=IST)

        logger.info("gap_report: querying price tables for %d symbols", len(all_symbols))
        daily_last = await self._prices.get_last_data_ts_bulk(all_symbols, "1d")
        logger.info("gap_report: done")

        gaps:    dict = {}
        summary: dict = {"1d": {"INITIAL": 0, "FETCH_TODAY": 0, "FETCH_GAP": 0, "SKIP": 0}}

        for symbol in all_symbols:
            d_ts  = ensure_utc(daily_last.get(symbol))
            d_act = classify_daily(d_ts, now_ist)
            summary["1d"][d_act] += 1
            if d_act != "SKIP":
                gaps[symbol] = {
                    "1d": {"action": d_act, "last_ts": d_ts.isoformat() if d_ts else None},
                }

        return {
            "as_of_ist":     now_ist.isoformat(),
            "total_symbols": len(all_symbols),
            "gap_count":     len(gaps),
            "summary":       summary,
            "symbols":       gaps,
        }

    # ── Private ───────────────────────────────────────────────────────────────

    async def _run_daily_sync(
        self,
        all_symbols: list[str],
        last_ts_map: dict[str, datetime | None],
    ) -> dict:
        now_ist      = datetime.now(tz=IST)
        initial:     list[str] = []
        fetch_today: list[str] = []
        fetch_gap:   list[str] = []

        for symbol in all_symbols:
            action = classify_daily(ensure_utc(last_ts_map.get(symbol)), now_ist)
            if action == "INITIAL":
                initial.append(symbol)
            elif action == "FETCH_TODAY":
                fetch_today.append(symbol)
            elif action == "FETCH_GAP":
                fetch_gap.append(symbol)

        skip_count = len(all_symbols) - len(initial) - len(fetch_today) - len(fetch_gap)
        logger.info("[1d] INITIAL=%d  FETCH_TODAY=%d  FETCH_GAP=%d  SKIP=%d",
                    len(initial), len(fetch_today), len(fetch_gap), skip_count)

        updated = 0
        if initial:
            updated += await self._fetcher.fetch_full(initial)
        if fetch_today:
            since_dt = datetime.combine(
                now_ist.date() - timedelta(days=1), time.min
            ).replace(tzinfo=IST)
            updated += await self._fetcher.fetch_since_uniform(fetch_today, since_dt)
        if fetch_gap:
            updated += await self._fetcher.fetch_gap(fetch_gap, last_ts_map)

        # Recompute precomputed metrics after price data is updated.
        metrics_rows = await self._metrics.recompute()

        return {
            "initial":       len(initial),
            "fetch_today":   len(fetch_today),
            "fetch_gap":     len(fetch_gap),
            "skip":          skip_count,
            "updated":       updated,
            "metrics_rows":  metrics_rows,
        }
