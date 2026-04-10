"""
Dhan instrument master: download, parse, and expose as typed records.

Dhan publishes a daily CSV at DHAN_MASTER_URL containing every tradable
instrument with its security ID, exchange segment, series, expiry, etc.

The parsed output is intentionally kept as plain dataclasses — callers
(instrument_mapper) decide what to do with each record.
"""

import logging
from dataclasses import dataclass
from datetime import date
from io import StringIO
from typing import Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

# Published daily by Dhan; no auth required.
DHAN_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

# Instrument types we care about.
_EQUITY   = "EQUITY"
_FUTIDX   = "FUTIDX"   # index futures (our market proxy)
_FUTSTK   = "FUTSTK"   # stock futures (future use)

# Index underlyings used as market proxy.
PROXY_UNDERLYINGS = frozenset({"NIFTY", "BANKNIFTY", "SENSEX"})

# Columns in the Dhan master CSV that we consume.
_REQUIRED_COLS = {
    "SEM_EXM_EXCH_ID",        # NSE | BSE | MCX …
    "SEM_SEGMENT",             # compact segment code: E | D | M ...
    "SEM_SMST_SECURITY_ID",    # numeric security ID (what Dhan calls securityId)
    "SEM_TRADING_SYMBOL",      # RELIANCE, NIFTY, BANKNIFTY …
    "SEM_CUSTOM_SYMBOL",       # NIFTY APR FUT, SENSEX JUN FUT ...
    "SEM_INSTRUMENT_NAME",     # EQUITY | FUTIDX | FUTSTK | OPTIDX …
    "SEM_SERIES",              # EQ | BE | N | XX …
    "SEM_EXPIRY_DATE",         # DD-MMM-YYYY for F&O, empty for EQ
    "SEM_LOT_UNITS",           # lot size
}


@dataclass(frozen=True)
class EquityRecord:
    security_id:      int
    trading_symbol:   str    # matches symbols.symbol
    exchange_segment: str    # NSE_EQ | BSE_EQ


@dataclass(frozen=True)
class IndexFutureRecord:
    security_id:      int
    underlying:       str    # NIFTY | BANKNIFTY | SENSEX
    exchange_segment: str    # NSE_FNO | BSE_FNO
    expiry_date:      date
    lot_size:         int


@dataclass(frozen=True)
class MasterData:
    equities:      list[EquityRecord]
    index_futures: list[IndexFutureRecord]


async def download_and_parse(
    url: str = DHAN_MASTER_URL,
    *,
    timeout_s: float = 30.0,
) -> MasterData:
    """
    Download the Dhan instrument master CSV and return typed records.

    Raises httpx.HTTPError on network / HTTP failures.
    Raises ValueError if required columns are missing.
    """
    logger.info("Downloading Dhan instrument master from %s", url)
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.get(url)
        response.raise_for_status()

    raw_csv = response.text
    logger.info("Downloaded %d bytes", len(raw_csv))

    df = pd.read_csv(StringIO(raw_csv), low_memory=False)
    df.columns = df.columns.str.strip()

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Dhan master CSV missing expected columns: {missing}")

    # Normalise strings.
    for col in [
        "SEM_EXM_EXCH_ID",
        "SEM_SEGMENT",
        "SEM_INSTRUMENT_NAME",
        "SEM_SERIES",
        "SEM_TRADING_SYMBOL",
        "SEM_CUSTOM_SYMBOL",
    ]:
        df[col] = df[col].astype(str).str.strip()

    equities      = _extract_equities(df)
    index_futures = _extract_index_futures(df)

    logger.info(
        "Master parsed: %d equities, %d index futures",
        len(equities), len(index_futures),
    )
    return MasterData(equities=equities, index_futures=index_futures)


# ── Private helpers ────────────────────────────────────────────────────────────

def _extract_equities(df: pd.DataFrame) -> list[EquityRecord]:
    """NSE EQ series equities only — these map 1:1 to our symbols table."""
    mask = (
        (df["SEM_INSTRUMENT_NAME"] == _EQUITY) &
        (df["SEM_EXM_EXCH_ID"]    == "NSE")    &
        (df["SEM_SERIES"]         == "EQ")
    )
    subset = df[mask].copy()

    records: list[EquityRecord] = []
    for _, row in subset.iterrows():
        sec_id = _parse_int(row["SEM_SMST_SECURITY_ID"])
        symbol = str(row["SEM_TRADING_SYMBOL"]).strip()
        seg    = _normalise_exchange_segment(
            exchange_id=str(row["SEM_EXM_EXCH_ID"]).strip(),
            segment_code=str(row["SEM_SEGMENT"]).strip(),
        )
        if sec_id and symbol:
            records.append(EquityRecord(
                security_id      = sec_id,
                trading_symbol   = symbol,
                exchange_segment = seg,
            ))

    return records


def _extract_index_futures(df: pd.DataFrame) -> list[IndexFutureRecord]:
    """
    Front-month FUTIDX contracts for NIFTY, BANKNIFTY, SENSEX.

    Returns ALL expiries; the mapper selects the nearest active one.
    """
    subset = df[df["SEM_INSTRUMENT_NAME"] == _FUTIDX].copy()

    records: list[IndexFutureRecord] = []
    for _, row in subset.iterrows():
        sec_id     = _parse_int(row["SEM_SMST_SECURITY_ID"])
        underlying = _extract_proxy_underlying(row)
        seg        = _normalise_exchange_segment(
            exchange_id=str(row["SEM_EXM_EXCH_ID"]).strip(),
            segment_code=str(row["SEM_SEGMENT"]).strip(),
        )
        expiry     = _parse_date(str(row["SEM_EXPIRY_DATE"]).strip())
        lot_size   = _parse_int(row["SEM_LOT_UNITS"]) or 1

        if sec_id and underlying and expiry:
            records.append(IndexFutureRecord(
                security_id      = sec_id,
                underlying       = underlying,
                exchange_segment = seg,
                expiry_date      = expiry,
                lot_size         = lot_size,
            ))

    return records


def _parse_int(value) -> Optional[int]:
    try:
        v = int(float(str(value).strip()))
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _parse_date(value: str) -> Optional[date]:
    """Parse Dhan expiry date into a date, tolerating current CSV timestamp format."""
    if not value or value.lower() in ("nan", "none", ""):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def _normalise_exchange_segment(*, exchange_id: str, segment_code: str) -> str:
    exchange_id = exchange_id.upper()
    segment_code = segment_code.upper()

    mapping = {
        ("NSE", "E"): "NSE_EQ",
        ("NSE", "D"): "NSE_FNO",
        ("BSE", "E"): "BSE_EQ",
        ("BSE", "D"): "BSE_FNO",
    }
    return mapping.get((exchange_id, segment_code), segment_code)


def _extract_proxy_underlying(row: pd.Series) -> Optional[str]:
    trading_symbol = str(row["SEM_TRADING_SYMBOL"]).strip().upper()
    custom_symbol = str(row.get("SEM_CUSTOM_SYMBOL", "")).strip().upper()

    if trading_symbol.startswith("BANKNIFTY") or custom_symbol.startswith("BANKNIFTY"):
        return "BANKNIFTY"
    if trading_symbol.startswith("NIFTY-") or custom_symbol.startswith("NIFTY "):
        return "NIFTY"
    if (
        trading_symbol == "SENSEX"
        or trading_symbol.startswith("SENSEX-")
        or custom_symbol.startswith("SENSEX ")
    ):
        return "SENSEX"
    return None
