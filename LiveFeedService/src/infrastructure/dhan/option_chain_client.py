from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionchain"
_EXPIRY_LIST_URL  = "https://api.dhan.co/v2/optionchain/expirylist"
_MIN_INTERVAL_S   = 3.1  # Dhan rate limit: 1 per 3 seconds


class OptionChainClient:
    """Thread-safe Dhan option chain REST client with rate limiting (1 req / 3 s)."""

    def __init__(
        self,
        client_id: str,
        token_getter,
        timeout_s: float = 10.0,
    ) -> None:
        self._client_id    = client_id
        self._token_getter = token_getter
        self._timeout      = timeout_s
        self._lock         = asyncio.Lock()
        self._last_call_at = 0.0

    async def _headers(self) -> dict[str, str]:
        token = await self._token_getter()
        return {
            "Content-Type": "application/json",
            "access-token": token,
            "client-id": self._client_id,
        }

    async def _rate_limited_post(self, url: str, payload: dict) -> dict[str, Any]:
        """POST with rate limiting: max 1 call per 3 seconds."""
        async with self._lock:
            elapsed = time.monotonic() - self._last_call_at
            if elapsed < _MIN_INTERVAL_S:
                await asyncio.sleep(_MIN_INTERVAL_S - elapsed)
            headers = await self._headers()
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
            self._last_call_at = time.monotonic()
            if resp.status_code == 429:
                logger.warning("Option chain rate limited (429) — caller should retry")
                return {"status": "error", "message": "Rate limited"}
            resp.raise_for_status()
            return resp.json()

    async def get_expiry_list(
        self, underlying_scrip: int, underlying_seg: str,
    ) -> list[str]:
        """Fetch all active expiry dates for an underlying."""
        data = await self._rate_limited_post(_EXPIRY_LIST_URL, {
            "UnderlyingScrip": underlying_scrip,
            "UnderlyingSeg":   underlying_seg,
        })
        return data.get("data", [])

    async def get_option_chain(
        self, underlying_scrip: int, underlying_seg: str, expiry: str,
    ) -> dict[str, Any]:
        """Fetch full option chain for one underlying + expiry."""
        data = await self._rate_limited_post(_OPTION_CHAIN_URL, {
            "UnderlyingScrip": underlying_scrip,
            "UnderlyingSeg":   underlying_seg,
            "Expiry":          expiry,
        })
        return data.get("data", {})
