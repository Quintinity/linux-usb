"""Self-Calibration — discover real physical joint limits by moving until stall.

Each motor moves incrementally in both directions until it can't move further.
The stall position = physical limit. Results are saved to the genome.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]
MOTOR_IDS = {name: i + 1 for i, name in enumerate(MOTOR_NAMES)}


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
    min_stall: bool = False   # True if MIN was found by stall detection
    max_stall: bool = False   # True if MAX was found by stall detection
    calibrated: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "id": self.motor_id,
            "min": self.min_position,
            "max": self.max_position,
            "range": self.range,
            "center": self.center,
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
    """Find the physical limits of a single motor by moving until stall.

    Args:
        bus: FeetechMotorsBus with port open
        motor_id: Servo ID (1-6)
        motor_name: Human-readable name
        step: Position increment per step
        stall_threshold: If position changes less than this, count as stall
        stall_count_required: Number of consecutive stalls to confirm limit
        max_steps: Maximum steps in each direction
        step_delay: Seconds between steps
        log_fn: Optional logging function

    Returns:
        MotorLimits with discovered min/max positions.
    """
    ph = bus.packet_handler
    port = bus.port_handler

    def _log(msg):
        if log_fn:
            log_fn(msg)

    # Read current position
    pos_raw, result, _ = ph.read2ByteTxRx(port, motor_id, 56)
    if result != 0:
        _log(f"  {motor_name}: read failed")
        return MotorLimits(name=motor_name, motor_id=motor_id)

    limits = MotorLimits(
        name=motor_name,
        motor_id=motor_id,
        start_position=pos_raw,
    )
    _log(f"  {motor_name} (ID {motor_id}): start={pos_raw}")

    # Enable torque for this motor only
    ph.write1ByteTxRx(port, motor_id, 40, 1)
    time.sleep(0.3)

    # Find MIN limit — move downward
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
        if abs(actual - current) < stall_threshold:
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
    time.sleep(0.8)

    # Find MAX limit — move upward
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
        if abs(actual - current) < stall_threshold:
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
        # Motor moved in unexpected direction — use raw values
        limits.range = abs(limits.max_position - limits.min_position)
        limits.center = pos_raw
        limits.calibrated = False
        _log(f"    WARNING: unexpected range (min={limits.min_position}, max={limits.max_position})")

    # Return to center and disable torque
    ph.write2ByteTxRx(port, motor_id, 42, limits.center)
    time.sleep(0.5)
    ph.write1ByteTxRx(port, motor_id, 40, 0)

    _log(f"    range: {limits.min_position} → {limits.max_position} (width={limits.range}, center={limits.center})")
    return limits


def self_calibrate_all(
    bus,
    motor_names: list[str] | None = None,
    log_fn=None,
) -> SelfCalibrationResult:
    """Self-calibrate all motors on an arm.

    Args:
        bus: FeetechMotorsBus with port open
        motor_names: List of motors to calibrate (default: all 6)
        log_fn: Optional logging function

    Returns:
        SelfCalibrationResult with limits for each motor.
    """
    names = motor_names or MOTOR_NAMES
    result = SelfCalibrationResult()
    t0 = time.time()

    def _log(msg):
        if log_fn:
            log_fn(msg)

    _log("Self-calibration starting...")
    for name in names:
        mid = MOTOR_IDS.get(name)
        if mid is None:
            continue
        _log(f"\n  Calibrating {name}...")
        limits = find_motor_limits(bus, mid, name, log_fn=log_fn)
        result.motors[name] = limits

    result.duration_s = time.time() - t0
    _log(f"\nSelf-calibration complete in {result.duration_s:.1f}s")

    return result
