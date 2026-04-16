from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SyncStateSnapshot:
    symbol: str
    timeframe: str
    last_synced_at: datetime | None
    last_data_ts: datetime | None
    status: str | None
