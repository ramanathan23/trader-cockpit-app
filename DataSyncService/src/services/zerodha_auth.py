from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any
from urllib.parse import urlencode

import asyncpg

from ..config import settings
from ..infrastructure.zerodha.client import ZerodhaClient
from .zerodha_accounts import account_rows, get_account
from .zerodha_constants import BROKER
from .zerodha_utils import json_text


def client(account) -> ZerodhaClient:
    return ZerodhaClient(account, base_url=settings.zerodha_api_base_url, timeout_s=settings.zerodha_timeout_s)


async def token_status(pool: asyncpg.Pool) -> dict[str, dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT account_id, login_time, expires_at, last_error FROM broker_tokens WHERE broker=$1", BROKER)
    now = datetime.now(UTC)
    return {
        r["account_id"]: {
            "status": "connected" if r["expires_at"] and r["expires_at"] > now and not r["last_error"] else "expired",
            "login_time": r["login_time"].isoformat() if r["login_time"] else None,
            "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
            "last_error": r["last_error"],
        }
        for r in rows
    }


async def list_accounts(pool: asyncpg.Pool) -> list[dict[str, Any]]:
    rows, tokens = await account_rows(pool), await token_status(pool)
    out = []
    for r in rows:
        has_creds = bool(r["api_key"] and r["api_secret"])
        out.append({
            "account_id": r["account_id"], "client_id": r["client_id"], "display_name": r["display_name"],
            "broker": BROKER, "strategy_capital": float(r["strategy_capital"]) if r["strategy_capital"] else None,
            "has_credentials": has_creds, "login_url": await login_url(pool, r["account_id"]) if has_creds else "",
            **tokens.get(r["account_id"], {"status": "not_connected"}),
        })
    return out


async def login_url(pool: asyncpg.Pool, account_id: str) -> str:
    account = await get_account(pool, account_id)
    params = urlencode({"api_key": account.api_key, "v": "3", "redirect_params": urlencode({"account_id": account.account_id})})
    return f"{settings.zerodha_login_base_url}?{params}"


async def complete_login(pool: asyncpg.Pool, account_id: str, request_token: str) -> dict[str, Any]:
    account = await get_account(pool, account_id)
    data = (await client(account).generate_session(request_token)).get("data") or {}
    if not data.get("access_token"):
        raise ValueError("Zerodha session response did not include access_token")
    now = datetime.now(UTC)
    expires = datetime.combine((now + timedelta(days=1)).date(), time(6), tzinfo=UTC)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO broker_tokens
              (broker, account_id, access_token, public_token, user_id, user_name, login_time, expires_at, last_error, raw_payload, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NULL,$9::jsonb,NOW())
            ON CONFLICT (broker, account_id) DO UPDATE SET
              access_token=EXCLUDED.access_token, public_token=EXCLUDED.public_token,
              user_id=EXCLUDED.user_id, user_name=EXCLUDED.user_name, login_time=EXCLUDED.login_time,
              expires_at=EXCLUDED.expires_at, last_error=NULL, raw_payload=EXCLUDED.raw_payload, updated_at=NOW()
            """,
            BROKER, account.account_id, data.get("access_token"), data.get("public_token"),
            data.get("user_id"), data.get("user_name"), now, expires, json_text(data),
        )
    return {"account_id": account.account_id, "status": "connected", "expires_at": expires.isoformat()}


async def infer_single_account_id(pool: asyncpg.Pool) -> str | None:
    ids = [r["account_id"] for r in await account_rows(pool) if r["api_key"] and r["api_secret"]]
    return ids[0] if len(ids) == 1 else None
