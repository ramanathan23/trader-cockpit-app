from src.domain.direction import Direction
from src.signals.exhaustion_reversal import detect_candidate, confirm, ExhaustionCandidate

def _make_history(make_candle, n=20, base=100.0, *, volume=100):
    return [
        make_candle(base, base+0.1, high=base+0.5, low=base-0.5, volume=volume, minute=15+i)
        for i in range(n)
    ]

def test_confirm_bullish_passes_when_low_holds_and_close_recovers(make_candle):
    climax    = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300)
    candidate = ExhaustionCandidate(climax=climax, direction=Direction.BULLISH, volume_ratio=3.0, downtrend_len=3)
    conf      = make_candle(94.5, 95.5, high=96.0, low=93.5, volume=200, minute=20)
    result    = confirm(conf, candidate)
    assert result is not None
    assert result.direction == Direction.BULLISH
    assert result.climax == climax
    assert result.confirmation == conf

def test_confirm_bullish_fails_when_new_low_printed(make_candle):
    climax    = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300)
    candidate = ExhaustionCandidate(climax=climax, direction=Direction.BULLISH, volume_ratio=3.0, downtrend_len=3)
    assert confirm(make_candle(94.5, 95.0, high=95.5, low=92.5, volume=200, minute=20), candidate) is None

def test_confirm_bullish_fails_when_close_does_not_recover(make_candle):
    climax    = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300)
    candidate = ExhaustionCandidate(climax=climax, direction=Direction.BULLISH, volume_ratio=3.0, downtrend_len=3)
    assert confirm(make_candle(94.0, 94.0, high=94.5, low=93.5, volume=200, minute=20), candidate) is None

def test_detect_candidate_works_without_day_open(make_candle):
    base = _make_history(make_candle, n=16, volume=100)
    dt = [
        make_candle(99.0, 98.5, high=99.2, low=98.0, volume=100, minute=40),
        make_candle(98.5, 97.5, high=98.8, low=97.0, volume=110, minute=43),
        make_candle(97.5, 96.5, high=97.8, low=96.0, volume=120, minute=46),
        make_candle(96.5, 95.5, high=96.8, low=95.0, volume=130, minute=49),
    ]
    climax = make_candle(95.0, 94.5, high=95.5, low=93.0, volume=300, minute=52)
    result = detect_candidate(climax, base + dt, day_open=None)
    assert result is not None
    assert result.direction == Direction.BULLISH
