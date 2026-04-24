"""Additional error-path tests for score persistence (part 2)."""

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


def _make_candidate(symbol: str, rsi: float | None = 55.0) -> dict:
    return {
        "symbol": symbol, "is_fno": False,
        "rsi_14": rsi, "macd_hist": 0.1, "macd_hist_std": 0.5,
        "roc_5": 1.0, "roc_20": 2.0, "roc_60": 3.0, "vol_ratio_20": 1.2,
        "adx_14": 25.0, "plus_di": 20.0, "minus_di": 15.0, "weekly_bias": "BULLISH",
        "bb_squeeze": False, "squeeze_days": 0, "nr7": False,
        "atr_ratio": 0.9, "atr_5": 5.0, "bb_width": 0.05, "kc_width": 0.06,
        "rs_vs_nifty": 1.5, "stage": "STAGE_2",
        "prev_day_close": 100.0, "week52_high": 120.0, "week52_low": 80.0,
        "ema_20": 98.0, "ema_50": 95.0, "ema_200": 90.0, "adv_20_cr": 5.0,
    }


@pytest.mark.asyncio
async def test_os_error_in_persist_is_caught():
    """OSError during persist should be caught; scored count = 0."""
    service = ScoreService(_make_pool())
    service._symbols = AsyncMock()
    service._scores = AsyncMock()

    service._symbols.fetch_ranked_candidates.return_value = [_make_candidate("FAIL")]
    service._scores.upsert_daily_score = AsyncMock(side_effect=OSError("Connection reset"))

    count, msg = await service.compute_unified()

    assert count == 0


@pytest.mark.asyncio
async def test_missing_rsi_symbol_skipped_gracefully():
    """Candidates with null rsi_14 produce no valid score — counted as 0."""
    service = ScoreService(_make_pool())
    service._symbols = AsyncMock()
    service._scores = AsyncMock()

    service._symbols.fetch_ranked_candidates.return_value = [_make_candidate("NORSI", rsi=None)]

    count, msg = await service.compute_unified()

    assert count == 0
    service._scores.upsert_daily_score.assert_not_called()
