#!/usr/bin/env python3
"""
SO-101 Arm Diagnostic Tool
===========================
Systematically tests every component of the leader/follower arm setup.
Identifies hardware faults, firmware issues, communication problems, and power issues.

Usage:
    source ~/lerobot-env/bin/activate
    python diagnose_arms.py
"""

import json
import sys
import time

# ── Imports ──────────────────────────────────────────────────────────────────
try:
    from lerobot.motors.feetech.feetech import FeetechMotorsBus, OperatingMode
    from lerobot.motors.motors_bus import Motor, MotorNormMode, MotorCalibration
except ImportError:
    print("ERROR: Cannot import lerobot. Activate the venv first:")
    print("  source ~/lerobot-env/bin/activate")
    sys.exit(1)

# ── Configuration ────────────────────────────────────────────────────────────
FOLLOWER_PORT = "/dev/ttyACM0"
LEADER_PORT = "/dev/ttyACM1"
FOLLOWER_CAL = "/home/bradley/.cache/huggingface/lerobot/calibration/robots/so_follower/follower.json"
LEADER_CAL = "/home/bradley/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/leader.json"

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
MOTOR_IDS = [1, 2, 3, 4, 5, 6]

# Thresholds
VOLTAGE_MIN = 6.0   # Volts - below this, servos may brown out
VOLTAGE_MAX = 13.0  # Volts - above this, overvoltage alarm
TEMP_WARN = 55      # Celsius
TEMP_CRIT = 65      # Celsius
EXPECTED_FIRMWARE_MINOR = 10  # v3.10 required

# ── Helpers ──────────────────────────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

issues_found = []


def header(title):
    print(f"\n{BOLD}{CYAN}{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}{RESET}")


def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg):
    print(f"  {YELLOW}!{RESET} {msg}")
    issues_found.append(("WARN", msg))


def fail(msg):
    print(f"  {RED}✗{RESET} {msg}")
    issues_found.append(("FAIL", msg))


def info(msg):
    print(f"  {msg}")


def load_calibration(path):
    try:
        with open(path) as f:
            data = json.load(f)
        return {name: MotorCalibration(**c) for name, c in data.items()}
    except FileNotFoundError:
        return None


def make_motors():
    return {
        "shoulder_pan": Motor(1, "sts3215", MotorNormMode.RANGE_M100_100),
        "shoulder_lift": Motor(2, "sts3215", MotorNormMode.RANGE_M100_100),
        "elbow_flex": Motor(3, "sts3215", MotorNormMode.RANGE_M100_100),
        "wrist_flex": Motor(4, "sts3215", MotorNormMode.RANGE_M100_100),
        "wrist_roll": Motor(5, "sts3215", MotorNormMode.RANGE_M100_100),
        "gripper": Motor(6, "sts3215", MotorNormMode.RANGE_0_100),
    }


# ── Phase 1: Port Detection ─────────────────────────────────────────────────
def phase1_ports():
    import os

    header("PHASE 1: USB Port Detection")

    for name, port in [("Follower", FOLLOWER_PORT), ("Leader", LEADER_PORT)]:
        if os.path.exists(port):
            ok(f"{name} port {port} exists")
            # Check permissions
            if os.access(port, os.R_OK | os.W_OK):
                ok(f"{name} port is readable/writable")
            else:
                fail(f"{name} port {port} not accessible. Check udev rules / dialout group")
        else:
            fail(f"{name} port {port} NOT FOUND")

    # Check for brltty
    import subprocess
    result = subprocess.run(["dpkg", "-l", "brltty"], capture_output=True, text=True)
    if "ii" in result.stdout:
        fail("brltty is installed - it steals Feetech serial ports. Run: sudo apt remove brltty")
    else:
        ok("brltty not installed")


# ── Phase 2: Individual Motor Ping ───────────────────────────────────────────
def phase2_ping(arm_name, port, calibration):
    header(f"PHASE 2: Motor Ping - {arm_name} ({port})")

    bus = FeetechMotorsBus(port=port, motors=make_motors(), calibration=calibration)
    try:
        bus.port_handler.openPort()
        bus.port_handler.setBaudRate(1_000_000)
    except Exception as e:
        fail(f"Cannot open {port}: {e}")
        return None

    found_motors = {}
    for name, motor_id in zip(MOTOR_NAMES, MOTOR_IDS):
        model, comm, error = bus.packet_handler.ping(bus.port_handler, motor_id)
        if comm == 0:  # COMM_SUCCESS
            found_motors[name] = motor_id
            error_bits = []
            if error & 1: error_bits.append("VOLTAGE")
            if error & 2: error_bits.append("ANGLE_SENSOR")
            if error & 4: error_bits.append("OVERHEAT")
            if error & 8: error_bits.append("OVER_ELECTRIC")
            if error & 32: error_bits.append("OVERLOAD")
            if error_bits:
                fail(f"{name} (ID {motor_id}): PING OK but ERROR FLAGS: {', '.join(error_bits)}")
            else:
                ok(f"{name} (ID {motor_id}): model={model}, no errors")
        else:
            fail(f"{name} (ID {motor_id}): NO RESPONSE (comm={comm})")

    bus.port_handler.closePort()

    if len(found_motors) == 6:
        ok(f"All 6 motors responding on {arm_name}")
    else:
        missing = set(MOTOR_NAMES) - set(found_motors.keys())
        fail(f"{arm_name}: Missing motors: {missing}")

    return found_motors


# ── Phase 3: Firmware Version Check ─────────────────────────────────────────
def phase3_firmware(arm_name, port, calibration):
    header(f"PHASE 3: Firmware Version - {arm_name}")

    bus = FeetechMotorsBus(port=port, motors=make_motors(), calibration=calibration)
    try:
        bus.port_handler.openPort()
        bus.port_handler.setBaudRate(1_000_000)
    except Exception as e:
        fail(f"Cannot open {port}: {e}")
        return

    for name, motor_id in zip(MOTOR_NAMES, MOTOR_IDS):
        try:
            major, comm_maj, _ = bus.packet_handler.read1ByteTxRx(bus.port_handler, motor_id, 0)  # Firmware_Major
            minor, comm_min, _ = bus.packet_handler.read1ByteTxRx(bus.port_handler, motor_id, 1)  # Firmware_Minor
            if comm_maj == 0 and comm_min == 0:
                version = f"v{major}.{minor}"
                if minor < EXPECTED_FIRMWARE_MINOR:
                    fail(f"{name} (ID {motor_id}): firmware {version} — NEEDS UPDATE to v{major}.{EXPECTED_FIRMWARE_MINOR}+")
                else:
                    ok(f"{name} (ID {motor_id}): firmware {version}")
            else:
                fail(f"{name} (ID {motor_id}): cannot read firmware version")
        except Exception as e:
            fail(f"{name} (ID {motor_id}): firmware read error: {e}")

    bus.port_handler.closePort()


# ── Phase 4: Voltage & Temperature ──────────────────────────────────────────
def phase4_power(arm_name, port, calibration):
    header(f"PHASE 4: Voltage & Temperature - {arm_name}")

    bus = FeetechMotorsBus(port=port, motors=make_motors(), calibration=calibration)
    try:
        bus.port_handler.openPort()
        bus.port_handler.setBaudRate(1_000_000)
    except Exception as e:
        fail(f"Cannot open {port}: {e}")
        return

    for name, motor_id in zip(MOTOR_NAMES, MOTOR_IDS):
        try:
            voltage_raw, comm_v, _ = bus.packet_handler.read1ByteTxRx(bus.port_handler, motor_id, 62)
            temp_raw, comm_t, _ = bus.packet_handler.read1ByteTxRx(bus.port_handler, motor_id, 63)

            if comm_v != 0 or comm_t != 0:
                fail(f"{name} (ID {motor_id}): cannot read voltage/temperature")
                continue

            voltage = voltage_raw / 10.0
            temp = temp_raw

            status = []
            if voltage < VOLTAGE_MIN:
                status.append(f"{RED}LOW VOLTAGE{RESET}")
            elif voltage > VOLTAGE_MAX:
                status.append(f"{RED}OVER VOLTAGE{RESET}")
            else:
                status.append(f"{GREEN}voltage OK{RESET}")

            if temp >= TEMP_CRIT:
                status.append(f"{RED}CRITICAL TEMP{RESET}")
            elif temp >= TEMP_WARN:
                status.append(f"{YELLOW}warm{RESET}")
            else:
                status.append(f"{GREEN}temp OK{RESET}")

            msg = f"{name} (ID {motor_id}): {voltage:.1f}V, {temp}°C [{', '.join(status)}]"
            if voltage < VOLTAGE_MIN or voltage > VOLTAGE_MAX or temp >= TEMP_CRIT:
                fail(msg)
            elif temp >= TEMP_WARN:
                warn(msg)
            else:
                ok(msg)

        except Exception as e:
            fail(f"{name} (ID {motor_id}): read error: {e}")

    bus.port_handler.closePort()


# ── Phase 5: Status Register & Error Flags ───────────────────────────────────
def phase5_status(arm_name, port, calibration):
    header(f"PHASE 5: Status Register & Error Flags - {arm_name}")

    bus = FeetechMotorsBus(port=port, motors=make_motors(), calibration=calibration)
    try:
        bus.port_handler.openPort()
        bus.port_handler.setBaudRate(1_000_000)
    except Exception as e:
        fail(f"Cannot open {port}: {e}")
        return

    for name, motor_id in zip(MOTOR_NAMES, MOTOR_IDS):
        try:
            status, comm, _ = bus.packet_handler.read1ByteTxRx(bus.port_handler, motor_id, 65)
            if comm != 0:
                fail(f"{name} (ID {motor_id}): cannot read status register")
                continue

            flags = []
            if status & 1: flags.append("VOLTAGE_ERR")
            if status & 2: flags.append("ANGLE_SENSOR_ERR")
            if status & 4: flags.append("OVERHEAT_ERR")
            if status & 8: flags.append("OVERCURRENT_ERR")
            if status & 32: flags.append("OVERLOAD_ERR")

            if flags:
                fail(f"{name} (ID {motor_id}): STATUS={status} FLAGS: {', '.join(flags)}")
            else:
                ok(f"{name} (ID {motor_id}): status={status} (clean)")

        except Exception as e:
            fail(f"{name} (ID {motor_id}): status read error: {e}")

    bus.port_handler.closePort()


# ── Phase 6: EEPROM Configuration Dump ───────────────────────────────────────
def phase6_config(arm_name, port, calibration):
    header(f"PHASE 6: EEPROM Configuration - {arm_name}")

    bus = FeetechMotorsBus(port=port, motors=make_motors(), calibration=calibration)
    try:
        bus.port_handler.openPort()
        bus.port_handler.setBaudRate(1_000_000)
    except Exception as e:
        fail(f"Cannot open {port}: {e}")
        return

    registers_1byte = [
        ("Baud_Rate", 6), ("Return_Delay_Time", 7), ("Response_Status_Level", 8),
        ("Max_Temperature_Limit", 13), ("Max_Voltage_Limit", 14), ("Min_Voltage_Limit", 15),
        ("P_Coefficient", 21), ("D_Coefficient", 22), ("I_Coefficient", 23),
        ("Operating_Mode", 33), ("Torque_Enable", 40), ("Acceleration", 41),
    ]
    registers_2byte = [
        ("Min_Position_Limit", 9), ("Max_Position_Limit", 11),
        ("Max_Torque_Limit", 16), ("Protection_Current", 28),
        ("Homing_Offset", 31),
    ]

    for name, motor_id in zip(MOTOR_NAMES, MOTOR_IDS):
        info(f"\n  {BOLD}{name} (ID {motor_id}):{RESET}")
        row = {}
        for reg_name, addr in registers_1byte:
            val, comm, _ = bus.packet_handler.read1ByteTxRx(bus.port_handler, motor_id, addr)
            if comm == 0:
                row[reg_name] = val
            else:
                row[reg_name] = "ERR"
        for reg_name, addr in registers_2byte:
            val, comm, _ = bus.packet_handler.read2ByteTxRx(bus.port_handler, motor_id, addr)
            if comm == 0:
                row[reg_name] = val
            else:
                row[reg_name] = "ERR"

        for reg_name, val in row.items():
            info(f"    {reg_name:35s} = {val}")

        # Flag suspicious values
        if row.get("Return_Delay_Time") == 0:
            warn(f"{name}: Return_Delay_Time=0 (2us) - may cause comm issues with some USB adapters")
        if row.get("Min_Voltage_Limit", 99) > 10:
            warn(f"{name}: Min_Voltage_Limit={row['Min_Voltage_Limit']} (high threshold)")
        if row.get("Protection_Current", 0) == 0:
            warn(f"{name}: Protection_Current=0 (no current protection!)")

    bus.port_handler.closePort()


# ── Phase 7: Communication Reliability ───────────────────────────────────────
def phase7_comms(arm_name, port, calibration):
    header(f"PHASE 7: Communication Reliability - {arm_name}")
    info(f"  Running 200 sync_read cycles (no torque)...")

    bus = FeetechMotorsBus(port=port, motors=make_motors(), calibration=calibration)
    try:
        bus.connect()
    except Exception as e:
        fail(f"Cannot connect to {arm_name}: {e}")
        return

    success = 0
    failures = 0
    latencies = []
    for i in range(200):
        try:
            t0 = time.perf_counter()
            bus.sync_read("Present_Position")
            dt = (time.perf_counter() - t0) * 1000
            latencies.append(dt)
            success += 1
        except Exception:
            failures += 1

    bus.disconnect()

    pct = success / 200 * 100
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        info(f"  Results: {success}/200 ({pct:.0f}%) success, {failures} failures")
        info(f"  Latency: avg={avg_lat:.1f}ms, max={max_lat:.1f}ms")
        if pct == 100:
            ok(f"{arm_name} comms: 100% reliable (no torque)")
        elif pct >= 95:
            warn(f"{arm_name} comms: {pct:.0f}% reliable — marginal")
        else:
            fail(f"{arm_name} comms: {pct:.0f}% reliable — UNSTABLE")
    else:
        fail(f"{arm_name} comms: ALL reads failed")


# ── Phase 8: Torque Stress Test ──────────────────────────────────────────────
def phase8_torque_stress(arm_name, port, calibration):
    header(f"PHASE 8: Torque Stress Test - {arm_name}")
    info("  Enabling torque, writing current position, reading 200 cycles...")

    bus = FeetechMotorsBus(port=port, motors=make_motors(), calibration=calibration)
    try:
        bus.connect()
    except Exception as e:
        fail(f"Cannot connect to {arm_name}: {e}")
        return

    # Configure like teleop does
    try:
        bus.disable_torque()
        bus.configure_motors(return_delay_time=0)
        for motor in bus.motors:
            bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
            bus.write("P_Coefficient", motor, 16)
            bus.write("I_Coefficient", motor, 0)
            bus.write("D_Coefficient", motor, 32)
            if motor == "gripper":
                bus.write("Max_Torque_Limit", motor, 500)
        bus.enable_torque()
    except Exception as e:
        fail(f"Cannot configure {arm_name}: {e}")
        bus.disconnect()
        return

    success = 0
    failures = 0
    fail_at = None
    for i in range(200):
        try:
            pos = bus.sync_read("Present_Position")
            bus.sync_write("Goal_Position", pos)  # Write own position (no movement)
            success += 1
        except Exception as e:
            failures += 1
            if fail_at is None:
                fail_at = i

    try:
        bus.disable_torque()
    except Exception:
        pass
    bus.disconnect()

    pct = success / 200 * 100
    info(f"  Results: {success}/200 ({pct:.0f}%) success, {failures} failures")
    if fail_at is not None:
        info(f"  First failure at cycle {fail_at}")
    if pct == 100:
        ok(f"{arm_name} torque stress: 100% reliable")
    elif pct >= 95:
        warn(f"{arm_name} torque stress: {pct:.0f}% reliable — marginal")
    else:
        fail(f"{arm_name} torque stress: {pct:.0f}% reliable — UNSTABLE")


# ── Phase 9: Cross-Bus Stress Test (Teleop Simulation) ──────────────────────
def phase9_teleop_sim():
    header("PHASE 9: Cross-Bus Teleop Simulation")
    info("  Reading leader + writing follower for 500 cycles with torque...")

    fcal = load_calibration(FOLLOWER_CAL)
    lcal = load_calibration(LEADER_CAL)
    if not fcal or not lcal:
        fail("Missing calibration files — cannot run teleop sim")
        return

    follower = FeetechMotorsBus(FOLLOWER_PORT, make_motors(), calibration=fcal)
    leader = FeetechMotorsBus(LEADER_PORT, make_motors(), calibration=lcal)

    try:
        follower.connect()
        leader.connect()
    except Exception as e:
        fail(f"Cannot connect both arms: {e}")
        return

    # Configure follower with torque
    try:
        follower.disable_torque()
        follower.configure_motors(return_delay_time=0)
        for motor in follower.motors:
            follower.write("Operating_Mode", motor, OperatingMode.POSITION.value)
            follower.write("P_Coefficient", motor, 16)
            follower.write("I_Coefficient", motor, 0)
            follower.write("D_Coefficient", motor, 32)
            if motor == "gripper":
                follower.write("Max_Torque_Limit", motor, 500)
        follower.enable_torque()
    except Exception as e:
        fail(f"Cannot configure follower: {e}")
        follower.disconnect()
        leader.disconnect()
        return

    success = 0
    failures = 0
    fail_at = None
    retry_cycles = 0
    voltage_readings = []

    for i in range(500):
        try:
            fpos = follower.sync_read("Present_Position", num_retry=10)
            lpos = leader.sync_read("Present_Position", num_retry=10)
            follower.sync_write("Goal_Position", lpos)
            success += 1

            # Sample voltage every 50 cycles
            if i % 50 == 0:
                try:
                    v, comm, _ = follower.packet_handler.read1ByteTxRx(
                        follower.port_handler, 1, 62
                    )
                    if comm == 0:
                        voltage_readings.append((i, v / 10.0))
                except Exception:
                    pass

        except Exception as e:
            failures += 1
            if fail_at is None:
                fail_at = i

    try:
        follower.disable_torque()
    except Exception:
        pass

    follower.disconnect()
    leader.disconnect()

    pct = success / 500 * 100
    info(f"  Results: {success}/500 ({pct:.0f}%) success, {failures} failures")
    if fail_at is not None:
        info(f"  First failure at cycle {fail_at}")
    if voltage_readings:
        info(f"  Voltage samples during test:")
        for cycle, v in voltage_readings:
            marker = f" {RED}<-- LOW{RESET}" if v < VOLTAGE_MIN else ""
            info(f"    Cycle {cycle:4d}: {v:.1f}V{marker}")

    if pct == 100:
        ok("Teleop simulation: 500 cycles, 100% reliable")
    elif pct >= 98:
        warn(f"Teleop simulation: {pct:.1f}% reliable — occasional drops, retries should handle it")
    elif pct >= 90:
        warn(f"Teleop simulation: {pct:.1f}% reliable — needs investigation")
    else:
        fail(f"Teleop simulation: {pct:.1f}% reliable — UNSTABLE")


# ── Phase 10: Individual Motor Isolation Test ────────────────────────────────
def phase10_isolation(arm_name, port, calibration):
    header(f"PHASE 10: Individual Motor Isolation - {arm_name}")
    info("  Testing each motor individually to find the weak link...")

    bus = FeetechMotorsBus(port=port, motors=make_motors(), calibration=calibration)
    try:
        bus.port_handler.openPort()
        bus.port_handler.setBaudRate(1_000_000)
    except Exception as e:
        fail(f"Cannot open {port}: {e}")
        return

    for name, motor_id in zip(MOTOR_NAMES, MOTOR_IDS):
        success = 0
        failures = 0
        for i in range(100):
            try:
                val, comm, error = bus.packet_handler.read2ByteTxRx(bus.port_handler, motor_id, 56)
                if comm == 0:
                    success += 1
                else:
                    failures += 1
            except Exception:
                failures += 1

        pct = success / 100 * 100
        if pct == 100:
            ok(f"{name} (ID {motor_id}): 100/100 reads OK")
        elif pct >= 95:
            warn(f"{name} (ID {motor_id}): {success}/100 reads OK — marginal")
        else:
            fail(f"{name} (ID {motor_id}): {success}/100 reads OK — FAULTY MOTOR OR CABLE")

    bus.port_handler.closePort()


# ── Phase 11: Calibration File Validation ────────────────────────────────────
def phase11_calibration():
    header("PHASE 11: Calibration File Validation")

    for arm_name, cal_path in [("Follower", FOLLOWER_CAL), ("Leader", LEADER_CAL)]:
        cal = load_calibration(cal_path)
        if cal is None:
            fail(f"{arm_name}: calibration file not found at {cal_path}")
            continue

        ok(f"{arm_name}: calibration file loaded ({len(cal)} motors)")

        for name, mc in cal.items():
            issues = []
            if mc.range_min >= mc.range_max:
                issues.append(f"range_min({mc.range_min}) >= range_max({mc.range_max})")
            if mc.range_max - mc.range_min < 100 and name != "gripper":
                issues.append(f"tiny range ({mc.range_max - mc.range_min}) — recalibrate?")
            if name == "gripper" and mc.range_max - mc.range_min < 3:
                issues.append(f"gripper range only {mc.range_max - mc.range_min} — may not open/close")

            if issues:
                fail(f"  {arm_name}/{name}: {'; '.join(issues)}")
            else:
                ok(f"  {arm_name}/{name}: range=[{mc.range_min}, {mc.range_max}], offset={mc.homing_offset}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print(f"\n{BOLD}{CYAN}{'=' * 60}")
    print(f"  SO-101 ARM DIAGNOSTIC TOOL")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}{RESET}")

    fcal = load_calibration(FOLLOWER_CAL)
    lcal = load_calibration(LEADER_CAL)

    # Run all phases
    phase1_ports()

    follower_motors = phase2_ping("Follower", FOLLOWER_PORT, fcal)
    leader_motors = phase2_ping("Leader", LEADER_PORT, lcal)

    if follower_motors:
        phase3_firmware("Follower", FOLLOWER_PORT, fcal)
    if leader_motors:
        phase3_firmware("Leader", LEADER_PORT, lcal)

    if follower_motors:
        phase4_power("Follower", FOLLOWER_PORT, fcal)
    if leader_motors:
        phase4_power("Leader", LEADER_PORT, lcal)

    if follower_motors:
        phase5_status("Follower", FOLLOWER_PORT, fcal)
    if leader_motors:
        phase5_status("Leader", LEADER_PORT, lcal)

    if follower_motors:
        phase6_config("Follower", FOLLOWER_PORT, fcal)
    if leader_motors:
        phase6_config("Leader", LEADER_PORT, lcal)

    phase11_calibration()

    if follower_motors:
        phase10_isolation("Follower", FOLLOWER_PORT, fcal)
    if leader_motors:
        phase10_isolation("Leader", LEADER_PORT, lcal)

    if fcal:
        phase7_comms("Follower", FOLLOWER_PORT, fcal)
    if lcal:
        phase7_comms("Leader", LEADER_PORT, lcal)

    if fcal:
        phase8_torque_stress("Follower", FOLLOWER_PORT, fcal)

    if fcal and lcal:
        phase9_teleop_sim()

    # ── Summary ──────────────────────────────────────────────────────────────
    header("SUMMARY")
    if not issues_found:
        ok("All tests passed — no issues detected")
    else:
        fails = [msg for level, msg in issues_found if level == "FAIL"]
        warns = [msg for level, msg in issues_found if level == "WARN"]
        if fails:
            print(f"\n  {RED}{BOLD}{len(fails)} FAILURE(S):{RESET}")
            for msg in fails:
                print(f"    {RED}✗{RESET} {msg}")
        if warns:
            print(f"\n  {YELLOW}{BOLD}{len(warns)} WARNING(S):{RESET}")
            for msg in warns:
                print(f"    {YELLOW}!{RESET} {msg}")

    print()


if __name__ == "__main__":
    main()
