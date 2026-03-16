---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - synthesis-robot-citizenry.md
  - research-distributed-robotics.md
  - citizenry/ (30 modules, 257 tests)
  - docs/project-overview.md
date: 2026-03-16
author: Bradley
---

# Product Brief: armOS v2 — Citizenry-Native Robot Operating System

## Vision

**armOS is the Android of robotics.** Plug a USB stick into any x86 computer, boot it, connect robot arms and cameras, and you have a working robot control station with distributed intelligence in minutes. Every device is a citizen in a self-governing mesh — discovering each other, negotiating tasks, sharing knowledge, and collaborating autonomously.

The citizenry protocol (30 modules, 257 tests, running on real hardware today) IS the operating system. What remains is packaging it so anyone can use it.

## Problem Statement

Building a working robot setup today requires:
- Hours of Linux configuration, Python environments, driver debugging
- Deep knowledge of servo protocols, USB serial, udev rules
- No standardized way to add a second arm, a camera, or coordinate multiple devices
- When something goes wrong, no diagnostics, no warnings, no fleet awareness
- Every new device is a fresh manual setup from scratch

**armOS solves this:** Boot from USB → hardware auto-detected → citizens discover each other → natural language control → data collection for AI training. Five minutes from USB stick to working robot mesh.

## What Already Exists (The Citizenry Foundation)

The distributed agent protocol is complete and verified on real hardware:

| Layer | What's Built | Status |
|-------|-------------|--------|
| **Protocol** | 7-message UDP protocol, Ed25519 signing, mDNS discovery | Running |
| **Governance** | Constitutional safety, NL commands, rolling policy updates | Running |
| **Collaboration** | Task marketplace, skill trees, XP, symbiosis contracts | Running |
| **Intelligence** | Immune memory, mycelium warnings, emotional state, genome | Running |
| **Vision** | Camera citizen, color detection, camera-guided pick-and-place | Running |
| **UI** | Governor CLI (NL REPL), web dashboard, ANSI TUI dashboard | Running |
| **Data** | LeRobot-compatible data collection, calibration system | Running |
| **Architecture** | Federated learning format, multi-location design | Designed |

**Hardware verified:** Surface Pro 7 (governor) + Pi 5 (arm + camera) + DJI Osmo Action 4 + SO-101 arms. 3-citizen mesh across LAN at 24.5 FPS teleop.

## What Needs to Be Built (The Product Shell)

### 1. Bootable USB Image
- Live Ubuntu 24.04 ISO with citizenry pre-installed
- Auto-starts governor CLI on boot
- All dependencies bundled (Python 3.12, lerobot, pynacl, opencv, zeroconf)
- Persistent storage partition for genomes, calibration, datasets
- `live-build` or `cubic` for ISO creation, GitHub Actions for CI/CD

### 2. Hardware Auto-Detection
- USB device enumeration on plug-in (udev rules + hotplug)
- Identify servo controllers: Feetech CH340 (vendor 1a86), Dynamixel USB2Dynamixel, etc.
- Identify cameras: V4L2 device scan
- Auto-create citizen for each detected device
- Notify governor: "New hardware detected: Feetech servo controller on /dev/ttyACM0. Create arm citizen? [Y/n]"

### 3. Multi-Servo HAL (Citizen Plugins)
- Abstract servo protocol behind a citizen capability interface
- Feetech STS3215 driver: already built (pi_citizen.py)
- Dynamixel XL330/XL430 driver: new citizen type using dynamixel_sdk
- Generic CAN-bus driver: future
- Each driver = a citizen type with `6dof_arm` capability
- Robot profiles (SO-101, Koch, Aloha) become genome templates

### 4. First-Run Experience
- Boot → detect hardware → guided setup via governor CLI
- "I found a Feetech servo controller. Is this an SO-101 arm? [Y/n]"
- Auto-calibrate → generate genome → join mesh → ready
- Takes under 5 minutes from cold boot

### 5. CI/CD and Distribution
- GitHub Actions: build ISO on every release tag
- Windows flash script (flash.ps1 → Rufus/dd)
- Release page with download link + checksums
- Auto-update mechanism for citizenry package (git pull or pip)

## Target Users

1. **Robotics hobbyists** — Want a working robot without Linux expertise
2. **AI researchers** — Need quick data collection on physical robots
3. **Educators** — Classroom setup in minutes, fleet management built-in
4. **Makers** — Building custom robots, need a standard control platform

## Competitive Advantage

| vs. | armOS Advantage |
|-----|-----------------|
| **ROS2** | 5 minutes vs. 8 hours setup. NL control vs. CLI/YAML. |
| **LeRobot (bare)** | Multi-robot mesh, diagnostics, safety, profiles. Not just AI. |
| **phosphobot** | Free, open source, multi-hardware, distributed-first. |
| **NVIDIA Isaac** | Runs on Intel iGPU. $0 hardware cost. |

**The real differentiator:** Every device is a citizen. Plug in a second arm → it joins the mesh. Plug in a camera → it forms a symbiosis contract with the arm. The system self-organizes. No other robotics platform does this.

## Success Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Boot to teleop | < 5 minutes | v2.0 launch |
| Servo protocols supported | 2 (Feetech + Dynamixel) | v2.0 |
| Robot profiles | 2 (SO-101 + Koch) | v2.0 |
| GitHub stars | 500 | 6 months |
| ISO downloads | 1,000 | 6 months |
| Active users (completed teleop) | 50 | 3 months |

## Constraints

- Must boot from USB (no hard drive install required)
- Must work without GPU (Intel integrated baseline)
- Fully open source (Apache 2.0)
- No internet required after first boot
- Python-based (maximum accessibility)
- x86_64 UEFI only for v2.0 (Pi ARM image = v2.1)

## Scope Boundaries

### In Scope (armOS v2.0)
- Bootable USB ISO with citizenry
- Feetech + Dynamixel servo support
- SO-101 + Koch arm profiles
- Hardware auto-detection
- First-run wizard
- CI/CD pipeline
- Governor CLI + web dashboard
- Data collection for LeRobot

### Out of Scope (v3.0+)
- Pi ARM bootable image
- CAN-bus servo protocol
- Cloud training service
- VLA inference on device
- Profile marketplace
- Education licensing
- Hardware partnerships
