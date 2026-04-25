from __future__ import annotations

from datetime import date
from typing import Any

import asyncpg

from ..config import settings
from .zerodha_constants import BROKER


async def trade_rows(pool: asyncpg.Pool, start: date | None, end: date | None, account_id: str | None = None):
    start_date = start or date.fromisoformat(settings.zerodha_performance_start_date)
    end_date = end or date.today()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT account_id, trading_symbol, transaction_type, quantity::float8 AS quantity,
                   average_price::float8 AS average_price, fill_timestamp, trade_id
            FROM broker_trades_raw
            WHERE broker=$1 AND fill_timestamp::date >= $2 AND fill_timestamp::date <= $3
              AND ($4::text IS NULL OR account_id=$4)
            ORDER BY account_id, trading_symbol, fill_timestamp, trade_id
            """, BROKER, start_date, end_date, account_id,
        )
    return start_date, end_date, rows


def reconstruct(rows) -> list[dict[str, Any]]:
    lots: dict[tuple[str, str], list[dict[str, Any]]] = {}
    trades: list[dict[str, Any]] = []
    for row in rows:
        side, qty, price = str(row["transaction_type"] or "").upper(), float(row["quantity"] or 0), float(row["average_price"] or 0)
        if side not in {"BUY", "SELL"} or qty <= 0:
            continue
        key, sign = (row["account_id"], row["trading_symbol"]), 1 if side == "BUY" else -1
        queue = lots.setdefault(key, [])
        while qty > 0 and queue and queue[0]["sign"] == -sign:
            lot = queue[0]
            close_qty = min(qty, lot["qty"])
            pnl = (price - lot["price"]) * close_qty if lot["sign"] == 1 else (lot["price"] - price) * close_qty
            entry_value = lot["price"] * close_qty
            trades.append({
                "account_id": row["account_id"], "symbol": row["trading_symbol"],
                "side": "long" if lot["sign"] == 1 else "short", "quantity": close_qty,
                "entry_time": lot["time"].isoformat() if lot["time"] else None,
                "exit_time": row["fill_timestamp"].isoformat() if row["fill_timestamp"] else None,
                "entry_price": lot["price"], "exit_price": price, "pnl": round(pnl, 2),
                "return_pct": round((pnl / entry_value) * 100, 2) if entry_value else 0.0,
                "result": "win" if pnl > 0 else "loss" if pnl < 0 else "flat",
                "realized_r": None, "rr_note": "Needs planned stop/target to compute true R:R",
            })
            lot["qty"] -= close_qty
            qty -= close_qty
            if lot["qty"] <= 0:
                queue.pop(0)
        if qty > 0:
            queue.append({"sign": sign, "qty": qty, "price": price, "time": row["fill_timestamp"]})
    return sorted(trades, key=lambda x: (x["exit_time"] or "", x["account_id"], x["symbol"]), reverse=True)


async def reconstructed_trades(pool: asyncpg.Pool, start: date | None, end: date | None, account_id: str | None):
    start_date, end_date, rows = await trade_rows(pool, start, end, account_id)
    trades = reconstruct(rows)
    latest_day = max((t["exit_time"][:10] for t in trades if t["exit_time"]), default=None)
    day_trades = [t for t in trades if latest_day and t["exit_time"] and t["exit_time"].startswith(latest_day)]
    return {
        "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
        "latest_trade_date": latest_day, "trades": trades[:500], "latest_day_trades": day_trades[:200],
    }


async def performance_summary(pool: asyncpg.Pool, start: date | None, end: date | None):
    start_date, end_date, rows = await trade_rows(pool, start, end)
    by_account: dict[str, dict[str, Any]] = {}
    for t in reconstruct(rows):
        acc = by_account.setdefault(t["account_id"], {"account_id": t["account_id"], "closed_trades": 0, "wins": 0, "losses": 0, "realized_pnl": 0.0, "entry_value": 0.0})
        acc["closed_trades"] += 1
        acc["realized_pnl"] += t["pnl"]
        acc["entry_value"] += t["entry_price"] * t["quantity"]
        acc["wins"] += 1 if t["pnl"] > 0 else 0
        acc["losses"] += 1 if t["pnl"] < 0 else 0
    for acc in by_account.values():
        acc["win_rate_pct"] = round((acc["wins"] / acc["closed_trades"]) * 100, 2) if acc["closed_trades"] else 0
        acc["trade_return_pct"] = round((acc["realized_pnl"] / acc["entry_value"]) * 100, 2) if acc["entry_value"] else 0
        acc["realized_pnl"], acc["entry_value"] = round(acc["realized_pnl"], 2), round(acc["entry_value"], 2)
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "accounts": list(by_account.values())}
