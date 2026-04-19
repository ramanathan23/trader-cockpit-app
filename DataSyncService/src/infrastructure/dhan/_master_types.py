from dataclasses import dataclass
from datetime import date

# Published daily by Dhan; no auth required.
DHAN_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

# Index underlyings used as market proxy.
PROXY_UNDERLYINGS = frozenset({"NIFTY", "BANKNIFTY", "SENSEX"})

# Columns in the Dhan master CSV that we consume.
_REQUIRED_COLS = {
    "SEM_EXM_EXCH_ID",
    "SEM_SEGMENT",
    "SEM_SMST_SECURITY_ID",
    "SEM_TRADING_SYMBOL",
    "SEM_CUSTOM_SYMBOL",
    "SEM_INSTRUMENT_NAME",
    "SEM_SERIES",
    "SEM_EXPIRY_DATE",
    "SEM_LOT_UNITS",
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
