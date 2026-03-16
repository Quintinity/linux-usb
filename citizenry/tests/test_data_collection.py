"""Tests for data collection."""

import pytest
from unittest.mock import MagicMock
from citizenry.data_collection import DataCollector, RecordingSession


class TestRecordingSession:
    def test_defaults(self):
        s = RecordingSession()
        assert not s.is_recording
        assert s.frame_count == 0

class TestDataCollector:
    def test_init(self):
        gov = MagicMock()
        dc = DataCollector(gov)
        assert not dc.session.is_recording

    def test_start_recording(self):
        gov = MagicMock()
        dc = DataCollector(gov)
        ok = dc.start_recording("pick and place")
        assert ok
        assert dc.session.is_recording
        assert dc.session.task_label == "pick and place"

    def test_double_start(self):
        gov = MagicMock()
        dc = DataCollector(gov)
        dc.start_recording()
        assert not dc.start_recording()  # Already recording

    def test_add_frame(self):
        gov = MagicMock()
        dc = DataCollector(gov)
        dc.start_recording()
        dc.add_frame(arm_positions={"shoulder_pan": 2048})
        assert dc.session.frame_count == 1

    def test_add_frame_not_recording(self):
        gov = MagicMock()
        dc = DataCollector(gov)
        dc.add_frame(arm_positions={"shoulder_pan": 2048})
        assert dc.session.frame_count == 0

    def test_stop_recording(self):
        gov = MagicMock()
        dc = DataCollector(gov)
        dc.start_recording("test")
        dc.add_frame(arm_positions={"shoulder_pan": 2048})
        dc.add_frame(arm_positions={"shoulder_pan": 2100})
        result = dc.stop_recording()
        assert result["frames"] == 2
        assert result["task"] == "test"
        assert not dc.session.is_recording

    def test_stop_not_recording(self):
        gov = MagicMock()
        dc = DataCollector(gov)
        result = dc.stop_recording()
        assert "error" in result
