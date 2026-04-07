"""
Symbol persistence: CSV loading and database upserts.
"""

import logging
from datetime import date
from pathlib import Path

import asyncpg
import pandas as pd

from ..domain.models import Symbol

logger = logging.getLogger(__name__)

_SYMBOLS_CSV = Path(__file__).parent.parent / "data" / "symbols.csv"


def load_from_csv(csv_path: Path = _SYMBOLS_CSV) -> list[Symbol]:
    """
    Parse NSE symbols.csv and return EQ-series Symbol records.

    Uses pandas with skipinitialspace=True to handle the leading spaces
    present in column names of the NSE-published CSV format.
    """
    df = pd.read_csv(csv_path, skipinitialspace=True)
    df.columns = df.columns.str.strip()

    eq = df[df["SERIES"].str.strip() == "EQ"].copy()
    eq["DATE OF LISTING"] = pd.to_datetime(
        eq["DATE OF LISTING"], format="mixed", dayfirst=True, errors="coerce"
    ).dt.date

    symbols: list[Symbol] = []
    for _, row in eq.iterrows():
        isin = str(row.get("ISIN NUMBER", "")).strip()
        face = row.get("FACE VALUE")
        symbols.append(Symbol(
            symbol=str(row["SYMBOL"]).strip(),
            company_name=str(row["NAME OF COMPANY"]).strip(),
            series="EQ",
            isin=isin if isin and isin != "nan" else None,
            listed_date=row["DATE OF LISTING"] if isinstance(row["DATE OF LISTING"], date) else None,
            face_value=float(face) if pd.notna(face) else None,
        ))
    return symbols


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
