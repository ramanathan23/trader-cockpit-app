from src.domain.direction import Direction
from src.signals.exhaustion_reversal import detect_candidate, confirm, ExhaustionCandidate

def _make_history(make_candle, n=20, base=100.0, *, volume=100):
    return [
        make_candle(base, base+0.1, high=base+0.5, low=base-0.5, volume=volume, minute=15+i)
        for i in range(n)
    ]

def test_detect_candidate_returns_none_with_insufficient_history(make_candle):
    history = _make_history(make_candle, n=10)
    assert detect_candidate(make_candle(95.0, 96.0, high=97.0, low=94.0, volume=600), history, day_open=100.0) is None

def test_detect_bullish_candidate_on_selloff_climax(make_candle):
    base = _make_history(make_candle, n=16, volume=100)
    dt = [
        make_candle(99.0, 98.5, high=99.2, low=98.0, volume=100, minute=40),
        make_candle(98.5, 97.5, high=98.8, low=97.0, volume=110, minute=43),
        make_candle(97.5, 96.5, high=97.8, low=96.0, volume=120, minute=46),
        make_candle(96.5, 95.5, high=96.8, low=95.0, volume=130, minute=49),
    ]
    climax = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300, minute=52)
    result = detect_candidate(climax, base + dt, day_open=100.0)
    assert result is not None
    assert result.direction == Direction.BULLISH
    assert result.volume_ratio >= 2.5

def test_detect_candidate_returns_none_when_volume_is_low(make_candle):
    base = _make_history(make_candle, n=16, volume=100)
    dt = [
        make_candle(99.0, 98.5, high=99.2, low=98.0, volume=100, minute=40),
        make_candle(98.5, 97.5, high=98.8, low=97.0, volume=110, minute=43),
        make_candle(97.5, 96.5, high=97.8, low=96.0, volume=120, minute=46),
        make_candle(96.5, 95.5, high=96.8, low=95.0, volume=130, minute=49),
    ]
    assert detect_candidate(make_candle(95.0, 94.5, high=95.5, low=93.0, volume=150, minute=52), base+dt, day_open=100.0) is None

def test_detect_candidate_without_downtrend(make_candle):
    base = _make_history(make_candle, n=16, volume=100)
    flat = [make_candle(100.0, 100.1, high=100.5, low=99.5, volume=100, minute=40+i*3) for i in range(4)]
    assert detect_candidate(make_candle(100.0, 100.2, high=100.5, low=99.0, volume=500, minute=52), base+flat, day_open=100.0) is None

def test_detect_bearish_candidate_on_rally_climax(make_candle):
    base = _make_history(make_candle, n=16, volume=100)
    ut = [
        make_candle(101.0, 101.5, high=102.0, low=100.8, volume=100, minute=40),
        make_candle(101.5, 102.5, high=103.0, low=101.3, volume=110, minute=43),
        make_candle(102.5, 103.5, high=104.0, low=102.3, volume=120, minute=46),
        make_candle(103.5, 104.5, high=105.0, low=103.3, volume=130, minute=49),
    ]
    climax = make_candle(105.0, 105.5, high=107.0, low=104.5, volume=300, minute=52)
    result = detect_candidate(climax, base + ut, day_open=100.0)
    assert result is not None
    assert result.direction == Direction.BEARISH
