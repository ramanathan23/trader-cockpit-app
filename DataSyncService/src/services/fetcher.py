"""
yfinance-based OHLCV fetcher for NSE (National Stock Exchange India) symbols.

Hard limits imposed by yfinance:
  1m  interval → max 7 days lookback
  5m  interval → max 60 days lookback
  1d  interval → no practical limit

Strategy:
  - Initial sync: fetch 7 days of 1m + 90 days of daily per symbol
  - Patch sync:   fetch from last_data_ts to now for each symbol
  - Symbols use the `.NS` suffix (e.g. RELIANCE → RELIANCE.NS)
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

NSE_SUFFIX = ".NS"

# Maximum lookback days yfinance honours per interval
INTERVAL_MAX_DAYS: dict[str, int] = {
    "1m": 7,
    "2m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "1h": 730,
    "1d": 3650,
}


def _ticker(symbol: str) -> str:
    return f"{symbol}{NSE_SUFFIX}"


def _parse_multiindex(raw: pd.DataFrame, symbols: list[str]) -> dict[str, pd.DataFrame]:
    """
    Parse yfinance multi-ticker download result into {symbol: OHLCV DataFrame}.

    yfinance download with multiple tickers returns a MultiIndex DataFrame:
      columns level 0 = Price field (Open/High/Low/Close/Volume)
      columns level 1 = Ticker
    """
    result: dict[str, pd.DataFrame] = {}
    tickers = [_ticker(s) for s in symbols]

    for symbol, ticker in zip(symbols, tickers):
        try:
            df = pd.DataFrame({
                "Open":   raw["Open"][ticker],
                "High":   raw["High"][ticker],
                "Low":    raw["Low"][ticker],
                "Close":  raw["Close"][ticker],
                "Volume": raw["Volume"][ticker],
            })
            df = df.dropna(subset=["Open", "Close"])
            if not df.empty:
                result[symbol] = df
        except (KeyError, TypeError):
            logger.debug("No data in response for %s", ticker)

    return result


async def fetch_batch(
    symbols: list[str],
    interval: str,
    days: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV data for a batch of NSE symbols.

    Args:
        symbols: NSE symbol codes (without .NS suffix)
        interval: yfinance interval string ('1m', '1d', etc.)
        days: how many calendar days of history to request
        start: override start datetime (UTC-aware)
        end: override end datetime (UTC-aware)

    Returns:
        Mapping of symbol → DataFrame indexed by UTC timestamp
        with columns [Open, High, Low, Close, Volume].
    """
    if not symbols:
        return {}

    max_days = INTERVAL_MAX_DAYS.get(interval, 90)
    effective_days = min(days, max_days)

    now = datetime.now(tz=timezone.utc)
    end = end or now
    start = start or (end - timedelta(days=effective_days))

    tickers = [_ticker(s) for s in symbols]

    try:
        raw: pd.DataFrame = await asyncio.to_thread(
            yf.download,
            tickers=tickers,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        logger.exception("yfinance download failed for batch starting with %s", symbols[:3])
        return {}

    if raw is None or raw.empty:
        logger.warning("Empty response from yfinance for batch %s...", symbols[:3])
        return {}

    # Single-ticker download returns flat columns (no MultiIndex)
    if len(symbols) == 1:
        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df = df.dropna(subset=["Open", "Close"])
        return {symbols[0]: df} if not df.empty else {}

    return _parse_multiindex(raw, symbols)


async def fetch_since(
    symbol: str,
    interval: str,
    since: datetime,
) -> pd.DataFrame:
    """
    Fetch data for one symbol from `since` to now (patch sync).
    Returns empty DataFrame if nothing is available.
    """
    now = datetime.now(tz=timezone.utc)
    if since >= now:
        return pd.DataFrame()

    result = await fetch_batch(
        symbols=[symbol],
        interval=interval,
        days=0,   # unused — start/end override takes precedence
        start=since,
        end=now,
    )
    return result.get(symbol, pd.DataFrame())
