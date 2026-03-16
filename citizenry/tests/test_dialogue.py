"""Tests for citizen dialogue system."""

import pytest
from unittest.mock import MagicMock
from citizenry.dialogue import (
    CitizenVoice, CitizenNeeds, DialogueMessage,
    parse_question, compose_response,
)
from citizenry.emotional import EmotionalState


class TestParseQuestion:
    def test_how_are_you(self):
        assert parse_question("how are you") == "how_are_you"
        assert parse_question("How are you doing?") == "how_are_you"
        assert parse_question("status") == "how_are_you"

    def test_memory(self):
        assert parse_question("what do you remember about blocks") == "what_do_you_remember"
        assert parse_question("do you recall the red block") == "what_do_you_remember"

    def test_pain(self):
        assert parse_question("does anything hurt") == "what_hurts"
        assert parse_question("are you damaged") == "what_hurts"

    def test_goals(self):
        assert parse_question("what are your goals") == "what_are_your_goals"
        assert parse_question("what do you want") == "what_are_your_goals"

    def test_growth(self):
        assert parse_question("what growth stage are you") == "growth_status"

    def test_sleep(self):
        assert parse_question("are you tired") == "sleep_status"

    def test_default(self):
        assert parse_question("banana") == "how_are_you"


class TestCitizenVoice:
    def _make_citizen(self):
        c = MagicMock()
        c.name = "arm-1"
        c.emotional_state = EmotionalState(fatigue=0.3, confidence=0.8)
        c.growth_tracker.get_stage.return_value = MagicMock(name="JUVENILE")
        c.growth_tracker.get_stage.return_value.name = "JUVENILE"
        c.growth_tracker.maturation.total_tasks = 50
        c.growth_tracker.maturation.success_rate = 0.75
        c.pain_memory.active_zones.return_value = 2
        c.pain_memory.total_pain_events.return_value = 5
        c.pain_memory.sensitivity = 1.0
        c.pain_memory.events = []
        c.performance.records = {}
        c.metabolism_tracker.state.brownout_stage.value = "normal"
        c.memory.stats.return_value = {"episodes": 10, "facts": 5, "procedures": 3, "unconsolidated": 2}
        c.memory.unconsolidated_count.return_value = 2
        c.sleep_engine.last_sleep_time = 1000.0
        c.soul.personality.neuroticism = 0.5
        c.soul.personality.exploration_drive = 0.5
        c.start_time = 1000.0
        return c

    def test_how_are_you(self):
        c = self._make_citizen()
        voice = CitizenVoice(c)
        response = voice.how_are_you()
        assert len(response) > 0
        assert isinstance(response, str)

    def test_what_hurts_no_pain(self):
        c = self._make_citizen()
        c.pain_memory.total_pain_events.return_value = 0
        voice = CitizenVoice(c)
        assert "Nothing hurts" in voice.what_hurts()

    def test_what_hurts_with_pain(self):
        c = self._make_citizen()
        voice = CitizenVoice(c)
        response = voice.what_hurts()
        assert "pain events" in response

    def test_goals(self):
        c = self._make_citizen()
        c.soul.goals.get_active.return_value = [
            MagicMock(description="Protect hardware", priority=0),
            MagicMock(description="Complete tasks", priority=2),
        ]
        voice = CitizenVoice(c)
        response = voice.what_are_your_goals()
        assert "Protect hardware" in response


class TestDialogueMessage:
    def test_to_body(self):
        msg = DialogueMessage(sender="arm-1", recipient="governor", text="I'm tired")
        body = msg.to_body()
        assert body["task"] == "dialogue"
        assert body["text"] == "I'm tired"

    def test_to_report_body(self):
        msg = DialogueMessage(sender="arm-1", recipient="governor", text="help")
        body = msg.to_report_body()
        assert body["type"] == "dialogue_response"


class TestCitizenNeeds:
    def test_no_needs(self):
        c = MagicMock()
        c.name = "arm-1"
        c.start_time = 0
        c.emotional_state = EmotionalState(fatigue=0.1)
        c.sleep_engine.compute_pressure.return_value = MagicMock(should_sleep=False, pressure=0.2)
        c.memory.unconsolidated_count.return_value = 2
        c.performance.records = {}
        c.metabolism_tracker.state.brownout_stage.value = "normal"
        import time
        c.sleep_engine.last_sleep_time = time.time()  # Just slept

        needs = CitizenNeeds(c)
        assert needs.check_needs() is None
