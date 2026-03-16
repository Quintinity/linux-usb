---
story_id: "REC-v1"
status: ready-for-dev
created: 2026-03-16
---

# Story: Multi-Modal Synchronized Recording & Offline Analysis

## User Story
As a president/governor, I want ALL sensor data recorded to a synchronized timeline during calibration and operation, so I can replay, analyze, debug, and train models from real robot behavior.

## Architecture

### Phase 1: RECORD (lightweight, runs during operation)
- TimelineRecorder: manages all data streams on a common clock
- VideoStream: records camera frames (OpenCV VideoWriter, MJPG codec)
- TelemetryStream: logs servo data per sample (position, current, load, temp, status)
- CommandStream: logs every command sent to servos (target position, timestamp)
- EventStream: logs events (reflex fired, stall detected, task started/completed)
- SensorStream: extensible for touch, force, IMU, microphone
- All streams reference a common monotonic clock (time.monotonic_ns)
- Output: session directory with video.avi + telemetry.jsonl + commands.jsonl + events.jsonl

### Phase 2: ANALYZE (offline, can run multiple times with different params)
- TimelineAnalyzer: loads a recording session and correlates streams
- VideoAnalyzer: computes optical flow, frame diff, contour tracking per frame
- CorrelationEngine: for each command, find video frames ±500ms, measure response
- CalibrationExtractor: from correlated data, determine actual joint limits
- AnnotatedVideoGenerator: render telemetry overlay on video frames, save as new video

### Phase 3: REVIEW (web dashboard)
- Recording browser: list sessions, show metadata
- Video player with timeline scrub
- Telemetry charts synced to video position
- Event markers on timeline
- Export to LeRobot dataset format

## Data Streams

| Stream | Source | Rate | Format |
|--------|--------|------|--------|
| Video | Camera (OpenCV) | 10-30 FPS | MJPG .avi |
| Servo telemetry | STS3215 registers | 10 Hz | JSONL |
| Commands | Governor/citizen | Event-driven | JSONL |
| Events | Reflexes, tasks, etc | Event-driven | JSONL |
| Audio | Microphone (future) | 16kHz | WAV |
| Force/touch | Sensors (future) | 100 Hz | JSONL |
| IMU | Accelerometer (future) | 100 Hz | JSONL |

## Files to Create
- citizenry/recorder.py — TimelineRecorder, streams, session management
- citizenry/analyzer.py — offline analysis engine
- citizenry/annotator.py — video annotation overlay
- citizenry/static/recorder.html — recording controls in web dashboard
- citizenry/tests/test_recorder.py

## Acceptance Criteria
- "start recording" captures synchronized video + telemetry
- "stop recording" saves session to ~/.citizenry/recordings/
- "analyze session" runs offline analysis and produces results
- Web dashboard shows recording controls and session browser
- Calibration uses recorder automatically
