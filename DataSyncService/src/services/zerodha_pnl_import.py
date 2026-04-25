from __future__ import annotations

import csv
import hashlib
import io
from datetime import date
from typing import Any

import asyncpg

from .zerodha_constants import BROKER
from .zerodha_history_import import pick
from .zerodha_utils import json_text, money_float


def num(row: dict[str, str], *names: str) -> float:
    text = pick(row, *names).replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def stmt_date(row: dict[str, str]) -> date | None:
    text = pick(row, "date", "trade_date", "exit_date", "statement_date")
    if not text:
        return None
    for part in [text[:10], text]:
        try:
            return date.fromisoformat(part)
        except ValueError:
            continue
    return None


def charges(row: dict[str, str]) -> float:
    direct = num(row, "charges", "total_charges", "total charges")
    if direct:
        return abs(direct)
    return sum(num(row, name) for name in ["brokerage", "stt", "transaction_tax", "gst", "sebi", "stamp_duty"])


def record(account_id: str, row: dict[str, str], idx: int) -> tuple:
    gross = num(row, "realized_pnl", "realised_pnl", "gross_pnl", "gross realized p&l", "p&l")
    fee = charges(row)
    net = num(row, "net_realized_pnl", "net realised", "net realized", "net p&l")
    if not gross and net:
        gross = net + fee
    if not net:
        net = gross - fee
    symbol = pick(row, "symbol", "tradingsymbol", "scrip")
    raw = f"{account_id}|{stmt_date(row)}|{symbol}|{gross}|{fee}|{net}|{idx}"
    return (
        BROKER, account_id, hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24],
        stmt_date(row), symbol or None, pick(row, "segment") or None,
        gross, fee, net, json_text(row),
    )


async def import_pnl_csv(pool: asyncpg.Pool, account_id: str, csv_text: str) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    rows = [row for row in reader if any((value or "").strip() for value in row.values())]
    return await import_pnl_rows(pool, account_id, rows)


async def import_pnl_rows(pool: asyncpg.Pool, account_id: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    records = [record(account_id, row, idx) for idx, row in enumerate(rows, 1)]
    records = [r for r in records if r[3] and (r[6] or r[7] or r[8])]
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO broker_pnl_statement
              (broker, account_id, row_hash, statement_date, trading_symbol, segment,
               realized_pnl, charges, net_realized_pnl, payload, imported_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,NOW())
            ON CONFLICT (broker, account_id, row_hash) DO UPDATE SET
              realized_pnl=EXCLUDED.realized_pnl, charges=EXCLUDED.charges,
              net_realized_pnl=EXCLUDED.net_realized_pnl, payload=EXCLUDED.payload, imported_at=NOW()
            """,
            records,
        )
    return {"account_id": account_id, "rows_read": len(rows), "pnl_rows_imported": len(records)}
