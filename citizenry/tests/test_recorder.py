"""Tests for multi-modal timeline recorder."""

import pytest
import json
import time
from pathlib import Path
from citizenry.recorder import (
    TimelineRecorder, TimelineEntry, SessionMetadata,
    VideoStream, list_sessions, load_session,
)


class TestTimelineEntry:
    def test_to_json_line(self):
        e = TimelineEntry(timestamp_mono=1.234, timestamp_wall=1000.0, stream="telemetry",
                         data={"motors": {"pan": {"position": 2048}}})
        line = e.to_json_line()
        parsed = json.loads(line)
        assert parsed["stream"] == "telemetry"
        assert parsed["t"] == 1.234
        assert parsed["motors"]["pan"]["position"] == 2048


class TestSessionMetadata:
    def test_to_dict(self):
        m = SessionMetadata(name="test", video_frames=100, telemetry_samples=50)
        d = m.to_dict()
        assert d["name"] == "test"
        assert d["video_frames"] == 100


class TestTimelineRecorder:
    def test_log_event_without_start(self):
        # Should not crash even without start()
        r = TimelineRecorder("test-no-start")
        r.log_event("test_event", {"key": "value"})
        # No crash = pass

    def test_log_telemetry_without_start(self):
        r = TimelineRecorder("test")
        r.log_telemetry({"pan": {"position": 2048}})
        # No crash

    def test_log_command_without_start(self):
        r = TimelineRecorder("test")
        r.log_command("shoulder_pan", target=2048, actual=2045)
        # No crash

    def test_session_name_default(self):
        r = TimelineRecorder()
        assert r.session_name.startswith("session-")

    def test_is_recording(self):
        r = TimelineRecorder("test")
        assert not r.is_recording
