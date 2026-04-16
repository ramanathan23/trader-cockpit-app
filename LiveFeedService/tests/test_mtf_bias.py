from src.core.mtf_bias import compute
from src.domain.direction import Direction


def test_compute_returns_neutral_when_history_is_too_short(make_candle) -> None:
    history = [make_candle(100.0, 101.0)]

    bias = compute(history, candles_15m=3, candles_1h=4)

    assert bias.bias_15m == Direction.NEUTRAL
    assert bias.bias_1h == Direction.NEUTRAL


def test_compute_returns_bullish_bias_for_rising_window(make_candle) -> None:
    history = [
        make_candle(100.0 + idx, 101.0 + idx, minute=15 + idx * 5)
        for idx in range(4)
    ]

    bias = compute(history, candles_15m=3, candles_1h=4, min_move_pct=0.05)

    assert bias.bias_15m == Direction.BULLISH
    assert bias.bias_1h == Direction.BULLISH


def test_compute_returns_bearish_bias_for_falling_window(make_candle) -> None:
    history = [
        make_candle(105.0 - idx, 104.0 - idx, minute=15 + idx * 5)
        for idx in range(4)
    ]

    bias = compute(history, candles_15m=3, candles_1h=4, min_move_pct=0.05)

    assert bias.bias_15m == Direction.BEARISH
    assert bias.bias_1h == Direction.BEARISH


def test_compute_keeps_small_moves_neutral(make_candle) -> None:
    history = [
        make_candle(100.0, 100.02 + idx * 0.01, minute=15 + idx * 5)
        for idx in range(4)
    ]

    bias = compute(history, candles_15m=3, candles_1h=4, min_move_pct=0.2)

    assert bias.bias_15m == Direction.NEUTRAL
    assert bias.bias_1h == Direction.NEUTRAL