from datetime import datetime
from typing import Protocol

import pandas as pd


class DataFetcher(Protocol):
    """Common interface every OHLCV source must satisfy."""

    async def fetch_batch(
        self,
        symbols: list[str],
        days: int,
    ) -> dict[str, pd.DataFrame]: ...

    async def fetch_since(
        self,
        symbol: str,
        since: datetime,
    ) -> pd.DataFrame: ...
