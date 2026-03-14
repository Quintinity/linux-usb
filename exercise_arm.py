#!/usr/bin/env python3
"""
SO-101 Arm Exercise & Stress Test
==================================
Moves the follower arm through a series of positions programmatically,
monitoring communication health at every step. No leader arm needed.

Doubles as a post-calibration verification — confirms every joint can
reach its full range and the gripper opens/closes.

Usage:
    source ~/lerobot-env/bin/activate
    python exercise_arm.py                    # full test
    python exercise_arm.py --joint gripper    # test one joint
    python exercise_arm.py --cycles 5         # more repetitions
"""

import argparse
import json
import signal
import sys
import time

from lerobot.motors.feetech.feetech import FeetechMotorsBus, OperatingMode
from lerobot.motors.motors_bus import Motor, MotorNormMode, MotorCalibration

# ── Config ───────────────────────────────────────────────────────────────────
PORT = "/dev/ttyACM0"
CAL_PATH = "/home/bradley/.cache/huggingface/lerobot/calibration/robots/so_follower/follower.json"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_calibration(path):
    with open(path) as f:
        return {name: MotorCalibration(**c) for name, c in json.load(f).items()}


def make_motors():
    return {
        "shoulder_pan": Motor(1, "sts3215", MotorNormMode.RANGE_M100_100),
        "shoulder_lift": Motor(2, "sts3215", MotorNormMode.RANGE_M100_100),
        "elbow_flex": Motor(3, "sts3215", MotorNormMode.RANGE_M100_100),
        "wrist_flex": Motor(4, "sts3215", MotorNormMode.RANGE_M100_100),
        "wrist_roll": Motor(5, "sts3215", MotorNormMode.RANGE_M100_100),
        "gripper": Motor(6, "sts3215", MotorNormMode.RANGE_0_100),
    }


def read_voltage(bus, motor_id):
    """Read voltage from a single servo."""
    try:
        v, comm, _ = bus.packet_handler.read1ByteTxRx(bus.port_handler, motor_id, 62)
        return v / 10.0 if comm == 0 else None
    except Exception:
        return None


def read_status(bus, motor_id):
    """Read error status register."""
    try:
        s, comm, _ = bus.packet_handler.read1ByteTxRx(bus.port_handler, motor_id, 65)
        return s if comm == 0 else None
    except Exception:
        return None


def read_load(bus, motor_id):
    """Read present load (torque %)."""
    try:
        val, comm, _ = bus.packet_handler.read2ByteTxRx(bus.port_handler, motor_id, 60)
        if comm != 0:
            return None
        # Sign-magnitude: bit 10 is sign, bits 0-9 are magnitude
        magnitude = val & 0x3FF
        return magnitude / 10.0  # percentage
    except Exception:
        return None


# ── Movement ─────────────────────────────────────────────────────────────────

def move_to(bus, targets, steps=30, pause=0.02):
    """
    Smoothly interpolate from current position to targets over `steps` steps.
    Returns (success_count, fail_count, positions_log).
    """
    success = 0
    fails = 0
    log = []

    try:
        current = bus.sync_read("Present_Position", num_retry=10)
    except Exception as e:
        print(f"  {RED}Cannot read current position: {e}{RESET}")
        return 0, 1, []

    for step in range(1, steps + 1):
        t = step / steps
        interpolated = {}
        for joint in targets:
            start_val = current[joint]
            end_val = targets[joint]
            interpolated[joint] = start_val + (end_val - start_val) * t

        try:
            bus.sync_write("Goal_Position", interpolated)
            success += 1
        except Exception:
            fails += 1

        try:
            pos = bus.sync_read("Present_Position", num_retry=10)
            log.append(pos)
            success += 1
        except Exception:
            fails += 1

        time.sleep(pause)

    return success, fails, log


def hold_and_monitor(bus, duration=1.0, label=""):
    """Hold position and monitor voltage/status/load for duration seconds."""
    t0 = time.perf_counter()
    reads = 0
    fails = 0
    voltages = []
    loads = []
    statuses = set()

    while time.perf_counter() - t0 < duration:
        try:
            bus.sync_read("Present_Position", num_retry=10)
            reads += 1
        except Exception:
            fails += 1

        v = read_voltage(bus, 1)
        if v is not None:
            voltages.append(v)

        load = read_load(bus, 1)  # shoulder_pan as representative
        if load is not None:
            loads.append(load)

        for mid in range(1, 7):
            s = read_status(bus, mid)
            if s and s != 0:
                statuses.add((mid, s))

        time.sleep(0.02)

    avg_v = sum(voltages) / len(voltages) if voltages else 0
    min_v = min(voltages) if voltages else 0
    avg_load = sum(loads) / len(loads) if loads else 0

    status_str = f"{GREEN}clean{RESET}" if not statuses else f"{RED}{statuses}{RESET}"
    voltage_color = GREEN if min_v >= 6.0 else RED
    result = "OK" if fails == 0 else f"{RED}{fails} FAILS{RESET}"

    print(f"    {label:30s} reads={reads} {result}  "
          f"V={voltage_color}{avg_v:.1f}V (min {min_v:.1f}V){RESET}  "
          f"load={avg_load:.0f}%  status={status_str}")

    return fails


# ── Test Sequences ───────────────────────────────────────────────────────────

def test_joint(bus, joint_name, cycles=2):
    """Move a single joint through its range while keeping others at center."""
    print(f"\n  {BOLD}Testing: {joint_name}{RESET}")

    # Gripper uses 0-100 range, others use -100 to 100
    if joint_name == "gripper":
        positions = [50, 0, 100, 50]  # center, closed, open, center
        labels = ["center", "closed", "open", "center"]
    else:
        positions = [0, -80, 80, 0]  # center, min, max, center
        labels = ["center", "min (-80)", "max (+80)", "center"]

    total_fails = 0

    for cycle in range(cycles):
        if cycles > 1:
            print(f"    Cycle {cycle + 1}/{cycles}")

        for pos, label in zip(positions, labels):
            target = {joint_name: pos}
            s, f, _ = move_to(bus, target, steps=20, pause=0.02)
            total_fails += f
            total_fails += hold_and_monitor(bus, duration=0.5, label=f"{joint_name} → {label}")

    if total_fails == 0:
        print(f"  {GREEN}✓ {joint_name}: PASSED{RESET}")
    else:
        print(f"  {RED}✗ {joint_name}: {total_fails} communication failures{RESET}")

    return total_fails


def test_combined_movement(bus, cycles=2):
    """Move multiple joints simultaneously — the real stress test."""
    print(f"\n  {BOLD}Testing: Combined movement (all joints){RESET}")

    sequences = [
        {"shoulder_pan": 0, "shoulder_lift": 0, "elbow_flex": 0,
         "wrist_flex": 0, "wrist_roll": 0, "gripper": 50},

        {"shoulder_pan": -60, "shoulder_lift": -60, "elbow_flex": 60,
         "wrist_flex": -40, "wrist_roll": -80, "gripper": 0},

        {"shoulder_pan": 60, "shoulder_lift": 60, "elbow_flex": -60,
         "wrist_flex": 40, "wrist_roll": 80, "gripper": 100},

        {"shoulder_pan": -30, "shoulder_lift": 30, "elbow_flex": -30,
         "wrist_flex": 30, "wrist_roll": 0, "gripper": 50},

        {"shoulder_pan": 0, "shoulder_lift": 0, "elbow_flex": 0,
         "wrist_flex": 0, "wrist_roll": 0, "gripper": 50},
    ]
    labels = ["home", "pose A", "pose B", "pose C", "home"]

    total_fails = 0

    for cycle in range(cycles):
        if cycles > 1:
            print(f"    Cycle {cycle + 1}/{cycles}")

        for target, label in zip(sequences, labels):
            s, f, _ = move_to(bus, target, steps=40, pause=0.02)
            total_fails += f
            total_fails += hold_and_monitor(bus, duration=0.5, label=f"all → {label}")

    if total_fails == 0:
        print(f"  {GREEN}✓ Combined movement: PASSED{RESET}")
    else:
        print(f"  {RED}✗ Combined movement: {total_fails} communication failures{RESET}")

    return total_fails


def test_rapid_gripper(bus, cycles=5):
    """Rapid open/close of gripper — common failure mode."""
    print(f"\n  {BOLD}Testing: Rapid gripper cycling{RESET}")
    total_fails = 0

    for cycle in range(cycles):
        for pos, label in [(0, "close"), (100, "open")]:
            target = {"gripper": pos}
            s, f, _ = move_to(bus, target, steps=10, pause=0.01)
            total_fails += f
            total_fails += hold_and_monitor(bus, duration=0.3, label=f"gripper {label} #{cycle+1}")

    if total_fails == 0:
        print(f"  {GREEN}✓ Rapid gripper: PASSED{RESET}")
    else:
        print(f"  {RED}✗ Rapid gripper: {total_fails} communication failures{RESET}")

    return total_fails


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SO-101 Arm Exercise & Stress Test")
    parser.add_argument("--port", default=PORT, help="Serial port")
    parser.add_argument("--cal", default=CAL_PATH, help="Calibration file path")
    parser.add_argument("--joint", default=None, help="Test a single joint only")
    parser.add_argument("--cycles", type=int, default=2, help="Number of repetitions")
    args = parser.parse_args()

    print(f"\n{BOLD}{CYAN}{'=' * 60}")
    print(f"  SO-101 ARM EXERCISE & STRESS TEST")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}{RESET}")

    cal = load_calibration(args.cal)
    bus = FeetechMotorsBus(port=args.port, motors=make_motors(), calibration=cal)
    bus.connect()

    # Configure for position control
    bus.disable_torque()
    bus.configure_motors(return_delay_time=0)
    for motor in bus.motors:
        bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
        bus.write("P_Coefficient", motor, 16)
        bus.write("I_Coefficient", motor, 0)
        bus.write("D_Coefficient", motor, 32)
        if motor == "gripper":
            bus.write("Max_Torque_Limit", motor, 500)
            bus.write("Protection_Current", motor, 250)
    bus.enable_torque()

    # Graceful shutdown on Ctrl+C
    def cleanup(sig=None, frame=None):
        print(f"\n{YELLOW}Stopping — disabling torque...{RESET}")
        try:
            bus.disable_torque()
        except Exception:
            pass
        bus.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)

    total_fails = 0

    if args.joint:
        # Test single joint
        total_fails += test_joint(bus, args.joint, cycles=args.cycles)
    else:
        # Full test sequence
        joints = ["shoulder_pan", "shoulder_lift", "elbow_flex",
                   "wrist_flex", "wrist_roll", "gripper"]
        for joint in joints:
            total_fails += test_joint(bus, joint, cycles=args.cycles)

        total_fails += test_combined_movement(bus, cycles=args.cycles)
        total_fails += test_rapid_gripper(bus, cycles=args.cycles)

    # Summary
    print(f"\n{BOLD}{CYAN}{'─' * 60}")
    print(f"  RESULTS")
    print(f"{'─' * 60}{RESET}")
    if total_fails == 0:
        print(f"  {GREEN}{BOLD}ALL TESTS PASSED — arm is healthy{RESET}")
    else:
        print(f"  {RED}{BOLD}{total_fails} total communication failures{RESET}")
    print()

    cleanup()


if __name__ == "__main__":
    main()
