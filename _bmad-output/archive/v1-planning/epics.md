# armOS USB - Epic Breakdown

**Author:** John (Product Manager Agent)
**Date:** 2026-03-15
**Status:** Consolidated v2.1
**Version:** 2.1

---

## Overview

This document provides the complete epic and story breakdown for armOS USB, decomposing the requirements from the PRD and Architecture into implementable stories. Epics are ordered by the architecture's migration phases (A through F) and aligned to the PRD's three-phase product scope: MVP (v0.1), Growth (v0.5), and Vision (v1.0).

Version 2.1 consolidates findings from the developer review, scrum master review, QA/execution enhancements, and implementation enhancements documents. Key changes from v2.0:
- Demo mode (B4) pulled into MVP Epic 7 as Story 7.4 and scheduled in Sprint 6a
- New Epic 11 "Business Enablement" for Growth-phase business features (5 stories: B1-B5)
- SDK conformance tests (SDK2) added to MVP Epic 2
- CI/CD and distribution stories added to MVP Epic 8
- ISO version metadata (V2) added to MVP Epic 8
- Updated requirements traceability matrix covering all FRs including FR45-FR55
- Updated story point summary
- Sprint plan compressed to 20 weeks to public launch

---

## Requirements Inventory

### Functional Requirements

| ID | Requirement | Phase |
|----|-------------|-------|
| FR1 | USB-serial adapter detection (CH340, FTDI, CP2102) and protocol identification | MVP (CH340 only), Growth (all) |
| FR2 | Servo bus scan and enumeration | MVP |
| FR3 | Profile matching from detected hardware | Growth |
| FR4 | USB camera detection via V4L2 | MVP |
| FR5 | Device-to-role assignment with user confirmation | Growth |
| FR6 | Automatic udev rules and serial port permissions | MVP |
| FR7 | YAML robot profile loading | MVP |
| FR8 | Guided robot profile creation | Growth |
| FR9 | Profile export/import | Growth |
| FR10 | Pre-built SO-101 profile | MVP |
| FR11 | Apply protection settings from profile to servo bus | MVP |
| FR12 | Guided calibration procedure | MVP |
| FR13 | Calibration persistence across reboots | MVP |
| FR14 | Calibration validation and staleness warning | MVP (pulled from Growth -- see Story 3.4) |
| FR15 | Leader-follower teleoperation from dashboard | MVP |
| FR16 | Live telemetry during teleoperation | MVP |
| FR17 | Auto-halt on protection threshold breach | MVP |
| FR18 | Configurable teleop parameters | Growth |
| FR19 | Hardware diagnostics (per-servo health checks) | MVP |
| FR20 | Real-time servo telemetry stream | MVP |
| FR21 | Telemetry logging (CSV) | MVP |
| FR22 | Programmatic arm exercise routines | MVP |
| FR23 | Fault detection and alerting | MVP |
| FR24 | Record teleop sessions as LeRobot datasets | MVP |
| FR25 | Episode management (start, stop, discard) | MVP |
| FR26 | Episode review and replay | Growth |
| FR27 | Dataset export in LeRobot format | MVP |
| FR28 | Bootable USB image with all dependencies | MVP |
| FR29 | Persistent storage across reboots | MVP |
| FR30 | Offline operation (no internet required) | MVP |
| FR31 | Windows flash script | MVP |
| FR32 | USB image cloning for fleet deployment | Growth |
| FR33 | TUI dashboard with hardware status | MVP |
| FR34 | TUI workflow launcher (keyboard shortcuts) | MVP |
| FR35 | Live camera feeds in TUI | Growth |
| FR36 | Bus disconnection detection and alert | MVP |
| FR37 | AI-assisted troubleshooting context | MVP |
| FR38 | AI troubleshooting with live system state | Vision |
| FR39 | ServoProtocol plugin architecture (ABC) | MVP (ABC), Growth (plugins) |
| FR40 | Entry-point-based plugin discovery | Growth |
| FR41 | Plugin scaffolding command | Vision |
| FR42 | Teleop watchdog (disable torque on stall) | MVP |
| FR43 | First-run setup wizard | MVP |
| FR44 | Plymouth boot splash | MVP |
| FR45 | Demo mode (kiosk) for trade shows and videos | MVP |
| FR46 | Anonymous telemetry collection (opt-in) | Growth |
| FR47 | Cloud training upload hook | Growth |
| FR48 | Profile sharing via HuggingFace Hub | Growth |
| FR49 | Fleet deployment config export/import | Growth |
| FR50 | ISO distribution pipeline (HuggingFace Hub + fallbacks) | MVP |
| FR51 | ISO version metadata (/etc/armos-release) | MVP |
| FR52 | Reproducible ISO builds via Docker | MVP |
| FR53 | QEMU ISO smoke test | MVP |
| FR54 | ServoProtocol conformance test suite | MVP |
| FR55 | armos update command (OTA package updates) | Growth |

### Non-Functional Requirements (Summary)

| ID | Requirement |
|----|-------------|
| NFR1 | Python 3.12+, Linux x86_64 |
| NFR2 | Single-file install via pip |
| NFR3 | Hardware detection within 5 seconds |
| NFR4 | Telemetry update rate 10 Hz minimum |
| NFR5 | Boot to TUI within 90 seconds |
| NFR6 | Retry with exponential backoff on transient serial errors |
| NFR7 | Graceful degradation on hardware disconnect |
| NFR8 | No data loss on crash (episodes saved immediately) |
| NFR9 | Filesystem survives unexpected power loss |
| NFR10 | 80%+ boot success on post-2016 x86 UEFI hardware |
| NFR11 | All workflows accessible without terminal commands |
| NFR12 | Actionable error messages with remediation steps |
| NFR13 | Sub-500ms teleop loop stall detection |
| NFR14 | ISO size under 16GB |
| NFR15 | All public APIs documented with Google-style docstrings |
| NFR16 | 80%+ test coverage |
| NFR17 | Profile schema validated with Pydantic |
| NFR18 | ServoProtocol ABC has fewer than 12 abstract methods |
| NFR19 | Plugin implementable in under 500 lines |
| NFR20 | Green CI on every merge |
| NFR21 | Pre-commit hooks (ruff, mypy) from day one |
| NFR22 | No user data transmitted without explicit action |

---

## Story-to-FR Coverage Map

| Story | FRs Covered |
|-------|-------------|
| 0.1 | -- (infrastructure) |
| 0.2 | -- (infrastructure) |
| 1.1 | -- (infrastructure) |
| 1.2 | -- (infrastructure) |
| 1.3 | -- (infrastructure) |
| 1.4 | -- (infrastructure) |
| 1.5 | FR37 |
| 2.1 | FR1 (CH340), FR39 (partial) |
| 2.2 | FR2, FR23 (partial) |
| 2.3 | FR11 |
| 2.4 | NFR6 |
| 2.5 | FR54 |
| 3.1 | FR7, FR10, NFR17 |
| 3.2 | FR7 (validation) |
| 3.3 | FR12, FR13 |
| 3.4 | FR14 |
| 3.5 | FR4 |
| 4.1 | FR19 (partial) |
| 4.2a | FR19, FR23 |
| 4.2b | FR19, FR23 |
| 4.3 | FR19, FR21 |
| 4.4 | FR22 |
| 5.1 | FR20, FR16 |
| 5.2 | FR21 |
| 5.3 | FR23, FR36, NFR7, NFR12 |
| 6.1 | FR12 |
| 6.2 | FR15, FR17, FR42 |
| 6.3 | FR16 |
| 6.4 | FR1 (CH340), FR4 |
| 7.0 | FR43 |
| 7.1 | FR33 (TUI), FR34 (TUI) |
| 7.2 | FR33 (TUI) |
| 7.3 | FR34 (TUI), NFR11 |
| 7.4 | FR45 |
| 8.1a | NFR5 (spike validation) |
| 8.1b | FR28, FR30, NFR5, NFR14 |
| 8.2 | FR6, FR29, NFR9 |
| 8.3 | FR31 |
| 8.4 | NFR10 |
| 8.5 | FR44 |
| 8.6 | FR52 |
| 8.7 | FR53 |
| 8.8 | FR50 |
| 8.9 | FR51 |
| 9.1 | FR37 |
| 9.2 | FR24, FR25, FR27 |
| 9.3 | FR24, FR27, NFR8 |
| 10.1 | FR1 (all chips), FR3, FR5, NFR3 |
| 10.2 | FR39, FR40, FR41 (partial) |
| 10.3 | FR8, FR9 |
| 10.4 | FR18, FR26, FR35 |
| 10.5 | FR32 |
| 10.6 | FR38 |
| 11.1 | FR46 |
| 11.2 | FR47 |
| 11.3 | FR48 |
| 11.4 | FR49 |
| 11.5 | FR55 |

---

## Epic List

| Epic | Title | Phase | Product Scope | Priority |
|------|-------|-------|---------------|----------|
| 0 | Sprint 0 -- Tooling and Environment Setup | Pre-A (Sprint 0) | MVP | P0 |
| 1 | Package Skeleton and CLI Foundation | A (Package skeleton) | MVP | P0 |
| 2 | Hardware Abstraction Layer -- Feetech | B (HAL and profiles) | MVP | P0 |
| 3 | Robot Profile System -- SO-101 | B (HAL and profiles) | MVP | P0 |
| 4 | Diagnostic Framework Refactor | C (Diagnostics and telemetry) | MVP | P0 |
| 5 | Telemetry and Monitoring Library | C (Diagnostics and telemetry) | MVP | P0 |
| 6 | Calibration and Teleop CLI | D (Calibration, teleop, TUI) | MVP | P0 |
| 7 | TUI Launcher | D (Calibration, teleop, TUI) | MVP | P1 |
| 8 | Pre-built USB Image | E (ISO build and AI) | MVP | P0 |
| 9 | AI Integration and Data Collection | E (ISO build and AI) | MVP | P0 |
| 10 | Growth Phase -- Multi-Hardware and Polish | F (Growth and polish) | Growth/Vision | P2 |
| 11 | Business Enablement | F (Growth and polish) | Growth | P2 |

---

## Epic 0: Sprint 0 -- Tooling and Environment Setup

**Goal:** Establish CI/CD, test infrastructure, MockServoProtocol, code quality tooling, and hardware inventory before any feature work begins.

**Migration Phase:** Pre-A (Sprint 0)
**Product Scope:** MVP (v0.1)

### Story 0.1: CI/CD, Test Fixtures, MockServoProtocol, and Code Quality Tooling

As a **developer**,
I want a CI/CD pipeline, pytest configuration, MockServoProtocol, and pre-commit hooks (ruff, mypy) in place from day one,
So that every subsequent story has automated testing, consistent code quality, and regression safety.

**Acceptance Criteria:**

**Given** the repository has a GitHub Actions workflow
**When** I push to any branch
**Then** ruff lint, mypy type check, and pytest all run and must pass

**Given** the `MockServoProtocol` class exists
**When** I instantiate it with `servo_ids=[1,2,3,4,5,6]`
**Then** it implements the full `ServoProtocol` ABC with in-memory state, configurable failure rates, and a call log for assertions

**Given** `conftest.py` exists
**When** I run pytest
**Then** fixtures are available: `mock_protocol`, `sample_profile`, `tmp_config_dir`

**Size:** M
**Dependencies:** None

---

### Story 0.2: Hardware Inventory and Test Environment Setup

As a **developer**,
I want a documented inventory of all available hardware (machines, servos, cameras, USB hubs) and a reproducible development environment setup,
So that hardware availability is known before feature work begins and any contributor can bootstrap the dev environment.

**Acceptance Criteria:**

**Given** the hardware inventory document exists
**When** I review it
**Then** it lists all available test machines, servo kits, cameras, and USB adapters with their status

**Given** a new contributor clones the repository
**When** they run `make dev`
**Then** the development environment is fully configured (venv, dependencies, pre-commit hooks)

**Size:** S
**Dependencies:** None

---

## Epic 1: Package Skeleton and CLI Foundation

**Goal:** Establish the `armos` Python package structure with `src/` layout, CLI entry point using Click, utility modules, and AI context files. This is the foundation everything else builds on.

**Migration Phase:** A
**Product Scope:** MVP (v0.1)

### Story 1.1: Initialize Python Package with pyproject.toml

As a **developer**,
I want a `pyproject.toml` with `src/` layout, `click` entry point, dependency declarations, and `[dev]` extras,
So that `pip install -e .[dev]` works and the package structure is established.

**Acceptance Criteria:**

**Given** the repository has a `src/armos/` directory with `__init__.py`
**When** I run `pip install -e .[dev]`
**Then** the `armos` command is available and `import armos` works

**Given** the `pyproject.toml` specifies tool configuration
**When** I inspect it
**Then** ruff, mypy, and pytest are configured with the project's standard settings

**Size:** S
**Dependencies:** None

---

### Story 1.2: CLI Command Group Structure

As a **developer**,
I want all top-level CLI commands defined as Click stubs so the command surface area is established,
So that subsequent stories can implement individual commands without restructuring the CLI.

**Acceptance Criteria:**

**Given** the `armos` package is installed
**When** I run `armos detect --help`
**Then** I see a help message describing the detect command
**And** the same works for `status`, `calibrate`, `teleop`, `record`, `diagnose`, `monitor`, `exercise`, and `config`

**Given** a stub command is invoked (e.g., `armos detect`)
**When** the underlying implementation is not yet complete
**Then** the command prints "Not yet implemented" and exits with code 1

**Size:** S
**Dependencies:** 1.1

---

### Story 1.3: Utility Module -- Serial Helpers

As a **developer**,
I want a `armos.utils.serial` module with sign-magnitude decoding, port discovery helpers, and common serial constants,
So that all downstream code shares one tested implementation of these utilities.

**Acceptance Criteria:**

**Given** a raw register value in Feetech sign-magnitude format (e.g., load = 1033)
**When** I call `decode_sign_magnitude(1033, 1024)`
**Then** I receive the decoded float value `0.88%` (positive direction)

**Given** the utility module is imported
**When** I call `list_serial_ports()`
**Then** I receive a list of available `/dev/tty*` paths with vendor/product ID metadata

**Size:** S
**Dependencies:** 1.1

---

### Story 1.4: Utility Module -- XDG Config Paths

As a **developer**,
I want a `armos.utils.config` module that provides XDG-compliant paths for profiles, calibration, datasets, and logs,
So that all file storage follows a consistent, predictable convention.

**Acceptance Criteria:**

**Given** the module is imported
**When** I call `config_dir()`, `calibration_dir()`, `datasets_dir()`, `logs_dir()`
**Then** each returns the correct XDG path under `~/.config/armos/` or `~/.local/share/armos/`

**Size:** S
**Dependencies:** 1.1

---

### Story 1.5: Migrate CLAUDE.md and AI Context Files

As a **developer**,
I want the existing CLAUDE.md and memory files migrated into the armos package structure,
So that AI-assisted troubleshooting context is maintained and versioned with the code.

**Acceptance Criteria:**

**Given** the `armos` package has a `context/` directory
**When** I inspect it
**Then** it contains the migrated CLAUDE.md and relevant memory files
**And** references to CLI commands are updated to reflect the armos command names

**Size:** S
**Dependencies:** 1.2

---

## Epic 2: Hardware Abstraction Layer -- Feetech

**Goal:** Implement the servo protocol abstraction and the Feetech STS3215 driver, including bus scanning, protection settings, retry logic, and a conformance test suite for plugin authors.

**Migration Phase:** B
**Product Scope:** MVP (v0.1)

### Story 2.1: ServoProtocol ABC and FeetechPlugin

As a **developer**,
I want a `ServoProtocol` ABC with fewer than 12 abstract methods and a `FeetechPlugin` implementation wrapping LeRobot's `FeetechMotorsBus`,
So that the HAL provides a clean interface and the Feetech driver is testable against the contract.

**Acceptance Criteria:**

**Given** the `ServoProtocol` ABC is defined
**When** I inspect it
**Then** it has 12 or fewer abstract methods including: connect, disconnect, ping, scan_bus, sync_read_positions, sync_write_positions, get_telemetry, read_register, write_register, enable_torque, disable_torque, flush_port

**Given** the `FeetechPlugin` is instantiated
**When** I call `connect(port="/dev/ttyUSB0", baudrate=1000000)`
**Then** it connects to the Feetech servo bus via LeRobot's `FeetechMotorsBus`

**Given** the `FeetechPlugin` passes an integration test
**When** the test exercises the exact call sequence from `teleop_monitor.py`
**Then** all calls succeed on real hardware

**Size:** L
**Dependencies:** 1.1, 1.3

---

### Story 2.2: Servo Bus Scan

As a **user**,
I want the system to scan a servo bus and report all connected servos with their IDs, model numbers, and firmware versions,
So that I can verify my hardware is connected and identify any missing or misconfigured servos.

**Acceptance Criteria:**

**Given** a Feetech bus with servos at IDs [1, 2, 3, 4, 5, 6]
**When** I call `protocol.scan_bus(range(1, 13))`
**Then** 6 ServoInfo objects are returned with servo_id, model, and firmware_version fields

**Given** a `MockServoProtocol` configured with servos at IDs [1, 2, 3, 6]
**When** `scan_bus(range(1, 13))` is called
**Then** 4 ServoInfo objects are returned

**Size:** M
**Dependencies:** 2.1

---

### Story 2.3: Protection Settings Read/Write

As a **user**,
I want the system to read and write servo protection settings (overload torque, protection current, protection time) from the robot profile,
So that my servos are protected against damage.

**Acceptance Criteria:**

**Given** the SO-101 profile specifies `overload_torque=90` for body joints
**When** I call `protocol.write_register(servo_id=1, address=OVERLOAD_TORQUE, value=90)`
**Then** the servo's EEPROM is updated and `read_register` confirms the value

**Size:** M
**Dependencies:** 2.1

---

### Story 2.4: Resilient Communication with Retry and Port Flush

As a **developer**,
I want the FeetechPlugin to retry failed reads/writes with port flushing,
So that transient serial errors do not crash teleoperation sessions.

**Acceptance Criteria:**

**Given** the FeetechPlugin is performing a sync_read
**When** the first attempt fails with a communication error
**Then** the plugin flushes the serial port buffer, waits 1ms, and retries
**And** up to 10 retries are attempted before raising an error (configurable)

**Given** a transient failure occurs during a teleoperation session
**When** retry succeeds within the retry budget
**Then** teleoperation continues without interruption
**And** a warning is logged with the retry count

**Size:** M
**Dependencies:** 2.1

---

### Story 2.5: ServoProtocol Conformance Test Suite

As a **plugin developer**,
I want a pytest base class (`ServoProtocolConformanceTests`) that validates any `ServoProtocol` implementation against the ABC contract,
So that I can verify my plugin is correct without writing test boilerplate.

**Acceptance Criteria:**

**Given** a class subclasses `ServoProtocolConformanceTests` and provides a protocol fixture
**When** `pytest` runs
**Then** the conformance suite validates: connect/disconnect lifecycle, ping, scan_bus, sync_read/write round-trip, get_telemetry range validation, retry behavior, flush_port

**Given** the `MockServoProtocol` from Story 0.1
**When** the conformance tests run against it
**Then** all tests pass

**Size:** M
**Dependencies:** 2.1, 0.1
**Implements:** FR54

---

## Epic 3: Robot Profile System -- SO-101

**Goal:** Implement the YAML-based robot profile system with Pydantic validation, a profile loader, and the first built-in profile for the SO-101 robot. Profiles are the single source of truth for all hardware configuration.

**Migration Phase:** B
**Product Scope:** MVP (v0.1)

### Story 3.1: Profile Schema and Loader

As a **developer**,
I want Pydantic models defining the robot profile schema (arms, joints, servo IDs, protection settings, calibration config, LeRobot integration) and a loader that reads YAML files into validated objects,
So that malformed profiles are caught at load time with clear error messages.

**Acceptance Criteria:**

**Given** a valid SO-101 YAML profile file
**When** I call `ProfileLoader.load("so101.yaml")`
**Then** I receive a validated `RobotProfile` object with `arms`, `hardware`, `power`, `calibration`, and `lerobot` sections
**And** all fields are typed and accessible as Python attributes

**Given** a YAML profile with a missing required field (e.g., no `arms` section)
**When** I attempt to load it
**Then** a `ProfileValidationError` is raised with a message identifying the missing field

**Given** a YAML profile with `overload_torque: 2000` (exceeds safe maximum for STS3215)
**When** I attempt to load it
**Then** validation rejects with warning: "overload_torque exceeds safe maximum for STS3215"

**Size:** M
**Dependencies:** 1.1, 1.4

---

### Story 3.2: Built-in SO-101 Profile

As a **user**,
I want the system to ship with a pre-built SO-101 profile that describes the 2x 6-DOF leader-follower arm configuration with Feetech STS3215 servos,
So that I can use my SO-101 without creating any configuration files.

**Acceptance Criteria:**

**Given** the `armos` package is installed
**When** I call `ProfileLoader.list_profiles()`
**Then** "SO-101" appears in the list with description "HuggingFace SO-101 6-DOF robot arm (leader/follower pair)"

**Given** the SO-101 profile is loaded
**When** I inspect its structure
**Then** it defines 2 arms (leader + follower), each with 6 joints (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper)
**And** servo IDs are 1-6 for each arm
**And** protection settings match the tuned values from the existing deployment (overload_torque=90, protective_torque=50, protection_time=254 for body joints; overload_torque=25 for gripper)
**And** the LeRobot section specifies robot_type="so100" and fps=60

**Given** the SO-101 profile is loaded
**When** I inspect the bundled profiles
**Then** a demo calibration profile ("SO-101 Demo") is also available with pre-baked calibration data for demo mode

**Size:** S
**Dependencies:** 3.1

---

### Story 3.3: Calibration Storage and Recall

As a **user**,
I want my arm calibration data to be saved to disk and automatically recalled on subsequent sessions,
So that I do not have to recalibrate every time I reboot.

**Acceptance Criteria:**

**Given** a calibration procedure has been completed for the follower arm
**When** the calibration data is saved
**Then** a JSON file is written to `~/.config/armos/calibration/{instance_id}/follower.json`
**And** the file contains per-joint min/max register values and homing offsets

**Given** the system starts and detects the same servo controller (matched by USB serial number)
**When** the profile is loaded
**Then** the stored calibration is automatically loaded from disk
**And** the system reports "Calibration loaded for follower arm (saved: 2026-03-15)"

**Size:** M
**Dependencies:** 3.1, 2.1

---

### Story 3.4: Calibration Validation

As a **user**,
I want the system to warn me if my stored calibration appears stale or invalid (servo positions far outside calibrated range),
So that I know to recalibrate after replacing a servo or reassembling my arm.

**Acceptance Criteria:**

**Given** a stored calibration exists for the follower arm
**When** the current servo positions are read and compared to the calibrated range
**Then** if any joint's current position is more than 20% outside its calibrated range, a warning is displayed: "shoulder_pan position (3800) is outside calibrated range (1200-3200). Recalibration recommended."

**Given** the calibration file is older than 30 days
**When** the system loads the calibration
**Then** an informational message is displayed: "Calibration is 35 days old. Consider recalibrating if servos have been replaced."

**Size:** S
**Dependencies:** 3.3

> **Scope note:** FR14 is listed as Growth scope in the PRD Requirements Inventory, but is pulled into MVP Sprint 3 here. Rationale: calibration validation is a natural extension of Story 3.3 (calibration persistence) and is low-effort (S-sized). Shipping it in MVP improves the first-time user experience by catching stale calibrations early, directly supporting UJ1 (first-time boot). The PRD MVP FR list has been updated to reflect this.

---

### Story 3.5: Camera Auto-Detection and CameraManager Integration

As a **user**,
I want the system to auto-detect USB cameras via V4L2 and provide a CameraManager for opening and managing camera streams,
So that cameras are available for data collection and monitoring without manual configuration.

**Acceptance Criteria:**

**Given** one or more USB cameras are connected
**When** I run `armos detect`
**Then** the output includes each camera's device path, supported resolutions, and frame rates

**Given** a detected camera device path
**When** `CameraManager.open(device_path)` is called
**Then** it returns an OpenCV `VideoCapture` object ready for frame capture

**Given** no cameras are connected
**When** the CameraManager enumerates devices
**Then** it returns an empty list without error

**Size:** M
**Dependencies:** 1.3
**Sprint:** 3
**Implements:** FR4

---

## Epic 4: Diagnostic Framework Refactor

**Goal:** Decompose the monolithic `diagnose_arms.py` (11 phases) into a modular diagnostic framework with individual check classes, a runner, and pluggable output reporters. Each check becomes independently runnable and testable.

**Migration Phase:** C
**Product Scope:** MVP (v0.1)

### Story 4.1: DiagnosticRunner and HealthCheck Interface

As a **developer**,
I want a `DiagnosticRunner` that discovers and executes `HealthCheck` classes, collecting `CheckResult` objects (PASS/WARN/FAIL with messages and data),
So that diagnostics are composable, extensible, and independently testable.

**Acceptance Criteria:**

**Given** the `HealthCheck` ABC defines `name`, `description`, and `run(protocol, profile) -> list[CheckResult]`
**When** I implement a new check class and register it
**Then** `DiagnosticRunner.run_all()` discovers and runs it alongside all other checks

**Given** a check returns `FAIL`
**When** the runner processes results
**Then** the runner continues executing remaining checks (does not abort)
**And** the final report includes all results, ordered by severity (FAIL first, then WARN, then PASS)

**Given** I run `armos diagnose --protocol dynamixel`
**When** a non-default protocol is specified
**Then** the diagnostic suite runs through the specified protocol plugin

**Size:** M
**Dependencies:** 2.1, 3.1

---

### Story 4.2a: Migrate Read-Only Diagnostic Checks

As a **user**,
I want the read-only diagnostic phases from `diagnose_arms.py` (ping, firmware, voltage, temp, status, config, calibration) available as individual health checks,
So that I can quickly verify my hardware is connected and healthy without moving any servos.

**Acceptance Criteria:**

**Given** the following checks are implemented: PortDetection, ServoPing, FirmwareVersion, PowerHealth, StatusRegister, EEPROMConfig, CalibrationValid
**When** I run `armos diagnose`
**Then** all 7 read-only checks execute in sequence and produce a summary report
**And** each check uses the `ServoProtocol` and `RobotProfile` interfaces (not hardcoded Feetech calls)

**Given** I want to check only power health
**When** I run `armos diagnose --check power`
**Then** only the PowerHealth check executes

**Size:** L
**Dependencies:** 4.1, 2.1, 2.2, 2.3, 3.1, 3.3

---

### Story 4.2b: Migrate Active Diagnostic Checks

As a **user**,
I want the active diagnostic phases from `diagnose_arms.py` (comms reliability, torque stress, cross-bus teleop, motor isolation) available as individual health checks,
So that I can run stress tests and advanced diagnostics that require servo motion.

**Acceptance Criteria:**

**Given** the following checks are implemented: CommsReliability, TorqueStress, CrossBusTeleop, MotorIsolation
**When** I run `armos diagnose --active`
**Then** all 4 active checks execute in sequence and produce a summary report
**And** each check uses the `ServoProtocol` and `RobotProfile` interfaces (not hardcoded Feetech calls)

**Given** I want to check only servo communication reliability
**When** I run `armos diagnose --check comms`
**Then** only the CommsReliability check executes

**Size:** L
**Dependencies:** 4.1, 2.1, 2.2, 2.3, 3.1, 3.3, 4.2a

---

### Story 4.3: Diagnostic Output Reporters

As a **user**,
I want diagnostic results available in multiple formats: colored terminal output, JSON (for AI consumption), and CSV (for logging),
So that I can read results in the terminal, feed them to Claude Code, or analyze them in a spreadsheet.

**Acceptance Criteria:**

**Given** a diagnostic run has completed
**When** I run `armos diagnose` (default)
**Then** results are printed to the terminal with colored PASS/WARN/FAIL indicators using Rich

**Given** a diagnostic run has completed
**When** I run `armos diagnose --json`
**Then** results are printed as valid JSON with `status`, `message`, and `data` fields per check

**Given** a diagnostic run has completed
**When** I run `armos diagnose --log /path/to/output.csv`
**Then** results are appended to a CSV file with timestamp, check name, status, and message columns

**Size:** M
**Dependencies:** 4.1

---

### Story 4.4: Exercise Command Migration

As a **user**,
I want to run programmatic arm exercise routines via `armos exercise`,
So that I can verify mechanical health by moving each joint through its range.

**Acceptance Criteria:**

**Given** a calibrated SO-101 is connected
**When** I run `armos exercise --arm follower`
**Then** each joint moves through its calibrated range (min to max to center) at a safe speed
**And** per-joint telemetry (voltage, load, temperature) is displayed during the exercise

**Given** I want to exercise only one joint
**When** I run `armos exercise --arm follower --joint elbow_flex`
**Then** only the elbow_flex joint is exercised

**Size:** M
**Dependencies:** 2.1, 3.1, 3.3

---

## Epic 5: Telemetry and Monitoring Library

**Goal:** Extract the real-time telemetry streaming from `monitor_arm.py` into a reusable library with pluggable backends (console, CSV, WebSocket). This library is consumed by the CLI, TUI, and future web dashboard.

**Migration Phase:** C
**Product Scope:** MVP (v0.1)

### Story 5.1: TelemetryStream with Pluggable Backends

As a **developer**,
I want a `TelemetryStream` class that polls servo telemetry at a configurable rate and publishes samples to registered backends,
So that any UI layer can subscribe to live hardware data without implementing its own polling loop.

**Acceptance Criteria:**

**Given** a `TelemetryStream` is initialized with a connected `ServoProtocol` and loaded `RobotProfile`
**When** I call `stream.start(hz=10)`
**Then** the stream polls all servos defined in the profile 10 times per second
**And** each sample includes: position, velocity, load, voltage, temperature, error_flags per servo

**Given** a `ConsoleBackend` is registered
**When** telemetry samples arrive
**Then** the backend renders a colored terminal table (matching the existing `monitor_arm.py` output) updating in place

**Given** I call `stream.stop()`
**When** the stream is running
**Then** polling stops cleanly and all backends are flushed

**Size:** L
**Dependencies:** 2.1, 3.1

---

### Story 5.2: CSV Logging Backend

As a **user**,
I want telemetry data automatically logged to CSV files with timestamps,
So that I can analyze servo behavior after a session for troubleshooting or research.

**Acceptance Criteria:**

**Given** a `CSVBackend` is registered with an output path
**When** telemetry samples arrive
**Then** each sample is written as a row: timestamp, arm, joint, position, voltage, current, load, temperature, error_flags
**And** the CSV is flushed after each row (no data loss on crash)

**Given** I run `armos monitor --log /tmp/telemetry.csv`
**When** I monitor for 10 seconds at 10 Hz and then stop
**Then** the CSV file contains approximately 10 * 10 * num_joints rows (one per sample per joint)

**Size:** S
**Dependencies:** 5.1

---

### Story 5.3: Fault Detection and Alert System

As a **user**,
I want the system to detect and report specific fault conditions in real time (voltage sag, overload trip, temperature warning, communication timeout, bus disconnection),
So that I receive actionable warnings before hardware damage occurs.

**Acceptance Criteria:**

**Given** the telemetry stream is running
**When** a servo's voltage drops below the profile's minimum threshold (e.g., 7.0V)
**Then** an alert is generated within 2 seconds: "WARN: follower/elbow_flex voltage 6.8V (threshold 7.0V). Check power supply -- STS3215 requires 7.4V 3A minimum."

**Given** a servo's temperature exceeds the profile's warning threshold
**When** the telemetry sample is processed
**Then** an alert is generated: "WARN: follower/shoulder_lift temperature 55C (threshold 50C). Consider reducing duty cycle."

**Given** the servo bus is physically disconnected
**When** all reads fail for more than 2 seconds
**Then** an alert is generated: "FAIL: follower arm bus disconnected. Check USB cable."
**And** the system continues monitoring without crashing (NFR7)

**Size:** M
**Dependencies:** 5.1, 3.1

---

## Epic 6: Calibration and Teleop CLI

**Goal:** Implement the calibration workflow and leader-follower teleoperation as CLI commands that work through the HAL. These are the primary user-facing commands for operating the robot.

**Migration Phase:** D
**Product Scope:** MVP (v0.1)

### Story 6.1: Interactive Calibration Command

As a **user**,
I want to calibrate my robot arms through a guided procedure that tells me which joint to move and records the servo positions,
So that my robot's movements are accurately mapped.

**Acceptance Criteria:**

**Given** an SO-101 is connected and the profile is loaded
**When** I run `armos calibrate --arm follower`
**Then** the system guides me through each joint: "Move shoulder_pan to its minimum position and press Enter"
**And** after recording min/max for all joints, calibration data is saved to disk

**Given** calibration is in progress
**When** I press Ctrl+C
**Then** the partially completed calibration is discarded with a message "Calibration cancelled. No data saved."

**Given** a stored calibration already exists for this arm
**When** I run `armos calibrate --arm follower`
**Then** the system warns "Existing calibration found (saved: 2026-03-15). Overwrite? [y/N]"

**Size:** M
**Dependencies:** 2.1, 3.1, 3.3

---

### Story 6.2: Leader-Follower Teleoperation Command

As a **user**,
I want to launch leader-follower teleoperation from the CLI where moving the leader arm causes the follower arm to mirror the movements,
So that I can control my robot arm in real time.

**Acceptance Criteria:**

**Given** both leader and follower arms are connected, profiled, and calibrated
**When** I run `armos teleop`
**Then** the system reads leader arm positions and writes them to the follower arm at 60 Hz (per SO-101 profile)
**And** the system displays live telemetry (position, voltage, load) for both arms

**Given** teleoperation is running
**When** a servo exceeds its protection threshold (e.g., temperature > max)
**Then** teleoperation halts immediately with "SAFETY STOP: follower/elbow_flex temperature 65C exceeds limit 60C"
**And** all follower servo torques are disabled

**Given** teleoperation is running
**When** the control loop stalls for more than 500ms (e.g., USB controller hang)
**Then** the teleop watchdog fires and disables all follower torques immediately
**And** the user is alerted: "WATCHDOG: control loop stalled >500ms, torque disabled for safety"

**Given** teleoperation is running
**When** I press Ctrl+C
**Then** teleoperation stops gracefully, follower torques are disabled, and a session summary is printed (duration, max temps, max loads, error count)

**Size:** L
**Dependencies:** 2.1, 2.4, 3.1, 3.3, 5.1, 5.3
**Implements:** FR15, FR17, FR42

> **Concurrency note:** Start with the single-threaded interleaved model from `teleop_monitor.py` (teleop at 60Hz, telemetry sampling at 2Hz inline). Multi-threaded telemetry is deferred until performance profiling demonstrates a need.

---

### Story 6.3: Teleop Monitor Overlay

As a **user**,
I want to see live per-servo telemetry during teleoperation (voltage, current, load, temperature, error count),
So that I can detect developing problems before they cause a safety stop.

**Acceptance Criteria:**

**Given** teleoperation is running
**When** I look at the terminal output
**Then** I see a continuously updating status display showing per-joint: name, position, voltage, load%, temperature, and communication error count
**And** values exceeding warning thresholds are highlighted in yellow; values exceeding error thresholds are highlighted in red

**Size:** M
**Dependencies:** 6.2, 5.1

---

### Story 6.4: Hardware Detection Command

As a **user**,
I want to run `armos detect` to see all connected USB-serial adapters and cameras with their identified types,
So that I can verify my hardware is recognized before starting calibration or teleop.

**Acceptance Criteria:**

**Given** a CH340 USB-serial adapter is connected
**When** I run `armos detect`
**Then** I see: "USB Serial: /dev/ttyUSB0 (CH340, vendor=1a86, product=7523) -- Feetech servo controller"

**Given** a USB camera is connected
**When** I run `armos detect`
**Then** I see: "Camera: /dev/video0 (USB 2.0 Camera, 1920x1080@30fps, 640x480@60fps)"

**Given** no USB devices are connected
**When** I run `armos detect`
**Then** I see: "No USB serial devices or cameras detected."

**Size:** M
**Dependencies:** 2.1, 1.3

---

## Epic 7: TUI Launcher

**Goal:** Build a terminal user interface (TUI) using `textual` that provides a dashboard for robot status, hardware telemetry, launching all primary workflows without typing commands, and a demo mode for trade shows. This is the "zero terminal commands" experience for MVP.

**Migration Phase:** D
**Product Scope:** MVP (v0.1)

### Story 7.0: First-Run Setup Wizard with Hardware Auto-Detection

As a **first-time user**,
I want a setup wizard that auto-detects my connected hardware and guides me through initial calibration on first boot,
So that I can go from "USB plugged in" to "robot working" without reading documentation or typing terminal commands.

**Acceptance Criteria:**

**Given** the system has never been configured (no calibration files, no profile selection)
**When** the TUI launches for the first time
**Then** a first-run wizard starts automatically

**Given** the wizard is running
**When** hardware is detected (USB-serial adapters, servo buses, cameras)
**Then** the wizard displays what was found and auto-selects the matching robot profile

**Given** the wizard has identified the hardware
**When** the user confirms the detected configuration
**Then** the wizard launches the calibration workflow for each arm in sequence
**And** on completion, the user is dropped into the main TUI dashboard ready for teleop

**Given** the system has already been configured (calibration files exist)
**When** the TUI launches
**Then** the wizard is skipped and the main dashboard appears directly

**Given** the first-run wizard is running
**When** the telemetry opt-in step is reached
**Then** the wizard asks "Share anonymous usage data to help improve armOS? [y/N]" and stores the preference in `~/.config/armos/settings.yaml`

**Size:** L
**Dependencies:** 7.1, 6.1, 6.4
**Sprint:** 6a
**Implements:** FR43

---

### Story 7.1: TUI Application Shell

As a **user**,
I want to launch `armos tui` and see a terminal dashboard showing detected hardware, active profile, and calibration state,
So that I have a visual overview of my robot setup without memorizing CLI commands.

**Acceptance Criteria:**

**Given** the `armos` package is installed with the `tui` extra
**When** I run `armos tui`
**Then** a full-screen terminal application launches using `textual`
**And** the header shows "armOS v0.1.0" and the detected robot profile name
**And** a status panel shows: connected arms, calibration state per arm, and any active faults

**Given** no robot hardware is detected
**When** the TUI launches
**Then** the status panel shows "No hardware detected. Connect a servo controller and press R to refresh."

**Size:** M
**Dependencies:** 6.4, 3.1

---

### Story 7.2: Live Telemetry Panel

As a **user**,
I want to see live servo telemetry in the TUI dashboard (voltage, load, temperature per joint) updating in real time,
So that I can monitor my robot's health at a glance.

**Acceptance Criteria:**

**Given** the TUI is running and a robot is connected
**When** I navigate to the telemetry view (press M for Monitor)
**Then** I see a table with one row per joint showing: name, position, voltage, current, load%, temperature, status
**And** the table updates at 10 Hz (NFR4)
**And** out-of-range values are highlighted with color (yellow = warning, red = critical)

**Size:** M
**Dependencies:** 7.1, 5.1

---

### Story 7.3: Workflow Launcher Panel

As a **user**,
I want to launch calibration, teleoperation, diagnostics, and monitoring from the TUI using keyboard shortcuts,
So that I never need to open a terminal and type commands.

**Acceptance Criteria:**

**Given** the TUI is running
**When** I press D (Diagnose)
**Then** the diagnostic suite runs and results are displayed in the TUI
**And** I can scroll through results and see PASS/WARN/FAIL with details

**Given** the TUI is running
**When** I press T (Teleop)
**Then** leader-follower teleoperation starts with the telemetry overlay visible in the TUI

**Given** the TUI is running
**When** I press C (Calibrate)
**Then** the interactive calibration workflow runs within the TUI

**Given** the TUI is running and a workflow is active
**When** I press Q or Escape
**Then** the workflow stops gracefully and I return to the main dashboard

> **Implementation note:** Workflow commands (teleop, calibrate, exercise) should be launched as subprocess calls or take over the terminal, not embedded in the textual event loop. The TUI resumes when the subprocess exits.

**Size:** L
**Dependencies:** 7.1, 7.2, 6.1, 6.2, 4.2a

---

### Story 7.4: Demo Mode (Kiosk)

As a **person demonstrating armOS at a booth or in a video**,
I want a single-command demo mode that boots into a locked-down, self-recovering teleop session,
So that the demo cannot be interrupted by accidental keypresses, crashes, or configuration issues.

**Acceptance Criteria:**

**Given** a configured SO-101 is connected
**When** I run `armos demo`
**Then** a full-screen TUI launches with: large "armOS" header, live camera feed (if available), leader-follower teleop, and a telemetry panel

**Given** demo mode is running
**When** the servo bus disconnects
**Then** demo mode displays a reconnection message and auto-reconnects (up to 30 seconds), then resumes teleop

**Given** demo mode is running
**When** any unhandled exception occurs
**Then** demo mode restarts itself within 3 seconds

**Given** demo mode is running
**When** a key other than Escape is pressed
**Then** the keypress is ignored (all keyboard shortcuts disabled except Escape)

**Given** demo mode is running
**When** Escape is held for 3 seconds
**Then** demo mode exits

**Given** the ISO includes a GRUB boot option "armOS Demo Mode"
**When** the user selects it at boot
**Then** the system boots directly into demo mode without login

**Given** demo mode starts
**When** hardware is detected
**Then** teleop auto-starts using the demo calibration profile (from Story 3.2) with no user interaction required

**Size:** M
**Dependencies:** 6.2, 7.1, 3.2
**Sprint:** 6a
**Implements:** FR45

> **Business driver:** The business plan identifies the live demo as the single most important marketing asset. A 90-second flawless demo at Maker Faire or in a YouTube video is critical for launch. This story is scheduled in Sprint 6a to allow testing and polish before the launch sprint.

---

## Epic 8: Pre-built USB Image

**Goal:** Create a bootable USB image using `live-build` that ships with the entire `armos` package, LeRobot, all system dependencies, and the SO-101 profile pre-installed. Includes CI/CD for reproducible builds, smoke testing, and a distribution pipeline. Users flash and boot -- no install process.

**Migration Phase:** E
**Product Scope:** MVP (v0.1)

### Story 8.1a: Live-Build Spike -- Minimal Bootable ISO

As a **developer**,
I want a minimal `live-build` configuration that produces a bootable Ubuntu 24.04-based ISO with Python 3.12 and a "hello world" armos package,
So that we validate the live-build toolchain early and de-risk the full ISO build.

**Acceptance Criteria:**

**Given** the `armos-iso/` directory contains a minimal `live-build` configuration
**When** I run the build script (e.g., `./build-iso.sh`)
**Then** a bootable ISO is produced
**And** the ISO boots to a desktop on a x86 UEFI system (or QEMU/KVM)
**And** `python3.12 --version` works inside the booted image

**Size:** M
**Dependencies:** 1.1
**Sprint:** 4a

---

### Story 8.1b: Full Live-Build with All Packages

As a **developer**,
I want the full `live-build` configuration that produces a bootable Ubuntu 24.04-based ISO with all armOS dependencies pre-installed,
So that the ISO can be built reproducibly in CI or locally.

**Acceptance Criteria:**

**Given** the `armos-iso/` directory contains the full `live-build` configuration
**When** I run the build script (e.g., `./build-iso.sh`)
**Then** a `armos-0.1.0.iso` file is produced
**And** the ISO boots to a desktop on a x86 UEFI system within 90 seconds (NFR5)
**And** the ISO is under 16GB (NFR14)

**Given** the ISO has booted
**When** I open a terminal and run `armos --version`
**Then** it prints `0.1.0`
**And** `python3.12 -c "import lerobot; print(lerobot.__version__)"` prints `0.5.0`
**And** the SO-101 profile is available via `armos profile list`

**Size:** L
**Dependencies:** 1.1, 2.1, 3.2, 4.2a, 5.1, 6.1, 6.2, 7.1, 8.1a

---

### Story 8.2: System Configuration Baked Into Image

As a **user**,
I want the USB image to have all udev rules, brltty removal, dialout group membership, and persistent storage configured out of the box,
So that I never need to run system configuration commands.

**Acceptance Criteria:**

**Given** the ISO has booted on fresh hardware
**When** I plug in a CH340 USB-serial adapter
**Then** the device appears as `/dev/ttyUSB0` with mode 0666 (no root required)
**And** `brltty` is not installed (cannot steal the serial port)
**And** the default user is in the `dialout` group

**Given** the ISO is running from a USB drive
**When** I save calibration data or a dataset
**Then** the data persists across reboots (persistent partition or overlay filesystem)
**And** the filesystem survives unexpected power loss (NFR9)

**Size:** L
**Dependencies:** 8.1b

---

### Story 8.3: Windows Flash Script Update

As a **user**,
I want to flash the armOS USB image from Windows using a single PowerShell command,
So that I can prepare a bootable USB without needing Linux tools.

**Acceptance Criteria:**

**Given** I have downloaded `armos-0.1.0.iso` on a Windows machine
**When** I run `flash.ps1 -Image armos-0.1.0.iso -Drive E:`
**Then** the script writes the ISO to the USB drive
**And** the USB drive is bootable on x86 UEFI hardware

**Given** the script detects the target drive has data
**When** the script starts
**Then** it prompts for confirmation before overwriting

**Size:** M
**Dependencies:** 8.1b

---

### Story 8.4: Hardware Compatibility Testing

As a **user**,
I want the USB image validated on at least 5 distinct x86 hardware models,
So that I have confidence it will boot on my machine.

**Acceptance Criteria:**

**Given** the ISO has been built
**When** it is tested on 5+ hardware models (e.g., Surface Pro 7, Dell XPS 13, Lenovo ThinkPad, HP EliteBook, a desktop with AMD CPU)
**Then** boot success/failure and any hardware-specific issues are documented in a compatibility matrix
**And** at least 4 of 5 models boot successfully to the TUI

**Size:** L
**Dependencies:** 8.1b, 8.2

---

### Story 8.5: Plymouth Boot Splash

As a **user**,
I want a branded Plymouth boot splash that hides Linux boot messages during startup,
So that the boot experience looks polished and professional rather than showing a wall of systemd text.

**Acceptance Criteria:**

**Given** the ISO image includes a custom Plymouth theme
**When** the system boots from USB
**Then** a branded armOS splash screen is displayed instead of Linux boot messages
**And** a progress indicator shows boot is progressing

**Size:** S
**Dependencies:** 8.1b

---

### Story 8.6: Dockerfile.build for Reproducible ISO Builds

As a **developer**,
I want a Dockerfile that produces identical ISO images regardless of the build machine,
So that ISO builds are reproducible in CI and locally.

**Acceptance Criteria:**

**Given** the `Dockerfile.build` exists
**When** I run `docker build -f Dockerfile.build -t armos-builder .`
**Then** the image builds successfully with all live-build dependencies pinned

**Given** the builder container runs
**When** I execute `docker run --privileged -v $PWD/output:/output armos-builder`
**Then** a valid ISO is produced in the `output/` directory

**Size:** M
**Dependencies:** 8.1b
**Implements:** FR52

---

### Story 8.7: QEMU ISO Smoke Test

As a **developer**,
I want an automated smoke test that boots the ISO in QEMU and validates basic functionality,
So that broken ISOs are caught in CI before release.

**Acceptance Criteria:**

**Given** `tests/iso/test-iso.sh` exists
**When** I run it against a built ISO
**Then** it boots the ISO in QEMU with OVMF (UEFI firmware)
**And** validates: login prompt within 90s, `armos --version` returns expected version, `armos profile list` includes SO-101, no kernel panics in dmesg

**Given** the ISO has a critical issue (fails to boot, missing armos package)
**When** the smoke test runs
**Then** the test exits with a non-zero code and a clear error message

**Size:** M
**Dependencies:** 8.1b
**Implements:** FR53

---

### Story 8.8: ISO Distribution Pipeline

As a **developer**,
I want `make release` to build the ISO, compute SHA256, upload to HuggingFace Hub, and generate a BitTorrent file,
So that users can download verified ISOs from a reliable CDN.

**Acceptance Criteria:**

**Given** a version tag has been pushed
**When** the GitHub Actions workflow runs
**Then** the ISO is built via Docker, smoke-tested via QEMU, and uploaded to HuggingFace Hub as a tagged release
**And** a SHA256 checksum is published alongside the download

**Given** a fresh machine with a 50Mbps connection
**When** the user downloads the ISO from HuggingFace Hub
**Then** the download completes and verifies in under 10 minutes

**Size:** M
**Dependencies:** 8.6, 8.7
**Implements:** FR50

> **Distribution channels:** Primary: HuggingFace Hub (`armos/armos-usb` repo). Fallback: Cloudflare R2. Community: BitTorrent seeded after each release.

---

### Story 8.9: ISO Version Metadata

As a **developer**,
I want the ISO build to write `/etc/armos-release` with version, build date, git hash, and armos package version,
So that `armos --version` can display complete build information.

**Acceptance Criteria:**

**Given** the ISO has been built
**When** I boot it and run `armos --version`
**Then** it displays: package version, ISO version (with date suffix), and git hash

**Given** `/etc/armos-release` exists in the ISO
**When** I inspect it
**Then** it contains: `version`, `build_date`, `git_hash`, `armos_version` fields

**Size:** S
**Dependencies:** 8.1b
**Implements:** FR51

---

## Epic 9: AI Integration and Data Collection

**Goal:** Integrate the LeRobot data collection pipeline into the `armos` package and set up the Claude Code context for AI-assisted troubleshooting. Users can record teleop sessions as datasets and get AI help when things go wrong.

**Migration Phase:** E
**Product Scope:** MVP (v0.1)

### Story 9.1: Claude Code Context Pre-seeding

As a **user**,
I want the USB image to include pre-seeded Claude Code context files (CLAUDE.md, memory files) that enable Claude to understand my robot setup and diagnose issues,
So that I can get AI-assisted troubleshooting without manual context setup.

**Acceptance Criteria:**

**Given** the USB image has booted
**When** I launch Claude Code in the armOS project directory
**Then** CLAUDE.md is present and describes all `armos` CLI commands
**And** memory files document known hardware issues (Feetech sync_read bug, brltty hijack, power supply requirements)
**And** `armos diagnose --json` output can be pasted to Claude for interpretation

**Size:** S
**Dependencies:** 1.5, 8.1b

---

### Story 9.2: LeRobot Bridge -- Profile to Config Translation

As a **user**,
I want the system to automatically translate my robot profile into LeRobot configuration objects,
So that I can record datasets without writing LeRobot config files manually.

**Acceptance Criteria:**

**Given** an SO-101 profile is loaded with calibration data
**When** I call `LeRobotBridge.build_config(profile, calibration)`
**Then** a valid LeRobot robot configuration object is returned
**And** it maps joint names to the correct servo IDs and port paths
**And** the fps and monitor_hz values come from the profile's `lerobot` section

**Given** cameras are detected via V4L2
**When** the bridge builds the config
**Then** detected cameras are mapped to observation keys in the LeRobot config

**Given** the bridge produces a config
**When** it is passed to LeRobot's `record()` function
**Then** it successfully records an episode to disk (validated with a 5-second recording session)

**Size:** M
**Dependencies:** 3.1, 3.3, 2.1

---

### Story 9.3: Data Collection Command

As a **user**,
I want to record teleoperation sessions as LeRobot-compatible datasets via `armos record`,
So that I can collect training data for imitation learning.

**Acceptance Criteria:**

**Given** both arms are connected, calibrated, and cameras are detected
**When** I run `armos record --task pick_and_place --episodes 10`
**Then** the system starts teleoperation and records servo positions + camera frames + timestamps
**And** after each episode (user presses Enter to advance), the episode is saved to disk immediately (NFR8)

**Given** 10 episodes have been recorded
**When** the session completes
**Then** the dataset is saved in LeRobot format at `~/.local/share/armos/datasets/pick_and_place/`
**And** `armos record --list` shows the dataset with episode count and disk size

**Given** a recording is in progress
**When** the system encounters a transient servo error
**Then** the current episode is marked with a warning flag but recording continues

**Given** the user runs `armos upload`
**When** cloud training is not yet available
**Then** the command prints "Cloud training coming soon. Your dataset is saved at /path." (placeholder for Growth phase)

**Size:** L
**Dependencies:** 9.2, 6.2, 5.1

---

## Epic 10: Growth Phase -- Multi-Hardware and Polish

**Goal:** Extend armOS beyond the SO-101 to support multiple robot platforms, servo protocols, and host hardware. Add the user-facing polish features (profile creation wizard, configurable teleop, episode review, image cloning, web dashboard foundations). This epic covers Growth (v0.5) and Vision (v1.0) scope items.

**Migration Phase:** F
**Product Scope:** Growth (v0.5) / Vision (v1.0)

### Story 10.1: DeviceManager -- pyudev Hotplug and Profile Matching

As a **user**,
I want the system to automatically detect USB devices when plugged in and match them to the best robot profile,
So that I do not need to manually configure ports or select profiles.

**Size:** L
**Dependencies:** 2.1, 3.1, 6.4

---

### Story 10.2: Plugin Architecture for Servo Protocols

As a **developer**,
I want to add support for new servo protocols by implementing the `ServoProtocol` interface and registering via Python entry points,
So that the community can contribute hardware support without modifying core code.

**Size:** L
**Dependencies:** 2.1

---

### Story 10.3: Profile Creation Wizard and Export/Import

As a **user**,
I want to create a new robot profile through a guided workflow and export it for sharing,
So that I can use armOS with custom hardware and share my configuration with others.

**Size:** L
**Dependencies:** 3.1, 3.2

---

### Story 10.4: Configurable Teleop, Episode Review, and Camera Feeds

As a **user**,
I want to configure teleoperation parameters (speed scaling, deadband), review recorded episodes, and see live camera feeds,
So that I have full control over my data collection workflow.

**Size:** L
**Dependencies:** 6.2, 9.3, 6.4

---

### Story 10.5: USB Image Cloning for Fleet Deployment

As an **educator**,
I want to clone a configured USB image (with my profiles and calibrations) to multiple USB sticks,
So that I can set up a classroom of identical robot stations quickly.

**Size:** M
**Dependencies:** 8.1b, 8.2

---

### Story 10.6: AI Troubleshooting with Live System State

As a **user**,
I want to launch an AI troubleshooting session that automatically provides Claude Code with my current system state (detected hardware, recent errors, servo telemetry),
So that I get context-aware diagnostic assistance without manually copying data.

**Size:** M
**Dependencies:** 9.1, 4.3, 5.3

---

## Epic 11: Business Enablement

**Goal:** Implement business-critical features that drive revenue, community growth, and the data flywheel: anonymous telemetry for product analytics, cloud training upload hooks, community profile sharing, fleet deployment tooling, and OTA updates. All features require explicit user consent before transmitting any data.

**Migration Phase:** F (Growth)
**Product Scope:** Growth (v0.5)

### Story 11.1: Anonymous Telemetry Collection (Opt-in)

As a **product owner**,
I want armOS to collect anonymous usage telemetry (hardware detected, boot count, teleop session duration, diagnostic pass/fail rates) with explicit opt-in,
So that we can track adoption metrics, identify the most common hardware configurations, and prioritize support.

**Acceptance Criteria:**

**Given** the user has opted in via the first-run wizard or `armos telemetry on`
**When** events occur (boot, teleop session, diagnostic run)
**Then** events are queued to a local SQLite file (`~/.local/share/armos/telemetry.db`)
**And** events are batched and uploaded via HTTPS POST when internet is available (never blocks offline workflows)

**Given** a user wants to inspect what data would be sent
**When** they run `armos telemetry show`
**Then** the exact pending events are displayed

**Given** a user wants to disable telemetry
**When** they run `armos telemetry off`
**Then** collection is disabled and the local queue is deleted

**Given** telemetry is enabled
**When** hardware serial numbers are included in events
**Then** they are hashed with a per-install salt (no PII)

**Size:** L
**Dependencies:** Settings system (from 7.0 opt-in), backend service
**Implements:** FR46

---

### Story 11.2: Cloud Training Upload Hook

As a **user who has collected demonstration data**,
I want to upload my dataset to armOS Cloud for GPU training and download the trained policy,
So that I can go from data collection to a working policy without setting up a GPU environment.

**Acceptance Criteria:**

**Given** I have a collected dataset
**When** I run `armos cloud upload --dataset ./my-dataset`
**Then** the dataset is uploaded via resumable multipart upload to the cloud service

**Given** a training job is in progress
**When** I run `armos cloud status`
**Then** I see training job progress

**Given** a training job is complete
**When** I run `armos cloud download --job <id>`
**Then** the trained policy checkpoint is retrieved

**Given** no internet is available
**When** I attempt to upload
**Then** a clear error is shown: "No internet connection. Dataset saved locally at /path."

**Size:** XL
**Dependencies:** 9.3 (data collection), cloud backend (separate project)
**Implements:** FR47

---

### Story 11.3: Profile Sharing via HuggingFace Hub

As a **community member who has tuned a robot profile**,
I want to publish my profile to a shared repository and browse/download profiles others have published,
So that new users can get pre-tuned configs for their specific hardware setup.

**Acceptance Criteria:**

**Given** I have a working profile
**When** I run `armos profile publish --name "so101-wowrobo-resin"`
**Then** the profile YAML + calibration is pushed to HuggingFace Hub under the `armos-community/profiles` organization

**Given** I want to find profiles
**When** I run `armos profile search "so101"`
**Then** matching profiles are listed from the Hub with star counts and last-updated dates

**Given** I find a profile I want
**When** I run `armos profile install <hub-id>`
**Then** the profile is downloaded, validated against the JSON schema, and installed to `~/.config/armos/profiles/`

**Size:** L
**Dependencies:** 3.1, HuggingFace Hub API
**Implements:** FR48

---

### Story 11.4: Fleet Deployment Config Export/Import

As an **educator setting up 30 armOS stations**,
I want to configure one USB stick and clone its state (calibrations, profiles, settings) to all others,
So that I do not have to configure each station individually.

**Acceptance Criteria:**

**Given** a configured armOS station
**When** I run `armos fleet export`
**Then** a `.armos-config.tar.gz` is created containing all user-writable state

**Given** a config bundle
**When** I run `armos fleet import <file>`
**Then** the config is applied to the current machine
**And** calibration data is marked as "needs re-validation"

**Given** the flash script
**When** I run `flash.ps1 --config <file>`
**Then** the config bundle is embedded into the image during flashing

**Size:** M
**Dependencies:** 8.2, 8.3
**Implements:** FR49

---

### Story 11.5: armos update Command

As a **user**,
I want to update the armos Python package on my USB stick without re-flashing,
So that I can get bug fixes and new features with a single command.

**Acceptance Criteria:**

**Given** a newer version of armos is available on PyPI
**When** I run `armos update --check`
**Then** the available update is displayed with release notes

**Given** I want to update
**When** I run `armos update --apply`
**Then** the new version is installed to the persistent partition's virtualenv
**And** the new version is verified before committing

**Size:** M
**Dependencies:** 8.2 (persistent partition)
**Implements:** FR55

---

## Dependency Graph

```
Epic 1 (Package Skeleton)
  |
  +---> Epic 2 (HAL - Feetech) ----+
  |                                  |
  +---> Epic 3 (Profiles - SO-101) -+
                                     |
                    +----------------+
                    |
                    v
               Epic 4 (Diagnostics)
               Epic 5 (Telemetry)
                    |
                    v
               Epic 6 (Calibration & Teleop)
                    |
          +---------+---------+
          |                   |
          v                   v
     Epic 7 (TUI)       Epic 9 (AI & Data)
          |                   |
          +---------+---------+
                    |
                    v
               Epic 8 (USB Image)
                    |
          +---------+---------+
          |                   |
          v                   v
     Epic 10 (Growth)   Epic 11 (Business)
```

---

## Story Point Summary

| Epic | Stories | S | M | L | XL | Total Weight* |
|------|---------|---|---|---|----|----|
| 0: Sprint 0 | 2 | 1 | 1 | 0 | 0 | 4 |
| 1: Package Skeleton | 5 | 5 | 0 | 0 | 0 | 5 |
| 2: HAL - Feetech | 5 | 0 | 4 | 1 | 0 | 17 |
| 3: Profiles - SO-101 | 5 | 2 | 3 | 0 | 0 | 11 |
| 4: Diagnostics | 5 | 0 | 3 | 2 | 0 | 19 |
| 5: Telemetry | 3 | 1 | 1 | 1 | 0 | 9 |
| 6: Calibration & Teleop | 4 | 0 | 3 | 1 | 0 | 14 |
| 7: TUI Launcher | 5 | 0 | 3 | 2 | 0 | 17 |
| 8: USB Image | 10 | 3 | 5 | 2 | 0 | 27 |
| 9: AI & Data | 3 | 1 | 1 | 1 | 0 | 8 |
| **MVP Total** | **47** | **13** | **24** | **10** | **0** | **131** |
| 10: Growth | 6 | 0 | 2 | 4 | 0 | 26 |
| 11: Business | 5 | 0 | 2 | 2 | 1 | 19 |
| **Grand Total** | **58** | **13** | **28** | **16** | **1** | **176** |

*Weight: S=1, M=3, L=5, XL=8

---

## Requirements Traceability Matrix

| FR | Story | Epic | Phase |
|----|-------|------|-------|
| FR1 (CH340) | 2.1, 6.4 | 2, 6 | MVP |
| FR1 (all) | 10.1 | 10 | Growth |
| FR2 | 2.2 | 2 | MVP |
| FR3 | 10.1 | 10 | Growth |
| FR4 | 3.5, 6.4 | 3, 6 | MVP |
| FR5 | 10.1 | 10 | Growth |
| FR6 | 8.2 | 8 | MVP |
| FR7 | 3.1 | 3 | MVP |
| FR8 | 10.3 | 10 | Growth |
| FR9 | 10.3 | 10 | Growth |
| FR10 | 3.2 | 3 | MVP |
| FR11 | 2.3 | 2 | MVP |
| FR12 | 6.1, 3.3 | 6, 3 | MVP |
| FR13 | 3.3 | 3 | MVP |
| FR14 | 3.4 | 3 | MVP (pulled from Growth) |
| FR15 | 6.2 | 6 | MVP |
| FR16 | 6.3, 5.1 | 6, 5 | MVP |
| FR17 | 6.2 | 6 | MVP |
| FR18 | 10.4 | 10 | Growth |
| FR19 | 4.1, 4.2a, 4.2b | 4 | MVP |
| FR20 | 5.1 | 5 | MVP |
| FR21 | 5.2, 4.3 | 5, 4 | MVP |
| FR22 | 4.4 | 4 | MVP |
| FR23 | 5.3, 4.2a, 4.2b | 5, 4 | MVP |
| FR24 | 9.3 | 9 | MVP |
| FR25 | 9.3 | 9 | MVP |
| FR26 | 10.4 | 10 | Growth |
| FR27 | 9.3 | 9 | MVP |
| FR28 | 8.1b | 8 | MVP |
| FR29 | 8.2 | 8 | MVP |
| FR30 | 8.1b | 8 | MVP |
| FR31 | 8.3 | 8 | MVP |
| FR32 | 10.5 | 10 | Growth |
| FR33 | 7.1, 7.2 | 7 | MVP (TUI) |
| FR34 | 7.3 | 7 | MVP (TUI) |
| FR35 | 10.4 | 10 | Growth |
| FR36 | 5.3 | 5 | MVP |
| FR37 | 1.5, 9.1 | 1, 9 | MVP |
| FR38 | 10.6 | 10 | Vision |
| FR39 | 2.1, 10.2 | 2, 10 | MVP (ABC), Growth (plugins) |
| FR40 | 10.2 | 10 | Growth |
| FR41 | 10.2 | 10 | Vision |
| FR42 | 6.2 | 6 | MVP |
| FR43 | 7.0 | 7 | MVP |
| FR44 | 8.5 | 8 | MVP |
| FR45 | 7.4 | 7 | MVP (launch) |
| FR46 | 11.1 | 11 | Growth |
| FR47 | 11.2 | 11 | Growth |
| FR48 | 11.3 | 11 | Growth |
| FR49 | 11.4 | 11 | Growth |
| FR50 | 8.8 | 8 | MVP |
| FR51 | 8.9 | 8 | MVP |
| FR52 | 8.6 | 8 | MVP |
| FR53 | 8.7 | 8 | MVP |
| FR54 | 2.5 | 2 | MVP |
| FR55 | 11.5 | 11 | Growth |

---

_Epic breakdown for armOS USB v2.1 -- consolidated from planning, reviews, and implementation enhancements._
