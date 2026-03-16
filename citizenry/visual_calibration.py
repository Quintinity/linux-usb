"""Visual-First Self-Calibration — camera-guided joint limit discovery.

When servo position registers are unreliable under load (gravity-fighting
joints), the camera becomes the primary feedback sensor. The system:
1. Captures a baseline frame (arm at rest)
2. Moves a joint in one direction
3. Captures a new frame and measures movement via optical flow + contours
4. If movement detected → keep going; if not → stall/limit reached
5. Tries the other direction if first doesn't work
6. Uses the camera-verified positions to calibrate

Falls back to servo position registers for non-gravity joints where
the registers are reliable.
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np


MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]
MOTOR_IDS = {name: i + 1 for i, name in enumerate(MOTOR_NAMES)}

# Joints where position registers are unreliable under load
VISUAL_REQUIRED = {"shoulder_lift", "elbow_flex"}

# Joints where position registers work fine
REGISTER_RELIABLE = {"shoulder_pan", "wrist_flex", "wrist_roll", "gripper"}

# Calibration order: reliable joints first, visual joints last
VISUAL_CAL_ORDER = [
    "wrist_roll", "gripper", "wrist_flex", "shoulder_pan",  # Register-based
    "elbow_flex", "shoulder_lift",  # Camera-based
]


@dataclass
class VisualMotorLimits:
    """Limits discovered via visual feedback."""
    name: str
    motor_id: int
    min_position: int = 0
    max_position: int = 4095
    range: int = 4095
    center: int = 2048
    method: str = "register"  # "register", "visual", "full_rotation"
    calibrated: bool = False
    visual_confidence: float = 0.0  # How confident the visual detection was

    def to_dict(self) -> dict:
        return {
            "name": self.name, "id": self.motor_id,
            "min": self.min_position, "max": self.max_position,
            "range": self.range, "center": self.center,
            "method": self.method, "calibrated": self.calibrated,
        }


@dataclass
class VisualCalibrationResult:
    """Results of visual calibration."""
    motors: dict[str, VisualMotorLimits] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    duration_s: float = 0.0
    frames_captured: int = 0

    def to_dict(self) -> dict:
        return {
            "motors": {k: v.to_dict() for k, v in self.motors.items()},
            "duration_s": round(self.duration_s, 1),
            "frames_captured": self.frames_captured,
        }


# ── Visual Measurement Tools ─────────────────────────────────────────────────

class VisualFeedback:
    """Camera-based movement detection for calibration."""

    def __init__(self, camera_index: int = 0):
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.frame_count = 0
        self._prev_gray = None

    def capture(self) -> np.ndarray | None:
        """Capture a frame (flush buffer first for freshness)."""
        for _ in range(3):
            self.cap.read()
        ret, frame = self.cap.read()
        if ret:
            self.frame_count += 1
            return frame
        return None

    def measure_movement(self, before: np.ndarray, after: np.ndarray) -> dict:
        """Measure movement between two frames using multiple methods.

        Returns dict with:
            mean_diff: average pixel difference (0-255)
            optical_flow_magnitude: average optical flow magnitude
            contour_shift: shift in largest contour centroid (pixels)
            movement_direction: 'up', 'down', 'left', 'right', or 'none'
            confidence: 0-1 confidence in the measurement
        """
        if before is None or after is None:
            return {"mean_diff": 0, "optical_flow_magnitude": 0,
                    "contour_shift": 0, "movement_direction": "none", "confidence": 0}

        gray_before = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
        gray_after = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

        # Method 1: Mean pixel difference
        diff = cv2.absdiff(gray_before, gray_after)
        mean_diff = float(np.mean(diff))

        # Method 2: Optical flow (Farneback dense flow)
        flow_mag = 0.0
        flow_dir_y = 0.0
        try:
            flow = cv2.calcOpticalFlowFarneback(
                gray_before, gray_after, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
            mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            flow_mag = float(np.mean(mag))
            # Average vertical flow component (negative = upward in image)
            flow_dir_y = float(np.mean(flow[..., 1]))
        except Exception:
            pass

        # Method 3: Contour centroid tracking
        contour_shift = 0.0
        movement_direction = "none"
        try:
            # Find largest contour in the difference image
            _, thresh = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
            kernel = np.ones((5, 5), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                largest = max(contours, key=cv2.contourArea)
                M = cv2.moments(largest)
                if M["m00"] > 100:
                    cx = M["m10"] / M["m00"]
                    cy = M["m01"] / M["m00"]
                    # Compare to frame center to determine direction
                    h, w = gray_before.shape
                    if cy < h * 0.4:
                        movement_direction = "up"
                    elif cy > h * 0.6:
                        movement_direction = "down"
                    contour_shift = float(cv2.contourArea(largest))
        except Exception:
            pass

        # Determine direction from optical flow
        if flow_dir_y < -0.5:
            movement_direction = "up"
        elif flow_dir_y > 0.5:
            movement_direction = "down"

        # Confidence: combine all signals
        confidence = min(1.0, (mean_diff / 10.0 + flow_mag / 2.0) / 2.0)

        return {
            "mean_diff": round(mean_diff, 2),
            "optical_flow_magnitude": round(flow_mag, 3),
            "contour_shift": round(contour_shift, 0),
            "movement_direction": movement_direction,
            "flow_y": round(flow_dir_y, 3),
            "confidence": round(confidence, 3),
        }

    def is_arm_upright(self, frame: np.ndarray) -> float:
        """Estimate how upright the arm is (0=horizontal, 1=vertical).

        Uses edge detection — vertical edges in upper frame = upright arm.
        """
        if frame is None:
            return 0.0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        h, w = edges.shape

        # Count edges in upper vs lower half
        upper_edges = np.mean(edges[:h//2, :])
        lower_edges = np.mean(edges[h//2:, :])

        # More edges in upper half = arm is upright
        total = upper_edges + lower_edges + 0.1
        return float(upper_edges / total)

    def release(self):
        if self.cap:
            self.cap.release()


# ── Servo Helpers ─────────────────────────────────────────────────────────────

def _read_pos(ph, port, mid):
    val, r, _ = ph.read2ByteTxRx(port, mid, 56)
    return val if r == 0 and val > 0 else -1

def _write_pos(ph, port, mid, pos):
    ph.write2ByteTxRx(port, mid, 42, max(0, min(4095, pos)))

def _enable(ph, port, mid):
    ph.write1ByteTxRx(port, mid, 40, 1)

def _disable(ph, port, mid):
    ph.write1ByteTxRx(port, mid, 40, 0)

def _boost_torque(ph, port, mid):
    """Temporarily boost torque for gravity-fighting joints."""
    _disable(ph, port, mid)
    time.sleep(0.05)
    ph.write2ByteTxRx(port, mid, 16, 900)   # Max torque 90%
    ph.write2ByteTxRx(port, mid, 28, 600)   # Protection current 600mA
    ph.write1ByteTxRx(port, mid, 36, 90)    # Overload torque 90%
    ph.write1ByteTxRx(port, mid, 35, 250)   # Protection time max

def _restore_torque(ph, port, mid):
    """Restore default torque settings."""
    _disable(ph, port, mid)
    time.sleep(0.05)
    ph.write2ByteTxRx(port, mid, 16, 500)
    ph.write2ByteTxRx(port, mid, 28, 250)


# ── Visual Calibration for Gravity Joints ─────────────────────────────────────

def _visual_find_limits(ph, port, motor_id: int, motor_name: str,
                        vis: VisualFeedback, log_fn=None) -> VisualMotorLimits:
    """Find joint limits using camera feedback instead of position registers.

    Strategy:
    1. Boost torque for this joint
    2. Capture baseline frame
    3. Try both directions with big steps
    4. Pick the direction with more visual movement (= arm moving up/correctly)
    5. Keep moving in that direction until camera shows no more movement
    6. That's the limit for this direction
    7. Return to start, do the other direction
    """
    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log(f"  [VISUAL] {motor_name} — camera-guided limit finding")

    _boost_torque(ph, port, motor_id)
    _enable(ph, port, motor_id)
    time.sleep(0.3)

    start_pos = _read_pos(ph, port, motor_id)
    if start_pos < 0:
        start_pos = 2048
    _log(f"    start: {start_pos}")

    limits = VisualMotorLimits(name=motor_name, motor_id=motor_id, method="visual")

    # Capture baseline
    baseline = vis.capture()

    # === Find which direction makes the arm move more ===
    step_size = 300
    best_direction = 0
    best_movement = 0

    for direction in [1, -1]:
        target = start_pos + (step_size * direction)
        target = max(200, min(3800, target))

        _write_pos(ph, port, motor_id, target)
        time.sleep(1.0)

        frame = vis.capture()
        measurement = vis.measure_movement(baseline, frame)
        _log(f"    dir={'+' if direction > 0 else '-'}: diff={measurement['mean_diff']:.1f} "
             f"flow={measurement['optical_flow_magnitude']:.2f} dir={measurement['movement_direction']}")

        if measurement["mean_diff"] > best_movement:
            best_movement = measurement["mean_diff"]
            best_direction = direction

        # Return to start
        _write_pos(ph, port, motor_id, start_pos)
        time.sleep(0.8)

    if best_direction == 0:
        best_direction = -1  # Default: try negative first
    _log(f"    best direction: {'positive' if best_direction > 0 else 'negative'} (movement={best_movement:.1f})")

    # === Find limit in the BEST direction ===
    _log(f"    finding limit in {'positive' if best_direction > 0 else 'negative'} direction...")
    current_pos = start_pos
    prev_frame = vis.capture()
    limit_pos = start_pos
    step = 200 * best_direction
    no_movement_count = 0

    for i in range(20):
        target = current_pos + step
        target = max(100, min(3900, target))

        _write_pos(ph, port, motor_id, target)
        time.sleep(0.8)

        frame = vis.capture()
        measurement = vis.measure_movement(prev_frame, frame)

        actual = _read_pos(ph, port, motor_id)
        _log(f"      [{i}] target={target} actual={actual} diff={measurement['mean_diff']:.1f} "
             f"flow={measurement['optical_flow_magnitude']:.2f}")

        if measurement["mean_diff"] < 1.5 and measurement["optical_flow_magnitude"] < 0.3:
            no_movement_count += 1
            if no_movement_count >= 2:
                limit_pos = actual if actual > 0 else target
                _log(f"      VISUAL STALL at ~{limit_pos}")
                break
        else:
            no_movement_count = 0
            limit_pos = actual if actual > 0 else target
            current_pos = target

        prev_frame = frame

    if best_direction > 0:
        limits.max_position = limit_pos
    else:
        limits.min_position = limit_pos

    # Return to start
    _write_pos(ph, port, motor_id, start_pos)
    time.sleep(1.0)

    # === Find limit in the OPPOSITE direction ===
    opp_direction = -best_direction
    _log(f"    finding limit in {'positive' if opp_direction > 0 else 'negative'} direction...")
    current_pos = start_pos
    prev_frame = vis.capture()
    step = 200 * opp_direction
    no_movement_count = 0

    for i in range(20):
        target = current_pos + step
        target = max(100, min(3900, target))

        _write_pos(ph, port, motor_id, target)
        time.sleep(0.8)

        frame = vis.capture()
        measurement = vis.measure_movement(prev_frame, frame)

        actual = _read_pos(ph, port, motor_id)
        _log(f"      [{i}] target={target} actual={actual} diff={measurement['mean_diff']:.1f}")

        if measurement["mean_diff"] < 1.5 and measurement["optical_flow_magnitude"] < 0.3:
            no_movement_count += 1
            if no_movement_count >= 2:
                pos = actual if actual > 0 else target
                if opp_direction > 0:
                    limits.max_position = pos
                else:
                    limits.min_position = pos
                _log(f"      VISUAL STALL at ~{pos}")
                break
        else:
            no_movement_count = 0
            if actual > 0:
                current_pos = actual
            else:
                current_pos = target

        prev_frame = frame

    # Compute range
    if limits.max_position > limits.min_position:
        limits.range = limits.max_position - limits.min_position
        limits.center = (limits.min_position + limits.max_position) // 2
        limits.calibrated = True
        limits.visual_confidence = min(1.0, best_movement / 10.0)
    else:
        limits.center = start_pos
        _log(f"    WARNING: could not determine range visually")

    # Return to center
    _write_pos(ph, port, motor_id, limits.center)
    time.sleep(0.5)

    _restore_torque(ph, port, motor_id)
    _disable(ph, port, motor_id)

    _log(f"    result: {limits.min_position} → {limits.max_position} (range={limits.range}, method={limits.method})")
    return limits


# ── Register-Based Calibration for Reliable Joints ────────────────────────────

def _register_find_limits(ph, port, motor_id: int, motor_name: str,
                          log_fn=None) -> VisualMotorLimits:
    """Find limits using servo position register (reliable for non-gravity joints)."""
    def _log(msg):
        if log_fn:
            log_fn(msg)

    if motor_name == "wrist_roll":
        _log(f"  [REG] wrist_roll — full rotation")
        return VisualMotorLimits(name=motor_name, motor_id=motor_id,
                                 min_position=0, max_position=4095, range=4095,
                                 center=2048, method="full_rotation", calibrated=True)

    _log(f"  [REG] {motor_name} — register-based stall detection")
    _enable(ph, port, motor_id)
    time.sleep(0.2)

    start = _read_pos(ph, port, motor_id)
    if start < 0:
        start = 2048
    limits = VisualMotorLimits(name=motor_name, motor_id=motor_id, method="register")

    step = 50
    stall_threshold = 15

    # Find MIN
    current = start
    stalls = 0
    for _ in range(80):
        target = current - step
        if target < 0:
            limits.min_position = 0
            break
        _write_pos(ph, port, motor_id, target)
        time.sleep(0.12)
        actual = _read_pos(ph, port, motor_id)
        if actual < 0:
            continue
        if abs(actual - current) < stall_threshold:
            stalls += 1
            if stalls >= 3:
                limits.min_position = actual
                _log(f"    MIN stall at {actual}")
                break
        else:
            stalls = 0
            current = actual
    else:
        limits.min_position = current

    _write_pos(ph, port, motor_id, start)
    time.sleep(0.8)

    # Find MAX
    current = start
    stalls = 0
    for _ in range(80):
        target = current + step
        if target > 4095:
            limits.max_position = 4095
            break
        _write_pos(ph, port, motor_id, target)
        time.sleep(0.12)
        actual = _read_pos(ph, port, motor_id)
        if actual < 0:
            continue
        if abs(actual - current) < stall_threshold:
            stalls += 1
            if stalls >= 3:
                limits.max_position = actual
                _log(f"    MAX stall at {actual}")
                break
        else:
            stalls = 0
            current = actual
    else:
        limits.max_position = current

    if limits.max_position > limits.min_position:
        limits.range = limits.max_position - limits.min_position
        limits.center = (limits.min_position + limits.max_position) // 2
        limits.calibrated = True

    _write_pos(ph, port, motor_id, limits.center)
    time.sleep(0.3)
    _disable(ph, port, motor_id)

    _log(f"    result: {limits.min_position} → {limits.max_position} (range={limits.range})")
    return limits


# ── Main Entry Point ──────────────────────────────────────────────────────────

def visual_self_calibrate(bus, camera_index: int = 0, log_fn=None) -> VisualCalibrationResult:
    """Full visual-first self-calibration.

    Uses camera for gravity-sensitive joints (shoulder_lift, elbow_flex).
    Uses servo registers for reliable joints (shoulder_pan, wrist, gripper).
    """
    ph = bus.packet_handler
    port = bus.port_handler
    result = VisualCalibrationResult()
    t0 = time.time()

    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log("=== Visual-First Self-Calibration ===\n")

    # Open camera
    vis = VisualFeedback(camera_index)
    if not vis.cap.isOpened():
        _log("ERROR: Camera not available")
        vis.release()
        return result

    # Enable all motors
    _log("Enabling motors...")
    for mid in range(1, 7):
        _enable(ph, port, mid)
    time.sleep(0.5)

    # First: lift arm off table using visual feedback
    _log("\n--- Phase 1: Lift arm off table ---")
    shoulder_id = MOTOR_IDS["shoulder_lift"]
    _boost_torque(ph, port, shoulder_id)
    _boost_torque(ph, port, MOTOR_IDS["elbow_flex"])
    _enable(ph, port, shoulder_id)
    _enable(ph, port, MOTOR_IDS["elbow_flex"])
    time.sleep(0.3)

    baseline = vis.capture()
    start_pos = _read_pos(ph, port, shoulder_id)
    if start_pos < 0:
        start_pos = 1500

    # Try both directions to lift
    for direction in [-1, 1]:
        _log(f"  Trying {'negative' if direction < 0 else 'positive'} direction to lift...")
        target = start_pos + (500 * direction)
        target = max(300, min(3500, target))
        _write_pos(ph, port, shoulder_id, target)
        time.sleep(1.5)

        frame = vis.capture()
        measurement = vis.measure_movement(baseline, frame)
        _log(f"    movement: diff={measurement['mean_diff']:.1f} direction={measurement['movement_direction']}")

        if measurement["mean_diff"] > 5 and measurement["movement_direction"] == "up":
            _log(f"    Arm is lifting! Continuing...")
            # Keep going in this direction
            for _ in range(5):
                target += 300 * direction
                target = max(300, min(3500, target))
                _write_pos(ph, port, shoulder_id, target)
                time.sleep(0.8)
                f2 = vis.capture()
                m2 = vis.measure_movement(frame, f2)
                if m2["mean_diff"] < 1.5:
                    break
                frame = f2
            break
        else:
            # Return and try other direction
            _write_pos(ph, port, shoulder_id, start_pos)
            time.sleep(1)

    # Fold elbow
    _log("\n  Folding elbow for safety...")
    elbow_id = MOTOR_IDS["elbow_flex"]
    elbow_pos = _read_pos(ph, port, elbow_id)
    if elbow_pos > 0:
        _write_pos(ph, port, elbow_id, 3000)
        time.sleep(1)

    # Phase 2: Calibrate reliable joints (register-based)
    _log("\n--- Phase 2: Register-based joints ---")
    for name in VISUAL_CAL_ORDER:
        if name in VISUAL_REQUIRED:
            continue
        mid = MOTOR_IDS[name]
        limits = _register_find_limits(ph, port, mid, name, log_fn=_log)
        result.motors[name] = limits

    # Phase 3: Calibrate gravity joints (visual-based)
    _log("\n--- Phase 3: Visual-based gravity joints ---")
    for name in VISUAL_CAL_ORDER:
        if name not in VISUAL_REQUIRED:
            continue
        mid = MOTOR_IDS[name]
        limits = _visual_find_limits(ph, port, mid, name, vis, log_fn=_log)
        result.motors[name] = limits

    # Phase 4: Return to centers
    _log("\n--- Phase 4: Returning to centers ---")
    for name, lim in result.motors.items():
        mid = MOTOR_IDS[name]
        _enable(ph, port, mid)
        _write_pos(ph, port, mid, lim.center)
    time.sleep(1)

    for mid in range(1, 7):
        _restore_torque(ph, port, mid)
        _disable(ph, port, mid)

    vis.release()

    result.duration_s = time.time() - t0
    result.frames_captured = vis.frame_count

    _log(f"\n=== RESULTS ===")
    for name in VISUAL_CAL_ORDER:
        if name in result.motors:
            m = result.motors[name]
            s = "✓" if m.calibrated else "✗"
            _log(f"  {s} {name:<16} {m.min_position:>5} → {m.max_position:<5} "
                 f"(range={m.range}, method={m.method})")
    _log(f"\nCompleted in {result.duration_s:.1f}s, {result.frames_captured} frames captured")

    return result
