"""
Regression tests for signal detection edge cases.

Covers:
  - Frozen Signal immutability
  - Engine reset clears state
  - Confluence filter blocks opposing signals
  - Confluence exempt types pass through
"""

import dataclasses as dc
from datetime import datetime, timezone
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from src.domain.candle import Candle
from src.domain.direction import Direction
from src.domain.index_bias import IndexBias
from src.domain.signal import Signal
from src.domain.signal_type import SignalType
from src.domain.strength import Strength
from src.core.session_manager import SessionManager
from src.domain.session_phase import SessionPhase

IST = ZoneInfo("Asia/Kolkata")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_signal(
    direction: Direction = Direction.BULLISH,
    signal_type: SignalType = SignalType.OPEN_DRIVE_ENTRY,
    strength: Strength = Strength.MEDIUM,
    score: float = 5.0,
) -> Signal:
    return Signal(
        symbol="TEST",
        signal_type=signal_type,
        direction=direction,
        strength=strength,
        score=score,
        price=100.0,
        session_phase=SessionPhase.EXECUTION,
    )


# ── Test: Frozen Signal ───────────────────────────────────────────────────────

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


# ── Test: MTF Confluence filter ───────────────────────────────────────────────

class TestConfluenceFilter:

    def test_opposing_15m_blocks_signal(self, make_candle):
        from src.core import mtf_bias
        bias = mtf_bias.MTFBias(
            bias_15m=Direction.BEARISH,
            bias_1h=Direction.NEUTRAL,
        )
        sig = _make_signal(
            direction=Direction.BULLISH,
            signal_type=SignalType.ORB_BREAKOUT,
        )
        from src.signals.engine import SignalEngine
        builder = MagicMock()
        builder.get_history.return_value = []
        session = MagicMock(spec=SessionManager)

        engine = SignalEngine("TEST", builder, session)
        result = engine._apply_confluence([sig], bias)
        assert len(result) == 0

    def test_aligned_15m_and_1h_upgrades_strength(self, make_candle):
        from src.core import mtf_bias
        bias = mtf_bias.MTFBias(
            bias_15m=Direction.BULLISH,
            bias_1h=Direction.BULLISH,
        )
        sig = _make_signal(
            direction=Direction.BULLISH,
            signal_type=SignalType.ORB_BREAKOUT,
            strength=Strength.MEDIUM,
        )
        from src.signals.engine import SignalEngine
        builder = MagicMock()
        builder.get_history.return_value = []
        session = MagicMock(spec=SessionManager)

        engine = SignalEngine("TEST", builder, session)
        result = engine._apply_confluence([sig], bias)
        assert len(result) == 1
        assert result[0].strength == Strength.HIGH

    def test_exempt_types_pass_through(self, make_candle):
        from src.core import mtf_bias
        bias = mtf_bias.MTFBias(
            bias_15m=Direction.BEARISH,
            bias_1h=Direction.BEARISH,
        )
        sig = _make_signal(
            direction=Direction.BULLISH,
            signal_type=SignalType.TRAIL_UPDATE,  # exempt
        )
        from src.signals.engine import SignalEngine
        builder = MagicMock()
        builder.get_history.return_value = []
        session = MagicMock(spec=SessionManager)

        engine = SignalEngine("TEST", builder, session)
        result = engine._apply_confluence([sig], bias)
        assert len(result) == 1


# ── Test: Engine reset ────────────────────────────────────────────────────────

class TestEngineReset:

    def test_reset_clears_state(self):
        from src.signals.engine import SignalEngine
        builder = MagicMock()
        builder.get_history.return_value = []
        session = MagicMock(spec=SessionManager)

        engine = SignalEngine("TEST", builder, session)
        engine._state.day_open = 100.0
        engine._state.drive_signalled = True
        engine._state.orb_high = 101.0

        engine.reset()

        assert engine._state.day_open is None
        assert engine._state.drive_signalled is False
        assert engine._state.orb_high is None
