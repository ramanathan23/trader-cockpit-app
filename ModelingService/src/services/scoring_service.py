"""
ScoringService — batch-scores all symbols for a given date and persists
comfort scores (and any future models) into model_predictions.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import date

import asyncpg

from ..config import settings
from ..core.base_model import PredictionResult
from ..core.model_registry import ModelRegistry
from ..repositories.prediction_repository import PredictionRepository
from ..models.comfort_scorer._model_predict import apply_comfort_v3

logger = logging.getLogger(__name__)


@dataclass
class ScoreRunResult:
    model_name: str
    score_date: date
    total: int
    success: int
    failed: int
    stored: int


class ScoringService:
    """Fetch all scored symbols, run model inference, persist predictions."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        registry: ModelRegistry,
        prediction_repo: PredictionRepository,
    ) -> None:
        self._pool = pool
        self._registry = registry
        self._prediction_repo = prediction_repo
        self._semaphore = asyncio.Semaphore(settings.score_concurrency)

    async def run_all(self, model_name: str, score_date: date) -> ScoreRunResult:
        """
        Score all symbols that have daily_scores for score_date.
        Returns summary of results.
        """
        model = self._registry.get_model(model_name)
        if model.model is None:
            raise RuntimeError(f"Model '{model_name}' not loaded")

        symbols = await self._fetch_scored_symbols(score_date)
        if not symbols:
            logger.warning("No symbols in daily_scores for %s", score_date)
            return ScoreRunResult(model_name, score_date, 0, 0, 0, 0)

        logger.info(
            "Scoring %d symbols with '%s' for %s", len(symbols), model_name, score_date
        )

        results = await asyncio.gather(
            *[self._score_one(model_name, symbol, score_date) for symbol in symbols]
        )

        predictions = [r for r in results if r is not None]
        failed = len(symbols) - len(predictions)
        stored = await self._prediction_repo.bulk_insert(predictions)

        logger.info(
            "Scoring complete: %d/%d succeeded, %d stored, %d failed",
            len(predictions), len(symbols), stored, failed,
        )
        return ScoreRunResult(
            model_name=model_name,
            score_date=score_date,
            total=len(symbols),
            success=len(predictions),
            failed=failed,
            stored=stored,
        )

    async def _score_one(
        self, model_name: str, symbol: str, score_date: date
    ) -> PredictionResult | None:
        async with self._semaphore:
            try:
                model = self._registry.get_model(model_name)
                features = await model.extract_features(symbol, score_date)
                prediction = await model.predict(features)
                if model_name == "comfort_scorer":
                    ctx = await self._fetch_intraday_context(symbol, score_date)
                    prediction = apply_comfort_v3(
                        prediction,
                        ctx.get("iss_score"),
                        ctx.get("pullback_depth_pred"),
                        ctx.get("session_type_pred"),
                    )
                return PredictionResult(
                    model_name=model_name,
                    model_version=model.version,
                    symbol=symbol,
                    prediction_date=score_date,
                    predictions=prediction,
                    confidence=prediction.get("confidence"),
                )
            except Exception as e:
                logger.warning("Score failed for %s on %s: %s", symbol, score_date, e)
                return None

    async def _fetch_scored_symbols(self, score_date: date) -> list[str]:
        """Return all symbols that have daily_scores for the given date."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT symbol FROM daily_scores WHERE score_date = $1",
                score_date,
            )
        return [row["symbol"] for row in rows]

    async def _fetch_intraday_context(self, symbol: str, score_date: date) -> dict:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT sip.iss_score, isp.pullback_depth_pred, isp.session_type_pred
                FROM (SELECT $1::text AS symbol) sym
                LEFT JOIN symbol_intraday_profile sip ON sip.symbol = sym.symbol
                LEFT JOIN intraday_session_predictions isp
                    ON isp.symbol = sym.symbol AND isp.prediction_date = $2
            """, symbol, score_date)
        if not row:
            return {}
        return {
            "iss_score": float(row["iss_score"]) if row["iss_score"] is not None else None,
            "pullback_depth_pred": float(row["pullback_depth_pred"]) if row["pullback_depth_pred"] is not None else None,
            "session_type_pred": row["session_type_pred"],
        }
