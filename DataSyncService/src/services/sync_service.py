"""
SyncService orchestrates OHLCV sync for all NSE symbols.

Design
------
* Source of truth for gap detection is MAX(time) queried directly from the price
  tables, not sync_state.last_data_ts.  sync_state is updated after each ingest
  for reporting / status endpoints.

* Per-symbol classification:

  1d (yfinance / price_data_daily)
  ─────────────────────────────────
  INITIAL     — no rows in price_data_daily           → pull 5 yr history
  SKIP        — last_date == today                    → nothing to do
  SKIP        — last_date == today-1 AND time < 15:30 → market hasn't closed
  FETCH_TODAY — last_date == today-1 AND time ≥ 15:30 → pull today's session
  FETCH_GAP   — last_date < today-1                   → pull from last_date → now
"""

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

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

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")
_MARKET_CLOSE = time(hour=15, minute=30)
_ACQUIRE_TIMEOUT = 30  # seconds


# ── Type aliases ──────────────────────────────────────────────────────────────

DailyAction = Literal["INITIAL", "SKIP", "FETCH_TODAY", "FETCH_GAP"]


# ── Pure classification functions (no I/O, easily unit-testable) ──────────────

def _classify_daily(last_ts: datetime | None, now_ist: datetime) -> DailyAction:
    """Decide what daily sync action a symbol needs based on its last price timestamp."""
    if last_ts is None:
        return "INITIAL"

    last_date = last_ts.astimezone(_IST).date()
    today     = now_ist.date()
    yesterday = today - timedelta(days=1)
    after_close = now_ist.time() >= _MARKET_CLOSE

    if last_date >= today:
        return "SKIP"
    if last_date == yesterday and not after_close:
        return "SKIP"   # market hasn't closed; nothing new yet
    if last_date == yesterday and after_close:
        return "FETCH_TODAY"
    return "FETCH_GAP"  # last_date < yesterday — multi-day gap


# ── Helpers ───────────────────────────────────────────────────────────────────

def _batches(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i: i + size]


def _to_utc_datetime(ts) -> datetime:
    if hasattr(ts, "tzinfo") and ts.tzinfo is None:
        return ts.tz_localize("UTC").to_pydatetime()
    return ts.to_pydatetime()


def _ensure_utc(ts: datetime | None) -> datetime | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


# ── Service ───────────────────────────────────────────────────────────────────

class SyncService:
    """
    Coordinates symbol loading, price fetching, ingestion, and sync-state updates.
    All configuration comes from Settings; all dependencies are injected via the pool.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool   = pool
        self._symbols = SymbolRepository(pool)
        self._prices  = PriceRepository(pool)
        self._state   = SyncStateRepository(pool)
        self._yf      = YFinanceFetcher()

    async def bootstrap_symbols(self) -> int:
        return await self._symbols.upsert_many(load_from_csv())

    async def refresh_security_master(self) -> MappingResult:
        """
        Download the Dhan instrument master CSV and sync security IDs into the DB.

        Steps:
          1. Download + parse the master CSV.
          2. Bulk-update symbols.dhan_security_id for all matched equities.
          3. Upsert index_futures and activate the nearest expiry per underlying.
        """
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

    # ── Public entry points ───────────────────────────────────────────────────

    async def run_sync(self) -> dict:
        """
        Unified sync — auto-classifies every symbol and applies the appropriate
        action (initial pull / gap fill / skip).
        """
        await self.bootstrap_symbols()
        all_symbol_objs = load_from_csv()
        all_symbols = [s.symbol for s in all_symbol_objs]
        logger.info("run_sync: %d symbols — loading sync state", len(all_symbols))

        daily_snapshots = await self._state.get_snapshots(all_symbols, "1d")
        daily_ts_map: dict[str, datetime | None] = {s.symbol: s.last_data_ts for s in daily_snapshots}
        logger.info("run_sync: sync state loaded — starting sync")

        daily_result = await self._run_daily_sync(all_symbols, daily_ts_map)

        return {"1d": daily_result}

    # ── Diagnostics ───────────────────────────────────────────────────────────

    async def get_gap_report(self) -> dict:
        """
        Returns per-symbol classification without fetching any data.
        Useful for inspecting which symbols need work and why.
        Only symbols that are NOT fully up-to-date are included.
        """
        all_symbols = [s.symbol for s in load_from_csv()]
        now_utc = datetime.now(tz=timezone.utc)
        now_ist = now_utc.astimezone(_IST)

        logger.info("gap_report: querying price tables for %d symbols (may be slow)", len(all_symbols))
        daily_last = await self._prices.get_last_data_ts_bulk(all_symbols, "1d")
        logger.info("gap_report: price table query complete")

        gaps: dict[str, dict] = {}
        summary: dict[str, dict[str, int]] = {
            "1d": {"INITIAL": 0, "FETCH_TODAY": 0, "FETCH_GAP": 0, "SKIP": 0},
        }

        for symbol in all_symbols:
            d_ts  = _ensure_utc(daily_last.get(symbol))
            d_act = _classify_daily(d_ts, now_ist)
            summary["1d"][d_act] += 1
            if d_act != "SKIP":
                gaps[symbol] = {
                    "1d": {"action": d_act, "last_ts": d_ts.isoformat() if d_ts else None},
                }

        return {
            "as_of_ist": now_ist.isoformat(),
            "total_symbols": len(all_symbols),
            "gap_count": len(gaps),
            "summary": summary,
            "symbols": gaps,
        }

    # ── Daily sync (yfinance → price_data_daily) ──────────────────────────────

    async def _run_daily_sync(
        self,
        all_symbols: list[str],
        last_ts_map: dict[str, datetime | None],
    ) -> dict:
        now_ist = datetime.now(tz=_IST)
        initial:     list[str] = []
        fetch_today: list[str] = []
        fetch_gap:   list[str] = []

        for symbol in all_symbols:
            action = _classify_daily(_ensure_utc(last_ts_map.get(symbol)), now_ist)
            if action == "INITIAL":
                initial.append(symbol)
            elif action == "FETCH_TODAY":
                fetch_today.append(symbol)
            elif action == "FETCH_GAP":
                fetch_gap.append(symbol)

        skip_count = len(all_symbols) - len(initial) - len(fetch_today) - len(fetch_gap)
        logger.info(
            "[1d] INITIAL=%d  FETCH_TODAY=%d  FETCH_GAP=%d  SKIP=%d",
            len(initial), len(fetch_today), len(fetch_gap), skip_count,
        )

        updated = 0

        # 1. Initial: no data → pull full 5yr history in batches of 50
        if initial:
            updated += await self._daily_fetch_full(initial)

        # 2. FETCH_TODAY: all share yesterday as their since date → batched download
        if fetch_today:
            since_dt = datetime.combine(
                now_ist.date() - timedelta(days=1), time.min
            ).replace(tzinfo=_IST)
            updated += await self._daily_fetch_since_uniform(fetch_today, since_dt)

        # 3. FETCH_GAP: each symbol has a different since date → per-symbol fetch_since
        if fetch_gap:
            updated += await self._daily_fetch_gap(fetch_gap, last_ts_map)

        return {
            "initial": len(initial),
            "fetch_today": len(fetch_today),
            "fetch_gap": len(fetch_gap),
            "skip": skip_count,
            "updated": updated,
        }

    async def _daily_fetch_full(self, symbols: list[str]) -> int:
        """Fetch full 5yr history for symbols with no daily data."""
        total_batches = -(-len(symbols) // settings.sync_batch_size)  # ceiling div
        logger.info("[1d/initial] starting: %d symbols, %d batches of %d",
                    len(symbols), total_batches, settings.sync_batch_size)
        updated = 0
        for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):
            logger.debug("[1d/initial] batch %d/%d — fetching %s … %s",
                         i + 1, total_batches, batch[0], batch[-1])
            data = await self._yf.fetch_batch(batch, "1d", settings.sync_1d_history_days)
            got = len(data)
            missing = len(batch) - got
            if missing:
                logger.warning("[1d/initial] batch %d/%d — no data for %d symbol(s): %s",
                               i + 1, total_batches, missing,
                               [s for s in batch if s not in data])
            await self._persist_batch(batch, data, "1d")
            updated += got
            done = min((i + 1) * settings.sync_batch_size, len(symbols))
            logger.info("[1d/initial] %d / %d symbols processed (%d with data)",
                        done, len(symbols), updated)
            await asyncio.sleep(settings.sync_batch_delay_s)
        logger.info("[1d/initial] done — %d / %d symbols had data", updated, len(symbols))
        return updated

    async def _daily_fetch_since_uniform(
        self, symbols: list[str], since_dt: datetime
    ) -> int:
        """Batch-download for symbols that all share the same since date (FETCH_TODAY)."""
        total_batches = -(-len(symbols) // settings.sync_batch_size)
        logger.info("[1d/today] starting: %d symbols since %s, %d batches",
                    len(symbols), since_dt.date(), total_batches)
        updated = 0
        for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):
            data = await self._yf.fetch_batch(
                batch, "1d", settings.sync_1d_history_days, start=since_dt
            )
            got = len(data)
            if len(batch) - got:
                logger.debug("[1d/today] batch %d/%d — no data for: %s",
                             i + 1, total_batches,
                             [s for s in batch if s not in data])
            await self._persist_batch(batch, data, "1d")
            updated += got
            done = min((i + 1) * settings.sync_batch_size, len(symbols))
            logger.info("[1d/today] %d / %d symbols processed (%d with data)",
                        done, len(symbols), updated)
            await asyncio.sleep(settings.sync_batch_delay_s)
        logger.info("[1d/today] done — %d / %d symbols had new data", updated, len(symbols))
        return updated

    async def _daily_fetch_gap(
        self,
        symbols: list[str],
        last_ts_map: dict[str, datetime | None],
    ) -> int:
        """Per-symbol gap fill for symbols whose last price date is behind yesterday."""
        total_batches = -(-len(symbols) // settings.sync_batch_size)
        logger.info("[1d/gap] starting: %d symbols, %d batches", len(symbols), total_batches)
        updated = 0
        for i, batch in enumerate(_batches(symbols, settings.sync_batch_size)):
            batch_data: dict = {}
            for symbol in batch:
                since = _ensure_utc(last_ts_map.get(symbol))
                if since is None:
                    logger.warning("[1d/gap] %s has no last_ts — skipping", symbol)
                    continue
                logger.debug("[1d/gap] %s — fetching since %s", symbol, since.date())
                df = await self._yf.fetch_since(symbol, "1d", since)
                if df.empty:
                    logger.debug("[1d/gap] %s — no new bars returned", symbol)
                else:
                    logger.debug("[1d/gap] %s — got %d new bars", symbol, len(df))
                    batch_data[symbol] = df
            await self._persist_batch(batch, batch_data, "1d")
            updated += len(batch_data)
            done = min((i + 1) * settings.sync_batch_size, len(symbols))
            logger.info("[1d/gap] %d / %d processed, %d updated so far",
                        done, len(symbols), updated)
            await asyncio.sleep(settings.sync_batch_delay_s)
        logger.info("[1d/gap] done — %d / %d symbols had gaps filled", updated, len(symbols))
        return updated

    # ── Persistence helpers ───────────────────────────────────────────────────

    async def _persist_batch(
        self,
        batch: list[str],
        data: dict,
        interval: str,
    ) -> None:
        """Bulk-ingest price data then update sync state for the whole batch."""
        try:
            if data:
                inserted = await self._prices.bulk_ingest(data, interval)
                logger.debug("[%s] bulk_ingest: %d new rows for %d symbols",
                             interval, inserted, len(data))
            await self._update_state(batch, data, interval)
        except Exception as exc:
            logger.error("[%s] persist failed for batch [%s…]: %s",
                         interval, batch[0], exc, exc_info=True)
            await self._mark_state_error(batch, interval, str(exc))

    async def _update_state(
        self,
        symbols: list[str],
        data: dict,
        interval: str,
    ) -> None:
        """Batch-update sync state for all symbols in a single round-trip."""
        records: list[tuple] = []
        for symbol, df in data.items():
            records.append((symbol, interval, _to_utc_datetime(df.index.max()), "synced", None))
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
