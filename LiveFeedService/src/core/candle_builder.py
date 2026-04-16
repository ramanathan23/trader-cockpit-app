"""
CandleBuilder: aggregates tick-by-tick data into fixed 3-minute OHLCV candles.

Design:
  - Candle boundaries are fixed from MARKET_OPEN every CANDLE_MINUTES minutes:
      9:15, 9:18, 9:21 … 15:27, 15:30  (all IST)
  - The FIRST boundary encountered when the stream connects may be partial
    (ticks before our connection are lost). We silently discard it and begin
    accumulating from the NEXT boundary, ensuring every emitted candle is
    complete.
  - One CandleBuilder instance per instrument — no shared state.
  - on_tick() returns a completed Candle when a boundary rolls over, else None.
    Callers receive the candle synchronously so they can route it immediately
    (signal engine, DB writer, etc.) without an internal queue.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Optional

from ..domain.candle import Candle
from ..domain.direction import Direction

_IST = ZoneInfo("Asia/Kolkata")


def _boundary(dt: datetime, open_h: int, open_m: int, candle_min: int) -> Optional[datetime]:
    """
    Floor *dt* (any tz) to the nearest candle boundary ≥ MARKET_OPEN.
    Returns None when outside market hours.
    """
    ist = dt.astimezone(_IST)
    open_total  = open_h * 60 + open_m          # e.g. 9*60+15 = 555
    close_total = 15 * 60 + 30                  # 15:30 fixed

    tick_total = ist.hour * 60 + ist.minute
    if tick_total < open_total or tick_total >= close_total:
        return None

    minutes_since_open = tick_total - open_total
    floored            = (minutes_since_open // candle_min) * candle_min
    boundary_total     = open_total + floored

    return ist.replace(
        hour        = boundary_total // 60,
        minute      = boundary_total % 60,
        second      = 0,
        microsecond = 0,
    )


class _ActiveCandle:
    """Mutable accumulator for the candle currently being built."""

    __slots__ = ("boundary", "open", "high", "low", "close", "volume", "tick_count")

    def __init__(self, boundary: datetime, price: float, qty: int) -> None:
        self.boundary   = boundary
        self.open       = price
        self.high       = price
        self.low        = price
        self.close      = price
        self.volume     = qty
        self.tick_count = 1

    def update(self, price: float, qty: int) -> None:
        if price > self.high: self.high = price
        if price < self.low:  self.low  = price
        self.close      = price
        self.volume    += qty
        self.tick_count += 1

    def to_candle(self, symbol: str, is_index_future: bool) -> Candle:
        return Candle(
            symbol          = symbol,
            boundary        = self.boundary,
            open            = self.open,
            high            = self.high,
            low             = self.low,
            close           = self.close,
            volume          = self.volume,
            tick_count      = self.tick_count,
            is_index_future = is_index_future,
        )


class CandleBuilder:
    """
    Aggregates ticks for one instrument into 3-min candles.

    Parameters
    ----------
    symbol          : instrument ticker (used in emitted Candle)
    is_index_future : whether this is an index futures contract
    history_size    : rolling window of completed candles kept in memory
                      (used by the signal engine for rolling metrics)
    open_h / open_m : market open hour/minute in IST (default 9:15)
    candle_min      : candle size in minutes (default 3)
    """

    def __init__(
        self,
        symbol:          str,
        is_index_future: bool = False,
        history_size:    int  = 50,
        open_h:          int  = 9,
        open_m:          int  = 15,
        candle_min:      int  = 3,
    ) -> None:
        self.symbol          = symbol
        self.is_index_future = is_index_future
        self._open_h         = open_h
        self._open_m         = open_m
        self._candle_min     = candle_min

        self._current:  Optional[_ActiveCandle]  = None
        self._is_first: bool                     = True   # True until first boundary seen
        self._history:  deque[Candle]            = deque(maxlen=history_size)

    # ── Public interface ───────────────────────────────────────────────────────

    def on_tick(self, price: float, qty: int, tick_time: datetime) -> Optional[Candle]:
        """
        Feed a tick.

        Returns a completed Candle when a boundary rolls over, else None.
        The returned candle is also appended to the internal history.
        """
        bnd = _boundary(tick_time, self._open_h, self._open_m, self._candle_min)
        if bnd is None:
            return None   # outside market hours

        if self._current is None:
            # Very first tick of the session.
            # Mark as first boundary — we'll discard the candle that completes
            # on the NEXT boundary cross because we may have missed ticks before
            # our WebSocket connected.
            self._current  = _ActiveCandle(bnd, price, qty)
            self._is_first = not self._history
            return None

        if bnd == self._current.boundary:
            self._current.update(price, qty)
            return None

        # Boundary rolled — complete the current candle.
        completed = self._current.to_candle(self.symbol, self.is_index_future)
        self._current = _ActiveCandle(bnd, price, qty)

        if self._is_first:
            # First candle is potentially partial — discard silently.
            self._is_first = False
            return None

        self._history.append(completed)
        return completed

    def get_history(self, n: int | None = None) -> list[Candle]:
        """Return up to *n* most recent completed candles (newest last)."""
        if n is None:
            return list(self._history)
        return list(self._history)[-n:]

    def seed_history(self, candles: list[Candle]) -> None:
        """Seed completed candles loaded from storage so indicators can warm-start."""
        if not candles:
            return
        self._history.clear()
        for candle in sorted(candles, key=lambda c: c.boundary):
            self._history.append(candle)
        self._is_first = False

    def last_price(self) -> Optional[float]:
        """Most recent close price (from the last completed candle or active tick)."""
        if self._current:
            return self._current.close
        if self._history:
            return self._history[-1].close
        return None

    def candles_completed(self) -> int:
        return len(self._history)

    def reset(self) -> None:
        """Reset for a new trading session."""
        self._current  = None
        self._is_first = True
        self._history.clear()
