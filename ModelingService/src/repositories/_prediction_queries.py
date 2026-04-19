"""Standalone query functions for prediction repository."""

from datetime import date
from typing import List

import asyncpg


async def fetch_latest_predictions(
    pool: asyncpg.Pool,
    model_name: str,
    symbol: str,
    limit: int = 1,
) -> List[dict]:
    """Get latest predictions for a symbol."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                id, model_name, model_version, symbol, prediction_date,
                predictions, confidence, created_at
            FROM model_predictions
            WHERE model_name = $1 AND symbol = $2
            ORDER BY prediction_date DESC
            LIMIT $3
        """, model_name, symbol, limit)
        return [dict(row) for row in rows]


async def fetch_predictions_by_date(
    pool: asyncpg.Pool,
    model_name: str,
    prediction_date: date,
) -> List[dict]:
    """Get all predictions for a specific date."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                id, model_name, model_version, symbol, prediction_date,
                predictions, confidence, created_at
            FROM model_predictions
            WHERE model_name = $1 AND prediction_date = $2
            ORDER BY symbol
        """, model_name, prediction_date)
        return [dict(row) for row in rows]
