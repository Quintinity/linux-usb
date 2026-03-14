# linux-usb - Source Tree Analysis

**Date:** 2026-03-15

## Overview

This project is a flat, single-directory repository with no nested source tree. All scripts and documentation live at the root level or in shallow subdirectories. The simplicity is intentional -- the repo is cloned onto a freshly installed Ubuntu system and needs to work immediately without build steps.

## Complete Directory Structure

```
linux-usb/
|-- .claude/                          # Claude Code project settings
|   |-- settings.json
|
|-- .git/                             # Git repository data
|-- .gitignore                        # Ignores downloads/ and CLAUDE.md (generated)
|
|-- _bmad/                            # BMAD Method tooling (documentation workflows)
|   |-- bmm/
|       |-- config.yaml               # Project config for BMAD workflows
|       |-- workflows/
|           |-- document-project/     # Documentation generation workflow
|
|-- _bmad-output/                     # BMAD output artifacts
|   |-- implementation-artifacts/
|   |-- planning-artifacts/
|
|-- claude-context/                   # Context files seeded into Claude Code by setup.sh
|   |-- CLAUDE.md                     # Master AI instructions (copied to repo root)
|   |-- memory/
|       |-- MEMORY.md                 # Memory index
|       |-- hardware_surface-pro-7.md # Surface Pro 7 hardware reference
|       |-- project_surface-lerobot.md# Setup status and project context
|
|-- docs/                             # Documentation
|   |-- BOOT-GUIDE.md                 # Step-by-step Ubuntu USB install guide
|   |-- plans/
|       |-- 2026-03-14-autoinstall.md # Future zero-touch install design
|
|-- CLAUDE.md                         # AI orchestration instructions (5-phase setup)
|-- README.md                         # Quick start guide and project overview
|-- flash.ps1                         # [ENTRY] Windows: ISO download + Rufus launch
|-- setup.sh                          # [ENTRY] Linux: Claude Code install + context seeding
|-- phase1-surface-kernel.sh          # Standalone kernel install (Phase 1 only)
|-- diagnose_arms.py                  # 11-phase servo diagnostic tool
|-- monitor_arm.py                    # Live servo telemetry monitor
|-- exercise_arm.py                   # Programmatic arm stress test
|-- teleop_monitor.py                 # Teleop with monitoring and failure detection
```

## Critical Directories

### `/` (Project Root)

The root contains all executable scripts and the AI instructions file. There is no `src/` or `lib/` separation because these are standalone scripts, not a library.

**Purpose:** Flat layout for direct execution on a freshly cloned repo.
**Contains:** 2 shell scripts, 1 PowerShell script, 4 Python scripts, 2 markdown instruction files.

### `claude-context/`

Files that `setup.sh` copies into Claude Code's project memory directory (`~/.claude/projects/<path>/memory/`). This is how domain knowledge about the hardware and project status travels with the repository and becomes available to Claude Code on first launch.

**Purpose:** Portable AI context -- seeds Claude Code with hardware specs, setup status, and instructions.
**Contains:** CLAUDE.md (master instructions), hardware reference, project status tracker.

### `docs/`

User-facing documentation and generated project knowledge.

**Purpose:** Documentation for humans and AI agents.
**Contains:** Boot guide, future plans, generated architecture docs.

## Entry Points

- **`flash.ps1`** -- First entry point. Run on Windows to create the bootable USB. Downloads Ubuntu 24.04.2 ISO (~6GB), verifies SHA-256 checksum against published hashes, downloads Rufus 4.6 portable, and launches Rufus for USB flashing.

- **`setup.sh`** -- Second entry point. Run on the Surface after Ubuntu is installed from USB. Installs git/curl, configures passwordless sudo, installs Claude Code, and copies context files from `claude-context/` into Claude's memory directory and `CLAUDE.md` to the repo root.

- **`CLAUDE.md`** -- Third entry point (AI). Read by Claude Code when the user says "continue setup". Contains the 5-phase install sequence that Claude executes as commands.

- **`diagnose_arms.py`** -- Post-setup entry point. Run after the SO-101 arms are connected to diagnose hardware issues.

## File Organization Patterns

### Scripts by execution environment

| Environment | Files | Language |
|------------|-------|----------|
| Windows (PowerShell) | `flash.ps1` | PowerShell 5.1 |
| Linux (shell) | `setup.sh`, `phase1-surface-kernel.sh` | Bash |
| Linux (Python, in venv) | `diagnose_arms.py`, `monitor_arm.py`, `exercise_arm.py`, `teleop_monitor.py` | Python 3.12 |
| AI Agent (Claude Code) | `CLAUDE.md` | Markdown (structured instructions) |

### Naming conventions

- Shell scripts: `*.sh` with `#!/usr/bin/env bash` and `set -euo pipefail`
- Python scripts: `*_arm*.py` or `*_monitor.py`, all with docstrings and `argparse` CLIs
- Documentation: `*.md` in `docs/` or project root
- AI context: files in `claude-context/` with frontmatter metadata

## Key File Types

### PowerShell Scripts (`.ps1`)

- **Pattern:** `*.ps1`
- **Purpose:** Windows-side automation (USB flashing)
- **Examples:** `flash.ps1` -- downloads ISO, verifies checksum, launches Rufus

### Bash Scripts (`.sh`)

- **Pattern:** `*.sh`
- **Purpose:** Linux bootstrap and standalone install phases
- **Examples:** `setup.sh` (bootstrap), `phase1-surface-kernel.sh` (kernel install)

### Python Diagnostic Scripts (`.py`)

- **Pattern:** `*.py` at project root
- **Purpose:** Hardware diagnostics, monitoring, and testing for SO-101 servo arms
- **Examples:** `diagnose_arms.py`, `monitor_arm.py`, `exercise_arm.py`, `teleop_monitor.py`

### AI Instruction Files

- **Pattern:** `CLAUDE.md`, `claude-context/memory/*.md`
- **Purpose:** Structured instructions and context for Claude Code AI agent
- **Examples:** `CLAUDE.md` (5-phase setup), `hardware_surface-pro-7.md` (hardware reference)

## Configuration Files

- **`.gitignore`**: Ignores `downloads/` (ISO files) and `CLAUDE.md` (generated from claude-context/ by setup.sh)
- **`_bmad/bmm/config.yaml`**: BMAD Method configuration (project name, paths, user settings)
- **`.claude/settings.json`**: Claude Code project-level settings

## Notes for Development

- All Python scripts require the `~/lerobot-env` virtual environment to be activated first
- Python scripts import from `lerobot.motors.feetech.feetech` -- this is the LeRobot v0.5.0 Feetech motor bus API
- Serial port paths are hardcoded (`/dev/ttyACM0` for follower, `/dev/ttyACM1` for leader) but can be overridden via CLI flags
- Calibration files are expected at `~/.cache/huggingface/lerobot/calibration/` (generated by LeRobot's calibration process)
- The `CLAUDE.md` in the repo root is git-ignored because it's generated by `setup.sh` from `claude-context/CLAUDE.md`

---

_Generated using BMAD Method `document-project` workflow_
