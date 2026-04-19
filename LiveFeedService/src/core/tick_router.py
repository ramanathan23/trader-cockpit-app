from __future__ import annotations

import logging

from .candle_builder import CandleBuilder
from .session_manager import SessionManager
from ..domain.instrument_meta import InstrumentMeta
from ._tick_parsers import _parse_ltt, _extract_security_id, OnCandleCallback

logger = logging.getLogger(__name__)


class TickRouter:
    """Routes Dhan market-feed ticks to per-instrument CandleBuilders."""

    def __init__(
        self,
        instruments:     list[InstrumentMeta],
        session_manager: SessionManager,
        on_candle:       OnCandleCallback,
        open_h:          int = 9,
        open_m:          int = 15,
        candle_min:      int = 3,
    ) -> None:
        self._session    = session_manager
        self._on_candle  = on_candle
        self._open_h     = open_h
        self._open_m     = open_m
        self._candle_min = candle_min
        self._builders: dict[int, tuple[InstrumentMeta, CandleBuilder]] = {}
        for meta in instruments:
            self._register(meta)
        logger.info("TickRouter initialised with %d instruments", len(self._builders))

    async def on_tick(self, raw: dict) -> None:
        """Process one raw Dhan tick dict."""
        try:
            sec_id = _extract_security_id(raw)
        except (KeyError, TypeError, ValueError):
            return
        entry = self._builders.get(sec_id)
        if entry is None:
            return
        meta, builder = entry
        try:
            price     = float(raw["LTP"])
            qty       = int(raw.get("LTQ", 0))
            ltt       = raw.get("LTT")
            tick_time = _parse_ltt(ltt)
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("Malformed tick for security %d: %s", sec_id, exc)
            return
        if tick_time is None:
            return
        if not self._session.is_market_open(tick_time):
            return
        candle = builder.on_tick(price, qty, tick_time)
        if candle is not None:
            await self._on_candle(meta, candle)

    def register(self, meta: InstrumentMeta) -> None:
        """Dynamically add a new instrument."""
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
        """Per-instrument snapshot: symbol, candles, last price."""
        rows = []
        for meta, builder in self._builders.values():
            rows.append({
                "symbol":            meta.symbol,
                "is_index_future":   meta.is_index_future,
                "candles_completed": builder.candles_completed(),
                "last_price":        builder.last_price(),
            })
        return sorted(rows, key=lambda r: r["symbol"])

    def _register(self, meta: InstrumentMeta) -> None:
        sym = meta.symbol if not meta.is_index_future else (meta.underlying or meta.symbol)
        b   = CandleBuilder(sym, meta.is_index_future,
                            open_h=self._open_h, open_m=self._open_m,
                            candle_min=self._candle_min)
        self._builders[meta.dhan_security_id] = (meta, b)
