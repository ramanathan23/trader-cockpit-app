from datetime import date
from pathlib import Path

import pandas as pd

from ..domain.symbol import Symbol

_SYMBOLS_CSV = Path(__file__).parent.parent / "data" / "symbols.csv"


def load_from_csv(csv_path: Path = _SYMBOLS_CSV) -> list[Symbol]:
    """
    Parse NSE symbols.csv and return EQ-series equity records plus any INDEX
    benchmark rows (e.g. NIFTY500) needed by the scorer.

    Uses pandas with skipinitialspace=True to handle the leading spaces
    present in column names of the NSE-published CSV format.
    """
    df = pd.read_csv(csv_path, skipinitialspace=True)
    df.columns = df.columns.str.strip()

    included = df[df["SERIES"].str.strip().isin(["EQ", "INDEX"])].copy()
    included["DATE OF LISTING"] = pd.to_datetime(
        included["DATE OF LISTING"], format="mixed", dayfirst=True, errors="coerce"
    ).dt.date

    symbols: list[Symbol] = []
    for _, row in included.iterrows():
        isin   = str(row.get("ISIN NUMBER", "")).strip()
        face   = row.get("FACE VALUE")
        series = str(row["SERIES"]).strip()
        symbols.append(Symbol(
            symbol=str(row["SYMBOL"]).strip(),
            company_name=str(row["NAME OF COMPANY"]).strip(),
            series=series,
            isin=isin if isin and isin != "nan" else None,
            listed_date=row["DATE OF LISTING"] if isinstance(row["DATE OF LISTING"], date) else None,
            face_value=float(face) if pd.notna(face) else None,
        ))
    return symbols
