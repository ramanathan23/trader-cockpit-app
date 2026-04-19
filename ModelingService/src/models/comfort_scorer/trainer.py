"""Training dataset builder and LightGBM trainer for ComfortScorer."""

from datetime import date
from typing import Tuple

import pandas as pd
import asyncpg
import lightgbm as lgb

from ._dataset_builder import build_dataset
from ._lgbm_trainer import train_lightgbm
from ._normalizers import (
    normalize_return,
    normalize_drawdown,
    normalize_volatility,
    extract_features_from_row,
)


class ComfortScorerTrainer:
    """Build training dataset and train LightGBM model."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def build_dataset(
        self, start_date: date, end_date: date
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Build training dataset from historical scores + forward outcomes."""
        return await build_dataset(self.db_pool, start_date, end_date)

    @staticmethod
    def train_lightgbm(
        X: pd.DataFrame, y: pd.Series, val_split: float = 0.2
    ) -> Tuple[lgb.Booster, dict]:
        """Train LightGBM regression model."""
        return train_lightgbm(X, y, val_split)

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
