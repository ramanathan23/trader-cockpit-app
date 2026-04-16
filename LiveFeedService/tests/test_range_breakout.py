from src.domain.signal_type import SignalType
from src.signals.range_breakout import detect


def test_detect_returns_none_without_enough_history(make_candle) -> None:
    candle = make_candle(100.0, 102.0, high=102.2, low=99.9, volume=200)

    assert detect(candle, [], lookback=5) is None


def test_detect_rejects_wide_ranges(make_candle) -> None:
    history = [
        make_candle(100.0, 100.0, high=105.0, low=95.0, volume=100, minute=15 + idx * 5)
        for idx in range(5)
    ]
    candle = make_candle(100.0, 106.0, high=106.0, low=99.0, volume=500, minute=45)

    assert detect(candle, history, lookback=5, max_range_pct=0.02) is None


def test_detect_returns_breakout_when_close_exits_tight_rectangle(make_candle) -> None:
    history = [
        make_candle(100.0, 100.2, high=100.5, low=99.8, volume=100, minute=15 + idx * 5)
        for idx in range(5)
    ]
    candle = make_candle(100.1, 101.0, high=101.2, low=100.0, volume=200, minute=45)

    assert detect(candle, history, lookback=5, min_vol_ratio=1.5) == SignalType.RANGE_BREAKOUT


def test_detect_returns_breakdown_when_close_leaves_rectangle_lower(make_candle) -> None:
    history = [
        make_candle(100.0, 100.2, high=100.5, low=99.8, volume=100, minute=15 + idx * 5)
        for idx in range(5)
    ]
    candle = make_candle(100.0, 99.0, high=100.0, low=98.8, volume=200, minute=45)

    assert detect(candle, history, lookback=5, min_vol_ratio=1.5) == SignalType.RANGE_BREAKDOWN