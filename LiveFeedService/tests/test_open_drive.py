from src.domain.direction import Direction
from src.domain.drive_status import DriveStatus
from src.signals.open_drive import evaluate

def test_evaluate_returns_pending_for_empty_history():
    state = evaluate([], 100.0)
    assert state.status == DriveStatus.PENDING
    assert state.direction == Direction.NEUTRAL
    assert state.confidence == 0.0

def test_evaluate_returns_pending_until_drive_window_is_complete(make_candle):
    candles = [
        make_candle(100.0, 103.0, high=103.5, low=100.0),
        make_candle(103.0, 105.0, high=105.5, low=103.0, minute=20),
    ]
    state = evaluate(candles, 100.0, drive_candles=3)
    assert state.status == DriveStatus.PENDING
    assert state.direction == Direction.BULLISH
    assert state.candles_evaluated == 2

def test_evaluate_confirms_a_strong_bullish_drive(make_candle):
    candles = [
        make_candle(100.0, 103.0, high=103.2, low=100.0, volume=1000),
        make_candle(103.0, 106.0, high=106.2, low=103.0, minute=20, volume=1100),
        make_candle(106.0, 109.0, high=109.2, low=106.0, minute=25, volume=1200),
    ]
    state = evaluate(candles, 100.0, drive_candles=3)
    assert state.status == DriveStatus.CONFIRMED
    assert state.direction == Direction.BULLISH
    assert state.confidence == 1.0

def test_evaluate_marks_bullish_drive_failed_when_close_breaks_day_open(make_candle):
    candles = [
        make_candle(100.0, 103.0, high=103.5, low=100.0, volume=1000),
        make_candle(103.0, 99.0, high=103.2, low=98.5, minute=20, volume=1100),
    ]
    state = evaluate(candles, 100.0, drive_candles=3)
    assert state.status == DriveStatus.FAILED

def test_evaluate_tolerates_wick_through_day_open(make_candle):
    candles = [
        make_candle(100.0, 103.0, high=103.2, low=99.5, volume=1000),
        make_candle(103.0, 106.0, high=106.2, low=103.0, minute=20, volume=1100),
        make_candle(106.0, 109.0, high=109.2, low=106.0, minute=25, volume=1200),
    ]
    state = evaluate(candles, 100.0, drive_candles=3)
    assert state.status == DriveStatus.CONFIRMED
    assert state.direction == Direction.BULLISH
