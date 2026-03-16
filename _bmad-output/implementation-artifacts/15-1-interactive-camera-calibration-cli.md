---
story_id: "15.1"
story_key: "15-1-interactive-camera-calibration-cli"
epic: "Epic 15: Camera Calibration Interactive Flow"
status: ready-for-dev
created: 2026-03-16
---

# Story: Interactive Camera Calibration CLI

## User Story
As a governor operator, I want to run `calibrate camera` in the CLI and be guided through camera placement and calibration, so that camera-guided pick-and-place uses accurate pixel→servo mapping.

## Acceptance Criteria
- `calibrate camera` launches interactive calibration in governor CLI
- Phase 1: camera placement evaluation — guides user to adjust camera if needed
- Phase 2: arm moves to 10 poses, camera detects gripper tip at each via frame differencing
- Phase 3: homography fit with RANSAC, reports inlier count + reprojection error
- Phase 4: validation on 3 held-out poses, reports accuracy
- Phase 5: saves calibration to ~/.citizenry/calibration.calibration.json
- `check calibration` shows age, error, and staleness warning

## Technical Requirements

### Files to modify
- `citizenry/governor_cli.py` — replace placeholder calibration handler with real async flow
- `citizenry/calibration.py` — all primitives exist (GripperDetector, CameraPlacementGuide, fit_homography, apply_homography, validation, persistence)
- `citizenry/visual_tasks.py` — load_calibration_transform() already implemented

### Existing code to reuse
- `calibration.GripperDetector.detect()` — frame differencing, returns (px, py)
- `calibration.CameraPlacementGuide.evaluate()` — returns PlacementScore
- `calibration.fit_homography()` — RANSAC homography
- `calibration.compute_validation_error()` — held-out validation
- `calibration.save_calibration()` / `load_calibration()` — persistence
- `calibration.CALIBRATION_POSES` — 10 poses, `CORNER_POSES` — 4 corners, `VALIDATION_POSES` — 3 validation
- `pi_citizen._smooth_move()` — smooth arm movement

### Architecture constraints
- Camera is on the Pi, arm is on the Pi — calibration must be orchestrated via citizenry protocol
- Governor sends PROPOSE tasks to arm (move to pose) and camera (capture frame)
- Or: run calibration directly on the Pi where both are local
- Simplest: add a calibration endpoint to PiCitizen that handles the full procedure locally

### Key decision
The camera and arm are both on the Pi. The governor CLI is on the Surface. Two approaches:
1. **Governor-orchestrated**: governor sends marketplace tasks to arm+camera for each calibration point (complex, slow)
2. **Pi-local calibration**: add a "calibrate" task that the Pi handles entirely locally, reports result to governor (simple, fast)

**Recommend approach 2**: Pi runs calibration locally (it has both arm and camera), sends the CalibrationResult back to the governor via REPORT.

## Testing
- Existing tests: 25 calibration tests covering gripper detection, homography, placement scoring
- No new tests needed for the integration (it's wiring existing pieces)
- Manual verification: run on real hardware
