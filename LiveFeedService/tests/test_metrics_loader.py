import pytest

from src.services._metrics_loader import load_daily_metrics


class _FakePool:
    def __init__(self) -> None:
        self.query = ""

    async def fetch(self, query: str):
        self.query = query
        return [
            {
                "symbol": "RELIANCE",
                "is_fno": True,
                "week52_high": 3100,
                "week52_low": 2200,
                "atr_14": 42.12,
                "adv_20_cr": 850.6,
                "ema_50": 2860,
                "ema_200": 2710,
                "week_return_pct": 2.5,
                "week_gain_pct": 4.1,
                "week_decline_pct": -1.2,
                "trading_days": 250,
                "prev_day_high": 2960,
                "prev_day_low": 2895,
                "prev_day_close": 2930,
                "prev_week_high": 2990,
                "prev_week_low": 2840,
                "prev_month_high": 3050,
                "prev_month_low": 2700,
            },
        ]


@pytest.mark.asyncio
async def test_load_daily_metrics_includes_fno_flag() -> None:
    pool = _FakePool()

    metrics = await load_daily_metrics(pool)

    assert "LEFT JOIN symbols" in pool.query
    assert metrics["RELIANCE"]["is_fno"] is True
