"""Citizen Factory — create the right citizen from detected hardware.

Given a DeviceInfo from auto-detection, creates the appropriate citizen
(ArmCitizen with the right driver, or CameraCitizen).
"""

from __future__ import annotations

import json
from pathlib import Path

from .device_db import DeviceInfo
from ..hal.servo_driver import ServoDriver
from ..hal.motor_scanner import scan_bus
from ..hal.profile_loader import match_profile, RobotProfile


# Device serial → citizen identity mapping
DEVICE_MAP_PATH = Path.home() / ".citizenry" / "device_map.json"


def create_driver(driver_type: str) -> ServoDriver | None:
    """Create the appropriate ServoDriver for a device type."""
    if driver_type == "feetech":
        from ..hal.feetech_driver import FeetechDriver
        return FeetechDriver()
    elif driver_type == "dynamixel":
        from ..hal.dynamixel_driver import DynamixelDriver
        return DynamixelDriver()
    return None


def detect_and_identify(device: DeviceInfo) -> dict | None:
    """Detect hardware and identify the robot.

    Returns a dict with: driver_type, profile, motors, citizen_name, port
    Or None if identification fails.
    """
    if device.driver_type == "unknown":
        return None

    driver = create_driver(device.driver_type)
    if driver is None:
        return None

    # Scan for motors
    scan = scan_bus(driver, device.port)
    if scan.motor_count == 0:
        return None

    # Match against profiles
    profile = match_profile(device.driver_type, scan.motors)

    # Check device map for existing identity
    existing = load_device_map().get(device.serial)

    citizen_name = None
    if existing:
        citizen_name = existing.get("citizen_name")

    if citizen_name is None:
        if profile:
            citizen_name = profile.name.lower().replace(" ", "-")
        else:
            citizen_name = f"arm-{device.serial[:6]}" if device.serial else f"arm-{device.port.split('/')[-1]}"

    return {
        "driver_type": device.driver_type,
        "profile": profile,
        "motors": scan.motors,
        "motor_count": scan.motor_count,
        "citizen_name": citizen_name,
        "port": device.port,
        "serial": device.serial,
    }


def save_device_mapping(serial: str, citizen_name: str, profile_name: str) -> None:
    """Save a device serial → citizen identity mapping."""
    device_map = load_device_map()
    device_map[serial] = {
        "citizen_name": citizen_name,
        "profile": profile_name,
    }
    DEVICE_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DEVICE_MAP_PATH.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(device_map, indent=2) + "\n")
        tmp.replace(DEVICE_MAP_PATH)
    except OSError:
        if tmp.exists():
            tmp.unlink()


def load_device_map() -> dict:
    """Load the device serial → citizen identity map."""
    try:
        return json.loads(DEVICE_MAP_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
