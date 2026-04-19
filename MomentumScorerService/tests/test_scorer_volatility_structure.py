"""Tests for volatility and structure scorer components."""

from src.signals.unified_scorer import _structure_score, _volatility_score
from tests._scorer_fixtures import compressed, trending_down, trending_up


class TestVolatilityScore:

    def test_returns_score_in_range(self):
        df = trending_up()
        score, raw = _volatility_score(df, df["close"])
        assert 0 <= score <= 100

    def test_compressed_scores_higher_than_expanding(self):
        comp_df = compressed()
        exp_df = trending_up()
        comp_score, _ = _volatility_score(comp_df, comp_df["close"])
        exp_score, _ = _volatility_score(exp_df, exp_df["close"])
        assert comp_score >= exp_score

    def test_returns_squeeze_and_nr7_fields(self):
        df = trending_up()
        _, raw = _volatility_score(df, df["close"])
        assert "bb_squeeze" in raw
        assert "squeeze_days" in raw
        assert "nr7" in raw
        assert "atr_ratio" in raw


class TestStructureScore:

    def test_returns_score_in_range(self):
        df = trending_up()
        score, raw = _structure_score(df, df["close"], df["volume"])
        assert 0 <= score <= 100

    def test_near_highs_scores_better(self):
        up_df = trending_up()
        down_df = trending_down()
        up_score, _ = _structure_score(up_df, up_df["close"], up_df["volume"])
        down_score, _ = _structure_score(down_df, down_df["close"], down_df["volume"])
        assert up_score > down_score

    def test_benchmark_outperformance_boosts_score(self):
        df = trending_up()
        without, _ = _structure_score(df, df["close"], df["volume"])
        with_weak_bench, _ = _structure_score(
            df, df["close"], df["volume"], nifty500_roc_60=-15.0
        )
        assert with_weak_bench >= without

    def test_returns_rs_field(self):
        df = trending_up()
        _, raw = _structure_score(df, df["close"], df["volume"])
        assert "rs_vs_nifty" in raw
