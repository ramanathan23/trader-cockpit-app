"""Shared OHLCV fixture factories for scorer tests."""

import numpy as np
import pandas as pd


def trending_up(n: int = 200) -> pd.DataFrame:
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


def trending_down(n: int = 200) -> pd.DataFrame:
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


def flat(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(99)
    close = 100 + rng.normal(0, 0.3, n)
    return pd.DataFrame({
        "open":   close - rng.uniform(0.1, 0.2, n),
        "high":   close + rng.uniform(0.1, 0.3, n),
        "low":    close - rng.uniform(0.1, 0.3, n),
        "close":  close,
        "volume": rng.uniform(100_000, 300_000, n),
    })


def compressed(n: int = 200) -> pd.DataFrame:
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
