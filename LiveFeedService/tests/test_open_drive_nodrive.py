from src.domain.direction import Direction
from src.domain.drive_status import DriveStatus
from src.signals.open_drive import evaluate

def test_evaluate_returns_no_drive_for_doji_first_candle(make_candle):
    state = evaluate([make_candle(100.0, 100.0, high=101.0, low=99.0)], 100.0, drive_candles=3)
    assert state.status == DriveStatus.NO_DRIVE
    assert state.direction == Direction.NEUTRAL

def test_evaluate_returns_no_drive_for_low_conviction_sequence(make_candle):
    candles = [
        make_candle(100.0, 100.1, high=102.0, low=100.0, volume=100),
        make_candle(100.1, 100.05, high=102.0, low=100.0, minute=20, volume=50),
        make_candle(100.05, 100.02, high=102.0, low=100.0, minute=25, volume=30),
    ]
    state = evaluate(candles, 100.0, drive_candles=3)
    assert state.status == DriveStatus.NO_DRIVE
    assert state.confidence < 0.5

def test_evaluate_confirms_bearish_drive(make_candle):
    candles = [
        make_candle(100.0, 97.0, high=100.0, low=96.8, volume=1000),
        make_candle(97.0, 94.0, high=97.0, low=93.8, minute=20, volume=1100),
        make_candle(94.0, 91.0, high=94.0, low=90.8, minute=25, volume=1200),
    ]
    state = evaluate(candles, 100.0, drive_candles=3)
    assert state.status == DriveStatus.CONFIRMED
    assert state.direction == Direction.BEARISH
    assert state.confidence == 1.0

def test_volume_scoring_rewards_rising_volume(make_candle):
    rising = [
        make_candle(100.0, 103.0, high=103.2, low=100.0, volume=1000),
        make_candle(103.0, 106.0, high=106.2, low=103.0, minute=20, volume=1500),
        make_candle(106.0, 109.0, high=109.2, low=106.0, minute=25, volume=2000),
    ]
    declining = [
        make_candle(100.0, 103.0, high=103.2, low=100.0, volume=2000),
        make_candle(103.0, 106.0, high=106.2, low=103.0, minute=20, volume=1000),
        make_candle(106.0, 109.0, high=109.2, low=106.0, minute=25, volume=500),
    ]
    assert evaluate(rising, 100.0, drive_candles=3).confidence >= evaluate(declining, 100.0, drive_candles=3).confidence
