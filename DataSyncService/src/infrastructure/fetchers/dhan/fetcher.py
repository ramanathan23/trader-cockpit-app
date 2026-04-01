"""
Dhan API fetcher for 1-minute historical OHLCV data (dhanhq SDK).

Why Dhan for 1m:
  yfinance caps 1-min history at 7 days; Dhan provides up to 5 years
  of intraday history, with at most 90 days per API call.

Strategy:
  Split the requested range into CHUNK_DAYS windows, call
  dhanhq.intraday_minute_data() for each via asyncio.to_thread
  (SDK is synchronous), concat into a single UTC-indexed DataFrame.

Dhan docs: https://dhanhq.co/docs/v2/
"""

import asyncio
import logging
from datetime import date, datetime, timedelta

import pandas as pd
from dhanhq import dhanhq as DhanHQ

from .security_master import DhanSecurityMaster

logger = logging.getLogger(__name__)

_CHUNK_DAYS = 90


def _fetch_chunk_sync(
    dhan: DhanHQ,
    security_id: str,
    from_date: date,
    to_date: date,
) -> pd.DataFrame:
    """
    Synchronous single-chunk fetch via dhanhq SDK. Called via asyncio.to_thread.

    SDK timestamps are Unix seconds in IST (UTC+5:30) — converted to UTC here.
    """
    response = dhan.intraday_minute_data(
        security_id=security_id,
        exchange_segment=dhan.NSE,
        instrument_type="EQUITY",
        from_date=from_date.strftime("%Y-%m-%d"),
        to_date=to_date.strftime("%Y-%m-%d"),
    )

    payload = response.get("data", response) if isinstance(response, dict) else {}
    timestamps = payload.get("timestamp", [])
    if not timestamps:
        return pd.DataFrame()

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


class DhanFetcher:
    """
    Dhan API fetcher for 1-minute NSE OHLCV data.
    Satisfies the DataFetcher protocol for the '1m' interval.
    """

    def __init__(
        self,
        client_id: str,
        access_token: str,
        max_concurrency: int = 5,
        security_master_url: str = "https://images.dhan.co/api-data/api-scrip-master.csv",
        master_ttl_hours: int = 24,
    ) -> None:
        self._client_id = (client_id or "").strip()
        self._access_token = (access_token or "").strip()
        self._dhan = (
            DhanHQ(client_id=self._client_id, access_token=self._access_token)
            if self.is_configured
            else None
        )
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._master = DhanSecurityMaster(url=security_master_url, ttl_hours=master_ttl_hours)

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._access_token)

    def require_credentials(self) -> None:
        if self.is_configured:
            return
        raise RuntimeError(
            "Dhan credentials are missing in DataSyncService. "
            "Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN, then recreate the data-sync container."
        )

    async def refresh_security_master(self) -> int:
        return await self._master.refresh()

    async def fetch_1m(
        self,
        symbol: str,
        days: int = 90,
        end: date | None = None,
    ) -> pd.DataFrame:
        """Fetch `days` of 1-minute OHLCV for one symbol, split into chunks."""
        self.require_credentials()
        sec_map = await self._master.get()
        security_id = sec_map.get(symbol)
        if not security_id:
            logger.warning("Symbol %s not found in Dhan security master — skipping", symbol)
            return pd.DataFrame()

        end_date   = end or date.today()
        start_date = end_date - timedelta(days=days)
        chunks: list[pd.DataFrame] = []

        async with self._semaphore:
            cursor = start_date
            while cursor < end_date:
                chunk_end = min(cursor + timedelta(days=_CHUNK_DAYS - 1), end_date)
                try:
                    df = await asyncio.to_thread(
                        _fetch_chunk_sync, self._dhan, security_id, cursor, chunk_end
                    )
                    if not df.empty:
                        chunks.append(df)
                        logger.debug("[%s] Fetched %d bars (%s → %s)", symbol, len(df), cursor, chunk_end)
                except Exception:
                    logger.warning("[%s] Chunk failed %s → %s", symbol, cursor, chunk_end, exc_info=True)
                cursor = chunk_end + timedelta(days=1)
                await asyncio.sleep(0.05)

        if not chunks:
            return pd.DataFrame()

        result = pd.concat(chunks).sort_index()
        return result[~result.index.duplicated(keep="last")]

    async def fetch_batch(
        self,
        symbols: list[str],
        days: int = 90,
    ) -> dict[str, pd.DataFrame]:
        """Fetch 1-min data for multiple symbols concurrently (bounded by semaphore)."""
        self.require_credentials()
        tasks = {sym: asyncio.create_task(self.fetch_1m(sym, days)) for sym in symbols}
        results: dict[str, pd.DataFrame] = {}
        for sym, task in tasks.items():
            try:
                df = await task
                if not df.empty:
                    results[sym] = df
            except Exception:
                logger.warning("fetch_batch: task failed for %s", sym, exc_info=True)
        return results

    async def fetch_since(
        self,
        symbol: str,
        since: datetime,
    ) -> pd.DataFrame:
        """Incremental fetch from `since` to today."""
        self.require_credentials()
        today = date.today()
        start = since.date() if hasattr(since, "date") else since
        if start >= today:
            return pd.DataFrame()
        days = (today - start).days + 1
        return await self.fetch_1m(symbol, days=days, end=today)
