"""Tests for capability composition discovery."""

import pytest
from citizenry.composition import (
    CompositionRule, CompositionEngine, DEFAULT_RULES,
)


class TestCompositionRule:
    def test_matches(self):
        rule = CompositionRule(
            required_capabilities=["6dof_arm", "video_stream"],
            composite_capability="visual_pick_and_place",
        )
        assert rule.matches({"6dof_arm", "video_stream", "gripper"})
        assert not rule.matches({"6dof_arm", "gripper"})


class TestCompositionEngine:
    def test_no_citizens(self):
        engine = CompositionEngine()
        caps = engine.discover_capabilities({})
        assert caps == []

    def test_single_arm_no_composition(self):
        engine = CompositionEngine()
        caps = engine.discover_capabilities({
            "arm1": ["6dof_arm", "gripper"],
        })
        assert caps == []

    def test_arm_plus_camera(self):
        engine = CompositionEngine()
        caps = engine.discover_capabilities({
            "arm1": ["6dof_arm", "gripper"],
            "cam1": ["video_stream", "frame_capture", "color_detection"],
        })
        assert "visual_pick_and_place" in caps
        assert "color_sorting" in caps
        assert "visual_inspection" in caps

    def test_min_citizens_enforced(self):
        engine = CompositionEngine()
        # Even if one citizen has both capabilities, min_citizens=2 means
        # it needs to come from 2 different citizens
        caps = engine.discover_capabilities({
            "super": ["6dof_arm", "video_stream", "color_detection"],
        })
        # All default rules have min_citizens=2, so no match from 1 citizen
        assert caps == []

    def test_custom_rule(self):
        engine = CompositionEngine(rules=[
            CompositionRule(
                required_capabilities=["sensor_a", "sensor_b"],
                composite_capability="combined_sensing",
                min_citizens=1,
            ),
        ])
        caps = engine.discover_capabilities({
            "device1": ["sensor_a", "sensor_b"],
        })
        assert "combined_sensing" in caps

    def test_default_rules_exist(self):
        assert len(DEFAULT_RULES) >= 3

    def test_discover_returns_full_rules(self):
        engine = CompositionEngine()
        rules = engine.discover({
            "arm1": ["6dof_arm"],
            "cam1": ["video_stream"],
        })
        assert len(rules) >= 1
        assert rules[0].composite_capability == "visual_pick_and_place"
