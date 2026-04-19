from __future__ import annotations

from collections import deque
from datetime import datetime

from ..domain.candle import Candle
from ._candle_boundary import _boundary
from ._active_candle import _ActiveCandle


class CandleBuilder:
    """Aggregates ticks for one instrument into CANDLE_MIN-minute candles."""

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
        self._current:  _ActiveCandle | None = None
        self._is_first: bool                 = True
        self._history:  deque[Candle]        = deque(maxlen=history_size)
        self._session_open: float | None     = None
        self._last_tick_minute: int | None   = None
        self._last_tick_hour:   int | None   = None

    def on_tick(self, price: float, qty: int, tick_time: datetime) -> Candle | None:
        """Feed a tick; returns completed Candle on boundary roll, else None."""
        if (
            self._current is not None
            and self._last_tick_minute is not None
            and tick_time.minute == self._last_tick_minute
            and tick_time.hour == self._last_tick_hour
        ):
            self._current.update(price, qty)
            return None
        bnd = _boundary(tick_time, self._open_h, self._open_m, self._candle_min)
        self._last_tick_minute = tick_time.minute
        self._last_tick_hour   = tick_time.hour
        if bnd is None:
            return None
        if self._current is None:
            self._current  = _ActiveCandle(bnd, price, qty)
            self._is_first = not self._history
            if self._session_open is None:
                self._session_open = price
            return None
        if bnd == self._current.boundary:
            self._current.update(price, qty)
            return None
        completed = self._current.to_candle(self.symbol, self.is_index_future)
        self._current = _ActiveCandle(bnd, price, qty)
        if self._is_first:
            self._is_first = False
            return None
        self._history.append(completed)
        return completed

    def get_history(self, n: int | None = None) -> list[Candle]:
        if n is None:
            return list(self._history)
        return list(self._history)[-n:]

    def seed_history(self, candles: list[Candle]) -> None:
        """Seed completed candles from storage to warm-start indicators."""
        if not candles:
            return
        self._history.clear()
        for candle in sorted(candles, key=lambda c: c.boundary):
            self._history.append(candle)
        self._is_first = False

    def last_price(self) -> float | None:
        if self._current:
            return self._current.close
        if self._history:
            return self._history[-1].close
        return None

    def candles_completed(self) -> int: return len(self._history)

    @property
    def session_open_price(self) -> float | None:
        """First tick price of the session (even if first candle was discarded)."""
        return self._session_open

    def reset(self) -> None:
        """Reset for a new trading session."""
        self._current = self._session_open = self._last_tick_minute = self._last_tick_hour = None
        self._is_first = True
        self._history.clear()
