import dataclasses as dc
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo
import pytest
from src.domain.direction import Direction
from src.domain.signal import Signal
from src.domain.signal_type import SignalType
from src.domain.strength import Strength
from src.core.session_manager import SessionManager
from src.domain.session_phase import SessionPhase

IST = ZoneInfo("Asia/Kolkata")

def _make_signal(direction=Direction.BULLISH, signal_type=SignalType.OPEN_DRIVE_ENTRY,
                 strength=Strength.MEDIUM, score=5.0):
    return Signal(symbol="TEST", signal_type=signal_type, direction=direction,
                  strength=strength, score=score, price=100.0, session_phase=SessionPhase.EXECUTION)

class TestFrozenSignal:
    def test_signal_is_immutable(self):
        sig = _make_signal()
        with pytest.raises(dc.FrozenInstanceError):
            sig.score = 10.0

    def test_signal_replace_creates_new_instance(self):
        sig = _make_signal(score=7.5)
        new_sig = dc.replace(sig, score=10.0)
        assert new_sig.score == 10.0
        assert sig.score == 7.5
        assert new_sig is not sig


class TestConfluenceFilter:
    def test_opposing_15m_blocks_signal(self, make_candle):
        from src.core import mtf_bias
        from src.signals.engine import SignalEngine
        bias = mtf_bias.MTFBias(bias_15m=Direction.BEARISH, bias_1h=Direction.NEUTRAL)
        sig  = _make_signal(direction=Direction.BULLISH, signal_type=SignalType.ORB_BREAKOUT)
        builder = MagicMock(); builder.get_history.return_value = []
        engine = SignalEngine("TEST", builder, MagicMock(spec=SessionManager))
        assert len(engine._apply_confluence([sig], bias)) == 0

    def test_aligned_15m_and_1h_upgrades_strength(self, make_candle):
        from src.core import mtf_bias
        from src.signals.engine import SignalEngine
        bias = mtf_bias.MTFBias(bias_15m=Direction.BULLISH, bias_1h=Direction.BULLISH)
        sig  = _make_signal(direction=Direction.BULLISH, signal_type=SignalType.ORB_BREAKOUT, strength=Strength.MEDIUM)
        builder = MagicMock(); builder.get_history.return_value = []
        result = SignalEngine("TEST", builder, MagicMock(spec=SessionManager))._apply_confluence([sig], bias)
        assert len(result) == 1
        assert result[0].strength == Strength.HIGH

    def test_exempt_types_pass_through(self, make_candle):
        from src.core import mtf_bias
        from src.signals.engine import SignalEngine
        bias = mtf_bias.MTFBias(bias_15m=Direction.BEARISH, bias_1h=Direction.BEARISH)
        sig  = _make_signal(direction=Direction.BULLISH, signal_type=SignalType.TRAIL_UPDATE)
        builder = MagicMock(); builder.get_history.return_value = []
        assert len(SignalEngine("TEST", builder, MagicMock(spec=SessionManager))._apply_confluence([sig], bias)) == 1
