#!/usr/bin/env python3
"""Choreographed arm movement demo over the citizenry protocol.

Writes a dance sequence to the leader arm on the Surface.
The teleop loop reads those positions and streams them to the
follower arm on the Pi. Both arms move in sync.
"""

import asyncio
import math
import time

from .surface_citizen import SurfaceCitizen, MOTOR_NAMES

# ── Poses (raw STS3215 position values, 0-4095, center ~2048) ──

HOME = {
    "shoulder_pan": 2048,
    "shoulder_lift": 1400,
    "elbow_flex": 3000,
    "wrist_flex": 2048,
    "wrist_roll": 2048,
    "gripper": 2048,
}

WAVE_LEFT = {
    "shoulder_pan": 2400,
    "shoulder_lift": 1600,
    "elbow_flex": 2500,
    "wrist_flex": 2048,
    "wrist_roll": 1600,
    "gripper": 2048,
}

WAVE_RIGHT = {
    "shoulder_pan": 1700,
    "shoulder_lift": 1600,
    "elbow_flex": 2500,
    "wrist_flex": 2048,
    "wrist_roll": 2500,
    "gripper": 2048,
}

REACH_UP = {
    "shoulder_pan": 2048,
    "shoulder_lift": 1800,
    "elbow_flex": 2200,
    "wrist_flex": 2048,
    "wrist_roll": 2048,
    "gripper": 1500,
}

GRIP_OPEN = {
    "shoulder_pan": 2048,
    "shoulder_lift": 1400,
    "elbow_flex": 2800,
    "wrist_flex": 2048,
    "wrist_roll": 2048,
    "gripper": 1400,
}

GRIP_CLOSE = {
    "shoulder_pan": 2048,
    "shoulder_lift": 1400,
    "elbow_flex": 2800,
    "wrist_flex": 2048,
    "wrist_roll": 2048,
    "gripper": 2500,
}

BOW = {
    "shoulder_pan": 2048,
    "shoulder_lift": 2200,
    "elbow_flex": 3200,
    "wrist_flex": 1500,
    "wrist_roll": 2048,
    "gripper": 2048,
}

# The dance sequence: (pose, hold_seconds, description)
DANCE = [
    (HOME, 1.5, "home position"),
    (WAVE_LEFT, 0.8, "wave left"),
    (WAVE_RIGHT, 0.8, "wave right"),
    (WAVE_LEFT, 0.8, "wave left"),
    (WAVE_RIGHT, 0.8, "wave right"),
    (HOME, 1.0, "return home"),
    (REACH_UP, 1.0, "reach up"),
    (GRIP_OPEN, 0.8, "open gripper"),
    (GRIP_CLOSE, 0.8, "close gripper"),
    (GRIP_OPEN, 0.8, "open gripper"),
    (GRIP_CLOSE, 0.8, "close gripper"),
    (HOME, 1.0, "return home"),
    (BOW, 1.5, "take a bow"),
    (HOME, 1.5, "home position"),
]


BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"


def interpolate(start: dict, end: dict, t: float) -> dict:
    """Smooth interpolation between two poses. t in [0, 1]."""
    # Ease in-out
    t = t * t * (3 - 2 * t)
    return {
        name: int(start[name] + (end[name] - start[name]) * t)
        for name in MOTOR_NAMES
    }


async def run_choreo(leader_port="/dev/ttyACM0", fps=30.0):
    """Run the choreography demo."""

    # Connect directly to leader arm for writing
    from lerobot.motors.feetech.feetech import FeetechMotorsBus
    from lerobot.motors.motors_bus import Motor, MotorNormMode

    motors = {
        name: Motor(i + 1, "sts3215",
                    MotorNormMode.RANGE_0_100 if name == "gripper" else MotorNormMode.RANGE_M100_100)
        for i, name in enumerate(MOTOR_NAMES)
    }
    leader_bus = FeetechMotorsBus(port=leader_port, motors=motors)
    leader_bus.connect()

    # Start the citizenry — Surface reads the leader arm, Pi follows
    surface = SurfaceCitizen(leader_port=leader_port, teleop_fps=fps)

    # Override leader bus init to share our bus
    surface._init_leader_bus = lambda: leader_bus

    await surface.start()

    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  armOS CITIZENRY — SYNCHRONIZED DANCE                       ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()

    # Wait for Pi follower
    print(f"{BOLD}Waiting for follower...{RESET}")
    t0 = time.time()
    while not surface._teleop_active and time.time() - t0 < 10:
        await asyncio.sleep(0.1)

    if not surface._teleop_active:
        print(f"{YELLOW}No follower connected — dancing solo on leader arm{RESET}")
        solo = True
    else:
        n = list(surface.neighbors.values())[0]
        print(f"{GREEN}✓{RESET} Follower connected: {n.name} @ {n.addr[0]}")
        print(f"  Teleop active — both arms will move in sync")
        solo = False

    print()

    # Enable torque on leader arm
    leader_bus.enable_torque()
    print(f"{GREEN}✓{RESET} Leader arm torque enabled")
    print()

    # Move to home first
    print(f"{BOLD}Moving to home position...{RESET}")
    current = leader_bus.sync_read("Present_Position", normalize=False)
    current_pos = {name: int(current[name]) if not hasattr(current[name], 'item') else int(current[name].item()) for name in MOTOR_NAMES}

    # Smooth move to home over 2 seconds
    steps = 60
    for i in range(steps + 1):
        t = i / steps
        pose = interpolate(current_pos, HOME, t)
        leader_bus.sync_write("Goal_Position", pose, normalize=False)
        await asyncio.sleep(2.0 / steps)

    await asyncio.sleep(0.5)
    print(f"{GREEN}✓{RESET} At home position")
    print()

    # Run the dance
    print(f"{BOLD}Dancing!{RESET}")
    print()

    prev_pose = HOME
    for i, (target_pose, hold_time, desc) in enumerate(DANCE):
        step_num = i + 1
        total = len(DANCE)

        frames_at_start = surface._frames_sent

        # Smooth transition over 0.5 seconds
        move_steps = 15
        for s in range(move_steps + 1):
            t = s / move_steps
            pose = interpolate(prev_pose, target_pose, t)
            leader_bus.sync_write("Goal_Position", pose, normalize=False)
            await asyncio.sleep(0.5 / move_steps)

        # Hold
        await asyncio.sleep(hold_time)

        frames_during = surface._frames_sent - frames_at_start
        sync_str = f" → {frames_during} frames to follower" if not solo else ""
        print(f"  {DIM}[{step_num:2d}/{total}]{RESET} {desc:<20}{sync_str}")

        prev_pose = target_pose

    print()

    # Summary
    total_frames = surface._frames_sent
    elapsed = time.time() - surface._teleop_start if surface._teleop_start else 1
    avg_fps = total_frames / elapsed if elapsed > 0 else 0

    if not solo:
        n = list(surface.neighbors.values())[0]
        telem = surface.follower_telemetry.get(n.pubkey, {})
        print(f"{BOLD}Results:{RESET}")
        print(f"  Teleop frames: {total_frames} at {avg_fps:.1f} FPS")
        print(f"  Follower: {n.name} @ {n.addr[0]} — {n.presence.value}")
        if telem:
            print(f"  Telemetry: V={telem.get('min_voltage')}V T={telem.get('max_temperature')}°C")
        violations = surface.safety_violations
        if violations:
            for v in violations:
                print(f"  {YELLOW}⚠ {v['violation']}{RESET}")
        else:
            print(f"  {GREEN}✓ No safety violations{RESET}")

    print()
    print(f"  Disabling torque...")
    leader_bus.disable_torque()

    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  Both arms danced in sync. The citizenry moves as one.      ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}")

    await surface.stop()
    leader_bus.disconnect()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--leader-port", default="/dev/ttyACM0")
    parser.add_argument("--fps", type=float, default=30.0)
    args = parser.parse_args()
    asyncio.run(run_choreo(args.leader_port, args.fps))
