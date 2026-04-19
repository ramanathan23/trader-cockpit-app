"""Repository for model predictions storage."""

import logging
from datetime import date
from typing import List

import asyncpg

from ..core.base_model import PredictionResult
from ._prediction_queries import fetch_latest_predictions, fetch_predictions_by_date

logger = logging.getLogger(__name__)


class PredictionRepository:
    """Store and retrieve model predictions."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def insert(self, prediction: PredictionResult) -> int:
        """Insert a single prediction. Returns prediction_id."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO model_predictions
                    (model_name, model_version, symbol, prediction_date,
                     predictions, confidence, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (model_name, symbol, prediction_date) DO UPDATE
                SET predictions = EXCLUDED.predictions,
                    confidence = EXCLUDED.confidence,
                    model_version = EXCLUDED.model_version,
                    created_at = EXCLUDED.created_at
                RETURNING id
            """,
                prediction.model_name,
                prediction.model_version,
                prediction.symbol,
                prediction.prediction_date,
                prediction.predictions,
                prediction.confidence,
            )
            return row['id']

    async def bulk_insert(self, predictions: List[PredictionResult]) -> int:
        """Insert multiple predictions. Returns count inserted."""
        if not predictions:
            return 0
        count = 0
        for pred in predictions:
            try:
                await self.insert(pred)
                count += 1
            except Exception as e:
                logger.error(f"Failed to insert prediction for {pred.symbol}: {e}")
        return count

    async def get_latest(
        self, model_name: str, symbol: str, limit: int = 1
    ) -> List[dict]:
        """Get latest predictions for a symbol."""
        return await fetch_latest_predictions(self.pool, model_name, symbol, limit)

    async def get_by_date(
        self, model_name: str, prediction_date: date
    ) -> List[dict]:
        """Get all predictions for a specific date."""
        return await fetch_predictions_by_date(self.pool, model_name, prediction_date)
