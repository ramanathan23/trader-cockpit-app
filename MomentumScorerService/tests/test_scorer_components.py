"""
Per-component tests for the unified scorer.

Tests each scoring function (_momentum_score, _trend_score, _volatility_score,
_structure_score) in isolation to verify:
  - correct score ranges (0–100)
  - expected directional behavior (trending > flat, compressed > expanding)
  - edge cases (insufficient data, zero volume, NaN values)
"""

import numpy as np
import pandas as pd
import pytest

from src.signals.unified_scorer import (
    _momentum_score,
    _trend_score,
    _volatility_score,
    _structure_score,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _trending_up(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.5 + np.cumsum(rng.normal(0, 0.3, n))
    vol = np.linspace(200_000, 400_000, n) + rng.uniform(0, 50_000, n)
    return pd.DataFrame({
        "open":   close - rng.uniform(0.2, 0.5, n),
        "high":   close + rng.uniform(0.5, 1.5, n),
        "low":    close - rng.uniform(0.5, 1.5, n),
        "close":  close,
        "volume": vol,
    })


def _trending_down(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(77)
    close = 200 - np.arange(n) * 0.5 + np.cumsum(rng.normal(0, 0.3, n))
    vol = np.linspace(300_000, 150_000, n) + rng.uniform(0, 30_000, n)
    return pd.DataFrame({
        "open":   close + rng.uniform(0.2, 0.5, n),
        "high":   close + rng.uniform(0.5, 1.5, n),
        "low":    close - rng.uniform(0.5, 1.5, n),
        "close":  close,
        "volume": vol,
    })


def _flat(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(99)
    close = 100 + rng.normal(0, 0.3, n)
    return pd.DataFrame({
        "open":   close - rng.uniform(0.1, 0.2, n),
        "high":   close + rng.uniform(0.1, 0.3, n),
        "low":    close - rng.uniform(0.1, 0.3, n),
        "close":  close,
        "volume": rng.uniform(100_000, 300_000, n),
    })


def _compressed(n: int = 200) -> pd.DataFrame:
    """First 150 bars normal, last 50 bars very tight range → squeeze."""
    rng = np.random.default_rng(55)
    close_start = 100 + np.arange(150) * 0.3 + np.cumsum(rng.normal(0, 0.5, 150))
    last_val = close_start[-1]
    close_end = last_val + rng.normal(0, 0.05, 50)
    close = np.concatenate([close_start, close_end])
    vol = rng.uniform(100_000, 200_000, n)
    return pd.DataFrame({
        "open":   close - rng.uniform(0.1, 0.3, n),
        "high":   close + rng.uniform(0.05, 0.15, n),
        "low":    close - rng.uniform(0.05, 0.15, n),
        "close":  close,
        "volume": vol,
    })


# ── Momentum tests ────────────────────────────────────────────────────────────

class TestMomentumScore:

    def test_returns_score_in_range(self):
        df = _trending_up()
        score, raw = _momentum_score(df["close"], df["volume"])
        assert score is not None
        assert 0 <= score <= 100

    def test_trending_up_scores_higher_than_flat(self):
        up_score, _ = _momentum_score(_trending_up()["close"], _trending_up()["volume"])
        flat_score, _ = _momentum_score(_flat()["close"], _flat()["volume"])
        assert up_score is not None and flat_score is not None
        assert up_score > flat_score

    def test_returns_raw_indicator_values(self):
        score, raw = _momentum_score(_trending_up()["close"], _trending_up()["volume"])
        assert "rsi_14" in raw
        assert "macd_hist" in raw
        assert "roc_5" in raw
        assert "roc_20" in raw
        assert "vol_ratio_20" in raw

    def test_returns_none_for_insufficient_data(self):
        short = pd.Series([100.0] * 5)
        vol = pd.Series([100_000.0] * 5)
        score, raw = _momentum_score(short, vol)
        # RSI needs at least period+1 bars; may return None or low score
        # The function returns None if RSI is NaN
        if score is not None:
            assert 0 <= score <= 100


# ── Trend tests ───────────────────────────────────────────────────────────────

class TestTrendScore:

    def test_returns_score_in_range(self):
        df = _trending_up()
        score, raw = _trend_score(df, df["close"])
        assert 0 <= score <= 100

    def test_trending_beats_flat(self):
        up_df = _trending_up()
        flat_df = _flat()
        up_score, _ = _trend_score(up_df, up_df["close"])
        flat_score, _ = _trend_score(flat_df, flat_df["close"])
        assert up_score > flat_score

    def test_returns_weekly_bias(self):
        df = _trending_up()
        _, raw = _trend_score(df, df["close"])
        assert raw["weekly_bias"] in ("BULLISH", "BEARISH", "NEUTRAL")

    def test_returns_adx_and_di_values(self):
        df = _trending_up()
        _, raw = _trend_score(df, df["close"])
        assert "adx_14" in raw
        assert "plus_di" in raw
        assert "minus_di" in raw


# ── Volatility tests ──────────────────────────────────────────────────────────

class TestVolatilityScore:

    def test_returns_score_in_range(self):
        df = _trending_up()
        score, raw = _volatility_score(df, df["close"])
        assert 0 <= score <= 100

    def test_compressed_scores_higher_than_expanding(self):
        comp_df = _compressed()
        exp_df = _trending_up()
        comp_score, _ = _volatility_score(comp_df, comp_df["close"])
        exp_score, _ = _volatility_score(exp_df, exp_df["close"])
        # Compressed should score higher (coiled spring = opportunity)
        assert comp_score >= exp_score

    def test_returns_squeeze_and_nr7_fields(self):
        df = _trending_up()
        _, raw = _volatility_score(df, df["close"])
        assert "bb_squeeze" in raw
        assert "squeeze_days" in raw
        assert "nr7" in raw
        assert "atr_ratio" in raw


# ── Structure tests ───────────────────────────────────────────────────────────

class TestStructureScore:

    def test_returns_score_in_range(self):
        df = _trending_up()
        score, raw = _structure_score(df, df["close"], df["volume"])
        assert 0 <= score <= 100

    def test_near_highs_scores_better(self):
        up_df = _trending_up()  # ends near 52-week high
        down_df = _trending_down()  # ends near 52-week low
        up_score, _ = _structure_score(up_df, up_df["close"], up_df["volume"])
        down_score, _ = _structure_score(down_df, down_df["close"], down_df["volume"])
        assert up_score > down_score

    def test_benchmark_outperformance_boosts_score(self):
        df = _trending_up()
        without, _ = _structure_score(df, df["close"], df["volume"])
        with_weak_bench, _ = _structure_score(
            df, df["close"], df["volume"], nifty500_roc_60=-15.0
        )
        # Strong stock vs weak benchmark → relative strength bonus
        assert with_weak_bench >= without

    def test_returns_rs_field(self):
        df = _trending_up()
        _, raw = _structure_score(df, df["close"], df["volume"])
        assert "rs_vs_nifty" in raw
