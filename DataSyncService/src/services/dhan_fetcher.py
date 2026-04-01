"""
Dhan API fetcher for 1-minute historical OHLCV data — uses the `dhanhq` SDK.

Why Dhan for 1m:
  yfinance caps 1-min history at 7 days.
  Dhan provides up to 90 days of 1-min intraday history.

How it works:
  1. On first use, download Dhan's security master CSV and cache it locally.
     Maps NSE trading symbol → Dhan securityId.
  2. Split the 90-day range into CHUNK_DAYS windows (Dhan allows ~45 days
     per call; we use 30 to be safe).
  3. Call dhanhq.intraday_minute_data() for each window via asyncio.to_thread
     (the SDK is synchronous).
  4. Concat windows into a single UTC-indexed OHLCV DataFrame.

Dhan docs: https://dhanhq.co/docs/v2/
dhanhq SDK: https://github.com/dhan-oss/DhanHQ-py
"""

import asyncio
import io
import logging
import time
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import httpx
import pandas as pd
from dhanhq import dhanhq as DhanHQ

from ..config import settings

logger = logging.getLogger(__name__)

SECURITY_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
MASTER_CACHE_PATH = Path(__file__).parent.parent / "data" / "dhan_security_master.csv"
MASTER_TTL_HOURS = 24

# Dhan allows up to ~45 days per intraday call; 30 is safe
CHUNK_DAYS = 30


# ── Dhan client (singleton) ───────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _dhan_client() -> DhanHQ:
    return DhanHQ(
        client_id=settings.dhan_client_id,
        access_token=settings.dhan_access_token,
    )


# ── Security master ───────────────────────────────────────────────────────────

_security_map: dict[str, str] | None = None


def _is_cache_stale() -> bool:
    if not MASTER_CACHE_PATH.exists():
        return True
    age_hours = (time.time() - MASTER_CACHE_PATH.stat().st_mtime) / 3600
    return age_hours > MASTER_TTL_HOURS


def _load_master_from_disk() -> pd.DataFrame:
    return pd.read_csv(MASTER_CACHE_PATH, low_memory=False)


def _download_master_sync() -> pd.DataFrame:
    logger.info("Downloading Dhan security master…")
    resp = httpx.get(SECURITY_MASTER_URL, timeout=60, follow_redirects=True)
    resp.raise_for_status()
    MASTER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MASTER_CACHE_PATH.write_bytes(resp.content)
    return pd.read_csv(io.BytesIO(resp.content), low_memory=False)


def _build_security_map(df: pd.DataFrame) -> dict[str, str]:
    """
    Parse Dhan master CSV into {NSE_EQ_SYMBOL: security_id}.
    Handles minor column name variations across master file versions.
    """
    col_aliases = {
        "symbol":      ["sem_trading_symbol", "trading_symbol", "symbol"],
        "security_id": ["sem_smst_security_id", "security_id", "scrip_id", "sm_security_id"],
        "exchange":    ["sem_exm_exch_id", "exchange", "exch_id", "sem_segment"],
        "series":      ["sem_series", "series"],
        "instrument":  ["sem_instrument_name", "instrument_name", "instrument"],
    }

    # Normalise column names to lowercase-stripped
    df.columns = [c.strip().lower() for c in df.columns]

    def find_col(aliases: list[str]) -> str | None:
        for alias in aliases:
            if alias in df.columns:
                return alias
        # Partial match fallback
        for col in df.columns:
            for alias in aliases:
                if alias in col:
                    return col
        return None

    sym_col  = find_col(col_aliases["symbol"])
    id_col   = find_col(col_aliases["security_id"])
    exch_col = find_col(col_aliases["exchange"])
    ser_col  = find_col(col_aliases["series"])
    inst_col = find_col(col_aliases["instrument"])

    if not sym_col or not id_col:
        raise RuntimeError(
            f"Cannot parse Dhan master — could not find symbol/security_id columns. "
            f"Available: {list(df.columns)}"
        )

    # Filter to NSE EQ equities
    mask = pd.Series([True] * len(df))
    if exch_col:
        mask &= df[exch_col].astype(str).str.upper().str.contains("NSE")
    if ser_col:
        mask &= df[ser_col].astype(str).str.strip().str.upper() == "EQ"
    if inst_col:
        mask &= df[inst_col].astype(str).str.strip().str.upper() == "EQUITY"

    filtered = df[mask]
    result = dict(
        zip(
            filtered[sym_col].astype(str).str.strip(),
            filtered[id_col].astype(str).str.strip(),
        )
    )
    logger.info("Security master: %d NSE EQ symbols mapped", len(result))
    return result


async def get_security_map() -> dict[str, str]:
    global _security_map
    if _security_map is not None:
        return _security_map

    if _is_cache_stale():
        df = await asyncio.to_thread(_download_master_sync)
    else:
        df = await asyncio.to_thread(_load_master_from_disk)

    _security_map = _build_security_map(df)
    return _security_map


async def refresh_security_map() -> int:
    """Force re-download of security master. Returns number of symbols mapped."""
    global _security_map
    df = await asyncio.to_thread(_download_master_sync)
    _security_map = _build_security_map(df)
    return len(_security_map)


# ── Intraday fetch ────────────────────────────────────────────────────────────

def _fetch_chunk_sync(
    dhan: DhanHQ,
    security_id: str,
    from_date: date,
    to_date: date,
) -> pd.DataFrame:
    """
    Synchronous single-chunk fetch via dhanhq SDK.
    Called via asyncio.to_thread.

    dhanhq.intraday_minute_data returns:
      {"data": {"open": [...], "high": [...], "low": [...],
                "close": [...], "volume": [...], "timestamp": [...]}}
    Timestamps are Unix seconds in IST (Asia/Kolkata = UTC+5:30).
    """
    response = dhan.intraday_minute_data(
        security_id=security_id,
        exchange_segment=dhan.NSE,
        instrument_type=dhan.EQUITY,
        from_date=from_date.strftime("%Y-%m-%d"),
        to_date=to_date.strftime("%Y-%m-%d"),
    )

    # SDK may return dict directly or wrap in {"data": {...}}
    if isinstance(response, dict):
        payload = response.get("data", response)
    else:
        payload = {}

    timestamps = payload.get("timestamp", [])
    if not timestamps:
        return pd.DataFrame()

    # Convert IST Unix timestamps → UTC-aware DatetimeIndex
    index = (
        pd.to_datetime(timestamps, unit="s", utc=False)
        .tz_localize("Asia/Kolkata")
        .tz_convert("UTC")
    )

    df = pd.DataFrame(
        {
            "Open":   payload.get("open",   []),
            "High":   payload.get("high",   []),
            "Low":    payload.get("low",    []),
            "Close":  payload.get("close",  []),
            "Volume": payload.get("volume", []),
        },
        index=index,
    )
    return df.dropna(subset=["Open", "Close"])


# ── Concurrency limiter ───────────────────────────────────────────────────────

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.dhan_max_concurrency)
    return _semaphore


# ── Public API ────────────────────────────────────────────────────────────────

async def fetch_1m(
    symbol: str,
    days: int = 90,
    end: date | None = None,
) -> pd.DataFrame:
    """
    Fetch `days` of 1-minute OHLCV for one NSE symbol from Dhan.

    Splits into CHUNK_DAYS windows, fetches each via asyncio.to_thread,
    concatenates, deduplicates, and returns a UTC-indexed DataFrame.
    Returns empty DataFrame if symbol not in master or on API failure.
    """
    sec_map = await get_security_map()
    security_id = sec_map.get(symbol)
    if not security_id:
        logger.warning("Symbol %s not found in Dhan security master — skipping", symbol)
        return pd.DataFrame()

    end_date   = end or date.today()
    start_date = end_date - timedelta(days=days)
    dhan       = _dhan_client()
    chunks: list[pd.DataFrame] = []

    async with _get_semaphore():
        cursor = start_date
        while cursor < end_date:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS - 1), end_date)
            try:
                df = await asyncio.to_thread(
                    _fetch_chunk_sync, dhan, security_id, cursor, chunk_end
                )
                if not df.empty:
                    chunks.append(df)
                    logger.debug("[%s] Fetched %d bars (%s → %s)", symbol, len(df), cursor, chunk_end)
            except Exception:
                logger.warning(
                    "[%s] Chunk failed %s → %s", symbol, cursor, chunk_end, exc_info=True
                )
            cursor = chunk_end + timedelta(days=1)
            await asyncio.sleep(0.05)   # light pacing between chunks

    if not chunks:
        return pd.DataFrame()

    result = pd.concat(chunks).sort_index()
    result = result[~result.index.duplicated(keep="last")]
    return result


async def fetch_since(
    symbol: str,
    since: datetime,
) -> pd.DataFrame:
    """Incremental fetch from `since` to today (patch sync)."""
    from datetime import timezone
    today = date.today()
    start = since.date() if hasattr(since, "date") else since
    if start >= today:
        return pd.DataFrame()

    days = (today - start).days + 1
    return await fetch_1m(symbol, days=days, end=today)


async def fetch_1m_batch(
    symbols: list[str],
    days: int = 90,
) -> dict[str, pd.DataFrame]:
    """
    Fetch 1-min data for multiple symbols.
    Concurrency is bounded by settings.dhan_max_concurrency (default 5).
    """
    tasks = {sym: asyncio.create_task(fetch_1m(sym, days)) for sym in symbols}
    results: dict[str, pd.DataFrame] = {}
    for sym, task in tasks.items():
        try:
            df = await task
            if not df.empty:
                results[sym] = df
        except Exception:
            logger.warning("fetch_1m_batch: task failed for %s", sym, exc_info=True)
    return results
