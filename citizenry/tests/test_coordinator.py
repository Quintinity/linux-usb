"""Tests for the task coordinator."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from citizenry.coordinator import TaskCoordinator, CompositeTaskResult
from citizenry.visual_tasks import plan_pick_and_place, plan_sort_sequence


class TestCoordinator:
    def test_init(self):
        gov = MagicMock()
        coord = TaskCoordinator(gov)
        assert coord.governor is gov


class TestCompositeTaskResult:
    def test_defaults(self):
        r = CompositeTaskResult()
        assert not r.success
        assert r.steps_completed == 0
        assert r.duration_ms == 0

    def test_with_data(self):
        r = CompositeTaskResult(
            success=True,
            steps_completed=3,
            steps_total=3,
            detections=[{"color": "red"}],
            duration_ms=5000,
        )
        assert r.success
        assert len(r.detections) == 1


class TestVisualPickAndPlacePlanning:
    """Test the planning logic used by the coordinator."""

    def test_plan_with_detections(self):
        dets = [
            {"color": "red", "bbox": [200, 300, 60, 60], "area": 3600},
            {"color": "blue", "bbox": [400, 100, 30, 30], "area": 900},
        ]
        target, arm_pos = plan_pick_and_place(dets)
        assert target is not None
        assert target.color == "red"  # Largest
        assert arm_pos is not None
        assert "shoulder_pan" in arm_pos
        assert "gripper" in arm_pos

    def test_plan_with_target_color(self):
        dets = [
            {"color": "red", "bbox": [200, 300, 60, 60], "area": 3600},
            {"color": "blue", "bbox": [400, 100, 80, 80], "area": 6400},
        ]
        target, arm_pos = plan_pick_and_place(dets, target_color="blue")
        assert target.color == "blue"


class TestSortPlanning:
    def test_plan_sort_sequence(self):
        dets = [
            {"color": "red", "bbox": [100, 100, 50, 50], "area": 2500},
            {"color": "blue", "bbox": [300, 300, 40, 40], "area": 1600},
            {"color": "green", "bbox": [200, 200, 60, 60], "area": 3600},
        ]
        seq = plan_sort_sequence(dets)
        assert len(seq) == 3
        # Sorted by area descending
        assert seq[0][0].color == "green"
        assert seq[1][0].color == "red"
        assert seq[2][0].color == "blue"
        # Each has pick and place positions
        for obj, pick, place in seq:
            assert "shoulder_pan" in pick
            assert "shoulder_pan" in place
