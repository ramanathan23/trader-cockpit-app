"""
Dhan Historical Charts API — low-level async client.

Endpoint: POST https://api.dhan.co/v2/charts/historical
  securityId      : Dhan numeric security ID (as string)
  exchangeSegment : "NSE_EQ" | "BSE_EQ" | "NSE_FNO" | ...
  instrument      : "EQUITY" for spot equities
  interval        : "1" for 1-minute bars
  fromDate        : "YYYY-MM-DD"
  toDate          : "YYYY-MM-DD"   (max 90 calendar days per request)

Response: { "open": [...], "high": [...], "low": [...],
            "close": [...], "volume": [...], "timestamp": [...] }
  timestamps are Unix seconds (UTC).
"""
import logging
from datetime import date

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

_INSTRUMENT_EQUITY = "EQUITY"
_INTERVAL_1MIN = "1"


def _parse_response(payload: dict) -> pd.DataFrame:
    """Convert Dhan response dict → OHLCV DataFrame indexed by UTC timestamps."""
    timestamps = payload.get("timestamp") or []
    if not timestamps:
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "Open":   payload["open"],
            "High":   payload["high"],
            "Low":    payload["low"],
            "Close":  payload["close"],
            "Volume": payload["volume"],
        },
        index=pd.to_datetime(timestamps, unit="s", utc=True),
    )
    df.index.name = "time"
    return df.dropna(subset=["Open", "Close"])


async def fetch_1min_ohlcv(
    client: httpx.AsyncClient,
    url: str,
    security_id: int,
    exchange_segment: str,
    from_date: date,
    to_date: date,
) -> pd.DataFrame:
    """
    Single 1-min OHLCV request for one security. Returns empty DataFrame on any error.
    Caller is responsible for rate limiting.
    """
    payload = {
        "securityId":      str(security_id),
        "exchangeSegment": exchange_segment,
        "instrument":      _INSTRUMENT_EQUITY,
        "interval":        _INTERVAL_1MIN,
        "ott":             False,
        "fromDate":        from_date.strftime("%Y-%m-%d"),
        "toDate":          to_date.strftime("%Y-%m-%d"),
    }
    try:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict) or "timestamp" not in data:
            logger.warning(
                "Unexpected Dhan response for security_id=%s: %s",
                security_id, str(data)[:200],
            )
            return pd.DataFrame()
        return _parse_response(data)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Dhan HTTP %d for security_id=%s: %s",
            exc.response.status_code, security_id, exc,
        )
        return pd.DataFrame()
    except (httpx.RequestError, ValueError, KeyError) as exc:
        logger.warning("Dhan fetch error for security_id=%s: %s", security_id, exc)
        return pd.DataFrame()
