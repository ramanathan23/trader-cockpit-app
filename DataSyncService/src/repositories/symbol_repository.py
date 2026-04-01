"""
Symbol persistence: CSV parsing and database upserts.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path

import asyncpg

from ..domain.models import Symbol

logger = logging.getLogger(__name__)

_SYMBOLS_CSV = Path(__file__).parent.parent / "data" / "symbols.csv"


def _parse_date(val: str):
    val = val.strip()
    for fmt in ("%d-%b-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _parse_float(val: str):
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None


def load_from_csv() -> list[Symbol]:
    """Parse symbols.csv and return EQ-series Symbol records."""
    rows: list[Symbol] = []
    with open(_SYMBOLS_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            series = row.get(" SERIES", "").strip()
            if series != "EQ":
                continue
            rows.append(Symbol(
                symbol=row["SYMBOL"].strip(),
                company_name=row["NAME OF COMPANY"].strip(),
                series=series,
                isin=row[" ISIN NUMBER"].strip(),
                listed_date=_parse_date(row.get(" DATE OF LISTING", "")),
                face_value=_parse_float(row.get(" FACE VALUE", "")),
            ))
    return rows


class SymbolRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert_many(self, symbols: list[Symbol]) -> int:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany("""
                    INSERT INTO symbols (symbol, company_name, series, isin, listed_date, face_value)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (symbol) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        series       = EXCLUDED.series,
                        isin         = EXCLUDED.isin
                """, [(s.symbol, s.company_name, s.series,
                       s.isin, s.listed_date, s.face_value) for s in symbols])
        logger.info("Upserted %d symbols", len(symbols))
        return len(symbols)

    async def list_by_series(self, series: str = "EQ") -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT symbol, company_name, series, isin, listed_date "
                "FROM symbols WHERE series = $1 ORDER BY symbol",
                series.upper(),
            )
        return [dict(r) for r in rows]
