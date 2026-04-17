from src.domain.direction import Direction
from src.domain.drive_status import DriveStatus
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
        make_candle(100.0, 103.0, high=103.2, low=100.0, volume=1000),
        make_candle(103.0, 106.0, high=106.2, low=103.0, minute=20, volume=1100),
        make_candle(106.0, 109.0, high=109.2, low=106.0, minute=25, volume=1200),
    ]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.CONFIRMED
    assert state.direction == Direction.BULLISH
    assert state.confidence == 1.0


def test_evaluate_marks_bullish_drive_failed_when_close_breaks_day_open(make_candle) -> None:
    """Invalidation is now close-based, not wick-based."""
    candles = [
        make_candle(100.0, 103.0, high=103.5, low=100.0, volume=1000),
        make_candle(103.0, 99.0, high=103.2, low=98.5, minute=20, volume=1100),
    ]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.FAILED
    assert state.candles_evaluated == 2


def test_evaluate_tolerates_wick_through_day_open(make_candle) -> None:
    """A wick below day_open that closes above it should NOT fail the drive."""
    candles = [
        make_candle(100.0, 103.0, high=103.2, low=99.5, volume=1000),
        make_candle(103.0, 106.0, high=106.2, low=103.0, minute=20, volume=1100),
        make_candle(106.0, 109.0, high=109.2, low=106.0, minute=25, volume=1200),
    ]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.CONFIRMED
    assert state.direction == Direction.BULLISH


def test_evaluate_returns_no_drive_for_doji_first_candle(make_candle) -> None:
    """A doji first candle means no directional conviction — immediate NO_DRIVE."""
    candles = [
        make_candle(100.0, 100.0, high=101.0, low=99.0),
    ]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.NO_DRIVE
    assert state.direction == Direction.NEUTRAL


def test_evaluate_returns_no_drive_for_low_conviction_sequence(make_candle) -> None:
    candles = [
        make_candle(100.0, 100.1, high=102.0, low=100.0, volume=100),
        make_candle(100.1, 100.05, high=102.0, low=100.0, minute=20, volume=50),
        make_candle(100.05, 100.02, high=102.0, low=100.0, minute=25, volume=30),
    ]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.NO_DRIVE
    assert state.direction == Direction.BULLISH
    assert state.confidence < 0.5


def test_evaluate_confirms_bearish_drive(make_candle) -> None:
    candles = [
        make_candle(100.0, 97.0, high=100.0, low=96.8, volume=1000),
        make_candle(97.0, 94.0, high=97.0, low=93.8, minute=20, volume=1100),
        make_candle(94.0, 91.0, high=94.0, low=90.8, minute=25, volume=1200),
    ]

    state = evaluate(candles, 100.0, drive_candles=3)

    assert state.status == DriveStatus.CONFIRMED
    assert state.direction == Direction.BEARISH
    assert state.confidence == 1.0


def test_volume_scoring_rewards_rising_volume(make_candle) -> None:
    """Candles with rising volume should score higher than declining volume."""
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

    rising_state = evaluate(rising, 100.0, drive_candles=3)
    declining_state = evaluate(declining, 100.0, drive_candles=3)

    assert rising_state.confidence >= declining_state.confidence