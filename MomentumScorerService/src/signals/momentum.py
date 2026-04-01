"""
Composite momentum scorer.

Score components (each normalised to 0–100):
  RSI          30% — momentum strength; penalises extremes (>80 overbought)
  MACD         30% — trend acceleration; histogram z-score maps to 0-100
  ROC (10-bar) 25% — raw price momentum
  Volume ratio 15% — volume confirms the move

Final score = weighted sum, rounded to 2 dp.

Design notes:
  - Computation is CPU-bound (pandas vectorised) — runs in the async event loop
    via asyncio.to_thread for large symbol sets.
  - Scores are upserted into momentum_scores table; stale scores overwritten.
"""

import asyncio
import logging
from typing import NamedTuple

import asyncpg
import numpy as np
import pandas as pd

from . import indicators
from ..config import settings

logger = logging.getLogger(__name__)


class ScoreBreakdown(NamedTuple):
    score:      float
    rsi:        float
    macd_score: float
    roc_score:  float
    vol_score:  float


def _compute_score(df: pd.DataFrame) -> ScoreBreakdown | None:
    """
    Compute momentum score for one symbol's OHLCV DataFrame.

    Requires at least 30 rows; returns None if insufficient data.
    """
    if len(df) < 30:
        return None

    close  = df["close"].astype(float)
    high   = df["high"].astype(float)
    low    = df["low"].astype(float)
    volume = df["volume"].astype(float)

    # ── RSI ──────────────────────────────────────────────────────────────────
    rsi_val = indicators.rsi(close).iloc[-1]
    if pd.isna(rsi_val):
        return None

    # RSI score: penalise extremes to reduce overbought chasing
    if rsi_val > 80:
        rsi_score = max(0.0, 100.0 - (rsi_val - 80) * 2)
    elif rsi_val < 20:
        rsi_score = rsi_val * 1.5
    else:
        rsi_score = float(rsi_val)

    # ── MACD histogram z-score ────────────────────────────────────────────────
    _, _, histogram = indicators.macd(close)
    hist_now = histogram.iloc[-1]
    hist_std = histogram.std()

    if pd.isna(hist_now) or hist_std == 0 or pd.isna(hist_std):
        macd_score = 50.0
    else:
        z = hist_now / hist_std
        macd_score = float(np.clip(50.0 + z * 15.0, 0.0, 100.0))

    # ── Rate of Change ────────────────────────────────────────────────────────
    roc = indicators.rate_of_change(close, period=10).iloc[-1]
    if pd.isna(roc):
        return None
    # ±10% ROC maps roughly to 0–100; clipped at extremes
    roc_score = float(np.clip(50.0 + roc * 5.0, 0.0, 100.0))

    # ── Volume ratio ──────────────────────────────────────────────────────────
    vol_r = indicators.volume_ratio(volume).iloc[-1]
    if pd.isna(vol_r):
        vol_score = 50.0
    else:
        # ratio of 2× avg volume → 100, 0.5× → 25
        vol_score = float(np.clip(vol_r * 50.0, 0.0, 100.0))

    # ── Composite ─────────────────────────────────────────────────────────────
    composite = (
        0.30 * rsi_score
        + 0.30 * macd_score
        + 0.25 * roc_score
        + 0.15 * vol_score
    )

    return ScoreBreakdown(
        score=round(composite, 2),
        rsi=round(rsi_score, 2),
        macd_score=round(macd_score, 2),
        roc_score=round(roc_score, 2),
        vol_score=round(vol_score, 2),
    )


async def compute_all_scores(pool: asyncpg.Pool, timeframe: str = "1d") -> int:
    """
    Compute and persist momentum scores for all synced symbols.

    Uses asyncio.to_thread for the pandas computation to avoid blocking
    the event loop during large scoring runs.

    Returns the number of symbols successfully scored.
    """
    table = "price_data_daily" if timeframe == "1d" else "price_data_1m"
    lookback = settings.score_lookback_bars

    async with pool.acquire() as conn:
        symbols = [r["symbol"] for r in await conn.fetch(
            "SELECT DISTINCT symbol FROM sync_state WHERE status = 'synced'"
        )]

    if not symbols:
        logger.warning("No synced symbols found — run initial sync first")
        return 0

    logger.info("Computing %s momentum scores for %d symbols", timeframe, len(symbols))
    scored = 0

    async with pool.acquire() as conn:
        for symbol in symbols:
            try:
                rows = await conn.fetch(f"""
                    SELECT time, open, high, low, close, volume
                    FROM   {table}
                    WHERE  symbol = $1
                    ORDER  BY time DESC
                    LIMIT  $2
                """, symbol, lookback)

                if not rows:
                    continue

                df = pd.DataFrame([dict(r) for r in rows]).sort_values("time").reset_index(drop=True)

                breakdown = await asyncio.to_thread(_compute_score, df)
                if breakdown is None:
                    continue

                await conn.execute("""
                    INSERT INTO momentum_scores
                        (symbol, timeframe, score, rsi, macd_score, roc_score, vol_score, computed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    ON CONFLICT (symbol, timeframe) DO UPDATE SET
                        score       = $3,
                        rsi         = $4,
                        macd_score  = $5,
                        roc_score   = $6,
                        vol_score   = $7,
                        computed_at = NOW()
                """, symbol, timeframe,
                    breakdown.score, breakdown.rsi,
                    breakdown.macd_score, breakdown.roc_score, breakdown.vol_score)

                scored += 1

            except Exception:
                logger.warning("Scoring failed for %s", symbol, exc_info=True)

    logger.info("Scored %d / %d symbols (%s)", scored, len(symbols), timeframe)
    return scored
