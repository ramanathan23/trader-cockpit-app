from src.domain.models import Direction, DriveStatus
from src.signals.open_drive import evaluate


def test_evaluate_returns_pending_for_empty_history() -> None:
    state = evaluate([], 100.0)

    assert state.status == DriveStatus.PENDING
    assert state.direction == Direction.NEUTRAL
    assert state.confidence == 0.0


def test_evaluate_returns_pending_until_drive_window_is_complete(make_candle) -> None:
    candles = [
        make_candle(100.0, 103.0, high=103.5, low=100.0),
        make_candle(103.0, 105.0, high=105.5, low=103.0, minute=20),
    ]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.PENDING
    assert state.direction == Direction.BULLISH
    assert state.candles_evaluated == 2


def test_evaluate_confirms_a_strong_bullish_drive(make_candle) -> None:
    candles = [
        make_candle(100.0, 103.0, high=103.2, low=100.0),
        make_candle(103.0, 106.0, high=106.2, low=103.0, minute=20),
        make_candle(106.0, 109.0, high=109.2, low=106.0, minute=25),
    ]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.CONFIRMED
    assert state.direction == Direction.BULLISH
    assert state.confidence == 1.0


def test_evaluate_marks_bullish_drive_failed_when_price_breaks_day_open(make_candle) -> None:
    candles = [make_candle(100.0, 103.0, high=103.2, low=99.5)]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.FAILED
    assert state.candles_evaluated == 1


def test_evaluate_returns_no_drive_for_low_conviction_sequence(make_candle) -> None:
    candles = [
        make_candle(100.0, 100.0, high=101.0, low=100.0),
        make_candle(100.0, 100.0, high=101.0, low=100.0, minute=20),
        make_candle(100.0, 100.0, high=101.0, low=100.0, minute=25),
    ]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.NO_DRIVE
    assert state.direction == Direction.BULLISH
    assert state.confidence < 0.5