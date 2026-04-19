"""
Maps Dhan instrument master records onto the trader_cockpit database.

Responsibilities:
  1. Update symbols.dhan_security_id + exchange_segment for all matched equities.
  2. Upsert index_futures rows (NIFTY / BANKNIFTY / SENSEX front-month contracts).
  3. Mark exactly one index_futures row per underlying as is_active (nearest expiry
     on or after today).

Returns a MappingResult summary for the caller / API response.
"""

from dataclasses import dataclass

from ._equity_mapper import apply_equity_mapping
from ._futures_mapper import apply_index_future_mapping

__all__ = ["MappingResult", "apply_equity_mapping", "apply_index_future_mapping"]


@dataclass
class MappingResult:
    equities_matched:        int
    equities_unmatched:      int
    index_futures_upserted:  int
    index_futures_activated: int

