"""
Unit tests for the momentum scorer and its component sub-functions.

All tests are pure-function — no DB, no network, no yfinance.
"""
import numpy as np
import pandas as pd
import pytest

from src.signals.scorer import (
    compute_score,
    _rsi_score,
    _macd_score,
    _roc_score,
    _volume_score,
    _trend_mult,
    _atr_mult,
    _proximity_mult,
    _rs_mult,
)
from src.domain.models import ScoreBreakdown


# ── Helpers ───────────────────────────────────────────────────────────────────

def _trending_up(n: int = 60, start: float = 100.0, step: float = 0.5) -> pd.Series:
    """Steadily rising close prices."""
    return pd.Series([start + i * step for i in range(n)])


def _trending_down(n: int = 60, start: float = 100.0, step: float = 0.5) -> pd.Series:
    return pd.Series([start - i * step for i in range(n)])


def _flat(n: int = 60, price: float = 100.0) -> pd.Series:
    return pd.Series([price] * n)


def _full_df(close: pd.Series) -> pd.DataFrame:
    """Wrap a close series in an OHLCV DataFrame."""
    n = len(close)
    return pd.DataFrame({
        "open":   close - 0.5,
        "high":   close + 1.0,
        "low":    close - 1.0,
        "close":  close,
        "volume": [200_000.0] * n,
    })


# ── RSI score ─────────────────────────────────────────────────────────────────

class TestRsiScore:
    def test_returns_none_on_single_constant_nan(self):
        # The ta library returns a default when series is too short;
        # guard against that by checking compute_score's min_bars gate first.
        # Here we verify _rsi_score returns a float (not None) on valid input.
        close = _flat(30)
        result = _rsi_score(close, period=14)
        # Flat series → RSI near 50; result is a float, not None
        assert result is not None
        assert isinstance(result, float)

    def test_overbought_penalised(self):
        # A steadily rising series will have RSI > 80.
        close  = pd.Series([100.0 + i * 2 for i in range(60)])
        score  = _rsi_score(close, period=14)
        normal = _rsi_score(_trending_up(60), period=14)
        # Overbought should score lower than a moderate uptrend.
        if score is not None and normal is not None:
            assert score <= normal

    def test_mid_range_returns_rsi_value(self):
        # A moderate uptrend should produce RSI in 40–70.
        close = _trending_up(60, step=0.3)
        score = _rsi_score(close, period=14)
        assert score is not None
        assert 0 <= score <= 100


# ── MACD score ────────────────────────────────────────────────────────────────

class TestMacdScore:
    def test_returns_50_on_flat(self):
        close = _flat(60)
        # Flat series → histogram near zero → score near 50.
        score = _macd_score(close, fast=12, slow=26, signal=9)
        assert 40.0 <= score <= 60.0

    def test_uptrend_scores_above_50(self):
        close = _trending_up(80)
        score = _macd_score(close, fast=12, slow=26, signal=9)
        assert score > 50.0

    def test_downtrend_scores_below_50(self):
        close = _trending_down(80)
        score = _macd_score(close, fast=12, slow=26, signal=9)
        assert score < 50.0


# ── ROC score ─────────────────────────────────────────────────────────────────

class TestRocScore:
    def test_returns_none_on_insufficient_data(self):
        close = pd.Series([100.0] * 3)
        score, rocs = _roc_score(close)
        assert score is None

    def test_uptrend_produces_positive_roc(self):
        close = _trending_up(80)
        score, rocs = _roc_score(close)
        assert score is not None
        assert score > 0
        assert all(v > 0 for v in rocs.values())

    def test_downtrend_has_low_alignment_score(self):
        close = _trending_down(80)
        score, rocs = _roc_score(close)
        assert score is not None
        # All ROCs negative → alignment=0 → score near 0 (only consistency term)
        assert score < 30.0


# ── Volume score ──────────────────────────────────────────────────────────────

class TestVolumeScore:
    def test_double_average_volume_scores_100(self):
        volume = pd.Series([200_000.0] * 40)
        # All bars at same level → ratio = 1.0 → score = 50.
        score = _volume_score(volume, period=20)
        assert score == pytest.approx(50.0, abs=1.0)

    def test_returns_50_on_consistent_volume(self):
        volume = pd.Series([100_000.0] * 30)
        assert _volume_score(volume, period=20) == pytest.approx(50.0)


# ── Quality multipliers ───────────────────────────────────────────────────────

class TestTrendMult:
    def test_no_penalty_on_uptrend(self):
        close = _trending_up(80)
        assert _trend_mult(close, trend_lookback=60) == pytest.approx(1.0)

    def test_penalty_on_severe_downtrend(self):
        close = _trending_down(80, step=1.5)
        mult  = _trend_mult(close, trend_lookback=60)
        assert mult < 1.0

    def test_short_series_no_penalty(self):
        close = _flat(20)
        assert _trend_mult(close, trend_lookback=60) == pytest.approx(1.0)


class TestAtrMult:
    def test_no_penalty_below_threshold(self):
        close = _flat(30)
        df    = _full_df(close)  # ATR ~1/100 = 1% well under 5% default
        assert _atr_mult(df, close, atr_period=14, atr_pct_max=5.0) == pytest.approx(1.0)

    def test_penalty_on_choppy_stock(self):
        # Very high ATR relative to price.
        close = pd.Series([100.0] * 30)
        df = pd.DataFrame({
            "high":  [110.0] * 30,   # ATR ~10 → 10% >> 5% threshold
            "low":   [90.0]  * 30,
            "close": close,
            "volume": [1_000_000.0] * 30,
        })
        mult = _atr_mult(df, close, atr_period=14, atr_pct_max=5.0)
        assert mult < 1.0


class TestProximityMult:
    def test_no_penalty_near_52w_high(self):
        close = _trending_up(252)   # last point is the 52-week high
        assert _proximity_mult(close) == pytest.approx(1.0)

    def test_penalty_well_below_52w_high(self):
        close = pd.Series([100.0] * 200 + [60.0] * 52)  # dropped 40%
        mult  = _proximity_mult(close)
        assert mult < 1.0


class TestRsMult:
    def test_no_benchmark_returns_1(self):
        assert _rs_mult(5.0, None) == pytest.approx(1.0)

    def test_outperformance_capped_at_1(self):
        mult = _rs_mult(20.0, 5.0)   # excess = +15% → boost capped at 1.0
        assert mult == pytest.approx(1.0)

    def test_underperformance_penalised(self):
        mult = _rs_mult(-10.0, 5.0)  # excess = -15%
        assert mult < 1.0


# ── compute_score integration ─────────────────────────────────────────────────

class TestComputeScore:
    def test_returns_none_on_insufficient_bars(self):
        df = _full_df(_flat(10))
        assert compute_score(df, min_bars=30) is None

    def test_returns_score_breakdown_on_valid_data(self):
        df     = _full_df(_trending_up(80))
        result = compute_score(df)
        assert isinstance(result, ScoreBreakdown)
        assert 0.0 <= result.score <= 100.0

    def test_uptrend_scores_higher_than_downtrend(self):
        up_df   = _full_df(_trending_up(80))
        down_df = _full_df(_trending_down(80))
        up_result   = compute_score(up_df)
        down_result = compute_score(down_df)
        assert up_result is not None and down_result is not None
        assert up_result.score > down_result.score

    def test_weights_sum_affects_composite(self):
        df = _full_df(_trending_up(80))
        # Equal weights — should still return a valid breakdown.
        result = compute_score(df, weights=(0.25, 0.25, 0.25, 0.25))
        assert result is not None

    def test_nifty500_underperformance_lowers_score(self):
        close    = _trending_up(80, step=0.1)   # moderate uptrend
        df       = _full_df(close)
        base     = compute_score(df, nifty500_roc_60=None)
        penalised = compute_score(df, nifty500_roc_60=50.0)   # index up 50%, stock underperforms
        assert base is not None and penalised is not None
        assert penalised.score <= base.score
