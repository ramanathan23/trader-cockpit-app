"""Training dataset builder compatibility wrapper for ComfortScorer."""

from datetime import date
from typing import Tuple

import pandas as pd
import asyncpg

from ._dataset_builder import build_dataset
from ._normalizers import (
    normalize_return,
    normalize_drawdown,
    normalize_volatility,
    extract_features_from_row,
)


class ComfortScorerTrainer:
    """Build legacy datasets; model training has been retired."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def build_dataset(
        self, start_date: date, end_date: date
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Build training dataset from historical scores + forward outcomes."""
        return await build_dataset(self.db_pool, start_date, end_date)

    @staticmethod
    def _normalize_return(ret: float) -> float:
        return normalize_return(ret)

    @staticmethod
    def _normalize_drawdown(dd_pct: float) -> float:
        return normalize_drawdown(dd_pct)

    @staticmethod
    def _normalize_volatility(vol_pct: float) -> float:
        return normalize_volatility(vol_pct)

    @staticmethod
    def _extract_features_from_row(row) -> list:
        return extract_features_from_row(row)
