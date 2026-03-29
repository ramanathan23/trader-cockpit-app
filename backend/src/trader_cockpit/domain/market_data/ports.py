"""Outbound port (interface) for market data. Implemented by the Dhan adapter."""
from abc import ABC, abstractmethod
from datetime import date

from trader_cockpit.domain.shared.symbol import Symbol
from .entities import OHLCV, Instrument
from .enums import CandleInterval


class IMarketDataPort(ABC):
    """
    Port for fetching historical and reference market data from the broker.
    Implemented by DhanMarketDataAdapter.
    The live feed (WebSocket ticks) is handled separately via DhanFeedAdapter.
    """

    @abstractmethod
    async def get_historical_candles(
        self,
        symbol: Symbol,
        security_id: str,
        interval: CandleInterval,
        from_date: date,
        to_date: date,
    ) -> list[OHLCV]:
        """Fetch OHLCV candles from broker historical API."""
        ...

    @abstractmethod
    async def get_instrument(self, security_id: str) -> Instrument | None:
        """Fetch instrument metadata (lot size, sector, tick size, etc.)."""
        ...

    @abstractmethod
    async def search_instruments(self, query: str) -> list[Instrument]:
        """Search instruments by name or ticker."""
        ...
