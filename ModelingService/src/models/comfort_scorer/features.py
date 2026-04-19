"""Feature extraction for ComfortScorer model."""

import logging
from datetime import date
from typing import Optional, Dict, Any

import numpy as np
import asyncpg

from ._feature_names import FEATURE_NAMES
from ._feature_extract import fetch_features, _encode_weekly_bias

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract features from daily_scores and symbol_metrics tables."""

    FEATURE_NAMES = FEATURE_NAMES

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def build_features(
        self,
        symbol: str,
        date: date,
        context: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """Build 28-dim feature vector for a symbol on given date."""
        return await fetch_features(self.db_pool, symbol, date, context)

    @staticmethod
    def _encode_weekly_bias(bias: Optional[str]) -> float:
        """Encode weekly bias: BULLISH=1, NEUTRAL=0, BEARISH=-1."""
        return _encode_weekly_bias(bias)
