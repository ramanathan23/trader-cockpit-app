import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.score_service import ScoreService


def _make_pool():
    pool = MagicMock()
    conn = MagicMock()
    conn.transaction.return_value.__aenter__ = AsyncMock(return_value=None)
    conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


def _make_candidate(symbol: str, adv: float = 5.0) -> dict:
    return {
        "symbol": symbol, "is_fno": False,
        "rsi_14": 55.0, "macd_hist": 0.1, "macd_hist_std": 0.5,
        "roc_5": 1.0, "roc_20": 2.0, "roc_60": 3.0, "vol_ratio_20": 1.2,
        "adx_14": 25.0, "plus_di": 20.0, "minus_di": 15.0, "weekly_bias": "BULLISH",
        "bb_squeeze": False, "squeeze_days": 0, "nr7": False,
        "atr_ratio": 0.9, "atr_5": 5.0, "bb_width": 0.05, "kc_width": 0.06,
        "rs_vs_nifty": 1.5, "stage": "STAGE_2",
        "prev_day_close": 100.0, "week52_high": 120.0, "week52_low": 80.0,
        "ema_20": 98.0, "ema_50": 95.0, "ema_200": 90.0, "adv_20_cr": adv,
    }


@pytest.mark.asyncio
async def test_compute_unified_scores_and_persists():
    service = ScoreService(_make_pool())
    service._symbols = AsyncMock()
    service._scores = AsyncMock()

    candidates = [_make_candidate("ABC"), _make_candidate("XYZ")]
    service._symbols.fetch_ranked_candidates.return_value = candidates
    service._scores.upsert_daily_score = AsyncMock()

    count, msg = await service.compute_unified()

    assert count == 2
    assert "2" in msg


@pytest.mark.asyncio
async def test_compute_unified_returns_zero_when_no_indicators():
    service = ScoreService(_make_pool())
    service._symbols = AsyncMock()
    service._scores = AsyncMock()

    service._symbols.fetch_ranked_candidates.return_value = []
    service._symbols.fetch_candidate_counts.return_value = {
        "total_indicators": 0, "total_metrics": 0, "joined": 0, "after_adv_filter": 0,
    }

    count, msg = await service.compute_unified()

    assert count == 0
    assert "IndicatorsService" in msg


@pytest.mark.asyncio
async def test_compute_unified_returns_zero_when_adv_filter_excludes_all():
    service = ScoreService(_make_pool())
    service._symbols = AsyncMock()
    service._scores = AsyncMock()

    service._symbols.fetch_ranked_candidates.return_value = []
    service._symbols.fetch_candidate_counts.return_value = {
        "total_indicators": 100, "total_metrics": 100, "joined": 100, "after_adv_filter": 0,
    }

    count, msg = await service.compute_unified()

    assert count == 0
    assert "ADV filter" in msg


@pytest.mark.asyncio
async def test_compute_unified_marks_top_watchlist():
    service = ScoreService(_make_pool())
    service._symbols = AsyncMock()
    service._scores = AsyncMock()

    candidates = [_make_candidate(f"SYM{i:03d}") for i in range(30)]
    service._symbols.fetch_ranked_candidates.return_value = candidates
    service._scores.upsert_daily_score = AsyncMock()

    count, msg = await service.compute_unified()

    assert count == 30
