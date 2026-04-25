from __future__ import annotations

from datetime import date
from typing import Any

import asyncpg

from ..infrastructure.zerodha.client import ZerodhaAccount
from .zerodha_auth import client
from .zerodha_charges import sync_charges
from .zerodha_constants import BROKER
from .zerodha_utils import json_text, parse_ts


async def access_token(pool: asyncpg.Pool, account_id: str) -> str | None:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT access_token FROM broker_tokens WHERE broker=$1 AND account_id=$2 AND expires_at > NOW()",
            BROKER, account_id,
        )


async def start_run(pool: asyncpg.Pool, account_id: str) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval("INSERT INTO broker_sync_runs (broker, account_id) VALUES ($1,$2) RETURNING id", BROKER, account_id)


async def sync_account(pool: asyncpg.Pool, account: ZerodhaAccount) -> dict[str, Any]:
    token = await access_token(pool, account.account_id)
    if not token:
        return {"account_id": account.account_id, "status": "login_required", "message": "Access token missing"}
    run_id = await start_run(pool, account.account_id)
    try:
        api = client(account)
        orders, trades = await api.orders(token), await api.trades(token)
        positions, holdings, margins = await api.positions(token), await api.holdings(token), await api.margins(token)
        async with pool.acquire() as conn, conn.transaction():
            await store_orders(conn, account.account_id, orders or [])
            await store_trades(conn, account.account_id, trades or [])
            charges_count = await sync_charges(conn, api, token, account.account_id, orders or [])
            await store_snapshot(conn, "broker_positions_raw", account.account_id, positions)
            await store_snapshot(conn, "broker_holdings_raw", account.account_id, holdings)
            await store_snapshot(conn, "broker_margins_raw", account.account_id, margins)
            await conn.execute(
                "UPDATE broker_sync_runs SET finished_at=NOW(), status='ok', orders_count=$2, trades_count=$3 WHERE id=$1",
                run_id, len(orders or []), len(trades or []),
            )
        return {"account_id": account.account_id, "status": "ok", "orders": len(orders or []), "trades": len(trades or []), "charges": charges_count}
    except Exception as exc:
        await mark_error(pool, run_id, account.account_id, str(exc))
        raise


async def mark_error(pool: asyncpg.Pool, run_id: int, account_id: str, error: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("UPDATE broker_sync_runs SET finished_at=NOW(), status='error', error_msg=$2 WHERE id=$1", run_id, error)
        await conn.execute(
            """
            INSERT INTO broker_tokens (broker, account_id, last_error, updated_at) VALUES ($1,$2,$3,NOW())
            ON CONFLICT (broker, account_id) DO UPDATE SET last_error=EXCLUDED.last_error, updated_at=NOW()
            """, BROKER, account_id, error,
        )


async def store_orders(conn: asyncpg.Connection, account_id: str, orders: list[dict[str, Any]]) -> None:
    await conn.executemany(
        """
        INSERT INTO broker_orders_raw (broker, account_id, order_id, trading_symbol, exchange, status, order_timestamp, payload, synced_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,NOW())
        ON CONFLICT (broker, account_id, order_id) DO UPDATE SET
          trading_symbol=EXCLUDED.trading_symbol, exchange=EXCLUDED.exchange, status=EXCLUDED.status,
          order_timestamp=EXCLUDED.order_timestamp, payload=EXCLUDED.payload, synced_at=NOW()
        """,
        [(BROKER, account_id, str(o.get("order_id")), o.get("tradingsymbol"), o.get("exchange"), o.get("status"),
          parse_ts(o.get("order_timestamp") or o.get("exchange_timestamp")), json_text(o)) for o in orders if o.get("order_id")],
    )


async def store_trades(conn: asyncpg.Connection, account_id: str, trades: list[dict[str, Any]]) -> None:
    await conn.executemany(
        """
        INSERT INTO broker_trades_raw (broker, account_id, trade_id, order_id, trading_symbol, exchange, transaction_type, quantity, average_price, fill_timestamp, payload, synced_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,NOW())
        ON CONFLICT (broker, account_id, trade_id) DO UPDATE SET payload=EXCLUDED.payload, synced_at=NOW()
        """,
        [(BROKER, account_id, str(t.get("trade_id")), str(t.get("order_id")) if t.get("order_id") else None,
          t.get("tradingsymbol"), t.get("exchange"), t.get("transaction_type"), t.get("quantity"),
          t.get("average_price"), parse_ts(t.get("fill_timestamp") or t.get("exchange_timestamp")), json_text(t))
         for t in trades if t.get("trade_id")],
    )


async def store_snapshot(conn: asyncpg.Connection, table: str, account_id: str, data: Any) -> None:
    await conn.execute(
        f"INSERT INTO {table} (broker, account_id, snapshot_date, payload, synced_at) VALUES ($1,$2,$3,$4::jsonb,NOW()) "
        f"ON CONFLICT (broker, account_id, snapshot_date) DO UPDATE SET payload=EXCLUDED.payload, synced_at=NOW()",
        BROKER, account_id, date.today(), json_text(data),
    )
