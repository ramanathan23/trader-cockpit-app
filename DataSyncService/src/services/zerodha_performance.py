from __future__ import annotations

from datetime import date
from typing import Any

import asyncpg

from .zerodha_constants import BROKER
from .zerodha_trade_metrics import base_metrics, trade_metrics
from .zerodha_trades import reconstruct, trade_rows


async def performance_summary(pool: asyncpg.Pool, start: date | None, end: date | None):
    start_date, end_date, rows = await trade_rows(pool, start, end)
    trades, pnl_stmt = reconstruct(rows), await pnl_statement(pool, start_date, end_date)
    by_account: dict[str, dict[str, Any]] = {aid: empty_account(aid) for aid in pnl_stmt}
    for trade in trades:
        acc = by_account.setdefault(trade["account_id"], empty_account(trade["account_id"]))
        acc["closed_trades"] += 1
        acc["realized_pnl"] += trade["pnl"]
        acc["entry_value"] += trade["entry_price"] * trade["quantity"]
        acc["wins"] += 1 if trade["pnl"] > 0 else 0
        acc["losses"] += 1 if trade["pnl"] < 0 else 0
    for acc in by_account.values():
        account_trades = [t for t in trades if t["account_id"] == acc["account_id"]]
        acc["win_rate_pct"] = round((acc["wins"] / acc["closed_trades"]) * 100, 2) if acc["closed_trades"] else 0
        acc["trade_return_pct"] = round((acc["realized_pnl"] / acc["entry_value"]) * 100, 2) if acc["entry_value"] else 0
        acc["realized_pnl"], acc["entry_value"] = round(acc["realized_pnl"], 2), round(acc["entry_value"], 2)
        acc.update(trade_metrics(account_trades))
        apply_statement(acc, pnl_stmt.get(acc["account_id"], {}))
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "accounts": list(by_account.values())}


def empty_account(account_id: str) -> dict[str, Any]:
    return {
        "account_id": account_id, "closed_trades": 0, "wins": 0, "losses": 0,
        "realized_pnl": 0.0, "entry_value": 0.0, **base_metrics(),
    }


def apply_statement(acc: dict[str, Any], stmt: dict[str, Any]) -> None:
    gross = float(stmt.get("realized_pnl") or 0)
    charges = float(stmt.get("charges") or 0)
    net = float(stmt.get("net_realized_pnl") or 0)
    acc["statement_realized_pnl"] = round(gross, 2)
    acc["charges"] = round(charges, 2)
    acc["realized_after_charges"] = round(net if gross else acc["realized_pnl"] - charges, 2)


async def pnl_statement(pool: asyncpg.Pool, start_date: date, end_date: date):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT account_id, SUM(realized_pnl)::float8 realized_pnl,
                   SUM(charges)::float8 charges, SUM(net_realized_pnl)::float8 net_realized_pnl
            FROM broker_pnl_statement
            WHERE broker=$1 AND statement_date >= $2 AND statement_date <= $3
            GROUP BY account_id
            """, BROKER, start_date, end_date,
        )
    return {r["account_id"]: dict(r) for r in rows}
