"""
SyncService — orchestrates full and incremental OHLCV sync for all NSE symbols.

Data sources:
  1d → YFinanceFetcher  (batched, up to 1825 days)
  1m → DhanFetcher      (per-symbol concurrent, 90 days via Dhan API)
"""

import asyncio
import logging
from datetime import datetime

import asyncpg

from ..config import settings
from ..infrastructure.fetchers.dhan.fetcher import DhanFetcher
from ..infrastructure.fetchers.yfinance.fetcher import YFinanceFetcher
from ..repositories.price_repository import PriceRepository
from ..repositories.symbol_repository import SymbolRepository, load_from_csv
from ..repositories.sync_state_repository import SyncStateRepository

logger = logging.getLogger(__name__)

_SYNC_CONFIG: dict[str, dict] = {
    "1d": {"days": 1825},
    "1m": {"days": 90},
}


def _batches(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i: i + size]


def _to_utc_datetime(ts) -> datetime:
    if hasattr(ts, "tzinfo") and ts.tzinfo is None:
        return ts.tz_localize("UTC").to_pydatetime()
    return ts.to_pydatetime()


class SyncService:
    """
    Coordinates symbol loading, price fetching, ingestion, and sync-state updates.
    All dependencies are injected; no global state.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._symbols = SymbolRepository(pool)
        self._prices  = PriceRepository(pool)
        self._state   = SyncStateRepository(pool)
        self._yf      = YFinanceFetcher()
        self._dhan    = DhanFetcher(
            client_id=settings.dhan_client_id,
            access_token=settings.dhan_access_token,
            max_concurrency=settings.dhan_max_concurrency,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def bootstrap_symbols(self) -> int:
        return await self._symbols.upsert_many(load_from_csv())

    async def run_initial_sync(self) -> dict:
        """Full backfill: 5yr daily via yfinance + 90d 1-min via Dhan."""
        total = await self.bootstrap_symbols()
        all_symbols = [s.symbol for s in load_from_csv()]
        logger.info("Starting initial sync for %d symbols", len(all_symbols))
        await self._sync_daily_initial(all_symbols)
        await self._sync_1m_initial(all_symbols)
        return {"symbols_loaded": total, "intervals": list(_SYNC_CONFIG)}

    async def run_patch_sync(self) -> dict:
        """Incremental sync: 1d (yfinance) and 1m (Dhan) run in parallel."""
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

    # ── Initial sync helpers ──────────────────────────────────────────────────

    async def _sync_daily_initial(self, symbols: list[str]) -> None:
        days = _SYNC_CONFIG["1d"]["days"]
        for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):
            data = await self._yf.fetch_batch(batch, "1d", days)
            await self._persist_batch(batch, data, "1d")
            done = min((i + 1) * settings.sync_batch_size, len(symbols))
            logger.info("[1d] %d / %d done", done, len(symbols))
            await asyncio.sleep(settings.sync_batch_delay_s)

    async def _sync_1m_initial(self, symbols: list[str]) -> None:
        days = _SYNC_CONFIG["1m"]["days"]
        dhan_batch = 200
        for i, batch in enumerate(_batches(symbols, dhan_batch)):
            data = await self._dhan.fetch_batch(batch, days=days)
            await self._persist_batch(batch, data, "1m")
            done = min((i + 1) * dhan_batch, len(symbols))
            logger.info("[1m] %d / %d done", done, len(symbols))

    # ── Patch sync helpers ────────────────────────────────────────────────────

    async def _run_daily_patch(self, all_symbols: list[str]) -> int:
        stale = await self._state.get_stale_daily(all_symbols)
        if not stale:
            logger.info("[1d] All symbols up to date")
            return 0

        syms      = [s for s, _ in stale]
        since_map = {s: ts for s, ts in stale if ts is not None}
        logger.info("[1d] Patching %d symbols", len(syms))

        all_data: dict = {}
        for batch in _batches(syms, settings.sync_batch_size):
            batch_since = {s: since_map[s] for s in batch if s in since_map}
            if batch_since:
                for sym, since in batch_since.items():
                    df = await self._yf.fetch_since(sym, "1d", since)
                    if not df.empty:
                        all_data[sym] = df
            else:
                data = await self._yf.fetch_batch(batch, "1d", _SYNC_CONFIG["1d"]["days"])
                all_data.update(data)
            await asyncio.sleep(settings.sync_batch_delay_s)

        if all_data:
            await self._prices.bulk_ingest(all_data, "1d")
        await self._update_state(syms, all_data, "1d")
        return len(all_data)

    async def _run_1m_patch(self, all_symbols: list[str]) -> int:
        stale = await self._state.get_stale_1m(all_symbols)
        if not stale:
            logger.info("[1m] All symbols up to date")
            return 0

        logger.info("[1m] Patching %d symbols", len(stale))
        tasks = {
            sym: asyncio.create_task(
                self._dhan.fetch_since(sym, last_time)
                if last_time is not None
                else self._dhan.fetch_1m(sym, days=90)
            )
            for sym, last_time in stale
        }

        all_data: dict = {}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for sym, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning("[1m] fetch failed for %s: %s", sym, result)
            elif not result.empty:
                all_data[sym] = result

        if all_data:
            await self._prices.bulk_ingest(all_data, "1m")
        await self._update_state([s for s, _ in stale], all_data, "1m")
        return len(all_data)

    # ── Shared state helpers ──────────────────────────────────────────────────

    async def _persist_batch(
        self,
        batch: list[str],
        data: dict,
        interval: str,
    ) -> None:
        try:
            if data:
                await self._prices.bulk_ingest(data, interval)
            async with self._pool.acquire() as conn:
                for sym, df in data.items():
                    await self._state.upsert(
                        conn, sym, interval, "synced",
                        last_data_ts=_to_utc_datetime(df.index.max()),
                    )
                for sym in batch:
                    if sym not in data:
                        await self._state.upsert(conn, sym, interval, "empty")
        except Exception as exc:
            logger.error("Batch persist failed (%s): %s", interval, exc, exc_info=True)
            async with self._pool.acquire() as conn:
                for sym in batch:
                    await self._state.upsert(conn, sym, interval, "error", error_msg=str(exc))

    async def _update_state(
        self,
        syms: list[str],
        data: dict,
        interval: str,
    ) -> None:
        async with self._pool.acquire() as conn:
            for sym, df in data.items():
                await self._state.upsert(
                    conn, sym, interval, "synced",
                    last_data_ts=_to_utc_datetime(df.index.max()),
                )
            for sym in syms:
                if sym not in data:
                    await self._state.upsert(conn, sym, interval, "empty")
