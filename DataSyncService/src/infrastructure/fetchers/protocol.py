from datetime import datetime
from typing import Optional, Protocol

import pandas as pd


class DataFetcher(Protocol):
    """Common interface every OHLCV source must satisfy."""

    async def fetch_batch(
        self,
        symbols: list[str],
        interval: str,
        days: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> dict[str, pd.DataFrame]: ...

    async def fetch_since(
        self,
        symbol: str,
        interval: str,
        since: datetime,
    ) -> pd.DataFrame: ...
