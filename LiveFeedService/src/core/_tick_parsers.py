from __future__ import annotations

import logging
from datetime import datetime
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

from ..domain.candle import Candle
from ..domain.instrument_meta import InstrumentMeta

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")
_KEY_SECURITY_IDS = ("security_id", "securityId")

OnCandleCallback = Callable[[InstrumentMeta, Candle], Awaitable[None]]


def _parse_ltt(ltt) -> datetime | None:
    """Parse Dhan LTT (last traded time). Returns None if unparseable."""
    if ltt is not None:
        try:
            return datetime.fromtimestamp(float(ltt), tz=_IST)
        except (TypeError, ValueError, OSError):
            pass
        if isinstance(ltt, str):
            try:
                parsed = datetime.strptime(ltt, "%H:%M:%S")
                now    = datetime.now(tz=_IST)
                return now.replace(
                    hour=parsed.hour, minute=parsed.minute,
                    second=parsed.second, microsecond=0,
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
