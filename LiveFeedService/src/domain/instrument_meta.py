from dataclasses import dataclass
from typing import Optional


@dataclass
class InstrumentMeta:
    """Lightweight descriptor for a subscribed instrument."""
    symbol:           str
    dhan_security_id: int
    exchange_segment: str
    is_index_future:  bool = False
    underlying:       Optional[str] = None
