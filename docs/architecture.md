# linux-usb - Architecture

**Date:** 2026-03-15

## Architecture Overview

linux-usb uses a multi-stage provisioning pipeline that spans two operating systems. The architecture is unusual in that it uses an AI coding agent (Claude Code) as the primary orchestrator for the Linux configuration phases, rather than a traditional shell script.

```
[Windows PC]                    [Surface Pro 7]

flash.ps1                       setup.sh
  |                               |
  v                               v
Download ISO ----USB Drive----> Boot Ubuntu
Verify SHA-256                  Install git, curl
Launch Rufus                    Install Claude Code
Flash USB                       Configure sudo
                                Seed AI context
                                  |
                                  v
                                Claude Code reads CLAUDE.md
                                  |
                                  v
                              Phase 1: linux-surface kernel
                                  | (reboot)
                              Phase 2: System packages
                              Phase 3: LeRobot + venv
                              Phase 4: udev rules
                              Phase 5: Verification
                                  |
                                  v
                              [System Ready]
                                  |
                                  v
                              Diagnostic Scripts
                              (diagnose, monitor, exercise, teleop)
```

## Component Architecture

### 1. USB Flash Tool (`flash.ps1`)

A self-contained PowerShell script that runs on Windows. No external dependencies beyond PowerShell 5.1 and internet access.

**Responsibilities:**
- Create `downloads/` directory
- Download SHA256SUMS file from Ubuntu release server
- Download Ubuntu 24.04.2 desktop ISO (~6GB) via BITS transfer (resumable)
- Verify ISO integrity against published SHA-256 checksum
- Download Rufus 4.6 portable
- Display recommended Rufus settings (GPT, UEFI, FAT32)
- Launch Rufus and wait for completion

**Design decisions:**
- Uses BITS transfer for resumable downloads (important for 6GB file)
- Skips files that already exist (idempotent)
- Verifies checksum before launching Rufus (prevents flashing corrupt image)
- Portable Rufus (no installation needed)

### 2. Bootstrap Script (`setup.sh`)

A Bash script that prepares the freshly installed Ubuntu system for AI-driven configuration.

**Responsibilities:**
1. Install `git` and `curl` (minimal dependencies)
2. Configure passwordless sudo for the current user (writes `/etc/sudoers.d/<user>-nopasswd`)
3. Install Claude Code via `https://claude.ai/install.sh`
4. Copy context files from `claude-context/` to Claude Code's memory directory

**Design decisions:**
- Passwordless sudo is critical: Claude Code has no terminal to enter a password, so without NOPASSWD it cannot run `sudo` commands autonomously
- Context seeding uses Claude Code's project memory path convention: `~/.claude/projects/<repo-path-with-dashes>/memory/`
- The script is idempotent: checks for existing sudo config, existing Claude Code install

### 3. AI Orchestration Layer (`CLAUDE.md`)

The central design innovation. Instead of encoding all setup logic in shell scripts, the domain knowledge lives in `CLAUDE.md` as structured instructions that Claude Code reads and executes.

**Structure:**
- 5 sequential phases with verification gates between them
- Phase 1 requires a manual reboot (hardware constraint)
- Each phase has explicit commands and verification checks
- Environment notes section provides constraint information
- Lessons learned section captures operational knowledge

**Why AI orchestration instead of shell scripts:**
- **Error handling**: Claude Code can diagnose and adapt to unexpected failures
- **Interactivity**: The reboot between Phase 1 and Phase 2 requires human interaction; Claude handles the state transition naturally
- **Maintenance**: Instructions in English are easier to update than complex shell scripts
- **Debugging**: When something goes wrong, Claude can inspect state and suggest fixes

### 4. Context Seeding System (`claude-context/`)

Portable AI context that travels with the repository.

**Files:**
- `CLAUDE.md` -- Copied to repo root; contains 5-phase setup instructions
- `memory/MEMORY.md` -- Index of memory files
- `memory/hardware_surface-pro-7.md` -- Hardware specs and Linux compatibility notes
- `memory/project_surface-lerobot.md` -- Setup status and remaining work

**Flow:** `setup.sh` copies these files to Claude Code's memory directory, so when the user launches `claude` in the repo directory, Claude has full context about what hardware it's running on, what has been done, and what remains.

### 5. Diagnostic Scripts (Python)

Four Python scripts that interface directly with the Feetech STS3215 servos via the LeRobot motor bus API. All require the `~/lerobot-env` virtual environment.

#### `diagnose_arms.py` -- Comprehensive Hardware Diagnostic

11-phase test sequence covering every aspect of the servo hardware:

| Phase | Test | What It Checks |
|-------|------|----------------|
| 1 | Port Detection | USB ports exist, are accessible, brltty not installed |
| 2 | Motor Ping | Individual servo response on each bus |
| 3 | Firmware Version | STS3215 firmware version (expects v3.10+) |
| 4 | Voltage & Temperature | Power supply health, thermal status |
| 5 | Status Register | Error flags (voltage, angle, overheat, overcurrent, overload) |
| 6 | EEPROM Configuration | Full register dump with anomaly detection |
| 7 | Communication Reliability | 200 sync_read cycles, latency stats |
| 8 | Torque Stress Test | 200 read/write cycles with torque enabled |
| 9 | Cross-Bus Teleop Sim | 500 cycles reading leader + writing follower |
| 10 | Individual Motor Isolation | Per-motor reliability to find weak links |
| 11 | Calibration Validation | Calibration file sanity checks |

#### `monitor_arm.py` -- Live Telemetry Monitor

Real-time streaming of servo registers at configurable polling rate (default 10Hz):
- Voltage, current, load, temperature, position, velocity, status/error flags per motor
- Color-coded terminal output with threshold-based warnings
- Optional CSV logging for post-session analysis
- Session summary with min voltages, max currents, max loads, error counts

#### `exercise_arm.py` -- Programmatic Movement Test

Moves the follower arm through predefined positions to verify mechanical and electrical health:
- Per-joint range testing (center -> min -> max -> center)
- Combined multi-joint movement sequences
- Rapid gripper cycling stress test
- Smooth interpolation with configurable step count
- Voltage/load/status monitoring at each position

#### `teleop_monitor.py` -- Monitored Teleoperation

Leader-follower teleoperation with integrated telemetry:
- Teleop loop at configurable FPS (default 60Hz)
- Telemetry sampling at separate rate (default 2Hz) to minimize servo bus contention
- Ring buffer of last 20 telemetry snapshots for failure forensics
- Automatic bus death detection with pre-failure telemetry dump
- Full CSV logging of every cycle's read/write success and servo state

## Hardware Architecture

```
[Surface Pro 7]
  |
  |-- USB-A port (via multi-port adapter)
  |     |-- USB wireless keyboard dongle
  |     |-- CH340 USB-Serial adapter #1 -> Follower arm (6x STS3215)
  |     |-- CH340 USB-Serial adapter #2 -> Leader arm (6x STS3215)
  |     |-- USB camera(s) (for data collection)
  |
  |-- USB-C port
        |-- (available for additional peripherals)
```

**Serial communication:**
- Baud rate: 1,000,000 (1 Mbps)
- Protocol: Feetech STS3215 servo protocol (similar to Dynamixel)
- Motor IDs: 1-6 per arm (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper)
- Calibration files: JSON at `~/.cache/huggingface/lerobot/calibration/`

**Hardware constraints:**
- No CUDA (Intel Iris Plus GPU) -- training must be done in cloud
- Built-in cameras do not work under Linux -- use USB cameras
- 8GB RAM limits concurrent operations
- Feetech servo firmware updates require Windows

## Data Flow

### Setup Flow
```
flash.ps1 downloads -> SHA256SUMS, Ubuntu ISO, Rufus
                        |
                        v (Rufus writes to USB)
                    Bootable USB drive
                        |
                        v (boot Surface from USB)
                    Ubuntu installer
                        |
                        v (install to USB)
                    Installed Ubuntu on USB
                        |
                        v (git clone + setup.sh)
                    Claude Code + context
                        |
                        v (CLAUDE.md phases)
                    Configured system
```

### Teleop Data Flow
```
Leader arm (6 servos) --serial--> /dev/ttyACM1
                                      |
                                      v
                                leader.sync_read("Present_Position")
                                      |
                                      v
                                follower.sync_write("Goal_Position", leader_positions)
                                      |
                                      v
Follower arm (6 servos) <--serial-- /dev/ttyACM0
```

## Security Considerations

- `setup.sh` grants NOPASSWD sudo to the current user -- this is intentional for unattended AI-driven setup but should be reviewed for production environments
- Udev rules set Feetech serial devices to mode 0666 (world-readable/writable) -- acceptable for single-user Surface but not for shared systems
- WiFi credentials are not stored in the repository (entered manually during Ubuntu install)
- No secrets, tokens, or credentials are committed to the repository

## Testing Strategy

There are no automated tests in the traditional sense (no test runner, no CI). Verification is built into the pipeline:

- `flash.ps1` verifies ISO checksum before flashing
- Phase 5 of `CLAUDE.md` runs verification checks (kernel version, Python, LeRobot import, surface modules)
- `diagnose_arms.py` is a comprehensive hardware test suite
- `exercise_arm.py` serves as an integration test for arm movement
- `monitor_arm.py` and `teleop_monitor.py` provide runtime monitoring

## Deployment

The "deployment" is the USB drive itself. The entire system is portable -- plug the USB into any Surface Pro 7, boot from it, and the full environment is ready. The setup phases are idempotent and can be re-run if needed.

---

_Generated using BMAD Method `document-project` workflow_
