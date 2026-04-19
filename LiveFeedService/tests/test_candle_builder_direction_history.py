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

class TestDirection:
    def _emit_candle(self, boundary_open, last_close):
        b = _builder()
        b.on_tick(100.0, 100, _ist(9, 15))
        b.on_tick(boundary_open, 100, _ist(9, 18))
        b.on_tick(last_close, 100, _ist(9, 20))
        return b.on_tick(999.0, 100, _ist(9, 21))

    def test_bullish_candle(self):
        candle = self._emit_candle(100.0, 105.0)
        assert candle is not None
        assert candle.direction == Direction.BULLISH

    def test_bearish_candle(self):
        candle = self._emit_candle(100.0, 95.0)
        assert candle is not None
        assert candle.direction == Direction.BEARISH

    def test_neutral_candle(self):
        candle = self._emit_candle(100.0, 100.0)
        assert candle is not None
        assert candle.direction == Direction.NEUTRAL


class TestHistorySeeding:
    def test_seed_disables_first_candle_discard(self):
        b = _builder()
        today = datetime.now(tz=_IST).date()
        seed = Candle(
            symbol="TEST",
            boundary=datetime(today.year, today.month, today.day, 9, 9, tzinfo=_IST),
            open=100.0, high=101.0, low=99.0, close=100.5, volume=1000, tick_count=5,
        )
        b.seed_history([seed])
        assert b.candles_completed() == 1
        b.on_tick(100.0, 100, _ist(9, 15))
        candle = b.on_tick(101.0, 200, _ist(9, 18))
        assert candle is not None

    def test_seed_preserves_chronological_order(self):
        b = _builder()
        today = datetime.now(tz=_IST).date()
        candles = [
            Candle("TEST", datetime(today.year, today.month, today.day, h, 15, tzinfo=_IST),
                   100.0, 101.0, 99.0, 100.0, 1000, 5)
            for h in [9, 11, 14]
        ]
        b.seed_history(candles)
        history = b.get_history()
        assert len(history) == 3
        assert history[0].boundary.hour == 9
        assert history[-1].boundary.hour == 14
