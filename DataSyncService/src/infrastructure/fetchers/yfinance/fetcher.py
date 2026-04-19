"""
yfinance-based OHLCV fetcher for NSE (National Stock Exchange India) symbols.

Hard limits imposed by yfinance:
  1d  → no practical limit

Symbols use the `.NS` suffix (e.g. RELIANCE → RELIANCE.NS).
"""

from datetime import datetime
from typing import Optional

import pandas as pd

from ._yf_client import fetch_batch, fetch_since


class YFinanceFetcher:
    """yfinance OHLCV fetcher. Satisfies the DataFetcher protocol for the '1d' interval."""

    async def fetch_batch(
        self,
        symbols: list[str],
        interval: str,
        days: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> dict[str, pd.DataFrame]:
        return await fetch_batch(symbols, interval, days, start, end)

    async def fetch_since(
        self,
        symbol: str,
        interval: str,
        since: datetime,
    ) -> pd.DataFrame:
        return await fetch_since(symbol, interval, since)

