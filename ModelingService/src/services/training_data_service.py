from __future__ import annotations

import logging
from datetime import date, datetime
from math import isfinite
from zoneinfo import ZoneInfo

import asyncpg
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")
_STAGE_MAP = {"UNKNOWN": 0, "STAGE_1": 1, "STAGE_2": 2, "STAGE_3": 3, "STAGE_4": 4}


class TrainingDataService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def build_training_sessions(self, lookback_years: int = 5) -> dict:
        symbols = await self._fetch_symbols()
        nifty_df = await self._fetch_daily_ohlcv("NIFTY500", lookback_years)
        if not nifty_df.empty:
            nifty_df["nifty_gap_pct"] = (
                (nifty_df["open"] - nifty_df["close"].shift(1))
                / nifty_df["close"].shift(1)
                * 100
            )

        total_written = 0
        symbols_written = 0
        for symbol in symbols:
            try:
                rows = await self._build_symbol_sessions(symbol, nifty_df, lookback_years)
                written = await self._upsert_training_sessions(rows)
                if written:
                    total_written += written
                    symbols_written += 1
            except Exception:
                logger.warning("Training session build failed for %s", symbol, exc_info=True)

        return {"symbols": symbols_written, "sessions_written": total_written}

    async def _build_symbol_sessions(
        self,
        symbol: str,
        nifty_df: pd.DataFrame,
        lookback_years: int,
    ) -> list[tuple]:
        df = await self._fetch_daily_ohlcv(symbol, lookback_years)
        if len(df) < 60:
            return []

        df["atr_14"] = _compute_rolling_atr(df, 14)
        df["prev_close"] = df["close"].shift(1)
        df["gap_pct"] = (df["open"] - df["prev_close"]) / df["prev_close"] * 100
        day_range = (df["high"] - df["low"]).replace(0, np.nan)
        df["range_vs_atr"] = (df["high"] - df["low"]) / df["atr_14"].clip(lower=0.01)
        df["high_close_ratio"] = (df["close"] - df["low"]) / (day_range + 1e-8)
        df["low_close_ratio"] = (df["high"] - df["close"]) / (day_range + 1e-8)

        df["trend_up"] = (
            (df["high_close_ratio"] > 0.65)
            & (df["range_vs_atr"] > 0.8)
            & (df["close"] > df["open"])
        )
        df["trend_down"] = (
            (df["low_close_ratio"] > 0.65)
            & (df["range_vs_atr"] > 0.8)
            & (df["close"] < df["open"])
        )
        df["chop_day"] = (
            (df["range_vs_atr"] < 0.7)
            | (df["high_close_ratio"].between(0.25, 0.75) & (df["range_vs_atr"] < 1.1))
        )
        df["volatile_day"] = df["range_vs_atr"] > 1.6
        df["gap_fade"] = (
            (df["gap_pct"].abs() > 0.5)
            & (
                ((df["gap_pct"] > 0.5) & (df["close"] < df["open"]))
                | ((df["gap_pct"] < -0.5) & (df["close"] > df["open"]))
            )
        )

        conds = [df["trend_up"], df["trend_down"], df["volatile_day"], df["gap_fade"], df["chop_day"]]
        choices = ["TREND_UP", "TREND_DOWN", "VOLATILE", "GAP_FADE", "CHOP"]
        df["session_type"] = np.select(conds, choices, default="NEUTRAL")
        up_day = df["close"] > df["open"] * 1.005
        df["pullback_depth"] = np.where(
            up_day,
            (df["high"] - df["close"]) / ((df["high"] - df["low"]) + 1e-8),
            np.nan,
        )

        scores_df = await self._fetch_daily_scores(symbol, lookback_years)
        if not scores_df.empty:
            prev = scores_df.shift(1).rename(columns=lambda c: f"prev_{c}")
            df = df.join(prev, how="left")

        df["prev_di_spread"] = df.get("prev_plus_di", np.nan) - df.get("prev_minus_di", np.nan)
        df["stage_encoded"] = df.get("prev_stage", pd.Series(index=df.index, dtype=object)).map(_STAGE_MAP).fillna(0)
        df["day_of_week"] = pd.to_datetime(df.index).dayofweek
        if not nifty_df.empty:
            df = df.join(nifty_df[["nifty_gap_pct"]], how="left")
        else:
            df["nifty_gap_pct"] = np.nan

        profile = await self._fetch_intraday_profile(symbol)
        if profile:
            df["iss_score"] = profile.get("iss_score")
            df["choppiness_idx"] = profile.get("choppiness_idx")
            df["stop_hunt_rate"] = profile.get("stop_hunt_rate")
            df["orb_followthrough_rate"] = profile.get("orb_followthrough_rate")
            df["pullback_depth_hist"] = profile.get("pullback_depth_on_up_days")

        return [_training_record(symbol, idx, row) for idx, row in df.iterrows()]

    async def _fetch_symbols(self) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT symbol
                FROM symbol_intraday_profile
                WHERE sessions_analyzed > 0
                ORDER BY symbol
            """)
        return [row["symbol"] for row in rows]

    async def _fetch_daily_ohlcv(self, symbol: str, years: int) -> pd.DataFrame:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time::date AS session_date, open, high, low, close, volume
                FROM price_data_daily
                WHERE symbol = $1
                  AND time >= NOW() - ($2::int * INTERVAL '1 year')
                ORDER BY time ASC
            """, symbol, years)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        df = df.set_index(pd.to_datetime(df.pop("session_date")))
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df

    async def _fetch_daily_scores(self, symbol: str, years: int) -> pd.DataFrame:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT score_date, rsi_14, adx_14, plus_di, minus_di, atr_ratio,
                       roc_5, roc_20, vol_ratio_20, bb_squeeze, squeeze_days,
                       rs_vs_nifty, stage
                FROM daily_scores
                WHERE symbol = $1
                  AND score_date >= (NOW() - ($2::int * INTERVAL '1 year'))::date
                ORDER BY score_date ASC
            """, symbol, years)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        df = df.set_index(pd.to_datetime(df.pop("score_date")))
        return df

    async def _fetch_intraday_profile(self, symbol: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT iss_score, choppiness_idx, stop_hunt_rate,
                       orb_followthrough_rate, pullback_depth_on_up_days
                FROM symbol_intraday_profile
                WHERE symbol = $1
            """, symbol)
        return dict(row) if row else None

    async def _upsert_training_sessions(self, records: list[tuple]) -> int:
        if not records:
            return 0
        async with self._pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO intraday_training_sessions (
                    symbol, session_date, prev_rsi, prev_adx, prev_di_spread,
                    prev_atr_ratio, prev_roc_5, prev_roc_20, prev_vol_ratio,
                    prev_bb_squeeze, prev_squeeze_days, prev_rs_vs_nifty,
                    stage_encoded, day_of_week, nifty_gap_pct, iss_score,
                    choppiness_idx, stop_hunt_rate, orb_followthrough_rate,
                    pullback_depth_hist, high_close_ratio, range_vs_atr,
                    pullback_depth, session_type, trend_up, trend_down,
                    chop_day, volatile_day, computed_at
                ) VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,
                    $17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,NOW()
                )
                ON CONFLICT (symbol, session_date) DO UPDATE SET
                    prev_rsi = EXCLUDED.prev_rsi,
                    prev_adx = EXCLUDED.prev_adx,
                    prev_di_spread = EXCLUDED.prev_di_spread,
                    prev_atr_ratio = EXCLUDED.prev_atr_ratio,
                    prev_roc_5 = EXCLUDED.prev_roc_5,
                    prev_roc_20 = EXCLUDED.prev_roc_20,
                    prev_vol_ratio = EXCLUDED.prev_vol_ratio,
                    prev_bb_squeeze = EXCLUDED.prev_bb_squeeze,
                    prev_squeeze_days = EXCLUDED.prev_squeeze_days,
                    prev_rs_vs_nifty = EXCLUDED.prev_rs_vs_nifty,
                    stage_encoded = EXCLUDED.stage_encoded,
                    day_of_week = EXCLUDED.day_of_week,
                    nifty_gap_pct = EXCLUDED.nifty_gap_pct,
                    iss_score = EXCLUDED.iss_score,
                    choppiness_idx = EXCLUDED.choppiness_idx,
                    stop_hunt_rate = EXCLUDED.stop_hunt_rate,
                    orb_followthrough_rate = EXCLUDED.orb_followthrough_rate,
                    pullback_depth_hist = EXCLUDED.pullback_depth_hist,
                    high_close_ratio = EXCLUDED.high_close_ratio,
                    range_vs_atr = EXCLUDED.range_vs_atr,
                    pullback_depth = EXCLUDED.pullback_depth,
                    session_type = EXCLUDED.session_type,
                    trend_up = EXCLUDED.trend_up,
                    trend_down = EXCLUDED.trend_down,
                    chop_day = EXCLUDED.chop_day,
                    volatile_day = EXCLUDED.volatile_day,
                    computed_at = NOW()
            """, records)
        return len(records)


def _compute_rolling_atr(df: pd.DataFrame, window: int) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=window, min_periods=window).mean()


def _training_record(symbol: str, idx, row: pd.Series) -> tuple:
    return (
        symbol,
        idx.date() if hasattr(idx, "date") else idx,
        _num(row.get("prev_rsi_14")),
        _num(row.get("prev_adx_14")),
        _num(row.get("prev_di_spread")),
        _num(row.get("prev_atr_ratio")),
        _num(row.get("prev_roc_5")),
        _num(row.get("prev_roc_20")),
        _num(row.get("prev_vol_ratio_20")),
        _bool(row.get("prev_bb_squeeze")),
        _int(row.get("prev_squeeze_days")),
        _num(row.get("prev_rs_vs_nifty")),
        _int(row.get("stage_encoded")) or 0,
        _int(row.get("day_of_week")),
        _num(row.get("nifty_gap_pct")),
        _num(row.get("iss_score")),
        _num(row.get("choppiness_idx")),
        _num(row.get("stop_hunt_rate")),
        _num(row.get("orb_followthrough_rate")),
        _num(row.get("pullback_depth_hist")),
        _num(row.get("high_close_ratio")),
        _num(row.get("range_vs_atr")),
        _num(row.get("pullback_depth")),
        str(row.get("session_type") or "NEUTRAL"),
        _bool(row.get("trend_up")) or False,
        _bool(row.get("trend_down")) or False,
        _bool(row.get("chop_day")) or False,
        _bool(row.get("volatile_day")) or False,
    )


def _num(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    out = float(value)
    return out if isfinite(out) else None


def _int(value) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def _bool(value) -> bool | None:
    if value is None or pd.isna(value):
        return None
    return bool(value)
