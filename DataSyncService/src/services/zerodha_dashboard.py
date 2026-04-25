from __future__ import annotations

from datetime import date
from typing import Any

import asyncpg

from ..config import settings
from .zerodha_constants import BROKER
from .zerodha_dashboard_cards import account_card
from .zerodha_performance import performance_summary


async def latest(pool: asyncpg.Pool, table: str):
    async with pool.acquire() as conn:
        return await conn.fetch(
            f"SELECT DISTINCT ON (account_id) account_id, payload, synced_at FROM {table} "
            f"WHERE broker=$1 ORDER BY account_id, snapshot_date DESC, synced_at DESC",
            BROKER,
        )


async def dashboard(pool: asyncpg.Pool, start: date | None, end: date | None) -> dict[str, Any]:
    start_date = start or date.fromisoformat(settings.zerodha_performance_start_date)
    end_date = end or date.today()
    perf = {r["account_id"]: r for r in (await performance_summary(pool, start_date, end_date))["accounts"]}
    async with pool.acquire() as conn:
        accounts = await conn.fetch("SELECT account_id, client_id, display_name, strategy_capital FROM broker_accounts WHERE broker=$1 AND is_active=TRUE ORDER BY account_id", BROKER)
        runs = await conn.fetch("SELECT DISTINCT ON (account_id) * FROM broker_sync_runs WHERE broker=$1 ORDER BY account_id, started_at DESC", BROKER)
        daily = await conn.fetch(
            "SELECT fill_timestamp::date d, COUNT(*) n FROM broker_trades_raw WHERE broker=$1 AND fill_timestamp::date >= $2 AND fill_timestamp::date <= $3 GROUP BY d ORDER BY d",
            BROKER, start_date, end_date,
        )
    margins = {r["account_id"]: r for r in await latest(pool, "broker_margins_raw")}
    positions = {r["account_id"]: r for r in await latest(pool, "broker_positions_raw")}
    holdings = {r["account_id"]: r for r in await latest(pool, "broker_holdings_raw")}
    runs_by = {r["account_id"]: r for r in runs}
    cards, totals = [], empty_totals()
    for account in accounts:
        card = account_card(
            account, margins.get(account["account_id"]), positions.get(account["account_id"]),
            holdings.get(account["account_id"]), runs_by.get(account["account_id"]), perf.get(account["account_id"], {}),
        )
        cards.append(card)
        add_totals(totals, card)
    return {
        "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
        "totals": {k: round(v, 2) if isinstance(v, float) else v for k, v in totals.items()},
        "accounts": cards,
        "daily": [{"date": r["d"].isoformat(), "cashflow": 0, "executions": int(r["n"] or 0)} for r in daily],
        "sync_note": "Kite /orders and /trades are current-day APIs. Daily sync stores history from Apr 2026 onward.",
    }


def empty_totals():
    return {"strategy_capital": 0.0, "broker_net": 0.0, "realized_pnl": 0.0, "realized_after_charges": 0.0, "charges": 0.0, "unrealized_pnl": 0.0, "open_exposure": 0.0, "open_positions": 0, "trades_today": 0, "orders_today": 0}


def add_totals(totals, card):
    for key in ["strategy_capital", "broker_net", "realized_pnl", "realized_after_charges", "charges", "unrealized_pnl", "open_exposure"]:
        totals[key] += card[key]
    totals["open_positions"] += card["open_positions_count"]
    totals["trades_today"] += card["latest_sync"]["trades_count"]
    totals["orders_today"] += card["latest_sync"]["orders_count"]
