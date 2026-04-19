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

class TestEngineReset:
    def test_reset_clears_state(self):
        from src.signals.engine import SignalEngine
        builder = MagicMock(); builder.get_history.return_value = []
        engine = SignalEngine("TEST", builder, MagicMock(spec=SessionManager))
        engine._state.day_open = 100.0
        engine._state.drive_signalled = True
        engine._state.orb_high = 101.0
        engine.reset()
        assert engine._state.day_open is None
        assert engine._state.drive_signalled is False
        assert engine._state.orb_high is None
