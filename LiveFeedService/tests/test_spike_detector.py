from src.domain.direction import Direction
from src.domain.spike_type import SpikeType
from src.signals.spike_detector import evaluate, is_volume_dry_up


def build_history(make_candle):
    return [
        make_candle(100.0, 100.0 + idx * 0.1, high=100.5, low=99.5, volume=100, minute=15 + idx * 5)
        for idx in range(5)
    ]


def test_evaluate_requires_minimum_history(make_candle) -> None:
    candle = make_candle(100.0, 103.0, high=104.0, low=99.0, volume=500)

    assert evaluate(candle, []) is None


def test_evaluate_detects_breakout_shock(make_candle) -> None:
    history = build_history(make_candle)
    candle = make_candle(100.0, 103.0, high=103.5, low=99.9, volume=500, minute=45)

    state = evaluate(candle, history, vol_spike_ratio=3.0, price_shock_pct=1.5)

    assert state is not None
    assert state.spike_type == SpikeType.BREAKOUT_SHOCK
    assert state.direction == Direction.BULLISH


def test_evaluate_detects_absorption_and_flips_direction(make_candle) -> None:
    history = build_history(make_candle)
    candle = make_candle(100.0, 100.2, high=100.5, low=99.8, volume=500, minute=45)

    state = evaluate(candle, history, vol_spike_ratio=3.0, price_shock_pct=1.5)

    assert state is not None
    assert state.spike_type == SpikeType.ABSORPTION
    assert state.direction == Direction.BEARISH


def test_evaluate_detects_weak_shock_without_volume_confirmation(make_candle) -> None:
    history = build_history(make_candle)
    candle = make_candle(100.0, 103.0, high=103.2, low=99.8, volume=120, minute=45)

    state = evaluate(candle, history, vol_spike_ratio=3.0, price_shock_pct=1.5)

    assert state is not None
    assert state.spike_type == SpikeType.WEAK_SHOCK


def test_is_volume_dry_up_uses_median_baseline(make_candle) -> None:
    history = build_history(make_candle)
    candle = make_candle(100.0, 100.1, high=100.2, low=99.9, volume=10, minute=45)

    assert is_volume_dry_up(candle, history) is True