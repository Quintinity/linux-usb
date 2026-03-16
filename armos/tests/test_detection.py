"""Tests for hardware auto-detection."""

import pytest
from unittest.mock import MagicMock, patch
from armos.detection.device_db import identify_device, DeviceInfo, KNOWN_DEVICES, list_known_devices
from armos.detection.citizen_factory import create_driver, detect_and_identify, load_device_map
from armos.detection.camera_scan import CameraInfo
from armos.detection.usb_monitor import USBMonitor, HotplugEvent


class TestDeviceDB:
    def test_feetech_ch340(self):
        info = identify_device("1a86", "55d3")
        assert info.driver_type == "feetech"
        assert "CH340" in info.device_name

    def test_dynamixel_ftdi(self):
        info = identify_device("0403", "6014")
        assert info.driver_type == "dynamixel"

    def test_unknown_device(self):
        info = identify_device("dead", "beef")
        assert info.driver_type == "unknown"

    def test_case_insensitive(self):
        info = identify_device("1A86", "55D3")
        assert info.driver_type == "feetech"

    def test_list_known(self):
        known = list_known_devices()
        assert len(known) >= 4
        assert any("feetech" in d[1] for d in known)
        assert any("dynamixel" in d[1] for d in known)


class TestCitizenFactory:
    def test_create_feetech_driver(self):
        driver = create_driver("feetech")
        assert driver is not None
        assert driver.protocol_name == "feetech"

    def test_create_dynamixel_driver(self):
        driver = create_driver("dynamixel")
        assert driver is not None
        assert driver.protocol_name == "dynamixel"

    def test_create_unknown_driver(self):
        assert create_driver("canbus") is None

    def test_load_empty_device_map(self):
        # Should return empty dict when file doesn't exist
        dm = load_device_map()
        assert isinstance(dm, dict)


class TestCameraInfo:
    def test_create(self):
        c = CameraInfo(device_path="/dev/video0", name="USB Cam")
        assert c.device_path == "/dev/video0"
        assert c.resolutions == []


class TestUSBMonitor:
    def test_init(self):
        monitor = USBMonitor()
        assert len(monitor._known_devices) == 0

    def test_hotplug_event(self):
        event = HotplugEvent(
            action="add",
            device=DeviceInfo("1a86", "55d3", "feetech", "CH340"),
            timestamp=1000.0,
        )
        assert event.action == "add"
        assert event.device.driver_type == "feetech"


class TestWizard:
    def test_is_first_run(self):
        from armos.wizard.wizard import is_first_run
        # Will be False since ~/.citizenry/ exists from our testing
        result = is_first_run()
        assert isinstance(result, bool)
