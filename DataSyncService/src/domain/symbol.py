from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Symbol:
    symbol: str
    company_name: str
    series: str
    isin: Optional[str] = None
    listed_date: Optional[date] = None
    face_value: Optional[float] = None
