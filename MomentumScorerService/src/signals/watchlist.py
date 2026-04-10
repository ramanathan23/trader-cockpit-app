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

from ..domain.models import WatchlistCandidate


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
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    volume = df["volume"].astype(float)

    run_start = -(run_window + base_window + 1)
    run_end = -base_window

    pre_run_close = float(closes.iloc[run_start])
    run = df.iloc[run_start + 1:run_end].copy()
    base = df.iloc[-base_window:].copy()

    if run.empty or base.empty or pre_run_close <= 0:
        return None

    run_closes = run["close"].astype(float)
    base_high = float(base["high"].astype(float).max())
    base_low = float(base["low"].astype(float).min())
    base_last_close = float(base["close"].astype(float).iloc[-1])
    impulse_high = float(run["high"].astype(float).max())
    impulse_low = float(run["low"].astype(float).min())
    directional_closes = min_directional_closes or max(3, run_window - 1)

    if side == "bull":
        run_move_pct = (float(run_closes.iloc[-1]) / pre_run_close - 1.0) * 100.0
        same_direction_days = int((run_closes.diff() > 0).sum())
        if run_move_pct < min_run_move_pct or same_direction_days < directional_closes:
            return None

        impulse_range = impulse_high - pre_run_close
        if impulse_range <= 0:
            return None

        base_range_pct = ((base_high - base_low) / impulse_high) * 100.0
        retracement_pct = (impulse_high - base_low) / impulse_range
        distance_to_trigger_pct = ((impulse_high - base_last_close) / impulse_high) * 100.0
        trigger_price = impulse_high
    elif side == "bear":
        run_move_pct = (1.0 - float(run_closes.iloc[-1]) / pre_run_close) * 100.0
        same_direction_days = int((run_closes.diff() < 0).sum())
        if run_move_pct < min_run_move_pct or same_direction_days < directional_closes:
            return None

        impulse_range = pre_run_close - impulse_low
        if impulse_range <= 0 or impulse_low <= 0:
            return None

        base_range_pct = ((base_high - base_low) / impulse_low) * 100.0
        retracement_pct = (base_high - impulse_low) / impulse_range
        distance_to_trigger_pct = ((base_last_close - impulse_low) / impulse_low) * 100.0
        trigger_price = impulse_low
    else:
        raise ValueError(f"Unsupported side: {side!r}")

    if base_range_pct > max_base_range_pct:
        return None
    if retracement_pct > max_retracement_pct:
        return None

    run_avg_volume = float(volume.iloc[run_start + 1:run_end].mean() or 0.0)
    base_avg_volume = float(volume.iloc[-base_window:].mean() or 0.0)
    volume_contraction = (base_avg_volume / run_avg_volume) if run_avg_volume > 0 else 1.0

    # Higher is better: strong move, tight base, shallow giveback, close to trigger.
    pattern_score = (
        run_move_pct * 5.0
        - base_range_pct * 8.0
        - retracement_pct * 30.0
        - distance_to_trigger_pct * 4.0
        - max(0.0, volume_contraction - 1.0) * 10.0
    )

    candidate = WatchlistCandidate(
        symbol=symbol,
        company_name=company_name,
        side=side,
        pattern_score=round(pattern_score, 2),
        run_move_pct=round(run_move_pct, 2),
        base_range_pct=round(base_range_pct, 2),
        retracement_pct=round(retracement_pct, 3),
        distance_to_trigger_pct=round(distance_to_trigger_pct, 2),
        volume_contraction=round(volume_contraction, 2),
        trigger_price=round(trigger_price, 2),
        last_close=round(base_last_close, 2),
    )
    return asdict(candidate)