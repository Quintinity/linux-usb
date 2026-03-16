"""Self-Calibration v3 — Multi-mode joint limit discovery.

4 calibration modes:
  A) Manual: user lifts arm, system reads positions, then auto-calibrates
  B) Camera-guided: camera detects arm position, guides liftoff
  C) Current-sensing: monitor current for liftoff signature
  D) Gravity-aware staged: lift → fold → calibrate → validate (recommended)

All modes end with stall-detection per joint to find physical limits.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]
MOTOR_IDS = {name: i + 1 for i, name in enumerate(MOTOR_NAMES)}


class CalibrationMode(Enum):
    MANUAL = "manual"           # A: User lifts arm first
    CAMERA_GUIDED = "camera"    # B: Camera detects table contact
    CURRENT_SENSING = "current" # C: Current-based liftoff detection
    GRAVITY_STAGED = "staged"   # D: Automatic staged lift + calibrate


# Calibration order: easiest → hardest
CALIBRATION_ORDER = [
    "wrist_roll", "gripper", "wrist_flex",
    "shoulder_pan", "elbow_flex", "shoulder_lift",
]

FULL_ROTATION_MOTORS = {"wrist_roll"}
GRAVITY_SENSITIVE = {"shoulder_lift", "elbow_flex"}

# Safe pre-positions per motor test (arm held upright)
SAFE_POSITIONS = {
    "wrist_roll": {"shoulder_pan": 2048, "shoulder_lift": 1800, "elbow_flex": 2500, "wrist_flex": 2048, "gripper": 2048},
    "gripper": {"shoulder_pan": 2048, "shoulder_lift": 1800, "elbow_flex": 2500, "wrist_flex": 2048, "wrist_roll": 2048},
    "wrist_flex": {"shoulder_pan": 2048, "shoulder_lift": 1800, "elbow_flex": 2200, "wrist_roll": 2048, "gripper": 2048},
    "shoulder_pan": {"shoulder_lift": 1600, "elbow_flex": 2800, "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 2048},
    "elbow_flex": {"shoulder_pan": 2048, "shoulder_lift": 2200, "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 2048},
    "shoulder_lift": {"shoulder_pan": 2048, "elbow_flex": 3200, "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 2048},
}


@dataclass
class MotorLimits:
    """Discovered physical limits for a single motor."""
    name: str
    motor_id: int
    min_position: int = 0
    max_position: int = 4095
    range: int = 4095
    center: int = 2048
    start_position: int = 2048
    min_stall: bool = False
    max_stall: bool = False
    calibrated: bool = False

    def to_dict(self) -> dict:
        return {"name": self.name, "id": self.motor_id, "min": self.min_position,
                "max": self.max_position, "range": self.range, "center": self.center,
                "calibrated": self.calibrated}


@dataclass
class SelfCalibrationResult:
    """Results of a full self-calibration run."""
    motors: dict[str, MotorLimits] = field(default_factory=dict)
    mode: str = "staged"
    timestamp: float = field(default_factory=time.time)
    duration_s: float = 0.0
    liftoff_position: int = 0
    liftoff_current_ma: float = 0.0

    def to_dict(self) -> dict:
        return {
            "motors": {k: v.to_dict() for k, v in self.motors.items()},
            "mode": self.mode, "timestamp": self.timestamp,
            "duration_s": round(self.duration_s, 1),
            "liftoff_position": self.liftoff_position,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_pos(ph, port, motor_id: int) -> int:
    val, r, _ = ph.read2ByteTxRx(port, motor_id, 56)
    return val if r == 0 else -1

def _read_current(ph, port, motor_id: int) -> float:
    val, r, _ = ph.read2ByteTxRx(port, motor_id, 69)
    if r != 0:
        return 0.0
    magnitude = val & 0x7FFF
    return magnitude * 6.5

def _read_moving(ph, port, motor_id: int) -> bool:
    val, r, _ = ph.read1ByteTxRx(port, motor_id, 66)
    return val == 1 if r == 0 else False

def _write_pos(ph, port, motor_id: int, position: int):
    ph.write2ByteTxRx(port, motor_id, 42, max(0, min(4095, position)))

def _enable_torque(ph, port, motor_id: int):
    ph.write1ByteTxRx(port, motor_id, 40, 1)

def _disable_torque(ph, port, motor_id: int):
    ph.write1ByteTxRx(port, motor_id, 40, 0)

def _enable_all(ph, port):
    for mid in range(1, 7):
        _enable_torque(ph, port, mid)

def _disable_all(ph, port):
    for mid in range(1, 7):
        _disable_torque(ph, port, mid)

def _smooth_move_to(ph, port, target: dict, steps: int = 10, delay: float = 0.08):
    """Smoothly move all motors to target positions."""
    # Read current positions
    current = {}
    for name, mid in MOTOR_IDS.items():
        pos = _read_pos(ph, port, mid)
        current[name] = pos if pos >= 0 else target.get(name, 2048)

    for step in range(1, steps + 1):
        t = step / steps
        for name, mid in MOTOR_IDS.items():
            if name in target:
                interp = int(current[name] + (target[name] - current[name]) * t)
                _write_pos(ph, port, mid, interp)
        time.sleep(delay)


# ── Mode D: Gravity-Aware Staged Calibration (recommended) ────────────────────

def _lift_arm_off_table(ph, port, log_fn=None) -> tuple[int, float]:
    """Stage 1: Lift the arm off the table by driving shoulder_lift UP.

    Monitors current for the liftoff signature:
    - Current rises as servo pushes against table
    - Current peaks at liftoff (full arm weight on servo)
    - Current drops slightly as arm momentum stabilizes

    Returns (liftoff_position, peak_current_ma)
    """
    def _log(msg):
        if log_fn:
            log_fn(msg)

    shoulder_id = MOTOR_IDS["shoulder_lift"]

    # Read starting position
    start_pos = _read_pos(ph, port, shoulder_id)
    _log(f"  lift: starting at {start_pos}")

    # Enable torque on shoulder_lift only first
    _enable_torque(ph, port, shoulder_id)
    time.sleep(0.3)

    # Read baseline current
    baseline_current = _read_current(ph, port, shoulder_id)
    _log(f"  lift: baseline current = {baseline_current:.0f}mA")

    # Slowly move shoulder_lift in the "up" direction
    # For SO-101: LOWER position number = arm moves UP (toward vertical)
    current_pos = start_pos
    peak_current = baseline_current
    liftoff_pos = start_pos
    liftoff_detected = False
    readings = []

    step = -30  # Move up (decrease position)
    for i in range(80):
        target = current_pos + step
        if target < 500:  # Safety floor
            break

        _write_pos(ph, port, shoulder_id, target)
        time.sleep(0.1)

        actual = _read_pos(ph, port, shoulder_id)
        current_ma = _read_current(ph, port, shoulder_id)
        readings.append(current_ma)

        if current_ma > peak_current:
            peak_current = current_ma

        # Liftoff detection: after seeing high current, if current drops 30%+
        if len(readings) >= 5 and not liftoff_detected:
            recent_avg = sum(readings[-3:]) / 3
            older_avg = sum(readings[-6:-3]) / 3 if len(readings) >= 6 else baseline_current

            if older_avg > baseline_current * 1.5 and recent_avg < older_avg * 0.8:
                liftoff_detected = True
                liftoff_pos = actual
                _log(f"  lift: LIFTOFF at position {actual} (current dropped from {older_avg:.0f} to {recent_avg:.0f}mA)")

        # Also detect by position movement — if we've moved 200+ ticks, arm is probably up
        if abs(actual - start_pos) > 300:
            if not liftoff_detected:
                liftoff_detected = True
                liftoff_pos = actual
                _log(f"  lift: arm moved 300+ ticks — assuming lifted (pos={actual})")
            break

        current_pos = actual

        if i % 10 == 0:
            _log(f"  lift: pos={actual} current={current_ma:.0f}mA")

    if not liftoff_detected:
        liftoff_pos = current_pos
        _log(f"  lift: liftoff not clearly detected, using current pos {current_pos}")

    _log(f"  lift: complete. liftoff={liftoff_pos}, peak_current={peak_current:.0f}mA")
    return liftoff_pos, peak_current


def _fold_elbow_for_safety(ph, port, log_fn=None):
    """Stage 2: Fold the elbow to reduce moment arm."""
    def _log(msg):
        if log_fn:
            log_fn(msg)

    elbow_id = MOTOR_IDS["elbow_flex"]
    _enable_torque(ph, port, elbow_id)
    time.sleep(0.2)

    # Fold elbow (higher position = more folded for SO-101)
    target = 3000
    current = _read_pos(ph, port, elbow_id)
    _log(f"  fold: elbow {current} → {target}")

    steps = 15
    for i in range(1, steps + 1):
        interp = int(current + (target - current) * (i / steps))
        _write_pos(ph, port, elbow_id, interp)
        time.sleep(0.06)

    time.sleep(0.3)
    _log(f"  fold: elbow folded to {_read_pos(ph, port, elbow_id)}")


def calibrate_staged(bus, log_fn=None) -> SelfCalibrationResult:
    """Mode D: Gravity-aware staged calibration.

    Stage 1: Lift arm off table
    Stage 2: Fold elbow for safety
    Stage 3: Calibrate each joint with pre-positioning
    Stage 4: Return to centers
    """
    ph = bus.packet_handler
    port = bus.port_handler
    result = SelfCalibrationResult(mode="staged")
    t0 = time.time()

    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log("=== MODE D: Gravity-Aware Staged Calibration ===")

    # Stage 1: Lift
    _log("\nStage 1: Lifting arm off table...")
    _enable_all(ph, port)
    time.sleep(0.3)
    liftoff_pos, peak_current = _lift_arm_off_table(ph, port, log_fn=_log)
    result.liftoff_position = liftoff_pos
    result.liftoff_current_ma = peak_current

    # Stage 2: Fold elbow
    _log("\nStage 2: Folding elbow for safety...")
    _fold_elbow_for_safety(ph, port, log_fn=_log)

    # Stage 3: Calibrate each motor
    _log("\nStage 3: Calibrating motors...")
    for name in CALIBRATION_ORDER:
        mid = MOTOR_IDS[name]
        _log(f"\n  [{CALIBRATION_ORDER.index(name)+1}/{len(CALIBRATION_ORDER)}] {name}...")

        # Pre-position other motors
        safe = SAFE_POSITIONS.get(name, {})
        if safe:
            _smooth_move_to(ph, port, safe)
            time.sleep(0.3)

        limits = _find_motor_limits(ph, port, mid, name, log_fn=_log)
        result.motors[name] = limits

    # Stage 4: Return to centers
    _log("\nStage 4: Returning to centers...")
    centers = {name: lim.center for name, lim in result.motors.items()}
    _smooth_move_to(ph, port, centers, steps=15, delay=0.06)
    time.sleep(0.5)
    _disable_all(ph, port)

    result.duration_s = time.time() - t0
    _log(f"\nCalibration complete in {result.duration_s:.1f}s")
    _print_results(result, _log)
    return result


# ── Mode C: Current-Sensing Calibration ───────────────────────────────────────

def calibrate_current_sensing(bus, log_fn=None) -> SelfCalibrationResult:
    """Mode C: Lift detection via current monitoring, then calibrate."""
    ph = bus.packet_handler
    port = bus.port_handler
    result = SelfCalibrationResult(mode="current")
    t0 = time.time()

    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log("=== MODE C: Current-Sensing Calibration ===")
    _enable_all(ph, port)
    time.sleep(0.3)

    # Same lift procedure as Mode D
    _log("\nLifting arm using current detection...")
    liftoff_pos, peak_current = _lift_arm_off_table(ph, port, log_fn=_log)
    result.liftoff_position = liftoff_pos

    _log("\nFolding elbow...")
    _fold_elbow_for_safety(ph, port, log_fn=_log)

    _log("\nCalibrating motors...")
    for name in CALIBRATION_ORDER:
        mid = MOTOR_IDS[name]
        _log(f"\n  {name}...")
        safe = SAFE_POSITIONS.get(name, {})
        if safe:
            _smooth_move_to(ph, port, safe)
            time.sleep(0.3)
        result.motors[name] = _find_motor_limits(ph, port, mid, name, log_fn=_log)

    centers = {name: lim.center for name, lim in result.motors.items()}
    _smooth_move_to(ph, port, centers, steps=15, delay=0.06)
    _disable_all(ph, port)

    result.duration_s = time.time() - t0
    _print_results(result, _log)
    return result


# ── Mode B: Camera-Guided Calibration ─────────────────────────────────────────

def calibrate_camera_guided(bus, camera_index: int = 0, log_fn=None) -> SelfCalibrationResult:
    """Mode B: Camera watches the arm during calibration."""
    ph = bus.packet_handler
    port = bus.port_handler
    result = SelfCalibrationResult(mode="camera")
    t0 = time.time()

    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log("=== MODE B: Camera-Guided Calibration ===")

    try:
        import cv2
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            _log("Camera not available — falling back to Mode D (staged)")
            cap = None
    except ImportError:
        _log("OpenCV not available — falling back to Mode D (staged)")
        cap = None

    _enable_all(ph, port)
    time.sleep(0.3)

    if cap:
        # Capture frame before lifting
        ret, frame_before = cap.read()
        _log(f"  Camera captured pre-lift frame")

        # Lift arm
        _log("\nLifting arm...")
        liftoff_pos, peak_current = _lift_arm_off_table(ph, port, log_fn=_log)
        result.liftoff_position = liftoff_pos

        # Capture frame after lifting
        time.sleep(0.5)
        ret, frame_after = cap.read()
        if ret and frame_before is not None:
            # Compare frames to verify arm moved
            import numpy as np
            diff = cv2.absdiff(frame_before, frame_after)
            movement = np.mean(diff)
            _log(f"  Camera verified arm movement: diff={movement:.1f}")
            if movement < 5:
                _log(f"  WARNING: Low movement detected — arm may not have lifted properly")

        cap.release()
    else:
        _lift_arm_off_table(ph, port, log_fn=_log)

    _fold_elbow_for_safety(ph, port, log_fn=_log)

    _log("\nCalibrating motors...")
    for name in CALIBRATION_ORDER:
        mid = MOTOR_IDS[name]
        _log(f"\n  {name}...")
        safe = SAFE_POSITIONS.get(name, {})
        if safe:
            _smooth_move_to(ph, port, safe)
            time.sleep(0.3)
        result.motors[name] = _find_motor_limits(ph, port, mid, name, log_fn=_log)

    centers = {name: lim.center for name, lim in result.motors.items()}
    _smooth_move_to(ph, port, centers, steps=15, delay=0.06)
    _disable_all(ph, port)

    result.duration_s = time.time() - t0
    _print_results(result, _log)
    return result


# ── Mode A: Manual Pre-Position ───────────────────────────────────────────────

def calibrate_manual(bus, log_fn=None) -> SelfCalibrationResult:
    """Mode A: User physically positions the arm first.

    Disables torque so user can move the arm, then reads positions
    as the starting point for stall detection.
    """
    ph = bus.packet_handler
    port = bus.port_handler
    result = SelfCalibrationResult(mode="manual")
    t0 = time.time()

    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log("=== MODE A: Manual Pre-Position ===")
    _log("Please lift the arm to an upright L-shape position.")
    _log("Shoulder pointing up, elbow at 90 degrees.")
    _log("Waiting 10 seconds for you to position the arm...")

    _disable_all(ph, port)
    time.sleep(10)  # Give user time

    # Read the manual position
    _log("\nReading manual positions...")
    for name, mid in MOTOR_IDS.items():
        pos = _read_pos(ph, port, mid)
        _log(f"  {name}: {pos}")

    _enable_all(ph, port)
    time.sleep(0.3)

    _log("\nCalibrating motors...")
    for name in CALIBRATION_ORDER:
        mid = MOTOR_IDS[name]
        _log(f"\n  {name}...")
        safe = SAFE_POSITIONS.get(name, {})
        if safe:
            _smooth_move_to(ph, port, safe)
            time.sleep(0.3)
        result.motors[name] = _find_motor_limits(ph, port, mid, name, log_fn=_log)

    centers = {name: lim.center for name, lim in result.motors.items()}
    _smooth_move_to(ph, port, centers, steps=15, delay=0.06)
    _disable_all(ph, port)

    result.duration_s = time.time() - t0
    _print_results(result, _log)
    return result


# ── Core: Stall-Detection per Motor ──────────────────────────────────────────

def _find_motor_limits(ph, port, motor_id: int, motor_name: str,
                       step: int = 50, stall_threshold: int = 15,
                       stall_count: int = 3, max_steps: int = 80,
                       step_delay: float = 0.12, log_fn=None) -> MotorLimits:
    """Find physical limits by moving until stall."""
    def _log(msg):
        if log_fn:
            log_fn(msg)

    if motor_name in FULL_ROTATION_MOTORS:
        _log(f"    {motor_name}: full rotation (0-4095)")
        return MotorLimits(name=motor_name, motor_id=motor_id, min_position=0,
                          max_position=4095, range=4095, center=2048, calibrated=True)

    if motor_name in GRAVITY_SENSITIVE:
        step = 40
        step_delay = 0.15
        stall_threshold = 20

    pos_raw = _read_pos(ph, port, motor_id)
    if pos_raw < 0:
        return MotorLimits(name=motor_name, motor_id=motor_id)

    limits = MotorLimits(name=motor_name, motor_id=motor_id, start_position=pos_raw)
    _enable_torque(ph, port, motor_id)
    time.sleep(0.2)

    # Find MIN
    current = pos_raw
    stalls = 0
    for i in range(max_steps):
        target = current - step
        if target < 0:
            limits.min_position = 0
            limits.min_stall = True
            break
        _write_pos(ph, port, motor_id, target)
        time.sleep(step_delay)
        actual = _read_pos(ph, port, motor_id)
        if actual < 0:
            continue
        moving = _read_moving(ph, port, motor_id)
        if abs(actual - current) < stall_threshold and not moving:
            stalls += 1
            if stalls >= stall_count:
                limits.min_position = actual
                limits.min_stall = True
                _log(f"    MIN stall at {actual}")
                break
        else:
            stalls = 0
            current = actual
    else:
        limits.min_position = current

    _write_pos(ph, port, motor_id, pos_raw)
    time.sleep(0.8)

    # Find MAX
    current = pos_raw
    stalls = 0
    for i in range(max_steps):
        target = current + step
        if target > 4095:
            limits.max_position = 4095
            limits.max_stall = True
            break
        _write_pos(ph, port, motor_id, target)
        time.sleep(step_delay)
        actual = _read_pos(ph, port, motor_id)
        if actual < 0:
            continue
        moving = _read_moving(ph, port, motor_id)
        if abs(actual - current) < stall_threshold and not moving:
            stalls += 1
            if stalls >= stall_count:
                limits.max_position = actual
                limits.max_stall = True
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
    else:
        limits.range = abs(limits.max_position - limits.min_position)
        limits.center = pos_raw
        _log(f"    WARNING: unexpected range")

    _write_pos(ph, port, motor_id, limits.center)
    time.sleep(0.3)
    _disable_torque(ph, port, motor_id)

    _log(f"    result: {limits.min_position} → {limits.max_position} (range={limits.range})")
    return limits


# ── Entry Point ───────────────────────────────────────────────────────────────

def self_calibrate_all(bus, mode: CalibrationMode = CalibrationMode.GRAVITY_STAGED,
                       camera_index: int = 0, log_fn=None) -> SelfCalibrationResult:
    """Run self-calibration in the specified mode."""
    if mode == CalibrationMode.GRAVITY_STAGED:
        return calibrate_staged(bus, log_fn=log_fn)
    elif mode == CalibrationMode.CURRENT_SENSING:
        return calibrate_current_sensing(bus, log_fn=log_fn)
    elif mode == CalibrationMode.CAMERA_GUIDED:
        return calibrate_camera_guided(bus, camera_index=camera_index, log_fn=log_fn)
    elif mode == CalibrationMode.MANUAL:
        return calibrate_manual(bus, log_fn=log_fn)
    else:
        return calibrate_staged(bus, log_fn=log_fn)


def _print_results(result: SelfCalibrationResult, log_fn):
    log_fn(f"\n=== RESULTS ({result.mode}) ===")
    for name in CALIBRATION_ORDER:
        if name in result.motors:
            m = result.motors[name]
            s = "✓" if m.calibrated else "✗"
            log_fn(f"  {s} {name:<16} {m.min_position:>5} → {m.max_position:<5} (range={m.range}, center={m.center})")
