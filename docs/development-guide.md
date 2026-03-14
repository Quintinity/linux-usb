# linux-usb - Development Guide

**Date:** 2026-03-15

## Prerequisites

### For USB Flashing (Windows)
- Windows 10/11 with PowerShell 5.1+
- Internet connection (downloads ~6GB ISO)
- 64GB+ USB 3.0 drive

### For Surface Setup (Linux)
- Surface Pro 7 with Secure Boot disabled
- USB wireless keyboard with 2.4GHz dongle
- Multi-port USB adapter (keyboard + USB stick simultaneously)
- Internet connection (WiFi works with stock Ubuntu kernel)

### For Diagnostic Scripts (Post-Setup)
- Completed setup (all 5 phases)
- `~/lerobot-env` virtual environment with LeRobot 0.5.0
- SO-101 arm(s) connected via USB serial
- 7.4V power supply for follower arm servos

## Environment Setup

### Python Virtual Environment

All Python scripts require the LeRobot virtual environment:

```bash
source ~/lerobot-env/bin/activate
```

The venv is created during Phase 3 of the setup process at `~/lerobot-env` using Python 3.12.

### Serial Port Access

The Feetech servo controllers appear as `/dev/ttyACM0` and `/dev/ttyACM1`. The udev rule from Phase 4 grants access without root:

```bash
# Verify port access
ls -la /dev/ttyACM*
```

If ports are not accessible, check:
1. User is in the `dialout` group: `groups $USER`
2. Udev rule exists: `cat /etc/udev/rules.d/99-feetech-serial.rules`
3. `brltty` is not installed (it steals Feetech serial ports): `dpkg -l brltty`

### Port Assignment Convention

- `/dev/ttyACM0` -- Follower arm (the arm that moves)
- `/dev/ttyACM1` -- Leader arm (the arm you move by hand)

Port assignment depends on USB enumeration order. If ports are swapped, unplug both and re-plug in the correct order (follower first).

## Usage Guide

### Running Diagnostics

The diagnostic tool runs 11 phases of hardware testing:

```bash
source ~/lerobot-env/bin/activate
python diagnose_arms.py
```

This tests both arms. It checks port detection, motor ping, firmware versions, voltage/temperature, status registers, EEPROM configuration, communication reliability, torque stress, cross-bus teleop simulation, individual motor isolation, and calibration file validity.

### Monitoring Servos

Stream real-time telemetry from one arm:

```bash
source ~/lerobot-env/bin/activate

# Monitor follower arm (default)
python monitor_arm.py

# Monitor leader arm
python monitor_arm.py --port /dev/ttyACM1

# Log to CSV for later analysis
python monitor_arm.py --log session_data.csv

# Adjust polling rate
python monitor_arm.py --hz 20
```

Press Ctrl+C to stop. A session summary is printed showing min voltages, max currents, max loads, and error counts per motor.

### Exercising the Arm

Move the follower arm through predefined positions programmatically:

```bash
source ~/lerobot-env/bin/activate

# Full test (all joints + combined movement + rapid gripper)
python exercise_arm.py

# Test a single joint
python exercise_arm.py --joint gripper

# More repetitions
python exercise_arm.py --cycles 5

# Different port
python exercise_arm.py --port /dev/ttyACM1
```

The arm must be powered and have valid calibration at `~/.cache/huggingface/lerobot/calibration/robots/so_follower/follower.json`.

### Monitored Teleoperation

Run leader-follower teleop with built-in monitoring:

```bash
source ~/lerobot-env/bin/activate

# Default: 60Hz teleop, 2Hz monitoring, log to /tmp/teleop_monitor.csv
python teleop_monitor.py

# Custom settings
python teleop_monitor.py --fps 30 --monitor-hz 5 --log ~/teleop_session.csv
```

Both arms must be connected and calibrated. The follower arm must be powered. Press Ctrl+C to stop. If the servo bus dies (20 consecutive read failures), the script dumps the last 5 telemetry snapshots to help diagnose the failure.

## Modifying the Project

### Adding a New Setup Phase

1. Edit `claude-context/CLAUDE.md` (the source of truth)
2. Add the new phase in order with commands and verification steps
3. Update Phase 5 (verification) to include the new phase's checks
4. Run `setup.sh` on a test machine to re-deploy the updated CLAUDE.md

### Adding a New Diagnostic Script

Follow the patterns established by the existing scripts:

1. Import from `lerobot.motors.feetech.feetech` for servo access
2. Use `argparse` for CLI options (at minimum: `--port`, `--cal`)
3. Use the `make_motors()` helper to create the standard 6-motor configuration
4. Handle `SIGINT` gracefully (disable torque before exit)
5. Use ANSI color codes for terminal output (RED/GREEN/YELLOW/CYAN)
6. Provide CSV logging when applicable

### Changing Target Hardware

The project is specific to:
- **Surface Pro 7** -- kernel is `linux-surface`, hardware notes reference specific components
- **SO-101 arm** -- motor IDs 1-6, STS3215 servos, specific calibration paths

To target different hardware:
- Update `CLAUDE.md` Phase 1 if the kernel needs to change
- Update motor configuration in all Python scripts if the arm model changes
- Update port paths if serial devices enumerate differently
- Update calibration paths in Python scripts

### Modifying flash.ps1

The script is self-contained. Key variables at the top:

```powershell
$IsoUrl    = 'https://releases.ubuntu.com/24.04.2/ubuntu-24.04.2-desktop-amd64.iso'
$ShaUrl    = 'https://releases.ubuntu.com/24.04.2/SHA256SUMS'
$RufusUrl  = 'https://github.com/pbatard/rufus/releases/download/v4.6/rufus-4.6p.exe'
```

To update Ubuntu version: change these URLs and the filename references below them.

## Known Issues and Workarounds

### Terminal line wrapping breaks multi-line commands

Long `apt install` commands using backslash continuations break when the terminal wraps mid-line. Always write long apt commands as a single unbroken line in `CLAUDE.md`.

### brltty steals serial ports

The `brltty` package (Braille display driver) claims Feetech serial ports. If installed, remove it:

```bash
sudo apt remove brltty
```

`diagnose_arms.py` Phase 1 checks for this automatically.

### Surface cameras do not work

The front and rear cameras on the Surface Pro 7 do not function under Linux. Use external USB cameras for LeRobot data collection.

### Servo overload errors

If servos report OVERLOAD errors, check:
1. Power supply voltage (should be 7.4V, minimum 6.0V under load)
2. Mechanical binding (joints should move freely when torque is disabled)
3. Protection_Current EEPROM register (should not be 0)
4. Max_Torque_Limit for the gripper (set to 500 by the scripts)

## Calibration

LeRobot calibration files are stored at:
- Follower: `~/.cache/huggingface/lerobot/calibration/robots/so_follower/follower.json`
- Leader: `~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/leader.json`

To re-calibrate, follow LeRobot's calibration procedure. The diagnostic script (`diagnose_arms.py` Phase 11) validates calibration file integrity.

## File Reference

| File | Language | Purpose |
|------|----------|---------|
| `flash.ps1` | PowerShell | Download Ubuntu ISO, verify checksum, launch Rufus |
| `setup.sh` | Bash | Install Claude Code, configure sudo, seed AI context |
| `CLAUDE.md` | Markdown | 5-phase AI-driven setup instructions |
| `phase1-surface-kernel.sh` | Bash | Standalone kernel install script |
| `diagnose_arms.py` | Python | 11-phase hardware diagnostic |
| `monitor_arm.py` | Python | Live servo telemetry streaming |
| `exercise_arm.py` | Python | Programmatic arm movement tests |
| `teleop_monitor.py` | Python | Teleop with integrated monitoring |
| `docs/BOOT-GUIDE.md` | Markdown | Ubuntu USB install instructions |
| `claude-context/CLAUDE.md` | Markdown | Source of CLAUDE.md (copied by setup.sh) |

---

_Generated using BMAD Method `document-project` workflow_
