from __future__ import annotations

import logging
from typing import Awaitable, Callable

from dhanhq import marketfeed as mf

from ...domain.instrument_meta import InstrumentMeta
from .websocket_client import DhanWebSocketClient

logger = logging.getLogger(__name__)


def _to_dhan_instrument(meta: InstrumentMeta) -> tuple[str, str, int]:
    return (_normalise_exchange_segment(meta), str(meta.dhan_security_id), mf.Quote)


def _normalise_exchange_segment(meta: InstrumentMeta) -> str:
    segment = meta.exchange_segment.strip().upper()
    if segment in {"NSE_EQ", "NSE_FNO", "BSE_EQ", "BSE_FNO", "IDX_I"}:
        return segment
    if segment == "E":
        return "NSE_EQ"
    if segment == "D":
        if meta.is_index_future and meta.underlying == "SENSEX":
            return "BSE_FNO"
        return "NSE_FNO"
    logger.warning(
        "Unknown exchange segment '%s' for %s; passing through unchanged",
        meta.exchange_segment, meta.symbol,
    )
    return meta.exchange_segment


def build_dhan_clients(
    equities:          list[InstrumentMeta],
    index_futures:     list[InstrumentMeta],
    client_id:         str,
    token_getter:      Callable[[], Awaitable[str]],
    reconnect_delay_s: float,
    batch_size:        int,
) -> list[DhanWebSocketClient]:
    """Build DhanWebSocketClient list, batching equities and appending index futures."""
    equity_batches: list[list[InstrumentMeta]] = []
    for i in range(0, len(equities), batch_size):
        equity_batches.append(equities[i: i + batch_size])
    if not equity_batches:
        equity_batches = [[]]
    remaining = batch_size - len(equity_batches[-1])
    if len(index_futures) <= remaining:
        equity_batches[-1].extend(index_futures)
    else:
        equity_batches.append(index_futures)
    clients = []
    for batch in equity_batches:
        instruments = [_to_dhan_instrument(m) for m in batch]
        clients.append(DhanWebSocketClient(
            client_id=client_id, token_getter=token_getter,
            instruments=instruments, reconnect_delay_s=reconnect_delay_s,
        ))
    total = sum(len(b) for b in equity_batches)
    logger.info(
        "SubscriptionManager: %d instruments across %d connection(s) "
        "(%d equities, %d index futures)",
        total, len(clients), len(equities), len(index_futures),
    )
    return clients
