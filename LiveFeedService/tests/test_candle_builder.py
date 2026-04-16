"""
Unit tests for CandleBuilder.

No DB, no network — driven entirely by synthetic ticks with precise IST timestamps.
Exercises boundary detection, OHLCV accumulation, first-candle discard,
history seeding, and direction computation.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.core.candle_builder import CandleBuilder
from src.domain.candle import Candle
from src.domain.direction import Direction

_IST = ZoneInfo("Asia/Kolkata")


def _ist(hour: int, minute: int, second: int = 0) -> datetime:
    today = datetime.now(tz=_IST).date()
    return datetime(today.year, today.month, today.day,
                    hour, minute, second, tzinfo=_IST)


def _builder(symbol: str = "TEST") -> CandleBuilder:
    return CandleBuilder(symbol, open_h=9, open_m=15, candle_min=3)


class TestFirstCandleDiscard:
    def test_first_boundary_always_discarded(self):
        """The very first boundary seen may be partial — always drop it."""
        b = _builder()
        assert b.on_tick(100.0, 100, _ist(9, 15)) is None
        # Cross into next boundary — first candle completes but is discarded.
        assert b.on_tick(101.0, 100, _ist(9, 18)) is None
        assert b.candles_completed() == 0

    def test_second_boundary_emitted(self):
        b = _builder()
        b.on_tick(100.0, 100, _ist(9, 15))
        b.on_tick(101.0, 100, _ist(9, 18))   # first candle → discarded
        candle = b.on_tick(102.0, 200, _ist(9, 21))  # second candle emitted
        assert candle is not None
        assert candle.symbol == "TEST"
        assert b.candles_completed() == 1


class TestOHLCVAccumulation:
    def test_open_high_low_close_volume(self):
        """Within one boundary, OHLCV accumulates correctly.

        Key mechanic: the tick that CROSSES a boundary opens the next candle —
        it is NOT included in the candle that just completed.
        """
        b = _builder()
        # First boundary (will be discarded on roll).
        b.on_tick(100.0, 100, _ist(9, 15))
        b.on_tick(99.0,  50,  _ist(9, 16))
        b.on_tick(103.0, 75,  _ist(9, 17))
        # Cross to 9:18 — first candle (discarded) completes; 200.0 opens 9:18 boundary.
        assert b.on_tick(200.0, 10, _ist(9, 18)) is None

        b.on_tick(204.0, 100, _ist(9, 19))  # new high
        b.on_tick(198.0, 150, _ist(9, 20))  # new low; this becomes close
        # Cross to 9:21 — 9:18 candle completes; 202.0 tick opens 9:21 boundary.
        candle = b.on_tick(202.0, 50, _ist(9, 21))

        assert candle is not None
        assert candle.open   == 200.0
        assert candle.high   == 204.0
        assert candle.low    == 198.0
        assert candle.close  == 198.0   # last tick BEFORE the boundary cross
        assert candle.volume == 260     # 10+100+150 (the 50-qty cross tick opens next candle)

    def test_tick_count(self):
        b = _builder()
        b.on_tick(100.0, 100, _ist(9, 15))
        b.on_tick(101.0, 100, _ist(9, 18))   # discard first; 101.0 opens second boundary
        b.on_tick(102.0, 100, _ist(9, 19))
        b.on_tick(103.0, 100, _ist(9, 20))
        candle = b.on_tick(104.0, 100, _ist(9, 21))  # 104.0 opens third boundary
        assert candle is not None
        assert candle.tick_count == 3   # 101.0, 102.0, 103.0


class TestMarketHours:
    def test_before_open_returns_none(self):
        b = _builder()
        assert b.on_tick(100.0, 100, _ist(8, 0)) is None

    def test_at_or_after_close_returns_none(self):
        b = _builder()
        assert b.on_tick(100.0, 100, _ist(15, 30)) is None
        assert b.on_tick(100.0, 100, _ist(16, 0))  is None


class TestDirection:
    def _emit_candle(self, boundary_open: float, last_close: float) -> Candle:
        """
        Emit the second candle with a controlled open and close.

        boundary_open : price of the first tick in the target boundary (sets candle open)
        last_close    : price of the last tick before the boundary rolls (sets candle close)
        """
        b = _builder()
        b.on_tick(100.0, 100, _ist(9, 15))          # start first boundary (discarded)
        b.on_tick(boundary_open, 100, _ist(9, 18))  # cross; first discarded; opens with boundary_open
        b.on_tick(last_close, 100, _ist(9, 20))     # last tick in boundary → sets close
        return b.on_tick(999.0, 100, _ist(9, 21))   # cross; candle emitted with close=last_close

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
        """After seeding, the first live candle is not discarded."""
        b = _builder()
        today = datetime.now(tz=_IST).date()
        seed = Candle(
            symbol="TEST",
            boundary=datetime(today.year, today.month, today.day, 9, 9, tzinfo=_IST),
            open=100.0, high=101.0, low=99.0, close=100.5,
            volume=1000, tick_count=5,
        )
        b.seed_history([seed])
        assert b.candles_completed() == 1

        b.on_tick(100.0, 100, _ist(9, 15))
        candle = b.on_tick(101.0, 200, _ist(9, 18))
        assert candle is not None   # not discarded after seeding

    def test_seed_preserves_chronological_order(self):
        b = _builder()
        today = datetime.now(tz=_IST).date()
        # Use different hours (not minutes) so boundaries sort correctly.
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
