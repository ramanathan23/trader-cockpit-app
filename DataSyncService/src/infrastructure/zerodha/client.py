from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ZerodhaAccount:
    account_id: str
    client_id: str
    api_key: str
    api_secret: str


class ZerodhaClient:
    def __init__(self, account: ZerodhaAccount, *, base_url: str, timeout_s: float) -> None:
        self._account = account
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    async def generate_session(self, request_token: str) -> dict[str, Any]:
        checksum = hashlib.sha256(
            f"{self._account.api_key}{request_token}{self._account.api_secret}".encode("utf-8")
        ).hexdigest()
        return await self._post(
            "/session/token",
            data={
                "api_key": self._account.api_key,
                "request_token": request_token,
                "checksum": checksum,
            },
            auth=False,
        )

    async def orders(self, access_token: str) -> list[dict[str, Any]]:
        return await self._get_data("/orders", access_token)

    async def trades(self, access_token: str) -> list[dict[str, Any]]:
        return await self._get_data("/trades", access_token)

    async def positions(self, access_token: str) -> dict[str, Any]:
        return await self._get_data("/portfolio/positions", access_token)

    async def holdings(self, access_token: str) -> list[dict[str, Any]]:
        return await self._get_data("/portfolio/holdings", access_token)

    async def margins(self, access_token: str) -> dict[str, Any]:
        return await self._get_data("/user/margins", access_token)

    async def order_charges(self, access_token: str, orders: list[dict[str, Any]]) -> Any:
        payload = await self._post("/charges/orders", data=orders, auth=True, access_token=access_token)
        return payload.get("data")

    async def _get_data(self, path: str, access_token: str) -> Any:
        payload = await self._get(path, access_token=access_token)
        return payload.get("data")

    async def _get(self, path: str, *, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            res = await client.get(
                f"{self._base_url}{path}",
                headers={
                    "X-Kite-Version": "3",
                    "Authorization": f"token {self._account.api_key}:{access_token}",
                },
            )
        res.raise_for_status()
        return res.json()

    async def _post(self, path: str, *, data: Any, auth: bool, access_token: str | None = None) -> dict[str, Any]:
        headers = {"X-Kite-Version": "3"}
        if auth:
            headers["Authorization"] = f"token {self._account.api_key}:{access_token}"
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            res = await client.post(f"{self._base_url}{path}", json=data if auth else None, data=None if auth else data, headers=headers)
        res.raise_for_status()
        return res.json()
