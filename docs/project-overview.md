# linux-usb - Project Overview

**Date:** 2026-03-15
**Type:** Automation / Provisioning Toolkit
**Architecture:** Multi-stage pipeline with AI-driven orchestration

## Executive Summary

linux-usb is a turnkey provisioning system that creates a bootable Ubuntu USB drive, then uses Claude Code (an AI coding agent) to fully configure a Microsoft Surface Pro 7 as a LeRobot SO-101 robot arm control station. The pipeline spans two operating systems (Windows for USB creation, Linux for configuration) and automates kernel patching, dependency installation, Python environment setup, and USB serial hardware access. It also includes a suite of Python diagnostic and monitoring tools for the Feetech STS3215 servo motors used in the SO-101 arm.

## Project Classification

- **Repository Type:** Single-part automation toolkit
- **Project Type:** CLI / Provisioning (closest to `cli` + `infra` hybrid)
- **Primary Languages:** Bash (bootstrap), PowerShell (USB flashing), Python (diagnostics)
- **Architecture Pattern:** Multi-stage provisioning pipeline

## Technology Stack Summary

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| OS Target | Ubuntu | 24.04.2 LTS | Target operating system on USB |
| Kernel | linux-surface | latest | Patched kernel for Surface hardware support |
| Flash Tool | Rufus | 4.6 portable | USB drive imaging (Windows) |
| AI Agent | Claude Code | latest | Drives 5-phase automated configuration |
| Robot Framework | LeRobot (HuggingFace) | 0.5.0 | Robot arm control and data collection |
| Servo Hardware | Feetech STS3215 | firmware v3.10+ | 6-DOF servo motors in SO-101 arm kit |
| USB Serial | CH340 | -- | Feetech servo controller USB interface |
| Python | CPython | 3.12.x | Runtime for LeRobot and diagnostic tools |
| Shell | Bash | 5.x | Bootstrap scripts |
| Shell (Windows) | PowerShell | 5.1+ | USB flash automation |

## Key Features

- **One-command USB flashing** -- `flash.ps1` downloads Ubuntu ISO, verifies SHA-256, and launches Rufus
- **AI-driven post-install** -- Claude Code reads `CLAUDE.md` and executes a 5-phase setup autonomously (kernel, packages, LeRobot, udev, verification)
- **Passwordless automation** -- `setup.sh` configures NOPASSWD sudo so Claude Code can run all commands without user intervention
- **Context portability** -- Claude's memory files and instructions travel with the repo via `claude-context/` and get installed by `setup.sh`
- **11-phase hardware diagnostics** -- `diagnose_arms.py` tests every aspect of the servo hardware (ping, firmware, voltage, temperature, status registers, EEPROM config, communication reliability, torque stress, cross-bus teleop simulation, individual motor isolation, calibration validation)
- **Live servo monitoring** -- `monitor_arm.py` streams real-time voltage, current, load, temperature, and error flags from all 6 servos with CSV logging
- **Programmatic arm exercise** -- `exercise_arm.py` moves each joint through its range and runs combined movement stress tests
- **Monitored teleoperation** -- `teleop_monitor.py` runs leader-follower teleop with built-in telemetry logging and failure detection

## Architecture Highlights

1. **Two-OS pipeline**: The workflow starts on Windows (flash.ps1) and continues on Linux (setup.sh + Claude Code). The handoff point is the physical USB drive.

2. **AI as orchestrator**: Rather than a monolithic install script, the domain knowledge lives in `CLAUDE.md` as structured instructions. Claude Code interprets these and runs commands, handling errors adaptively. This pattern proved effective for complex multi-step installs where individual steps may need troubleshooting.

3. **Context seeding**: `setup.sh` copies `claude-context/CLAUDE.md` to the repo root and memory files to Claude's project memory directory. This gives Claude Code full context about the hardware, setup status, and remaining work when the user launches it.

4. **Diagnostic suite**: Four Python scripts provide progressively deeper hardware inspection -- from passive monitoring to active stress testing. All use the LeRobot `FeetechMotorsBus` API for low-level servo register access.

## Development Overview

### Prerequisites

- Windows PC with PowerShell 5.1+ (for flash.ps1)
- 64GB+ USB 3.0 drive
- Surface Pro 7 with Secure Boot disabled
- USB wireless keyboard + multi-port adapter

### Getting Started

1. On Windows: `.\flash.ps1` to create the bootable USB
2. On Surface: Boot from USB, install Ubuntu per [BOOT-GUIDE.md](./BOOT-GUIDE.md)
3. On Surface: Run `setup.sh` then `claude` and say "continue setup"

### Key Commands

- **Flash USB:** `.\flash.ps1` (PowerShell, Windows)
- **Bootstrap:** `./setup.sh` (Bash, on Surface after Ubuntu install)
- **Run diagnostics:** `python diagnose_arms.py` (in lerobot-env venv)
- **Monitor servos:** `python monitor_arm.py --log data.csv` (in lerobot-env venv)
- **Exercise arm:** `python exercise_arm.py --cycles 3` (in lerobot-env venv)
- **Monitored teleop:** `python teleop_monitor.py --log session.csv` (in lerobot-env venv)

## Repository Structure

```
linux-usb/
  flash.ps1            -- Windows: download ISO, verify, launch Rufus
  setup.sh             -- Linux: install Claude Code, configure sudo, seed context
  CLAUDE.md            -- AI instructions: 5-phase automated setup
  README.md            -- Quick start guide
  diagnose_arms.py     -- 11-phase servo diagnostic tool
  monitor_arm.py       -- Live servo telemetry monitor
  exercise_arm.py      -- Programmatic arm movement stress test
  teleop_monitor.py    -- Teleop with built-in monitoring
  phase1-surface-kernel.sh -- Standalone Phase 1 kernel install script
  claude-context/      -- Files seeded into Claude Code's memory on setup
  docs/                -- Documentation (boot guide, plans, generated docs)
```

## Documentation Map

For detailed information, see:

- [index.md](./index.md) - Master documentation index
- [architecture.md](./architecture.md) - Detailed architecture
- [source-tree-analysis.md](./source-tree-analysis.md) - Directory structure
- [development-guide.md](./development-guide.md) - Development workflow

---

_Generated using BMAD Method `document-project` workflow_
