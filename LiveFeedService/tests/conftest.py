from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.domain.models import Candle


IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def make_candle():
    def _make(
        open_price: float,
        close_price: float,
        *,
        high: float | None = None,
        low: float | None = None,
        volume: int = 100,
        hour: int = 9,
        minute: int = 15,
        symbol: str = "TEST",
        tick_count: int = 1,
        is_index_future: bool = False,
    ) -> Candle:
        resolved_high = high if high is not None else max(open_price, close_price)
        resolved_low = low if low is not None else min(open_price, close_price)
        return Candle(
            symbol=symbol,
            boundary=datetime(2026, 4, 16, hour, minute, tzinfo=IST),
            open=open_price,
            high=resolved_high,
            low=resolved_low,
            close=close_price,
            volume=volume,
            tick_count=tick_count,
            is_index_future=is_index_future,
        )

    return _make