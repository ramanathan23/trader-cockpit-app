import logging
from io import StringIO

import httpx
import pandas as pd

from ._master_types import DHAN_MASTER_URL, MasterData, _REQUIRED_COLS
from ._master_parser import _extract_equities, _extract_index_futures

logger = logging.getLogger(__name__)

_NORMALISE_COLS = [
    "SEM_EXM_EXCH_ID",
    "SEM_SEGMENT",
    "SEM_INSTRUMENT_NAME",
    "SEM_SERIES",
    "SEM_TRADING_SYMBOL",
    "SEM_CUSTOM_SYMBOL",
]


async def download_and_parse(
    url: str = DHAN_MASTER_URL,
    *,
    timeout_s: float = 30.0,
) -> MasterData:
    """
    Download the Dhan instrument master CSV and return typed records.

    Raises httpx.HTTPError on network / HTTP failures.
    Raises ValueError if required columns are missing.
    """
    logger.info("Downloading Dhan instrument master from %s", url)
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.get(url)
        response.raise_for_status()

    raw_csv = response.text
    logger.info("Downloaded %d bytes", len(raw_csv))

    df = pd.read_csv(StringIO(raw_csv), low_memory=False)
    df.columns = df.columns.str.strip()

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Dhan master CSV missing expected columns: {missing}")

    for col in _NORMALISE_COLS:
        df[col] = df[col].astype(str).str.strip()

    equities      = _extract_equities(df)
    index_futures = _extract_index_futures(df)

    logger.info(
        "Master parsed: %d equities, %d index futures",
        len(equities), len(index_futures),
    )
    return MasterData(equities=equities, index_futures=index_futures)
