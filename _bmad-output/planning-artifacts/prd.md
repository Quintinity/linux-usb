---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
inputDocuments:
  - product-brief.md
  - project-overview.md
  - README.md
  - CLAUDE.md
workflowType: 'prd'
---

# Product Requirements Document - RobotOS USB

**Author:** Bradley
**Date:** 2026-03-15

## Executive Summary

RobotOS USB transforms a bootable Linux USB stick into a universal robot operating system. Users plug the USB into any x86 computer, boot it, connect supported robotic hardware, and have a working robot control station in minutes -- no Linux expertise, no manual configuration, no internet required after first setup.

The project evolves from an existing single-purpose tool (Surface Pro 7 + SO-101 setup automation) into a hardware-agnostic robotics platform. It preserves the proven AI-driven setup pipeline (Claude Code + CLAUDE.md) and comprehensive servo diagnostic suite while adding hardware auto-detection, a universal robot API, and plug-and-play robot profiles.

**Differentiator:** Zero-config, USB-bootable, AI-assisted robotics OS that works on commodity x86 hardware. No GPU required. No cloud dependency for operation. Bridges the gap between complex ROS2 setups and bare-metal LeRobot installs.

**Target users:** Robotics hobbyists, AI researchers collecting training data, educators teaching physical robotics, and makers building custom robot platforms.

## Success Criteria

- **SC1:** A new user boots the USB on untested x86 hardware and reaches working robot teleoperation in under 5 minutes, measured from BIOS boot to first successful leader-follower movement.
- **SC2:** The system supports 3 or more robot arm platforms (SO-101, Koch v1.1, Aloha) with pre-configured profiles by v1.0 release.
- **SC3:** The system supports 3 or more servo protocols (Feetech STS3215, Dynamixel XL330, Dynamixel XL430) by v1.0 release.
- **SC4:** Zero manual terminal commands are required for basic operation (boot, detect hardware, calibrate, teleop, collect data) -- all accessible through a dashboard interface.
- **SC5:** The OS image boots successfully on 90% or more of tested x86 laptops and desktops (target: 20+ distinct hardware models validated).
- **SC6:** Community adoption reaches 100+ GitHub stars within 6 months of public release.
- **SC7:** Servo diagnostic suite detects and reports hardware faults (voltage sag, overload, communication failure) within 2 seconds of occurrence.
- **SC8:** Offline operation is fully functional after initial USB creation -- no internet required for boot, hardware detection, calibration, teleoperation, or data collection.

## Product Scope

### MVP (v0.1) -- Single-Platform Stabilization

Harden the existing Surface Pro 7 + SO-101 pipeline into a reproducible, pre-built OS image. Eliminate the multi-phase AI-driven install by shipping a fully configured image.

- Pre-built bootable USB image (no install-from-live-USB required)
- Feetech STS3215 auto-detection and udev configuration on boot
- Existing diagnostic suite (diagnose_arms.py, monitor_arm.py, exercise_arm.py, teleop_monitor.py) accessible from a terminal menu
- LeRobot v0.5.0 pre-installed with SO-101 profile
- USB camera detection and V4L2 configuration
- Claude Code context files pre-seeded for AI-assisted troubleshooting

### Growth (v0.5) -- Multi-Hardware Support

Extend beyond SO-101 to support multiple robot platforms and host hardware.

- Hardware auto-detection layer (USB device enumeration, servo protocol identification, camera enumeration)
- Robot profile system (YAML-based hardware descriptions for SO-101, Koch v1.1)
- Universal robot API abstracting Feetech and Dynamixel protocols
- Full-featured TUI dashboard with real-time telemetry, multi-robot support, and advanced configuration (MVP ships a basic TUI launcher menu)
- Support for 5+ x86 hardware targets (not just Surface Pro 7)
- Plugin architecture for adding new servo protocols

### Vision (v1.0) -- Universal Robot OS

Full platform with broad hardware support, community ecosystem, and zero-config operation.

- Web-based dashboard for robot control and monitoring
- 3+ robot arm profiles with auto-detection
- 3+ servo protocol drivers
- Community profile repository (users contribute hardware profiles)
- Offline AI assistant for troubleshooting and guided calibration
- Data collection pipeline with local dataset management
- One-click cloud training upload integration

## User Journeys

### UJ1: First-Time Boot (Hobbyist)

**Actor:** Robotics hobbyist with an SO-101 kit and a laptop.
**Trigger:** User has flashed RobotOS USB and wants to control their robot.

1. User inserts USB into laptop and boots from USB via BIOS boot menu.
2. System boots to RobotOS desktop or dashboard within 90 seconds.
3. User connects SO-101 servo controller via USB.
4. System detects Feetech CH340 USB-serial adapter, identifies it as a servo controller, and loads the Feetech STS3215 driver.
5. System scans the servo bus, discovers 6 servos per arm, and matches the configuration to the SO-101 robot profile.
6. Dashboard displays detected hardware: "SO-101 Leader Arm (6 servos) + SO-101 Follower Arm (6 servos)."
7. User selects "Calibrate" from the dashboard. System guides user through homing each joint.
8. User selects "Teleop." System launches leader-follower teleoperation. User moves the leader arm and the follower arm mirrors movements.

**Success:** Boot to teleop in under 5 minutes. No terminal commands. [Traces to SC1, SC4]

### UJ2: Hardware Diagnosis (Hobbyist with Problem)

**Actor:** User whose follower arm is not responding correctly.
**Trigger:** Servo 4 on the follower arm is stuttering during teleop.

1. User opens the diagnostics panel from the dashboard.
2. System runs a bus scan and displays per-servo health: voltage, temperature, load, communication error rate.
3. System flags servo 4: "Voltage: 6.8V (below 7.0V threshold) -- possible power supply sag under load."
4. System recommends: "Check power supply. STS3215 servos require 7.4V 3A minimum. Voltage drops below 7.0V cause torque instability."
5. User fixes power supply. Re-runs diagnostics. All servos pass.

**Success:** Root cause identified and communicated in under 60 seconds. [Traces to SC7]

### UJ3: Data Collection Session (AI Researcher)

**Actor:** AI researcher collecting demonstration data for imitation learning.
**Trigger:** User wants to record 50 episodes of a pick-and-place task.

1. User connects USB cameras and robot arms.
2. System detects cameras via V4L2, displays video feeds in dashboard.
3. User selects "Collect Data," specifies task name and episode count.
4. System configures LeRobot data collection pipeline with detected hardware.
5. User performs demonstrations. System records servo positions, camera frames, and timestamps.
6. After 50 episodes, user selects "Finish." System saves dataset in LeRobot format.
7. User can review recorded episodes from the dashboard.

**Success:** Data collection session with zero configuration of cameras or servo ports. [Traces to SC4, SC8]

### UJ4: New Robot Platform (Maker)

**Actor:** Maker who built a custom 4-DOF arm using Dynamixel XL330 servos.
**Trigger:** User wants to use RobotOS with unsupported hardware.

1. User boots RobotOS and connects Dynamixel U2D2 USB adapter.
2. System detects U2D2, identifies Dynamixel protocol, scans bus and finds 4 servos.
3. System reports: "Unknown robot configuration: 4x Dynamixel XL330 servos. No matching profile found."
4. User selects "Create Profile." System launches guided profile creation.
5. User specifies joint names, axis mappings, position limits, and default protection settings.
6. System saves the profile as a YAML file.
7. User can now calibrate and teleop their custom arm using the standard dashboard.

**Success:** Custom hardware operational with guided profile creation, no code changes required. [Traces to SC2, SC3]

### UJ5: Classroom Setup (Educator)

**Actor:** Teacher setting up 10 robot stations for a robotics class.
**Trigger:** Beginning of semester, 10 identical SO-101 kits, 10 different laptops.

1. Teacher creates one RobotOS USB with pre-configured SO-101 profile and calibration.
2. Teacher clones the USB image to 9 additional USB sticks.
3. Students insert USBs into their laptops (mixed Dell, HP, Lenovo hardware) and boot.
4. Each station auto-detects the connected SO-101 and applies the pre-loaded profile.
5. Students begin teleop within minutes, no per-station configuration needed.

**Success:** 10 stations operational in under 30 minutes total. All running identical, reproducible environments. [Traces to SC1, SC4, SC5]

## Domain Model

### Core Entities

**Robot:** A complete robotic system composed of one or more arms, each with a servo bus and optional cameras. Identified by a profile name (e.g., "SO-101", "Koch v1.1"). A robot has a calibration state, a protection configuration, and an operational mode (idle, teleop, data collection, replay).

**Arm:** A kinematic chain of servos connected via a single serial bus. Each arm has a role (leader or follower), a port assignment (e.g., /dev/ttyUSB0), and a set of named joints. An arm belongs to exactly one robot.

**Servo:** A single actuator identified by bus ID (1-6 typical). Each servo has readable registers: position, velocity, load, voltage, temperature, status flags. Each servo has writable registers: goal position, torque enable, protection thresholds (max temperature, max voltage, overload threshold). Servo protocol varies by manufacturer (Feetech STS3215, Dynamixel XL330, etc.).

**ServoProtocol:** An abstraction over manufacturer-specific communication protocols. Defines how to read/write registers, scan for devices, configure protection settings, and handle communication errors. Each protocol has a USB hardware identifier (vendor ID + product ID) used for auto-detection.

**Controller:** A USB-to-serial adapter that bridges the host computer to a servo bus. Identified by USB vendor/product ID (e.g., CH340 = 1a86:7523 for Feetech, FTDI = 0403:6014 for U2D2). A controller connects to exactly one arm.

**Camera:** A USB video device enumerated via V4L2. Each camera has a device path, resolution capabilities, and frame rate. Cameras are assigned to observation roles (e.g., "wrist_cam", "overhead_cam") within a robot profile.

**Profile:** A YAML file describing a complete robot configuration: number of arms, servos per arm, joint names, position limits, default protection settings, camera assignments, calibration procedure, and compatible servo protocols. Profiles are the unit of hardware portability.

**Calibration:** A stored mapping between servo register values and meaningful joint positions (degrees or radians). Generated per-arm through a guided homing procedure. Stored alongside the profile. Must be re-done when servos are replaced.

**Dataset:** A collection of recorded episodes in LeRobot format. Each episode contains timestamped servo positions and camera frames. Datasets are stored locally and can be uploaded to HuggingFace Hub for training.

### Entity Relationships

```
Profile 1---* Arm
Arm 1---1 Controller
Arm 1---* Servo
Servo *---1 ServoProtocol
Robot 1---1 Profile
Robot 1---* Camera
Robot 1---* Calibration
Robot 1---* Dataset
Controller 1---1 USB Port (auto-detected)
Camera 1---1 USB Port (auto-detected)
```

## Functional Requirements

### Hardware Detection and Configuration

- **FR1:** The system can detect USB-serial adapters (CH340, FTDI, CP2102) on connection and identify the associated servo protocol based on USB vendor/product ID.
- **FR2:** The system can scan a detected servo bus and enumerate all connected servos, reporting their IDs, firmware versions, and protocol type.
- **FR3:** The system can match a detected hardware configuration (servo count, protocol type, bus topology) against the installed profile library and suggest the best-matching robot profile.
- **FR4:** The system can detect USB cameras via V4L2 and enumerate their capabilities (resolutions, frame rates, device paths).
- **FR5:** The system can assign detected controllers and cameras to profile-defined roles (leader arm, follower arm, wrist camera, etc.) with user confirmation.
- **FR6:** The system can configure udev rules and serial port permissions automatically, without requiring manual terminal commands or root access from the user.

### Robot Profiles

- **FR7:** The system can load robot profiles from YAML files that describe arm configurations, joint names, position limits, protection settings, and camera assignments.
- **FR8:** Users can create new robot profiles through a guided workflow that captures joint count, naming, limits, and default settings.
- **FR9:** Users can export and import robot profiles as standalone files for sharing across RobotOS installations.
- **FR10:** The system ships with pre-built profiles for SO-101 (Feetech STS3215, 2x 6-DOF arms, leader-follower).
- **FR11:** The system can apply protection settings from a profile to all servos on the bus (max temperature, max voltage, overload threshold, overload duration).

### Calibration

- **FR12:** Users can calibrate each arm through a guided procedure that moves joints to reference positions and records the servo register values.
- **FR13:** The system can store and recall calibration data per arm, persisting across reboots.
- **FR14:** The system can validate stored calibration against current servo positions and warn if any joint deviates by more than 20% from its calibrated range, or if a servo fails to respond within 2 seconds (stale = no response for >2 seconds).

### Teleoperation

- **FR15:** Users can launch leader-follower teleoperation from the dashboard, mapping leader arm joint positions to follower arm goal positions in real time.
- **FR16:** The system can display live telemetry during teleoperation: per-servo voltage, current, load, temperature, and communication error count.
- **FR17:** The system can halt teleoperation automatically if any servo exceeds protection thresholds (temperature, voltage, load), displaying the specific fault.
- **FR18:** Users can configure teleoperation parameters (speed scaling, position offset, deadband) from the dashboard.

### Diagnostics and Monitoring

- **FR19:** Users can run a comprehensive hardware diagnostic that tests servo communication reliability, firmware version consistency, voltage stability, temperature baselines, and EEPROM configuration.
- **FR20:** Users can monitor all servo registers in real time with configurable refresh rate (1-50 Hz).
- **FR21:** The system can log diagnostic and monitoring data to CSV files with timestamps for post-session analysis.
- **FR22:** Users can run programmatic arm exercise routines that move each joint through its range to verify mechanical health.
- **FR23:** The system can detect and report specific fault conditions: voltage sag under load, communication timeouts, overload protection trips, temperature warnings.

### Data Collection

- **FR24:** Users can record teleoperation sessions as LeRobot-compatible datasets (servo positions + camera frames + timestamps).
- **FR25:** Users can specify task name, episode count, and camera configuration before starting a data collection session.
- **FR26:** Users can review, replay, and delete recorded episodes from the dashboard.
- **FR27:** The system can store datasets locally in LeRobot format, ready for training upload.

### OS and Boot

- **FR28:** The system can boot from USB on x86 UEFI-compatible hardware without requiring hard drive installation.
- **FR29:** The system can persist user data (profiles, calibrations, datasets, preferences) across reboots on the USB drive.
- **FR30:** The system can operate fully offline after initial USB creation -- no internet required for boot, detection, calibration, teleop, or data collection.
- **FR31:** Users can flash the OS image to a USB drive from Windows using a single-command script.
- **FR32:** Users can clone a configured USB image (with profiles and calibrations) to additional USB drives for fleet deployment.

### Dashboard

- **FR33:** Users can view system status (detected hardware, active profile, calibration state, servo health) from a central dashboard.
- **FR34:** Users can launch all primary workflows (calibrate, teleop, collect data, diagnose) from the dashboard without using the terminal.
- **FR35:** Users can view live camera feeds from detected USB cameras in the dashboard.
- **FR36:** The system displays actionable error messages with suggested fixes when hardware faults are detected.

### AI-Assisted Troubleshooting

- **FR37:** The system includes pre-seeded AI context files (CLAUDE.md, memory files) that enable Claude Code to diagnose and resolve hardware and configuration issues.
- **FR38:** Users can launch an AI troubleshooting session from the dashboard that provides Claude Code with current system state (detected hardware, recent errors, servo telemetry).

### Extensibility

- **FR39:** Developers can add support for new servo protocols by implementing a defined driver interface without modifying core system code.
- **FR40:** Developers can add new robot profiles by creating YAML files conforming to the profile schema, without modifying core system code.
- **FR41:** The system can load third-party profiles and drivers from a designated plugin directory.

### FR Dependency Chain

The following critical-path dependencies must be respected during implementation. An FR cannot be delivered until all of its upstream dependencies are complete.

```
FR1 (USB-serial detection)
  -> FR2 (bus scan)
    -> FR3 (profile matching)
      -> FR7 (load profiles)
        -> FR12 (calibration)
          -> FR15 (teleoperation)
            -> FR24 (data collection)
```

Additional dependency links:
- FR19 (diagnostics) depends on FR1, FR2
- FR36 (actionable errors) depends on FR23 (fault detection)
- FR4 (camera detection) is independent of the servo chain but required by FR24

## Non-Functional Requirements

### Performance

- **NFR1:** Teleoperation loop latency (leader position read to follower position write) shall not exceed 20ms for 95th percentile, as measured by internal timing instrumentation.
- **NFR2:** Servo bus scan (enumerate all servos on a single bus) shall complete within 3 seconds for up to 12 servos, as measured from scan initiation to result display.
- **NFR3:** Hardware auto-detection (USB device enumeration + profile matching) shall complete within 5 seconds of device connection, as measured from USB hotplug event to dashboard notification.
- **NFR4:** Dashboard shall render live telemetry updates at 10 Hz or higher without frame drops, as measured by dashboard frame rate counter.
- **NFR5:** Boot time from USB power-on to dashboard ready shall not exceed 90 seconds on hardware meeting minimum specifications, as measured by systemd-analyze.

### Reliability

- **NFR6:** The system shall recover from transient servo communication failures (single dropped packet) without interrupting teleoperation, using automatic retry with a maximum of 3 attempts per read cycle.
- **NFR7:** The system shall detect and report servo bus disconnection within 2 seconds, as measured from physical disconnection to dashboard alert.
- **NFR8:** Data collection sessions shall not lose recorded episodes due to system errors -- each episode shall be flushed to disk before the next begins.
- **NFR9:** The system shall survive unexpected power loss without corrupting the USB filesystem, using journaling or copy-on-write filesystem strategies.
- **NFR10:** The OS image shall boot successfully on 90% or more of x86 UEFI-compatible hardware manufactured after 2016, validated against a test matrix of 20+ models.

### Usability

- **NFR11:** All primary workflows (calibrate, teleop, collect data, diagnose) shall be completable without terminal access, requiring no more than 5 user actions from dashboard launch to workflow execution.
- **NFR12:** Error messages shall include: (a) what failed, (b) probable cause, and (c) suggested remediation, in language understandable to users without Linux or robotics experience.
- **NFR13:** The dashboard shall be operable via keyboard, mouse, or touchscreen without requiring specialized input devices.

### Portability

- **NFR14:** The USB image shall fit on a 32GB or larger USB 3.0 drive, with the base OS image not exceeding 16GB.
- **NFR15:** The system shall operate on x86_64 CPUs with integrated graphics (no discrete GPU required). Minimum specification: Intel Core i5 6th generation or AMD Ryzen 3 1st generation, 8GB RAM.
- **NFR16:** All runtime dependencies shall be pre-installed on the USB image. No package downloads shall be required during normal operation.

### Maintainability

- **NFR17:** Robot profiles shall be human-readable YAML files, editable with any text editor, and validate against a published JSON schema.
- **NFR18:** Servo protocol drivers shall conform to a documented interface with fewer than 15 required methods, enabling a new protocol implementation in under 500 lines of code.
- **NFR19:** The system shall log all hardware events (connect, disconnect, fault, recovery) to a structured log file queryable by timestamp and severity.

### Security

- **NFR20:** The system shall not require or enable network services by default. No listening ports shall be open on a fresh boot.
- **NFR21:** Servo bus access shall be restricted to the `robotos` group via udev rules using `MODE="0660"` and `GROUP="robotos"`. The default RobotOS user shall be a member of the `robotos` group. No world-writable serial device nodes.
- **NFR22:** The AI troubleshooting context shall not contain or transmit user data beyond the local machine without explicit user action (e.g., manual upload to HuggingFace Hub).

## Technical Constraints

- **TC1: No GPU dependence.** The baseline target hardware is Intel integrated graphics. All compute-intensive training must be offloaded. The system is for inference, data collection, and teleoperation only.
- **TC2: USB boot required.** The system must boot and operate entirely from a USB drive. Hard drive installation is optional, never required.
- **TC3: Offline operation.** After initial USB creation, all core functionality must work without internet. Internet is optional for AI assistant features and dataset upload.
- **TC4: Python-based.** The robot API, diagnostic tools, and dashboard must be implemented in Python for maximum community accessibility. System-level components (boot, udev) may use bash.
- **TC5: LeRobot compatibility.** The universal robot API must remain compatible with LeRobot v0.5.0+ data formats and collection pipelines. RobotOS is a platform for LeRobot, not a replacement.
- **TC6: Open source.** All components must be open source. No proprietary dependencies for core functionality. Claude Code integration is optional (AI-assisted troubleshooting is a convenience, not a requirement).
- **TC7: x86_64 only.** ARM support (Raspberry Pi, Jetson) is out of scope for v1.0. The USB boot architecture targets x86_64 UEFI systems.
- **TC8: Single-user system.** RobotOS runs as a single-user desktop OS on the host machine. Multi-user, networked, or remote operation is out of scope for v1.0.

## MVP Scope vs Future Phases

### MVP (v0.1) Includes

- Pre-built bootable USB image with Ubuntu 24.04 LTS base
- Feetech STS3215 servo protocol driver (existing code, hardened)
- SO-101 robot profile (2x 6-DOF arms, leader-follower)
- USB-serial auto-detection for CH340 adapters
- USB camera detection via V4L2
- Existing diagnostic suite integrated as system commands
- TUI-based launcher menu (calibrate, teleop, diagnose, monitor)
- LeRobot v0.5.0 pre-installed
- Calibration persistence across reboots
- Claude Code context files pre-seeded
- flash.ps1 updated to write pre-built image instead of Ubuntu ISO

Functional requirements in MVP: FR1 (CH340 only), FR2, FR3 (single-profile matching for SO-101), FR4, FR6, FR7, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR19, FR20, FR21, FR22, FR23, FR24, FR25, FR27, FR28, FR29, FR30, FR31, FR33 (TUI version), FR34 (TUI version), FR36, FR37.

Note: FR3 is limited to single-profile matching (SO-101 only) in MVP; full multi-profile matching is Growth. FR4 provides camera detection; FR5 (user-confirmed role assignment) is deferred -- MVP auto-assigns the first detected camera. FR14 (calibration validation) is pulled into MVP to support the calibrate workflow in Story 3.4.

### MVP Excludes (Deferred)

- Dynamixel protocol support (Growth phase)
- Koch and Aloha profiles (Growth phase)
- Web-based dashboard (Vision phase)
- Robot profile creation wizard (Growth phase)
- Profile export/import and sharing (Growth phase)
- Dataset review and replay in dashboard (Growth phase)
- Plugin directory for third-party drivers (Vision phase)
- AI troubleshooting with live system state injection (Vision phase)
- USB image cloning tool (Growth phase)
- Custom arm profile creation (Growth phase)

## Success Metrics

| Metric | Target | Measurement Method | Traces To |
|--------|--------|--------------------|-----------|
| Time to first teleop (new user, known hardware) | Under 5 minutes | Timed user test from USB boot to first leader-follower movement | SC1 |
| Supported robot platforms | 3+ by v1.0 | Count of shipped, tested profiles | SC2 |
| Supported servo protocols | 3+ by v1.0 | Count of implemented, tested protocol drivers | SC3 |
| Terminal commands for basic operation | 0 | User test: complete calibrate + teleop workflow without terminal | SC4 |
| Hardware compatibility rate | 90%+ of tested models | Boot test matrix: 20+ x86 laptops/desktops | SC5 |
| GitHub stars (6 months post-launch) | 100+ | GitHub repository metrics | SC6 |
| Fault detection latency | Under 2 seconds | Instrumented test: disconnect servo, measure time to alert | SC7 |
| Offline operation coverage | 100% of core workflows | Airplane mode test: boot, detect, calibrate, teleop, collect | SC8 |

---

_Product Requirements Document for RobotOS USB -- a universal robot operating system on a bootable USB stick._
