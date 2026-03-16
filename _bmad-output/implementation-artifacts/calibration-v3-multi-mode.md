---
story_id: "CAL-v3"
status: ready-for-dev
created: 2026-03-16
---

# Story: Multi-Mode Self-Calibration System

## User Story
As a president/governor, I want to choose between calibration methods (manual, camera-guided, current-sensing, gravity-aware staged) so that calibration works reliably regardless of arm starting position.

## The Problem
Arms start resting ON the table. Calibrating gravity-sensitive joints (shoulder_lift, elbow_flex) fails because the arm can't move — it's pressing against the surface. Need to lift the arm off the table first.

## 4 Calibration Modes

### Mode A: Manual Pre-Position
- User physically lifts arm to upright L-shape
- System reads current positions as starting point
- Proceeds with stall-detection from the safe position
- Most reliable, requires human touch

### Mode B: Camera-Guided
- Camera captures frame before each motor test
- Detects if arm is on the table (low vertical extent in frame)
- If on table → move shoulder_lift UP until camera sees arm rising
- Then proceed with stall detection
- Fully autonomous, needs camera

### Mode C: Current-Based Lift Detection
- Monitor motor current while slowly moving shoulder_lift UP
- Current spike = arm lifting off table, current drop = arm free
- Once free, record liftoff position
- Then calibrate all joints from safe upright position
- No camera needed

### Mode D: Gravity-Aware Staged (recommended)
- Stage 1: Lift shoulder_lift with high torque, monitor current for liftoff
- Stage 2: Once upright, fold elbow to reduce moment arm
- Stage 3: Calibrate each joint in safe order with pre-positioning
- Stage 4: Validate by moving to discovered centers
- Most robust, purely mechanical

## Files to Create/Modify
- `citizenry/self_calibration.py` — add CalibrationMode enum, all 4 modes
- `citizenry/pi_citizen.py` — accept mode parameter in self_calibrate task
- `citizenry/governor_cli.py` — mode selection in CLI
- `citizenry/static/dashboard.html` — calibration panel with mode buttons
- `citizenry/web_dashboard.py` — calibration API endpoints

## Acceptance Criteria
- `self calibrate` CLI command offers mode selection
- Mode D works without human intervention on table-resting arm
- Web dashboard shows calibration status + mode buttons
- Results saved to genome
- All 374 existing tests still pass
