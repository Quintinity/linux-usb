#!/usr/bin/env python3
"""
SO-101 Monitored Teleop
========================
Teleop with built-in voltage/current/load monitoring.
Logs all servo telemetry to CSV and prints warnings in real-time.
When a failure occurs, dumps the last N readings to show what happened.

Usage:
    source ~/lerobot-env/bin/activate
    python teleop_monitor.py
    python teleop_monitor.py --log teleop_data.csv
"""

import argparse
import collections
import csv
import json
import signal
import sys
import time

from lerobot.motors.feetech.feetech import FeetechMotorsBus, OperatingMode
from lerobot.motors.motors_bus import Motor, MotorNormMode, MotorCalibration

# ── Config ───────────────────────────────────────────────────────────────────
FOLLOWER_PORT = "/dev/ttyACM0"
LEADER_PORT = "/dev/ttyACM1"
FOLLOWER_CAL = "/home/bradley/.cache/huggingface/lerobot/calibration/robots/so_follower/follower.json"
LEADER_CAL = "/home/bradley/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/leader.json"

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
MOTOR_IDS = [1, 2, 3, 4, 5, 6]

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

ERROR_FLAGS = {1: "VOLTAGE", 2: "ANGLE", 4: "OVERHEAT", 8: "OVERCURRENT", 32: "OVERLOAD"}


def decode_sign_magnitude(val, bits):
    mask = (1 << bits) - 1
    magnitude = val & mask
    sign = val >> bits
    return -magnitude if sign else magnitude


def decode_errors(status_byte):
    return [name for bit, name in ERROR_FLAGS.items() if status_byte & bit]


def load_cal(path):
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


def read_servo_telemetry(ph, port_handler, motor_id):
    """Read voltage, current, load, temp, status from one servo. Returns dict or None."""
    try:
        voltage_raw, c1, _ = ph.read1ByteTxRx(port_handler, motor_id, 62)
        load_raw, c2, _ = ph.read2ByteTxRx(port_handler, motor_id, 60)
        temp_raw, c3, _ = ph.read1ByteTxRx(port_handler, motor_id, 63)
        status_raw, c4, _ = ph.read1ByteTxRx(port_handler, motor_id, 65)
        current_raw, c5, _ = ph.read2ByteTxRx(port_handler, motor_id, 69)

        if any(c != 0 for c in [c1, c2, c3, c4, c5]):
            return None

        return {
            "voltage": voltage_raw / 10.0,
            "current_mA": abs(decode_sign_magnitude(current_raw, 15)) * 6.5,
            "load_pct": decode_sign_magnitude(load_raw, 10) / 10.0,
            "temp_C": temp_raw,
            "status": status_raw,
            "errors": decode_errors(status_raw),
        }
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="SO-101 Monitored Teleop")
    parser.add_argument("--log", default="/tmp/teleop_monitor.csv", help="CSV log path")
    parser.add_argument("--fps", type=int, default=60, help="Teleop FPS")
    parser.add_argument("--monitor-hz", type=int, default=2, help="Telemetry polling rate")
    args = parser.parse_args()

    print(f"\n{BOLD}{CYAN}SO-101 Monitored Teleop{RESET}")
    print(f"{DIM}Teleop @ {args.fps}Hz, monitoring @ {args.monitor_hz}Hz{RESET}")
    print(f"{DIM}Log: {args.log}{RESET}")
    print(f"{DIM}Ctrl+C to stop{RESET}\n")

    # Connect both arms
    follower = FeetechMotorsBus(FOLLOWER_PORT, make_motors(), calibration=load_cal(FOLLOWER_CAL))
    leader = FeetechMotorsBus(LEADER_PORT, make_motors(), calibration=load_cal(LEADER_CAL))

    follower.connect()
    leader.connect()

    # Configure follower
    follower.disable_torque()
    follower.configure_motors(return_delay_time=0)
    for motor in follower.motors:
        follower.write("Operating_Mode", motor, OperatingMode.POSITION.value)
        follower.write("P_Coefficient", motor, 16)
        follower.write("I_Coefficient", motor, 0)
        follower.write("D_Coefficient", motor, 32)
        if motor == "gripper":
            follower.write("Max_Torque_Limit", motor, 500)
            follower.write("Protection_Current", motor, 250)
    follower.enable_torque()

    # CSV setup
    csv_file = open(args.log, "w", newline="")
    fields = ["timestamp", "elapsed_s", "cycle", "teleop_ok",
              "follower_read_ok", "leader_read_ok", "follower_write_ok"]
    for prefix in ["f", "l"]:
        for name in MOTOR_NAMES:
            fields.extend([f"{prefix}_{name}_voltage", f"{prefix}_{name}_current_mA",
                          f"{prefix}_{name}_load_pct", f"{prefix}_{name}_temp_C",
                          f"{prefix}_{name}_status"])
    csv_writer = csv.DictWriter(csv_file, fieldnames=fields)
    csv_writer.writeheader()

    # Ring buffer for last 20 telemetry snapshots
    history = collections.deque(maxlen=20)

    # Stats
    min_voltages_f = {name: 99.0 for name in MOTOR_NAMES}
    min_voltages_l = {name: 99.0 for name in MOTOR_NAMES}
    max_loads_f = {name: 0.0 for name in MOTOR_NAMES}
    total_cycles = 0
    follower_read_fails = 0
    leader_read_fails = 0
    follower_write_fails = 0
    retries_used = 0

    running = True
    def stop(sig, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, stop)

    t0 = time.time()
    last_monitor = 0
    monitor_interval = 1.0 / args.monitor_hz

    print(f"{BOLD}{'CYCLE':>7s}  {'Hz':>4s}  ", end="")
    for name in MOTOR_NAMES:
        short = name[:8]
        print(f"{short:>8s} ", end="")
    print(f"  {'STATUS'}{RESET}")
    print("─" * 90)

    while running:
        loop_start = time.time()
        elapsed = loop_start - t0
        csv_row = {"timestamp": time.strftime("%H:%M:%S"), "elapsed_s": f"{elapsed:.2f}",
                    "cycle": total_cycles}

        # ── Teleop cycle ─────────────────────────────────────────────────
        f_read_ok = True
        l_read_ok = True
        f_write_ok = True

        try:
            fpos = follower.sync_read("Present_Position", num_retry=10)
        except Exception:
            follower_read_fails += 1
            f_read_ok = False

        try:
            lpos = leader.sync_read("Present_Position", num_retry=10)
        except Exception:
            leader_read_fails += 1
            l_read_ok = False

        if l_read_ok and f_read_ok:
            try:
                follower.sync_write("Goal_Position", lpos)
            except Exception:
                follower_write_fails += 1
                f_write_ok = False

        csv_row["follower_read_ok"] = f_read_ok
        csv_row["leader_read_ok"] = l_read_ok
        csv_row["follower_write_ok"] = f_write_ok
        csv_row["teleop_ok"] = f_read_ok and l_read_ok and f_write_ok
        total_cycles += 1

        # ── Telemetry sampling (slower rate) ─────────────────────────────
        now = time.time()
        if now - last_monitor >= monitor_interval:
            last_monitor = now
            snapshot = {"cycle": total_cycles, "elapsed": elapsed, "follower": {}, "leader": {}}

            # Sample follower telemetry
            for name, mid in zip(MOTOR_NAMES, MOTOR_IDS):
                t = read_servo_telemetry(follower.packet_handler, follower.port_handler, mid)
                if t:
                    snapshot["follower"][name] = t
                    min_voltages_f[name] = min(min_voltages_f[name], t["voltage"])
                    max_loads_f[name] = max(max_loads_f[name], abs(t["load_pct"]))
                    csv_row[f"f_{name}_voltage"] = f"{t['voltage']:.1f}"
                    csv_row[f"f_{name}_current_mA"] = f"{t['current_mA']:.0f}"
                    csv_row[f"f_{name}_load_pct"] = f"{t['load_pct']:.1f}"
                    csv_row[f"f_{name}_temp_C"] = t["temp_C"]
                    csv_row[f"f_{name}_status"] = t["status"]

            # Sample leader telemetry
            for name, mid in zip(MOTOR_NAMES, MOTOR_IDS):
                t = read_servo_telemetry(leader.packet_handler, leader.port_handler, mid)
                if t:
                    snapshot["leader"][name] = t
                    min_voltages_l[name] = min(min_voltages_l[name], t["voltage"])
                    csv_row[f"l_{name}_voltage"] = f"{t['voltage']:.1f}"
                    csv_row[f"l_{name}_current_mA"] = f"{t['current_mA']:.0f}"
                    csv_row[f"l_{name}_load_pct"] = f"{t['load_pct']:.1f}"
                    csv_row[f"l_{name}_temp_C"] = t["temp_C"]
                    csv_row[f"l_{name}_status"] = t["status"]

            history.append(snapshot)

            # Print compact status line
            hz = total_cycles / max(elapsed, 0.01)
            line = f"{total_cycles:7d}  {hz:4.0f}  "
            any_error = False
            for name in MOTOR_NAMES:
                ft = snapshot["follower"].get(name)
                if ft:
                    v = ft["voltage"]
                    l = abs(ft["load_pct"])
                    if ft["errors"]:
                        line += f"{RED}{v:4.1f}V!{l:3.0f}{RESET} "
                        any_error = True
                    elif v < 8.0:
                        line += f"{YELLOW}{v:4.1f}V {l:3.0f}{RESET} "
                    else:
                        line += f"{v:4.1f}V {l:3.0f} "
                else:
                    line += f"{RED}  FAIL  {RESET} "
                    any_error = True

            status = f"{GREEN}OK{RESET}" if not any_error else f"{RED}ERROR{RESET}"
            line += f"  {status}"
            print(f"\r{line}")

        csv_writer.writerow(csv_row)

        # ── Check for fatal failure ──────────────────────────────────────
        if not f_read_ok or not l_read_ok:
            consecutive_fails = 0
            for _ in range(20):
                try:
                    follower.sync_read("Present_Position", num_retry=5)
                    break
                except Exception:
                    consecutive_fails += 1
                    time.sleep(0.05)

            if consecutive_fails >= 20:
                print(f"\n{RED}{BOLD}BUS DEAD — dumping last telemetry before failure:{RESET}\n")
                for snap in list(history)[-5:]:
                    print(f"  Cycle {snap['cycle']} ({snap['elapsed']:.1f}s):")
                    for name in MOTOR_NAMES:
                        ft = snap["follower"].get(name, {})
                        if ft:
                            v = ft.get("voltage", "?")
                            c = ft.get("current_mA", "?")
                            l = ft.get("load_pct", "?")
                            t = ft.get("temp_C", "?")
                            e = ft.get("errors", [])
                            e_str = f"{RED}{','.join(e)}{RESET}" if e else "ok"
                            print(f"    {name:>14s}: {v:>5}V  {c:>5}mA  {l:>5}%  {t:>3}°C  {e_str}")
                    print()
                break

        # ── FPS timing ───────────────────────────────────────────────────
        dt = time.time() - loop_start
        sleep_time = (1.0 / args.fps) - dt
        if sleep_time > 0:
            time.sleep(sleep_time)

    # ── Cleanup & Summary ────────────────────────────────────────────────
    csv_file.close()

    print(f"\n{BOLD}{CYAN}{'=' * 90}")
    print(f"  SESSION SUMMARY  ({elapsed:.0f}s, {total_cycles} cycles)")
    print(f"{'=' * 90}{RESET}")
    print(f"  Follower read fails:  {follower_read_fails}")
    print(f"  Leader read fails:    {leader_read_fails}")
    print(f"  Follower write fails: {follower_write_fails}")

    print(f"\n  {BOLD}Follower Min Voltage / Max Load:{RESET}")
    for name in MOTOR_NAMES:
        v = min_voltages_f[name]
        l = max_loads_f[name]
        v_color = RED if v < 8.0 else GREEN
        l_color = RED if l > 80 else YELLOW if l > 50 else RESET
        print(f"    {name:>14s}: {v_color}{v:5.1f}V{RESET}  {l_color}{l:5.1f}% load{RESET}")

    print(f"\n  {BOLD}Leader Min Voltage:{RESET}")
    for name in MOTOR_NAMES:
        v = min_voltages_l[name]
        v_color = RED if v < 5.0 else YELLOW if v < 6.0 else GREEN
        print(f"    {name:>14s}: {v_color}{v:5.1f}V{RESET}")

    print(f"\n  Log saved to: {args.log}")
    print()

    try:
        follower.disable_torque()
    except Exception:
        pass
    follower.disconnect()
    leader.disconnect()


if __name__ == "__main__":
    main()
