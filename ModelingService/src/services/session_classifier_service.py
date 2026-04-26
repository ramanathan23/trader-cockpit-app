from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import asyncpg
import pandas as pd

from ..models.comfort_scorer._model_predict import apply_comfort_v3
from ..config import settings
from ..models.session_classifier._predict import predict_session
from ..models.session_classifier._train import train_pullback_regressor, train_session_classifier

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")
_MODEL_VERSION = "session_v1"


class SessionClassifierService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._model_dir = Path(settings.model_base_path) / "session_classifier"
        self._classifier = None
        self._pullback = None

    async def train(self) -> dict:
        sessions = await self._load_training_sessions()
        if sessions.empty:
            raise ValueError("No intraday_training_sessions rows found")
        classifier, cls_metrics = train_session_classifier(sessions)
        pullback, pb_metrics = train_pullback_regressor(sessions)

        self._model_dir.mkdir(parents=True, exist_ok=True)
        import joblib

        joblib.dump(classifier, self._model_dir / "lgbm_session_classifier.pkl")
        joblib.dump(pullback, self._model_dir / "lgbm_pullback_regressor.pkl")
        (self._model_dir / "metadata.json").write_text(
            json.dumps({
                "model_version": _MODEL_VERSION,
                "trained_at": datetime.now(tz=_IST).isoformat(),
                "accuracy": cls_metrics["accuracy"],
                "pullback_mae": pb_metrics["mae"],
            }, indent=2),
            encoding="utf-8",
        )
        self._classifier = classifier
        self._pullback = pullback
        return {
            "model_version": _MODEL_VERSION,
            "accuracy": cls_metrics["accuracy"],
            "class_report": cls_metrics["class_report"],
            "pullback_mae": pb_metrics["mae"],
        }

    async def score_all(self, score_date: date | None = None) -> dict:
        score_date = score_date or datetime.now(tz=_IST).date()
        self._ensure_loaded()
        cleared = await self._clear_predictions_without_profile(score_date)
        symbols = await self._fetch_symbols_for_scoring(score_date)
        records = []
        for symbol in symbols:
            features = await self._build_prediction_features(symbol, score_date)
            if not features:
                continue
            pred = predict_session(self._classifier, self._pullback, features)
            records.append(_prediction_record(symbol, score_date, pred))
        written = await self._upsert_predictions(records)
        comfort_updated = await self._update_comfort_v3(score_date)
        return {
            "symbols_scored": written,
            "stale_predictions_cleared": cleared,
            "comfort_v3_updated": comfort_updated,
            "model_version": _MODEL_VERSION,
        }

    async def predict_one(self, symbol: str, prediction_date: date | None = None) -> dict:
        prediction_date = prediction_date or datetime.now(tz=_IST).date()
        row = await self._fetch_prediction(symbol, prediction_date)
        if row:
            return row
        self._ensure_loaded()
        features = await self._build_prediction_features(symbol, prediction_date)
        if not features:
            raise ValueError(f"No feature row available for {symbol} on {prediction_date}")
        pred = predict_session(self._classifier, self._pullback, features)
        await self._upsert_predictions([_prediction_record(symbol, prediction_date, pred)])
        return await self._fetch_prediction(symbol, prediction_date) or pred

    async def _load_training_sessions(self) -> pd.DataFrame:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM intraday_training_sessions ORDER BY session_date ASC")
        return pd.DataFrame([dict(r) for r in rows])

    def _ensure_loaded(self) -> None:
        if self._classifier is not None:
            return
        import joblib

        classifier_path = self._model_dir / "lgbm_session_classifier.pkl"
        pullback_path = self._model_dir / "lgbm_pullback_regressor.pkl"
        if not classifier_path.exists():
            raise RuntimeError("Session classifier is not trained")
        self._classifier = joblib.load(classifier_path)
        self._pullback = joblib.load(pullback_path) if pullback_path.exists() else None

    async def _fetch_symbols_for_scoring(self, score_date: date) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT symbol
                FROM daily_scores ds
                JOIN symbol_intraday_profile sip
                  ON sip.symbol = ds.symbol AND sip.sessions_analyzed > 0
                WHERE ds.score_date = (
                    SELECT MAX(score_date)
                    FROM daily_scores
                    WHERE score_date <= $1
                )
                ORDER BY symbol
            """, score_date)
        return [row["symbol"] for row in rows]

    async def _clear_predictions_without_profile(self, prediction_date: date) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM intraday_session_predictions isp
                WHERE isp.prediction_date = $1
                  AND NOT EXISTS (
                      SELECT 1
                      FROM symbol_intraday_profile sip
                      WHERE sip.symbol = isp.symbol
                        AND sip.sessions_analyzed > 0
                  )
            """, prediction_date)
        return int(result.split()[-1]) if result.startswith("DELETE ") else 0

    async def _build_prediction_features(self, symbol: str, prediction_date: date) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                WITH prev AS (
                    SELECT *
                    FROM daily_scores
                    WHERE symbol = $1 AND score_date <= $2
                    ORDER BY score_date DESC
                    LIMIT 1
                )
                SELECT
                    prev.rsi_14 AS prev_rsi,
                    prev.adx_14 AS prev_adx,
                    (prev.plus_di - prev.minus_di) AS prev_di_spread,
                    prev.atr_ratio AS prev_atr_ratio,
                    prev.roc_5 AS prev_roc_5,
                    prev.roc_20 AS prev_roc_20,
                    prev.vol_ratio_20 AS prev_vol_ratio,
                    prev.bb_squeeze AS prev_bb_squeeze,
                    prev.squeeze_days AS prev_squeeze_days,
                    prev.rs_vs_nifty AS prev_rs_vs_nifty,
                    CASE COALESCE(prev.stage, 'UNKNOWN')
                        WHEN 'STAGE_1' THEN 1
                        WHEN 'STAGE_2' THEN 2
                        WHEN 'STAGE_3' THEN 3
                        WHEN 'STAGE_4' THEN 4
                        ELSE 0
                    END AS stage_encoded,
                    EXTRACT(ISODOW FROM $2::date)::int - 1 AS day_of_week,
                    0::numeric AS nifty_gap_pct,
                    sip.iss_score,
                    sip.choppiness_idx,
                    sip.stop_hunt_rate,
                    sip.orb_followthrough_rate,
                    sip.pullback_depth_on_up_days AS pullback_depth_hist
                FROM prev
                LEFT JOIN symbol_intraday_profile sip ON sip.symbol = prev.symbol
            """, symbol, prediction_date)
        if not row:
            return None
        return {k: _plain(v) for k, v in dict(row).items()}

    async def _upsert_predictions(self, records: list[tuple]) -> int:
        if not records:
            return 0
        async with self._pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO intraday_session_predictions (
                    symbol, prediction_date, session_type_pred, trend_up_prob,
                    trend_down_prob, chop_prob, volatile_prob, pullback_depth_pred,
                    model_version, computed_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,NOW())
                ON CONFLICT (symbol, prediction_date) DO UPDATE SET
                    session_type_pred = EXCLUDED.session_type_pred,
                    trend_up_prob = EXCLUDED.trend_up_prob,
                    trend_down_prob = EXCLUDED.trend_down_prob,
                    chop_prob = EXCLUDED.chop_prob,
                    volatile_prob = EXCLUDED.volatile_prob,
                    pullback_depth_pred = EXCLUDED.pullback_depth_pred,
                    model_version = EXCLUDED.model_version,
                    computed_at = NOW()
            """, records)
        return len(records)

    async def _fetch_prediction(self, symbol: str, prediction_date: date) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT isp.*, sip.iss_score
                FROM intraday_session_predictions isp
                LEFT JOIN symbol_intraday_profile sip ON sip.symbol = isp.symbol
                WHERE isp.symbol = $1 AND isp.prediction_date = $2
            """, symbol, prediction_date)
        if not row:
            return None
        return {k: _plain(v) for k, v in dict(row).items()}

    async def _update_comfort_v3(self, prediction_date: date) -> int:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    mp.id,
                    mp.predictions,
                    sip.iss_score,
                    isp.pullback_depth_pred,
                    isp.session_type_pred
                FROM model_predictions mp
                LEFT JOIN symbol_intraday_profile sip ON sip.symbol = mp.symbol
                LEFT JOIN intraday_session_predictions isp
                    ON isp.symbol = mp.symbol AND isp.prediction_date = mp.prediction_date
                WHERE mp.model_name = 'comfort_scorer'
                  AND mp.prediction_date = $1
            """, prediction_date)
            updated = 0
            for row in rows:
                prediction = dict(row["predictions"])
                next_prediction = apply_comfort_v3(
                    prediction,
                    float(row["iss_score"]) if row["iss_score"] is not None else None,
                    float(row["pullback_depth_pred"]) if row["pullback_depth_pred"] is not None else None,
                    row["session_type_pred"],
                )
                await conn.execute("""
                    UPDATE model_predictions
                    SET predictions = $2::jsonb, confidence = $3, created_at = NOW()
                    WHERE id = $1
                """, row["id"], json.dumps(next_prediction), next_prediction.get("confidence"))
                updated += 1
        return updated


def _prediction_record(symbol: str, prediction_date: date, pred: dict) -> tuple:
    return (
        symbol,
        prediction_date,
        pred.get("session_type_pred"),
        pred.get("trend_up_prob"),
        pred.get("trend_down_prob"),
        pred.get("chop_prob"),
        pred.get("volatile_prob"),
        pred.get("pullback_depth_pred"),
        _MODEL_VERSION,
    )


def _plain(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    return float(value)
