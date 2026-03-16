"""Tests for visual task coordination."""

import pytest
from citizenry.visual_tasks import (
    DetectedObject, camera_to_arm_position, plan_pick_and_place,
    plan_sort_sequence, HOME_POSITION, WORKSPACE, SORT_BINS,
)


class TestDetectedObject:
    def test_from_detection(self):
        d = {"color": "red", "bbox": [100, 200, 50, 60], "area": 3000}
        obj = DetectedObject.from_detection(d, 640, 480)
        assert obj.color == "red"
        assert obj.center_x == pytest.approx((100 + 25) / 640)
        assert obj.center_y == pytest.approx((200 + 30) / 480)


class TestCameraToArm:
    def test_center_maps_to_mid_range(self):
        pos = camera_to_arm_position(0.5, 0.5)
        ws = WORKSPACE
        pan_mid = (ws["shoulder_pan"]["min"] + ws["shoulder_pan"]["max"]) / 2
        assert abs(pos["shoulder_pan"] - pan_mid) < 50

    def test_left_maps_to_high_pan(self):
        left = camera_to_arm_position(0.0, 0.5)
        right = camera_to_arm_position(1.0, 0.5)
        # Camera left = arm right (mirrored)
        assert left["shoulder_pan"] > right["shoulder_pan"]

    def test_gripper_starts_open(self):
        pos = camera_to_arm_position(0.5, 0.5)
        assert pos["gripper"] == WORKSPACE["gripper"]["open"]


class TestPlanPickAndPlace:
    def test_no_detections(self):
        obj, pos = plan_pick_and_place([])
        assert obj is None
        assert pos is None

    def test_single_detection(self):
        dets = [{"color": "red", "bbox": [320, 240, 50, 50], "area": 2500}]
        obj, pos = plan_pick_and_place(dets)
        assert obj is not None
        assert obj.color == "red"
        assert pos is not None
        assert "shoulder_pan" in pos

    def test_filter_by_color(self):
        dets = [
            {"color": "red", "bbox": [100, 100, 50, 50], "area": 2500},
            {"color": "blue", "bbox": [300, 300, 80, 80], "area": 6400},
        ]
        obj, pos = plan_pick_and_place(dets, target_color="red")
        assert obj.color == "red"

    def test_picks_largest(self):
        dets = [
            {"color": "red", "bbox": [100, 100, 20, 20], "area": 400},
            {"color": "red", "bbox": [300, 300, 80, 80], "area": 6400},
        ]
        obj, pos = plan_pick_and_place(dets)
        assert obj.area == 6400

    def test_no_match_for_color(self):
        dets = [{"color": "red", "bbox": [100, 100, 50, 50], "area": 2500}]
        obj, pos = plan_pick_and_place(dets, target_color="purple")
        assert obj is None


class TestPlanSortSequence:
    def test_empty(self):
        assert plan_sort_sequence([]) == []

    def test_sorts_by_color(self):
        dets = [
            {"color": "red", "bbox": [100, 100, 50, 50], "area": 2500},
            {"color": "blue", "bbox": [300, 300, 40, 40], "area": 1600},
        ]
        seq = plan_sort_sequence(dets)
        assert len(seq) == 2
        # Largest first
        assert seq[0][0].color == "red"
        assert seq[0][2] == SORT_BINS["red"]

    def test_unknown_color_skipped(self):
        dets = [{"color": "purple", "bbox": [100, 100, 50, 50], "area": 2500}]
        seq = plan_sort_sequence(dets)
        assert len(seq) == 0  # No bin for purple
