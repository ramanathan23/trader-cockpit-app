from __future__ import annotations

import logging
from datetime import date
from typing import Any

import asyncpg

from .zerodha_accounts import configured_accounts, delete_account, save_account
from .zerodha_auth import complete_login, infer_single_account_id, list_accounts, login_url
from .zerodha_dashboard import dashboard
from .zerodha_history_import import import_tradebook_csv
from .zerodha_ingest import sync_account
from .zerodha_performance import performance_summary
from .zerodha_pnl_import import import_pnl_csv
from .zerodha_trades import reconstructed_trades

logger = logging.getLogger(__name__)


class ZerodhaSyncService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_accounts(self) -> list[dict[str, Any]]:
        return await list_accounts(self._pool)

    async def save_account(self, payload: dict[str, Any]) -> dict[str, str]:
        return await save_account(self._pool, payload)

    async def delete_account(self, account_id: str) -> dict[str, str]:
        return await delete_account(self._pool, account_id)

    async def login_url(self, account_id: str) -> str:
        return await login_url(self._pool, account_id)

    async def complete_login(self, account_id: str, request_token: str) -> dict[str, Any]:
        return await complete_login(self._pool, account_id, request_token)

    async def infer_single_account_id(self) -> str | None:
        return await infer_single_account_id(self._pool)

    async def sync_all(self) -> dict[str, Any]:
        accounts = await configured_accounts(self._pool)
        if not accounts:
            return {"accounts": [], "message": "No active Zerodha accounts configured"}
        results = []
        for account in accounts:
            try:
                results.append(await sync_account(self._pool, account))
            except Exception as exc:
                logger.exception("Zerodha sync failed for %s", account.account_id)
                results.append({"account_id": account.account_id, "status": "error", "message": str(exc)})
        return {"accounts": results}

    async def performance_summary(self, start: date | None = None, end: date | None = None) -> dict[str, Any]:
        return await performance_summary(self._pool, start, end)

    async def reconstructed_trades(
        self, start: date | None = None, end: date | None = None, account_id: str | None = None
    ) -> dict[str, Any]:
        return await reconstructed_trades(self._pool, start, end, account_id)

    async def dashboard(self, start: date | None = None, end: date | None = None) -> dict[str, Any]:
        return await dashboard(self._pool, start, end)

    async def import_tradebook_csv(self, account_id: str, csv_text: str) -> dict[str, Any]:
        return await import_tradebook_csv(self._pool, account_id, csv_text)

    async def import_pnl_csv(self, account_id: str, csv_text: str) -> dict[str, Any]:
        return await import_pnl_csv(self._pool, account_id, csv_text)
