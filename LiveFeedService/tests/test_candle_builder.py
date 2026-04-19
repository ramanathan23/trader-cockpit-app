from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from src.core.candle_builder import CandleBuilder
from src.domain.candle import Candle
from src.domain.direction import Direction

_IST = ZoneInfo("Asia/Kolkata")

def _ist(hour, minute, second=0):
    today = datetime.now(tz=_IST).date()
    return datetime(today.year, today.month, today.day, hour, minute, second, tzinfo=_IST)

def _builder(symbol="TEST"):
    return CandleBuilder(symbol, open_h=9, open_m=15, candle_min=3)

class TestFirstCandleDiscard:
    def test_first_boundary_always_discarded(self):
        b = _builder()
        assert b.on_tick(100.0, 100, _ist(9, 15)) is None
        assert b.on_tick(101.0, 100, _ist(9, 18)) is None
        assert b.candles_completed() == 0

    def test_second_boundary_emitted(self):
        b = _builder()
        b.on_tick(100.0, 100, _ist(9, 15))
        b.on_tick(101.0, 100, _ist(9, 18))
        candle = b.on_tick(102.0, 200, _ist(9, 21))
        assert candle is not None
        assert candle.symbol == "TEST"
        assert b.candles_completed() == 1


class TestOHLCVAccumulation:
    def test_open_high_low_close_volume(self):
        b = _builder()
        b.on_tick(100.0, 100, _ist(9, 15))
        b.on_tick(99.0, 50, _ist(9, 16))
        b.on_tick(103.0, 75, _ist(9, 17))
        assert b.on_tick(200.0, 10, _ist(9, 18)) is None
        b.on_tick(204.0, 100, _ist(9, 19))
        b.on_tick(198.0, 150, _ist(9, 20))
        candle = b.on_tick(202.0, 50, _ist(9, 21))
        assert candle is not None
        assert candle.open == 200.0
        assert candle.high == 204.0
        assert candle.low == 198.0
        assert candle.close == 198.0
        assert candle.volume == 260

    def test_tick_count(self):
        b = _builder()
        b.on_tick(100.0, 100, _ist(9, 15))
        b.on_tick(101.0, 100, _ist(9, 18))
        b.on_tick(102.0, 100, _ist(9, 19))
        b.on_tick(103.0, 100, _ist(9, 20))
        candle = b.on_tick(104.0, 100, _ist(9, 21))
        assert candle is not None
        assert candle.tick_count == 3


class TestMarketHours:
    def test_before_open_returns_none(self):
        b = _builder()
        assert b.on_tick(100.0, 100, _ist(8, 0)) is None

    def test_at_or_after_close_returns_none(self):
        b = _builder()
        assert b.on_tick(100.0, 100, _ist(15, 30)) is None
        assert b.on_tick(100.0, 100, _ist(16, 0)) is None
