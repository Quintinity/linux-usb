---
project: armOS v2.0
date: 2026-03-16
status: approved
---

# Epics & Stories — armOS v2.0: The Product Shell

## Epic 1: Hardware Abstraction Layer

**Goal:** Abstract servo protocols behind a common interface so adding new hardware = one Python file.

### Stories

**E1-S1: ServoDriver ABC and FeetechDriver**
- Define `ServoDriver` abstract base class with: connect, disconnect, read/write position, sync_read/write, torque control, voltage/temp/load, scan_motors
- Implement `FeetechDriver` wrapping lerobot's FeetechMotorsBus
- Extract servo communication from pi_citizen.py into the driver
- AC: FeetechDriver passes unit tests with mocked bus; pi_citizen works with FeetechDriver

**E1-S2: DynamixelDriver**
- Implement `DynamixelDriver` using dynamixel_sdk for XL330 and XL430 motors
- Same interface as FeetechDriver: connect, scan, read/write, torque, telemetry
- AC: DynamixelDriver passes unit tests with mocked SDK

**E1-S3: Motor Scanner**
- Scan connected motors on a servo bus: ping all IDs (1-253), report model and firmware
- Works with both Feetech and Dynamixel buses
- AC: Scanner returns motor list from mocked bus

**E1-S4: Robot Profiles (Genome Templates)**
- SO-101 profile: 6 Feetech STS3215, motor IDs 1-6, home positions, protection limits
- Koch v1.1 profile: 6 Dynamixel XL330, motor IDs 1-6, home positions
- Profile loader: JSON → CitizenGenome template
- AC: Profiles load correctly; motor config matches real hardware specs

**E1-S5: ArmCitizen with HAL**
- Generic `ArmCitizen` class that takes a ServoDriver + RobotProfile
- Replaces direct bus usage in pi_citizen.py
- Same capabilities, marketplace bidding, task execution — just uses HAL underneath
- AC: ArmCitizen + FeetechDriver behaves identically to current pi_citizen

---

## Epic 2: Hardware Auto-Detection

**Goal:** Plug in a servo controller or camera → auto-identified, citizen created, joins mesh.

### Stories

**E2-S1: USB Device Database**
- Map USB vendor:product IDs to driver types (feetech, dynamixel, camera)
- Include all known variants (CH340, CH341, FTDI, etc.)
- AC: Database correctly identifies test device IDs

**E2-S2: USB Hotplug Monitor**
- Watch for USB device add/remove events via pyudev
- Filter for known servo controllers and cameras
- Emit events to the governor
- AC: Monitor detects simulated plug/unplug events

**E2-S3: Camera Detection**
- Scan /dev/video* for V4L2 cameras on startup and hotplug
- Report: device path, name, resolution capabilities
- AC: Camera scan finds test video devices

**E2-S4: Citizen Factory**
- Given a detected device, create the appropriate citizen:
  - Servo controller → scan motors → match profile → ArmCitizen
  - Camera → CameraCitizen
- Handle "unknown" devices gracefully (log, skip, or prompt)
- AC: Factory creates correct citizen type from mock device info

**E2-S5: Device-to-Identity Persistence**
- Map USB serial numbers to citizen identities in device_map.json
- Same physical device = same citizen identity across reboots
- AC: Reconnected device restores previous identity

**E2-S6: udev Rules**
- Write udev rules for Feetech (1a86:*) and Dynamixel (0403:6014) controllers
- Set permissions (0666, dialout group)
- Tag devices for hotplug notification
- AC: Rules file installs correctly; devices get proper permissions

---

## Epic 3: First-Run Wizard

**Goal:** New user boots from USB → guided through setup in under 3 minutes.

### Stories

**E3-S1: Wizard Framework**
- Step-based CLI wizard: each step is a function that returns success/skip/back
- Keyboard-only interaction (input() based)
- Re-runnable via `python -m citizenry setup`
- AC: Wizard framework runs with mock steps

**E3-S2: Hardware Detection Step**
- Scan USB devices, list detected hardware
- "Found: Feetech controller on /dev/ttyACM0, USB camera on /dev/video0"
- Wait for user confirmation or prompt to plug in hardware
- AC: Step lists mock hardware correctly

**E3-S3: Robot Identification Step**
- Scan motors on detected controller
- Match against known profiles
- "This looks like an SO-101 arm. Correct? [Y/n/I don't know]"
- "I don't know" → show profile list for manual selection
- AC: Step correctly identifies SO-101 from 6 Feetech motors

**E3-S4: Calibration Step**
- Load profile → guide user through home position calibration
- "Move shoulder_pan to center position. Press Enter when ready."
- Or auto-calibrate if profile has known home positions
- Save calibration to genome
- AC: Calibration data persisted to ~/.citizenry/

**E3-S5: Completion Step**
- Generate citizen identity (Ed25519 keypair)
- Create genome from profile + calibration
- Start citizen → join mesh
- "Setup complete! Your SO-101 arm is ready. Type 'help' to get started."
- AC: Citizen starts and appears in governor mesh

---

## Epic 4: Bootable USB Image

**Goal:** Downloadable ISO that boots on any x86_64 machine with armOS ready to go.

### Stories

**E4-S1: live-build Configuration**
- Ubuntu 24.04 Noble base with XFCE desktop (lightweight)
- Package list: python3.12, python3.12-venv, git, v4l-utils, ffmpeg
- Auto-login to armos user
- AC: live-build config produces bootable ISO in VM

**E4-S2: armOS Installation Hook**
- Chroot hook installs: citizenry, armos, dependencies into /opt/armos/env
- Creates launch script at /usr/local/bin/armos-start
- Installs udev rules
- AC: Hook runs without errors in chroot

**E4-S3: Systemd Service + Auto-Start**
- armos-governor.service starts on boot
- Auto-launches governor CLI in terminal
- Web dashboard starts on port 8080
- AC: Service starts on boot in VM test

**E4-S4: Persistent Storage**
- casper-rw partition for ~/.citizenry/ data
- Survives reboots: identities, genomes, calibration, datasets
- AC: Data persists across reboot in VM

**E4-S5: Surface Pro Kernel Support**
- Include linux-surface kernel packages
- IPTSD for touchscreen, Type Cover support
- AC: ISO boots on Surface Pro 7 with touchscreen working

---

## Epic 5: CI/CD Pipeline

**Goal:** Reproducible builds, automated testing, one-click releases.

### Stories

**E5-S1: Test Workflow**
- GitHub Actions runs pytest on every push and PR
- Python 3.12, all dependencies installed
- Must pass all 257+ citizenry tests + new armos tests
- AC: Workflow passes on GitHub-hosted runner

**E5-S2: ISO Build Workflow**
- Triggered by version tags (v2.0.0, etc.)
- Runs on ubuntu-24.04 runner with sudo access
- Produces: ISO file + SHA256 checksum
- Uploads to GitHub Releases
- AC: Tag push produces downloadable ISO on releases page

**E5-S3: Windows Flash Script**
- flash.ps1: downloads Rufus portable, flashes ISO to selected USB drive
- Interactive: lists available drives, confirms before writing
- AC: Script runs on Windows 10/11, produces bootable USB

**E5-S4: Linux/macOS Flash Script**
- flash.sh: uses dd with progress indicator
- Lists available drives, confirms before writing
- AC: Script produces bootable USB on Linux and macOS

---

## Sprint Plan

### Sprint 1: HAL Foundation (E1-S1 through E1-S5)
- ServoDriver ABC, FeetechDriver, DynamixelDriver
- Motor scanner, profiles, ArmCitizen
- All unit tests

### Sprint 2: Hardware Detection (E2-S1 through E2-S6)
- USB database, hotplug monitor, camera detection
- Citizen factory, identity persistence, udev rules

### Sprint 3: First-Run + Integration (E3-S1 through E3-S5)
- Wizard framework and all steps
- End-to-end: plug in → wizard → citizen running

### Sprint 4: Packaging (E4-S1 through E4-S5, E5-S1 through E5-S4)
- live-build ISO, systemd service, persistent storage
- CI/CD: test workflow, ISO build, flash scripts
- Surface Pro kernel support
