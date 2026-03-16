---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - prd.md
  - product-brief.md
  - citizenry/ (30 modules)
workflowType: 'architecture'
---

# Architecture — armOS v2.0

**Date:** 2026-03-16
**Status:** Approved

---

## System Overview

armOS v2.0 adds a **product shell** around the existing citizenry protocol. Five new subsystems sit below and beside the citizenry layer:

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                               │
│  First-Run Wizard │ Governor CLI │ Web Dashboard                 │
├─────────────────────────────────────────────────────────────────┤
│                    CITIZENRY PROTOCOL (existing)                 │
│  30 modules │ 7 messages │ Ed25519 │ marketplace │ NL governance │
├─────────────────────────────────────────────────────────────────┤
│                  HARDWARE ABSTRACTION LAYER (new)                │
│  ServoDriver ABC │ FeetechDriver │ DynamixelDriver               │
│  RobotProfile (genome templates) │ Motor Scanner                 │
├─────────────────────────────────────────────────────────────────┤
│                  HARDWARE DETECTION LAYER (new)                  │
│  udev rules │ USB hotplug daemon │ V4L2 camera scan              │
│  Device→Citizen mapping │ Serial number persistence              │
├─────────────────────────────────────────────────────────────────┤
│                     OS IMAGE LAYER (new)                         │
│  live-build config │ casper persistence │ auto-login              │
│  systemd services │ splash screen │ desktop shortcuts             │
├─────────────────────────────────────────────────────────────────┤
│                     CI/CD LAYER (new)                             │
│  GitHub Actions │ ISO build │ test gate │ flash scripts           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Architecture

### New directory structure

```
linux-usb/
├── citizenry/                    # Existing protocol (unchanged)
│   ├── __init__.py ... (30 modules)
│   └── tests/ (257 tests)
│
├── armos/                        # NEW: Product shell
│   ├── __init__.py
│   ├── hal/                      # Hardware Abstraction Layer
│   │   ├── __init__.py
│   │   ├── servo_driver.py       # Abstract ServoDriver ABC
│   │   ├── feetech_driver.py     # Feetech STS3215 implementation
│   │   ├── dynamixel_driver.py   # Dynamixel XL330/XL430 implementation
│   │   ├── motor_scanner.py      # Scan bus for connected motors
│   │   └── profiles/             # Robot genome templates
│   │       ├── so101.json        # SO-101 profile
│   │       └── koch_v1.json      # Koch v1.1 profile
│   │
│   ├── detection/                # Hardware Auto-Detection
│   │   ├── __init__.py
│   │   ├── usb_monitor.py        # udev hotplug daemon
│   │   ├── device_db.py          # USB vendor/product ID database
│   │   ├── camera_scan.py        # V4L2 camera enumeration
│   │   └── citizen_factory.py    # Detected device → citizen instance
│   │
│   ├── wizard/                   # First-Run Experience
│   │   ├── __init__.py
│   │   ├── wizard.py             # Main wizard flow
│   │   ├── detect_step.py        # Hardware detection step
│   │   ├── identify_step.py      # Robot identification step
│   │   ├── calibrate_step.py     # Calibration step
│   │   └── complete_step.py      # Mesh join + completion
│   │
│   └── tests/                    # Product shell tests
│       ├── test_hal.py
│       ├── test_detection.py
│       ├── test_wizard.py
│       └── test_profiles.py
│
├── image/                        # ISO Build System
│   ├── build.sh                  # Main build script
│   ├── live-build/               # live-build configuration
│   │   ├── auto/
│   │   │   ├── config            # live-build auto config
│   │   │   └── build             # live-build auto build
│   │   ├── config/
│   │   │   ├── package-lists/
│   │   │   │   └── armos.list.chroot  # Package list
│   │   │   ├── includes.chroot/  # Files to include in image
│   │   │   │   ├── etc/udev/rules.d/
│   │   │   │   │   └── 99-armos-hardware.rules
│   │   │   │   ├── etc/systemd/system/
│   │   │   │   │   └── armos-governor.service
│   │   │   │   └── usr/local/bin/
│   │   │   │       └── armos-start
│   │   │   └── hooks/
│   │   │       └── 0100-install-armos.hook.chroot
│   │   └── Makefile
│   ├── flash.ps1                 # Windows flash script
│   └── flash.sh                  # Linux/macOS flash script
│
├── .github/
│   └── workflows/
│       ├── test.yml              # Run tests on every push
│       └── build-iso.yml         # Build ISO on release tags
│
└── setup.py / pyproject.toml     # Package config
```

---

## Subsystem Details

### 1. Hardware Abstraction Layer (armos/hal/)

#### ServoDriver ABC

```python
from abc import ABC, abstractmethod

class ServoDriver(ABC):
    """Abstract interface for servo motor communication."""

    @abstractmethod
    def connect(self, port: str, baudrate: int = 1000000) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def read_position(self, motor_id: int) -> int: ...

    @abstractmethod
    def write_position(self, motor_id: int, position: int) -> None: ...

    @abstractmethod
    def sync_read(self, register: str, motor_ids: list[int]) -> dict[int, int]: ...

    @abstractmethod
    def sync_write(self, register: str, values: dict[int, int]) -> None: ...

    @abstractmethod
    def enable_torque(self, motor_ids: list[int] | None = None) -> None: ...

    @abstractmethod
    def disable_torque(self, motor_ids: list[int] | None = None) -> None: ...

    @abstractmethod
    def read_voltage(self, motor_id: int) -> float: ...

    @abstractmethod
    def read_temperature(self, motor_id: int) -> float: ...

    @abstractmethod
    def read_load(self, motor_id: int) -> float: ...

    @abstractmethod
    def scan_motors(self) -> list[int]: ...
```

#### Integration with Citizenry

The existing `pi_citizen.py` uses `lerobot.motors.feetech.FeetechMotorsBus` directly. The HAL wraps this:

```python
class FeetechDriver(ServoDriver):
    """Feetech STS3215 driver — wraps lerobot's FeetechMotorsBus."""

    def connect(self, port, baudrate=1000000):
        from lerobot.motors.feetech.feetech import FeetechMotorsBus
        # ... create bus with motor config from profile
```

A new `HalCitizen` base class (or mixin) replaces direct bus usage in pi_citizen:

```python
class ArmCitizen(Citizen):
    """Generic arm citizen using HAL driver."""

    def __init__(self, driver: ServoDriver, profile: RobotProfile, ...):
        self.driver = driver
        self.profile = profile
        capabilities = profile.capabilities  # ["6dof_arm", "gripper", ...]
        super().__init__(name=profile.name, citizen_type="manipulator", capabilities=capabilities)
```

#### Robot Profiles (Genome Templates)

```json
// armos/hal/profiles/so101.json
{
  "name": "SO-101",
  "driver": "feetech",
  "motor_count": 6,
  "motors": {
    "shoulder_pan": {"id": 1, "model": "sts3215", "range": [0, 4095], "home": 2048},
    "shoulder_lift": {"id": 2, "model": "sts3215", "range": [0, 4095], "home": 1400},
    "elbow_flex": {"id": 3, "model": "sts3215", "range": [0, 4095], "home": 3000},
    "wrist_flex": {"id": 4, "model": "sts3215", "range": [0, 4095], "home": 2048},
    "wrist_roll": {"id": 5, "model": "sts3215", "range": [0, 4095], "home": 2048},
    "gripper": {"id": 6, "model": "sts3215", "range": [0, 4095], "home": 2048}
  },
  "protection": {"max_torque": 500, "protection_current": 250, "max_temperature": 65},
  "capabilities": ["6dof_arm", "gripper", "feetech_sts3215"],
  "skills": ["basic_movement", "basic_grasp", "basic_gesture"]
}
```

### 2. Hardware Auto-Detection (armos/detection/)

#### USB Monitoring via udev + pyudev

```python
# usb_monitor.py
import pyudev

class USBMonitor:
    """Watch for USB device plug/unplug events."""

    KNOWN_DEVICES = {
        ("1a86", "55d3"): "feetech",    # QinHeng CH340 → Feetech
        ("1a86", "7523"): "feetech",    # CH340 variant
        ("0403", "6014"): "dynamixel",  # FTDI → USB2Dynamixel
        ("0403", "6001"): "dynamixel",  # FTDI variant
    }

    def __init__(self, on_device_added, on_device_removed):
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by('tty')
        # ...
```

#### Device→Citizen Factory

When a device is detected:
1. Look up vendor/product ID in `KNOWN_DEVICES`
2. Determine driver type (feetech / dynamixel)
3. Scan the bus for connected motors
4. Match motor count + IDs against known profiles (SO-101 = 6 Feetech, Koch = 6 Dynamixel)
5. Create appropriate citizen with the matched profile

```python
class CitizenFactory:
    def create_from_device(self, device_info: DeviceInfo) -> Citizen:
        driver = self._create_driver(device_info.driver_type)
        driver.connect(device_info.port)
        motors = driver.scan_motors()
        profile = self._match_profile(device_info.driver_type, motors)
        return ArmCitizen(driver=driver, profile=profile, ...)
```

#### Serial Number Persistence

Device serial numbers are mapped to citizen identities in `~/.citizenry/device_map.json`:

```json
{
  "5A7A015764": {  // USB serial number
    "citizen_name": "so101-arm-1",
    "profile": "so101",
    "identity_key": "arm-1.key"
  }
}
```

Reconnecting the same physical device restores the same citizen identity — no re-calibration needed.

### 3. First-Run Wizard (armos/wizard/)

#### Flow

```
┌──────────────┐
│  First Boot  │──→ ~/.citizenry/ exists? ──Yes──→ Normal Governor CLI
└──────┬───────┘                    │
       │                           No
       ▼                            │
┌──────────────┐                    ▼
│  Step 1:     │   ┌────────────────────────┐
│  Welcome     │   │  "Welcome to armOS!"    │
│              │   │  Scanning for hardware..│
└──────┬───────┘   └────────────┬───────────┘
       │                        │
       ▼                        ▼
┌──────────────┐   Found devices listed
│  Step 2:     │   "Feetech controller on /dev/ttyACM0"
│  Detect      │   "USB camera on /dev/video0"
│  Hardware    │
└──────┬───────┘
       │
       ▼
┌──────────────┐   Motor scan → match against profiles
│  Step 3:     │   "6 Feetech motors found. This looks like
│  Identify    │    an SO-101 arm. Correct? [Y/n]"
│  Robot       │
└──────┬───────┘
       │
       ▼
┌──────────────┐   Move each joint to home position
│  Step 4:     │   "Move shoulder_pan to center. Press Enter."
│  Calibrate   │   Auto-detect home positions if possible.
│              │
└──────┬───────┘
       │
       ▼
┌──────────────┐   Generate identity, load genome, join mesh
│  Step 5:     │   "Setup complete! Your arm is ready."
│  Complete    │   "Type 'help' to get started."
└──────────────┘
```

### 4. OS Image Build (image/)

#### Build System: live-build

```bash
# image/build.sh
#!/bin/bash
set -euo pipefail

# Configure live-build
lb config \
  --distribution noble \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --bootappend-live "boot=live components persistence" \
  --debian-installer false \
  --apt-recommends false \
  --linux-packages "linux-image linux-headers" \
  --bootloaders "syslinux,grub-efi"

# Build
lb build
```

#### Chroot Hook (installs armOS into the live image)

```bash
# config/hooks/0100-install-armos.hook.chroot
#!/bin/bash
# Install Python 3.12 and create venv
apt-get install -y python3.12 python3.12-venv python3-pip

# Create armOS venv
python3.12 -m venv /opt/armos/env
source /opt/armos/env/bin/activate

# Install citizenry and dependencies
pip install pynacl zeroconf opencv-python-headless aiohttp numpy
pip install lerobot==0.5.0
pip install dynamixel-sdk

# Copy citizenry package
cp -r /build/citizenry /opt/armos/citizenry
cp -r /build/armos /opt/armos/armos

# Install udev rules
cp /build/image/live-build/config/includes.chroot/etc/udev/rules.d/*.rules /etc/udev/rules.d/

# Create launch script
cat > /usr/local/bin/armos-start << 'LAUNCH'
#!/bin/bash
source /opt/armos/env/bin/activate
cd /opt/armos
exec python -m citizenry
LAUNCH
chmod +x /usr/local/bin/armos-start
```

#### udev Rules

```
# 99-armos-hardware.rules
# Feetech CH340 servo controllers
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout", TAG+="armos", ENV{ARMOS_DRIVER}="feetech"

# Dynamixel USB2Dynamixel / U2D2
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6014", MODE="0666", GROUP="dialout", TAG+="armos", ENV{ARMOS_DRIVER}="dynamixel"

# USB cameras
SUBSYSTEM=="video4linux", TAG+="armos", ENV{ARMOS_TYPE}="camera"

# Hotplug notification
ACTION=="add", TAG=="armos", RUN+="/usr/local/bin/armos-hotplug add %k"
ACTION=="remove", TAG=="armos", RUN+="/usr/local/bin/armos-hotplug remove %k"
```

#### Systemd Service

```ini
# armos-governor.service
[Unit]
Description=armOS Governor
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/armos-start
User=armos
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 5. CI/CD Pipeline (.github/workflows/)

#### Test Workflow (every push)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install pynacl zeroconf opencv-python-headless aiohttp numpy pytest pytest-asyncio
      - run: python -m pytest citizenry/tests/ armos/tests/ -q
```

#### ISO Build Workflow (release tags)

```yaml
# .github/workflows/build-iso.yml
name: Build ISO
on:
  push:
    tags: ['v*']
jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get install -y live-build
      - run: cd image && sudo ./build.sh
      - run: sha256sum image/live-image-amd64.hybrid.iso > checksums.txt
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            image/live-image-amd64.hybrid.iso
            checksums.txt
```

---

## Data Flow: Hardware Plug-In to Citizen

```
USB Device Plugged In
       │
       ▼
  udev rule fires ──→ armos-hotplug script
       │
       ▼
  USBMonitor receives event
       │
       ▼
  Look up vendor:product in DeviceDB
       │
  ┌────┴────┐
  │Known?   │──No──→ Log: "Unknown USB device"
  └────┬────┘
       │Yes
       ▼
  Create appropriate ServoDriver
       │
       ▼
  driver.connect(port) → driver.scan_motors()
       │
       ▼
  Match motor config against profiles
       │
  ┌────┴────┐
  │Match?   │──No──→ Prompt: "Unknown robot. Select profile or skip."
  └────┬────┘
       │Yes
       ▼
  Check device_map.json for serial number
       │
  ┌────┴────┐
  │Known?   │──No──→ First-run wizard for this device
  └────┬────┘
       │Yes
       ▼
  Restore citizen identity from existing key
       │
       ▼
  Create ArmCitizen(driver, profile, identity)
       │
       ▼
  citizen.start() → joins mesh → governor discovers
```

---

## Migration from Current State

The existing `citizenry/pi_citizen.py` directly uses `lerobot.motors.feetech.FeetechMotorsBus`. The HAL migration:

1. Extract servo communication into `FeetechDriver(ServoDriver)`
2. `pi_citizen.py` becomes a thin wrapper that instantiates `ArmCitizen` with `FeetechDriver`
3. New `DynamixelDriver` follows the same pattern
4. Both use the same `ArmCitizen` class — only the driver differs
5. **Zero changes to the citizenry protocol** — citizens still communicate the same way

---

## Testing Strategy

| Layer | Test Type | Framework | Hardware Needed |
|-------|-----------|-----------|----------------|
| HAL drivers | Unit (mocked bus) | pytest | No |
| Motor scanner | Unit (mocked responses) | pytest | No |
| Hardware detection | Unit (mocked udev) | pytest | No |
| Profile matching | Unit | pytest | No |
| Wizard flow | Unit (mocked I/O) | pytest | No |
| ISO build | Integration | GitHub Actions | No (VM) |
| End-to-end | Manual | Real hardware | Yes |

---

## Dependencies

| Package | Purpose | New? |
|---------|---------|------|
| `dynamixel-sdk>=3.7.51` | Dynamixel servo protocol | Yes |
| `pyudev>=0.24.0` | USB hotplug monitoring | Yes |
| `live-build` | ISO creation (build-time) | Yes |
| All existing citizenry deps | Protocol, crypto, etc. | No |
