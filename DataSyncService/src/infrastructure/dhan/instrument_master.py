"""
Dhan instrument master: download, parse, and expose as typed records.

Dhan publishes a daily CSV at DHAN_MASTER_URL containing every tradable
instrument with its security ID, exchange segment, series, expiry, etc.

The parsed output is intentionally kept as plain dataclasses — callers
(instrument_mapper) decide what to do with each record.
"""

from ._master_types import (
    DHAN_MASTER_URL,
    PROXY_UNDERLYINGS,
    EquityRecord,
    IndexFutureRecord,
    MasterData,
)
from ._master_loader import download_and_parse

__all__ = [
    "DHAN_MASTER_URL",
    "PROXY_UNDERLYINGS",
    "EquityRecord",
    "IndexFutureRecord",
    "MasterData",
    "download_and_parse",
]

