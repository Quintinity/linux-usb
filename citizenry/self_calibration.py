"""Self-Calibration — discover real physical joint limits by stall detection.

For each motor, the arm is pre-positioned so the joint under test has
maximum freedom of movement (no table collision, minimal gravity torque).
Motors are calibrated in order from easiest to hardest.

Calibration order (per research):
1. wrist_roll (ID 5) — full 360°, no stall detection needed
2. gripper (ID 6) — self-contained, no gravity
3. wrist_flex (ID 4) — low gravity, arm extended
4. shoulder_pan (ID 1) — no gravity, arm in L-shape upright
5. elbow_flex (ID 3) — shoulder vertical, minimizes gravity
6. shoulder_lift (ID 2) — elbow folded tight, use current derivative

Safe pre-positions keep the arm above the table surface for each test.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]
MOTOR_IDS = {name: i + 1 for i, name in enumerate(MOTOR_NAMES)}

# Calibration order: easiest → hardest
CALIBRATION_ORDER = [
    "wrist_roll",      # Full 360, no stall needed
    "gripper",         # Self-contained
    "wrist_flex",      # Low gravity
    "shoulder_pan",    # No gravity (horizontal)
    "elbow_flex",      # Moderate gravity
    "shoulder_lift",   # Highest gravity — hardest
]

# Safe pre-positions for each motor test.
# Other joints are set to these positions BEFORE testing the target motor.
# Goal: arm is upright, target joint has maximum freedom, nothing hits the table.
SAFE_POSITIONS = {
    "wrist_roll": {
        # Arm upright, forearm horizontal — wrist can spin freely
        "shoulder_pan": 2048, "shoulder_lift": 1800, "elbow_flex": 2500,
        "wrist_flex": 2048, "gripper": 2048,
    },
    "gripper": {
        # Arm upright — gripper can open/close freely
        "shoulder_pan": 2048, "shoulder_lift": 1800, "elbow_flex": 2500,
        "wrist_flex": 2048, "wrist_roll": 2048,
    },
    "wrist_flex": {
        # Arm upright, forearm extended — wrist has room to tilt
        "shoulder_pan": 2048, "shoulder_lift": 1800, "elbow_flex": 2200,
        "wrist_roll": 2048, "gripper": 2048,
    },
    "shoulder_pan": {
        # Arm in L-shape pointing up — base can rotate in clear air
        "shoulder_lift": 1600, "elbow_flex": 2800,
        "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 2048,
    },
    "elbow_flex": {
        # Shoulder vertical (arm pointing up) — elbow swings horizontally
        "shoulder_pan": 2048, "shoulder_lift": 2200,
        "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 2048,
    },
    "shoulder_lift": {
        # Elbow folded tight (minimize moment arm) — reduces gravity torque
        "shoulder_pan": 2048, "elbow_flex": 3200,
        "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 2048,
    },
}

# Special cases
FULL_ROTATION_MOTORS = {"wrist_roll"}  # Skip stall detection, use 0-4095
GRAVITY_SENSITIVE = {"shoulder_lift", "elbow_flex"}  # Use slower speed + current monitoring


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
        return {
            "name": self.name, "id": self.motor_id,
            "min": self.min_position, "max": self.max_position,
            "range": self.range, "center": self.center,
            "calibrated": self.calibrated,
        }


@dataclass
class SelfCalibrationResult:
    """Results of a full self-calibration run."""
    motors: dict[str, MotorLimits] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "motors": {k: v.to_dict() for k, v in self.motors.items()},
            "timestamp": self.timestamp,
            "duration_s": round(self.duration_s, 1),
        }


def _move_to_safe_position(bus, target_motor: str, log_fn=None):
    """Move all OTHER motors to safe positions before testing target_motor."""
    ph = bus.packet_handler
    port = bus.port_handler
    safe = SAFE_POSITIONS.get(target_motor, {})

    if log_fn:
        log_fn(f"    pre-positioning for {target_motor} test...")

    # Enable torque on all motors we need to move
    for name, pos in safe.items():
        mid = MOTOR_IDS[name]
        ph.write1ByteTxRx(port, mid, 40, 1)  # Enable torque

    time.sleep(0.2)

    # Move to safe positions gradually (3 steps to avoid jerky movement)
    for step in range(3):
        for name, target_pos in safe.items():
            mid = MOTOR_IDS[name]
            # Read current position
            current, r, _ = ph.read2ByteTxRx(port, mid, 56)
            if r != 0:
                continue
            # Interpolate
            t = (step + 1) / 3.0
            interp = int(current + (target_pos - current) * t)
            ph.write2ByteTxRx(port, mid, 42, interp)
        time.sleep(0.3)

    time.sleep(0.5)  # Let it settle

    # Disable torque on motors we moved (except the one we're about to test)
    for name in safe:
        if name != target_motor:
            mid = MOTOR_IDS[name]
            # Keep torque on to hold position during test
            pass  # Actually keep them enabled to hold the safe position


def find_motor_limits(
    bus,
    motor_id: int,
    motor_name: str,
    step: int = 50,
    stall_threshold: int = 15,
    stall_count_required: int = 3,
    max_steps: int = 80,
    step_delay: float = 0.12,
    log_fn=None,
) -> MotorLimits:
    """Find the physical limits of a single motor by moving until stall."""
    ph = bus.packet_handler
    port = bus.port_handler

    def _log(msg):
        if log_fn:
            log_fn(msg)

    # Handle full-rotation motors
    if motor_name in FULL_ROTATION_MOTORS:
        _log(f"  {motor_name}: full rotation (0-4095)")
        return MotorLimits(
            name=motor_name, motor_id=motor_id,
            min_position=0, max_position=4095, range=4095, center=2048,
            calibrated=True,
        )

    # Use slower steps for gravity-sensitive joints
    if motor_name in GRAVITY_SENSITIVE:
        step = 40
        step_delay = 0.15
        stall_threshold = 20  # More tolerance for gravity load

    # Read current position
    pos_raw, result, _ = ph.read2ByteTxRx(port, motor_id, 56)
    if result != 0:
        _log(f"  {motor_name}: read failed")
        return MotorLimits(name=motor_name, motor_id=motor_id)

    limits = MotorLimits(name=motor_name, motor_id=motor_id, start_position=pos_raw)
    _log(f"  {motor_name} (ID {motor_id}): start={pos_raw}")

    # Enable torque for this motor
    ph.write1ByteTxRx(port, motor_id, 40, 1)
    time.sleep(0.3)

    # Find MIN limit
    current = pos_raw
    stalls = 0
    min_found = False

    for i in range(max_steps):
        target = current - step
        if target < 0:
            limits.min_position = 0
            min_found = True
            break
        ph.write2ByteTxRx(port, motor_id, 42, target)
        time.sleep(step_delay)
        actual, r, _ = ph.read2ByteTxRx(port, motor_id, 56)
        if r != 0:
            continue

        # Also check Moving register for more reliable stall detection
        moving, _, _ = ph.read1ByteTxRx(port, motor_id, 66)

        if abs(actual - current) < stall_threshold and moving == 0:
            stalls += 1
            if stalls >= stall_count_required:
                limits.min_position = actual
                limits.min_stall = True
                min_found = True
                _log(f"    MIN stall at {actual}")
                break
        else:
            stalls = 0
            current = actual

    if not min_found:
        limits.min_position = current

    # Return to start before finding MAX
    ph.write2ByteTxRx(port, motor_id, 42, pos_raw)
    time.sleep(1.0)

    # Find MAX limit
    current = pos_raw
    stalls = 0
    max_found = False

    for i in range(max_steps):
        target = current + step
        if target > 4095:
            limits.max_position = 4095
            max_found = True
            break
        ph.write2ByteTxRx(port, motor_id, 42, target)
        time.sleep(step_delay)
        actual, r, _ = ph.read2ByteTxRx(port, motor_id, 56)
        if r != 0:
            continue

        moving, _, _ = ph.read1ByteTxRx(port, motor_id, 66)

        if abs(actual - current) < stall_threshold and moving == 0:
            stalls += 1
            if stalls >= stall_count_required:
                limits.max_position = actual
                limits.max_stall = True
                max_found = True
                _log(f"    MAX stall at {actual}")
                break
        else:
            stalls = 0
            current = actual

    if not max_found:
        limits.max_position = current

    # Compute range and center
    if limits.max_position > limits.min_position:
        limits.range = limits.max_position - limits.min_position
        limits.center = (limits.min_position + limits.max_position) // 2
        limits.calibrated = True
    else:
        limits.range = abs(limits.max_position - limits.min_position)
        limits.center = pos_raw
        limits.calibrated = False
        _log(f"    WARNING: unexpected range (min={limits.min_position}, max={limits.max_position})")

    # Return to center and disable torque on this motor
    ph.write2ByteTxRx(port, motor_id, 42, limits.center)
    time.sleep(0.5)
    ph.write1ByteTxRx(port, motor_id, 40, 0)

    _log(f"    result: {limits.min_position} → {limits.max_position} (range={limits.range}, center={limits.center})")
    return limits


def self_calibrate_all(
    bus,
    motor_names: list[str] | None = None,
    log_fn=None,
) -> SelfCalibrationResult:
    """Self-calibrate all motors with safe pre-positioning.

    Calibrates in order from easiest to hardest. Before each motor test,
    other joints are moved to safe positions that keep the arm upright
    and give the target joint maximum freedom.
    """
    names = motor_names or CALIBRATION_ORDER
    result = SelfCalibrationResult()
    t0 = time.time()
    ph = bus.packet_handler
    port = bus.port_handler

    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log("Self-calibration starting (safe pre-positioning enabled)...")
    _log(f"Order: {' → '.join(names)}")

    for name in names:
        mid = MOTOR_IDS.get(name)
        if mid is None:
            continue

        _log(f"\n  [{names.index(name)+1}/{len(names)}] Calibrating {name}...")

        # Pre-position other motors to safe pose
        _move_to_safe_position(bus, name, log_fn=_log)

        # Now calibrate this motor
        limits = find_motor_limits(bus, mid, name, log_fn=_log)
        result.motors[name] = limits

    # Return all motors to their discovered centers and disable torque
    _log("\n  Returning to centers and disabling torque...")
    for name, limits in result.motors.items():
        mid = MOTOR_IDS[name]
        ph.write1ByteTxRx(port, mid, 40, 1)
        ph.write2ByteTxRx(port, mid, 42, limits.center)
    time.sleep(1.0)
    for name in MOTOR_NAMES:
        ph.write1ByteTxRx(port, MOTOR_IDS[name], 40, 0)

    result.duration_s = time.time() - t0
    _log(f"\nSelf-calibration complete in {result.duration_s:.1f}s")

    # Summary
    _log("\n  === RESULTS ===")
    for name in CALIBRATION_ORDER:
        if name in result.motors:
            m = result.motors[name]
            status = "✓" if m.calibrated else "✗"
            _log(f"  {status} {name:<16} {m.min_position:>5} → {m.max_position:<5} (range={m.range}, center={m.center})")

    return result
