#!/usr/bin/env python3
"""
SO-101 Live Servo Monitor
==========================
Streams real-time voltage, current, load, temperature, and status
from all 6 servos. Use during teleop to catch the exact moment of failure.

Usage:
    source ~/lerobot-env/bin/activate
    python monitor_arm.py                          # monitor follower
    python monitor_arm.py --port /dev/ttyACM1      # monitor leader
    python monitor_arm.py --log voltlog.csv         # save to CSV
"""

import argparse
import csv
import json
import signal
import sys
import time

# ── Setup ────────────────────────────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
MOTOR_IDS = [1, 2, 3, 4, 5, 6]

# Error flag bits
ERROR_FLAGS = {
    1: "VOLTAGE",
    2: "ANGLE",
    4: "OVERHEAT",
    8: "OVERCURRENT",
    32: "OVERLOAD",
}


def decode_sign_magnitude(val, bits):
    """Decode sign-magnitude encoded value."""
    mask = (1 << bits) - 1
    magnitude = val & mask
    sign = val >> bits
    return -magnitude if sign else magnitude


def decode_errors(status_byte):
    """Decode error flag byte into list of error names."""
    if status_byte == 0:
        return []
    return [name for bit, name in ERROR_FLAGS.items() if status_byte & bit]


def color_voltage(v):
    if v < 5.0:
        return f"{RED}{v:5.1f}V{RESET}"
    elif v < 6.0:
        return f"{YELLOW}{v:5.1f}V{RESET}"
    else:
        return f"{GREEN}{v:5.1f}V{RESET}"


def color_temp(t):
    if t >= 65:
        return f"{RED}{t:3d}°C{RESET}"
    elif t >= 55:
        return f"{YELLOW}{t:3d}°C{RESET}"
    else:
        return f"{GREEN}{t:3d}°C{RESET}"


def color_load(l):
    if abs(l) > 80:
        return f"{RED}{l:6.1f}%{RESET}"
    elif abs(l) > 50:
        return f"{YELLOW}{l:6.1f}%{RESET}"
    else:
        return f"{l:6.1f}%"


def color_current(c):
    if c > 500:
        return f"{RED}{c:5.0f}mA{RESET}"
    elif c > 300:
        return f"{YELLOW}{c:5.0f}mA{RESET}"
    else:
        return f"{c:5.0f}mA"


def main():
    parser = argparse.ArgumentParser(description="SO-101 Live Servo Monitor")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port")
    parser.add_argument("--cal", default=None, help="Calibration file (optional)")
    parser.add_argument("--log", default=None, help="CSV log file path")
    parser.add_argument("--hz", type=int, default=10, help="Polling rate (default 10)")
    args = parser.parse_args()

    from lerobot.motors.feetech.feetech import FeetechMotorsBus
    from lerobot.motors.motors_bus import Motor, MotorNormMode, MotorCalibration

    motors = {
        "shoulder_pan": Motor(1, "sts3215", MotorNormMode.RANGE_M100_100),
        "shoulder_lift": Motor(2, "sts3215", MotorNormMode.RANGE_M100_100),
        "elbow_flex": Motor(3, "sts3215", MotorNormMode.RANGE_M100_100),
        "wrist_flex": Motor(4, "sts3215", MotorNormMode.RANGE_M100_100),
        "wrist_roll": Motor(5, "sts3215", MotorNormMode.RANGE_M100_100),
        "gripper": Motor(6, "sts3215", MotorNormMode.RANGE_0_100),
    }

    calibration = None
    if args.cal:
        with open(args.cal) as f:
            cal_data = json.load(f)
        calibration = {name: MotorCalibration(**c) for name, c in cal_data.items()}

    bus = FeetechMotorsBus(port=args.port, motors=motors, calibration=calibration)

    # Open port directly for raw register reads
    bus.port_handler.openPort()
    bus.port_handler.setBaudRate(1_000_000)
    ph = bus.packet_handler

    # CSV logging
    csv_file = None
    csv_writer = None
    if args.log:
        csv_file = open(args.log, "w", newline="")
        fields = ["timestamp", "elapsed_s"]
        for name in MOTOR_NAMES:
            fields.extend([f"{name}_voltage", f"{name}_current_mA", f"{name}_load_pct",
                          f"{name}_temp_C", f"{name}_position", f"{name}_velocity",
                          f"{name}_status", f"{name}_errors"])
        csv_writer = csv.DictWriter(csv_file, fieldnames=fields)
        csv_writer.writeheader()

    running = True
    def stop(sig, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, stop)

    # Track min voltage per motor
    min_voltages = {name: 99.0 for name in MOTOR_NAMES}
    max_currents = {name: 0.0 for name in MOTOR_NAMES}
    max_loads = {name: 0.0 for name in MOTOR_NAMES}
    error_counts = {name: 0 for name in MOTOR_NAMES}
    read_fails = 0
    total_reads = 0

    print(f"\n{BOLD}{CYAN}SO-101 Live Servo Monitor — {args.port} @ {args.hz}Hz{RESET}")
    if args.log:
        print(f"{DIM}Logging to {args.log}{RESET}")
    print(f"{DIM}Ctrl+C to stop{RESET}\n")

    # Print header
    header = f"{'TIME':>7s}  {'MOTOR':>14s}  {'VOLT':>6s}  {'CURR':>7s}  {'LOAD':>7s}  {'TEMP':>5s}  {'POS':>6s}  {'VEL':>5s}  {'STATUS'}"
    print(f"{BOLD}{header}{RESET}")
    print("─" * 85)

    t0 = time.time()
    interval = 1.0 / args.hz

    while running:
        loop_start = time.time()
        elapsed = loop_start - t0
        ts = time.strftime("%H:%M:%S")
        csv_row = {"timestamp": ts, "elapsed_s": f"{elapsed:.2f}"}
        any_error = False

        for name, mid in zip(MOTOR_NAMES, MOTOR_IDS):
            total_reads += 1

            # Read all registers for this motor
            try:
                voltage_raw, c1, _ = ph.read1ByteTxRx(bus.port_handler, mid, 62)
                current_raw, c2, _ = ph.read2ByteTxRx(bus.port_handler, mid, 69)
                load_raw, c3, _ = ph.read2ByteTxRx(bus.port_handler, mid, 60)
                temp_raw, c4, _ = ph.read1ByteTxRx(bus.port_handler, mid, 63)
                pos_raw, c5, _ = ph.read2ByteTxRx(bus.port_handler, mid, 56)
                vel_raw, c6, _ = ph.read2ByteTxRx(bus.port_handler, mid, 58)
                status_raw, c7, _ = ph.read1ByteTxRx(bus.port_handler, mid, 65)
            except Exception:
                read_fails += 1
                print(f"{ts}  {name:>14s}  {RED}READ FAILED{RESET}")
                continue

            if any(c != 0 for c in [c1, c2, c3, c4, c5, c6, c7]):
                read_fails += 1
                print(f"{ts}  {name:>14s}  {RED}COMM ERROR{RESET}")
                continue

            # Decode
            voltage = voltage_raw / 10.0
            current = decode_sign_magnitude(current_raw, 15)
            current_ma = abs(current) * 6.5  # rough mA conversion for STS3215
            load = decode_sign_magnitude(load_raw, 10) / 10.0
            temp = temp_raw
            position = decode_sign_magnitude(pos_raw, 15)
            velocity = decode_sign_magnitude(vel_raw, 15)
            errors = decode_errors(status_raw)

            # Track extremes
            min_voltages[name] = min(min_voltages[name], voltage)
            max_currents[name] = max(max_currents[name], current_ma)
            max_loads[name] = max(max_loads[name], abs(load))
            if errors:
                error_counts[name] += 1
                any_error = True

            # Format output
            err_str = f"{RED}{','.join(errors)}{RESET}" if errors else f"{GREEN}ok{RESET}"
            line = (f"{ts}  {name:>14s}  {color_voltage(voltage)}  {color_current(current_ma)}  "
                    f"{color_load(load)}  {color_temp(temp)}  {position:6d}  {velocity:5d}  {err_str}")
            print(line)

            # CSV
            if csv_writer:
                csv_row[f"{name}_voltage"] = f"{voltage:.1f}"
                csv_row[f"{name}_current_mA"] = f"{current_ma:.0f}"
                csv_row[f"{name}_load_pct"] = f"{load:.1f}"
                csv_row[f"{name}_temp_C"] = str(temp)
                csv_row[f"{name}_position"] = str(position)
                csv_row[f"{name}_velocity"] = str(velocity)
                csv_row[f"{name}_status"] = str(status_raw)
                csv_row[f"{name}_errors"] = ",".join(errors) if errors else ""

        if csv_writer:
            csv_writer.writerow(csv_row)

        # Separator between readings
        if any_error:
            print(f"{RED}{'─' * 85}{RESET}")
        else:
            print(f"{DIM}{'─' * 85}{RESET}")

        # Sleep for remaining interval
        dt = time.time() - loop_start
        if dt < interval:
            time.sleep(interval - dt)

    # ── Summary ──────────────────────────────────────────────────────────────
    bus.port_handler.closePort()
    if csv_file:
        csv_file.close()

    print(f"\n{BOLD}{CYAN}{'=' * 85}")
    print(f"  SESSION SUMMARY  ({elapsed:.0f}s, {total_reads} reads, {read_fails} failures)")
    print(f"{'=' * 85}{RESET}")
    print(f"\n  {'MOTOR':>14s}  {'MIN VOLT':>9s}  {'MAX CURR':>9s}  {'MAX LOAD':>9s}  {'ERRORS':>7s}")
    print(f"  {'─' * 55}")
    for name in MOTOR_NAMES:
        v = min_voltages[name]
        c = max_currents[name]
        l = max_loads[name]
        e = error_counts[name]
        v_str = f"{RED}{v:7.1f}V{RESET}" if v < 6.0 else f"{GREEN}{v:7.1f}V{RESET}"
        c_str = f"{RED}{c:7.0f}mA{RESET}" if c > 500 else f"{c:7.0f}mA"
        l_str = f"{RED}{l:7.1f}%{RESET}" if l > 80 else f"{l:7.1f}%"
        e_str = f"{RED}{e:7d}{RESET}" if e > 0 else f"{GREEN}{e:7d}{RESET}"
        print(f"  {name:>14s}  {v_str}  {c_str}  {l_str}  {e_str}")

    if args.log:
        print(f"\n  Full log saved to: {args.log}")
    print()


if __name__ == "__main__":
    main()
