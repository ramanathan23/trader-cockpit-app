from __future__ import annotations

import csv
import hashlib
import io
from typing import Any

import asyncpg

from .zerodha_constants import BROKER
from .zerodha_utils import json_text, parse_ts


def pick(row: dict[str, str], *names: str) -> str:
    lowered = {k.lower().strip(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()].strip()
    return ""


def trade_record(account_id: str, row: dict[str, str], idx: int) -> tuple:
    symbol = pick(row, "symbol", "tradingsymbol", "trading_symbol")
    trade_id = pick(row, "trade_id", "trade id")
    order_id = pick(row, "order_id", "order id")
    time_text = pick(row, "order_execution_time", "fill_timestamp", "exchange_timestamp", "trade_date")
    if not trade_id:
        raw = f"{account_id}|{order_id}|{symbol}|{time_text}|{idx}"
        trade_id = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]
    return (
        BROKER, account_id, trade_id, order_id or None, symbol,
        pick(row, "exchange"), pick(row, "trade_type", "transaction_type").upper(),
        float(pick(row, "quantity", "qty") or 0), float(pick(row, "price", "average_price") or 0),
        parse_ts(time_text), json_text(row),
    )


async def import_tradebook_csv(pool: asyncpg.Pool, account_id: str, csv_text: str) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    rows = [row for row in reader if any((value or "").strip() for value in row.values())]
    records = [trade_record(account_id, row, idx) for idx, row in enumerate(rows, 1)]
    records = [record for record in records if record[4] and record[6] in {"BUY", "SELL"} and record[7] > 0]
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO broker_trades_raw
              (broker, account_id, trade_id, order_id, trading_symbol, exchange, transaction_type,
               quantity, average_price, fill_timestamp, payload, synced_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,NOW())
            ON CONFLICT (broker, account_id, trade_id) DO UPDATE SET
              order_id=EXCLUDED.order_id, trading_symbol=EXCLUDED.trading_symbol,
              exchange=EXCLUDED.exchange, transaction_type=EXCLUDED.transaction_type,
              quantity=EXCLUDED.quantity, average_price=EXCLUDED.average_price,
              fill_timestamp=EXCLUDED.fill_timestamp, payload=EXCLUDED.payload, synced_at=NOW()
            """,
            records,
        )
    return {"account_id": account_id, "rows_read": len(rows), "trades_imported": len(records)}
