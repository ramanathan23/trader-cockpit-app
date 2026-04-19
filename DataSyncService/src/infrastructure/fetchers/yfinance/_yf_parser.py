import logging

import pandas as pd

logger = logging.getLogger(__name__)

_NSE_SUFFIX = ".NS"

_INDEX_TICKERS: dict[str, str] = {
    "NIFTY500": "^CRSLDX",
}


def ticker(symbol: str) -> str:
    return _INDEX_TICKERS.get(symbol, f"{symbol}{_NSE_SUFFIX}")


def extract_single_symbol(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        parsed = parse_multiindex(raw, [symbol])
        return parsed.get(symbol, pd.DataFrame())

    cols     = {str(col).strip().lower(): col for col in raw.columns}
    required = ["open", "high", "low", "close", "volume"]
    if not all(name in cols for name in required):
        logger.debug(
            "Single-symbol yfinance response missing OHLCV columns for %s: %s",
            ticker(symbol), list(raw.columns),
        )
        return pd.DataFrame()

    df = raw[[cols["open"], cols["high"], cols["low"], cols["close"], cols["volume"]]].copy()
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    return df.dropna(subset=["Open", "Close"])


def parse_multiindex(raw: pd.DataFrame, symbols: list[str]) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        t = ticker(symbol)
        try:
            df = pd.DataFrame({
                "Open":   raw["Open"][t],
                "High":   raw["High"][t],
                "Low":    raw["Low"][t],
                "Close":  raw["Close"][t],
                "Volume": raw["Volume"][t],
            })
            df = df.dropna(subset=["Open", "Close"])
            if not df.empty:
                result[symbol] = df
        except (KeyError, TypeError):
            logger.debug("No data in response for %s", t)
    return result
