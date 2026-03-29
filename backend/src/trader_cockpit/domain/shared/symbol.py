from dataclasses import dataclass
from enum import Enum


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"   # NSE Futures and Options
    BFO = "BFO"   # BSE Futures and Options
    MCX = "MCX"


@dataclass(frozen=True)
class Symbol:
    value: str           # e.g. "RELIANCE", "NIFTY24DEC24000CE"
    exchange: Exchange

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("Symbol value cannot be empty")
        object.__setattr__(self, "value", self.value.strip().upper())

    def __str__(self) -> str:
        return f"{self.exchange.value}:{self.value}"

    @property
    def is_derivative(self) -> bool:
        return self.exchange in (Exchange.NFO, Exchange.BFO)

    @property
    def is_equity(self) -> bool:
        return self.exchange in (Exchange.NSE, Exchange.BSE)
