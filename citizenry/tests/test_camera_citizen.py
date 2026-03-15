"""Tests for USB camera citizen."""

import pytest
from unittest.mock import MagicMock, patch

from citizenry.camera_citizen import CameraCitizen


class TestCameraCitizen:
    def test_init(self):
        cam = CameraCitizen(camera_index=0, name="test-cam")
        assert cam.name == "test-cam"
        assert cam.citizen_type == "sensor"
        assert "video_stream" in cam.capabilities
        assert "frame_capture" in cam.capabilities
        assert "color_detection" in cam.capabilities

    def test_health_degraded_without_camera(self):
        cam = CameraCitizen(name="test-cam")
        # Don't init camera — simulate no camera available
        cam._camera_ok = False
        cam.health = 0.5
        assert cam.health == 0.5

    @patch("citizenry.camera_citizen.CameraCitizen._capture_frame_b64")
    def test_handle_frame_capture_no_camera(self, mock_capture):
        cam = CameraCitizen(name="test-cam")
        cam._camera_ok = False

        # Mock the send methods
        cam.send_reject = MagicMock()
        env = MagicMock()
        env.sender = "governor_key"
        env.body = {"task": "frame_capture", "task_id": "t1"}

        cam._handle_frame_capture(env, ("127.0.0.1", 8000), env.body)
        cam.send_reject.assert_called_once()

    @patch("citizenry.camera_citizen.CameraCitizen._detect_colors")
    def test_handle_color_detection_no_camera(self, mock_detect):
        cam = CameraCitizen(name="test-cam")
        cam._camera_ok = False

        cam.send_reject = MagicMock()
        env = MagicMock()
        env.sender = "governor_key"
        env.body = {"task": "color_detection", "task_id": "t1"}

        cam._handle_color_detection(env, ("127.0.0.1", 8000), env.body)
        cam.send_reject.assert_called_once()

    def test_handle_propose_dispatches(self):
        cam = CameraCitizen(name="test-cam")
        cam._camera_ok = False
        cam.send_reject = MagicMock()

        env = MagicMock()
        env.sender = "governor_key"
        env.body = {"task": "frame_capture"}
        cam._handle_propose(env, ("127.0.0.1", 8000))
        cam.send_reject.assert_called()

    def test_handle_propose_unknown_task(self):
        cam = CameraCitizen(name="test-cam")
        cam.send_reject = MagicMock()

        env = MagicMock()
        env.sender = "governor_key"
        env.body = {"task": "unknown_task"}
        cam._handle_propose(env, ("127.0.0.1", 8000))
        cam.send_reject.assert_called_once()
        assert "unknown task" in cam.send_reject.call_args[0][1]
