"""
TickRouter: routes incoming Dhan ticks to the correct CandleBuilder.

Responsibilities:
  - Maintain one CandleBuilder per subscribed instrument (keyed by security_id).
  - Accept raw Dhan tick dicts and dispatch to the right builder.
  - Emit (instrument_meta, completed_candle) pairs to a caller-supplied callback.
  - Reset all builders at session open each day.

Thread-safety: NOT thread-safe — designed for single-threaded asyncio use.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

from ..core.candle_builder import CandleBuilder
from ..core.session_manager import SessionManager
from ..domain.candle import Candle
from ..domain.instrument_meta import InstrumentMeta

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")

# Dhan tick keys (Ticker subscription mode)
_KEY_SECURITY_IDS = ("security_id", "securityId")
_KEY_LTP          = "LTP"
_KEY_LTQ          = "LTQ"   # last traded quantity (tick volume)
_KEY_LTT          = "LTT"   # last traded time (epoch seconds)

OnCandleCallback = Callable[[InstrumentMeta, Candle], Awaitable[None]]


class TickRouter:
    """
    Routes Dhan market-feed ticks to per-instrument CandleBuilders.

    Usage
    -----
    router = TickRouter(instruments, session_manager, on_candle_cb, open_h=9, open_m=15, candle_min=3)
    await router.on_tick(raw_tick_dict)      # called from WebSocket receive loop
    router.reset_session()                   # called at 9:15 each day
    """

    def __init__(
        self,
        instruments:    list[InstrumentMeta],
        session_manager: SessionManager,
        on_candle:      OnCandleCallback,
        open_h:         int = 9,
        open_m:         int = 15,
        candle_min:     int = 3,
    ) -> None:
        self._session  = session_manager
        self._on_candle = on_candle
        self._open_h   = open_h
        self._open_m   = open_m
        self._candle_min = candle_min

        # Primary lookup: security_id → (meta, builder)
        self._builders: dict[int, tuple[InstrumentMeta, CandleBuilder]] = {}
        for meta in instruments:
            self._register(meta)

        logger.info("TickRouter initialised with %d instruments", len(self._builders))

    # ── Public interface ───────────────────────────────────────────────────────

    async def on_tick(self, raw: dict) -> None:
        """
        Process one raw Dhan tick dict.

        Silently ignores ticks for unknown security IDs (can happen briefly
        after a subscription change) or malformed payloads.
        """
        try:
            sec_id = _extract_security_id(raw)
        except (KeyError, TypeError, ValueError):
            return

        entry = self._builders.get(sec_id)
        if entry is None:
            return   # not subscribed

        meta, builder = entry

        try:
            price = float(raw[_KEY_LTP])
            qty   = int(raw.get(_KEY_LTQ, 0))
            ltt   = raw.get(_KEY_LTT)
            tick_time = _parse_ltt(ltt)
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("Malformed tick for security %d: %s", sec_id, exc)
            return

        if tick_time is None:
            return  # unparseable LTT — skip tick

        if not self._session.is_market_open(tick_time):
            return

        candle = builder.on_tick(price, qty, tick_time)
        if candle is not None:
            await self._on_candle(meta, candle)

    def register(self, meta: InstrumentMeta) -> None:
        """Dynamically add a new instrument (e.g. after ATM shift)."""
        self._register(meta)

    def deregister(self, security_id: int) -> None:
        """Remove an instrument from routing."""
        self._builders.pop(security_id, None)

    def reset_session(self) -> None:
        """Reset all CandleBuilders at the start of a new trading day."""
        for _, builder in self._builders.values():
            builder.reset()
        logger.info("TickRouter: all %d builders reset for new session", len(self._builders))

    def get_builder(self, security_id: int) -> CandleBuilder | None:
        entry = self._builders.get(security_id)
        return entry[1] if entry else None

    def instrument_count(self) -> int:
        return len(self._builders)

    def builder_summary(self) -> list[dict]:
        """
        Per-instrument diagnostic snapshot — symbol, candles completed, last close.
        Sorted by symbol for stable output.
        """
        rows = []
        for meta, builder in self._builders.values():
            rows.append({
                "symbol":            meta.symbol,
                "is_index_future":   meta.is_index_future,
                "candles_completed": builder.candles_completed(),
                "last_price":        builder.last_price(),
            })
        return sorted(rows, key=lambda r: r["symbol"])

    # ── Private ───────────────────────────────────────────────────────────────

    def _register(self, meta: InstrumentMeta) -> None:
        builder = CandleBuilder(
            symbol          = meta.symbol if not meta.is_index_future else (meta.underlying or meta.symbol),
            is_index_future = meta.is_index_future,
            open_h          = self._open_h,
            open_m          = self._open_m,
            candle_min      = self._candle_min,
        )
        self._builders[meta.dhan_security_id] = (meta, builder)


def _parse_ltt(ltt) -> datetime | None:
    """
    Parse Dhan LTT (last traded time).

    Dhan sends LTT as Unix epoch seconds (integer or float).
    Returns None if missing or unparseable — caller should skip the tick.
    """
    if ltt is not None:
        try:
            return datetime.fromtimestamp(float(ltt), tz=_IST)
        except (TypeError, ValueError, OSError):
            pass
        if isinstance(ltt, str):
            try:
                parsed = datetime.strptime(ltt, "%H:%M:%S")
                now = datetime.now(tz=_IST)
                return now.replace(
                    hour=parsed.hour,
                    minute=parsed.minute,
                    second=parsed.second,
                    microsecond=0,
                )
            except ValueError:
                pass
    logger.warning("Unparseable LTT value: %r — skipping tick", ltt)
    return None


def _extract_security_id(raw: dict) -> int:
    for key in _KEY_SECURITY_IDS:
        if key in raw:
            return int(raw[key])
    raise KeyError("security_id")
