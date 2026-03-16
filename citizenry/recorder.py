"""Multi-Modal Timeline Recorder — synchronized recording of all data streams.

Records video, servo telemetry, commands, and events on a common monotonic
clock. Lightweight enough to run during normal operation, not just calibration.

Usage:
    recorder = TimelineRecorder(session_name="calibration-001")
    recorder.start(camera_index=0)
    recorder.log_telemetry({"shoulder_pan": {"position": 2048, "current": 50}})
    recorder.log_command("shoulder_lift", target=1800, actual=1795)
    recorder.log_event("stall_detected", {"motor": "shoulder_lift", "position": 1795})
    recorder.stop()
    # Produces: ~/.citizenry/recordings/calibration-001/
    #   video.avi, telemetry.jsonl, commands.jsonl, events.jsonl, metadata.json
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .persistence import CITIZENRY_DIR

RECORDINGS_DIR = CITIZENRY_DIR / "recordings"


@dataclass
class TimelineEntry:
    """A single entry on the timeline."""
    timestamp_mono: float      # time.monotonic() — for sync
    timestamp_wall: float      # time.time() — for display
    stream: str                # "telemetry", "command", "event", "sensor"
    data: dict = field(default_factory=dict)

    def to_json_line(self) -> str:
        return json.dumps({
            "t": round(self.timestamp_mono, 6),
            "wall": round(self.timestamp_wall, 3),
            "stream": self.stream,
            **self.data,
        })


@dataclass
class SessionMetadata:
    """Metadata for a recording session."""
    name: str
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_s: float = 0.0
    video_frames: int = 0
    telemetry_samples: int = 0
    commands: int = 0
    events: int = 0
    video_fps: int = 10
    video_resolution: tuple[int, int] = (640, 480)
    motors: list[str] = field(default_factory=list)
    sensors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "started_at": self.started_at,
            "duration_s": round(self.duration_s, 1),
            "video_frames": self.video_frames,
            "telemetry_samples": self.telemetry_samples,
            "commands": self.commands,
            "events": self.events,
            "video_fps": self.video_fps,
            "video_resolution": list(self.video_resolution),
        }


class VideoStream:
    """Records video frames to disk with timestamps."""

    def __init__(self, output_path: Path, fps: int = 10,
                 resolution: tuple[int, int] = (640, 480)):
        self.output_path = output_path
        self.fps = fps
        self.resolution = resolution
        self._writer = None
        self._cap = None
        self._running = False
        self._thread = None
        self._frame_count = 0
        self._frame_timestamps: list[float] = []
        self._lock = threading.Lock()
        self._latest_frame = None

    def start(self, camera_index: int = 0):
        """Start video recording in a background thread."""
        import cv2
        self._cap = cv2.VideoCapture(camera_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

        if not self._cap.isOpened():
            return False

        # Save frames as JPEG images — most reliable across all platforms
        # VideoWriter codecs are unreliable on Pi (FFmpeg backend issues)
        self._save_frames = True
        self._writer = None
        (self.output_path.parent / "frames").mkdir(exist_ok=True)

        self._running = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        return True

    def _record_loop(self):
        import cv2
        interval = 1.0 / self.fps
        while self._running:
            t0 = time.monotonic()
            ret, frame = self._cap.read()
            if ret:
                if self._writer:
                    self._writer.write(frame)
                elif self._save_frames:
                    frame_path = self.output_path.parent / "frames" / f"{self._frame_count:06d}.jpg"
                    cv2.imwrite(str(frame_path), frame)

                mono = time.monotonic()
                self._frame_timestamps.append(mono)
                self._frame_count += 1
                with self._lock:
                    self._latest_frame = frame.copy()

            elapsed = time.monotonic() - t0
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)

    def get_latest_frame(self) -> np.ndarray | None:
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self._writer:
            self._writer.release()
        if self._cap:
            self._cap.release()

        # Save frame timestamps
        ts_path = self.output_path.with_suffix('.timestamps.json')
        try:
            ts_path.write_text(json.dumps(self._frame_timestamps))
        except Exception:
            pass

    @property
    def frame_count(self) -> int:
        return self._frame_count


class TimelineRecorder:
    """Records all data streams to a session directory."""

    def __init__(self, session_name: str | None = None):
        if session_name is None:
            session_name = f"session-{int(time.time())}"
        self.session_name = session_name
        self.session_dir = RECORDINGS_DIR / session_name
        self.metadata = SessionMetadata(name=session_name)
        self._video: VideoStream | None = None
        self._telemetry_file = None
        self._commands_file = None
        self._events_file = None
        self._sensors_file = None
        self._start_mono: float = 0
        self._running = False

    def start(self, camera_index: int = 0, video_fps: int = 10,
              video_resolution: tuple[int, int] = (640, 480)):
        """Start recording all streams."""
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._start_mono = time.monotonic()
        self.metadata.started_at = time.time()
        self.metadata.video_fps = video_fps
        self.metadata.video_resolution = video_resolution
        self._running = True

        # Start video
        self._video = VideoStream(
            self.session_dir / "video.avi",
            fps=video_fps,
            resolution=video_resolution,
        )
        video_ok = self._video.start(camera_index)
        if not video_ok:
            self._video = None

        # Open data files
        self._telemetry_file = open(self.session_dir / "telemetry.jsonl", "w")
        self._commands_file = open(self.session_dir / "commands.jsonl", "w")
        self._events_file = open(self.session_dir / "events.jsonl", "w")
        self._sensors_file = open(self.session_dir / "sensors.jsonl", "w")

        self.log_event("recording_started", {
            "session": self.session_name,
            "camera": camera_index,
            "video": video_ok,
        })

    def stop(self) -> SessionMetadata:
        """Stop recording and save metadata."""
        self._running = False

        self.log_event("recording_stopped", {})

        if self._video:
            self._video.stop()
            self.metadata.video_frames = self._video.frame_count

        for f in [self._telemetry_file, self._commands_file,
                  self._events_file, self._sensors_file]:
            if f:
                try:
                    f.close()
                except Exception:
                    pass

        self.metadata.ended_at = time.time()
        self.metadata.duration_s = time.time() - self.metadata.started_at

        # Save metadata
        meta_path = self.session_dir / "metadata.json"
        try:
            meta_path.write_text(json.dumps(self.metadata.to_dict(), indent=2))
        except Exception:
            pass

        return self.metadata

    def log_telemetry(self, motor_data: dict[str, dict]):
        """Log servo telemetry for all motors.

        motor_data: {"shoulder_pan": {"position": 2048, "current": 50, "load": 10, "temp": 35}}
        """
        if not self._running or not self._telemetry_file:
            return
        entry = TimelineEntry(
            timestamp_mono=time.monotonic() - self._start_mono,
            timestamp_wall=time.time(),
            stream="telemetry",
            data={"motors": motor_data},
        )
        self._telemetry_file.write(entry.to_json_line() + "\n")
        self._telemetry_file.flush()
        self.metadata.telemetry_samples += 1

    def log_command(self, motor_name: str, target: int, actual: int = -1,
                    command_type: str = "position"):
        """Log a servo command."""
        if not self._running or not self._commands_file:
            return
        entry = TimelineEntry(
            timestamp_mono=time.monotonic() - self._start_mono,
            timestamp_wall=time.time(),
            stream="command",
            data={"motor": motor_name, "target": target, "actual": actual,
                  "type": command_type},
        )
        self._commands_file.write(entry.to_json_line() + "\n")
        self._commands_file.flush()
        self.metadata.commands += 1

    def log_event(self, event_type: str, data: dict | None = None):
        """Log an event (stall, reflex, task start/end, etc)."""
        if not self._events_file:
            return
        entry = TimelineEntry(
            timestamp_mono=time.monotonic() - self._start_mono,
            timestamp_wall=time.time(),
            stream="event",
            data={"event": event_type, **(data or {})},
        )
        self._events_file.write(entry.to_json_line() + "\n")
        self._events_file.flush()
        self.metadata.events += 1

    def log_sensor(self, sensor_name: str, data: dict):
        """Log data from any sensor (touch, force, IMU, mic, etc)."""
        if not self._running or not self._sensors_file:
            return
        entry = TimelineEntry(
            timestamp_mono=time.monotonic() - self._start_mono,
            timestamp_wall=time.time(),
            stream="sensor",
            data={"sensor": sensor_name, **data},
        )
        self._sensors_file.write(entry.to_json_line() + "\n")
        self._sensors_file.flush()

    def get_latest_frame(self) -> np.ndarray | None:
        """Get the most recent camera frame (for live preview)."""
        if self._video:
            return self._video.get_latest_frame()
        return None

    @property
    def is_recording(self) -> bool:
        return self._running

    @property
    def elapsed_s(self) -> float:
        if not self._running:
            return 0
        return time.monotonic() - (self._start_mono + self.metadata.started_at - self.metadata.started_at)


# ── Session Management ────────────────────────────────────────────────────────

def list_sessions() -> list[dict]:
    """List all recording sessions."""
    sessions = []
    if not RECORDINGS_DIR.exists():
        return sessions
    for d in sorted(RECORDINGS_DIR.iterdir()):
        if d.is_dir():
            meta_path = d / "metadata.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    sessions.append(meta)
                except Exception:
                    sessions.append({"name": d.name, "error": "corrupt metadata"})
            else:
                sessions.append({"name": d.name, "error": "no metadata"})
    return sessions


def load_session(name: str) -> dict:
    """Load a recording session's data for analysis."""
    session_dir = RECORDINGS_DIR / name
    if not session_dir.exists():
        return {"error": f"session {name} not found"}

    data = {"name": name}

    # Load metadata
    meta_path = session_dir / "metadata.json"
    if meta_path.exists():
        data["metadata"] = json.loads(meta_path.read_text())

    # Load telemetry
    telem_path = session_dir / "telemetry.jsonl"
    if telem_path.exists():
        data["telemetry"] = [json.loads(line) for line in telem_path.read_text().strip().split("\n") if line]

    # Load commands
    cmd_path = session_dir / "commands.jsonl"
    if cmd_path.exists():
        data["commands"] = [json.loads(line) for line in cmd_path.read_text().strip().split("\n") if line]

    # Load events
    evt_path = session_dir / "events.jsonl"
    if evt_path.exists():
        data["events"] = [json.loads(line) for line in evt_path.read_text().strip().split("\n") if line]

    # Load video timestamps
    ts_path = session_dir / "video.timestamps.json"
    if ts_path.exists():
        data["video_timestamps"] = json.loads(ts_path.read_text())

    # Video path (for analysis)
    video_path = session_dir / "video.avi"
    if video_path.exists():
        data["video_path"] = str(video_path)

    return data
