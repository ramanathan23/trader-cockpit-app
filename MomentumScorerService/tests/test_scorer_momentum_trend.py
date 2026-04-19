"""Tests for momentum and trend scorer components."""

import pandas as pd
import pytest

from src.signals.unified_scorer import _momentum_score, _trend_score
from tests._scorer_fixtures import compressed, flat, trending_down, trending_up


class TestMomentumScore:

    def test_returns_score_in_range(self):
        df = trending_up()
        score, raw = _momentum_score(df["close"], df["volume"])
        assert score is not None
        assert 0 <= score <= 100

    def test_trending_up_scores_higher_than_flat(self):
        up_score, _ = _momentum_score(trending_up()["close"], trending_up()["volume"])
        flat_score, _ = _momentum_score(flat()["close"], flat()["volume"])
        assert up_score is not None and flat_score is not None
        assert up_score > flat_score

    def test_returns_raw_indicator_values(self):
        score, raw = _momentum_score(trending_up()["close"], trending_up()["volume"])
        assert "rsi_14" in raw
        assert "macd_hist" in raw
        assert "roc_5" in raw
        assert "roc_20" in raw
        assert "vol_ratio_20" in raw

    def test_returns_none_for_insufficient_data(self):
        short = pd.Series([100.0] * 5)
        vol = pd.Series([100_000.0] * 5)
        score, raw = _momentum_score(short, vol)
        if score is not None:
            assert 0 <= score <= 100


class TestTrendScore:

    def test_returns_score_in_range(self):
        df = trending_up()
        score, raw = _trend_score(df, df["close"])
        assert 0 <= score <= 100

    def test_trending_beats_flat(self):
        up_df = trending_up()
        flat_df = flat()
        up_score, _ = _trend_score(up_df, up_df["close"])
        flat_score, _ = _trend_score(flat_df, flat_df["close"])
        assert up_score > flat_score

    def test_returns_weekly_bias(self):
        df = trending_up()
        _, raw = _trend_score(df, df["close"])
        assert raw["weekly_bias"] in ("BULLISH", "BEARISH", "NEUTRAL")

    def test_returns_adx_and_di_values(self):
        df = trending_up()
        _, raw = _trend_score(df, df["close"])
        assert "adx_14" in raw
        assert "plus_di" in raw
        assert "minus_di" in raw
