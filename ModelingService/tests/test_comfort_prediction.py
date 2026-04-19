import numpy as np
import pytest

from src.models.comfort_scorer.model import ComfortScorerModel
from src.models.comfort_scorer._model_predict import (
    compute_chart_comfort,
    interpret_score,
    predict_comfort,
)


def _features(**overrides):
    values = {
        "total_score": 70.0,
        "momentum_score": 72.0,
        "trend_score": 70.0,
        "volatility_score": 58.0,
        "structure_score": 68.0,
        "rsi_14": 62.0,
        "macd_hist": 0.8,
        "roc_5": 3.0,
        "roc_20": 8.0,
        "roc_60": 18.0,
        "vol_ratio_20": 1.5,
        "adx_14": 30.0,
        "plus_di": 32.0,
        "minus_di": 16.0,
        "bb_squeeze": 0.0,
        "squeeze_days": 0.0,
        "nr7": 0.0,
        "atr_ratio": 0.9,
        "atr_5": 2.0,
        "bb_width": 0.06,
        "kc_width": 0.07,
        "rs_vs_nifty": 6.0,
    }
    values.update(overrides)
    return np.array(list(values.values()), dtype=np.float32)


def test_clean_momentum_chart_scores_high():
    score, components = compute_chart_comfort(_features())

    assert score >= 65
    assert components["penalty"] == 0
    assert components["trend"] >= 65


def test_overextended_momentum_is_less_comfortable():
    clean, _ = compute_chart_comfort(_features())
    extended, components = compute_chart_comfort(
        _features(rsi_14=82.0, roc_5=14.0, roc_20=32.0, atr_ratio=1.45)
    )

    assert extended < clean - 10
    assert components["penalty"] > 0


def test_negative_alignment_is_uncomfortable_even_with_total_score():
    aligned, _ = compute_chart_comfort(_features())
    broken, _ = compute_chart_comfort(
        _features(
            momentum_score=74.0,
            total_score=72.0,
            roc_5=-2.5,
            roc_20=-4.0,
            plus_di=14.0,
            minus_di=30.0,
        )
    )

    assert broken < aligned - 15


def test_interpretation_uses_trade_language():
    assert "clean momentum" in interpret_score(82.0)
    assert "avoid" in interpret_score(20.0)


def test_prediction_no_longer_exposes_legacy_model_score():
    prediction = predict_comfort(_features())

    assert prediction["method"] == "chart_comfort_v2"
    assert "comfort_score" in prediction
    assert "model_score" not in prediction


@pytest.mark.asyncio
async def test_rule_model_loads_without_legacy_model_file(tmp_path):
    model = ComfortScorerModel(model_base_path=str(tmp_path))

    await model.load()

    assert model.model is not None
    assert model.version == "chart_comfort_v2"
    assert model.metadata is not None
    assert model.metadata.framework == "chart_comfort_rules"
