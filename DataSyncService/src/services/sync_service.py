"""
SyncService orchestrates OHLCV sync for all NSE symbols.

Design
------
* Both intervals run in parallel via asyncio.gather — they use different providers
  (yfinance for 1d, Dhan for 1m) and write to different tables.

* Source of truth for gap detection is MAX(time) queried directly from the price
  tables, not sync_state.last_data_ts.  sync_state is updated after each ingest
  for reporting / status endpoints.

* Per-symbol classification (no separate "initial" vs "patch" entry points):

  1d (yfinance / price_data_daily)
  ─────────────────────────────────
  INITIAL     — no rows in price_data_daily           → pull 5 yr history
  SKIP        — last_date == today                    → nothing to do
  SKIP        — last_date == today-1 AND time < 15:30 → market hasn't closed
  FETCH_TODAY — last_date == today-1 AND time ≥ 15:30 → pull today's session
  FETCH_GAP   — last_date < today-1                   → pull from last_date → now

  1m (Dhan / price_data_1m)
  ──────────────────────────
  INITIAL     — no rows in price_data_1m              → pull 90 days
  SKIP        — now − last_data_ts ≤ 15 min           → within grace period
  SKIP        — market closed AND last_data_ts ≥ 15:30 IST → day already complete
  FETCH_GAP   — otherwise                             → fill gap from last_data_ts
"""

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

import asyncpg

from ..config import settings
from ..infrastructure.fetchers.dhan.fetcher import DhanFetcher
from ..infrastructure.fetchers.yfinance.fetcher import YFinanceFetcher
from ..repositories.price_repository import PriceRepository
from ..repositories.symbol_repository import SymbolRepository, load_from_csv
from ..repositories.sync_state_repository import SyncStateRepository

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")
_MARKET_CLOSE = time(hour=15, minute=30)
_INTRADAY_SYNC_GRACE = timedelta(minutes=15)
_ACQUIRE_TIMEOUT = 30  # seconds


# ── Type aliases ──────────────────────────────────────────────────────────────

DailyAction = Literal["INITIAL", "SKIP", "FETCH_TODAY", "FETCH_GAP"]
IntraAction  = Literal["INITIAL", "SKIP", "FETCH_GAP"]


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


def _classify_1m(
    last_ts: datetime | None,
    now_utc: datetime,
    now_ist: datetime,
) -> IntraAction:
    """Decide what 1-minute sync action a symbol needs based on its last price timestamp."""
    if last_ts is None:
        return "INITIAL"

    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    else:
        last_ts = last_ts.astimezone(timezone.utc)

    last_ist    = last_ts.astimezone(_IST)
    after_close = now_ist.time() >= _MARKET_CLOSE

    # Day's 1m data is complete: market has closed and last bar is at/after close
    if after_close and last_ist.time() >= _MARKET_CLOSE:
        return "SKIP"

    # Recent enough — within the 15-minute grace window
    if (now_utc - last_ts) <= _INTRADAY_SYNC_GRACE:
        return "SKIP"

    return "FETCH_GAP"


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
        self._dhan    = DhanFetcher(
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

    # ── Public entry points ───────────────────────────────────────────────────

    async def run_sync(self) -> dict:
        """
        Unified sync — auto-classifies every symbol per interval and applies
        the appropriate action (initial pull / gap fill / skip).

        Both intervals run concurrently; they use separate providers and tables.

        The two MAX(time) bulk queries run first (together, before any fetch work
        starts) so they don't compete with pool connections held by ingest tasks.
        """
        await self.bootstrap_symbols()
        all_symbol_objs = load_from_csv()
        all_symbols  = [s.symbol for s in all_symbol_objs]
        # Indices (e.g. NIFTY500) are synced via yfinance for daily data only —
        # Dhan 1m intraday uses a different exchange segment and is not needed
        # for the benchmark use-case; exclude them from the 1m pipeline.
        eq_symbols = [s.symbol for s in all_symbol_objs if s.series == "EQ"]
        logger.info("run_sync: %d symbols (%d EQ + %d index) — loading sync state",
                    len(all_symbols), len(eq_symbols), len(all_symbols) - len(eq_symbols))

        # Use sync_state (small plain table, ~4k rows) — fast.
        # Price-table MAX/DISTINCT scans span every hypertable chunk and are
        # too slow for the hot path.  sync_state.last_data_ts is kept accurate
        # after every successful ingest; the worst case is a re-fetch of a few
        # already-present rows, which bulk_ingest handles via ON CONFLICT DO NOTHING.
        daily_snapshots, intra_snapshots = await asyncio.gather(
            self._state.get_snapshots(all_symbols, "1d"),
            self._state.get_snapshots(eq_symbols, "1m"),
        )
        daily_ts_map: dict[str, datetime | None] = {s.symbol: s.last_data_ts for s in daily_snapshots}
        intra_ts_map: dict[str, datetime | None] = {s.symbol: s.last_data_ts for s in intra_snapshots}
        logger.info("run_sync: sync state loaded — starting parallel sync")

        daily_result, intra_result = await asyncio.gather(
            self._run_daily_sync(all_symbols, daily_ts_map),
            self._run_1m_sync(eq_symbols, intra_ts_map),
            return_exceptions=True,
        )

        if isinstance(daily_result, Exception):
            logger.error("[1d] sync failed: %s", daily_result, exc_info=daily_result)
            daily_result = {"error": str(daily_result)}
        if isinstance(intra_result, Exception):
            logger.error("[1m] sync failed: %s", intra_result, exc_info=intra_result)
            intra_result = {"error": str(intra_result)}

        return {"1d": daily_result, "1m": intra_result}

    # ── Diagnostics ───────────────────────────────────────────────────────────

    async def get_gap_report(self) -> dict:
        """
        Returns per-symbol classification without fetching any data.
        Useful for inspecting which symbols need work and why.
        Only symbols that are NOT fully up-to-date are included.
        """
        all_symbols = [s.symbol for s in load_from_csv() if s.series == "EQ"]
        now_utc = datetime.now(tz=timezone.utc)
        now_ist = now_utc.astimezone(_IST)

        # Gap report queries the price tables directly (source of truth).
        # This is slow on large hypertables — acceptable for a diagnostic endpoint
        # that is never called on the sync hot path.
        logger.info("gap_report: querying price tables for %d symbols (may be slow)", len(all_symbols))
        daily_last, intra_last = await asyncio.gather(
            self._prices.get_last_data_ts_bulk(all_symbols, "1d"),
            self._prices.get_last_data_ts_bulk(all_symbols, "1m"),
        )
        logger.info("gap_report: price table queries complete")

        gaps: dict[str, dict] = {}
        summary: dict[str, dict[str, int]] = {
            "1d": {"INITIAL": 0, "FETCH_TODAY": 0, "FETCH_GAP": 0, "SKIP": 0},
            "1m": {"INITIAL": 0, "FETCH_GAP": 0, "SKIP": 0},
        }

        for symbol in all_symbols:
            d_ts  = _ensure_utc(daily_last.get(symbol))
            m_ts  = _ensure_utc(intra_last.get(symbol))
            d_act = _classify_daily(d_ts, now_ist)
            m_act = _classify_1m(m_ts, now_utc, now_ist)
            summary["1d"][d_act] += 1
            summary["1m"][m_act] += 1
            if d_act != "SKIP" or m_act != "SKIP":
                gaps[symbol] = {
                    "1d": {"action": d_act, "last_ts": d_ts.isoformat() if d_ts else None},
                    "1m": {"action": m_act, "last_ts": m_ts.isoformat() if m_ts else None},
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

    # ── 1-min sync (Dhan → price_data_1m) ────────────────────────────────────

    async def _run_1m_sync(
        self,
        all_symbols: list[str],
        last_ts_map: dict[str, datetime | None],
    ) -> dict:
        now_utc = datetime.now(tz=timezone.utc)
        now_ist = now_utc.astimezone(_IST)

        try:
            self._dhan.require_credentials()
        except Exception as exc:
            logger.error("[1m] Sync blocked — credentials missing: %s", exc)
            return {"error": str(exc)}

        initial:  list[str]                      = []
        gap_syms: list[tuple[str, datetime]]     = []

        for symbol in all_symbols:
            last_ts = _ensure_utc(last_ts_map.get(symbol))
            action  = _classify_1m(last_ts, now_utc, now_ist)
            if action == "INITIAL":
                initial.append(symbol)
            elif action == "FETCH_GAP":
                gap_syms.append((symbol, last_ts))

        skip_count = len(all_symbols) - len(initial) - len(gap_syms)
        logger.info(
            "[1m] INITIAL=%d  FETCH_GAP=%d  SKIP=%d",
            len(initial), len(gap_syms), skip_count,
        )

        updated = 0

        # 1. Initial: no data → pull 90 days in batches
        if initial:
            total_batches = -(-len(initial) // settings.dhan_symbol_batch_size)
            logger.info("[1m/initial] starting: %d symbols, %d batches of %d, lookback=%dd",
                        len(initial), total_batches,
                        settings.dhan_symbol_batch_size, settings.sync_1m_history_days)
            for i, batch in enumerate(_batches(initial, settings.dhan_symbol_batch_size)):
                logger.debug("[1m/initial] batch %d/%d — %s … %s",
                             i + 1, total_batches, batch[0], batch[-1])
                try:
                    data = await self._dhan.fetch_batch(batch, days=settings.sync_1m_history_days)
                except Exception as exc:
                    logger.error("[1m/initial] batch %d/%d failed: %s",
                                 i + 1, total_batches, exc, exc_info=True)
                    await self._mark_state_error(batch, "1m", str(exc))
                    continue
                got = len(data)
                missing = len(batch) - got
                if missing:
                    logger.warning("[1m/initial] batch %d/%d — no data for %d symbol(s): %s",
                                   i + 1, total_batches, missing,
                                   [s for s in batch if s not in data])
                persisted = await self._persist_intraday_batch(batch, data)
                updated += persisted
                done = min((i + 1) * settings.dhan_symbol_batch_size, len(initial))
                logger.info("[1m/initial] %d / %d symbols processed (%d persisted so far)",
                            done, len(initial), updated)
            logger.info("[1m/initial] done — %d / %d symbols had data", updated, len(initial))

        # 2. Gap fill: concurrent per batch, each symbol fetches from its own last_ts
        if gap_syms:
            total_batches = -(-len(gap_syms) // settings.dhan_symbol_batch_size)
            logger.info("[1m/gap] starting: %d symbols, %d batches of %d",
                        len(gap_syms), total_batches, settings.dhan_symbol_batch_size)
            for i, batch in enumerate(_batches(gap_syms, settings.dhan_symbol_batch_size)):
                for sym, ts in batch:
                    logger.debug("[1m/gap] %s — fetching since %s", sym, ts)
                tasks = {
                    symbol: asyncio.create_task(self._dhan.fetch_since(symbol, last_ts))
                    for symbol, last_ts in batch
                }
                batch_data: dict = {}
                results = await asyncio.gather(*tasks.values(), return_exceptions=True)
                for symbol, result in zip(tasks.keys(), results):
                    if isinstance(result, Exception):
                        logger.warning("[1m/gap] fetch_since failed for %s: %s",
                                       symbol, result, exc_info=result)
                    elif result.empty:
                        logger.debug("[1m/gap] %s — no new bars returned", symbol)
                    else:
                        logger.debug("[1m/gap] %s — got %d new bars", symbol, len(result))
                        batch_data[symbol] = result

                persisted = await self._persist_intraday_batch(
                    [s for s, _ in batch], batch_data
                )
                updated += persisted
                done = min((i + 1) * settings.dhan_symbol_batch_size, len(gap_syms))
                logger.info("[1m/gap] %d / %d symbols processed (%d persisted so far)",
                            done, len(gap_syms), updated)
            logger.info("[1m/gap] done — %d / %d symbols had gaps filled",
                        updated, len(gap_syms))

        return {
            "initial": len(initial),
            "fetch_gap": len(gap_syms),
            "skip": skip_count,
            "updated": updated,
        }

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

    async def _persist_intraday_batch(
        self,
        batch_symbols: list[str],
        data: dict,
    ) -> int:
        """
        Persist all price data for the batch then update sync state for every
        symbol in a single batch upsert — one DB round-trip instead of N.
        """
        symbols_with_data  = {s: df for s, df in data.items() if df is not None and not df.empty}
        symbols_without    = [s for s in batch_symbols if s not in symbols_with_data]

        logger.debug("[1m] persist: %d with data, %d empty",
                     len(symbols_with_data), len(symbols_without))
        if symbols_without:
            logger.debug("[1m] persist: empty symbols: %s", symbols_without)

        if symbols_with_data:
            try:
                inserted = await self._prices.bulk_ingest(symbols_with_data, "1m")
                logger.debug("[1m] bulk_ingest: %d new rows for %d symbols",
                             inserted, len(symbols_with_data))
            except Exception as exc:
                logger.error("[1m] bulk_ingest failed for batch [%s…]: %s",
                             next(iter(symbols_with_data)), exc, exc_info=True)
                await self._mark_state_error(batch_symbols, "1m", str(exc))
                return 0

        records: list[tuple] = []
        for symbol, df in symbols_with_data.items():
            records.append((symbol, "1m", _to_utc_datetime(df.index.max()), "synced", None))
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
