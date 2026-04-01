"""
yfinance-based OHLCV fetcher for NSE (National Stock Exchange India) symbols.

Hard limits imposed by yfinance:
  1m  → max 7 days lookback
  1d  → no practical limit

Symbols use the `.NS` suffix (e.g. RELIANCE → RELIANCE.NS).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

_NSE_SUFFIX = ".NS"
_INTERVAL_MAX_DAYS: dict[str, int] = {
    "1m":  7,
    "2m":  60,
    "5m":  60,
    "15m": 60,
    "30m": 60,
    "1h":  730,
    "1d":  3650,
}


class YFinanceFetcher:
    """yfinance OHLCV fetcher. Satisfies the DataFetcher protocol for the '1d' interval."""

    @staticmethod
    def _ticker(symbol: str) -> str:
        return f"{symbol}{_NSE_SUFFIX}"

    @staticmethod
    def _extract_single_symbol(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        ticker = f"{symbol}{_NSE_SUFFIX}"

        if isinstance(raw.columns, pd.MultiIndex):
            parsed = YFinanceFetcher._parse_multiindex(raw, [symbol])
            return parsed.get(symbol, pd.DataFrame())

        cols = {str(col).strip().lower(): col for col in raw.columns}
        required = ["open", "high", "low", "close", "volume"]
        if not all(name in cols for name in required):
            logger.debug("Single-symbol yfinance response missing OHLCV columns for %s: %s", ticker, list(raw.columns))
            return pd.DataFrame()

        df = raw[[cols["open"], cols["high"], cols["low"], cols["close"], cols["volume"]]].copy()
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
        return df.dropna(subset=["Open", "Close"])

    @staticmethod
    def _parse_multiindex(raw: pd.DataFrame, symbols: list[str]) -> dict[str, pd.DataFrame]:
        result: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            ticker = f"{symbol}{_NSE_SUFFIX}"
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
        self,
        symbols: list[str],
        interval: str,
        days: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> dict[str, pd.DataFrame]:
        if not symbols:
            return {}

        max_days = _INTERVAL_MAX_DAYS.get(interval, 90)
        effective_days = min(days, max_days)

        now = datetime.now(tz=timezone.utc)
        end = end or now
        start = start or (end - timedelta(days=effective_days))
        tickers = [self._ticker(s) for s in symbols]

        try:
            raw: pd.DataFrame = await asyncio.to_thread(
                yf.download,
                tickers=tickers,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        except Exception:
            logger.exception("yfinance download failed for batch starting with %s", symbols[:3])
            return {}

        if raw is None or raw.empty:
            return {}

        if len(symbols) == 1:
            df = self._extract_single_symbol(raw, symbols[0])
            return {symbols[0]: df} if not df.empty else {}

        return self._parse_multiindex(raw, symbols)

    async def fetch_since(
        self,
        symbol: str,
        interval: str,
        since: datetime,
    ) -> pd.DataFrame:
        now = datetime.now(tz=timezone.utc)
        if since >= now:
            return pd.DataFrame()
        result = await self.fetch_batch(
            symbols=[symbol],
            interval=interval,
            days=0,
            start=since,
            end=now,
        )
        return result.get(symbol, pd.DataFrame())
