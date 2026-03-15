# armOS Technical Architecture

**Date:** 2026-03-15
**Author:** Winston (Architect Agent)
**Status:** Draft
**Version:** 2.0 (Consolidated)

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
11. [Cloud Training Pipeline](#11-cloud-training-pipeline)
12. [Telemetry and Product Analytics](#12-telemetry-and-product-analytics)
13. [Profile Marketplace](#13-profile-marketplace)
14. [Education Fleet Management](#14-education-fleet-management)
15. [Partnership Integration Points](#15-partnership-integration-points)
16. [Foxglove / rerun.io Bridge](#16-foxglove--rerunio-bridge)
17. [Frontier AI Intelligence Layer](#17-frontier-ai-intelligence-layer)
18. [Future Platform Targets](#18-future-platform-targets)
19. [Architecture Decision Records](#19-architecture-decision-records)
20. [Data Flow Diagrams](#20-data-flow-diagrams)
21. [Deployment Architecture](#21-deployment-architecture)
22. [Security Considerations](#22-security-considerations)
23. [Migration Path from Current Codebase](#23-migration-path-from-current-codebase)
24. [Implementation Priority](#24-implementation-priority)

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

### Component Maturity

Each component is tagged with its target maturity phase:

| Phase | Label | Timeline | Description |
|-------|-------|----------|-------------|
| MVP | **[MVP]** | Months 1-6 | Core USB stick, SO-101 support, diagnostics |
| Growth | **[Growth]** | Months 7-18 | Cloud training, marketplace, fleet, multi-hardware |
| Vision | **[Vision]** | Months 18-36 | Embodied AI agent, VLA models, federated learning |

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
- **x86 target.** ARM support is Growth scope (see Section 18).

---

## 3. OS Layer

**[MVP]**

### Decision: Pre-built Ubuntu ISO via live-build

Rather than the current install-from-scratch approach (flash Ubuntu ISO, then run
five phases of package installation), armOS ships as a pre-built custom ISO
with all robotics packages baked in.

### Build Toolchain

**Tool:** `live-build` (Debian/Ubuntu native live system builder)

**Why not Cubic?** Cubic is a GUI tool suitable for one-off customization.
`live-build` is scriptable, reproducible, and suitable for CI/CD pipelines
that produce new ISO releases automatically.

**Build reproducibility:** ISO builds use a containerized build environment
(`Dockerfile.build`) to ensure reproducibility across developer machines and
CI. This is orthogonal to whether the runtime OS uses containers.

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
  Dockerfile.build (containerized environment)
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
| LeRobot | Pre-installed in the venv (pinned to `lerobot==0.5.0`) |
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
This keeps the ISO universal across x86 hardware. Surface hardware is detected
at boot time via the DMI table; a first-boot script can auto-install the Surface
kernel to the persistent partition when Surface hardware is detected.

---

## 4. Hardware Abstraction Layer (HAL)

**[MVP]**

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

Every hardware driver plugin implements the `ServoProtocol` abstract base class.
The protocol also supports context manager usage (`__enter__`/`__exit__`) for safe
resource management, while keeping explicit `connect()`/`disconnect()` for
long-lived teleop sessions.

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

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

### Plugin Discovery

Plugins are discovered via Python entry points, allowing third-party packages to
register new servo protocols without modifying armOS core:

```toml
# In a third-party package's pyproject.toml:
[project.entry-points."armos.servo_protocols"]
dynamixel = "armos_dynamixel:DynamixelPlugin"
```

```python
# In armos/hal/protocol.py:
from importlib.metadata import entry_points

def get_protocol(name: str) -> type[ServoProtocol]:
    eps = entry_points(group="armos.servo_protocols")
    for ep in eps:
        if ep.name == name:
            return ep.load()
    raise PluginNotFoundError(name)
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

### Error Taxonomy

Structured errors replace ad-hoc error strings throughout the system:

```python
class ArmOSError(Exception): ...
class CommunicationError(ArmOSError): ...
class ServoTimeoutError(CommunicationError): ...
class BusDisconnectedError(CommunicationError): ...
class ProtectionTripError(ArmOSError): ...
class CalibrationError(ArmOSError): ...
class ProfileError(ArmOSError): ...
```

Each error class carries structured data (servo_id, register, expected_value,
actual_value) that diagnostic reporters and AI context generators can use
without parsing strings.

### Three-Level Failure Recovery

1. **Servo-level:** Single servo unresponsive. Mark degraded, continue operating
   with remaining joints. Already designed in graceful degradation (Section 10.3).
2. **Bus-level:** Entire serial port disappears. Pause teleop, attempt reconnect
   for 10 seconds, resume if successful, abort if not. USB hubs on laptops are
   notorious for resetting under power fluctuations.
3. **System-level:** Multiple buses fail. Halt all operations, display diagnostic
   summary, offer restart.

---

## 5. Robot Profile System

**[MVP]**

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

### Configuration Override Chain

Settings can be overridden without editing built-in profiles (which live in
read-only squashfs):

```
Built-in profile (read-only, /usr/share/armos/profiles/)
  -> User profile override (~/.config/armos/profiles/so101.override.yaml)
    -> CLI flags (--fps 30)
      -> Environment variables (ARMOS_TELEOP_FPS=30)
```

Each layer overrides the previous. The override YAML is a sparse document -- only
the fields being changed, not a full copy. Pydantic supports this pattern natively
via model inheritance and merge.

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

**[MVP]**

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

### Metrics Module

**[MVP]** A lightweight metrics module records histograms for key operations:
teleop cycle time, serial read/write latency, telemetry poll interval. Exposed
via `armos teleop --stats` which prints a summary at session end. This module
exists from Sprint 2 so every subsequent feature automatically reports its
performance characteristics.

### Logging Strategy

**[MVP]** Standardized on Python's `logging` module with a JSON formatter for
machine-readable logs and a human-readable formatter for console output. Log
levels: DEBUG (register-level reads), INFO (workflow start/stop), WARNING
(retries, threshold approaches), ERROR (failed operations), CRITICAL (safety
stops). Rotation: 50 MB per file, 5 files retained. Set up in Story 1.1 as
part of the package skeleton.

---

## 7. AI Integration Layer

**[MVP]**

### LeRobot Integration

LeRobot remains the default AI framework. armOS wraps it with:

1. **Automatic patching** -- The sync_read retry and port flush patches are applied
   programmatically at import time (monkey-patching), eliminating the need to
   manually patch site-packages. LeRobot is pinned to `lerobot==0.5.0` (exact
   version). A startup check verifies patched method signatures match expected
   signatures via `inspect.signature` comparison. If the signature changes, the
   system fails loudly rather than silently misbehaving.

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

4. **Per-episode integrity manifests:** Each episode produces an
   `episode_NNN.manifest.json` containing frame count, position sample count,
   SHA256 of camera frames file, and SHA256 of positions file. The
   `armos record --verify` command validates all manifests after a session.

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

### Inference Backend Abstraction

**[Growth]** An `InferenceBackend` abstraction supports multiple runtimes:

```python
class InferenceBackend(ABC):
    @abstractmethod
    def load_policy(self, policy_path: Path) -> Any: ...

    @abstractmethod
    def predict(self, observation: dict) -> dict: ...

class PyTorchBackend(InferenceBackend): ...    # Default, always available
class OpenVINOBackend(InferenceBackend): ...   # Optional, if openvino installed
class TensorRTBackend(InferenceBackend): ...   # Jetson only
```

Backend selection is automatic based on available hardware, overridable via
`--backend openvino`.

---

## 8. User Interface Layer

**[MVP]**

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
armos stats           # Personal usage statistics (from local telemetry DB)
armos export foxglove # Export session to MCAP format
armos export rerun    # Export session to .rrd format
armos train --upload  # Package and upload dataset for cloud training
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

**[MVP]**

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
    local_db.py                # SQLite local telemetry storage
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
    inference.py               # InferenceBackend ABC + implementations
  cloud/
    __init__.py
    upload_client.py           # Cloud training upload client
    huggingface.py             # HuggingFace Hub integration
  fleet/
    __init__.py
    hub.py                     # FleetHub (instructor side)
    agent.py                   # FleetAgent (student side)
  export/
    __init__.py
    foxglove.py                # MCAP export
    rerun_export.py            # .rrd export
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
    metrics.py                 # Latency histograms, performance instrumentation

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
    "lerobot==0.5.0",
    "rich>=13.0",            # For console output formatting
]

[project.optional-dependencies]
tui = ["textual>=0.40"]
web = ["fastapi>=0.100", "uvicorn>=0.20", "jinja2>=3.0", "websockets>=12.0"]
fleet = ["zeroconf>=0.130"]
export = ["mcap>=1.0"]
export-rerun = ["rerun-sdk>=0.15"]
openvino = ["openvino-runtime>=2024.0"]
all = ["armos[tui,web,fleet,export,export-rerun,openvino]"]

[project.scripts]
armos = "armos.cli.main:cli"

[project.entry-points."armos.servo_protocols"]
feetech = "armos.hal.plugins.feetech:FeetechPlugin"
```

### Configuration Directories

Following XDG Base Directory Specification:

| Path | Contents |
|------|----------|
| `/usr/share/armos/profiles/` | System-wide robot profiles (shipped with ISO) |
| `~/.config/armos/profiles/` | User-created robot profiles |
| `~/.config/armos/calibration/` | Per-instance calibration data |
| `~/.config/armos/config.yaml` | User preferences (default profile, telemetry settings) |
| `~/.config/armos/cloud.yaml` | Cloud API key (permissions 0600) |
| `~/.config/armos/telemetry.yaml` | Telemetry opt-in consent |
| `~/.local/share/armos/datasets/` | Recorded datasets |
| `~/.local/share/armos/logs/` | Diagnostic and telemetry logs |
| `~/.local/share/armos/telemetry.db` | Local telemetry SQLite database |

---

## 10. Key Architecture Patterns

### 10.1 Event-Driven Hardware State

**[MVP]** USB device connect/disconnect events drive the system through `pyudev` monitoring.

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

**[MVP]** Lesson learned from the sync_read bug: serial communication with servos is
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

**[MVP]** If one servo drops off the bus, the system continues operating with the
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

**[MVP]** All robot configuration lives in version-controlled YAML files. No hidden
state in databases or binary formats. A user can:

1. Copy a profile YAML to a new machine
2. Copy calibration JSON files
3. Have an identical robot setup

### 10.5 Separation of Concerns

**[MVP]**

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

**[MVP]** The system mixes synchronous serial I/O with async UI frameworks. The concurrency
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

**GC mitigation:** During active teleoperation, `gc.freeze()` (Python 3.12+)
is called to freeze the current generation 0/1/2 objects, preventing GC from
scanning the pre-existing object graph while still collecting new garbage.
`gc.unfreeze()` is called at the end of the session. Pre-allocated numpy arrays
are used for telemetry buffers to minimize allocations in the hot loop. A latency
histogram in the teleop controller validates NFR1 at runtime.

**Thread naming:** All threads are named (e.g., `Thread(name="bus-follower-rw", ...)`).
The `armos debug threads` command lists all active threads with their state, which
pays dividends during integration testing.

**TUI** runs in textual's event loop, calling core functions via textual's worker
threads (`@work` decorator).

**Web dashboard** runs in its own asyncio event loop (uvicorn), calling core
functions via `asyncio.to_thread()` to avoid blocking the event loop.

**CLI** calls core functions directly on the main thread (synchronous).

**`DeviceManager.watch()`** runs a pyudev monitor on a daemon thread, dispatching
callbacks to the caller's thread via a `queue.Queue`.

```
Main Thread          Bus Thread(s)              Textual/Asyncio
-----------          ----------------           ---------------
CLI commands   <-->  Combined R/W cycle         TUI event loop
                     (one per arm pair)         Web dashboard
                     publishes to subscribers   (asyncio.to_thread)
```

### 10.7 IPC Protocol

**[MVP]** The `armos-detect.service` communicates via a Unix domain socket at
`/run/armos/detect.sock` using a JSON-over-newline protocol. Each message is
a JSON object terminated by `\n`. This is debuggable with `socat`, parseable
from any language, and designed for extensibility (a future ROS2 bridge can
subscribe to the same socket).

---

## 11. Cloud Training Pipeline

**[Growth]**

**Business driver:** Cloud training is the primary monetization path. Users
collect data on armOS (no GPU), upload to cloud, receive trained policies.
Projected at $5-20 per training run.

### 11.1 End-to-End Data Flow

```
armOS (local)                              Cloud
+------------------+                       +---------------------------+
| 1. Collect data  |                       |                           |
|    (LeRobot fmt) |                       |                           |
+--------+---------+                       |                           |
         |                                 |                           |
+--------v---------+    HTTPS POST         | +---------------------+  |
| 2. Package       | -------------------> | | 4. Validate dataset |  |
|    dataset       |    multipart/form     | +----------+----------+  |
|    (tar.gz)      |    or tus.io resume   |            |             |
+--------+---------+                       | +----------v----------+  |
         |                                 | | 5. Queue training   |  |
+--------v---------+    WebSocket/SSE      | |    (LeRobot CLI)    |  |
| 3. Track         | <------------------- | +----------+----------+  |
|    progress      |    status updates     |            |             |
+--------+---------+                       | +----------v----------+  |
         |                                 | | 6. Export policy     |  |
+--------v---------+    HTTPS GET          | |    (.pt file)       |  |
| 7. Download      | <------------------- | +---------------------+  |
|    policy file   |    signed URL         |                           |
+------------------+                       +---------------------------+
```

### 11.2 Local Components (armOS Side)

#### Dataset Packager

```python
class DatasetPackager:
    """Packages recorded episodes into a cloud-uploadable archive."""

    def package(self, recording_dir: Path, metadata: RecordingMetadata) -> Path:
        """Create a tar.gz archive with:
        - episodes/ (LeRobot HDF5 or Parquet format)
        - metadata.json (robot profile, episode count, duration, camera config)
        - manifest.json (per-file SHA256 checksums for integrity verification)
        """

    def estimate_upload_size(self, recording_dir: Path) -> int:
        """Estimate archive size in bytes before packaging."""

    def validate_local(self, recording_dir: Path) -> list[ValidationError]:
        """Pre-flight checks: episode count > 0, no corrupted frames,
        checksums valid. Catches problems before wasting upload bandwidth."""
```

#### Upload Client

```python
class CloudUploadClient:
    """Handles dataset upload with resumable transfers."""

    def __init__(self, api_base: str = "https://api.armos.dev"):
        self._api_base = api_base

    def upload(self, archive_path: Path, api_key: str,
               on_progress: Callable[[int, int], None] = None) -> str:
        """Upload dataset archive. Returns a job_id.
        Uses tus.io resumable upload protocol."""

    def get_status(self, job_id: str, api_key: str) -> TrainingStatus:
        """Poll training job status. Returns queued/training/complete/failed."""

    def subscribe_status(self, job_id: str, api_key: str) -> Iterator[TrainingStatus]:
        """Server-Sent Events stream for real-time status updates."""

    def download_policy(self, job_id: str, api_key: str, dest: Path) -> Path:
        """Download the trained policy file (.pt) to dest."""
```

### 11.3 Cloud API Contract

```
POST   /v1/datasets              Upload dataset archive (tus.io endpoint)
GET    /v1/jobs/{job_id}         Get training job status
GET    /v1/jobs/{job_id}/events  SSE stream of status updates
GET    /v1/jobs/{job_id}/policy  Download trained policy (signed URL redirect)
POST   /v1/jobs/{job_id}/cancel  Cancel a queued or running job
GET    /v1/account/usage         Current billing period usage and limits
```

Authentication: API key in `Authorization: Bearer <key>` header. Keys are
provisioned via the armOS web dashboard (armos.dev). Keys are stored locally
in `~/.config/armos/cloud.yaml` (permissions 0600).

### 11.4 Training Backend (Cloud Side -- Design Only)

The cloud backend is out of scope for the armOS codebase but documented for consistency.

- **Compute:** Lambda Labs or vast.ai spot GPU instances, provisioned on demand.
- **Orchestration:** Lightweight job queue (Redis + worker). No Kubernetes for v1.
- **Training runtime:** Containerized LeRobot training CLI with pinned dependencies.
- **Storage:** S3-compatible object store (Cloudflare R2) for datasets and artifacts.
- **Billing:** Stripe usage-based billing, metered by GPU-minutes.

### 11.5 Offline Fallback

If the user has their own GPU machine, `armos train --local` generates a training
script and dataset archive that can be transferred via USB or SCP. The cloud service
is the easy path, not the only path. This aligns with Core Principle 3 (works offline).

### 11.6 Security Considerations

- Dataset archives may contain camera images of users' environments. The privacy
  policy states uploaded datasets are used solely for the user's training job and
  deleted after 30 days (configurable retention).
- Policy files are model weights, not executable code. Loaded via
  `torch.load(..., weights_only=True)` (PyTorch 2.6+ safe loading).
- API keys are scoped per-user. No shared keys.

---

## 12. Telemetry and Product Analytics

**[Growth]**

**Business driver:** The data flywheel -- more users produce more telemetry data,
which improves defaults, which reduces problems, which attracts more users.

### 12.1 Design Principles

1. **Opt-in only.** First boot asks: "Help improve armOS by sharing anonymous usage data?" Default is OFF.
2. **Transparent.** `armos telemetry show` prints exactly what would be sent.
3. **Anonymous.** No user identity, no IP address logging, no camera data.
4. **Local-first.** All telemetry is collected to a local SQLite database regardless of consent. The opt-in controls whether it is ever transmitted. The local database powers `armos stats`.

### 12.2 What Is Collected

```yaml
event:
  type: enum  # session_start, session_end, hardware_detected, calibration_complete,
              # teleop_session, diagnostic_result, error_occurred, training_uploaded
  timestamp: ISO8601
  armos_version: str
  session_id: UUIDv4  # Random per-boot, not tied to user

hardware:
  cpu_model: str
  ram_gb: int
  usb_controllers: list   # Vendor/product IDs only (no serial numbers)
  robot_profile: str
  servo_count: int
  camera_count: int

session:
  duration_seconds: float
  teleop_latency_p50_ms: float
  teleop_latency_p95_ms: float
  teleop_latency_p99_ms: float
  comm_errors: int
  comm_retries: int
  episodes_recorded: int
  servo_warnings: dict

diagnostic:
  check_name: str
  result: enum  # pass, warn, fail
```

### 12.3 Transmission

- **Protocol:** HTTPS POST to `https://telemetry.armos.dev/v1/events`
- **Batching:** Events buffered locally, transmitted every 24 hours (or on graceful shutdown).
- **Payload:** JSON array, gzip compressed. Typical batch < 10 KB.
- **Failure handling:** Events remain in buffer. Next 24-hour cycle includes them. Buffer capped at 90 days.
- **Server:** Simple append-only event store. No user accounts. No cross-session correlation.

### 12.4 Local Database Schema

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL,  -- JSON
    transmitted INTEGER DEFAULT 0
);

CREATE INDEX idx_events_transmitted ON events(transmitted);
CREATE INDEX idx_events_type ON events(event_type);
```

Stored at `~/.local/share/armos/telemetry.db`. Powers the `armos stats` command
regardless of remote telemetry opt-in.

---

## 13. Profile Marketplace

**[Growth]**

**Business driver:** Community profiles create a network effect -- each new profile
makes armOS more valuable.

### 13.1 Architecture: Git-Based, Not App Store

Profiles are YAML files. They belong in Git. The marketplace is a curated Git
repository with a web frontend, following the Homebrew / Helm model.

```
GitHub: armos-community/profiles (the canonical registry)
    |
    | git clone / sparse checkout
    |
armOS local: /usr/share/armos/profiles/          (shipped with ISO, read-only)
             ~/.config/armos/profiles/            (user-installed, writable)
             ~/.config/armos/profiles/registry.yaml  (installed profile index)
```

### 13.2 Profile Registry Format

```yaml
profiles:
  - name: so101
    version: "1.2.0"
    author: armos-team
    description: "HuggingFace SO-101 6-DOF arm (leader/follower pair)"
    hardware: [feetech-sts3215, ch340]
    license: Apache-2.0
    path: profiles/so101/
    verified: true
    downloads: 0

  - name: koch-v1.1
    version: "1.0.0"
    author: community-user
    description: "Koch v1.1 arm with Dynamixel XL-330 servos"
    hardware: [dynamixel-xl330, ftdi-ft232]
    license: MIT
    path: profiles/koch-v1.1/
    verified: false
    downloads: 0
```

### 13.3 Profile Package Structure

```
profiles/so101/
    profile.yaml          # The robot profile (same format as Section 5)
    README.md             # Human-readable description, photos, setup notes
    calibration/          # Optional: reference calibration
        default.json
    diagnostics/          # Optional: profile-specific diagnostic checks
        power_supply.py
    CHANGELOG.md
    LICENSE
```

### 13.4 CLI Commands

```bash
armos profile list                    # List installed profiles
armos profile search "koch"           # Search the community registry
armos profile install koch-v1.1       # Download and install from registry
armos profile install ./my-profile/   # Install from local directory
armos profile update                  # Update all installed profiles
armos profile publish                 # Validate and submit a PR to the community repo
armos profile verify so101            # Run the profile's diagnostic suite
```

### 13.5 Paid Profiles (Year 2)

For paid profiles, the marketplace adds a thin payment layer:
- Stripe Checkout ($5-50, set by author)
- License keys tied to armos.dev account, not machine
- Revenue split: 70% author / 30% armOS

### 13.6 HuggingFace Hub Integration

For profiles that include trained policies, weights are stored on HuggingFace
Hub rather than in Git:

```yaml
# In profile.yaml
policies:
  pick_and_place:
    source: huggingface
    repo_id: armos-community/so101-pick-place
    revision: main
    file: policy.pt
```

`armos profile install` detects HuggingFace references and downloads from Hub
using the `huggingface_hub` library (already a LeRobot dependency).

---

## 14. Education Fleet Management

**[Growth]**

**Business driver:** Education licensing at $50-200/seat/year. A classroom with
30 arms needs centralized management.

### 14.1 Architecture: Hub and Spoke

```
                        +----------------------+
                        |   Fleet Hub          |
                        |   (instructor laptop |
                        |    or lab server)    |
                        |   FastAPI + SQLite   |
                        +----------+-----------+
                                   |
                    mDNS discovery  |  HTTP/WebSocket
                  (armos-hub.local) |
              +--------------------+--------------------+
              |                    |                    |
    +---------v------+   +---------v------+   +---------v------+
    | Station 1      |   | Station 2      |   | Station N      |
    | (student USB)  |   | (student USB)  |   | (student USB)  |
    | armos-agent    |   | armos-agent    |   | armos-agent    |
    +----------------+   +----------------+   +----------------+
```

### 14.2 Fleet Hub (Instructor Side)

```python
class FleetHub:
    """Central management server for a classroom fleet."""

    def register_station(self, station: StationInfo) -> str: ...
    def list_stations(self) -> list[StationStatus]: ...
    def push_profile(self, profile_name: str, station_ids: list[str]) -> None: ...
    def push_config_override(self, overrides: dict, station_ids: list[str]) -> None: ...
    def lock_stations(self, station_ids: list[str]) -> None: ...
    def unlock_stations(self, station_ids: list[str]) -> None: ...
    def start_recording_all(self, task_name: str) -> None: ...
    def collect_datasets(self, station_ids: list[str], dest: Path) -> None: ...
```

### 14.3 Fleet Agent (Student Side)

```python
class FleetAgent:
    """Runs on each student station. Reports status, accepts commands from hub."""

    def discover_hub(self) -> Optional[str]:
        """Use mDNS (zeroconf) to find armos-hub.local on the LAN."""

    def register(self) -> None: ...
    def heartbeat_loop(self) -> None:
        """Send status updates every 10 seconds via WebSocket."""
    def handle_command(self, command: FleetCommand) -> None: ...
```

### 14.4 Discovery Protocol

- **Primary:** mDNS via `zeroconf`. Hub advertises `_armos-hub._tcp.local.`.
- **Fallback:** Manual hub URL in `~/.config/armos/fleet.yaml`.
- **Security:** 6-digit join code displayed on instructor's screen. Maps to HMAC key for signed WebSocket messages.

### 14.5 Web Dashboard

```
+----------------------------------------------------------------+
|  armOS Fleet Dashboard            [Classroom: Robotics 101]    |
+----------------------------------------------------------------+
|  Stations Online: 28/30          Errors: 2                     |
|  +----+----+----+----+----+----+----+----+----+----+           |
|  | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 |         |
|  | OK | OK | !! | OK | OK | OK | -- | OK | OK | OK |           |
|  +----+----+----+----+----+----+----+----+----+----+           |
|  [Start Recording All]  [Collect Datasets]  [Lock All]         |
+----------------------------------------------------------------+
```

### 14.6 Network Requirements

- All communication is LAN-only. No cloud dependency.
- Hub and stations must be on the same subnet.
- Bandwidth: < 1 KB/heartbeat. Dataset collection is the heavy operation (~500 MB per 50-episode dataset).

---

## 15. Partnership Integration Points

**[Growth]**

### 15.1 Integration Architecture

```
+---------------------------+
|     Partner Ecosystem     |
+---------------------------+
| Seeed Studio / Feetech   |-----> Robot Profile (YAML)
|   - Hardware specs        |       + Verified badge
|   - Servo register maps   |       + Official diagnostics
|                           |
| HuggingFace               |-----> LeRobot Bridge Layer
|   - LeRobot API           |       + Dataset upload to Hub
|   - Dataset format        |       + Model download from Hub
|                           |
| NVIDIA                    |-----> Inference Runtime Plugin
|   - OpenVINO (Intel)      |       + Model format conversion
|   - TensorRT (Jetson)     |       + Hardware-accelerated inference
|                           |
| Foxglove / rerun.io       |-----> Data Export Bridge
|   - MCAP format           |       (See Section 16)
|   - Arrow IPC format      |
+---------------------------+
```

### 15.2 Seeed Studio / Feetech

- armOS provides a verified, tested profile for their hardware.
- Partners provide pre-release hardware access and undocumented register maps.
- Technical integration point: a YAML file in the profile registry marked `verified: true, partner: seeed-studio`.

### 15.3 HuggingFace Integration

1. **LeRobot Bridge** (Section 7): wraps LeRobot, isolates from API changes.
2. **Dataset Upload to Hub** via `huggingface_hub` library.
3. **Policy Download from Hub** via `hf_hub_download`.
4. **"Certified for armOS" badge** in HuggingFace model cards.

### 15.4 NVIDIA / Intel Inference Optimization

1. **Intel OpenVINO (Growth):** 2-5x inference speedup on Intel CPUs via ONNX-to-IR conversion.
2. **NVIDIA Jetson (Vision):** TensorRT for GPU-accelerated inference on ARM/Jetson.

---

## 16. Foxglove / rerun.io Bridge

**[Growth]**

armOS does NOT embed Foxglove or rerun viewers. Instead, it exports data in
their native formats. Users open exported files on their own machines.

**Rationale:** Embedding viewers adds hundreds of MB to the ISO and creates
version coupling with actively developed external tools. Export files are stable
and version-independent.

### 16.1 Foxglove Export (MCAP Format)

```python
class FoxgloveExporter:
    """Exports armOS telemetry sessions to MCAP files for Foxglove Studio."""

    def export_session(self, session_dir: Path, output_path: Path) -> Path:
        """Channels: /servo/{id}/position, /servo/{id}/velocity,
        /servo/{id}/load, /servo/{id}/voltage, /servo/{id}/temperature,
        /diagnostics, /camera/{name}/image, /command/goal_positions
        Schema: JSON Schema (no Protobuf dependency)."""
```

**Dependencies:** `mcap` (~50 KB, MIT). CLI: `armos export foxglove ./session/ -o session.mcap`

### 16.2 rerun.io Export (.rrd Format)

```python
class RerunExporter:
    """Exports armOS telemetry sessions to rerun .rrd files."""

    def export_session(self, session_dir: Path, output_path: Path) -> Path:
        """Entities: /robot/joint/{name}/position, velocity, load;
        /robot/servo/{id}/voltage, temperature; /camera/{name}; /diagnostics/{check}
        Uses rerun timeline concept: frame + wall_clock timelines."""
```

**Dependencies:** `rerun-sdk` (~15 MB). Optional install: `armos install rerun-export`.
CLI: `armos export rerun ./session/ -o session.rrd`

### 16.3 Live Streaming (Growth Scope)

For real-time visualization during teleop:

```bash
armos teleop --foxglove-live    # Starts teleop + Foxglove WS server on ws://localhost:8765
armos teleop --rerun-live       # Starts teleop + rerun serve
```

Growth scope because it adds latency to the teleop loop.

### 16.4 Data Format Mapping

| armOS Internal | Foxglove MCAP | rerun .rrd | ROS2 (future) |
|---------------|---------------|------------|---------------|
| ServoTelemetry | JSON Schema channel | Scalar entities | sensor_msgs/JointState |
| Camera frame | compressed_image | Image archetype | sensor_msgs/Image |
| Diagnostic result | JSON channel | TextLog entity | diagnostic_msgs/DiagnosticArray |
| Goal positions | JSON Schema channel | Scalar entities | trajectory_msgs/JointTrajectory |

---

## 17. Frontier AI Intelligence Layer

**[Vision]** -- Months 18-36. Builds on MVP and Growth foundations.

All components below are designed for CPU-only hardware (Intel i5-1035G4, 8 GB
RAM, no GPU) with cloud offloading for training workloads.

### 17.1 Embodied AI Agent -- Natural Language Robot Control

A user says "pick up the red block and put it on the blue plate." The system
parses the command, grounds objects in the camera feed, plans a trajectory,
executes servo commands, and monitors execution with retry on failure.

**Latency budget (speech to servo motion, < 2 seconds):**

```
Speech-to-text:        200ms  (local Whisper tiny via whisper.cpp)
Language understanding: 500ms  (cloud API or local SLM)
Visual grounding:       300ms  (YOLO-World-S via ONNX + OpenVINO)
Motion planning:        200ms  (analytical IK + RRT)
Servo execution:        500ms  (first motion visible)
Safety check:            50ms  (collision/torque limits)
Total:                ~1750ms
```

**Model selection for CPU inference:**

| Component | Model | Size | Latency (i5) |
|-----------|-------|------|-------------|
| Speech-to-text | Whisper tiny (whisper.cpp) | 39 MB | 150-300ms |
| Intent parsing (Phase 1) | Rule-based | 0 MB | <1ms |
| Intent parsing (Phase 2) | TinyLlama 1.1B Q4 (llama.cpp) | 700 MB | 2-5s |
| Visual grounding | YOLO-World-S (ONNX) | 50 MB | 150-250ms |
| Motion planning | ikpy (Phase 1), IKFast (production) | <1 MB | <10ms |

**Safety Governor:** Wraps all agent-initiated servo commands. Validates trajectory
against joint limits, velocity limits (max 60 deg/s), self-collision, workspace
bounds, and torque limits. Cannot be bypassed by the AI agent -- operates at the
HAL level (defense in depth). Emergency stop triggered by voice command, safety
violation, or watchdog timeout.

### 17.2 Self-Diagnosing Robot -- AI-Powered Telemetry Analysis

Continuous anomaly detection across four layers:

| Layer | Method | Runs at | CPU Impact |
|-------|--------|---------|-----------|
| 1 | Rule-based thresholds (from profile) | 10 Hz | ~0 |
| 2 | Statistical z-score (1h rolling window) | 10 Hz | ~50 MB |
| 3a | Isolation forest per servo (scikit-learn) | 1 Hz | ~100 MB |
| 3b | Autoencoder for cross-servo correlation (ONNX) | 1 Hz | ~100 MB |
| 4 | LLM interpretation (cloud API or local SLM) | On anomaly | ~0 (cloud) |

**Predictable failure modes for STS3215:**

| Failure Mode | Signal | Detection | Lead Time |
|-------------|--------|-----------|-----------|
| Bearing wear | Load increases for same motion | Linear regression | Days-weeks |
| Overheating | Temperature ramp rate | Rate-of-change threshold | 10-30 min |
| Voltage collapse | Voltage drops correlate with load | Multi-servo regression | Seconds |
| Cable fatigue | Intermittent comm errors | Error rate trend | Days |
| Calibration drift | Monotonic position error growth | Drift rate | Hours-days |

### 17.3 Cross-Robot Learning -- Federated Intelligence

Fleet data aggregation with a three-phase privacy approach:

1. **Phase 1 (< 1,000 instances):** Centralized aggregation of anonymized statistics. Strict data minimization.
2. **Phase 2 (1,000+ instances):** Differential privacy (Laplace noise, epsilon = 1.0 per metric per 24h).
3. **Phase 3 (5,000+ instances):** Federated model training via Flower framework.

**Shared:** hardware config, calibration parameters, aggregate telemetry statistics, failure events.
**Never shared:** camera images, motion trajectories, user identity, raw telemetry streams.

### 17.4 Sim-to-Real Pipeline

- **MuJoCo** (Apache 2.0) as primary simulator for cloud training (1,000-5,000 Hz headless).
- **PyBullet** (MIT) for local visualization and basic testing (100-500 Hz on i5).
- **Digital twin** via rerun.io: 3D rendering of real arm state from live telemetry.
- URDF/MJCF models generated from robot profiles via `SimModelBuilder`.
- Domain randomization for sim-to-real transfer (mass, friction, delay, lighting, textures).

### 17.5 Vision-Language-Action Models

The CPU-realistic path is **Octo** (Berkeley Robot Learning):

| Model | Size (Q4) | CPU Latency | Control Hz |
|-------|-----------|-------------|------------|
| Octo-Small | ~20 MB | 50-150ms | 5-10 Hz |
| Octo-Base | ~60 MB | 200-500ms | 2-5 Hz |

Integration via ONNX Runtime + OpenVINO. Recording pipeline extended with
`armos record --task "description"` for language-annotated demonstrations.

### 17.6 Autonomous Data Collection

Practical approaches for CPU-only hardware:

1. **Scripted exploration** with random perturbation (60-120 episodes/hour, no ML needed).
2. **Visual outcome detection** via OpenCV frame differencing (~5ms).
3. **DAgger** human-in-the-loop correction (most practical convergence path).
4. **Overnight collection workflow:** `armos collect --task "..." --episodes 500 --overnight`

### 17.7 Hardware Constraints Reference

With 8 GB RAM and ~5 GB available after OS:

```
Base armOS + Python + HAL:           ~500 MB
LeRobot + PyTorch (CPU):             ~800 MB
Camera pipeline (2 cameras):          ~200 MB
Telemetry + SQLite:                   ~100 MB
Available for AI models:            ~3,400 MB

Maximum simultaneous:
  YOLO-World + Octo-Base + Whisper = ~1,000 MB  (fits)
  YOLO-World + TinyLlama + Whisper = ~2,300 MB  (fits, tight)
```

**OpenVINO** is the single most important optimization: 2-5x speedup over
PyTorch on Intel CPUs, the difference between 1 Hz and 5 Hz inference.

---

## 18. Future Platform Targets

**[Growth/Vision]**

### 18.1 Raspberry Pi 5 ARM Image

**Priority: High (Growth)**. The RPi 5 is the natural compute platform for
embedded robots (LeKiwi, Reachy Mini). armOS should provide an ARM image alongside
the x86 USB ISO.

| Variant | Price | Notes |
|---------|-------|-------|
| RPi 5 4GB | $60 | Minimum viable for inference |
| RPi 5 8GB | ~$90 | Recommended for LeRobot |

**Delivery options:**
- Raspberry Pi OS image (`.img` file flashed to SD card)
- Docker container on stock Raspberry Pi OS
- `pip install armos` on existing RPi installation

### 18.2 Docker Container

```
docker run -it --privileged --device=/dev/ttyUSB0 armos/armos:latest
```

**Advantages:** Works on any Linux host without rebooting, no package conflicts,
easy version management, CI/CD friendly.

**Disadvantages:** `--privileged` needed for USB, ~50ms added USB latency (negligible
for servo control), users must have Docker installed.

Docker is the right delivery mechanism for developers and CI. It complements (not
replaces) the USB boot image.

### 18.3 NVIDIA Jetson

**Priority: Vision**. The Jetson Orin Nano Super at $249 is the GPU-accelerated
target. Unlocks TensorRT inference for LeRobot policies. The `InferenceBackend`
abstraction (Section 7) already accounts for this.

### 18.4 LeKiwi Mobile Base

**Priority: High (Growth)**. First mobile robot target. Shares the SO-101 servo
ecosystem (Feetech STS3215), uses LeRobot framework. ~$440 for mobile manipulator
(base + arm). Profile support requires adding motor control for 3 base drive
motors and basic navigation.

### 18.5 Hardware Expansion Priority Matrix

#### Horizon 1 (Ship with armOS v1.0)

| Item | Effort | Impact |
|------|--------|--------|
| Waveshare Gripper-A profile | Low | High (same bus as SO-101) |
| OAK-D Lite camera support | Medium | High |
| Voltage/current diagnostics | Low | High (partially implemented) |

#### Horizon 2 (6-18 months)

| Item | Effort | Impact |
|------|--------|--------|
| Raspberry Pi 5 ARM image | High | Very High |
| LeKiwi mobile base profile | Medium | Very High |
| Docker container delivery | Medium | High |
| CAN bus servo driver | High | High (unlocks MyActuator, Damiao, CubeMars) |
| Reachy Mini Lite profile | Medium | Medium |

#### Horizon 3 (18-36 months)

| Item | Effort | Impact |
|------|--------|--------|
| Jetson Orin Nano image | High | High |
| HopeJr humanoid profile | Very High | Medium |
| QDD actuator profiles | Medium | Medium |

#### Do Not Pursue

| Item | Reason |
|------|--------|
| Drone manipulation | Entirely different control domain, safety certification |
| Soft robotics | No standardized USB interface |
| Phone as robot brain | Insufficient compute, high app development cost |
| Apple Silicon native | Tiny market overlap; Docker covers the use case |
| ZED cameras | Require NVIDIA GPU for depth |

---

## 19. Architecture Decision Records

### ADR-1: Python as Primary Language

**Status:** Accepted
**Phase:** MVP
**Context:** armOS needs to be accessible to the robotics hobbyist community.
**Decision:** Python 3.12+ as the primary language for all components.
**Rationale:** LeRobot is Python-based; robotics community predominantly uses Python; `pyudev`, `pyserial`, `textual`, `fastapi` are all mature Python libraries; contributor accessibility is maximized.
**Trade-offs:** Serial communication latency is higher than C/Rust (mitigated by servo controllers doing the real-time work). No true real-time guarantees (acceptable for teleop at 60 Hz).

### ADR-2: live-build Over Cubic for ISO Creation

**Status:** Accepted
**Phase:** MVP
**Context:** Need a reproducible way to build the custom Ubuntu ISO.
**Decision:** Use Debian `live-build` toolchain in a containerized build environment (`Dockerfile.build`).
**Rationale:** Scriptable, CI/CD compatible, reproducible. Used by Ubuntu itself. Supports custom package lists, hooks, chroot modifications. Containerized builds prevent "works on my machine" issues.
**Trade-offs:** Steeper learning curve than Cubic. Longer build times (~30-60 minutes).

### ADR-3: Plugin Architecture for Hardware Drivers

**Status:** Accepted
**Phase:** MVP
**Context:** Need to support Feetech today, Dynamixel and CAN-based servos in the future.
**Decision:** Abstract base class (`ServoProtocol`) with concrete plugin implementations. Python entry points for plugin discovery.
**Rationale:** Clean separation between protocol-specific code and generic robot logic. New hardware = new plugin, no core changes. Entry points allow third-party packages to register protocols without modifying armOS core.
**Trade-offs:** Abstraction layer adds small overhead. Lowest-common-denominator API mitigated by `read_register`/`write_register` escape hatch.

### ADR-4: YAML for Robot Profiles, JSON for Calibration

**Status:** Accepted
**Phase:** MVP
**Context:** Need human-readable configuration for robot definitions and calibration data.
**Decision:** YAML for profiles (human-edited), JSON for calibration data (machine-generated).
**Rationale:** YAML supports comments (essential for explaining protection settings). JSON is the existing LeRobot calibration format. Pydantic validates both at load time.

### ADR-5: No ROS2 Dependency

**Status:** Accepted
**Phase:** MVP
**Context:** ROS2 is the industry standard for robotics middleware.
**Decision:** armOS does not depend on ROS2. A future `armos-ros2-bridge` provides interop via the JSON-over-newline IPC protocol on the Unix domain socket.
**Rationale:** ROS2 adds ~2 GB and significant complexity. Target users find ROS2 overwhelming. LeRobot does not use ROS2. The bridge design publishes servo telemetry as ROS2 topics and subscribes to command topics.
**Trade-offs:** No access to ROS2 ecosystem tools out of the box.

### ADR-6: FastAPI + htmx for Web Dashboard

**Status:** Accepted
**Phase:** MVP
**Context:** Need a web UI for remote monitoring without heavy frontend tooling.
**Decision:** FastAPI backend with htmx for dynamic updates, no JavaScript SPA framework.
**Rationale:** FastAPI is async-native; htmx provides dynamic updates with zero JS build tooling; WebSocket for telemetry is native; total frontend < 500 lines.
**Trade-offs:** Less interactive than React/Vue. Limited to server-rendered patterns.

### ADR-7: Single Bus Thread Concurrency Model

**Status:** Accepted
**Phase:** MVP
**Context:** The teleop loop and telemetry polling both need serial bus access. A lock-per-port with separate threads causes jitter from lock contention.
**Decision:** A single reader/writer thread per bus performs a combined read-write cycle: read leader positions, read follower telemetry, write follower goal positions, publish to subscribers. No separate telemetry thread.
**Rationale:** Eliminates lock contention entirely. Guarantees deterministic cycle timing. Telemetry is a subscriber of the bus thread's output, not an independent reader.
**Consequences:** Telemetry sampling rate is tied to the teleop rate (60 Hz). This is a feature, not a limitation -- telemetry at a different rate would add bus contention.

### ADR-8: Cloud Training API Protocol

**Status:** Proposed
**Phase:** Growth
**Context:** The cloud training service needs a protocol between armOS (local) and the training backend.
**Decision:** HTTPS REST API with tus.io for resumable uploads and Server-Sent Events for status streaming.
**Rationale:** HTTPS works through firewalls and proxies. tus.io is the standard for resumable uploads (Vimeo, GitHub, Cloudflare). SSE is simpler than WebSocket for unidirectional status updates. Target users are on home/university networks where exotic protocols are blocked.
**Consequences:** Higher overhead than gRPC for status polling. Acceptable for infrequent updates.

### ADR-9: Telemetry Storage Format

**Status:** Proposed
**Phase:** Growth
**Context:** Telemetry data is collected locally and optionally transmitted to analytics server.
**Decision:** SQLite for local storage. JSON-over-HTTPS for transmission. DuckDB for server-side analytics.
**Rationale:** SQLite is zero-config, ships with Python, handles concurrent reads. DuckDB is columnar and optimized for aggregate queries. JSON-over-HTTPS is trivially debuggable.
**Consequences:** Local SQLite grows over time. Mitigated by 90-day retention cap and VACUUM on startup.

### ADR-10: Profile Distribution Mechanism

**Status:** Proposed
**Phase:** Growth
**Context:** Community profiles need to be discoverable, installable, and updatable.
**Decision:** Git repository as canonical registry with sparse checkout. HuggingFace Hub for binary policy weights.
**Rationale:** Git is the lingua franca of open-source contribution. GitHub PR workflow provides review, CI validation, audit trail. HuggingFace Hub is already a dependency for model hosting.
**Alternatives rejected:** PyPI packages (too heavy for YAML), custom HTTP API (unnecessary infrastructure).
**Consequences:** Requires network for install (installed profiles work offline). Paid profiles need license key layer.

### ADR-11: Fleet Management Discovery Protocol

**Status:** Proposed
**Phase:** Growth
**Context:** Education fleet management requires stations to find the instructor's hub on the LAN.
**Decision:** mDNS via `zeroconf` Python library, with manual URL fallback. 6-digit join code for authentication.
**Rationale:** mDNS is zero-configuration on most LANs. `zeroconf` is pure Python, ~100 KB. University networks sometimes block mDNS, hence the fallback. Join code provides lightweight auth without PKI.
**Consequences:** Adds `zeroconf` as optional dependency. Fleet features disabled by default.

### ADR-12: Visualization Bridge Strategy

**Status:** Proposed
**Phase:** Growth
**Context:** Foxglove ($58M raised) and rerun.io ($20M raised) are well-funded visualization tools.
**Decision:** Export-only for MVP (MCAP and .rrd file export). Live streaming as Growth scope. No embedded viewers.
**Rationale:** Embedding adds hundreds of MB and version coupling. Export files are stable. Users who need visualization already have these tools. armOS is a data source, not a visualization tool.
**Consequences:** Users must install Foxglove or rerun separately. `mcap` is tiny; `rerun-sdk` (15 MB) is optional.

### ADR-13: Inference Runtime Strategy

**Status:** Proposed
**Phase:** Vision
**Context:** All AI models must run on Intel i5 CPUs without discrete GPUs.
**Decision:** ONNX Runtime with OpenVINO Execution Provider as primary. whisper.cpp for STT. llama.cpp for local LLMs. PyTorch as fallback only.
**Rationale:** ONNX Runtime + OpenVINO delivers 2-5x speedup over PyTorch on Intel CPUs via AVX2 and iGPU. whisper.cpp and llama.cpp are purpose-built for CPU inference. The three runtimes cover vision, language, and VLA models without CUDA dependencies.
**Consequences:** Every model must be ONNX-exportable. Build pipeline includes ONNX export and validation steps.

### ADR-14: Embodied Agent Safety Architecture

**Status:** Proposed
**Phase:** Vision
**Context:** Natural language robot control means the AI agent generates servo commands. Misinterpretation or hallucination could cause dangerous motions.
**Decision:** SafetyGovernor at HAL level validates every trajectory (joint limits, velocity, torque, workspace). Agent cannot bypass it. Emergency stop on voice command, safety violation, or watchdog timeout.
**Rationale:** Defense in depth. AI agent is untrusted input to the servo system. Safety governor is small, auditable, deterministic -- no ML in the safety path.
**Consequences:** ~50ms latency per servo command. May reject aggressive motions (configurable bounds).

### ADR-15: Anomaly Detection Model Selection

**Status:** Proposed
**Phase:** Vision
**Context:** Servo anomaly detection must run continuously on CPU without impacting teleop.
**Decision:** Isolation Forest per servo for univariate anomalies. Tiny autoencoder (ONNX) for cross-servo correlations. Both at 1 Hz on a background thread.
**Rationale:** Isolation Forest is best-studied for tabular data, needs no hyperparameter tuning, trains in seconds, predicts in microseconds. 1 Hz reduces CPU by 90% with negligible delay. Rule-based thresholds (Layer 1) at 10 Hz catch spikes.
**Consequences:** ~1 second anomaly detection latency. Acceptable for trends; spikes caught by rule layer.

### ADR-16: Cross-Robot Learning Privacy Strategy

**Status:** Proposed
**Phase:** Vision
**Context:** Fleet data aggregation provides value but raises privacy concerns.
**Decision:** Three-phase: (1) opt-in with data minimization at < 1,000 instances, (2) differential privacy at 1,000+, (3) federated learning at 5,000+.
**Rationale:** Privacy protection scales with risk. At small scale, data minimization suffices and DP noise would destroy utility. Progression is a natural maturation path.
**Consequences:** Fleet recommendations less accurate at small scale. Acceptable vs zero fleet learning.

### ADR-17: Simulation Strategy

**Status:** Proposed
**Phase:** Vision
**Context:** Sim-to-real is essential but simulators are heavy.
**Decision:** PyBullet for local visualization (MIT, pip-installable, 100-500 Hz CPU). MuJoCo for cloud training (Apache 2.0, 1,000-5,000 Hz). No simulator in ISO by default -- `armos sim install` on demand.
**Rationale:** Bundling adds 50-200 MB for a minority use case. On-demand keeps ISO lean.
**Consequences:** One-time `armos sim install` step before simulation features.

---

## 20. Data Flow Diagrams

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

## 21. Deployment Architecture

**[MVP]**

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
  +-- armos/                # Persistent partition (f2fs, writable)
        config/               # Symlinked to ~/.config/armos
        calibration/          # Preserved across boots
        datasets/             # Recorded data
        logs/                 # Diagnostic/telemetry logs
```

The persistent partition uses f2fs for flash-wear leveling and expands to fill
remaining USB space on first boot via casper persistence.

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
        |  (IPC via Unix domain socket at /run/armos/detect.sock
        |   JSON-over-newline protocol, no TCP/IP listeners)
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

## 22. Security Considerations

### Threat Model

armOS is a local-only system for controlling physical robots. It is not
a server, not internet-facing, and not multi-user.

| Concern | Mitigation |
|---------|-----------|
| Serial port access | udev rules grant access by group, not world-writable in production |
| USB device spoofing | Profile matching verifies servo responses, not just USB IDs |
| Passwordless sudo | Required for setup automation; production ISO uses locked-down sudoers |
| Network exposure | Web dashboard binds to localhost by default; `--bind 0.0.0.0` is opt-in |
| Dataset integrity | Per-episode manifests with SHA256 checksums |
| Supply chain | ISO builds are reproducible in containers; dependencies pinned in lockfile |
| Dataset privacy | Uploaded datasets used solely for user's training job, deleted after 30 days |
| Cloud API keys | Scoped per-user, stored with 0600 permissions, no shared keys |
| Fleet auth | Join code maps to HMAC key for signed WebSocket messages |

### Principle: Local-First, Network-Optional

The system works fully offline. Network features (HuggingFace upload, web
dashboard on LAN, cloud training, telemetry transmission, fleet management)
are all opt-in.

---

## 23. Migration Path from Current Codebase

The existing scripts are the seed for the armOS package:

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
| LeRobot monkey-patches | `armos/ai/lerobot_patches.py` | Applied at import time, signature-checked |

### Migration Phases

**Phase A: Package skeleton** (Epic 1) -- Create the `armos` package with CLI entry
points. Move existing scripts into the package structure. Everything still works,
just invoked as `armos diagnose` instead of `python diagnose_arms.py`.

**Phase A.5: Validation harness** -- Before old scripts are deleted, integration tests
run both the old script and the new `armos` equivalent on the same hardware and
compare outputs. Ensures identical behavior. Removed after Phase C.

**Phase B: Hardware abstraction and profiles** (Epics 2, 3) -- Implement `ServoProtocol`
and `FeetechPlugin`. Refactor diagnostic checks to use the protocol interface.
Introduce robot profiles with SO-101 as the first implementation.

**Phase C: Diagnostics and telemetry** (Epics 4, 5) -- Decompose `diagnose_arms.py`
into modular health checks. Extract telemetry streaming into pluggable backends.

**Phase D: Calibration, teleop, and TUI** (Epics 6, 7) -- Implement calibration
persistence, leader-follower teleoperation CLI, and the TUI launcher menu.

**Phase E: ISO build and AI integration** (Epics 8, 9) -- Set up `live-build`
configuration. Package into bootable ISO. Integrate LeRobot data collection and
Claude Code context files.

**Phase F: Growth and polish** (Epic 10) -- Multi-hardware support (Dynamixel,
pyudev hotplug, profile wizard), web dashboard, plugin architecture. Cloud
training client, profile marketplace, fleet management. Foxglove/rerun export
bridges.

---

## 24. Implementation Priority

### Enhancement Timeline

| Enhancement | Phase | When | Dependency |
|------------|-------|------|------------|
| Foxglove/rerun export (file) | Growth | Sprint 7-8 | Telemetry stream |
| Telemetry local DB + `armos stats` | Growth | Sprint 7-8 | Metrics module |
| Profile marketplace (Git-based) | Growth | Month 7-9 | Profile system (Section 5) |
| Cloud training client (local side) | Growth | Month 7-9 | Data collection pipeline (Section 7) |
| Telemetry transmission (opt-in) | Growth | Month 9-10 | Local telemetry DB |
| Fleet management (hub + agent) | Growth | Month 10-12 | Web dashboard (Section 8) |
| Cloud training backend (server) | Growth | Month 9-12 | Cloud API contract (Section 11.3) |
| Paid profiles + license keys | Growth | Month 12+ | Profile marketplace |
| Live Foxglove/rerun streaming | Growth | Month 12+ | Export bridge |
| OpenVINO inference optimization | Growth | Month 10-12 | Inference backend (Section 7) |
| RPi 5 ARM image | Growth | Month 12-15 | Core package stabilized |
| Docker container | Growth | Month 10-12 | Core package stabilized |
| Embodied AI agent (Phase 1) | Vision | Month 18-24 | HAL, profiles, ONNX Runtime |
| Self-diagnosing robot | Vision | Month 18-28 | Telemetry DB, scikit-learn |
| Cross-robot learning | Vision | Month 20-36 | Fleet telemetry, cloud infra |
| Sim-to-real pipeline | Vision | Month 20-34 | Robot profiles, cloud training |
| VLA models (Octo) | Vision | Month 22-36 | ONNX Runtime, recording pipeline |
| Autonomous data collection | Vision | Month 24-36 | Motion planner, safety governor |
| NVIDIA Jetson support | Vision | Month 18+ | ARM ISO build pipeline |

**Key principle:** Local-side components (export, telemetry DB, upload client)
are built before their server-side counterparts. Users benefit from local
tooling immediately while cloud infrastructure is developed.

---

*Consolidated architecture document for armOS -- a universal robot operating system on a USB stick.*
*Incorporates core architecture, business-aligned enhancements, architect review corrections, frontier AI intelligence roadmap, and hardware ecosystem expansion plans.*
