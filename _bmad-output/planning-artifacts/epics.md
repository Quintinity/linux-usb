# RobotOS USB - Epic Breakdown

**Author:** John (Product Manager Agent)
**Date:** 2026-03-15
**Status:** Draft
**Version:** 1.0

---

## Overview

This document provides the complete epic and story breakdown for RobotOS USB, decomposing the requirements from the PRD and Architecture into implementable stories. Epics are ordered by the architecture's migration phases (A through F) and aligned to the PRD's three-phase product scope: MVP (v0.1), Growth (v0.5), and Vision (v1.0).

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
| FR19 | Comprehensive hardware diagnostic suite | MVP |
| FR20 | Real-time servo register monitoring | MVP |
| FR21 | Diagnostic/monitoring data logging to CSV | MVP |
| FR22 | Programmatic arm exercise routines | MVP |
| FR23 | Fault condition detection and reporting | MVP |
| FR24 | Record teleop sessions as LeRobot datasets | MVP |
| FR25 | Data collection session configuration | MVP |
| FR26 | Episode review, replay, and deletion | Growth |
| FR27 | Local dataset storage in LeRobot format | MVP |
| FR28 | USB boot on x86 UEFI hardware | MVP |
| FR29 | Persistent user data across reboots | MVP |
| FR30 | Full offline operation | MVP |
| FR31 | Windows flash script for USB image | MVP |
| FR32 | USB image cloning for fleet deployment | Growth |
| FR33 | Central status dashboard | MVP (TUI) |
| FR34 | Dashboard-launched workflows | MVP (TUI) |
| FR35 | Live camera feeds in dashboard | Growth |
| FR36 | Actionable error messages with suggested fixes | MVP |
| FR37 | Pre-seeded AI context files (CLAUDE.md, memory) | MVP |
| FR38 | AI troubleshooting with live system state | Vision |
| FR39 | Plugin interface for new servo protocols | Growth |
| FR40 | YAML-only profile addition (no code changes) | Growth |
| FR41 | Third-party plugin/profile directory | Vision |

### Non-Functional Requirements

| ID | Requirement | Category |
|----|-------------|----------|
| NFR1 | Teleop loop latency <= 20ms (p95) | Performance |
| NFR2 | Servo bus scan <= 3 seconds (12 servos) | Performance |
| NFR3 | Hardware auto-detection <= 5 seconds | Performance |
| NFR4 | Dashboard telemetry >= 10 Hz | Performance |
| NFR5 | Boot time <= 90 seconds to dashboard | Performance |
| NFR6 | Automatic retry on transient servo failures (max 3) | Reliability |
| NFR7 | Bus disconnection detection <= 2 seconds | Reliability |
| NFR8 | No episode data loss on system error | Reliability |
| NFR9 | Survive unexpected power loss (journaled FS) | Reliability |
| NFR10 | 90%+ x86 UEFI boot compatibility | Reliability |
| NFR11 | Primary workflows completable without terminal | Usability |
| NFR12 | Error messages include cause + remediation | Usability |
| NFR13 | Dashboard operable via keyboard, mouse, or touch | Usability |
| NFR14 | USB image fits on 32GB drive (base <= 16GB) | Portability |
| NFR15 | Runs on Intel i5 6th gen / Ryzen 3 1st gen, 8GB RAM | Portability |
| NFR16 | All runtime dependencies pre-installed | Portability |
| NFR17 | Human-readable YAML profiles with JSON schema | Maintainability |
| NFR18 | Servo driver interface < 15 methods, < 500 LOC | Maintainability |
| NFR19 | Structured hardware event logging | Maintainability |
| NFR20 | No network services on fresh boot | Security |
| NFR21 | Serial access restricted to robotos group (MODE=0660) | Security |
| NFR22 | No user data transmitted without explicit action | Security |

---

## FR Coverage Map

| Story | Functional Requirements Covered |
|-------|-------------------------------|
| 1.1 | -- (infrastructure) |
| 1.2 | -- (infrastructure) |
| 1.3 | -- (infrastructure) |
| 1.4 | -- (infrastructure) |
| 1.5 | FR37 |
| 2.1 | FR1 (CH340), FR39 (partial) |
| 2.2 | FR2, FR23 (partial) |
| 2.3 | FR11 |
| 2.4 | NFR6 |
| 3.1 | FR7, FR10, NFR17 |
| 3.2 | FR7 (validation) |
| 3.3 | FR12, FR13 |
| 3.4 | FR14 |
| 4.1 | FR19 (partial) |
| 4.2 | FR19, FR23 |
| 4.3 | FR19, FR21 |
| 4.4 | FR22 |
| 5.1 | FR20, FR16 |
| 5.2 | FR21 |
| 5.3 | FR23, FR36, NFR7, NFR12 |
| 6.1 | FR12 |
| 6.2 | FR15, FR17 |
| 6.3 | FR16 |
| 6.4 | FR1 (CH340), FR4 |
| 7.1 | FR33 (TUI), FR34 (TUI) |
| 7.2 | FR33 (TUI) |
| 7.3 | FR34 (TUI), NFR11 |
| 8.1 | FR28, FR30, NFR5, NFR14 |
| 8.2 | FR6, FR29, NFR9 |
| 8.3 | FR31 |
| 8.4 | NFR10 |
| 9.1 | FR37 |
| 9.2 | FR24, FR25, FR27 |
| 9.3 | FR24, FR27, NFR8 |
| 10.1 | FR1 (all chips), FR3, FR5, NFR3 |
| 10.2 | FR39, FR40, FR41 (partial) |
| 10.3 | FR8, FR9 |
| 10.4 | FR18, FR26, FR35 |
| 10.5 | FR32 |
| 10.6 | FR38 |

---

## Epic List

| Epic | Title | Phase | Product Scope | Priority |
|------|-------|-------|---------------|----------|
| 1 | Package Skeleton and CLI Foundation | A (Package skeleton) | MVP | P0 |
| 2 | Hardware Abstraction Layer -- Feetech | B (HAL and profiles) | MVP | P0 |
| 3 | Robot Profile System -- SO-101 | B (HAL and profiles) | MVP | P0 |
| 4 | Diagnostic Framework Refactor | C (Diagnostics and telemetry) | MVP | P0 |
| 5 | Telemetry and Monitoring Library | C (Diagnostics and telemetry) | MVP | P0 |
| 6 | Calibration and Teleop CLI | D (Calibration, teleop, TUI) | MVP | P0 |
| 7 | TUI Launcher | D (Calibration, teleop, TUI) | MVP | P1 |
| 8 | Pre-built USB Image | E (ISO build and AI) | MVP | P0 |
| 9 | AI Integration and Data Collection | E (ISO build and AI) | MVP | P1 |
| 10 | Growth Phase -- Multi-Hardware and Polish | F (Growth and polish) | Growth/Vision | P2 |

---

## Epic 1: Package Skeleton and CLI Foundation

**Goal:** Create the `robotos` Python package with a working CLI entry point. Move existing scripts into the package structure so that everything is invoked as `robotos <command>` instead of `python <script>.py`. This is the foundation every other epic builds on.

**Migration Phase:** A
**Product Scope:** MVP (v0.1)

### Story 1.1: Initialize Python Package with pyproject.toml

As a **developer**,
I want a `robotos` Python package with `pyproject.toml`, proper entry points, and a `click`-based CLI skeleton,
So that all future commands have a consistent, installable entry point.

**Acceptance Criteria:**

**Given** the repository root contains `robotos/` and `pyproject.toml`
**When** I run `pip install -e .` in the repository root
**Then** the `robotos` command is available on PATH
**And** running `robotos --help` displays available command groups
**And** running `robotos --version` displays the version string `0.1.0`

**Size:** S
**Dependencies:** None

---

### Story 1.2: CLI Command Group Structure

As a **developer**,
I want stub implementations for all MVP CLI commands (detect, status, calibrate, teleop, record, diagnose, monitor, exercise, config),
So that the command surface area is established and each epic can fill in the implementations.

**Acceptance Criteria:**

**Given** the `robotos` package is installed
**When** I run `robotos detect --help`
**Then** I see a help message describing the detect command
**And** the same works for `status`, `calibrate`, `teleop`, `record`, `diagnose`, `monitor`, `exercise`, and `config`

**Given** a stub command is invoked (e.g., `robotos detect`)
**When** the underlying implementation is not yet complete
**Then** the command prints "Not yet implemented" and exits with code 1

**Size:** S
**Dependencies:** 1.1

---

### Story 1.3: Utility Module -- Serial Helpers

As a **developer**,
I want a `robotos.utils.serial` module with sign-magnitude decoding, port discovery helpers, and common serial constants,
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
I want a `robotos.utils.config` module that provides XDG-compliant paths for profiles, calibration, datasets, and logs,
So that all file storage follows a consistent, predictable convention.

**Acceptance Criteria:**

**Given** the module is imported
**When** I call `config_dir()`, `calibration_dir()`, `datasets_dir()`, `logs_dir()`
**Then** each returns the correct XDG path under `~/.config/robotos/` or `~/.local/share/robotos/`
**And** directories are created automatically if they do not exist

**Size:** S
**Dependencies:** 1.1

---

### Story 1.5: Migrate CLAUDE.md and AI Context Files

As a **developer**,
I want the CLAUDE.md and memory files updated to reference `robotos` CLI commands instead of raw Python scripts,
So that AI-assisted troubleshooting works with the new package structure.

**Acceptance Criteria:**

**Given** a user has the `robotos` package installed
**When** Claude Code reads the CLAUDE.md
**Then** all commands reference `robotos diagnose`, `robotos monitor`, etc., not `python diagnose_arms.py`
**And** the CLAUDE.md documents the `robotos` CLI command set

**Size:** S
**Dependencies:** 1.2

---

## Epic 2: Hardware Abstraction Layer -- Feetech

**Goal:** Implement the `ServoProtocol` abstract base class and the first concrete implementation (`FeetechPlugin`) that wraps the existing Feetech STS3215 communication code. This decouples all higher-level code from the specific servo hardware.

**Migration Phase:** B
**Product Scope:** MVP (v0.1)

### Story 2.1: ServoProtocol ABC and FeetechPlugin

As a **developer**,
I want a `ServoProtocol` abstract base class defining the hardware interface (connect, disconnect, ping, read_position, write_position, sync_read, sync_write, get_telemetry, enable/disable_torque, read/write_register),
So that all servo communication goes through a testable, swappable abstraction.

**Acceptance Criteria:**

**Given** the `ServoProtocol` ABC exists in `robotos.hal.protocol`
**When** I implement `FeetechPlugin(ServoProtocol)` in `robotos.hal.plugins.feetech`
**Then** the plugin wraps `FeetechMotorsBus` from LeRobot
**And** all 10+ abstract methods are implemented
**And** the plugin is discoverable via `ServoProtocol.get_plugin("feetech")`

**Given** a CH340 USB-serial adapter is connected with STS3215 servos
**When** I call `plugin.connect("/dev/ttyUSB0")` and `plugin.ping(1)`
**Then** the servo responds and `ping` returns `True`

**Size:** L
**Dependencies:** 1.1, 1.3

---

### Story 2.2: Servo Bus Scan

As a **user**,
I want to scan a servo bus and see all connected servos with their IDs, firmware versions, and protocol type,
So that I can verify my hardware is properly connected before calibration.

**Acceptance Criteria:**

**Given** a Feetech servo controller is connected with 6 servos (IDs 1-6)
**When** I call `plugin.scan_bus(id_range=range(1, 13))`
**Then** I receive a list of 6 `ServoInfo` objects with id, firmware_version, model, and protocol fields
**And** the scan completes within 3 seconds (NFR2)

**Given** a servo on the bus is not responding (disconnected wire)
**When** the scan runs
**Then** that servo ID is absent from results (not an error, just not found)

**Size:** M
**Dependencies:** 2.1

---

### Story 2.3: Protection Settings Read/Write

As a **user**,
I want the system to read and write servo protection settings (max temperature, max voltage, overload torque, protection time) from a robot profile,
So that my servos are protected from damage according to my robot's requirements.

**Acceptance Criteria:**

**Given** a robot profile specifies `overload_torque: 90`, `protective_torque: 50`, `protection_time: 254`
**When** I call `plugin.apply_protection(servo_id, profile.protection)`
**Then** the EEPROM registers on the servo are written with the specified values
**And** a subsequent read confirms the values match

**Given** the gripper joint has different protection settings than other joints
**When** I apply protection from a profile with per-joint overrides
**Then** the gripper servo receives its custom settings while others receive defaults

**Size:** M
**Dependencies:** 2.1

---

### Story 2.4: Resilient Communication with Retry and Port Flush

As a **user**,
I want servo communication to automatically retry on transient failures with port flush between attempts,
So that brief electrical noise or timing issues do not crash my teleop session.

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

**Size:** M
**Dependencies:** 1.1, 1.4

---

### Story 3.2: Built-in SO-101 Profile

As a **user**,
I want the system to ship with a pre-built SO-101 profile that describes the 2x 6-DOF leader-follower arm configuration with Feetech STS3215 servos,
So that I can use my SO-101 without creating any configuration files.

**Acceptance Criteria:**

**Given** the `robotos` package is installed
**When** I call `ProfileLoader.list_profiles()`
**Then** "SO-101" appears in the list with description "HuggingFace SO-101 6-DOF robot arm (leader/follower pair)"

**Given** the SO-101 profile is loaded
**When** I inspect its structure
**Then** it defines 2 arms (leader + follower), each with 6 joints (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper)
**And** servo IDs are 1-6 for each arm
**And** protection settings match the tuned values from the existing deployment (overload_torque=90, protective_torque=50, protection_time=254 for body joints; overload_torque=25 for gripper)
**And** the LeRobot section specifies robot_type="so100" and fps=60

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
**Then** a JSON file is written to `~/.config/robotos/calibration/{instance_id}/follower.json`
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

**Size:** M
**Dependencies:** 2.1, 3.1

---

### Story 4.2: Migrate Existing Diagnostic Checks

As a **user**,
I want all 11 diagnostic phases from `diagnose_arms.py` available as individual health checks,
So that I can run a comprehensive hardware diagnostic or target a specific concern.

**Acceptance Criteria:**

**Given** the following checks are implemented: PortDetection, ServoPing, FirmwareVersion, PowerHealth, StatusRegister, EEPROMConfig, CommsReliability, TorqueStress, CrossBusTeleop, MotorIsolation, CalibrationValid
**When** I run `robotos diagnose`
**Then** all 11 checks execute in sequence and produce a summary report
**And** each check uses the `ServoProtocol` and `RobotProfile` interfaces (not hardcoded Feetech calls)

**Given** I want to check only servo communication
**When** I run `robotos diagnose --check comms`
**Then** only the CommsReliability check executes

**Size:** XL
**Dependencies:** 4.1, 2.1, 2.2, 2.3, 3.1, 3.3

---

### Story 4.3: Diagnostic Output Reporters

As a **user**,
I want diagnostic results available in multiple formats: colored terminal output, JSON (for AI consumption), and CSV (for logging),
So that I can read results in the terminal, feed them to Claude Code, or analyze them in a spreadsheet.

**Acceptance Criteria:**

**Given** a diagnostic run has completed
**When** I run `robotos diagnose` (default)
**Then** results are printed to the terminal with colored PASS/WARN/FAIL indicators using Rich

**Given** a diagnostic run has completed
**When** I run `robotos diagnose --json`
**Then** results are printed as valid JSON with `status`, `message`, and `data` fields per check

**Given** a diagnostic run has completed
**When** I run `robotos diagnose --log /path/to/output.csv`
**Then** results are appended to a CSV file with timestamp, check name, status, and message columns

**Size:** M
**Dependencies:** 4.1

---

### Story 4.4: Exercise Command Migration

As a **user**,
I want to run programmatic arm exercise routines via `robotos exercise`,
So that I can verify mechanical health by moving each joint through its range.

**Acceptance Criteria:**

**Given** a calibrated SO-101 is connected
**When** I run `robotos exercise --arm follower`
**Then** each joint moves through its calibrated range (min to max to center) at a safe speed
**And** per-joint telemetry (voltage, load, temperature) is displayed during the exercise

**Given** I want to exercise only one joint
**When** I run `robotos exercise --arm follower --joint elbow_flex`
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

**Given** I run `robotos monitor --log /tmp/telemetry.csv`
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
**When** I run `robotos calibrate --arm follower`
**Then** the system guides me through each joint: "Move shoulder_pan to its minimum position and press Enter"
**And** after recording min/max for all joints, calibration data is saved to disk

**Given** calibration is in progress
**When** I press Ctrl+C
**Then** the partially completed calibration is discarded with a message "Calibration cancelled. No data saved."

**Given** a stored calibration already exists for this arm
**When** I run `robotos calibrate --arm follower`
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
**When** I run `robotos teleop`
**Then** the system reads leader arm positions and writes them to the follower arm at 60 Hz (per SO-101 profile)
**And** the system displays live telemetry (position, voltage, load) for both arms

**Given** teleoperation is running
**When** a servo exceeds its protection threshold (e.g., temperature > max)
**Then** teleoperation halts immediately with "SAFETY STOP: follower/elbow_flex temperature 65C exceeds limit 60C"
**And** all follower servo torques are disabled

**Given** teleoperation is running
**When** I press Ctrl+C
**Then** teleoperation stops gracefully, follower torques are disabled, and a session summary is printed (duration, max temps, max loads, error count)

**Size:** L
**Dependencies:** 2.1, 2.4, 3.1, 3.3, 5.1, 5.3

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
I want to run `robotos detect` to see all connected USB-serial adapters and cameras with their identified types,
So that I can verify my hardware is recognized before starting calibration or teleop.

**Acceptance Criteria:**

**Given** a CH340 USB-serial adapter is connected
**When** I run `robotos detect`
**Then** I see: "USB Serial: /dev/ttyUSB0 (CH340, vendor=1a86, product=7523) -- Feetech servo controller"

**Given** a USB camera is connected
**When** I run `robotos detect`
**Then** I see: "Camera: /dev/video0 (USB 2.0 Camera, 1920x1080@30fps, 640x480@60fps)"

**Given** no USB devices are connected
**When** I run `robotos detect`
**Then** I see: "No USB serial devices or cameras detected."

**Size:** M
**Dependencies:** 2.1, 1.3

---

## Epic 7: TUI Launcher

**Goal:** Build a terminal user interface (TUI) using `textual` that provides a dashboard for robot status, hardware telemetry, and launching all primary workflows without typing commands. This is the "zero terminal commands" experience for MVP.

**Migration Phase:** D
**Product Scope:** MVP (v0.1)

### Story 7.1: TUI Application Shell

As a **user**,
I want to launch `robotos tui` and see a terminal dashboard showing detected hardware, active profile, and calibration state,
So that I have a visual overview of my robot setup without memorizing CLI commands.

**Acceptance Criteria:**

**Given** the `robotos` package is installed with the `tui` extra
**When** I run `robotos tui`
**Then** a full-screen terminal application launches using `textual`
**And** the header shows "RobotOS v0.1.0" and the detected robot profile name
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

**Size:** L
**Dependencies:** 7.1, 7.2, 6.1, 6.2, 4.2

---

## Epic 8: Pre-built USB Image

**Goal:** Create a bootable USB image using `live-build` that ships with the entire `robotos` package, LeRobot, all system dependencies, and the SO-101 profile pre-installed. Users flash and boot -- no install process.

**Migration Phase:** E
**Product Scope:** MVP (v0.1)

### Story 8.1: live-build Configuration and ISO Build Script

As a **developer**,
I want a `live-build` configuration that produces a bootable Ubuntu 24.04-based ISO with all RobotOS dependencies pre-installed,
So that the ISO can be built reproducibly in CI or locally.

**Acceptance Criteria:**

**Given** the `robotos-iso/` directory contains valid `live-build` configuration
**When** I run the build script (e.g., `./build-iso.sh`)
**Then** a `robotos-0.1.0.iso` file is produced
**And** the ISO boots to a desktop on a x86 UEFI system within 90 seconds (NFR5)
**And** the ISO is under 16GB (NFR14)

**Given** the ISO has booted
**When** I open a terminal and run `robotos --version`
**Then** it prints `0.1.0`
**And** `python3.12 -c "import lerobot; print(lerobot.__version__)"` prints `0.5.0`
**And** the SO-101 profile is available via `robotos profile list`

**Size:** XL
**Dependencies:** 1.1, 2.1, 3.2, 4.2, 5.1, 6.1, 6.2, 7.1

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
**Dependencies:** 8.1

---

### Story 8.3: Windows Flash Script Update

As a **user**,
I want to flash the RobotOS USB image from Windows using a single PowerShell command,
So that I can prepare a bootable USB without needing Linux tools.

**Acceptance Criteria:**

**Given** I have downloaded `robotos-0.1.0.iso` on a Windows machine
**When** I run `flash.ps1 -Image robotos-0.1.0.iso -Drive E:`
**Then** the script writes the ISO to the USB drive
**And** the USB drive is bootable on x86 UEFI hardware

**Given** the script detects the target drive has data
**When** the script starts
**Then** it prompts for confirmation before overwriting

**Size:** M
**Dependencies:** 8.1

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
**Dependencies:** 8.1, 8.2

---

## Epic 9: AI Integration and Data Collection

**Goal:** Integrate the LeRobot data collection pipeline into the `robotos` package and set up the Claude Code context for AI-assisted troubleshooting. Users can record teleop sessions as datasets and get AI help when things go wrong.

**Migration Phase:** E
**Product Scope:** MVP (v0.1)

### Story 9.1: Claude Code Context Pre-seeding

As a **user**,
I want the USB image to include pre-seeded Claude Code context files (CLAUDE.md, memory files) that enable Claude to understand my robot setup and diagnose issues,
So that I can get AI-assisted troubleshooting without manual context setup.

**Acceptance Criteria:**

**Given** the USB image has booted
**When** I launch Claude Code in the RobotOS project directory
**Then** CLAUDE.md is present and describes all `robotos` CLI commands
**And** memory files document known hardware issues (Feetech sync_read bug, brltty hijack, power supply requirements)
**And** `robotos diagnose --json` output can be pasted to Claude for interpretation

**Size:** S
**Dependencies:** 1.5, 8.1

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

**Size:** M
**Dependencies:** 3.1, 3.3, 2.1

---

### Story 9.3: Data Collection Command

As a **user**,
I want to record teleoperation sessions as LeRobot-compatible datasets via `robotos record`,
So that I can collect training data for imitation learning.

**Acceptance Criteria:**

**Given** both arms are connected, calibrated, and cameras are detected
**When** I run `robotos record --task pick_and_place --episodes 10`
**Then** the system starts teleoperation and records servo positions + camera frames + timestamps
**And** after each episode (user presses Enter to advance), the episode is saved to disk immediately (NFR8)

**Given** 10 episodes have been recorded
**When** the session completes
**Then** the dataset is saved in LeRobot format at `~/.local/share/robotos/datasets/pick_and_place/`
**And** `robotos record --list` shows the dataset with episode count and disk size

**Given** a recording is in progress
**When** the system encounters a transient servo error
**Then** the current episode is marked with a warning flag but recording continues

**Size:** L
**Dependencies:** 9.2, 6.2, 5.1

---

## Epic 10: Growth Phase -- Multi-Hardware and Polish

**Goal:** Extend RobotOS beyond the SO-101 to support multiple robot platforms, servo protocols, and host hardware. Add the user-facing polish features (profile creation wizard, configurable teleop, episode review, image cloning, web dashboard foundations). This epic covers Growth (v0.5) and Vision (v1.0) scope items.

**Migration Phase:** F
**Product Scope:** Growth (v0.5) / Vision (v1.0)

### Story 10.1: DeviceManager -- pyudev Hotplug and Profile Matching

As a **user**,
I want the system to automatically detect USB devices when plugged in and match them to the best robot profile,
So that I do not need to manually configure ports or select profiles.

**Acceptance Criteria:**

**Given** no robot hardware is connected
**When** I plug in two CH340 USB-serial adapters
**Then** within 5 seconds (NFR3), the system detects both adapters, scans the servo buses, and matches the configuration to the SO-101 profile
**And** the dashboard updates to show "SO-101 detected (leader + follower)"

**Given** a FTDI adapter (Dynamixel U2D2) is plugged in
**When** the system scans the servo bus
**Then** it identifies the Dynamixel protocol and reports "Dynamixel servos detected -- searching for matching profile"

**Given** the detected hardware does not match any profile
**When** detection completes
**Then** the system reports "Unknown configuration: 4x Dynamixel XL330 servos. No matching profile. Use `robotos profile create` to define one."

**Size:** L
**Dependencies:** 2.1, 3.1, 6.4

---

### Story 10.2: Plugin Architecture for Servo Protocols

As a **developer**,
I want to add support for new servo protocols by implementing the `ServoProtocol` interface and dropping a plugin file into the plugins directory,
So that the community can contribute hardware support without modifying core code.

**Acceptance Criteria:**

**Given** I create a file `dynamixel.py` implementing `DynamixelPlugin(ServoProtocol)` with all required methods
**When** I place it in `robotos/hal/plugins/`
**Then** `ServoProtocol.get_plugin("dynamixel")` returns the plugin
**And** all CLI commands work with the Dynamixel plugin (detect, calibrate, teleop, diagnose)

**Given** the `ServoProtocol` ABC is documented
**When** a community developer reads the documentation
**Then** they can implement a new protocol in under 500 lines of code (NFR18)
**And** the ABC has fewer than 10 required abstract methods

**Size:** L
**Dependencies:** 2.1

---

### Story 10.3: Profile Creation Wizard and Export/Import

As a **user**,
I want to create a new robot profile through a guided workflow and export it for sharing,
So that I can use RobotOS with custom hardware and share my configuration with others.

**Acceptance Criteria:**

**Given** I have an unsupported robot configuration
**When** I run `robotos profile create`
**Then** the system guides me through: specifying arm count, joints per arm, servo IDs, joint names, position limits, and protection settings
**And** the resulting profile is saved as a YAML file in `~/.config/robotos/profiles/`

**Given** I have a working profile
**When** I run `robotos profile export my-robot --output my-robot.yaml`
**Then** a standalone YAML file is created that can be imported on another RobotOS installation

**Given** I received a profile YAML from someone else
**When** I run `robotos profile import my-robot.yaml`
**Then** the profile is validated, copied to the profiles directory, and available for use

**Size:** L
**Dependencies:** 3.1, 3.2

---

### Story 10.4: Configurable Teleop, Episode Review, and Camera Feeds

As a **user**,
I want to configure teleoperation parameters (speed scaling, deadband), review recorded episodes, and see live camera feeds,
So that I have full control over my data collection workflow.

**Acceptance Criteria:**

**Given** teleoperation is running
**When** I have configured speed_scaling=0.5 in my profile or via `robotos teleop --speed 0.5`
**Then** the follower arm moves at half the speed of the leader arm

**Given** I have recorded datasets
**When** I run `robotos record --review pick_and_place --episode 5`
**Then** the system replays episode 5, showing servo positions over time

**Given** USB cameras are detected
**When** I run `robotos monitor --cameras`
**Then** camera device paths and capabilities are displayed

**Size:** L
**Dependencies:** 6.2, 9.3, 6.4

---

### Story 10.5: USB Image Cloning for Fleet Deployment

As an **educator**,
I want to clone a configured USB image (with my profiles and calibrations) to multiple USB sticks,
So that I can set up a classroom of identical robot stations quickly.

**Acceptance Criteria:**

**Given** I have a configured RobotOS USB drive with calibration data
**When** I run `robotos image clone --target /dev/sdc`
**Then** the entire USB drive (including persistent data) is cloned to the target
**And** the cloned drive boots identically to the source

**Given** I want to clone without user-specific data
**When** I run `robotos image clone --clean --target /dev/sdc`
**Then** the cloned drive has the base image with profiles but no calibration data or datasets

**Size:** M
**Dependencies:** 8.1, 8.2

---

### Story 10.6: AI Troubleshooting with Live System State

As a **user**,
I want to launch an AI troubleshooting session that automatically provides Claude Code with my current system state (detected hardware, recent errors, servo telemetry),
So that I get context-aware diagnostic assistance without manually copying data.

**Acceptance Criteria:**

**Given** my robot is connected and has recent diagnostic results
**When** I run `robotos ai-assist`
**Then** the system writes a context file containing: detected hardware, active profile, last diagnostic results, recent telemetry alerts, and error logs
**And** Claude Code is launched with this context file pre-loaded

**Given** a servo fault occurred in the last session
**When** the AI-assist context is generated
**Then** the fault details (servo ID, fault type, timestamp, telemetry at time of fault) are included

**Size:** M
**Dependencies:** 9.1, 4.3, 5.3

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
                    v
               Epic 10 (Growth)
```

---

## Story Point Summary

| Epic | Stories | S | M | L | XL | Total Weight* |
|------|---------|---|---|---|----|----|
| 1: Package Skeleton | 5 | 5 | 0 | 0 | 0 | 5 |
| 2: HAL - Feetech | 4 | 0 | 3 | 1 | 0 | 12 |
| 3: Profiles - SO-101 | 4 | 2 | 2 | 0 | 0 | 8 |
| 4: Diagnostics | 4 | 0 | 3 | 0 | 1 | 17 |
| 5: Telemetry | 3 | 1 | 1 | 1 | 0 | 7 |
| 6: Calibration & Teleop | 4 | 0 | 3 | 1 | 0 | 12 |
| 7: TUI Launcher | 3 | 0 | 2 | 1 | 0 | 9 |
| 8: USB Image | 4 | 0 | 1 | 2 | 1 | 16 |
| 9: AI & Data | 3 | 1 | 1 | 1 | 0 | 7 |
| 10: Growth | 6 | 0 | 2 | 4 | 0 | 18 |
| **Total** | **40** | **9** | **18** | **11** | **2** | **111** |

*Weight: S=1, M=3, L=5, XL=8

---

## Requirements Traceability Matrix

| FR | Story | Epic | Phase |
|----|-------|------|-------|
| FR1 (CH340) | 2.1, 6.4 | 2, 6 | MVP |
| FR1 (all) | 10.1 | 10 | Growth |
| FR2 | 2.2 | 2 | MVP |
| FR3 | 10.1 | 10 | Growth |
| FR4 | 6.4 | 6 | MVP |
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
| FR19 | 4.1, 4.2 | 4 | MVP |
| FR20 | 5.1 | 5 | MVP |
| FR21 | 5.2, 4.3 | 5, 4 | MVP |
| FR22 | 4.4 | 4 | MVP |
| FR23 | 5.3, 4.2 | 5, 4 | MVP |
| FR24 | 9.3 | 9 | MVP |
| FR25 | 9.3 | 9 | MVP |
| FR26 | 10.4 | 10 | Growth |
| FR27 | 9.3 | 9 | MVP |
| FR28 | 8.1 | 8 | MVP |
| FR29 | 8.2 | 8 | MVP |
| FR30 | 8.1 | 8 | MVP |
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

---

_Epic breakdown for RobotOS USB -- a universal robot operating system on a bootable USB stick._
