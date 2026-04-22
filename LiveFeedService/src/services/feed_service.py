from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from ..config import Settings
from ..core.session_manager import SessionManager
from ..domain.index_bias import IndexBias
from ..infrastructure.redis.publisher import SignalPublisher
from ..infrastructure.redis.token_store import TokenStore
from ..repositories.candle_repository import BufferedCandleWriter, CandleRepository
from ..repositories.symbol_repository import SymbolRepository
from ..signals.engine import SignalEngine
from .instrument_loader import InstrumentLoader
from .metrics_service import MetricsService
from ._feed_init_mixin import _FeedInitMixin
from ._feed_status_mixin import _FeedStatusMixin
from ._feed_signal_mixin import _FeedSignalMixin

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")


class FeedService(_FeedInitMixin, _FeedStatusMixin, _FeedSignalMixin):
    """Wires all components together and runs the main tick-processing loop."""

    def __init__(
        self,
        symbol_repo:     SymbolRepository,
        candle_repo:     CandleRepository,
        publisher:       SignalPublisher,
        token_store:     TokenStore,
        settings:        Settings,
        metrics_service: MetricsService,
    ) -> None:
        self._publisher       = publisher
        self._token_store     = token_store
        self._settings        = settings
        self._metrics_service = metrics_service
        self._session_mgr     = SessionManager()
        self._loader          = InstrumentLoader(
            symbol_repo, candle_repo,
            warm_limit=max(settings.drive_candles, settings.confluence_1h_candles),
            candle_min=settings.candle_minutes,
        )
        self._writer = BufferedCandleWriter(
            candle_repo,
            batch_size  = settings.candle_write_batch_size,
            flush_every = settings.candle_write_flush_s,
        )
        self._sub_mgr:    SubscriptionManager | None = None
        self._tick_router: TickRouter | None         = None
        self._engines:    dict[str, SignalEngine]    = {}
        self._index_bias = IndexBias()
        self._session_date: date | None              = None
        self._ticks_received:    int          = 0
        self._candles_completed: int          = 0
        self._signals_emitted:   int          = 0
        self._last_tick_at: datetime | None   = None
