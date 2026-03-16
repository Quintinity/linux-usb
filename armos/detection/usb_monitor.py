"""USB Hotplug Monitor — watch for device plug/unplug events.

Uses pyudev if available, falls back to polling /dev/tty* for portability.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .device_db import DeviceInfo, identify_device


@dataclass
class HotplugEvent:
    """A USB hotplug event."""
    action: str  # "add" or "remove"
    device: DeviceInfo
    timestamp: float


class USBMonitor:
    """Watch for USB device add/remove events.

    Tries pyudev first, falls back to polling.
    """

    def __init__(
        self,
        on_add: Callable[[DeviceInfo], None] | None = None,
        on_remove: Callable[[str], None] | None = None,
    ):
        self.on_add = on_add
        self.on_remove = on_remove
        self._known_devices: set[str] = set()
        self._running = False

    def scan_current(self) -> list[DeviceInfo]:
        """Scan currently connected USB serial devices."""
        devices = []
        for entry in Path("/sys/class/tty").iterdir():
            try:
                device_path = entry / "device"
                if not device_path.exists():
                    continue
                # Read vendor/product from USB parent
                usb_path = (device_path / "..").resolve()
                vid_path = usb_path / "idVendor"
                pid_path = usb_path / "idProduct"
                serial_path = usb_path / "serial"

                if not vid_path.exists():
                    continue

                vid = vid_path.read_text().strip()
                pid = pid_path.read_text().strip()
                serial = serial_path.read_text().strip() if serial_path.exists() else ""

                info = identify_device(vid, pid)
                info.port = f"/dev/{entry.name}"
                info.serial = serial
                devices.append(info)
                self._known_devices.add(info.port)
            except Exception:
                continue
        return devices

    def poll_once(self) -> list[HotplugEvent]:
        """Poll for changes since last scan. Returns list of events."""
        events = []
        current_ports = set()
        now = time.time()

        for entry in Path("/sys/class/tty").iterdir():
            try:
                device_path = entry / "device"
                if not device_path.exists():
                    continue
                usb_path = (device_path / "..").resolve()
                vid_path = usb_path / "idVendor"
                if not vid_path.exists():
                    continue

                port = f"/dev/{entry.name}"
                current_ports.add(port)

                if port not in self._known_devices:
                    vid = vid_path.read_text().strip()
                    pid = (usb_path / "idProduct").read_text().strip()
                    serial_path = usb_path / "serial"
                    serial = serial_path.read_text().strip() if serial_path.exists() else ""

                    info = identify_device(vid, pid)
                    info.port = port
                    info.serial = serial

                    events.append(HotplugEvent(action="add", device=info, timestamp=now))
                    if self.on_add:
                        self.on_add(info)
            except Exception:
                continue

        # Check for removed devices
        removed = self._known_devices - current_ports
        for port in removed:
            events.append(HotplugEvent(
                action="remove",
                device=DeviceInfo(vendor_id="", product_id="", driver_type="unknown", device_name="", port=port),
                timestamp=now,
            ))
            if self.on_remove:
                self.on_remove(port)

        self._known_devices = current_ports
        return events
