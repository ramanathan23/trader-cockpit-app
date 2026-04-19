import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import yfinance as yf

from ._yf_parser import ticker, extract_single_symbol, parse_multiindex

logger = logging.getLogger(__name__)

_INTERVAL_MAX_DAYS: dict[str, int] = {
    "2m":  60,
    "5m":  60,
    "15m": 60,
    "30m": 60,
    "1h":  730,
    "1d":  3650,
}


async def fetch_batch(
    symbols: list[str],
    interval: str,
    days: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> dict[str, pd.DataFrame]:
    if not symbols:
        return {}

    max_days       = _INTERVAL_MAX_DAYS.get(interval, 90)
    effective_days = min(days, max_days)

    now   = datetime.now(tz=timezone.utc)
    end   = end   or now
    start = start or (end - timedelta(days=effective_days))

    tickers = [ticker(s) for s in symbols]
    yf_end  = end + timedelta(days=1)   # yfinance end is exclusive

    try:
        raw: pd.DataFrame = await asyncio.to_thread(
            yf.download,
            tickers=tickers,
            start=start.strftime("%Y-%m-%d"),
            end=yf_end.strftime("%Y-%m-%d"),
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except (ValueError, KeyError, ConnectionError, OSError):
        logger.exception("yfinance download failed for batch starting with %s", symbols[:3])
        return {}

    if raw is None or raw.empty:
        return {}

    if len(symbols) == 1:
        df = extract_single_symbol(raw, symbols[0])
        return {symbols[0]: df} if not df.empty else {}

    return parse_multiindex(raw, symbols)


async def fetch_since(
    symbol: str,
    interval: str,
    since: datetime,
) -> pd.DataFrame:
    now = datetime.now(tz=timezone.utc)
    if since >= now:
        return pd.DataFrame()
    result = await fetch_batch(
        symbols=[symbol],
        interval=interval,
        days=0,
        start=since,
        end=now,
    )
    return result.get(symbol, pd.DataFrame())
