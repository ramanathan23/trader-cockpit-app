"""
Side-specific metric calculations for the run-and-tight-base watchlist pattern.
"""


def _calc_side_metrics(
    side: str,
    run_closes,
    pre_run_close: float,
    impulse_high: float,
    impulse_low: float,
    base_high: float,
    base_low: float,
    base_last_close: float,
    min_run_move_pct: float,
    directional_closes: int,
) -> dict | None:
    """
    Compute side-specific metrics for a run-and-base pattern.
    Returns None if the pattern fails its directional filters.
    """
    if side == "bull":
        run_move_pct = (float(run_closes.iloc[-1]) / pre_run_close - 1.0) * 100.0
        same_dir = int((run_closes.diff() > 0).sum())
        if run_move_pct < min_run_move_pct or same_dir < directional_closes:
            return None
        impulse_range = impulse_high - pre_run_close
        if impulse_range <= 0:
            return None
        base_range_pct = ((base_high - base_low) / impulse_high) * 100.0
        retracement_pct = (impulse_high - base_low) / impulse_range
        distance_pct = ((impulse_high - base_last_close) / impulse_high) * 100.0
        trigger = impulse_high
    else:  # bear
        run_move_pct = (1.0 - float(run_closes.iloc[-1]) / pre_run_close) * 100.0
        same_dir = int((run_closes.diff() < 0).sum())
        if run_move_pct < min_run_move_pct or same_dir < directional_closes:
            return None
        impulse_range = pre_run_close - impulse_low
        if impulse_range <= 0 or impulse_low <= 0:
            return None
        base_range_pct = ((base_high - base_low) / impulse_low) * 100.0
        retracement_pct = (base_high - impulse_low) / impulse_range
        distance_pct = ((base_last_close - impulse_low) / impulse_low) * 100.0
        trigger = impulse_low

    return dict(
        run_move_pct=run_move_pct,
        base_range_pct=base_range_pct,
        retracement_pct=retracement_pct,
        distance_to_trigger_pct=distance_pct,
        trigger_price=trigger,
    )
