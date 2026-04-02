"""
SyncService orchestrates full and incremental OHLCV sync for all NSE symbols.

Data sources:
  1d -> YFinanceFetcher (batched, configurable history depth)
  1m -> DhanFetcher     (concurrent per-symbol, configurable history depth)
"""

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import asyncpg

from ..config import settings
from ..infrastructure.fetchers.dhan.fetcher import DhanFetcher
from ..infrastructure.fetchers.yfinance.fetcher import YFinanceFetcher
from ..repositories.price_repository import PriceRepository
from ..repositories.symbol_repository import SymbolRepository, load_from_csv
from ..repositories.sync_state_repository import SyncStateRepository, SyncStateSnapshot

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")
_MARKET_CLOSE = time(hour=15, minute=30)
_INTRADAY_SYNC_GRACE = timedelta(minutes=15)

_ACQUIRE_TIMEOUT = 30  # seconds to wait for a pool connection


def _batches(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i: i + size]


def _to_utc_datetime(ts) -> datetime:
    if hasattr(ts, "tzinfo") and ts.tzinfo is None:
        return ts.tz_localize("UTC").to_pydatetime()
    return ts.to_pydatetime()


def _to_aware_utc(ts: datetime | None) -> datetime | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _is_after_market_close(now_ist: datetime) -> bool:
    return now_ist.timetz().replace(tzinfo=None) > _MARKET_CLOSE


def _daily_target_date(now_ist: datetime) -> date:
    if _is_after_market_close(now_ist):
        return now_ist.date()
    return now_ist.date() - timedelta(days=1)


def _needs_daily_sync(snapshot: SyncStateSnapshot, now_ist: datetime) -> bool:
    last_data_ts = _to_aware_utc(snapshot.last_data_ts)
    if last_data_ts is None:
        return True
    return last_data_ts.astimezone(_IST).date() < _daily_target_date(now_ist)


def _needs_1m_sync(
    snapshot: SyncStateSnapshot,
    now_utc: datetime,
    now_ist: datetime,
) -> bool:
    last_synced_at = _to_aware_utc(snapshot.last_synced_at)
    if last_synced_at is not None and (now_utc - last_synced_at) < _INTRADAY_SYNC_GRACE:
        return False

    if not _is_after_market_close(now_ist):
        return True

    last_data_ts = _to_aware_utc(snapshot.last_data_ts)
    if last_data_ts is None:
        return True

    last_data_ist = last_data_ts.astimezone(_IST)
    return not (
        last_data_ist.date() == now_ist.date()
        and last_data_ist.timetz().replace(tzinfo=None) >= _MARKET_CLOSE
    )


class SyncService:
    """
    Coordinates symbol loading, price fetching, ingestion, and sync-state updates.
    All configuration comes from Settings; all dependencies are injected via the pool.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._symbols = SymbolRepository(pool)
        self._prices = PriceRepository(pool)
        self._state = SyncStateRepository(pool)
        self._yf = YFinanceFetcher()
        self._dhan = DhanFetcher(
            client_id=settings.dhan_client_id,
            access_token=settings.dhan_access_token,
            max_concurrency=settings.dhan_max_concurrency,
            security_master_url=settings.dhan_security_master_url,
            master_ttl_hours=settings.dhan_master_ttl_hours,
        )

    async def bootstrap_symbols(self) -> int:
        return await self._symbols.upsert_many(load_from_csv())

    async def refresh_security_master(self) -> int:
        """Force re-download of the Dhan NSE scrip master CSV."""
        return await self._dhan.refresh_security_master()

    async def run_initial_sync(self) -> dict:
        """Full backfill: daily via yfinance + 1-min via Dhan API."""
        total = await self.bootstrap_symbols()
        all_symbols = [s.symbol for s in load_from_csv()]
        logger.info("Starting initial sync for %d symbols", len(all_symbols))
        daily_result, intraday_result = await asyncio.gather(
            self._sync_daily_initial(all_symbols),
            self._sync_1m_initial(all_symbols),
            return_exceptions=True,
        )
        if isinstance(daily_result, Exception):
            logger.error("[1d] Initial sync failed: %s", daily_result, exc_info=daily_result)
        if isinstance(intraday_result, Exception):
            logger.error("[1m] Initial sync failed: %s", intraday_result, exc_info=intraday_result)
        return {"symbols_loaded": total, "intervals": ["1d", "1m"]}

    async def run_patch_sync(self) -> dict:
        """Incremental sync: daily and 1-min run in parallel."""
        all_symbols = [s.symbol for s in load_from_csv()]
        daily_result, intraday_result = await asyncio.gather(
            self._run_daily_patch(all_symbols),
            self._run_1m_patch(all_symbols),
            return_exceptions=True,
        )
        if isinstance(daily_result, Exception):
            logger.error("[1d] Patch failed: %s", daily_result, exc_info=daily_result)
            daily_result = 0
        if isinstance(intraday_result, Exception):
            logger.error("[1m] Patch failed: %s", intraday_result, exc_info=intraday_result)
            intraday_result = 0
        return {"daily_updated": daily_result, "intraday_updated": intraday_result}

    async def _sync_daily_initial(self, symbols: list[str]) -> None:
        for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):
            data = await self._yf.fetch_batch(batch, "1d", settings.sync_1d_history_days)
            await self._persist_batch(batch, data, "1d")
            done = min((i + 1) * settings.sync_batch_size, len(symbols))
            logger.info("[1d] %d / %d done", done, len(symbols))
            await asyncio.sleep(settings.sync_batch_delay_s)

    async def _sync_1m_initial(self, symbols: list[str]) -> None:
        total_persisted = 0
        for i, batch in enumerate(_batches(symbols, settings.dhan_symbol_batch_size)):
            try:
                data = await self._dhan.fetch_batch(batch, days=settings.sync_1m_history_days)
            except Exception as exc:
                logger.error("[1m] Initial sync batch failed before fetch: %s", exc)
                await self._mark_state_error(batch, "1m", str(exc))
                continue

            batch_persisted = await self._persist_intraday_batch(batch, data)
            total_persisted += batch_persisted
            done = min((i + 1) * settings.dhan_symbol_batch_size, len(symbols))
            logger.info("[1m] Fetched data for %d symbols; processed %d / %d", total_persisted, done, len(symbols))

    async def _run_daily_patch(self, all_symbols: list[str]) -> int:
        now_ist = datetime.now(tz=_IST)
        snapshots = await self._state.get_snapshots(all_symbols, "1d")
        stale = [snapshot for snapshot in snapshots if _needs_daily_sync(snapshot, now_ist)]
        if not stale:
            logger.info("[1d] All symbols up to date")
            return 0

        syms = [snapshot.symbol for snapshot in stale]
        since_map = {
            snapshot.symbol: snapshot.last_data_ts
            for snapshot in stale
            if snapshot.last_data_ts is not None
        }
        logger.info("[1d] Patching %d symbols", len(syms))

        all_data: dict[str, object] = {}
        for batch in _batches(syms, settings.sync_batch_size):
            batch_since = {symbol: since_map[symbol] for symbol in batch if symbol in since_map}
            full_fetch_symbols = [symbol for symbol in batch if symbol not in since_map]
            if batch_since:
                for symbol, since in batch_since.items():
                    df = await self._yf.fetch_since(symbol, "1d", since)
                    if not df.empty:
                        all_data[symbol] = df
            if full_fetch_symbols:
                data = await self._yf.fetch_batch(full_fetch_symbols, "1d", settings.sync_1d_history_days)
                all_data.update(data)
            await asyncio.sleep(settings.sync_batch_delay_s)

        if all_data:
            await self._prices.bulk_ingest(all_data, "1d")
        await self._update_state(syms, all_data, "1d")
        return len(all_data)

    async def _run_1m_patch(self, all_symbols: list[str]) -> int:
        now_utc = datetime.now(tz=timezone.utc)
        now_ist = now_utc.astimezone(_IST)
        snapshots = await self._state.get_snapshots(all_symbols, "1m")
        stale = [snapshot for snapshot in snapshots if _needs_1m_sync(snapshot, now_utc, now_ist)]
        if not stale:
            logger.info("[1m] All symbols up to date")
            return 0

        try:
            self._dhan.require_credentials()
        except Exception as exc:
            logger.error("[1m] Patch blocked before fetch: %s", exc)
            await self._mark_state_error([snapshot.symbol for snapshot in stale], "1m", str(exc))
            return 0

        logger.info("[1m] Patching %d symbols", len(stale))
        updated = 0

        for i, batch in enumerate(_batches(stale, settings.dhan_symbol_batch_size)):
            tasks = {
                snapshot.symbol: asyncio.create_task(
                    self._dhan.fetch_since(snapshot.symbol, snapshot.last_data_ts)
                    if snapshot.last_data_ts is not None
                    else self._dhan.fetch_1m(snapshot.symbol, days=settings.sync_1m_history_days)
                )
                for snapshot in batch
            }

            batch_data: dict[str, object] = {}
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for symbol, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.warning("[1m] fetch failed for %s: %s", symbol, result)
                elif not result.empty:
                    batch_data[symbol] = result

            updated += await self._persist_intraday_batch(
                [snapshot.symbol for snapshot in batch],
                batch_data,
            )

            done = min((i + 1) * settings.dhan_symbol_batch_size, len(stale))
            logger.info("[1m] Processed %d / %d stale symbols", done, len(stale))

        return updated

    # ── Persistence helpers ───────────────────────────────────────────────────

    async def _persist_batch(
        self,
        batch: list[str],
        data: dict,
        interval: str,
    ) -> None:
        """Bulk-ingest price data then update sync state for the whole batch in one shot."""
        try:
            if data:
                await self._prices.bulk_ingest(data, interval)
            await self._update_state(batch, data, interval)
        except Exception as exc:
            logger.error("Batch persist failed (%s): %s", interval, exc, exc_info=True)
            await self._mark_state_error(batch, interval, str(exc))

    async def _persist_intraday_batch(
        self,
        batch_symbols: list[str],
        data: dict[str, object],
    ) -> int:
        """
        Persist all price data for the batch then update sync state for every
        symbol in a single batch upsert — one DB round-trip instead of N.

        Previously called _persist_intraday_results and issued one connection
        acquire + two round-trips per symbol, causing pool exhaustion under load.
        """
        # Separate symbols with data from those without
        symbols_with_data = {s: df for s, df in data.items() if df is not None and not df.empty}
        symbols_without = [s for s in batch_symbols if s not in symbols_with_data]

        if symbols_with_data:
            try:
                await self._prices.bulk_ingest(symbols_with_data, "1m")
            except Exception as exc:
                logger.error("[1m] bulk_ingest failed: %s", exc, exc_info=True)
                await self._mark_state_error(batch_symbols, "1m", str(exc))
                return 0

        # Build all state records for one batch upsert
        records: list[tuple] = []
        for symbol, df in symbols_with_data.items():
            records.append((
                symbol, "1m",
                _to_utc_datetime(df.index.max()),
                "synced",
                None,
            ))
        for symbol in symbols_without:
            records.append((symbol, "1m", None, "empty", None))

        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            await self._state.upsert_many(conn, records)

        return len(symbols_with_data)

    async def _update_state(
        self,
        symbols: list[str],
        data: dict,
        interval: str,
    ) -> None:
        """Batch-update sync state for all symbols in a single round-trip."""
        records: list[tuple] = []
        for symbol, df in data.items():
            records.append((
                symbol, interval,
                _to_utc_datetime(df.index.max()),
                "synced",
                None,
            ))
        for symbol in symbols:
            if symbol not in data:
                records.append((symbol, interval, None, "empty", None))

        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            await self._state.upsert_many(conn, records)

    async def _mark_state_error(
        self,
        symbols: list[str],
        interval: str,
        error_msg: str,
    ) -> None:
        records = [(s, interval, None, "error", error_msg) for s in symbols]
        async with self._pool.acquire(timeout=_ACQUIRE_TIMEOUT) as conn:
            await self._state.upsert_many(conn, records)
