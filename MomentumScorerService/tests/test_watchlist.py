import pandas as pd

from src.signals.watchlist import detect_run_and_tight_base


def _frame(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"]).assign(volume=1_000_000)


def test_detects_bull_run_with_tight_base():
    df = _frame([
        (100.0, 101.0, 99.0, 100.0),
        (101.0, 104.0, 100.0, 103.0),
        (103.0, 107.0, 102.0, 106.0),
        (106.0, 111.0, 105.0, 110.0),
        (110.0, 116.0, 109.0, 115.0),
        (115.0, 118.0, 114.5, 117.0),
        (117.0, 118.0, 115.5, 116.5),
        (116.5, 117.8, 115.8, 117.2),
        (117.2, 117.9, 116.2, 117.4),
    ])

    candidate = detect_run_and_tight_base("ABC", "Alpha", df, side="bull")

    assert candidate is not None
    assert candidate["side"] == "bull"
    assert candidate["run_move_pct"] >= 8.0
    assert candidate["base_range_pct"] <= 3.0


def test_detects_bear_run_with_tight_base():
    df = _frame([
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 100.5, 96.0, 97.0),
        (97.0, 97.5, 92.0, 93.0),
        (93.0, 93.5, 88.0, 89.0),
        (89.0, 89.5, 84.0, 85.0),
        (85.0, 85.8, 82.5, 83.5),
        (83.5, 84.6, 82.8, 83.8),
        (83.8, 84.9, 83.1, 84.0),
        (84.0, 84.8, 83.0, 83.7),
    ])

    candidate = detect_run_and_tight_base("XYZ", "Xylon", df, side="bear")

    assert candidate is not None
    assert candidate["side"] == "bear"
    assert candidate["run_move_pct"] >= 8.0
    assert candidate["base_range_pct"] <= 3.0


def test_rejects_loose_base_after_run():
    df = _frame([
        (100.0, 101.0, 99.0, 100.0),
        (101.0, 104.0, 100.0, 103.0),
        (103.0, 107.0, 102.0, 106.0),
        (106.0, 111.0, 105.0, 110.0),
        (110.0, 116.0, 109.0, 115.0),
        (115.0, 118.0, 111.0, 112.5),
        (112.5, 117.0, 110.5, 116.0),
        (116.0, 118.5, 111.5, 112.0),
        (112.0, 118.0, 111.0, 117.0),
    ])

    candidate = detect_run_and_tight_base("ABC", "Alpha", df, side="bull")

    assert candidate is None