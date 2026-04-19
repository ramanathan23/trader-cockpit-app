from datetime import date
from typing import Optional

import pandas as pd


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
    exchange_id  = exchange_id.upper()
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
    custom_symbol  = str(row.get("SEM_CUSTOM_SYMBOL", "")).strip().upper()

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
