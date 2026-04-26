from __future__ import annotations

from ...domain.signal import Signal
from ...domain.signal_type import SignalType as _ST

_EXEMPT = {
    _ST.CAM_H3_REVERSAL, _ST.CAM_H4_BREAKOUT,
    _ST.CAM_L3_REVERSAL, _ST.CAM_L4_BREAKDOWN,
}


def cluster_check_signal(
    signal: Signal,
    cluster_counts: dict[tuple[str, str], int],
    cluster_boundary: str,
    cluster_max: int,
) -> tuple[bool, dict[tuple[str, str], int], str]:
    """Returns (ok, updated_counts, updated_boundary). Drive-family signals exempt."""
    if signal.signal_type in _EXEMPT:
        return True, cluster_counts, cluster_boundary
    boundary = signal.timestamp.strftime("%Y-%m-%dT%H:%M")
    key      = (signal.signal_type.value, boundary)
    new_counts = dict(cluster_counts)
    new_counts[key] = new_counts.get(key, 0) + 1
    if boundary != cluster_boundary:
        new_counts = {k: v for k, v in new_counts.items() if k[1] == boundary}
    return new_counts[key] <= cluster_max, new_counts, boundary
