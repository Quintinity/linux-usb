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
  - step-13-consolidation
inputDocuments:
  - product-brief.md
  - project-overview.md
  - README.md
  - CLAUDE.md
  - prd-enhancements.md
  - review-pm.md
  - review-qa.md
  - strategy-content-enhancements.md
workflowType: 'prd'
---

# Product Requirements Document - armOS USB

**Author:** Bradley
**Date:** 2026-03-15
**Version:** 2.0 (Consolidated -- integrates PM enhancements, QA fixes, competitive positioning, and expanded metrics)

## Executive Summary

armOS USB transforms a bootable Linux USB stick into a universal robot operating system. Users plug the USB into any x86 computer, boot it, connect supported robotic hardware, and have a working robot control station in minutes -- no Linux expertise, no manual configuration, no internet required after first setup.

The project evolves from an existing single-purpose tool (Surface Pro 7 + SO-101 setup automation) into a hardware-agnostic robotics platform. It preserves the proven AI-driven setup pipeline (Claude Code + CLAUDE.md) and comprehensive servo diagnostic suite while adding hardware auto-detection, a universal robot API, and plug-and-play robot profiles.

**Differentiator:** Zero-config, USB-bootable, AI-assisted robotics OS that works on commodity x86 hardware. No GPU required. No cloud dependency for operation. Bridges the gap between complex ROS2 setups and bare-metal LeRobot installs.

**Target users:** Robotics hobbyists, AI researchers collecting training data, educators teaching physical robotics, and makers building custom robot platforms.

**Competitive position:** armOS owns the "low complexity, affordable hardware" quadrant. phosphobot requires $995+ kits and cloud connectivity. ROS2 requires a PhD-level tolerance for configuration. LeRobot (bare) requires a working Linux environment. armOS is the only product where you insert a USB stick and have a working robot in 5 minutes.

## Competitive Positioning

### Feature Comparison

| Capability | armOS | Foxglove | ROS2 + MoveIt2 | LeRobot (bare) | phosphobot | NVIDIA Isaac |
|---|---|---|---|---|---|---|
| **Setup time** | <5 min (USB boot) | 15-30 min (install) | 4-8 hours | 1-3 hours | 30-60 min (their kit) | 2-4 hours (GPU required) |
| **Target hardware cost** | $0 (any x86 laptop) | $0 (any machine) | $0 (any machine) | $0 (any machine) | $995+ (their kits) | $500+ (needs NVIDIA GPU) |
| **Robot arm support** | SO-101 (MVP), Dynamixel (Growth) | N/A (viz only) | 50+ (URDF-based) | SO-101, Koch, Aloha | SO-100, SO-101, Unitree Go2 | Industrial arms |
| **Servo diagnostics** | Real-time voltage, temp, load, comms | Log replay only | No built-in for hobby servos | None | Basic status | Industrial-grade |
| **Data collection** | Built-in (LeRobot format) | No | Rosbag (different format) | Built-in (native) | Built-in | SIM-focused |
| **Cloud training** | Planned (Year 2) | No | No | HuggingFace Hub | PRO subscription | Omniverse |
| **Offline operation** | Full (after first boot) | Partial | Full | Full | Requires internet for cloud | Partial |
| **License** | Apache 2.0 (planned) | Freemium ($18-90/user/mo) | Apache 2.0 | Apache 2.0 | Proprietary + open agent | Proprietary |
| **Primary user** | Hobbyist, educator, new researcher | Robotics engineer | Robotics engineer, researcher | ML researcher | Hobbyist, educator | Enterprise, researcher |

### Head-to-Head: armOS vs. phosphobot

| Dimension | armOS | phosphobot | Verdict |
|---|---|---|---|
| Price to start | Free (download ISO) | $995+ (buy their kit) | armOS wins |
| Hardware lock-in | None (BYOH) | Their kits preferred | armOS wins |
| VR teleoperation | No | Meta Quest support | phosphobot wins |
| Servo diagnostics | Deep (voltage, temp, load, comms) | Basic | armOS wins |
| Cloud training | Planned | Available now (PRO tier) | phosphobot wins (for now) |
| Community size | 0 (pre-launch) | 1,000+ claimed robots | phosphobot wins (for now) |
| Offline capability | Full | Internet required for cloud | armOS wins |
| Open source depth | Full OS + drivers + diagnostics | Open agent, closed platform | armOS wins |

**Positioning statement:** phosphobot sells a vertically integrated platform -- their hardware, their software, their cloud. armOS is the horizontal layer -- it works with any hardware, on any laptop, for free. We are the Android to their iPhone. They will capture the high end; we will capture the long tail.

### HuggingFace/Pollen Robotics Acquisition

HuggingFace acquired Pollen Robotics and released Reachy Mini and HopeJr. This is both an opportunity and a risk.

**Risk:** HuggingFace could build their own "LeRobot OS" backed by their 22k-star community and $4.5B valuation.

**Mitigation:** Position armOS as the *community* deployment tool for LeRobot, not a competitor to HuggingFace's own hardware. Engage the LeRobot team immediately. Upstream patches. The ideal outcome is a mention in LeRobot's README.

**Opportunity:** armOS profiles for Reachy Mini and HopeJr could make us a natural partner rather than a competitor.

## Success Criteria

- **SC1:** A new user boots the USB on untested x86 hardware and reaches working robot teleoperation in under 5 minutes (excluding first-time calibration), measured from BIOS boot to first successful leader-follower movement with pre-existing calibration.
- **SC2:** The system supports 3 or more robot arm platforms (SO-101, Koch v1.1, Aloha) with pre-configured profiles by v1.0 release.
- **SC3:** The system supports 3 or more servo protocols (Feetech STS3215, Dynamixel XL330, Dynamixel XL430) by v1.0 release.
- **SC4:** Zero manual terminal commands are required for basic operation (boot, detect hardware, calibrate, teleop, collect data) -- all accessible through a dashboard interface.
- **SC5:** The OS image boots successfully on 90% or more of tested x86 laptops and desktops (target: 20+ distinct hardware models validated).
- **SC6:** Community adoption reaches 500+ GitHub stars within 6 months of public release.
- **SC7:** Servo diagnostic suite detects and reports hardware faults (voltage sag, overload, communication failure) within 2 seconds of occurrence.
- **SC8:** Offline operation is fully functional after initial USB creation -- no internet required for boot, hardware detection, calibration, teleoperation, or data collection.
- **SC9:** Active users (booted armOS and completed teleop at least once) reach 50+ within 6 months, tracked via opt-in telemetry or self-reported survey.
- **SC10:** USB image downloads reach 1,000+ within 6 months, measured via GitHub release download count.
- **SC11:** Community-contributed robot profiles reach 5+ within 12 months.
- **SC12:** At least 1 university pilot deployment within 12 months (target: Georgia Tech ECE 4560 or equivalent).
- **SC13:** At least 1 signed hardware partnership LOI within 12 months (target: Seeed Studio).
- **SC14:** armOS USB distributed at 3+ hackathon events within 12 months.
- **SC15:** 10+ users completing cloud training runs within 15 months of launch.
- **SC16:** $1K monthly recurring revenue within 18 months (sources: cloud training + education pilot + USB sales).

## Product Scope

### MVP (v0.1) -- Single-Platform Stabilization

Harden the existing Surface Pro 7 + SO-101 pipeline into a reproducible, pre-built OS image. Eliminate the multi-phase AI-driven install by shipping a fully configured image.

- Pre-built bootable USB image (no install-from-live-USB required)
- Feetech STS3215 auto-detection and udev configuration on boot
- Existing diagnostic suite (diagnose_arms.py, monitor_arm.py, exercise_arm.py, teleop_monitor.py) accessible from a terminal menu
- LeRobot v0.5.0 pre-installed with SO-101 profile
- USB camera detection and V4L2 configuration
- Data collection pipeline for recording LeRobot-compatible datasets (P0 -- critical for AI researcher persona)
- Claude Code context files pre-seeded for AI-assisted troubleshooting
- Hackathon Mode -- streamlined first-run flow that skips advanced options (FR48)
- Demo Mode -- pre-loaded SO-101 replay trajectories for demos without trained policies (FR49)
- "What's Next?" onboarding panel with links to resources and next steps (FR54)
- Demo Mode launcher in TUI dashboard (FR66)

**MVP Functional Requirements:** FR1 (CH340 only), FR2, FR3 (single-profile matching for SO-101), FR4, FR6, FR7, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR19, FR20, FR21, FR22, FR23, FR24, FR25, FR27, FR28, FR29, FR30, FR31, FR33 (TUI version), FR34 (TUI version), FR36, FR37, FR42, FR43, FR44, FR48, FR49, FR54, FR66.

### Growth (v0.5) -- Multi-Hardware Support

Extend beyond SO-101 to support multiple robot platforms and host hardware.

- Hardware auto-detection layer (USB device enumeration, servo protocol identification, camera enumeration)
- Robot profile system (YAML-based hardware descriptions for SO-101, Koch v1.1)
- Universal robot API abstracting Feetech and Dynamixel protocols
- Full-featured TUI dashboard with real-time telemetry, multi-robot support, and advanced configuration
- Support for 5+ x86 hardware targets (not just Surface Pro 7)
- Plugin architecture for adding new servo protocols
- Fleet Mode image export with locked-down classroom configuration (FR45, FR47)
- Fleet Dashboard for local network station monitoring (FR46)
- One-click dataset upload to armOS Cloud or HuggingFace Hub (FR50)
- One-click policy download and deployment (FR51)
- Co-branded boot splash configurable per hardware partner (FR52)
- Partner quickstart URL embedded in boot splash (FR53)
- Opt-in telemetry consent and anonymous reporting (FR55, FR56, FR57)
- Dataset export to HuggingFace Hub with zero-config flow (FR59)
- armOS Cloud training submission from dashboard (FR60)
- Policy deployment from cloud (FR61)
- Profile export as .armos file and import from file or URL (FR62, FR63)
- Screen recording integration (FR67)
- Reachy Mini and HopeJr robot profiles (FR68, contingent on partnership)

**Growth Functional Requirements:** FR5, FR8, FR9, FR18, FR26, FR32, FR35, FR38, FR39, FR40, FR45, FR46, FR47, FR50, FR51, FR52, FR53, FR55, FR56, FR57, FR58, FR59, FR60, FR61, FR62, FR63, FR67, FR68.

### Vision (v1.0) -- Universal Robot OS

Full platform with broad hardware support, community ecosystem, and zero-config operation.

- Web-based dashboard for robot control and monitoring
- 3+ robot arm profiles with auto-detection
- 3+ servo protocol drivers
- Community profile repository (users contribute hardware profiles)
- Offline AI assistant for troubleshooting and guided calibration
- One-click cloud training upload integration
- Community profile browser and contribution workflow (FR64, FR65)
- Pro tier feature gating for power users (FR69)

**Vision Functional Requirements:** FR41, FR64, FR65, FR69.

## User Journeys

### UJ1: First-Time Boot (Hobbyist)

**Actor:** Robotics hobbyist with an SO-101 kit and a laptop.
**Trigger:** User has flashed armOS USB and wants to control their robot.

1. User inserts USB into laptop and boots from USB via BIOS boot menu.
2. System boots to armOS desktop or dashboard within 90 seconds.
3. User connects SO-101 servo controller via USB.
4. System detects Feetech CH340 USB-serial adapter, identifies it as a servo controller, and loads the Feetech STS3215 driver.
5. System scans the servo bus, discovers 6 servos per arm, and matches the configuration to the SO-101 robot profile.
6. Dashboard displays detected hardware: "SO-101 Leader Arm (6 servos) + SO-101 Follower Arm (6 servos)."
7. User selects "Calibrate" from the dashboard. System guides user through homing each joint.
8. User selects "Teleop." System launches leader-follower teleoperation. User moves the leader arm and the follower arm mirrors movements.

**Success:** Boot to teleop in under 5 minutes (with pre-existing calibration). No terminal commands. [Traces to SC1, SC4]

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
**Trigger:** User wants to use armOS with unsupported hardware.

1. User boots armOS and connects Dynamixel U2D2 USB adapter.
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

1. Teacher creates one armOS USB with pre-configured SO-101 profile and calibration.
2. Teacher clones the USB image to 9 additional USB sticks.
3. Students insert USBs into their laptops (mixed Dell, HP, Lenovo hardware) and boot.
4. Each station auto-detects the connected SO-101 and applies the pre-loaded profile.
5. Students begin teleop within minutes, no per-station configuration needed.

**Success:** 10 stations operational in under 30 minutes total. All running identical, reproducible environments. [Traces to SC1, SC4, SC5]

### UJ6: Educator Deploying 30 Arms (Classroom Fleet)

**Actor:** University instructor setting up a robotics lab for ECE 4560 (like Georgia Tech).
**Context:** The education market is $1.8B and growing at 18.1% CAGR. This journey must be frictionless enough for a TA to execute, not just the professor.

1. Instructor downloads the armOS image and flashes one USB stick.
2. Instructor boots one station, connects an SO-101, runs calibration, and verifies teleop works.
3. Instructor opens "Fleet Mode" from the TUI: exports the current profile + calibration + a locked-down configuration (no terminal access, restricted menus) as a clonable image.
4. TA uses a batch cloning tool to flash 29 additional USB sticks from the master image.
5. On lab day, 30 students insert USB sticks into 30 different laptops. Each boots to a branded splash screen showing the course name and lab number.
6. Each station auto-detects its SO-101. Because the profile is pre-loaded, students skip profile matching and go straight to "Calibrate" (each physical arm needs its own calibration, but the workflow is guided and takes under 3 minutes).
7. Instructor's station shows a "Fleet Dashboard" -- a simple grid of station status: booted, calibrating, teleoping, error. Requires local network (DHCP on a lab switch). No internet required.
8. When a student's station shows an error, the fleet dashboard surfaces the diagnostic message (e.g., "Station 14: Servo 3 voltage sag -- check power supply").
9. At end of semester, instructor collects all USB sticks. Student data is on the sticks. No data leaves the lab network.

**New FRs:** FR45 (Fleet Mode image export), FR46 (Fleet Dashboard), FR47 (Locked-down classroom configuration).
**Phase:** Fleet Dashboard is Growth (v0.5). Image cloning and locked-down config should be pulled into late MVP or v0.1.1.
**Success:** 30 stations operational in under 60 minutes (2 minutes per station average). Instructor can monitor all stations from one screen. [Traces to SC5, SC12]

### UJ7: Hackathon Participant (Zero to Demo in 2 Hours)

**Actor:** One of the 3,000+ LeRobot hackathon participants who just received an SO-101 kit at a hackathon venue.
**Context:** The LeRobot hackathon across 100+ cities is the single largest concentration of our target users.

1. Participant receives an SO-101 kit and an armOS USB stick (distributed by event organizers or downloaded from armOS.dev QR code).
2. Participant plugs USB into their personal laptop (unknown hardware).
3. System boots. If boot fails, the boot splash shows a "press [key] for boot menu" message tailored to the top 5 laptop brands detected from SMBIOS data.
4. Hardware is detected. System enters "Hackathon Mode" -- a streamlined flow that skips advanced options and goes straight to: Calibrate > Teleop > Collect Data.
5. After 30 minutes of data collection, participant wants to train a policy. System shows: "Training requires a GPU. Upload your dataset to armOS Cloud or HuggingFace Hub." One-click upload (requires WiFi).
6. While waiting for training, participant explores "Demo Mode" -- pre-loaded example policies that show what a trained arm can do (replay of pick-and-place, wave, or sorting tasks using pre-recorded trajectories).
7. Training completes. Participant downloads the policy, loads it via the dashboard, and runs inference.
8. Participant shares their profile + trained policy to the armOS community hub with one click.

**New FRs:** FR48 (Hackathon Mode), FR49 (Demo Mode), FR50 (One-click dataset upload), FR51 (One-click policy download).
**Phase:** Hackathon Mode (FR48) and Demo Mode (FR49) are MVP. Cloud upload/download (FR50, FR51) is Growth, with placeholder UI in MVP.
**Success:** Participant goes from unboxing to autonomous policy execution in under 2 hours. Zero terminal commands. [Traces to SC1, SC14]

### UJ8: Seeed Studio Customer Unboxing

**Actor:** Customer who just received an SO-101 Pro kit ($240) from Seeed Studio, with an armOS USB stick included in the box.
**Context:** This is the hardware partnership revenue model ($3-5 per USB stick).

1. Customer opens the SO-101 Pro box. Inside: servo kit, cables, screws, 3D printed parts, and a small armOS USB stick in a branded sleeve with a QR code.
2. QR code links to armOS.dev/seeed-quickstart -- a single page with a 90-second video and three steps: assemble, plug in USB, boot and connect.
3. Customer assembles the arm following Seeed's existing assembly guide.
4. Customer plugs the armOS USB into their laptop and boots.
5. System boots to a Seeed-cobranded splash screen ("Powered by armOS -- Seeed Studio SO-101 Edition").
6. System detects the SO-101 hardware. The SO-101 profile is pre-loaded and pre-selected.
7. Guided calibration walks the customer through homing each joint with visual diagrams.
8. Customer completes calibration, starts teleop, and moves the arm within 5 minutes of first boot.
9. Dashboard shows a "What's Next?" panel: links to the HuggingFace robotics course, the armOS community Discord, and the armOS Cloud training service.

**New FRs:** FR52 (Co-branded boot splash), FR53 (Partner quickstart URL), FR54 ("What's Next?" onboarding panel).
**Phase:** Co-branding (FR52, FR53) is Growth. "What's Next?" panel (FR54) is MVP for all users.
**Success:** Seeed customer reaches teleop in under 5 minutes. Seeed support tickets for SO-101 setup drop by 50%+. [Traces to SC1, SC13]

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
- **FR6:** The system can configure udev rules and serial port permissions automatically, without requiring manual terminal commands or root access from the user. Permissions use `MODE="0660"` and `GROUP="armos"`, not world-writable `0666`.

### Robot Profiles

- **FR7:** The system can load robot profiles from YAML files that describe arm configurations, joint names, position limits, protection settings, and camera assignments.
- **FR8:** Users can create new robot profiles through a guided workflow that captures joint count, naming, limits, and default settings.
- **FR9:** Users can export and import robot profiles as standalone files for sharing across armOS installations.
- **FR10:** The system ships with pre-built profiles for SO-101 (Feetech STS3215, 2x 6-DOF arms, leader-follower).
- **FR11:** The system can apply protection settings from a profile to all servos on the bus (max temperature, max voltage, overload threshold, overload duration).

### Calibration

- **FR12:** Users can calibrate each arm through a guided procedure that moves joints to reference positions and records the servo register values.
- **FR13:** The system can store and recall calibration data per arm, persisting across reboots.
- **FR14:** The system can validate stored calibration against current servo positions and warn if any joint deviates by more than 20% of its calibrated range width, or if a servo fails to respond within 2 seconds (stale = no response for >2 seconds).

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

### Safety

- **FR42:** The teleop watchdog shall disable follower torque if the control loop stalls for more than 500ms, preventing unsafe motion from stale commands.

### First-Run Experience

- **FR43:** A first-run setup wizard shall auto-detect connected hardware and guide the user through initial calibration on first boot.
- **FR44:** A Plymouth boot splash shall hide Linux boot messages, presenting a branded boot screen to the user.

### Fleet and Classroom

- **FR45:** The system can export a Fleet Mode image containing the current profile, calibration, and a locked-down configuration (restricted menus, no terminal access) as a clonable image.
- **FR46:** The system can display a Fleet Dashboard showing station status (booted, calibrating, teleoping, error) for all armOS stations on the local network via DHCP. No internet required.
- **FR47:** The system supports a locked-down classroom configuration that restricts menus and disables terminal access for student deployments.

### Hackathon and Demo

- **FR48:** The system provides a Hackathon Mode -- a streamlined first-run flow that skips advanced options and guides users directly through: Calibrate > Teleop > Collect Data.
- **FR49:** The system ships with 2-3 pre-recorded SO-101 demo trajectories (wave, pick-and-place, point-to-point) that can be replayed without a trained policy or leader arm.
- **FR50:** Users can upload a locally collected dataset to armOS Cloud or HuggingFace Hub with one click from the dashboard.
- **FR51:** Users can download a trained policy from armOS Cloud and load it for inference from the dashboard, with hardware compatibility verification before execution.

### Hardware Partnerships

- **FR52:** The system supports a co-branded boot splash configurable per hardware partner (e.g., "Powered by armOS -- Seeed Studio SO-101 Edition").
- **FR53:** The system can embed a partner quickstart URL in the boot splash, linking to partner-specific setup documentation.
- **FR54:** The dashboard includes a "What's Next?" onboarding panel with configurable links (HuggingFace course, community Discord, cloud training, partner-specific content).

### Telemetry (Opt-In)

- **FR55:** The first-run wizard includes a clear, plain-language telemetry opt-in screen. Default is OFF. Users can change their preference at any time from the dashboard settings.
- **FR56:** When opted in, the system sends a single anonymous HTTP POST on each successful boot: hardware model (SMBIOS), boot time, kernel version, detected USB devices. No user identifier.
- **FR57:** When opted in, the system can upload anonymized diagnostic results (servo health summary, fault types, communication reliability scores) to a central aggregation service.
- **FR58:** An internal telemetry dashboard aggregates telemetry data for maintainers: boot success rates by hardware model, most common faults, profile usage distribution.

### Cloud Training

- **FR59:** Users can push a locally collected dataset to their HuggingFace account with one command or dashboard button, with guided HF CLI login flow.
- **FR60:** Users can submit a dataset to the armOS Cloud training service from the dashboard: select dataset, choose model architecture (ACT, Diffusion Policy), confirm pricing, upload, receive notification when complete, download trained policy.
- **FR61:** Users can download a trained policy from armOS Cloud and load it for inference from the dashboard. The system verifies hardware compatibility before attempting to run.

### Profile Sharing

- **FR62:** Users can export their robot profile (YAML + calibration data + custom protection settings) as a single .armos file (zip archive) shareable via email, Discord, or USB.
- **FR63:** Users can import a .armos profile file from local storage or a URL. The system validates the profile against the schema before importing.
- **FR64:** The dashboard includes a "Community Profiles" section that lists profiles from a central GitHub-backed repository. Users can browse, search by robot type or servo protocol, and install with one click.
- **FR65:** Users can submit their profile to the community repository directly from the dashboard, creating a GitHub PR with the profile YAML, an optional hardware photo, and diagnostic test results.

### Demo and Marketing

- **FR66:** The TUI dashboard includes a prominent "Demo" button. When pressed with hardware connected, it replays pre-loaded trajectories. When pressed without hardware, it plays a video of the trajectories.
- **FR67:** Users can record a screen capture of their armOS session (TUI + camera feeds) with one keypress. Output is an MP4 file on the USB.

### Additional Robot Profiles

- **FR68:** The system includes Reachy Mini and HopeJr robot profiles (contingent on HuggingFace partnership).

### Monetization

- **FR69:** The system supports a Pro tier feature gating mechanism. The free tier includes everything in MVP. The Pro tier adds power-user features (advanced diagnostics, priority cloud training queue, profile analytics) without affecting the core experience.

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
- FR48 (Hackathon Mode) depends on FR43 (first-run wizard)
- FR49 (Demo Mode) depends on FR7 (profile loading) -- trajectories reference profile joint definitions
- FR50 (dataset upload) depends on FR27 (dataset storage)
- FR62 (profile export) depends on FR7 (profile loading) and FR13 (calibration storage)

### FR Phase Summary

| Phase | Functional Requirements |
|-------|------------------------|
| **MVP (v0.1)** | FR1 (CH340 only), FR2, FR3 (SO-101 only), FR4, FR6, FR7, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR19, FR20, FR21, FR22, FR23, FR24, FR25, FR27, FR28, FR29, FR30, FR31, FR33 (TUI), FR34 (TUI), FR36, FR37, FR42, FR43, FR44, FR48, FR49, FR54, FR66 |
| **Late MVP / v0.1.1** | FR59 |
| **Growth (v0.5)** | FR5, FR8, FR9, FR18, FR26, FR32, FR35, FR38, FR39, FR40, FR45, FR46, FR47, FR50, FR51, FR52, FR53, FR55, FR56, FR57, FR58, FR60, FR61, FR62, FR63, FR67, FR68 |
| **Vision (v1.0)** | FR41, FR64, FR65, FR69 |

## Non-Functional Requirements

### Performance

- **NFR1:** Teleoperation loop latency (leader position read to follower position write) shall not exceed 20ms for 95th percentile, as measured by internal timing instrumentation.
- **NFR2:** Servo bus scan (enumerate all servos on a single bus) shall complete within 3 seconds for up to 12 servos, as measured from scan initiation to result display.
- **NFR3:** Hardware auto-detection (USB device enumeration + profile matching) shall complete within 5 seconds of device connection, as measured from USB hotplug event to dashboard notification.
- **NFR4:** Dashboard shall render live telemetry updates at 10 Hz or higher without frame drops, as measured by dashboard frame rate counter.
- **NFR5:** Boot time from USB power-on to dashboard ready shall not exceed 90 seconds on hardware meeting minimum specifications, as measured by systemd-analyze.

### Reliability

- **NFR6:** The system shall recover from transient servo communication failures (single dropped packet) without interrupting teleoperation, using automatic retry with up to 10 retries per read cycle (proven working value from teleop patches).
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
- **NFR21:** Servo bus access shall be restricted to the `armos` group via udev rules using `MODE="0660"` and `GROUP="armos"`. The default armOS user shall be a member of the `armos` group. No world-writable serial device nodes.
- **NFR22:** The AI troubleshooting context shall not contain or transmit user data beyond the local machine without explicit user action (e.g., manual upload to HuggingFace Hub).

## Technical Constraints

- **TC1: No GPU dependence.** The baseline target hardware is Intel integrated graphics. All compute-intensive training must be offloaded. The system is for inference, data collection, and teleoperation only.
- **TC2: USB boot required.** The system must boot and operate entirely from a USB drive. Hard drive installation is optional, never required.
- **TC3: Offline operation.** After initial USB creation, all core functionality must work without internet. Internet is optional for AI assistant features, telemetry, and dataset upload.
- **TC4: Python-based.** The robot API, diagnostic tools, and dashboard must be implemented in Python for maximum community accessibility. System-level components (boot, udev) may use bash.
- **TC5: LeRobot compatibility.** The universal robot API must remain compatible with LeRobot v0.5.0+ data formats and collection pipelines. armOS is a platform for LeRobot, not a replacement. Pin to exact version (0.5.0) to avoid untested upgrades.
- **TC6: Open source.** All components must be open source. No proprietary dependencies for core functionality. Claude Code integration is optional (AI-assisted troubleshooting is a convenience, not a requirement).
- **TC7: x86_64 only.** ARM support (Raspberry Pi, Jetson) is out of scope for v1.0. The USB boot architecture targets x86_64 UEFI systems.
- **TC8: Single-user system.** armOS runs as a single-user desktop OS on the host machine. Multi-user, networked, or remote operation is out of scope for v1.0.

## Go-to-Market Requirements

### Demo Mode (MVP)

The 90-second demo video is the single highest-leverage marketing asset. Demo Mode makes every armOS installation a potential demo.

- **FR49:** Pre-loaded demo trajectories ship with MVP (2-3 SO-101 trajectories: wave, pick-and-place, point-to-point). These are recorded servo position sequences, not ML policies.
- **FR66:** Demo Mode launcher provides a prominent "Demo" button on the TUI dashboard. Works with or without hardware connected.
- **FR67:** Screen recording integration (Growth) enables users to share their experience on social media.

### Landing Page Requirements

- **GTM-1: Landing page at armOS.dev.** Single page with: hero video (90-second boot-to-teleop), three value props (zero setup / built-in diagnostics / works on any laptop), download button, hardware compatibility list, "Star us on GitHub" CTA.

- **GTM-2: SEO content strategy.** Three blog posts targeting specific search queries:
  1. "brltty stealing serial ports on Ubuntu" -- targets the #1 pain point.
  2. "SO-101 servo stuttering fix" -- targets power supply and overload issues.
  3. "LeRobot setup guide 2026" -- targets the broadest query.

- **GTM-3: 90-second video.** Continuous take, no narration, timer in corner. USB inserted > boot > detect > calibrate > teleop. Real hardware, no cuts.

- **GTM-4: Hackathon distribution kit.** Downloadable package for organizers: USB image, one-page printed quickstart (PDF), table tent with QR code, and opening presentation slide deck. Targets 3,000+ LeRobot hackathon participants across 100+ cities.

**Phase:** GTM-1 and GTM-3 are pre-launch. GTM-2 starts during development. GTM-4 is Growth, but the quickstart PDF should be drafted during MVP.

## Success Metrics

| Metric | Target | Measurement Method | Traces To |
|--------|--------|--------------------|-----------|
| Time to first teleop (new user, known hardware, pre-calibrated) | Under 5 minutes | Timed user test from USB boot to first leader-follower movement (excludes first-time calibration) | SC1 |
| Supported robot platforms | 3+ by v1.0 | Count of shipped, tested profiles | SC2 |
| Supported servo protocols | 3+ by v1.0 | Count of implemented, tested protocol drivers | SC3 |
| Terminal commands for basic operation | 0 | User test: complete calibrate + teleop workflow without terminal | SC4 |
| Hardware compatibility rate | 90%+ of tested models | Boot test matrix: 20+ x86 laptops/desktops, start testing Sprint 4 | SC5 |
| GitHub stars (6 months post-launch) | 500+ | GitHub repository metrics | SC6 |
| Fault detection latency | Under 2 seconds | Instrumented test: disconnect servo, measure time to alert | SC7 |
| Offline operation coverage | 100% of core workflows | Airplane mode test: boot, detect, calibrate, teleop, collect | SC8 |
| Active users (6 months) | 50+ | Opt-in telemetry or self-reported survey (booted + completed teleop) | SC9 |
| USB image downloads (6 months) | 1,000+ | GitHub release download count | SC10 |
| Community-contributed profiles (12 months) | 5+ | Count of merged community profile PRs | SC11 |
| Education pilots (12 months) | 1+ university | Signed pilot agreement | SC12 |
| Hardware partnership LOI (12 months) | 1+ signed | Signed letter of intent (target: Seeed Studio) | SC13 |
| Hackathon presence (12 months) | 3+ events | armOS USB distributed at events | SC14 |
| Cloud training beta users (15 months) | 10+ completing runs | Cloud training service logs | SC15 |
| Monthly recurring revenue (18 months) | $1K MRR | Stripe/payment processor records | SC16 |

### Leading Indicators (Track from Day 1)

These are not success criteria but early warning signals:

| Indicator | Signal | Action If Weak |
|-----------|--------|---------------|
| Demo video views (first 2 weeks) | <500 views | Rethink distribution channels. Try paid promotion on r/robotics. |
| LeRobot Discord reaction to launch post | <10 replies | The messaging is wrong. Reposition around a specific pain point. |
| Boot failure reports (first 50 users) | >20% failure rate | Halt feature work. Focus entirely on hardware compatibility. |
| Seeed Studio response to partnership email | No response in 2 weeks | Try Waveshare and Feetech in parallel via warm intro. |
| Profile contributions (first 6 months) | Zero external contributions | Simplify the contribution workflow. Write example profiles to show the pattern. |

---

_Product Requirements Document v2.0 for armOS USB -- a universal robot operating system on a bootable USB stick. Consolidated from core PRD, PM enhancements, QA review fixes, and strategic content enhancements._
