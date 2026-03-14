# armOS Technical Architecture

**Date:** 2026-03-15
**Author:** Winston (Architect Agent)
**Status:** Draft
**Version:** 1.0

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [System Context](#2-system-context)
3. [OS Layer](#3-os-layer)
4. [Hardware Abstraction Layer](#4-hardware-abstraction-layer)
5. [Robot Profile System](#5-robot-profile-system)
6. [Diagnostic Framework](#6-diagnostic-framework)
7. [AI Integration Layer](#7-ai-integration-layer)
8. [User Interface Layer](#8-user-interface-layer)
9. [Project Structure](#9-project-structure)
10. [Key Architecture Patterns](#10-key-architecture-patterns)
11. [Architecture Decision Records](#11-architecture-decision-records)
12. [Data Flow Diagrams](#12-data-flow-diagrams)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Security Considerations](#14-security-considerations)
15. [Migration Path from Current Codebase](#15-migration-path-from-current-codebase)

---

## 1. Architecture Overview

armOS is a bootable USB operating system purpose-built for robotics. It provides a
hardware abstraction layer, diagnostic framework, and AI integration pipeline that
allows users to plug in supported robot hardware and have a working control station
within minutes -- on any x86 machine.

### High-Level Architecture

```
+===================================================================+
|                       USER INTERFACE LAYER                        |
|  +-------------+  +-----------------+  +----------------------+  |
|  | CLI (armos|  | TUI (textual)   |  | Web Dashboard        |  |
|  | detect, cal,|  | headless status |  | (FastAPI + htmx)     |  |
|  | teleop, etc)|  | and control     |  | telemetry, control   |  |
|  +-------------+  +-----------------+  +----------------------+  |
+===================================================================+
|                      AI INTEGRATION LAYER                        |
|  +----------------+  +------------------+  +-----------------+   |
|  | LeRobot v0.5+  |  | Data Collection  |  | Claude Code     |   |
|  | (train/infer)  |  | Pipeline         |  | (setup/debug)   |   |
|  +----------------+  +------------------+  +-----------------+   |
+===================================================================+
|                     DIAGNOSTIC FRAMEWORK                         |
|  +-------------+  +----------------+  +---------------------+    |
|  | Health Check|  | Live Telemetry |  | Stress Testing      |    |
|  | Engine      |  | Streaming      |  | (comms, torque, xb) |    |
|  +-------------+  +----------------+  +---------------------+    |
+===================================================================+
|                  HARDWARE ABSTRACTION LAYER (HAL)                |
|  +-------------------+  +-------------------+  +-------------+  |
|  | Servo Protocol    |  | Robot Profile      |  | Device      |  |
|  | Plugins           |  | System             |  | Manager     |  |
|  | (feetech,dynamixel|  | (YAML definitions) |  | (pyudev)    |  |
|  |  can, custom)     |  |                    |  |             |  |
|  +-------------------+  +-------------------+  +-------------+  |
+===================================================================+
|                        OS LAYER                                  |
|  +------------------+  +------------------+  +----------------+ |
|  | Ubuntu 24.04 LTS |  | udev rules       |  | Pre-installed  | |
|  | (live-build ISO) |  | (auto-permission) |  | packages       | |
|  +------------------+  +------------------+  +----------------+ |
+===================================================================+
|                     PHYSICAL HARDWARE                            |
|  USB Serial (CH340, FTDI) | USB Cameras | Sensors | GPIO        |
+===================================================================+
```

---

## 2. System Context

### External Systems and Actors

```
                    +------------------+
                    |   HuggingFace    |
                    |   Hub            |
                    | (datasets,models)|
                    +--------+---------+
                             |
                             | upload/download
                             |
+----------+        +--------v---------+        +------------------+
|  User    | <----> |    armOS       | <----> |  Robot Hardware   |
| (human)  |  UI    |  (USB-booted)    |  USB   | (servos, cameras, |
+----------+        +------------------+  serial |  sensors)         |
                             |                   +------------------+
                             |
                             | AI assist
                             |
                    +--------v---------+
                    |   Claude Code    |
                    |   (local agent)  |
                    +------------------+
```

### Key Constraints

- **No GPU required.** Intel integrated graphics is the baseline. All training
  happens in the cloud; this machine is for inference and data collection.
- **USB-bootable.** Must run from a USB stick without hard drive installation.
- **Offline-capable.** After initial setup, no internet is required for core
  robot operation (teleop, diagnostics, data collection).
- **Python-based.** Maximum accessibility for the robotics community.
- **x86 target.** ARM support is out of scope for v1.

---

## 3. OS Layer

### Decision: Pre-built Ubuntu ISO via live-build

Rather than the current install-from-scratch approach (flash Ubuntu ISO, then run
five phases of package installation), armOS ships as a pre-built custom ISO
with all robotics packages baked in.

### Build Toolchain

**Tool:** `live-build` (Debian/Ubuntu native live system builder)

**Why not Cubic?** Cubic is a GUI tool suitable for one-off customization.
`live-build` is scriptable, reproducible, and suitable for CI/CD pipelines
that produce new ISO releases automatically.

### ISO Contents

```
armos-iso/
  auto/
    config                  # live-build auto-config
  config/
    package-lists/
      armos.list.chroot   # apt packages to include
    includes.chroot/
      etc/
        udev/rules.d/
          99-armos-serial.rules    # Feetech, Dynamixel, FTDI permissions
          99-armos-cameras.rules   # USB camera permissions
        skel/
          .bashrc                     # armos-env activation
      opt/
        armos/                      # Pre-installed armos package
      usr/
        share/
          armos/
            profiles/                 # Robot profile YAML files
    hooks/
      live/
        0100-install-armos.hook.chroot   # pip install armos + lerobot
        0200-configure-system.hook.chroot  # system tuning
```

### ISO Build Pipeline

```
[GitHub Actions / local]
        |
        v
  live-build config
        |
        v
  lb build
        |
        v
  armos-<version>.iso
        |
        v
  SHA256 checksum + release
```

### System Configuration Baked Into ISO

| Component | Configuration |
|-----------|--------------|
| udev rules | Serial port auto-permissions for known USB-serial chips (CH340, FTDI, CP2102) |
| brltty | Removed from image (it hijacks Feetech serial ports) |
| Python 3.12 | System Python with venv at `/opt/armos/env` |
| LeRobot | Pre-installed in the venv |
| armos package | Pre-installed in the venv |
| dialout group | Default user added automatically |
| systemd service | `armos-detect.service` for USB hotplug detection |
| GRUB | Configured for USB boot with Surface kernel option |

### Kernel Strategy

The base ISO ships with the standard Ubuntu kernel. An optional `armos-kernels`
meta-package provides:
- `linux-image-surface` for Microsoft Surface devices
- Standard kernel as fallback

The kernel is selected at boot via GRUB menu, not baked into a single image.
This keeps the ISO universal across x86 hardware.

---

## 4. Hardware Abstraction Layer (HAL)

### Architecture

```
                    +---------------------------+
                    |      HAL Public API        |
                    |  connect()                 |
                    |  read_position(joint)      |
                    |  write_position(joint,val) |
                    |  calibrate()               |
                    |  diagnose()                |
                    |  get_telemetry()           |
                    +-------------+-------------+
                                  |
                    +-------------v-------------+
                    |     DeviceManager          |
                    |  (pyudev + profile match)  |
                    +----+--------+--------+----+
                         |        |        |
               +---------+--+ +---+------+ +--+---------+
               | Feetech    | | Dynamixel| | CAN-based  |
               | Plugin     | | Plugin   | | Plugin     |
               +------------+ +----------+ +------------+
                     |              |             |
               [USB Serial]   [USB Serial]   [CAN bus]
```

### Plugin Interface

Every hardware driver plugin implements the `ServoProtocol` abstract base class:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ServoTelemetry:
    voltage: float          # Volts
    current_mA: float       # Milliamps
    load_pct: float         # Percent (-100 to 100)
    temperature_C: int      # Celsius
    position: int           # Raw encoder ticks
    velocity: int           # Raw velocity
    error_flags: list[str]  # e.g. ["OVERLOAD", "OVERHEAT"]

class ServoProtocol(ABC):
    """Base class for all servo communication protocols."""

    @abstractmethod
    def connect(self, port: str, baudrate: int = 1_000_000) -> None:
        """Open the serial/CAN connection."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection and release resources."""

    @abstractmethod
    def ping(self, servo_id: int) -> bool:
        """Check if a servo is responding."""

    @abstractmethod
    def read_position(self, servo_id: int) -> int:
        """Read the current position (raw encoder value)."""

    @abstractmethod
    def write_position(self, servo_id: int, position: int) -> None:
        """Command the servo to a goal position."""

    @abstractmethod
    def sync_read_positions(self, servo_ids: list[int]) -> dict[int, int]:
        """Read positions from multiple servos in one transaction."""

    @abstractmethod
    def sync_write_positions(self, positions: dict[int, int]) -> None:
        """Write positions to multiple servos in one transaction."""

    @abstractmethod
    def get_telemetry(self, servo_id: int) -> ServoTelemetry:
        """Read voltage, current, load, temperature, and error status."""

    @abstractmethod
    def sync_read_telemetry(self, servo_ids: list[int]) -> dict[int, ServoTelemetry]:
        """Read telemetry from multiple servos in one transaction.

        Reads contiguous register blocks (position through current) for all
        specified servos in a single bus transaction. Essential for meeting
        NFR1 latency targets -- avoids N round-trips for N servos."""

    @abstractmethod
    def read_register(self, servo_id: int, address: int, size: int) -> int:
        """Read a raw register value (1 or 2 bytes)."""

    @abstractmethod
    def write_register(self, servo_id: int, address: int, value: int, size: int) -> None:
        """Write a raw register value."""

    @abstractmethod
    def enable_torque(self, servo_id: int) -> None:
        """Enable torque on a servo."""

    @abstractmethod
    def disable_torque(self, servo_id: int) -> None:
        """Disable torque on a servo."""

    @abstractmethod
    def flush_port(self) -> None:
        """Flush stale bytes from the serial input buffer.

        Called between retry attempts to clear corrupted data.
        Standard implementation: self._serial.reset_input_buffer()
        """
```

### Feetech Plugin (First Implementation)

The Feetech plugin wraps the existing `FeetechMotorsBus` from LeRobot, adding:
- Retry logic with port flush (the sync_read fix we already patched)
- Telemetry reading from hardware registers (extracted from `monitor_arm.py`)
- EEPROM configuration reading/writing (extracted from `diagnose_arms.py` Phase 6)
- Sign-magnitude decoding for current/load/velocity values

```python
class FeetechPlugin(ServoProtocol):
    """Feetech STS3215 / SCS series servo protocol implementation."""

    # Register addresses (STS3215)
    ADDR_PRESENT_POSITION = 56
    ADDR_PRESENT_VELOCITY = 58
    ADDR_PRESENT_LOAD = 60
    ADDR_PRESENT_VOLTAGE = 62
    ADDR_PRESENT_TEMPERATURE = 63
    ADDR_HARDWARE_ERROR = 65
    ADDR_PRESENT_CURRENT = 69
    # ... (full register map)

    RETRY_COUNT = 10
    FLUSH_BEFORE_RETRY = True  # Lesson learned from sync_read bug
```

### DeviceManager

The DeviceManager uses `pyudev` to monitor USB device events and match them to
known hardware profiles.

```python
class DeviceManager:
    """Monitors USB devices and matches them to robot profiles."""

    def __init__(self):
        self._context = pyudev.Context()
        self._monitor = pyudev.Monitor.from_netlink(self._context)
        self._monitor.filter_by(subsystem='tty')
        self._known_devices: dict[str, USBDevice] = {}
        self._callbacks: list[Callable] = []

    def scan(self) -> list[USBDevice]:
        """Enumerate all currently connected USB serial devices."""

    def watch(self, callback: Callable[[str, USBDevice], None]) -> None:
        """Register a callback for device add/remove events."""

    def match_profile(self, devices: list[USBDevice]) -> Optional[RobotProfile]:
        """Match a set of detected devices to a known robot profile."""
```

### CameraManager

The CameraManager handles USB camera discovery and frame capture via V4L2. Unlike servo
protocols (which vary by manufacturer), V4L2 is the universal Linux camera interface, so
a single concrete class suffices -- no ABC is needed.

```python
class CameraInfo:
    """Detected camera metadata."""
    device_path: str        # e.g. /dev/video0
    name: str               # e.g. "USB 2.0 Camera"
    resolutions: list[tuple[int, int]]  # [(640, 480), (1280, 720), ...]
    frame_rates: list[int]  # [30, 60]

class CameraManager:
    """Discovers and manages USB cameras via V4L2."""

    def enumerate(self) -> list[CameraInfo]:
        """List all connected V4L2 video capture devices."""

    def open(self, device_path: str, width: int = 640, height: int = 480,
             fps: int = 30) -> cv2.VideoCapture:
        """Open a camera for frame capture via OpenCV."""

    def capture_frame(self, cap: cv2.VideoCapture) -> np.ndarray:
        """Capture a single frame, raising on failure."""

    def assign_roles(self, cameras: list[CameraInfo],
                     profile: RobotProfile) -> dict[str, CameraInfo]:
        """Auto-assign cameras to profile-defined observation roles.

        MVP: assigns the first detected camera to the first role.
        Growth: user confirmation of multi-camera assignments (FR5).
        """
```

Uses OpenCV (`cv2.VideoCapture`) as the backend, which is already a LeRobot dependency.
Camera auto-detection enumerates `/dev/video*` devices and filters to those with
`V4L2_CAP_VIDEO_CAPTURE` capability.

### USB Device Identification

Known USB-serial chips and their vendor/product IDs:

| Chip | Vendor ID | Product ID | Used By |
|------|-----------|------------|---------|
| CH340 | 1a86 | 7523 | Feetech servo controllers |
| FTDI FT232 | 0403 | 6001 | Dynamixel U2D2 |
| CP2102 | 10c4 | ea60 | Various servo controllers |
| STM32 CDC | 0483 | 5740 | Custom CAN bridges |

### udev Rules (shipped in ISO)

```
# Feetech servo controllers (CH340)
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0660", GROUP="armos", \
  SYMLINK+="armos/servo%n", TAG+="armos"

# Dynamixel U2D2 (FTDI)
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", \
  MODE="0660", GROUP="armos", SYMLINK+="armos/servo%n", TAG+="armos"

# USB cameras
SUBSYSTEM=="video4linux", MODE="0660", GROUP="armos", TAG+="armos"
```

---

## 5. Robot Profile System

### Profile Format (YAML)

Each supported robot is described by a YAML profile. Profiles are stored in
`/usr/share/armos/profiles/` (shipped with ISO) and `~/.config/armos/profiles/`
(user-created).

```yaml
# profiles/so101.yaml
name: "SO-101"
description: "HuggingFace SO-101 6-DOF robot arm (leader/follower pair)"
version: "1.0"

hardware:
  usb_devices:
    - role: "servo_controller"
      chip: "CH340"
      vendor_id: "1a86"
      count: 2  # one per arm (leader + follower)
      protocol: "feetech"
      baudrate: 1_000_000

arms:
  follower:
    role: "actuator"
    servo_protocol: "feetech"
    joints:
      - name: "shoulder_pan"
        servo_id: 1
        model: "sts3215"
        norm_mode: "range_m100_100"
      - name: "shoulder_lift"
        servo_id: 2
        model: "sts3215"
        norm_mode: "range_m100_100"
      - name: "elbow_flex"
        servo_id: 3
        model: "sts3215"
        norm_mode: "range_m100_100"
      - name: "wrist_flex"
        servo_id: 4
        model: "sts3215"
        norm_mode: "range_m100_100"
      - name: "wrist_roll"
        servo_id: 5
        model: "sts3215"
        norm_mode: "range_m100_100"
      - name: "gripper"
        servo_id: 6
        model: "sts3215"
        norm_mode: "range_0_100"

    control:
      operating_mode: "position"
      p_coefficient: 16
      i_coefficient: 0
      d_coefficient: 32

    protection:
      default:
        overload_torque: 90
        protective_torque: 50
        protection_time: 254
      gripper:
        overload_torque: 25
        max_torque_limit: 500
        protection_current: 250

  leader:
    role: "teleoperator"
    servo_protocol: "feetech"
    joints:
      # Same joint definitions as follower
      # ...

power:
  follower:
    recommended_voltage: 12
    recommended_current_amps: 5
    minimum_current_amps: 3
    warning: "12V 2A PSU is INSUFFICIENT. Use 12V 5A (60W) minimum."
  leader:
    note: "Runs on 5V USB power. Below STS3215 spec but works for read-only."

firmware:
  minimum_version: "3.10"
  update_requires: "Windows (Feetech debug software)"

calibration:
  storage_path: "~/.config/armos/calibration/{instance_id}/"
  format: "json"
  per_arm: true

lerobot:
  robot_type: "so100"
  teleop_config:
    fps: 60
    monitor_hz: 2
```

### Profile Matching Algorithm

When USB devices are detected, the profile matcher runs:

```
1. Enumerate all USB serial devices with vendor/product IDs
2. For each profile in the profile directory:
   a. Check if the required USB devices are present (chip type, count)
   b. For each required servo bus, attempt to ping servos at expected IDs
   c. Score = (matched_devices / required_devices) * (pinged_servos / expected_servos)
3. Return the profile with the highest score (threshold: > 0.8)
4. If no profile matches, offer manual selection
```

### Instance Management

A single profile (e.g., "SO-101") can have multiple physical instances. Each
instance gets a unique ID derived from the USB serial number of its controller.

```
~/.config/armos/
  calibration/
    so101-CH340-SN12345/
      follower.json
      leader.json
    so101-CH340-SN67890/
      follower.json
      leader.json
  instances.yaml           # Maps serial numbers to user-friendly names
```

---

## 6. Diagnostic Framework

### Architecture

The diagnostic framework generalizes the existing `diagnose_arms.py` and
`monitor_arm.py` into a reusable library.

```
+----------------------------------------------------+
|              DiagnosticRunner                       |
|  run_all() / run_check(name) / run_suite(suite)    |
+--+-----------+-----------+----------+--------------+
   |           |           |          |
+--v---+ +----v----+ +----v---+ +----v-----------+
| Port | | Servo   | | Comms  | | Stress         |
| Check| | Health  | | Check  | | Test           |
+------+ +---------+ +--------+ +----------------+
   |           |           |          |
   v           v           v          v
+----------------------------------------------------+
|            DiagnosticResult                        |
|  status: PASS | WARN | FAIL                        |
|  message: str                                      |
|  data: dict (telemetry, latency, etc.)             |
+----------------------------------------------------+
          |
          v
+----------------------------------------------------+
|            Output Backends                         |
|  ConsoleReporter | JSONReporter | CSVReporter      |
+----------------------------------------------------+
```

### Health Check Interface

```python
@dataclass
class CheckResult:
    name: str
    status: Literal["PASS", "WARN", "FAIL"]
    message: str
    data: dict = field(default_factory=dict)

class HealthCheck(ABC):
    """Base class for all diagnostic checks."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def run(self, protocol: ServoProtocol, profile: RobotProfile) -> list[CheckResult]: ...
```

### Built-in Health Checks

Derived from the existing 11-phase diagnostic tool:

| Check | Source | What It Tests |
|-------|--------|---------------|
| `PortDetection` | Phase 1 | USB ports exist, are readable/writable, brltty not installed |
| `ServoPing` | Phase 2 | Every expected servo responds to ping, no error flags |
| `FirmwareVersion` | Phase 3 | All servos meet minimum firmware version |
| `PowerHealth` | Phase 4 | Voltage within range (6-13V), temperature below thresholds |
| `StatusRegister` | Phase 5 | No error flags set (voltage, angle, overheat, overcurrent, overload) |
| `EEPROMConfig` | Phase 6 | Protection settings match profile, no dangerous values |
| `CommsReliability` | Phase 7 | 200 sync_read cycles, >99% success, latency within bounds |
| `TorqueStress` | Phase 8 | 200 read/write cycles with torque enabled, >99% success |
| `CrossBusTeleop` | Phase 9 | 500 leader-read/follower-write cycles, voltage monitoring |
| `MotorIsolation` | Phase 10 | Per-motor read reliability (find the weak link) |
| `CalibrationValid` | Phase 11 | Calibration file exists, ranges are sane |

### Telemetry Streaming

The live telemetry system (evolved from `monitor_arm.py`) provides a publish-subscribe
interface for real-time servo data.

```python
class TelemetryStream:
    """Real-time servo telemetry with pluggable backends."""

    def __init__(self, protocol: ServoProtocol, profile: RobotProfile):
        self._protocol = protocol
        self._profile = profile
        self._backends: list[TelemetryBackend] = []
        self._running = False

    def add_backend(self, backend: TelemetryBackend) -> None:
        """Register a telemetry output backend."""

    def start(self, hz: int = 10) -> None:
        """Begin polling servos and streaming to backends."""

    def stop(self) -> None:
        """Stop the telemetry stream."""

class TelemetryBackend(ABC):
    @abstractmethod
    def on_sample(self, timestamp: float, data: dict[str, ServoTelemetry]) -> None: ...

# Built-in backends
class CSVBackend(TelemetryBackend): ...
class WebSocketBackend(TelemetryBackend): ...
class ConsoleBackend(TelemetryBackend): ...   # The colored terminal output from monitor_arm.py
class InfluxDBBackend(TelemetryBackend): ...  # Future: time-series database
```

---

## 7. AI Integration Layer

### LeRobot Integration

LeRobot remains the default AI framework. armOS wraps it with:

1. **Automatic patching** -- The sync_read retry and port flush patches are applied
   programmatically at import time (monkey-patching), eliminating the need to
   manually patch site-packages.

2. **Profile-to-config translation** -- Robot profiles are translated to LeRobot
   configuration objects, so users never write LeRobot config files manually.

3. **Data collection pipeline:**

```
[Teleop Session]
      |
      v
[armos record]  -->  [HuggingFace Dataset format]
      |                          |
      v                          v
[Local storage]           [hub upload]
~/.config/armos/        huggingface.co/datasets/
  datasets/               username/robot-dataset
```

### Claude Code Integration

Claude Code serves as the interactive setup and debugging assistant. The
integration points are:

| Touchpoint | Mechanism |
|------------|-----------|
| Setup instructions | `CLAUDE.md` in repo root (already working) |
| Context seeding | `setup.sh` copies memory files to Claude project dir |
| Diagnostic interpretation | Claude reads `armos diagnose --json` output |
| Hardware debugging | Claude reads telemetry logs and suggests fixes |

No programmatic API between armOS and Claude Code -- the interaction is through
files and CLI output that Claude Code can read and interpret.

---

## 8. User Interface Layer

### CLI (Primary Interface)

All operations are available as CLI commands. The CLI is the single source of
truth; TUI and web dashboard call the same underlying functions.

```
armos detect          # Scan USB devices, match to robot profiles
armos status          # Show connected hardware status
armos calibrate       # Run interactive calibration for detected robot
armos teleop          # Start leader-follower teleoperation
armos record          # Record a teleop session as a dataset
armos diagnose        # Run full diagnostic suite
armos diagnose --json # Machine-readable diagnostic output
armos monitor         # Live servo telemetry stream
armos exercise        # Programmatic arm movement stress test
armos config show     # Show current robot profile configuration
armos config edit     # Edit robot profile
armos profile list    # List available robot profiles
armos profile create  # Create a new robot profile interactively
armos serve           # Start the web dashboard
```

Implementation: `click` library for CLI argument parsing.

### TUI (Headless Operation)

For SSH sessions and headless machines. Built with `textual` (Python TUI framework).

```
+--[ armOS v1.0 ]--------------------------------------------+
|                                                               |
|  Hardware:  SO-101 (follower + leader)                        |
|  Ports:     /dev/ttyACM0 (follower), /dev/ttyACM1 (leader)   |
|  Status:    Connected, calibrated                             |
|                                                               |
|  +-- Follower Arm ----------------------------------------+  |
|  | Joint          Pos    Volt   Curr   Load   Temp  Stat  |  |
|  | shoulder_pan   2048   12.1V   42mA   3.2%  28C   ok    |  |
|  | shoulder_lift  1890   12.0V  180mA  33.1%  31C   ok    |  |
|  | elbow_flex     2200   11.9V  210mA  45.0%  33C   ok    |  |
|  | wrist_flex     2048   12.1V   35mA   1.2%  27C   ok    |  |
|  | wrist_roll     2048   12.1V   30mA   0.8%  27C   ok    |  |
|  | gripper        1500   12.0V   50mA   5.0%  28C   ok    |  |
|  +---------------------------------------------------------+  |
|                                                               |
|  [D]iagnose  [T]eleop  [R]ecord  [M]onitor  [Q]uit          |
+---------------------------------------------------------------+
```

### Web Dashboard (Optional)

For remote monitoring and multi-robot setups. Technology choices:

- **Backend:** FastAPI (async Python, already in the ecosystem)
- **Frontend:** htmx + minimal JavaScript (no heavy SPA framework)
- **Real-time:** WebSocket for telemetry streaming
- **No external database required** -- reads from the same telemetry stream

The web dashboard is started explicitly with `armos serve` and binds to
`0.0.0.0:8080`. It is not auto-started.

---

## 9. Project Structure

### Python Package Layout

```
armos/
  __init__.py
  __main__.py                  # python -m armos
  cli/
    __init__.py
    main.py                    # click group, entry point
    detect.py                  # armos detect
    calibrate.py               # armos calibrate
    teleop.py                  # armos teleop
    record.py                  # armos record
    diagnose.py                # armos diagnose
    monitor.py                 # armos monitor
    exercise.py                # armos exercise
    config.py                  # armos config
    profile.py                 # armos profile
    serve.py                   # armos serve
  hal/
    __init__.py
    protocol.py                # ServoProtocol ABC, ServoTelemetry dataclass
    device_manager.py          # DeviceManager (pyudev)
    camera.py                  # CameraManager (V4L2 via OpenCV)
    plugins/
      __init__.py
      feetech.py               # FeetechPlugin (wraps FeetechMotorsBus)
      dynamixel.py             # DynamixelPlugin (future)
      can.py                   # CANPlugin (future)
  profiles/
    __init__.py
    loader.py                  # Load/validate YAML profiles
    matcher.py                 # Match detected hardware to profiles
    schema.py                  # Pydantic models for profile validation
    builtin/
      so101.yaml
      koch.yaml                # future
      aloha.yaml               # future
  diagnostics/
    __init__.py
    runner.py                  # DiagnosticRunner
    checks/
      __init__.py
      port_detection.py
      servo_ping.py
      firmware_version.py
      power_health.py
      status_register.py
      eeprom_config.py
      comms_reliability.py
      torque_stress.py
      cross_bus_teleop.py
      motor_isolation.py
      calibration_valid.py
    reporters/
      __init__.py
      console.py               # Colored terminal output
      json_reporter.py         # Machine-readable output
  telemetry/
    __init__.py
    stream.py                  # TelemetryStream
    backends/
      __init__.py
      csv_backend.py
      console_backend.py
      websocket_backend.py
  ai/
    __init__.py
    lerobot_bridge.py          # Profile-to-LeRobot config translation
    lerobot_patches.py         # Monkey-patches for sync_read retry
    data_pipeline.py           # Record, package, upload datasets
  ui/
    __init__.py
    tui/
      __init__.py
      app.py                   # Textual application
      screens/
        status.py
        teleop.py
        diagnostics.py
    web/
      __init__.py
      app.py                   # FastAPI application
      static/                  # CSS, minimal JS
      templates/               # Jinja2/htmx templates
  utils/
    __init__.py
    serial.py                  # Sign-magnitude decoding, port helpers
    colors.py                  # Terminal color constants
    config.py                  # XDG config path helpers

pyproject.toml                 # Package metadata, dependencies, entry points
```

### Entry Points (pyproject.toml)

```toml
[project]
name = "armos"
version = "0.1.0"
description = "Universal robot operating system"
requires-python = ">=3.12"
dependencies = [
    "click>=8.0",
    "pyudev>=0.24",
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "lerobot>=0.5.0",
    "rich>=13.0",            # For console output formatting
]

[project.optional-dependencies]
tui = ["textual>=0.40"]
web = ["fastapi>=0.100", "uvicorn>=0.20", "jinja2>=3.0", "websockets>=12.0"]
all = ["armos[tui,web]"]

[project.scripts]
armos = "armos.cli.main:cli"
```

### Configuration Directories

Following XDG Base Directory Specification:

| Path | Contents |
|------|----------|
| `/usr/share/armos/profiles/` | System-wide robot profiles (shipped with ISO) |
| `~/.config/armos/profiles/` | User-created robot profiles |
| `~/.config/armos/calibration/` | Per-instance calibration data |
| `~/.config/armos/config.yaml` | User preferences (default profile, telemetry settings) |
| `~/.local/share/armos/datasets/` | Recorded datasets |
| `~/.local/share/armos/logs/` | Diagnostic and telemetry logs |

---

## 10. Key Architecture Patterns

### 10.1 Event-Driven Hardware State

USB device connect/disconnect events drive the system through `pyudev` monitoring.

```
USB device plugged in
        |
        v
  pyudev event (add)
        |
        v
  DeviceManager.on_device_add()
        |
        v
  Identify chip (vendor/product ID)
        |
        v
  Attempt profile match
        |
        +---> Match found: auto-configure, notify UI
        |
        +---> No match: add to "unknown devices" list, prompt user
```

### 10.2 Retry and Resilience for Serial Communication

Lesson learned from the sync_read bug: serial communication with servos is
inherently unreliable. Every read/write operation must be wrapped in retry logic.

```python
def resilient_read(protocol, servo_id, register, retries=10):
    """Read with retry and port flush between attempts."""
    for attempt in range(retries):
        try:
            if attempt > 0:
                protocol.flush_port()  # Clear stale bytes
                time.sleep(0.001)      # Brief settle time
            return protocol.read_register(servo_id, register, size=2)
        except CommunicationError:
            if attempt == retries - 1:
                raise
    # Unreachable, but makes type checkers happy
    raise CommunicationError("Max retries exceeded")
```

All HAL methods use this pattern internally. The retry count is configurable
per-profile.

### 10.3 Graceful Degradation

If one servo drops off the bus, the system continues operating with the
remaining servos rather than crashing the entire session.

```
Servo 3 (elbow_flex) stops responding
        |
        v
  Retry N times (configurable)
        |
        +---> Recovers: log warning, continue
        |
        +---> Fails permanently:
                |
                v
          Mark joint as DEGRADED
                |
                v
          Continue teleop with remaining joints
                |
                v
          Flash warning in UI: "elbow_flex: OFFLINE"
                |
                v
          Log event for post-session analysis
```

This is critical for long data collection sessions where a brief servo hiccup
should not destroy an entire recording.

### 10.4 Configuration as Code

All robot configuration lives in version-controlled YAML files. No hidden
state in databases or binary formats. A user can:

1. Copy a profile YAML to a new machine
2. Copy calibration JSON files
3. Have an identical robot setup

### 10.5 Separation of Concerns

```
CLI/TUI/Web  -- presentation only, no business logic
     |
     v
  Commands   -- orchestration (wire up HAL + diagnostics + AI)
     |
     v
  HAL/Diagnostics/AI  -- domain logic, no UI awareness
     |
     v
  Protocols  -- raw hardware communication
```

No layer reaches more than one level down. The web dashboard never talks to
serial ports directly; it calls the same functions the CLI does.

### 10.6 Concurrency Model

The system mixes synchronous serial I/O with async UI frameworks. The concurrency
boundaries are defined explicitly to avoid GIL contention and integration issues.

**Core library functions** (HAL, diagnostics, profiles) are synchronous, using
blocking I/O on serial ports. This is the simplest model and matches pyserial's
design.

**Serial bus access** uses a **single bus thread per arm pair** that performs a
coordinated read-write cycle, eliminating lock contention entirely:

```
Single Bus Thread (per arm pair):
  loop at 60Hz:
    1. sync_read leader positions
    2. sync_read_telemetry follower (if telemetry subscribers exist)
    3. sync_write follower goal positions
    4. publish positions + telemetry to subscribers
```

The telemetry stream subscribes to data produced by this cycle rather than
initiating its own reads. This guarantees deterministic cycle timing and avoids
the jitter caused by lock contention between separate teleop and telemetry threads.

**Teleop watchdog:** A deadline-based watchdog runs alongside the bus thread. If
any teleop cycle exceeds a configurable deadline (default: 500ms), the watchdog
fires and disables all follower torques immediately. This is a safety-critical
component that prevents unsafe motion from stale commands (implements FR42). The
watchdog uses a separate `threading.Timer` that is reset on each successful cycle.

**GIL mitigation:** During active teleoperation, `gc.disable()` is called to prevent
garbage collection pauses (which can spike to 10-20ms in CPython). Manual
`gc.collect()` is triggered between episodes or during idle periods. A latency
histogram in the teleop controller validates NFR1 at runtime.

**TUI** runs in textual's event loop, calling core functions via textual's worker
threads (`@work` decorator).

**Web dashboard** runs in its own asyncio event loop (uvicorn), calling core
functions via `asyncio.to_thread()` to avoid blocking the event loop.

**CLI** calls core functions directly on the main thread (synchronous).

**`DeviceManager.watch()`** runs a pyudev monitor on a daemon thread, dispatching
callbacks to the caller's thread via a `queue.Queue`.

```
Main Thread          Reader Thread(s)       Textual/Asyncio
-----------          ----------------       ---------------
CLI commands   <-->  Telemetry polling      TUI event loop
Teleop loop          Serial I/O             Web dashboard
                     (one per bus)          (asyncio.to_thread)
```

---

## 11. Architecture Decision Records

### ADR-1: Python as Primary Language

**Context:** armOS needs to be accessible to the robotics hobbyist community.

**Decision:** Python 3.12+ as the primary language for all components.

**Rationale:**
- LeRobot is Python-based; same ecosystem avoids impedance mismatch
- Robotics community predominantly uses Python (ROS2 is Python + C++)
- `pyudev`, `pyserial`, `textual`, `fastapi` are all mature Python libraries
- Contributor accessibility is maximized

**Trade-offs:**
- Serial communication latency is higher than C/Rust (mitigated by the servo
  controllers doing the real-time work)
- No true real-time guarantees (acceptable for teleop at 60Hz; not suitable
  for motor control loops below 1ms)

### ADR-2: live-build Over Cubic for ISO Creation

**Context:** Need a reproducible way to build the custom Ubuntu ISO.

**Decision:** Use Debian `live-build` toolchain.

**Rationale:**
- Scriptable and CI/CD compatible (Cubic requires a GUI)
- Reproducible builds from a config directory checked into git
- Used by Ubuntu itself for official ISO builds
- Supports custom package lists, hooks, and chroot modifications

**Trade-offs:**
- Steeper learning curve than Cubic
- Longer build times (~30-60 minutes for a full ISO)

### ADR-3: Plugin Architecture for Hardware Drivers

**Context:** Need to support Feetech today, Dynamixel and CAN-based servos in the future.

**Decision:** Abstract base class (`ServoProtocol`) with concrete plugin implementations.

**Rationale:**
- Clean separation between protocol-specific code and generic robot logic
- New hardware support = new plugin file, no changes to core
- Existing diagnostic checks work across all protocols via the standard interface

**Trade-offs:**
- Abstraction layer adds a small amount of overhead
- Lowest-common-denominator API may not expose all protocol-specific features
  (mitigated by the `read_register`/`write_register` escape hatch)

### ADR-4: YAML for Robot Profiles, JSON for Calibration

**Context:** Need human-readable configuration for robot definitions and calibration data.

**Decision:** YAML for profiles (read by humans, edited by humans), JSON for
calibration data (generated by code, consumed by code).

**Rationale:**
- YAML supports comments, which are essential for explaining protection settings
  and hardware quirks
- JSON is the existing format used by LeRobot calibration, maintaining compatibility
- Pydantic validates both formats at load time

### ADR-5: No ROS2 Dependency

**Context:** ROS2 is the industry standard for robotics middleware.

**Decision:** armOS does not depend on ROS2. It provides its own lighter-weight
abstraction.

**Rationale:**
- ROS2 adds ~2GB to the ISO and significant complexity
- Target users are hobbyists who find ROS2 overwhelming
- LeRobot does not use ROS2
- A future `armos-ros2-bridge` package can provide interop without making
  it a core dependency

**Trade-offs:**
- Users who want ROS2 integration must install it separately
- No access to ROS2 ecosystem tools (RViz, etc.) out of the box

### ADR-6: FastAPI + htmx for Web Dashboard

**Context:** Need a web UI for remote monitoring without heavy frontend tooling.

**Decision:** FastAPI backend with htmx for dynamic updates, no JavaScript SPA framework.

**Rationale:**
- FastAPI is already in the Python ecosystem, async-native
- htmx provides dynamic updates with zero JavaScript build tooling
- WebSocket support for real-time telemetry is native in FastAPI
- Total frontend code stays under 500 lines -- maintainable by Python developers

**Trade-offs:**
- Less interactive than a React/Vue app
- Limited to server-rendered patterns

---

## 12. Data Flow Diagrams

### Teleop Data Flow

```
Leader Arm                                            Follower Arm
(read only)                                          (torque enabled)
    |                                                      ^
    | sync_read("Present_Position")                        |
    v                                                      |
+---+---+                                            +-----+----+
|Feetech|                                            | Feetech  |
|Plugin  |                                           | Plugin   |
+---+---+                                            +-----+----+
    |                                                      ^
    | raw positions                                        | goal positions
    v                                                      |
+---+------------------------------------------------+-----+----+
|                    Teleop Controller                            |
|  1. Read leader positions                                      |
|  2. Apply calibration mapping                                  |
|  3. Apply safety limits (from profile)                         |
|  4. Write follower goal positions                              |
|  5. Sample telemetry (at monitor_hz rate)                      |
+---------+-----------------------------+------------------------+
          |                             |
          v                             v
   [TelemetryStream]            [DataRecorder]
          |                     (if recording)
          |                             |
    +-----+------+               +-----+------+
    |  Console   |               | HuggingFace|
    |  Backend   |               | Dataset    |
    +-----+------+               +-----+------+
          |                             |
          v                             v
     [Terminal]                  [Local files]
                                        |
                                        v (optional)
                                 [HuggingFace Hub]
```

### Diagnostic Data Flow

```
+-------------------+
| armos diagnose  |
+--------+----------+
         |
         v
+--------+----------+
| DiagnosticRunner  |
|  load profile     |
|  connect HAL      |
+--------+----------+
         |
         | run each check
         v
+--------+----------+     +----------+----------+
| PortDetection     | --> | CheckResult(PASS)   |
+-------------------+     +---------------------+
| ServoPing         | --> | CheckResult(PASS)   |
+-------------------+     +---------------------+
| FirmwareVersion   | --> | CheckResult(WARN)   |
+-------------------+     +---------------------+
| PowerHealth       | --> | CheckResult(FAIL)   |
+-------------------+     +---------------------+
| ...               | --> | ...                 |
+-------------------+     +----------+----------+
                                     |
                          +----------v----------+
                          |    Reporter          |
                          | (console or JSON)    |
                          +----------+----------+
                                     |
                          +----------v----------+
                          |  Terminal / File /   |
                          |  Claude Code reads   |
                          +---------------------+
```

---

## 13. Deployment Architecture

### USB Stick Layout

```
USB Drive (64GB+)
  |
  +-- EFI/                    # UEFI boot partition
  |     BOOT/
  |       grubx64.efi
  |
  +-- boot/
  |     grub/
  |       grub.cfg            # Kernel selection (standard + surface)
  |     vmlinuz-*-generic
  |     vmlinuz-*-surface
  |     initrd.img-*
  |
  +-- casper/                 # Live filesystem (squashfs)
  |     filesystem.squashfs   # Full OS with armos pre-installed
  |     filesystem.manifest
  |
  +-- armos/                # Persistent partition (ext4, writable)
        config/               # Symlinked to ~/.config/armos
        calibration/          # Preserved across boots
        datasets/             # Recorded data
        logs/                 # Diagnostic/telemetry logs
```

The persistent partition is critical: calibration data and recorded datasets
survive reboots. The squashfs is read-only (fast, compact); user data goes
to the writable partition.

### First Boot Sequence

```
Power on + boot from USB
        |
        v
  GRUB menu (auto-select after 5s)
        |
        +---> "armOS (standard kernel)" -- default for most hardware
        |
        +---> "armOS (Surface kernel)"  -- for Surface Pro devices
        |
        v
  systemd boot
        |
        v
  armos-detect.service starts
        |  (IPC via Unix domain socket at /run/armos/detect.sock --
        |   no TCP/IP listeners, compliant with NFR20)
        v
  Scan USB devices
        |
        +---> Hardware detected: show profile match on login screen
        |
        +---> No hardware: show "connect your robot" message
        |
        v
  User logs in (auto-login, no password)
        |
        v
  Desktop / terminal with armos CLI available
        |
        v
  "armos status" shows detected hardware
```

---

## 14. Security Considerations

### Threat Model

armOS is a local-only system for controlling physical robots. It is not
a server, not internet-facing, and not multi-user.

| Concern | Mitigation |
|---------|-----------|
| Serial port access | udev rules grant access by group, not world-writable in production |
| USB device spoofing | Profile matching verifies servo responses, not just USB IDs |
| Passwordless sudo | Required for setup automation; production ISO uses a locked-down sudoers |
| Network exposure | Web dashboard binds to localhost by default; `--bind 0.0.0.0` is opt-in |
| Dataset integrity | Recorded datasets include SHA256 checksums |
| Supply chain | ISO builds are reproducible; dependencies pinned in lockfile |

### Principle: Local-First, Network-Optional

The system works fully offline. Network features (HuggingFace upload, web
dashboard on LAN, Claude Code) are all opt-in. No telemetry is collected.

---

## 15. Migration Path from Current Codebase

The existing scripts are the seed for the armOS package. Here is how each
existing file maps to the new architecture:

| Current File | Becomes | Notes |
|-------------|---------|-------|
| `diagnose_arms.py` | `armos/diagnostics/checks/*.py` | Split into individual check classes |
| `monitor_arm.py` | `armos/telemetry/stream.py` + `console_backend.py` | Generalized with pluggable backends |
| `exercise_arm.py` | `armos/cli/exercise.py` | Parameterized by profile |
| `teleop_monitor.py` | `armos/cli/teleop.py` | Uses HAL instead of direct FeetechMotorsBus |
| `setup.sh` | ISO build hooks | No longer needed at runtime |
| `CLAUDE.md` | Ships in ISO at `/opt/armos/CLAUDE.md` | Updated for armOS commands |
| `flash.ps1` | Replaced by ISO download + `dd`/Rufus | Simpler: just write the ISO |
| Hardcoded ports (`/dev/ttyACM0`) | DeviceManager auto-detection | No more port guessing |
| Hardcoded motor maps | Robot profile YAML | One source of truth |
| Hardcoded calibration paths | `~/.config/armos/calibration/` | XDG-compliant, per-instance |
| LeRobot monkey-patches | `armos/ai/lerobot_patches.py` | Applied at import time |

### Migration Phases

**Phase A: Package skeleton** (Epic 1) -- Create the `armos` package with CLI entry points.
Move existing scripts into the package structure. Everything still works, just
invoked as `armos diagnose` instead of `python diagnose_arms.py`.

**Phase B: Hardware abstraction and profiles** (Epics 2, 3) -- Implement `ServoProtocol` and `FeetechPlugin`.
Refactor diagnostic checks to use the protocol interface. Introduce robot profiles
with the SO-101 profile as the first implementation.

**Phase C: Diagnostics and telemetry** (Epics 4, 5) -- Decompose `diagnose_arms.py` into modular
health checks. Extract telemetry streaming from `monitor_arm.py` into the pluggable
backend system.

**Phase D: Calibration, teleop, and TUI** (Epics 6, 7) -- Implement calibration persistence,
leader-follower teleoperation CLI, and the TUI launcher menu.

**Phase E: ISO build and AI integration** (Epics 8, 9) -- Set up `live-build` configuration.
Package everything into a bootable ISO. Integrate LeRobot data collection pipeline
and Claude Code context files.

**Phase F: Growth and polish** (Epic 10) -- Add multi-hardware support (Dynamixel, pyudev
hotplug, profile wizard), web dashboard, and plugin architecture. Integrate with
visualization tools (Foxglove Studio, rerun.io) as telemetry export targets rather
than building competing visualization -- armOS owns the "getting started" experience,
not the "power user visualization" experience.

---

*Architecture document for armOS USB -- a universal robot operating system on a USB stick.*
