---
name: Surface LeRobot Setup Status
type: project
---

# Surface LeRobot Setup Status

## What happened so far
- Setup was initiated from a Windows machine (not the Surface itself)
- USB drive flashed with Ubuntu 24.04.2 LTS using flash.ps1
- setup.sh has been run on the Surface — this installed Claude Code and cloned the repo
- Claude Code is installed and ready to execute the remaining setup phases

## What remains
Five setup phases, defined in CLAUDE.md:
1. **Phase 1:** Install linux-surface kernel (requires reboot after)
2. **Phase 2:** Install system packages (build tools, media libs, Python 3.12)
3. **Phase 3:** Create Python venv, install LeRobot 0.5.0
4. **Phase 4:** Configure udev rules for Feetech USB serial
5. **Phase 5:** Verify everything works

## Why
This Surface Pro 7 is being set up as the control station for a **LeRobot SO-101** robotic arm. It handles:
- Data collection (teleoperation recording via USB cameras + servos)
- Inference (running trained policies locally)
- Training is done in the cloud (no CUDA on this machine)

## How to proceed
Open Claude Code on the Surface and say **"continue setup"**. Claude will read CLAUDE.md and execute Phase 1. After rebooting, say **"continue setup — phase 2"** to resume.
