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
  - citizenry/ (30 modules)
  - synthesis-robot-citizenry.md
  - architecture-citizenry-v2.md
  - architecture-citizenry-v3.md
workflowType: 'prd'
---

# Product Requirements Document — armOS v2.0

**Author:** Bradley
**Date:** 2026-03-16
**Version:** 2.0
**Status:** Approved for implementation

---

## Executive Summary

The armOS citizenry protocol — 30 modules, 257 tests, verified on real hardware — provides distributed robot intelligence: task marketplace, NL governance, camera-guided manipulation, safety monitoring, and fleet learning. **But it's not a product yet.** Users must clone a git repo, install dependencies manually, and understand Python to get started.

**armOS v2.0 turns the citizenry protocol into a shippable product** by wrapping it in a bootable USB image with hardware auto-detection, multi-servo support, a first-run wizard, and CI/CD for reproducible builds. The goal: **boot from USB → working robot mesh in 5 minutes.**

Five build items:
1. **Bootable USB Image** — Live Ubuntu 24.04 ISO with citizenry pre-installed
2. **Hardware Auto-Detection** — Plug in servo controller or camera → auto-identified, citizen created
3. **Multi-Servo HAL** — Dynamixel XL330/XL430 support via citizen plugin architecture
4. **First-Run Wizard** — Guided setup: detect hardware → identify robot → calibrate → join mesh
5. **CI/CD Pipeline** — GitHub Actions builds ISO on release, Windows flash script

---

## Vision

**"Boot from USB. Detect hardware. Start building."**

armOS is the Android of robotics. Like Android abstracted phone hardware behind a standard API, armOS abstracts robot hardware behind the citizenry protocol. Every servo controller is a citizen. Every camera is a citizen. Every computer running armOS is a governor. They find each other, negotiate capabilities, and collaborate — automatically.

The user's experience: plug a USB stick into any x86 laptop, boot it, connect a robot arm. Five minutes later they're controlling the arm with natural language ("wave hello"), collecting AI training data, and monitoring servo health on a web dashboard. No terminal commands. No Python knowledge. No Linux expertise.

---

## Problem Statement

Today, using the citizenry protocol requires:
1. **Manual Linux setup** — Ubuntu install, kernel patches, driver config
2. **Python environment management** — venv, pip, dependency resolution
3. **Git knowledge** — clone repo, navigate directory structure
4. **Hardware expertise** — identify servo controllers, configure udev rules, find correct ports
5. **Protocol understanding** — know which citizen type to run, how to start governor vs follower

**This eliminates 95% of potential users.** A robotics teacher, a hobbyist with a new SO-101, a researcher who just wants to collect data — they can't use armOS today without significant technical help.

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Boot to working teleop | < 5 minutes | Timed from USB boot to first arm movement |
| Hardware detection accuracy | > 95% | Auto-detect Feetech + Dynamixel controllers |
| First-run completion rate | > 80% | Users complete wizard without manual intervention |
| Servo protocols supported | 2 | Feetech STS3215 + Dynamixel XL330 |
| Robot profiles | 2 | SO-101 + Koch v1.1 |
| ISO build reproducibility | 100% | Same commit → same ISO hash |
| ISO size | < 4 GB | Fits on standard USB stick |
| Test suite | > 280 tests | All existing + new HAL/detection tests |
| GitHub stars | 500 | Within 6 months of launch |

---

## User Journeys

### Journey 1: First-Time User with SO-101

Sarah bought an SO-101 arm kit. She has a ThinkPad running Windows.

1. Downloads armOS ISO from GitHub releases (2.5 GB)
2. Flashes to USB stick using flash.ps1 (Windows) or dd (macOS/Linux)
3. Boots ThinkPad from USB → Ubuntu desktop loads with armOS splash
4. Plugs in SO-101 servo controller via USB
5. **Auto-detection fires:** "Feetech servo controller detected on /dev/ttyACM0"
6. First-run wizard: "Is this an SO-101 arm? [Yes] [No] [I don't know]"
7. Sarah taps Yes → wizard loads SO-101 genome template
8. "Move each joint to its home position" → guided calibration (30 seconds)
9. Wizard complete → Governor CLI starts: "armOS ready. 1 citizen: so101-arm. Type 'help' for commands."
10. Sarah types "wave hello" → arm waves
11. She opens http://localhost:8080 → web dashboard shows arm health, position, status

**Total time: 4 minutes from USB boot to first wave.**

### Journey 2: Adding a Camera

Sarah now wants to do camera-guided pick-and-place.

1. Plugs in USB camera
2. Auto-detection: "USB camera detected: DJI Osmo Action 4. Create camera citizen? [Y/n]"
3. Camera citizen starts → discovers arm citizen → symbiosis contract auto-proposed
4. Dashboard shows: "Composite capabilities: visual_pick_and_place, color_sorting"
5. Sarah types "what do you see" → camera detects colored objects
6. "pick up the red block" → camera-guided pick-and-place executes

### Journey 3: Adding a Second Arm (Koch v1.1)

A researcher has both an SO-101 and a Koch v1.1 arm.

1. Plugs in Dynamixel USB2Dynamixel adapter
2. Auto-detection: "Dynamixel servo controller detected. Scanning for motors..."
3. Scan finds 6 XL330 motors → "This looks like a Koch v1.1 arm. Confirm? [Y/n]"
4. Koch genome template loaded → calibration wizard runs
5. Two arm citizens now in the mesh → marketplace routes tasks to whichever is available
6. "sort the blocks" → both arms participate, camera coordinates

### Journey 4: Classroom Deployment

A teacher sets up 10 workstations for a robotics class.

1. Flashes 10 USB sticks from the same ISO
2. Each student boots, plugs in their SO-101 → auto-detected, calibrated in 2 minutes
3. Teacher's machine runs governor → discovers all 10 arm citizens on the LAN
4. Web dashboard shows fleet: 10 arms, health status, task completion
5. Teacher types "all wave hello" → all 10 arms wave in sync

---

## Functional Requirements

### FR-1: Bootable USB Image

**FR-1.1** The system MUST produce a bootable USB image based on Ubuntu 24.04.2 LTS that boots on any x86_64 UEFI machine manufactured after 2016.

**FR-1.2** The image MUST include all citizenry dependencies pre-installed: Python 3.12, lerobot 0.5.0, pynacl, zeroconf, opencv-python-headless, aiohttp, numpy.

**FR-1.3** The image MUST auto-start the governor CLI (`python -m citizenry`) on login, with the web dashboard accessible at http://localhost:8080.

**FR-1.4** The image MUST include a persistent storage partition (casper-rw or equivalent) that survives reboots, storing: citizen identities (~/.citizenry/), genomes, calibrations, datasets, and configuration.

**FR-1.5** The image MUST include the linux-surface kernel packages for Surface Pro support, plus standard Intel/AMD GPU drivers.

**FR-1.6** The image size MUST be under 4 GB to fit on standard USB sticks.

**FR-1.7** The image MUST work in both live mode (RAM only, no persistence) and persistent mode (with casper-rw partition).

### FR-2: Hardware Auto-Detection

**FR-2.1** The system MUST detect USB servo controllers within 3 seconds of plug-in using udev rules and hotplug events.

**FR-2.2** The system MUST identify servo controller type by USB vendor/product ID:
- Feetech: vendor `1a86` (QinHeng CH340)
- Dynamixel: vendor `0403` (FTDI) with product `6014` (USB2Dynamixel)

**FR-2.3** The system MUST scan detected servo controllers for connected motors and report: count, model, and ID range.

**FR-2.4** The system MUST detect USB cameras via V4L2 device enumeration and report: device path, name, supported resolutions.

**FR-2.5** The system MUST notify the governor when new hardware is detected, with a prompt to create the appropriate citizen type.

**FR-2.6** The system MUST handle hot-unplug gracefully: citizen goes offline, will broadcast, tasks re-auctioned.

**FR-2.7** The system MUST persist hardware→citizen mappings so that reconnecting the same device (same serial number) restores the same citizen identity.

### FR-3: Multi-Servo Hardware Abstraction Layer

**FR-3.1** The HAL MUST define an abstract `ServoDriver` interface with methods: `connect()`, `disconnect()`, `read_position(motor_id)`, `write_position(motor_id, value)`, `read_voltage(motor_id)`, `read_temperature(motor_id)`, `enable_torque()`, `disable_torque()`, `sync_read(register, motor_ids)`, `sync_write(register, values)`.

**FR-3.2** The system MUST include a `FeetechDriver` implementing `ServoDriver` for STS3215 servos (already exists in pi_citizen.py, to be extracted).

**FR-3.3** The system MUST include a `DynamixelDriver` implementing `ServoDriver` for XL330 and XL430 servos using the dynamixel_sdk package.

**FR-3.4** Each driver MUST be packaged as a citizen plugin: a Python class that extends `Citizen` and declares capabilities based on the connected hardware.

**FR-3.5** Robot profiles (SO-101, Koch v1.1) MUST be implemented as genome templates: pre-configured motor IDs, position ranges, calibration hints, protection limits.

**FR-3.6** Adding a new servo protocol MUST require only: (a) implementing `ServoDriver`, (b) creating a citizen class, (c) adding a udev rule. No changes to core protocol.

### FR-4: First-Run Wizard

**FR-4.1** The wizard MUST launch automatically on first boot (detected via absence of ~/.citizenry/ directory).

**FR-4.2** The wizard MUST guide the user through: (a) hardware detection, (b) robot identification, (c) calibration, (d) mesh join confirmation.

**FR-4.3** The wizard MUST support keyboard-only interaction (no mouse required — for headless/terminal setups).

**FR-4.4** The wizard MUST offer an "I don't know" option for robot identification, falling back to generic motor scan and manual profile selection.

**FR-4.5** The wizard MUST complete in under 3 minutes for a standard SO-101 setup.

**FR-4.6** The wizard MUST be re-runnable via `python -m citizenry setup` for adding new hardware later.

### FR-5: CI/CD Pipeline

**FR-5.1** GitHub Actions MUST build the ISO on every push to a `release/*` branch or creation of a version tag.

**FR-5.2** The build MUST be reproducible: same commit produces the same ISO contents (modulo timestamps).

**FR-5.3** The pipeline MUST run the full test suite (257+ tests) before building the ISO.

**FR-5.4** The pipeline MUST produce: ISO file, SHA256 checksum, build log.

**FR-5.5** A Windows flash script (`flash.ps1`) MUST be provided that downloads Rufus and flashes the ISO to a user-selected USB drive.

**FR-5.6** The pipeline MUST also produce a Pi ARM image (deferred to v2.1 but pipeline structure must support it).

---

## Non-Functional Requirements

### NFR-1: Boot Performance
- Cold boot to governor CLI ready: < 60 seconds on modern hardware
- Hardware detection latency: < 3 seconds after USB plug-in
- Citizen discovery on LAN: < 5 seconds

### NFR-2: Hardware Compatibility
- Tested on: ThinkPad T480+, Dell XPS 13+, Surface Pro 5+, any post-2016 UEFI x86_64
- GPU: Intel integrated (HD 520+), no discrete GPU required
- RAM: minimum 4 GB, recommended 8 GB
- USB: at least 1x USB-A or USB-C port

### NFR-3: Reliability
- System MUST function after unexpected power loss (no data corruption)
- Persistent storage uses journaling filesystem (ext4)
- All citizen state uses atomic writes (write-to-tmp, rename)

### NFR-4: Security
- Ed25519 signing on all protocol messages (existing)
- No default passwords — SSH disabled in live image
- USB serial devices accessible via udev rules (no root required)

### NFR-5: Offline Operation
- Fully functional without internet after first boot
- All dependencies bundled in ISO
- No cloud services required for any core feature

### NFR-6: Extensibility
- New servo protocol = 1 Python file + 1 udev rule
- New robot profile = 1 genome JSON template
- Community contributions via GitHub PRs

---

## Technical Constraints

1. **Ubuntu 24.04 LTS** — stable base, 5-year support
2. **Python 3.12** — matching current Surface setup
3. **No CUDA** — Intel integrated GPU only
4. **live-build or cubic** — standard Ubuntu ISO customization tools
5. **dynamixel_sdk** — official Robotis Python package for Dynamixel servos
6. **Existing citizenry protocol unchanged** — all new code builds on top, zero breaking changes
7. **Apache 2.0 license** — fully open source

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    armOS USB Image                        │
│  Ubuntu 24.04 + linux-surface kernel + citizenry         │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              First-Run Wizard                       │  │
│  │  Detect → Identify → Calibrate → Join Mesh         │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │           Governor CLI (python -m citizenry)        │  │
│  │  NL Governance │ Task Marketplace │ Web Dashboard   │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │              Citizenry Protocol                      │  │
│  │  7 messages │ Ed25519 │ UDP │ mDNS │ Constitution   │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │         Hardware Abstraction Layer                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │  │
│  │  │ Feetech  │  │Dynamixel │  │  Camera   │         │  │
│  │  │ Driver   │  │ Driver   │  │  Driver   │         │  │
│  │  └──────────┘  └──────────┘  └──────────┘         │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │           Hardware Auto-Detection                    │  │
│  │  udev rules │ USB hotplug │ V4L2 scan │ motor scan  │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Dependencies

### New packages (to add to ISO)
- `dynamixel-sdk>=3.7.51` — Dynamixel servo protocol
- `live-build` or `cubic` — ISO build tooling (build-time only)

### Existing (already in citizenry)
- `pynacl>=1.5.0`, `zeroconf>=0.131.0`, `opencv-python-headless>=4.8.0`
- `aiohttp>=3.9.0`, `numpy>=1.26.0`, `lerobot==0.5.0`

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| USB boot fails on some hardware | Users can't start | Medium | Test on 5+ machines; UEFI/legacy boot fallback |
| Dynamixel SDK compatibility issues | Koch arm doesn't work | Low | dynamixel_sdk is mature; test with real hardware |
| ISO too large (>4GB) | Doesn't fit standard USB | Low | Strip unnecessary Ubuntu packages; target 2.5GB |
| Persistent storage corruption | Calibration/genomes lost | Low | ext4 journaling + atomic writes (existing pattern) |
| First-run wizard confusing | Users abandon setup | Medium | User testing with 3+ non-technical users |

---

## Scope Boundaries

### In Scope (v2.0)
- Bootable x86_64 USB image
- Feetech STS3215 + Dynamixel XL330 drivers
- SO-101 + Koch v1.1 profiles
- Hardware auto-detection (servo + camera)
- First-run wizard
- CI/CD with GitHub Actions
- Windows flash script

### Out of Scope (v2.1+)
- Pi ARM bootable image
- CAN-bus servo protocol
- Aloha arm profile
- Cloud training service
- Profile marketplace
- OTA updates
- Android/iOS companion app
