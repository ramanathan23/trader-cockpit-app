from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

import asyncpg

from ..infrastructure.zerodha.client import ZerodhaClient
from .zerodha_constants import BROKER
from .zerodha_utils import json_text, money_float


def charge_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for order in orders:
        qty = order.get("filled_quantity") or order.get("quantity")
        price = order.get("average_price")
        if order.get("status") != "COMPLETE" or not qty or not price:
            continue
        out.append({
            "order_id": str(order.get("order_id")), "exchange": order.get("exchange"),
            "tradingsymbol": order.get("tradingsymbol"), "transaction_type": order.get("transaction_type"),
            "variety": order.get("variety") or "regular", "product": order.get("product"),
            "order_type": order.get("order_type") or "MARKET", "quantity": int(qty), "average_price": float(price),
        })
    return out


async def sync_charges(conn: asyncpg.Connection, api: ZerodhaClient, token: str, account_id: str, orders: list[dict[str, Any]]) -> int:
    req = charge_orders(orders)
    if not req:
        return 0
    rows = await api.order_charges(token, req) or []
    await conn.executemany(
        """
        INSERT INTO broker_pnl_statement
          (broker, account_id, row_hash, statement_date, trading_symbol, segment,
           realized_pnl, charges, net_realized_pnl, payload, imported_at)
        VALUES ($1,$2,$3,$4,$5,$6,0,$7,$8,$9::jsonb,NOW())
        ON CONFLICT (broker, account_id, row_hash) DO UPDATE SET
          charges=EXCLUDED.charges, net_realized_pnl=EXCLUDED.net_realized_pnl,
          payload=EXCLUDED.payload, imported_at=NOW()
        """,
        [charge_record(account_id, row) for row in rows],
    )
    return len(rows)


def charge_record(account_id: str, row: dict[str, Any]) -> tuple:
    charge = money_float((row.get("charges") or {}).get("total"))
    raw = f"{account_id}|{date.today()}|{row.get('tradingsymbol')}|{row.get('transaction_type')}|{row.get('quantity')}|{row.get('price')}|{charge}"
    return (
        BROKER, account_id, hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24],
        date.today(), row.get("tradingsymbol"), row.get("exchange"), charge, -charge, json_text(row),
    )
