"""
Pattern screen for directional runs followed by tight consolidation.

The screen is designed for daily watchlists:
  - bull: 4-5 day run-up, then a tight base near the highs
  - bear: 4-5 day sell-off, then a tight base near the lows

The function is pure and explicit about thresholds so the API layer can expose
them without hiding the screening logic inside a repository or route.
"""

from dataclasses import asdict

import pandas as pd

from ..domain.watchlist_candidate import WatchlistCandidate
from ._watchlist_calc import _calc_side_metrics


def detect_run_and_tight_base(
    symbol: str,
    company_name: str | None,
    df: pd.DataFrame,
    *,
    side: str,
    run_window: int = 5,
    base_window: int = 3,
    min_run_move_pct: float = 8.0,
    max_base_range_pct: float = 3.0,
    max_retracement_pct: float = 0.35,
    min_directional_closes: int | None = None,
) -> dict | None:
    required_bars = run_window + base_window + 1
    if len(df) < required_bars:
        return None

    closes = df["close"].astype(float)
    highs  = df["high"].astype(float)
    lows   = df["low"].astype(float)
    volume = df["volume"].astype(float)

    run_start = -(run_window + base_window + 1)
    run_end   = -base_window

    pre_run_close   = float(closes.iloc[run_start])
    run             = df.iloc[run_start + 1:run_end].copy()
    base            = df.iloc[-base_window:].copy()

    if run.empty or base.empty or pre_run_close <= 0:
        return None

    run_closes      = run["close"].astype(float)
    base_high       = float(base["high"].astype(float).max())
    base_low        = float(base["low"].astype(float).min())
    base_last_close = float(base["close"].astype(float).iloc[-1])
    impulse_high    = float(run["high"].astype(float).max())
    impulse_low     = float(run["low"].astype(float).min())
    directional_closes = min_directional_closes or max(3, run_window - 1)

    if side not in {"bull", "bear"}:
        raise ValueError(f"Unsupported side: {side!r}")

    metrics = _calc_side_metrics(
        side, run_closes, pre_run_close, impulse_high, impulse_low,
        base_high, base_low, base_last_close,
        min_run_move_pct, directional_closes,
    )
    if metrics is None:
        return None

    if metrics["base_range_pct"] > max_base_range_pct or metrics["retracement_pct"] > max_retracement_pct:
        return None

    run_avg_volume  = float(volume.iloc[run_start + 1:run_end].mean() or 0.0)
    base_avg_volume = float(volume.iloc[-base_window:].mean() or 0.0)
    volume_contraction = (base_avg_volume / run_avg_volume) if run_avg_volume > 0 else 1.0

    pattern_score = (
        metrics["run_move_pct"] * 5.0
        - metrics["base_range_pct"] * 8.0
        - metrics["retracement_pct"] * 30.0
        - metrics["distance_to_trigger_pct"] * 4.0
        - max(0.0, volume_contraction - 1.0) * 10.0
    )

    candidate = WatchlistCandidate(
        symbol=symbol,
        company_name=company_name,
        side=side,
        pattern_score=round(pattern_score, 2),
        run_move_pct=round(metrics["run_move_pct"], 2),
        base_range_pct=round(metrics["base_range_pct"], 2),
        retracement_pct=round(metrics["retracement_pct"], 3),
        distance_to_trigger_pct=round(metrics["distance_to_trigger_pct"], 2),
        volume_contraction=round(volume_contraction, 2),
        trigger_price=round(metrics["trigger_price"], 2),
        last_close=round(base_last_close, 2),
    )
    return asdict(candidate)