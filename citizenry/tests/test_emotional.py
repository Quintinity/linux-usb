"""Tests for emotional state signals."""

import pytest
from citizenry.emotional import EmotionalState, compute_emotional_state


class TestEmotionalState:
    def test_defaults(self):
        e = EmotionalState()
        assert e.fatigue == 0.0
        assert e.confidence == 0.5
        assert e.mood == "steady"

    def test_focused(self):
        e = EmotionalState(fatigue=0.1, confidence=0.9)
        assert e.mood == "focused"

    def test_exhausted(self):
        e = EmotionalState(fatigue=0.8)
        assert e.mood == "exhausted"

    def test_tired(self):
        e = EmotionalState(fatigue=0.5, confidence=0.5)
        assert e.mood == "tired"

    def test_uncertain(self):
        e = EmotionalState(fatigue=0.1, confidence=0.2)
        assert e.mood == "uncertain"

    def test_curious(self):
        e = EmotionalState(fatigue=0.1, confidence=0.5, curiosity=0.7)
        assert e.mood == "curious"

    def test_energized(self):
        e = EmotionalState(fatigue=0.1, confidence=0.6, curiosity=0.1)
        assert e.mood == "energized"

    def test_to_dict(self):
        e = EmotionalState(fatigue=0.333, confidence=0.777)
        d = e.to_dict()
        assert d["fatigue"] == 0.33
        assert d["confidence"] == 0.78

    def test_from_dict(self):
        e = EmotionalState.from_dict({"fatigue": 0.5, "confidence": 0.9, "curiosity": 0.3})
        assert e.fatigue == 0.5
        assert e.confidence == 0.9


class TestComputeEmotionalState:
    def test_fresh_citizen(self):
        e = compute_emotional_state(max_temperature=25, uptime_hours=0.1)
        assert e.fatigue < 0.2
        assert e.curiosity > 0  # New citizen is curious

    def test_hot_citizen(self):
        e = compute_emotional_state(max_temperature=60, uptime_hours=0.5)
        assert e.fatigue > 0.3

    def test_long_running(self):
        e = compute_emotional_state(max_temperature=30, uptime_hours=10)
        assert e.fatigue >= 0.4

    def test_high_confidence(self):
        e = compute_emotional_state(tasks_completed=20, tasks_failed=1)
        assert e.confidence > 0.9

    def test_low_confidence(self):
        e = compute_emotional_state(tasks_completed=2, tasks_failed=8)
        assert e.confidence < 0.3

    def test_no_tasks(self):
        e = compute_emotional_state()
        assert e.confidence == 0.5  # Neutral

    def test_novel_neighbors(self):
        e = compute_emotional_state(novel_neighbors=3)
        assert e.curiosity > 0.3

    def test_warnings_increase_fatigue(self):
        e1 = compute_emotional_state(warning_count=0)
        e2 = compute_emotional_state(warning_count=5)
        assert e2.fatigue > e1.fatigue
