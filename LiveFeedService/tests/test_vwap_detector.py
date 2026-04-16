from src.domain.enums import SignalType
from src.signals.vwap_detector import VwapState, detect_cross, update


def test_update_accumulates_vwap_and_side_count(make_candle) -> None:
    state = VwapState()

    state = update(state, make_candle(100.0, 101.0, high=101.0, low=99.0, volume=100))
    state = update(state, make_candle(101.0, 102.0, high=102.0, low=100.0, volume=100, minute=20))

    assert state.vwap is not None
    assert state.last_side == 1
    assert state.side_count >= 1


def test_detect_cross_requires_hysteresis(make_candle) -> None:
    state = VwapState(cum_tp_vol=10_000.0, cum_vol=100.0, last_side=-1, side_count=1, signalled=0)
    candle = make_candle(99.0, 102.0, high=102.0, low=98.5, volume=150)
    history = [make_candle(100.0, 99.0, high=100.2, low=98.8, volume=100, minute=15 + idx * 5) for idx in range(5)]

    assert detect_cross(candle, state, history, hysteresis_min=2) is None


def test_detect_cross_returns_breakout_after_valid_volume_confirmed_cross(make_candle) -> None:
    state = VwapState(cum_tp_vol=10_000.0, cum_vol=100.0, last_side=-1, side_count=3, signalled=0)
    candle = make_candle(99.0, 102.0, high=102.0, low=98.5, volume=150)
    history = [make_candle(100.0, 99.0, high=100.2, low=98.8, volume=100, minute=15 + idx * 5) for idx in range(5)]

    assert detect_cross(candle, state, history, min_vol_ratio=1.3) == SignalType.VWAP_BREAKOUT


def test_detect_cross_does_not_refire_same_direction(make_candle) -> None:
    state = VwapState(cum_tp_vol=10_000.0, cum_vol=100.0, last_side=-1, side_count=3, signalled=1)
    candle = make_candle(99.0, 102.0, high=102.0, low=98.5, volume=150)
    history = [make_candle(100.0, 99.0, high=100.2, low=98.8, volume=100, minute=15 + idx * 5) for idx in range(5)]

    assert detect_cross(candle, state, history, min_vol_ratio=1.3) is None