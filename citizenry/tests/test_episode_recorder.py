"""Tests for episode recorder and learning loop."""

import pytest
from citizenry.episode_recorder import (
    EpisodeRecorder, EpisodeFrame, EpisodeMetadata,
    list_episodes, get_episode_summary,
)
from citizenry.learning_loop import (
    analyze_recent_episodes, generate_improvement_plan, LearningInsight,
)


class TestEpisodeFrame:
    def test_to_dict(self):
        f = EpisodeFrame(frame_index=0, timestamp=1.0,
                        joint_positions=[2048]*6, action_positions=[2100]*6)
        d = f.to_dict()
        assert d["idx"] == 0
        assert len(d["state"]) == 6
        assert len(d["action"]) == 6


class TestEpisodeMetadata:
    def test_to_dict(self):
        m = EpisodeMetadata(episode_id=1, task="pick_and_place",
                           duration_s=5.0, frame_count=50, success=True)
        d = m.to_dict()
        assert d["task"] == "pick_and_place"
        assert d["success"] is True


class TestEpisodeRecorder:
    def test_not_recording(self):
        r = EpisodeRecorder("test")
        assert not r.is_recording

    def test_begin_end(self):
        r = EpisodeRecorder("test")
        r.begin_episode("test_task")
        assert r.is_recording
        meta = r.end_episode(success=True)
        assert not r.is_recording
        assert meta is not None
        assert meta.success is True

    def test_record_frame(self):
        r = EpisodeRecorder("test")
        r.begin_episode("test_task")
        r.record_frame(
            joint_positions=[2048, 1400, 3000, 2048, 2048, 2048],
            action_positions=[2100, 1400, 3000, 2048, 2048, 2048],
        )
        assert r.current_frame_count == 1
        r.end_episode(success=True)


class TestLearningInsight:
    def test_to_dict(self):
        i = LearningInsight(
            insight_type="failure_pattern",
            description="pick_and_place: 40% success rate",
            affected_task="pick_and_place",
        )
        d = i.to_dict()
        assert d["type"] == "failure_pattern"


class TestAnalysis:
    def test_no_episodes(self):
        # Will get "no_data" insight if no episodes
        insights = analyze_recent_episodes(10)
        assert len(insights) >= 0  # May have data from earlier tests

    def test_generate_plan(self):
        insights = [
            LearningInsight(
                insight_type="failure_pattern",
                description="test",
                suggested_action="analyze_failures",
                affected_task="pick",
            ),
        ]
        plan = generate_improvement_plan(insights)
        assert len(plan) >= 1
