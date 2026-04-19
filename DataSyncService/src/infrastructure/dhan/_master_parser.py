import logging

import pandas as pd

from ._master_types import EquityRecord, IndexFutureRecord
from ._master_filter import (
    _parse_int,
    _parse_date,
    _normalise_exchange_segment,
    _extract_proxy_underlying,
)

logger = logging.getLogger(__name__)

_EQUITY = "EQUITY"
_FUTIDX = "FUTIDX"


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
        expiry   = _parse_date(str(row["SEM_EXPIRY_DATE"]).strip())
        lot_size = _parse_int(row["SEM_LOT_UNITS"]) or 1

        if sec_id and underlying and expiry:
            records.append(IndexFutureRecord(
                security_id      = sec_id,
                underlying       = underlying,
                exchange_segment = seg,
                expiry_date      = expiry,
                lot_size         = lot_size,
            ))
    return records
