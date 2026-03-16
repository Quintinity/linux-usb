"""Tests for consciousness stream."""

import pytest
from unittest.mock import MagicMock
from citizenry.consciousness import narrate, narrate_to_report, _TEMPLATES
import citizenry.consciousness as cs


class TestNarrate:
    def setup_method(self):
        cs._last_narration_time = 0  # Reset rate limiter

    def test_idle(self):
        citizen = MagicMock()
        citizen.state = "idle"
        citizen.health = 0.95
        citizen.neighbors = {"a": MagicMock(), "b": MagicMock()}
        citizen.emotional_state.mood = "focused"
        citizen.emotional_state.confidence = 0.8
        citizen.mycelium.active_warnings = []
        citizen.start_time = 1000.0
        text = narrate(citizen)
        assert text is not None
        assert "Idle" in text
        assert "focused" in text

    def test_rate_limited(self):
        citizen = MagicMock()
        citizen.state = "idle"
        citizen.health = 1.0
        citizen.neighbors = {}
        citizen.emotional_state.mood = "steady"
        citizen.emotional_state.confidence = 0.5
        citizen.mycelium.active_warnings = []
        citizen.start_time = 1000.0
        # First call succeeds
        text1 = narrate(citizen)
        assert text1 is not None
        # Second call within 5s is rate-limited
        text2 = narrate(citizen)
        assert text2 is None

    def test_to_report(self):
        cs._last_narration_time = 0
        citizen = MagicMock()
        citizen.state = "idle"
        citizen.name = "arm-1"
        citizen.health = 0.9
        citizen.neighbors = {}
        citizen.emotional_state.mood = "steady"
        citizen.emotional_state.confidence = 0.5
        citizen.mycelium.active_warnings = []
        citizen.start_time = 1000.0
        report = narrate_to_report(citizen)
        assert report is not None
        assert report["type"] == "consciousness"
        assert report["citizen"] == "arm-1"


class TestTemplates:
    def test_all_states_have_templates(self):
        for state in ["idle", "teleop", "executing", "degraded", "emergency_stop", "offline"]:
            assert state in _TEMPLATES
