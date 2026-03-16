"""Tests for camera-to-arm calibration."""

import pytest
import numpy as np
from citizenry.calibration import (
    CalibrationPoint, CalibrationResult,
    compute_affine_transform, apply_calibrated_transform,
    CALIBRATION_POSES,
)


class TestCalibrationPoint:
    def test_create(self):
        p = CalibrationPoint(pixel_x=320, pixel_y=240, servo_pan=2048, servo_lift=1600, servo_elbow=2500)
        assert p.pixel_x == 320


class TestCalibrationResult:
    def test_roundtrip(self):
        r = CalibrationResult(
            points=[CalibrationPoint(100, 200, 2048, 1600, 2500)],
            transform_matrix=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            error_pixels=5.0,
        )
        d = r.to_dict()
        r2 = CalibrationResult.from_dict(d)
        assert len(r2.points) == 1
        assert r2.error_pixels == 5.0
        assert r2.transform_matrix is not None


class TestAffineTransform:
    def test_simple_transform(self):
        # 4 known correspondences
        pixels = [(0, 0), (640, 0), (0, 480), (640, 480)]
        servos = [
            (2600, 1200, 2500),
            (1500, 1200, 2500),
            (2600, 2200, 3000),
            (1500, 2200, 3000),
        ]
        T, error = compute_affine_transform(pixels, servos)
        assert T is not None
        assert len(T) == 3
        assert error < 50  # Should be low for perfect correspondences

    def test_center_prediction(self):
        pixels = [(0, 0), (640, 0), (0, 480), (640, 480)]
        servos = [
            (2600, 1200, 2500),
            (1500, 1200, 2500),
            (2600, 2200, 3000),
            (1500, 2200, 3000),
        ]
        T, _ = compute_affine_transform(pixels, servos)
        # Center pixel should map to mid-range servos
        result = apply_calibrated_transform(320, 240, T)
        assert 1800 < result["shoulder_pan"] < 2200
        assert 1500 < result["shoulder_lift"] < 1900

    def test_too_few_points(self):
        with pytest.raises(ValueError):
            compute_affine_transform([(0, 0), (1, 1)], [(100, 100, 100), (200, 200, 200)])

    def test_apply_clips_values(self):
        # Identity-ish transform but with extreme pixel values
        T = [[10, 0, 0], [0, 10, 0], [0, 0, 2500]]
        result = apply_calibrated_transform(999, 999, T)
        # Values should be clipped to safe ranges
        assert result["shoulder_pan"] <= 2800
        assert result["shoulder_lift"] <= 2200


class TestCalibrationPoses:
    def test_poses_exist(self):
        assert len(CALIBRATION_POSES) >= 4

    def test_poses_have_all_motors(self):
        for pose in CALIBRATION_POSES:
            assert "shoulder_pan" in pose
            assert "shoulder_lift" in pose
            assert "elbow_flex" in pose
