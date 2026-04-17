from src.domain.direction import Direction
from src.signals.exhaustion_reversal import (
    detect_candidate,
    confirm,
    ExhaustionCandidate,
)


def _make_history(make_candle, n=20, base=100.0, *, volume=100):
    """Create n flat candles as baseline history."""
    return [
        make_candle(base, base + 0.1, high=base + 0.5, low=base - 0.5,
                    volume=volume, minute=15 + i)
        for i in range(n)
    ]


def test_detect_candidate_returns_none_with_insufficient_history(make_candle) -> None:
    history = _make_history(make_candle, n=10)
    candle = make_candle(95.0, 96.0, high=97.0, low=94.0, volume=600)

    result = detect_candidate(candle, history, day_open=100.0)

    assert result is None


def test_detect_bullish_candidate_on_selloff_climax(make_candle) -> None:
    """Falling lows + volume climax + close in upper portion → bullish candidate."""
    base_history = _make_history(make_candle, n=16, volume=100)
    # 4 candles with falling lows (downtrend)
    downtrend = [
        make_candle(99.0, 98.5, high=99.2, low=98.0, volume=100, minute=40),
        make_candle(98.5, 97.5, high=98.8, low=97.0, volume=110, minute=43),
        make_candle(97.5, 96.5, high=97.8, low=96.0, volume=120, minute=46),
        make_candle(96.5, 95.5, high=96.8, low=95.0, volume=130, minute=49),
    ]
    history = base_history + downtrend

    # Climax candle: high volume, close in upper 60% of its range
    climax = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300, minute=52)
    # close=94.5, range=95.5-93.0=2.5, upper_40=93.0+1.0=94.0 → 94.5 >= 94.0 ✓

    result = detect_candidate(climax, history, day_open=100.0)

    assert result is not None
    assert result.direction == Direction.BULLISH
    assert result.volume_ratio >= 2.5


def test_detect_candidate_returns_none_when_volume_is_low(make_candle) -> None:
    """Volume below threshold → no candidate."""
    base_history = _make_history(make_candle, n=16, volume=100)
    downtrend = [
        make_candle(99.0, 98.5, high=99.2, low=98.0, volume=100, minute=40),
        make_candle(98.5, 97.5, high=98.8, low=97.0, volume=110, minute=43),
        make_candle(97.5, 96.5, high=97.8, low=96.0, volume=120, minute=46),
        make_candle(96.5, 95.5, high=96.8, low=95.0, volume=130, minute=49),
    ]
    history = base_history + downtrend

    # Low volume candle — not a climax
    candle = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=150, minute=52)

    result = detect_candidate(candle, history, day_open=100.0)

    assert result is None


def test_detect_candidate_without_downtrend(make_candle) -> None:
    """No falling lows → no bullish candidate."""
    base_history = _make_history(make_candle, n=16, volume=100)
    # Flat candles (no lower lows)
    flat = [
        make_candle(100.0, 100.1, high=100.5, low=99.5, volume=100, minute=40),
        make_candle(100.0, 100.1, high=100.5, low=99.5, volume=100, minute=43),
        make_candle(100.0, 100.1, high=100.5, low=99.5, volume=100, minute=46),
        make_candle(100.0, 100.1, high=100.5, low=99.5, volume=100, minute=49),
    ]
    history = base_history + flat

    # High volume but no preceding trend
    candle = make_candle(100.0, 100.2, high=100.5, low=99.0, volume=500, minute=52)

    result = detect_candidate(candle, history, day_open=100.0)

    assert result is None


def test_detect_bearish_candidate_on_rally_climax(make_candle) -> None:
    """Rising highs + volume climax + close in lower portion → bearish candidate."""
    base_history = _make_history(make_candle, n=16, volume=100)
    uptrend = [
        make_candle(101.0, 101.5, high=102.0, low=100.8, volume=100, minute=40),
        make_candle(101.5, 102.5, high=103.0, low=101.3, volume=110, minute=43),
        make_candle(102.5, 103.5, high=104.0, low=102.3, volume=120, minute=46),
        make_candle(103.5, 104.5, high=105.0, low=103.3, volume=130, minute=49),
    ]
    history = base_history + uptrend

    # Climax candle: high volume, close in lower 60% of its range
    climax = make_candle(105.0, 105.5, high=107.0, low=104.5, volume=300, minute=52)
    # close=105.5, range=107.0-104.5=2.5, lower_60=104.5+1.5=106.0 → 105.5 <= 106.0 ✓

    result = detect_candidate(climax, history, day_open=100.0)

    assert result is not None
    assert result.direction == Direction.BEARISH


def test_confirm_bullish_passes_when_low_holds_and_close_recovers(make_candle) -> None:
    climax = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300)
    candidate = ExhaustionCandidate(
        climax=climax, direction=Direction.BULLISH, volume_ratio=3.0, downtrend_len=3,
    )

    # Confirmation candle: low held (>= 93.0), close recovered (> 94.5)
    confirmation = make_candle(94.5, 95.5, high=96.0, low=93.5, volume=200, minute=20)

    result = confirm(confirmation, candidate)

    assert result is not None
    assert result.direction == Direction.BULLISH
    assert result.climax == climax
    assert result.confirmation == confirmation


def test_confirm_bullish_fails_when_new_low_printed(make_candle) -> None:
    climax = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300)
    candidate = ExhaustionCandidate(
        climax=climax, direction=Direction.BULLISH, volume_ratio=3.0, downtrend_len=3,
    )

    # Confirmation candle prints a new low (92.5 < 93.0) → sellers still in control
    confirmation = make_candle(94.5, 95.0, high=95.5, low=92.5, volume=200, minute=20)

    result = confirm(confirmation, candidate)

    assert result is None


def test_confirm_bullish_fails_when_close_does_not_recover(make_candle) -> None:
    climax = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300)
    candidate = ExhaustionCandidate(
        climax=climax, direction=Direction.BULLISH, volume_ratio=3.0, downtrend_len=3,
    )

    # Low held but close didn't recover above climax close
    confirmation = make_candle(94.0, 94.0, high=94.5, low=93.5, volume=200, minute=20)

    result = confirm(confirmation, candidate)

    assert result is None


def test_detect_candidate_works_without_day_open(make_candle) -> None:
    """day_open=None should not prevent detection."""
    base_history = _make_history(make_candle, n=16, volume=100)
    downtrend = [
        make_candle(99.0, 98.5, high=99.2, low=98.0, volume=100, minute=40),
        make_candle(98.5, 97.5, high=98.8, low=97.0, volume=110, minute=43),
        make_candle(97.5, 96.5, high=97.8, low=96.0, volume=120, minute=46),
        make_candle(96.5, 95.5, high=96.8, low=95.0, volume=130, minute=49),
    ]
    history = base_history + downtrend

    climax = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300, minute=52)

    result = detect_candidate(climax, history, day_open=None)

    assert result is not None
    assert result.direction == Direction.BULLISH
