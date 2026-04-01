"""
Orchestrates full and incremental sync for all NSE symbols.

Data sources
────────────
  1d  → yfinance    batch of 50 symbols, 90 days
  1m  → Dhan API    per-symbol, 90 days (dhanhq SDK, bounded concurrency)

Initial sync
────────────
  1. bootstrap_symbols()  — load CSV into symbols table (idempotent)
  2. Daily (1d): yfinance batch fetch → asyncpg COPY ingest
  3. 1-min (1m): Dhan per-symbol fetch (concurrent) → asyncpg COPY ingest

Patch sync
──────────
  For each interval, find symbols whose last_synced_at is older than
  STALE_THRESHOLD_MINUTES, fetch only the delta from last_data_ts.
"""

import asyncio
import csv
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg

from ..config import settings
from . import dhan_fetcher, fetcher, ingester

logger = logging.getLogger(__name__)

SYMBOLS_CSV = Path(__file__).parent.parent / "data" / "symbols.csv"

SYNC_CONFIG: dict[str, dict] = {
    "1d": {"days": 90, "source": "yfinance"},
    "1m": {"days": 90, "source": "dhan"},    # full 90-day backfill via Dhan
}

STALE_THRESHOLD_MINUTES = 60


# ── Symbol helpers ────────────────────────────────────────────────────────────

def load_symbols_from_csv() -> list[dict]:
    rows = []
    with open(SYMBOLS_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            series = row.get(" SERIES", "").strip()
            if series != "EQ":
                continue
            rows.append({
                "symbol":       row["SYMBOL"].strip(),
                "company_name": row["NAME OF COMPANY"].strip(),
                "series":       series,
                "isin":         row["ISIN NUMBER"].strip(),
                "listed_date":  _parse_date(row.get(" DATE OF LISTING", "")),
                "face_value":   _parse_float(row.get(" FACE VALUE", "")),
            })
    return rows


def _parse_date(val: str):
    val = val.strip()
    for fmt in ("%d-%b-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _parse_float(val: str):
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None


def _batches(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i: i + size]


# ── DB helpers ────────────────────────────────────────────────────────────────

async def bootstrap_symbols(pool: asyncpg.Pool) -> int:
    rows = load_symbols_from_csv()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany("""
                INSERT INTO symbols (symbol, company_name, series, isin, listed_date, face_value)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (symbol) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    series       = EXCLUDED.series,
                    isin         = EXCLUDED.isin
            """, [(r["symbol"], r["company_name"], r["series"],
                   r["isin"], r["listed_date"], r["face_value"]) for r in rows])
    logger.info("Bootstrapped %d symbols into DB", len(rows))
    return len(rows)


async def _upsert_sync_state(
    conn: asyncpg.Connection,
    symbol: str,
    timeframe: str,
    status: str,
    last_data_ts: datetime | None = None,
    error_msg: str | None = None,
) -> None:
    await conn.execute("""
        INSERT INTO sync_state (symbol, timeframe, last_synced_at, last_data_ts, status, error_msg)
        VALUES ($1, $2, NOW(), $3, $4, $5)
        ON CONFLICT (symbol, timeframe) DO UPDATE SET
            last_synced_at = NOW(),
            last_data_ts   = COALESCE($3, sync_state.last_data_ts),
            status         = $4,
            error_msg      = $5
    """, symbol, timeframe, last_data_ts, status, error_msg)


async def _get_stale_symbols(
    pool: asyncpg.Pool,
    timeframe: str,
    all_symbols: list[str],
) -> list[tuple[str, datetime | None]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            WITH all_syms AS (SELECT unnest($1::text[]) AS symbol)
            SELECT a.symbol, ss.last_data_ts
            FROM   all_syms a
            LEFT JOIN sync_state ss
                   ON ss.symbol = a.symbol AND ss.timeframe = $2
            WHERE  ss.last_synced_at IS NULL
               OR  ss.last_synced_at < NOW() - ($3 || ' minutes')::interval
            ORDER  BY ss.last_synced_at ASC NULLS FIRST
        """, all_symbols, timeframe, str(STALE_THRESHOLD_MINUTES))
    return [(r["symbol"], r["last_data_ts"]) for r in rows]


# ── Fetch helpers (source-aware) ──────────────────────────────────────────────

async def _fetch_initial(
    symbols: list[str],
    interval: str,
    days: int,
    source: str,
) -> dict:
    if source == "dhan":
        # Dhan: concurrent per-symbol, bounded by dhan_max_concurrency
        return await dhan_fetcher.fetch_1m_batch(symbols, days=days)
    else:
        # yfinance: multi-symbol batch
        return await fetcher.fetch_batch(symbols, interval, days)


async def _fetch_patch(
    symbols: list[str],
    interval: str,
    since: dict[str, datetime],
    source: str,
) -> dict:
    symbol_data: dict = {}
    if source == "dhan":
        for sym in symbols:
            start_ts = since.get(sym)
            if start_ts:
                df = await dhan_fetcher.fetch_since(sym, start_ts)
                if not df.empty:
                    symbol_data[sym] = df
    else:
        for sym in symbols:
            start_ts = since.get(sym)
            if start_ts:
                df = await fetcher.fetch_since(sym, interval, start_ts)
                if not df.empty:
                    symbol_data[sym] = df
    return symbol_data


# ── Core sync ─────────────────────────────────────────────────────────────────

async def _sync_batch(
    pool: asyncpg.Pool,
    symbols: list[str],
    interval: str,
    days: int,
    source: str,
    since: dict[str, datetime] | None = None,
) -> None:
    try:
        if since:
            symbol_data = await _fetch_patch(symbols, interval, since, source)
        else:
            symbol_data = await _fetch_initial(symbols, interval, days, source)

        if not symbol_data:
            async with pool.acquire() as conn:
                for sym in symbols:
                    await _upsert_sync_state(conn, sym, interval, "empty")
            return

        await ingester.ingest_ohlcv(pool, symbol_data, interval)

        async with pool.acquire() as conn:
            for symbol, df in symbol_data.items():
                last_ts = df.index.max()
                if hasattr(last_ts, "tzinfo") and last_ts.tzinfo is None:
                    last_ts = last_ts.tz_localize("UTC")
                await _upsert_sync_state(
                    conn, symbol, interval, "synced",
                    last_data_ts=last_ts.to_pydatetime(),
                )
            for sym in symbols:
                if sym not in symbol_data:
                    await _upsert_sync_state(conn, sym, interval, "empty")

    except Exception as exc:
        logger.error("Batch sync failed (%s, %s): %s", interval, symbols[:3], exc, exc_info=True)
        async with pool.acquire() as conn:
            for sym in symbols:
                await _upsert_sync_state(conn, sym, interval, "error", error_msg=str(exc))


# ── Public API ────────────────────────────────────────────────────────────────

async def run_initial_sync(pool: asyncpg.Pool) -> dict:
    """Full 90-day load: daily via yfinance, 1-min via Dhan."""
    total = await bootstrap_symbols(pool)
    all_symbols = [r["symbol"] for r in load_symbols_from_csv()]
    logger.info("Starting initial sync for %d symbols", len(all_symbols))

    for interval, cfg in SYNC_CONFIG.items():
        source = cfg["source"]
        days   = cfg["days"]

        # Dhan fetches are already concurrent (bounded by semaphore);
        # use larger batches to keep the task list manageable.
        batch_size = settings.sync_batch_size if source == "yfinance" else 200

        logger.info("[%s] source=%s, %d symbols, batch=%d", interval, source, len(all_symbols), batch_size)

        for i, batch in enumerate(_batches(all_symbols, batch_size)):
            await _sync_batch(pool, batch, interval, days, source)
            done = min((i + 1) * batch_size, len(all_symbols))
            logger.info("[%s] %d / %d done", interval, done, len(all_symbols))
            if source == "yfinance":
                await asyncio.sleep(settings.sync_batch_delay_s)

    return {"symbols_loaded": total, "intervals": list(SYNC_CONFIG)}


async def run_patch_sync(pool: asyncpg.Pool) -> dict:
    """Incremental sync — fetch only data newer than last_data_ts."""
    all_symbols = [r["symbol"] for r in load_symbols_from_csv()]
    updated = 0

    for interval, cfg in SYNC_CONFIG.items():
        source = cfg["source"]
        stale  = await _get_stale_symbols(pool, interval, all_symbols)
        if not stale:
            logger.info("[%s] All symbols up to date", interval)
            continue

        logger.info("[%s] Patching %d stale symbols (source=%s)", interval, len(stale), source)
        batch_size = settings.sync_batch_size if source == "yfinance" else 200

        for batch in _batches(stale, batch_size):
            syms  = [s for s, _ in batch]
            since = {s: ts for s, ts in batch if ts is not None}
            await _sync_batch(pool, syms, interval, days=1, source=source, since=since or None)
            updated += len(batch)
            if source == "yfinance":
                await asyncio.sleep(settings.sync_batch_delay_s)

    return {"updated": updated, "intervals": list(SYNC_CONFIG)}
