"""First-Run Wizard — guided setup from hardware detection to mesh join.

Launches automatically on first boot (no ~/.citizenry/ directory).
Re-runnable via `python -m citizenry setup`.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..detection.usb_monitor import USBMonitor
from ..detection.device_db import DeviceInfo
from ..detection.camera_scan import scan_cameras
from ..detection.citizen_factory import detect_and_identify, save_device_mapping
from ..hal.profile_loader import load_all_profiles, RobotProfile


BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"
CITIZENRY_DIR = Path.home() / ".citizenry"


def is_first_run() -> bool:
    """Check if this is the first time armOS is running."""
    return not CITIZENRY_DIR.exists()


def run_wizard() -> dict | None:
    """Run the first-run wizard. Returns setup result or None if cancelled.

    Returns dict with: citizen_name, profile, port, driver_type
    """
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  Welcome to armOS!                                           ║{RESET}")
    print(f"{BOLD}{CYAN}║  Let's set up your robot.                                    ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}")

    # Step 1: Detect hardware
    print(f"\n{BOLD}Step 1: Detecting hardware...{RESET}")
    result = step_detect()
    if result is None:
        return None

    # Step 2: Identify robot
    print(f"\n{BOLD}Step 2: Identifying robot...{RESET}")
    identified = step_identify(result)
    if identified is None:
        return None

    # Step 3: Calibrate
    print(f"\n{BOLD}Step 3: Calibration{RESET}")
    step_calibrate(identified)

    # Step 4: Complete
    print(f"\n{BOLD}Step 4: Completing setup{RESET}")
    setup_result = step_complete(identified)

    return setup_result


def step_detect() -> list[DeviceInfo] | None:
    """Scan for connected hardware."""
    monitor = USBMonitor()
    devices = monitor.scan_current()

    servo_devices = [d for d in devices if d.driver_type != "unknown"]
    cameras = scan_cameras()

    if not servo_devices and not cameras:
        print(f"  {YELLOW}No hardware detected.{RESET}")
        print(f"  {DIM}Please plug in a servo controller (Feetech or Dynamixel).{RESET}")
        response = input(f"  Press Enter to scan again, or 'q' to quit: ").strip()
        if response.lower() == 'q':
            return None
        return step_detect()

    print(f"  {GREEN}Found:{RESET}")
    for d in servo_devices:
        print(f"    {GREEN}●{RESET} {d.device_name} on {d.port}")
    for c in cameras:
        print(f"    {GREEN}●{RESET} Camera: {c.name} on {c.device_path}")

    if not servo_devices:
        print(f"  {YELLOW}No servo controller found. Only cameras detected.{RESET}")
        print(f"  {DIM}Plug in a servo controller to set up an arm.{RESET}")

    return servo_devices if servo_devices else None


def step_identify(devices: list[DeviceInfo]) -> dict | None:
    """Identify what robot is connected."""
    for device in devices:
        print(f"\n  Scanning {device.device_name} on {device.port}...")
        result = detect_and_identify(device)

        if result is None:
            print(f"  {YELLOW}Could not identify robot on {device.port}{RESET}")
            continue

        profile = result.get("profile")
        if profile:
            print(f"  {GREEN}●{RESET} Found {result['motor_count']} motors — this looks like a {BOLD}{profile.name}{RESET}")
            response = input(f"  Correct? [Y/n/list]: ").strip().lower()
            if response in ('', 'y', 'yes'):
                return result
            elif response == 'list':
                profiles = load_all_profiles()
                print(f"\n  {BOLD}Available profiles:{RESET}")
                for i, p in enumerate(profiles):
                    print(f"    {i+1}. {p.name} ({p.driver}, {p.motor_count} motors)")
                choice = input(f"  Select profile number: ").strip()
                try:
                    idx = int(choice) - 1
                    result["profile"] = profiles[idx]
                    return result
                except (ValueError, IndexError):
                    print(f"  {YELLOW}Invalid selection{RESET}")
                    continue
            # User said no — skip this device
        else:
            print(f"  {YELLOW}Found {result['motor_count']} motors but no matching profile.{RESET}")
            profiles = load_all_profiles()
            matching = [p for p in profiles if p.driver == device.driver_type]
            if matching:
                print(f"  {BOLD}Compatible profiles:{RESET}")
                for i, p in enumerate(matching):
                    print(f"    {i+1}. {p.name}")
                choice = input(f"  Select profile number (or Enter to skip): ").strip()
                if choice:
                    try:
                        result["profile"] = matching[int(choice) - 1]
                        return result
                    except (ValueError, IndexError):
                        pass

    return None


def step_calibrate(identified: dict) -> None:
    """Run basic calibration."""
    profile = identified.get("profile")
    if profile:
        print(f"  Loading {profile.name} defaults...")
        homes = profile.home_positions()
        print(f"  {GREEN}●{RESET} Home positions loaded from profile")
        print(f"  {DIM}For fine calibration, run 'calibrate camera' after setup.{RESET}")
    else:
        print(f"  {DIM}No profile — skipping calibration. Run 'calibrate camera' later.{RESET}")


def step_complete(identified: dict) -> dict:
    """Complete the setup — create citizen identity and persist."""
    CITIZENRY_DIR.mkdir(parents=True, exist_ok=True)

    citizen_name = identified.get("citizen_name", "arm-1")
    profile = identified.get("profile")
    serial = identified.get("serial", "")

    # Save device mapping
    if serial and profile:
        save_device_mapping(serial, citizen_name, profile.name)

    print(f"\n  {GREEN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"  {GREEN}║  Setup complete!                                         ║{RESET}")
    print(f"  {GREEN}║                                                          ║{RESET}")
    print(f"  {GREEN}║  Citizen: {citizen_name:<46} ║{RESET}")
    if profile:
        print(f"  {GREEN}║  Profile: {profile.name:<46} ║{RESET}")
    print(f"  {GREEN}║  Port:    {identified.get('port', '?'):<46} ║{RESET}")
    print(f"  {GREEN}║                                                          ║{RESET}")
    print(f"  {GREEN}║  Type 'help' to get started.                             ║{RESET}")
    print(f"  {GREEN}╚══════════════════════════════════════════════════════════╝{RESET}")

    return {
        "citizen_name": citizen_name,
        "profile": profile,
        "port": identified.get("port"),
        "driver_type": identified.get("driver_type"),
    }
