"""Offline Timeline Analyzer — correlate video with telemetry after recording.

Loads a recording session and analyzes:
- For each servo command: did the arm actually move? (video evidence)
- Movement direction and magnitude per frame
- Stall detection from video
- Calibration results extracted from correlated data
- Annotated video with telemetry overlay
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .recorder import load_session, RECORDINGS_DIR


@dataclass
class FrameAnalysis:
    """Analysis result for a single video frame."""
    frame_index: int
    timestamp: float
    mean_diff: float = 0.0
    optical_flow_mag: float = 0.0
    flow_direction_y: float = 0.0
    movement_detected: bool = False
    arm_centroid_y: float = 0.0


@dataclass
class CommandAnalysis:
    """Analysis of a single servo command correlated with video."""
    timestamp: float
    motor: str
    target: int
    actual: int
    video_movement: float = 0.0
    video_direction: str = "none"
    servo_moved: bool = False
    camera_confirms: bool = False
    discrepancy: bool = False  # Servo says moved but camera says no (or vice versa)


@dataclass
class AnalysisResult:
    """Complete analysis of a recording session."""
    session_name: str
    total_frames: int = 0
    total_commands: int = 0
    frame_analyses: list[FrameAnalysis] = field(default_factory=list)
    command_analyses: list[CommandAnalysis] = field(default_factory=list)
    detected_stalls: list[dict] = field(default_factory=list)
    motor_ranges: dict[str, dict] = field(default_factory=dict)
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "session": self.session_name,
            "total_frames": self.total_frames,
            "total_commands": self.total_commands,
            "stalls": len(self.detected_stalls),
            "motor_ranges": self.motor_ranges,
            "discrepancies": sum(1 for c in self.command_analyses if c.discrepancy),
            "duration_s": round(self.duration_s, 1),
        }


def analyze_session(session_name: str, log_fn=None) -> AnalysisResult:
    """Run full offline analysis on a recorded session.

    Loads video + telemetry, correlates them, and produces analysis results.
    """
    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log(f"Loading session: {session_name}")
    data = load_session(session_name)
    if "error" in data:
        _log(f"Error: {data['error']}")
        return AnalysisResult(session_name=session_name)

    result = AnalysisResult(session_name=session_name)
    t0 = time.time()

    # Load video
    video_path = data.get("video_path")
    video_timestamps = data.get("video_timestamps", [])
    commands = data.get("commands", [])
    telemetry = data.get("telemetry", [])
    events = data.get("events", [])

    _log(f"  Video: {'found' if video_path else 'missing'}")
    _log(f"  Telemetry: {len(telemetry)} samples")
    _log(f"  Commands: {len(commands)} entries")
    _log(f"  Events: {len(events)} entries")
    _log(f"  Video frames: {len(video_timestamps)} timestamps")

    if not video_path:
        _log("No video — analysis limited to telemetry only")
        result.duration_s = time.time() - t0
        return result

    # Analyze video frame by frame
    _log("\nAnalyzing video frames...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        _log("Failed to open video")
        return result

    prev_gray = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        fa = FrameAnalysis(
            frame_index=frame_idx,
            timestamp=video_timestamps[frame_idx] if frame_idx < len(video_timestamps) else 0,
        )

        if prev_gray is not None:
            # Frame difference
            diff = cv2.absdiff(prev_gray, gray)
            fa.mean_diff = float(np.mean(diff))

            # Optical flow
            try:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None,
                    pyr_scale=0.5, levels=2, winsize=15,
                    iterations=1, poly_n=5, poly_sigma=1.2, flags=0
                )
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                fa.optical_flow_mag = float(np.mean(mag))
                fa.flow_direction_y = float(np.mean(flow[..., 1]))
            except Exception:
                pass

            fa.movement_detected = fa.mean_diff > 2.0 or fa.optical_flow_mag > 0.5

        result.frame_analyses.append(fa)
        prev_gray = gray
        frame_idx += 1

        if frame_idx % 50 == 0:
            _log(f"  Processed {frame_idx} frames...")

    cap.release()
    result.total_frames = frame_idx
    _log(f"  Total: {frame_idx} frames analyzed")

    # Correlate commands with video frames
    _log("\nCorrelating commands with video...")
    result.total_commands = len(commands)

    for cmd in commands:
        cmd_time = cmd.get("t", 0)
        ca = CommandAnalysis(
            timestamp=cmd_time,
            motor=cmd.get("motor", ""),
            target=cmd.get("target", 0),
            actual=cmd.get("actual", -1),
        )

        # Find video frames within ±1 second of this command
        nearby_frames = [
            fa for fa in result.frame_analyses
            if abs(fa.timestamp - cmd_time) < 1.0
        ]

        if nearby_frames:
            ca.video_movement = max(fa.mean_diff for fa in nearby_frames)
            ca.camera_confirms = any(fa.movement_detected for fa in nearby_frames)
            # Direction from flow
            flows = [fa.flow_direction_y for fa in nearby_frames if fa.flow_direction_y != 0]
            if flows:
                avg_flow = sum(flows) / len(flows)
                ca.video_direction = "up" if avg_flow < -0.3 else "down" if avg_flow > 0.3 else "none"

        # Servo says it moved?
        if ca.actual > 0:
            ca.servo_moved = abs(ca.actual - ca.target) < 50  # Close to target = moved
        else:
            ca.servo_moved = False  # -1 = read failed

        # Discrepancy: servo says moved but camera says no (or vice versa)
        ca.discrepancy = ca.servo_moved != ca.camera_confirms

        result.command_analyses.append(ca)

    # Detect stalls from video
    _log("\nDetecting stalls...")
    in_stall = False
    stall_start = 0
    for fa in result.frame_analyses:
        if not fa.movement_detected and not in_stall:
            in_stall = True
            stall_start = fa.frame_index
        elif fa.movement_detected and in_stall:
            stall_duration = fa.frame_index - stall_start
            if stall_duration > 3:  # At least 3 frames of no movement
                result.detected_stalls.append({
                    "start_frame": stall_start,
                    "end_frame": fa.frame_index,
                    "duration_frames": stall_duration,
                    "timestamp": fa.timestamp,
                })
            in_stall = False

    _log(f"  Detected {len(result.detected_stalls)} stalls")

    # Extract motor ranges from commands
    _log("\nExtracting motor ranges...")
    for motor_name in set(ca.motor for ca in result.command_analyses):
        motor_cmds = [ca for ca in result.command_analyses if ca.motor == motor_name]
        if not motor_cmds:
            continue
        positions = [ca.actual for ca in motor_cmds if ca.actual > 0]
        confirmed_positions = [ca.actual for ca in motor_cmds if ca.actual > 0 and ca.camera_confirms]

        if confirmed_positions:
            result.motor_ranges[motor_name] = {
                "min": min(confirmed_positions),
                "max": max(confirmed_positions),
                "range": max(confirmed_positions) - min(confirmed_positions),
                "samples": len(confirmed_positions),
                "method": "video_confirmed",
            }
        elif positions:
            result.motor_ranges[motor_name] = {
                "min": min(positions),
                "max": max(positions),
                "range": max(positions) - min(positions),
                "samples": len(positions),
                "method": "register_only",
            }
        _log(f"  {motor_name}: {result.motor_ranges.get(motor_name, 'no data')}")

    result.duration_s = time.time() - t0
    _log(f"\nAnalysis complete in {result.duration_s:.1f}s")

    # Save results
    results_path = RECORDINGS_DIR / session_name / "analysis.json"
    try:
        results_path.write_text(json.dumps(result.to_dict(), indent=2))
    except Exception:
        pass

    return result


def generate_annotated_video(session_name: str, log_fn=None) -> str | None:
    """Generate a video with telemetry overlay."""
    def _log(msg):
        if log_fn:
            log_fn(msg)

    data = load_session(session_name)
    video_path = data.get("video_path")
    if not video_path:
        return None

    commands = data.get("commands", [])
    events = data.get("events", [])
    video_timestamps = data.get("video_timestamps", [])

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 10

    output_path = str(RECORDINGS_DIR / session_name / "annotated.avi")
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        ts = video_timestamps[frame_idx] if frame_idx < len(video_timestamps) else 0

        # Find commands near this frame
        nearby_cmds = [c for c in commands if abs(c.get("t", 0) - ts) < 0.5]
        nearby_events = [e for e in events if abs(e.get("t", 0) - ts) < 0.5]

        # Draw overlay
        y_offset = 20
        cv2.putText(frame, f"t={ts:.2f}s  frame={frame_idx}", (10, y_offset),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        for cmd in nearby_cmds:
            y_offset += 18
            text = f"{cmd.get('motor', '?')}: target={cmd.get('target', '?')} actual={cmd.get('actual', '?')}"
            cv2.putText(frame, text, (10, y_offset),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

        for evt in nearby_events:
            y_offset += 18
            text = f"EVENT: {evt.get('event', '?')}"
            color = (0, 0, 255) if "stall" in evt.get("event", "") else (0, 255, 255)
            cv2.putText(frame, text, (10, y_offset),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()
    _log(f"Annotated video: {output_path} ({frame_idx} frames)")
    return output_path
