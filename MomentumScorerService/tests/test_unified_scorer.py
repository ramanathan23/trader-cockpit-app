import numpy as np
import pandas as pd
import pytest

from src.signals.unified_scorer import compute_unified_score


def _make_trending_up(n: int = 200) -> pd.DataFrame:
    """Trending-up OHLCV with rising volume."""
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.5 + np.cumsum(rng.normal(0, 0.3, n))
    vol_base = np.linspace(200_000, 400_000, n) + rng.uniform(0, 50_000, n)
    return pd.DataFrame({
        "open":   close - rng.uniform(0.2, 0.5, n),
        "high":   close + rng.uniform(0.5, 1.5, n),
        "low":    close - rng.uniform(0.5, 1.5, n),
        "close":  close,
        "volume": vol_base,
    })


def _make_flat(n: int = 200) -> pd.DataFrame:
    """Sideways/flat OHLCV."""
    rng = np.random.default_rng(99)
    close = 100 + rng.normal(0, 0.5, n)
    return pd.DataFrame({
        "open":   close - rng.uniform(0.1, 0.3, n),
        "high":   close + rng.uniform(0.2, 0.5, n),
        "low":    close - rng.uniform(0.2, 0.5, n),
        "close":  close,
        "volume": rng.uniform(100_000, 300_000, n),
    })


def test_returns_none_for_insufficient_data():
    df = pd.DataFrame({
        "open": [100.0] * 10,
        "high": [101.0] * 10,
        "low": [99.0] * 10,
        "close": [100.0] * 10,
        "volume": [100_000.0] * 10,
    })
    result = compute_unified_score(df, min_bars=30)
    assert result is None


def test_returns_breakdown_with_all_components():
    result = compute_unified_score(_make_trending_up())
    assert result is not None
    assert 0 <= result.total_score <= 100
    assert 0 <= result.momentum_score <= 100
    assert 0 <= result.trend_score <= 100
    assert 0 <= result.volatility_score <= 100
    assert 0 <= result.structure_score <= 100


def test_trending_scores_higher_than_flat():
    trending = compute_unified_score(_make_trending_up())
    flat = compute_unified_score(_make_flat())
    assert trending is not None
    assert flat is not None
    assert trending.total_score > flat.total_score


def test_raw_indicator_values_populated():
    result = compute_unified_score(_make_trending_up())
    assert result is not None
    assert result.rsi_14 is not None
    assert result.adx_14 is not None
    assert result.atr_ratio is not None
    assert result.weekly_bias in ("BULLISH", "BEARISH", "NEUTRAL")


def test_total_is_average_of_four_components():
    result = compute_unified_score(_make_trending_up())
    assert result is not None
    expected = 0.25 * result.momentum_score + 0.25 * result.trend_score + \
               0.25 * result.volatility_score + 0.25 * result.structure_score
    assert abs(result.total_score - expected) < 0.02  # rounding tolerance


def test_benchmark_roc_affects_structure_score():
    df = _make_trending_up()
    without_bench = compute_unified_score(df)
    with_bench = compute_unified_score(df, nifty500_roc_60=-10.0)
    assert without_bench is not None
    assert with_bench is not None
    # Strong stock vs weak benchmark should boost structure
    assert with_bench.structure_score >= without_bench.structure_score - 5
