---
story_id: "LEARN-v1"
status: ready-for-dev
created: 2026-03-16
---

# Story: Universal Episode Recording + AI-Driven Improvement Loop

## Vision
Every action the robot takes is recorded as an episode. Claude can inspect any
episode, analyze performance, suggest improvements, and generate training data.
The robot gets better at everything it does — not just teleop.

## Architecture

### What Gets Recorded (ALL operations)
| Operation | Observation | State | Action | Label |
|-----------|-------------|-------|--------|-------|
| Teleop | camera frame | 6 joint positions | leader arm positions | "teleop" |
| Calibration | camera frame | 6 joint positions | calibration target | "calibration" |
| Task (wave) | camera frame | 6 joint positions | gesture trajectory | "basic_gesture/wave" |
| Task (pick) | camera frame | 6 joint positions | pick trajectory | "pick_and_place" |
| Reflex | camera frame | 6 joint positions + current | reflex response | "reflex/{type}" |
| Idle | camera frame | 6 joint positions | none (hold) | "idle" |

### Episode Format (LeRobot v3 compatible)
```
episode_NNNN/
  frames: [observation.image, observation.state, action, reward, done]
  metadata: {task, success, duration, citizen, timestamp}
```

Each frame:
- observation.image: camera RGB (480x640x3)
- observation.state: [pan, lift, elbow, wflex, wroll, gripper] raw positions
- observation.current: [6 current readings] mA
- action: [pan, lift, elbow, wflex, wroll, gripper] target positions
- reward: 1.0 on success, 0.0 on failure, partial for in-progress
- done: True on last frame of episode

### Claude Inspection API
The governor can ask Claude to analyze episodes:
- "analyze last episode" → load frames + telemetry, identify issues
- "why did that fail?" → compare failed episode to successful ones
- "improve pick and place" → analyze all pick episodes, suggest parameter changes
- "what did you learn?" → summarize insights across recent episodes

### Self-Improvement Loop
1. RECORD: Every operation auto-records an episode
2. STORE: Episodes saved to ~/.citizenry/episodes/ in LeRobot format
3. ANALYZE: After each episode, quick self-analysis (success rate, anomalies)
4. LEARN: Periodically batch-analyze episodes, update skill parameters
5. TRAIN: Export episodes to LeRobot dataset for model fine-tuning
6. DEPLOY: Load improved model/parameters, verify improvement

## Files
- citizenry/episode_recorder.py — universal episode recording
- citizenry/episode_analyzer.py — AI-driven episode analysis
- citizenry/learning_loop.py — self-improvement from episodes
