"""Tests for the Hardware Abstraction Layer."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from armos.hal.servo_driver import ServoDriver, MotorInfo
from armos.hal.motor_scanner import scan_bus, ScanResult
from armos.hal.profile_loader import (
    load_profile, load_all_profiles, match_profile,
    RobotProfile, MotorConfig, PROFILES_DIR,
)


class TestServoDriverABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ServoDriver()

    def test_motor_info(self):
        m = MotorInfo(id=1, model="sts3215")
        assert m.id == 1
        assert m.model == "sts3215"


class TestMotorScanner:
    def test_scan_result(self):
        r = ScanResult(port="/dev/ttyACM0", protocol="feetech", motors=[
            MotorInfo(id=1), MotorInfo(id=2), MotorInfo(id=3),
        ])
        assert r.motor_count == 3
        assert r.protocol == "feetech"

    def test_scan_with_mock_driver(self):
        driver = MagicMock(spec=ServoDriver)
        driver.protocol_name = "feetech"
        driver.scan_motors.return_value = [
            MotorInfo(id=1, model="sts3215"),
            MotorInfo(id=2, model="sts3215"),
        ]
        result = scan_bus(driver, "/dev/ttyACM0")
        assert result.motor_count == 2
        assert result.protocol == "feetech"
        driver.connect.assert_called_once_with("/dev/ttyACM0")
        driver.disconnect.assert_called_once()

    def test_scan_connection_failure(self):
        driver = MagicMock(spec=ServoDriver)
        driver.protocol_name = "feetech"
        driver.connect.side_effect = Exception("port busy")
        result = scan_bus(driver, "/dev/ttyACM0")
        assert result.motor_count == 0


class TestProfiles:
    def test_so101_exists(self):
        assert (PROFILES_DIR / "so101.json").exists()

    def test_koch_exists(self):
        assert (PROFILES_DIR / "koch_v1.json").exists()

    def test_load_so101(self):
        profile = load_profile("so101")
        assert profile is not None
        assert profile.name == "SO-101"
        assert profile.driver == "feetech"
        assert profile.motor_count == 6
        assert "shoulder_pan" in profile.motors
        assert profile.motors["shoulder_pan"].id == 1
        assert profile.motors["shoulder_pan"].home == 2048
        assert "6dof_arm" in profile.capabilities

    def test_load_koch(self):
        profile = load_profile("koch_v1")
        assert profile is not None
        assert profile.name == "Koch v1.1"
        assert profile.driver == "dynamixel"
        assert profile.motor_count == 6

    def test_load_nonexistent(self):
        assert load_profile("nonexistent") is None

    def test_load_all(self):
        profiles = load_all_profiles()
        assert len(profiles) >= 2
        names = [p.name for p in profiles]
        assert "SO-101" in names
        assert "Koch v1.1" in names

    def test_motor_ids(self):
        profile = load_profile("so101")
        ids = profile.motor_ids()
        assert sorted(ids) == [1, 2, 3, 4, 5, 6]

    def test_home_positions(self):
        profile = load_profile("so101")
        homes = profile.home_positions()
        assert homes["shoulder_pan"] == 2048
        assert homes["shoulder_lift"] == 1400
        assert homes["elbow_flex"] == 3000

    def test_to_genome_dict(self):
        profile = load_profile("so101")
        genome = profile.to_genome_dict()
        assert genome["citizen_type"] == "manipulator"
        assert genome["hardware"]["driver"] == "feetech"
        assert genome["calibration"]["shoulder_pan"] == 2048


class TestProfileMatching:
    def test_match_feetech_6_motors(self):
        motors = [MotorInfo(id=i, model="sts3215") for i in range(1, 7)]
        profile = match_profile("feetech", motors)
        assert profile is not None
        assert profile.name == "SO-101"

    def test_match_dynamixel_6_motors(self):
        motors = [MotorInfo(id=i, model="xl330") for i in range(1, 7)]
        profile = match_profile("dynamixel", motors)
        assert profile is not None
        assert profile.name == "Koch v1.1"

    def test_no_match_wrong_protocol(self):
        motors = [MotorInfo(id=i) for i in range(1, 7)]
        profile = match_profile("canbus", motors)
        assert profile is None

    def test_no_match_wrong_count(self):
        motors = [MotorInfo(id=i) for i in range(1, 4)]  # Only 3 motors
        profile = match_profile("feetech", motors)
        assert profile is None

    def test_match_by_count_fallback(self):
        # IDs don't match profile but count + driver do
        motors = [MotorInfo(id=i) for i in range(10, 16)]
        profile = match_profile("feetech", motors)
        assert profile is not None  # Fallback match by count


class TestFeetechDriver:
    def test_protocol_name(self):
        from armos.hal.feetech_driver import FeetechDriver
        d = FeetechDriver()
        assert d.protocol_name == "feetech"
        assert not d.is_connected

    def test_not_connected_returns_defaults(self):
        from armos.hal.feetech_driver import FeetechDriver
        d = FeetechDriver()
        assert d.read_position(1) == 0
        assert d.read_voltage(1) == 0.0
        assert d.read_temperature(1) == 0.0
        assert d.sync_read_positions([1, 2]) == {}


class TestDynamixelDriver:
    def test_protocol_name(self):
        from armos.hal.dynamixel_driver import DynamixelDriver
        d = DynamixelDriver()
        assert d.protocol_name == "dynamixel"
        assert not d.is_connected

    def test_not_connected_returns_defaults(self):
        from armos.hal.dynamixel_driver import DynamixelDriver
        d = DynamixelDriver()
        assert d.read_position(1) == 0
        assert d.read_voltage(1) == 0.0
        assert d.read_temperature(1) == 0.0
