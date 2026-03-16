"""Tests for camera-to-arm calibration system."""

import pytest
import cv2
import numpy as np
from citizenry.calibration import (
    CalibrationPoint, CalibrationResult, PlacementScore,
    GripperDetector, CameraPlacementGuide,
    fit_homography, apply_homography, compute_validation_error,
    CALIBRATION_POSES, VALIDATION_POSES, CORNER_POSES,
    _full_pose, HOME,
)


class TestCalibrationPoint:
    def test_create(self):
        p = CalibrationPoint(pixel_x=320, pixel_y=240, servo_pan=2048, servo_lift=1600, servo_elbow=2500)
        assert p.pixel_x == 320
        assert p.is_inlier is True


class TestCalibrationResult:
    def test_roundtrip(self):
        r = CalibrationResult(
            points=[CalibrationPoint(100, 200, 2048, 1600, 2500)],
            homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, 2500]],
            inlier_count=1,
            reprojection_error=5.0,
        )
        d = r.to_dict()
        r2 = CalibrationResult.from_dict(d)
        assert len(r2.points) == 1
        assert r2.reprojection_error == 5.0
        assert r2.homography is not None
        assert r2.inlier_count == 1


class TestGripperDetector:
    def test_detect_with_difference(self):
        """Simulate gripper open/close with synthetic frames."""
        # Frame with gripper open: white circle at (320, 240)
        frame_open = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(frame_open, (320, 240), 30, (255, 255, 255), -1)

        # Frame with gripper closed: smaller circle (different shape)
        frame_closed = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(frame_closed, (320, 240), 10, (255, 255, 255), -1)

        result = GripperDetector.detect(frame_open, frame_closed)
        assert result is not None
        px, py = result
        # Should be near (320, 240) — the gripper region
        assert abs(px - 320) < 40
        assert abs(py - 240) < 40

    def test_detect_no_difference(self):
        """Identical frames → no detection."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = GripperDetector.detect(frame, frame)
        assert result is None

    def test_detect_none_frames(self):
        assert GripperDetector.detect(None, None) is None

    def test_color_detection(self):
        """Detect green object in frame."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Draw a green circle (HSV green ≈ BGR (0, 255, 0))
        cv2.circle(frame, (200, 300), 25, (0, 255, 0), -1)

        result = GripperDetector.detect_by_color(frame)
        assert result is not None
        px, py = result
        assert abs(px - 200) < 30
        assert abs(py - 300) < 30

    def test_color_detection_none(self):
        assert GripperDetector.detect_by_color(None) is None

    def test_color_detection_no_match(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)  # All black
        result = GripperDetector.detect_by_color(frame)
        assert result is None


class TestCameraPlacementGuide:
    def test_all_corners_visible_centered(self):
        corners = [(160, 120), (480, 120), (160, 360), (480, 360)]
        score = CameraPlacementGuide.evaluate(corners)
        assert score.corners_visible == 4
        assert score.overall == "good"
        assert score.centered

    def test_no_corners(self):
        score = CameraPlacementGuide.evaluate([None, None, None, None])
        assert score.corners_visible == 0
        assert score.overall == "bad"

    def test_partial_visibility(self):
        corners = [(100, 100), (500, 100), None, None]
        score = CameraPlacementGuide.evaluate(corners)
        assert score.corners_visible == 2
        assert score.overall in ("adjust", "bad")

    def test_too_close(self):
        # Corners fill nearly entire frame
        corners = [(10, 10), (630, 10), (10, 470), (630, 470)]
        score = CameraPlacementGuide.evaluate(corners)
        assert score.coverage_pct > 80
        assert any("too close" in s.lower() for s in score.suggestions)

    def test_too_far(self):
        # Tiny workspace in frame
        corners = [(300, 230), (340, 230), (300, 250), (340, 250)]
        score = CameraPlacementGuide.evaluate(corners)
        assert score.coverage_pct < 15

    def test_off_center(self):
        # Workspace in top-left corner
        corners = [(10, 10), (200, 10), (10, 150), (200, 150)]
        score = CameraPlacementGuide.evaluate(corners)
        assert not score.centered
        assert any("shift" in s.lower() or "off-center" in s.lower() for s in score.suggestions)


class TestHomography:
    def test_fit_simple(self):
        """4 points with known correspondence."""
        pixels = [(0, 0), (640, 0), (0, 480), (640, 480)]
        servos = [
            (2600, 1200, 2500),
            (1500, 1200, 2500),
            (2600, 2200, 3000),
            (1500, 2200, 3000),
        ]
        transform, inliers, outliers, error = fit_homography(pixels, servos)
        assert transform is not None
        assert inliers == 4
        assert outliers == 0
        assert error < 50

    def test_fit_with_outlier(self):
        """RANSAC should reject outlier."""
        pixels = [(0, 0), (640, 0), (0, 480), (640, 480), (320, 240)]
        servos = [
            (2600, 1200, 2500),
            (1500, 1200, 2500),
            (2600, 2200, 3000),
            (1500, 2200, 3000),
            (9999, 9999, 9999),  # Outlier!
        ]
        transform, inliers, outliers, error = fit_homography(pixels, servos)
        assert transform is not None
        assert outliers >= 1

    def test_too_few_points(self):
        pixels = [(0, 0), (1, 1)]
        servos = [(100, 100, 100), (200, 200, 200)]
        transform, _, _, _ = fit_homography(pixels, servos)
        assert transform is None

    def test_apply_center(self):
        """Center pixel should map to mid-range servos."""
        pixels = [(0, 0), (640, 0), (0, 480), (640, 480)]
        servos = [
            (2600, 1200, 2500),
            (1500, 1200, 2500),
            (2600, 2200, 3000),
            (1500, 2200, 3000),
        ]
        transform, _, _, _ = fit_homography(pixels, servos)
        result = apply_homography(320, 240, transform)
        assert 1800 < result["shoulder_pan"] < 2300
        assert 1500 < result["shoulder_lift"] < 1900
        assert 2500 < result["elbow_flex"] < 3000

    def test_apply_clips_extremes(self):
        """Values should be clipped to safe servo ranges."""
        # Degenerate transform
        transform = [[10, 0, 0], [0, 10, 0], [0, 0, 1], [0, 0, 2500]]
        result = apply_homography(999, 999, transform)
        assert result["shoulder_pan"] <= 2800
        assert result["shoulder_lift"] <= 2200
        assert result["elbow_flex"] <= 3200


class TestValidation:
    def test_perfect_calibration(self):
        """Validation error should be low with perfect transform."""
        pixels = [(0, 0), (640, 0), (0, 480), (640, 480)]
        servos = [
            (2600, 1200, 2500),
            (1500, 1200, 2500),
            (2600, 2200, 3000),
            (1500, 2200, 3000),
        ]
        transform, _, _, _ = fit_homography(pixels, servos)
        # Validate on the same points (perfect fit)
        error = compute_validation_error(pixels, servos, transform)
        assert error < 50

    def test_no_transform(self):
        error = compute_validation_error([(0, 0)], [(2048, 1600, 2500)], None)
        assert error == float('inf')


class TestPosesExist:
    def test_calibration_poses(self):
        assert len(CALIBRATION_POSES) >= 6

    def test_validation_poses(self):
        assert len(VALIDATION_POSES) >= 3

    def test_corner_poses(self):
        assert len(CORNER_POSES) == 4

    def test_full_pose_fills_defaults(self):
        partial = {"shoulder_pan": 1700}
        full = _full_pose(partial)
        assert full["shoulder_pan"] == 1700
        assert full["gripper"] == 1400
        assert "wrist_flex" in full
