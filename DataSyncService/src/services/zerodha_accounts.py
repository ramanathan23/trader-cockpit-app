from __future__ import annotations

from typing import Any

import asyncpg

from ..infrastructure.zerodha.client import ZerodhaAccount
from .zerodha_constants import BROKER


async def account_rows(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT account_id, client_id, display_name, api_key, api_secret, strategy_capital
            FROM broker_accounts WHERE broker = $1 AND is_active = TRUE ORDER BY account_id
            """,
            BROKER,
        )


async def configured_accounts(pool: asyncpg.Pool) -> list[ZerodhaAccount]:
    rows = await account_rows(pool)
    return [
        ZerodhaAccount(r["account_id"], r["client_id"] or r["account_id"], r["api_key"], r["api_secret"])
        for r in rows
        if r["api_key"] and r["api_secret"]
    ]


async def save_account(pool: asyncpg.Pool, data: dict[str, Any]) -> dict[str, str]:
    account_id = str(data.get("account_id") or "").strip()
    if not account_id:
        raise ValueError("account_id is required")
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO broker_accounts
              (broker, account_id, client_id, display_name, api_key, api_secret, strategy_capital, is_active, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,TRUE,NOW())
            ON CONFLICT (broker, account_id) DO UPDATE SET
              client_id=EXCLUDED.client_id, display_name=EXCLUDED.display_name,
              api_key=EXCLUDED.api_key, api_secret=EXCLUDED.api_secret,
              strategy_capital=EXCLUDED.strategy_capital, is_active=TRUE, updated_at=NOW()
            """,
            BROKER,
            account_id,
            str(data.get("client_id") or account_id).strip(),
            str(data.get("display_name") or account_id).strip(),
            str(data.get("api_key") or "").strip(),
            str(data.get("api_secret") or "").strip(),
            data.get("strategy_capital"),
        )
    return {"account_id": account_id, "status": "saved"}


async def delete_account(pool: asyncpg.Pool, account_id: str) -> dict[str, str]:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE broker_accounts SET is_active=FALSE, updated_at=NOW() WHERE broker=$1 AND account_id=$2",
            BROKER,
            account_id,
        )
    return {"account_id": account_id, "status": "disabled"}


async def get_account(pool: asyncpg.Pool, account_id: str) -> ZerodhaAccount:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT account_id, client_id, api_key, api_secret
            FROM broker_accounts WHERE broker=$1 AND account_id=$2 AND is_active=TRUE
            """,
            BROKER,
            account_id,
        )
    if row and row["api_key"] and row["api_secret"]:
        return ZerodhaAccount(row["account_id"], row["client_id"] or row["account_id"], row["api_key"], row["api_secret"])
    raise KeyError(f"Zerodha account is not configured: {account_id}")
