from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class _FeedStatusMixin:
    async def _status_broadcast_loop(self) -> None:
        """Push market phase + per-index bias to WS clients every 10 s."""
        while True:
            try:
                await self._publisher.publish_status({
                    "session_phase": self._session_mgr.current_phase().value,
                    "index_bias": {
                        "nifty":     self._index_bias.nifty.value,
                        "banknifty": self._index_bias.banknifty.value,
                        "sensex":    self._index_bias.sensex.value,
                    },
                })
            except Exception as exc:
                logger.warning("status broadcast failed: %s", exc)
            await asyncio.sleep(10)

    def status(self) -> dict:
        builders          = self._tick_router.builder_summary() if self._tick_router else []
        active_builders   = [b for b in builders if b["candles_completed"] > 0]
        inactive_builders = [b for b in builders if b["candles_completed"] == 0]
        return {
            "session_phase":     self._session_mgr.current_phase().value,
            "session_date":      self._session_date.isoformat() if self._session_date else None,
            "connections":       self._sub_mgr.connection_count() if self._sub_mgr else 0,
            "instruments_total": len(builders),
            "ticks_received":    self._ticks_received,
            "candles_completed": self._candles_completed,
            "signals_emitted":   self._signals_emitted,
            "last_tick_at":      self._last_tick_at.isoformat() if self._last_tick_at else None,
            "index_bias": {
                "nifty":     self._index_bias.nifty.value,
                "banknifty": self._index_bias.banknifty.value,
                "sensex":    self._index_bias.sensex.value,
            },
            "active_symbols": [b["symbol"] for b in active_builders],
            "silent_symbols": [b["symbol"] for b in inactive_builders],
            "candle_counts":  {
                b["symbol"]: {"candles": b["candles_completed"], "last_price": b["last_price"]}
                for b in active_builders
            },
        }

    def screener_live_metrics(self) -> dict[str, dict]:
        """Lightweight live snapshot for the screener."""
        if not self._tick_router:
            return {}
        live: dict[str, dict] = {}
        for row in self._tick_router.builder_summary():
            if row["is_index_future"]:
                continue
            symbol = row["symbol"]
            snapshot: dict[str, float] = {}
            if row["last_price"] is not None:
                snapshot["current_price"] = round(float(row["last_price"]), 2)
            engine = self._engines.get(symbol)
            if engine is not None:
                vwap = engine.current_vwap()
                if vwap is not None:
                    snapshot["daily_vwap"] = round(float(vwap), 2)
            if snapshot:
                live[symbol] = snapshot
        return live
