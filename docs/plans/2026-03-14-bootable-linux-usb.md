# Bootable Linux USB for LeRobot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a bootable Ubuntu 24.04 USB stick that, once installed on a Surface Pro 7, bootstraps Claude Code to finish configuring itself for LeRobot SO-101 development.

**Architecture:** Two-phase approach. Phase 1 runs on Windows (download ISO, flash USB). Phase 2 runs on the Surface after Ubuntu install — a minimal `setup.sh` installs Claude Code, lays down memory/context files, then Claude takes over to install linux-surface kernel, system packages, Python venv, LeRobot v0.5.0, and Feetech servo tooling.

**Tech Stack:** Ubuntu 24.04 LTS, linux-surface kernel, Python 3.12, LeRobot v0.5.0, Feetech SDK, Claude Code CLI

**Hardware:** Surface Pro 7 — Intel i5, 8GB RAM, 64GB SanDisk USB (D:), USB wireless keyboard via dongle, multi-port USB adapter

---

### Task 1: Create Boot Guide

The manual steps the user follows between Phase 1 and Phase 2. This can't be automated.

**Files:**
- Create: `docs/BOOT-GUIDE.md`

**Step 1: Write the boot guide**

```markdown
# Boot Guide — Installing Ubuntu to USB via toram

## Prerequisites
- 64GB+ USB stick (flashed with Ubuntu 24.04 by flash.ps1)
- USB wireless keyboard + dongle
- Multi-port USB adapter
- Surface Pro 7

## Step 1: Disable Secure Boot on Surface
1. Shut down the Surface completely
2. Hold Volume Up + press Power, release Power when logo appears
3. In UEFI: Security > Secure Boot > Disable
4. Save and exit

## Step 2: Boot from USB
1. Plug USB stick + keyboard dongle into Surface via adapter
2. Shut down Surface
3. Hold Volume Down + press Power to boot from USB
4. At GRUB menu, press 'e' to edit the boot entry
5. Find the line starting with `linux` and add `toram` at the end
6. Press F10 to boot

## Step 3: Wait for Live Environment
- Ubuntu loads entirely into RAM (~3-4 minutes on USB 3.0)
- Once desktop appears, verify keyboard works

## Step 4: Connect to WiFi
- Click network icon in system tray
- Connect to your WiFi network

## Step 5: Remove and Re-insert USB
1. Open terminal (Ctrl+Alt+T or on-screen keyboard)
2. Run: `sudo umount /dev/sd*` (unmount all USB partitions)
3. Physically remove the USB stick
4. Wait 5 seconds
5. Re-insert the USB stick
6. Run: `lsblk` to identify the USB (likely /dev/sda)

## Step 6: Install Ubuntu to USB
1. Double-click "Install Ubuntu" on desktop
2. Follow installer normally until disk selection
3. Choose "Something else" (manual partitioning)
4. Select your USB drive (check size matches ~64GB)
5. Delete all existing partitions on the USB
6. Create partitions:
   - 512MB EFI System Partition (FAT32, mount /boot/efi)
   - Remaining space as ext4 (mount /)
7. **CRITICAL: Set bootloader location to the USB drive (e.g., /dev/sda), NOT the internal drive**
8. Complete installation

## Step 7: Reboot into Installed Ubuntu
1. Remove USB when prompted
2. Re-insert USB
3. Boot Surface from USB (Volume Down + Power)
4. You should see GRUB → Ubuntu

## Step 8: Run Setup
1. Connect to WiFi
2. Open terminal
3. Run:
   ```bash
   sudo apt update && sudo apt install -y git
   git clone https://github.com/Quintinity/linux-usb.git ~/linux-usb
   cd ~/linux-usb
   chmod +x setup.sh
   ./setup.sh
   ```
4. When prompted, authenticate Claude Code in browser
5. Run: `claude`
6. Say: "continue setup"
```

**Step 2: Commit**

```bash
git add docs/BOOT-GUIDE.md
git commit -m "docs: add boot guide for toram USB install method"
```

---

### Task 2: Create Flash Script

Downloads Ubuntu 24.04 ISO, verifies checksum, downloads Rufus portable, and launches Rufus with the ISO. Runs on Windows (PowerShell).

**Files:**
- Create: `flash.ps1`

**Step 1: Write the flash script**

```powershell
# flash.ps1 — Download Ubuntu 24.04 and flash to USB
# Run from PowerShell on Windows: .\flash.ps1

$ErrorActionPreference = "Stop"
$DownloadDir = "$PSScriptRoot\downloads"
$IsoUrl = "https://releases.ubuntu.com/24.04.2/ubuntu-24.04.2-desktop-amd64.iso"
$IsoFile = "$DownloadDir\ubuntu-24.04.2-desktop-amd64.iso"
$Sha256Url = "https://releases.ubuntu.com/24.04.2/SHA256SUMS"
$Sha256File = "$DownloadDir\SHA256SUMS"
$RufusUrl = "https://github.com/pbatard/rufus/releases/download/v4.6/rufus-4.6p.exe"
$RufusFile = "$DownloadDir\rufus-4.6p.exe"

Write-Host "=== Linux USB Flash Tool ===" -ForegroundColor Cyan

# Create download directory
if (!(Test-Path $DownloadDir)) { New-Item -ItemType Directory -Path $DownloadDir | Out-Null }

# Download Ubuntu ISO
if (!(Test-Path $IsoFile)) {
    Write-Host "Downloading Ubuntu 24.04.2 LTS ISO (~6GB)..." -ForegroundColor Yellow
    Write-Host "URL: $IsoUrl"
    Start-BitsTransfer -Source $IsoUrl -Destination $IsoFile -Description "Ubuntu ISO"
    Write-Host "Download complete." -ForegroundColor Green
} else {
    Write-Host "ISO already downloaded: $IsoFile" -ForegroundColor Green
}

# Download and verify checksum
Write-Host "Downloading SHA256 checksums..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $Sha256Url -OutFile $Sha256File

$ExpectedHash = (Get-Content $Sha256File | Select-String "ubuntu-24.04.2-desktop-amd64.iso").ToString().Split(" ")[0]
Write-Host "Verifying ISO checksum..." -ForegroundColor Yellow
$ActualHash = (Get-FileHash -Path $IsoFile -Algorithm SHA256).Hash.ToLower()

if ($ActualHash -ne $ExpectedHash) {
    Write-Host "CHECKSUM MISMATCH! ISO may be corrupted." -ForegroundColor Red
    Write-Host "Expected: $ExpectedHash"
    Write-Host "Actual:   $ActualHash"
    exit 1
}
Write-Host "Checksum verified." -ForegroundColor Green

# Download Rufus portable
if (!(Test-Path $RufusFile)) {
    Write-Host "Downloading Rufus 4.6 portable..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $RufusUrl -OutFile $RufusFile
    Write-Host "Download complete." -ForegroundColor Green
} else {
    Write-Host "Rufus already downloaded: $RufusFile" -ForegroundColor Green
}

# Launch Rufus
Write-Host ""
Write-Host "=== INSTRUCTIONS ===" -ForegroundColor Cyan
Write-Host "Rufus will open. Configure:" -ForegroundColor Yellow
Write-Host "  1. Device: Select your 64GB USB stick"
Write-Host "  2. Boot selection: Click SELECT -> choose: $IsoFile"
Write-Host "  3. Partition scheme: GPT"
Write-Host "  4. Target system: UEFI"
Write-Host "  5. Click START"
Write-Host ""
Write-Host "Launching Rufus..." -ForegroundColor Cyan
Start-Process -FilePath $RufusFile -Wait

Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Green
Write-Host "USB is ready. Follow docs/BOOT-GUIDE.md for next steps."
```

**Step 2: Add downloads/ to .gitignore**

Create `.gitignore`:
```
downloads/
```

**Step 3: Commit**

```bash
git add flash.ps1 .gitignore
git commit -m "feat: add flash script to download Ubuntu ISO and launch Rufus"
```

---

### Task 3: Create Bootstrap Setup Script

Minimal script that runs on the Surface after Ubuntu is installed. Installs Claude Code and lays down context files. Claude does the rest.

**Files:**
- Create: `setup.sh`

**Step 1: Write setup.sh**

```bash
#!/usr/bin/env bash
# setup.sh — Bootstrap Claude Code on fresh Ubuntu USB install
# Run: chmod +x setup.sh && ./setup.sh
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=== Linux USB Bootstrap ===${NC}"
echo -e "${YELLOW}Surface Pro 7 — LeRobot SO-101 Setup${NC}"
echo ""

# Step 1: Ensure git and curl are available
echo -e "${CYAN}[1/4] Installing prerequisites...${NC}"
sudo apt update
sudo apt install -y git curl

# Step 2: Install Claude Code
echo -e "${CYAN}[2/4] Installing Claude Code...${NC}"
if ! command -v claude &> /dev/null; then
    curl -fsSL https://claude.ai/install.sh | bash
    export PATH="$HOME/.claude/bin:$PATH"
else
    echo "Claude Code already installed."
fi

# Step 3: Set up Claude memory and project context
echo -e "${CYAN}[3/4] Setting up Claude context...${NC}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create Claude project memory directory
CLAUDE_MEMORY_DIR="$HOME/.claude/projects/$(echo "$REPO_DIR" | sed 's|/|--|g' | sed 's|^--||')/memory"
mkdir -p "$CLAUDE_MEMORY_DIR"

# Copy pre-built memory files
if [ -d "$REPO_DIR/claude-context/memory" ]; then
    cp -r "$REPO_DIR/claude-context/memory/"* "$CLAUDE_MEMORY_DIR/"
    echo "Claude memory files installed."
fi

# Copy CLAUDE.md to repo root if not already there
if [ -f "$REPO_DIR/claude-context/CLAUDE.md" ] && [ ! -f "$REPO_DIR/CLAUDE.md" ]; then
    cp "$REPO_DIR/claude-context/CLAUDE.md" "$REPO_DIR/CLAUDE.md"
    echo "CLAUDE.md installed."
fi

# Step 4: Instructions
echo ""
echo -e "${GREEN}=== Bootstrap Complete ===${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo "  1. Run: claude"
echo "  2. Authenticate in browser when prompted"
echo "  3. Say: continue setup"
echo ""
echo -e "${YELLOW}Claude will then:${NC}"
echo "  - Install linux-surface kernel (requires reboot)"
echo "  - Install system packages"
echo "  - Set up Python 3.12 + LeRobot v0.5.0"
echo "  - Configure SO-101 Feetech servo access"
echo "  - Verify everything works"
echo ""
```

**Step 2: Commit**

```bash
git add setup.sh
git commit -m "feat: add bootstrap setup script for Claude Code installation"
```

---

### Task 4: Create Claude Context Files

These files give Claude on the Surface full knowledge of what to do. Stored in repo under `claude-context/` and copied into place by `setup.sh`.

**Files:**
- Create: `claude-context/CLAUDE.md`
- Create: `claude-context/memory/MEMORY.md`
- Create: `claude-context/memory/project_surface-lerobot.md`
- Create: `claude-context/memory/hardware_surface-pro-7.md`

**Step 1: Write CLAUDE.md**

```markdown
# Linux USB — Surface Pro 7 LeRobot Setup

This repo configures a bootable Ubuntu 24.04 USB stick for running
HuggingFace LeRobot (v0.5.0) with an SO-101 robot arm on a Surface Pro 7.

## "continue setup" Command

When the user says "continue setup", execute the following phases IN ORDER.
After each phase, verify success before proceeding. If anything fails, debug
and fix before moving on.

### Phase 1: linux-surface Kernel

```bash
wget -qO - https://raw.githubusercontent.com/linux-surface/linux-surface/master/pkg/keys/surface.asc \
  | gpg --dearmor | sudo dd of=/etc/apt/trusted.gpg.d/linux-surface.gpg

echo "deb [arch=amd64] https://pkg.surfacelinux.com/debian release main" \
  | sudo tee /etc/apt/sources.list.d/linux-surface.list

sudo apt update
sudo apt install -y linux-image-surface linux-headers-surface libwacom-surface iptsd
sudo update-grub
```

Then tell the user: "linux-surface kernel installed. Please reboot now
(`sudo reboot`), then open terminal, cd to this repo, and run `claude` again.
Say 'continue setup — phase 2'."

### Phase 2: System Packages

```bash
sudo apt update && sudo apt install -y \
  build-essential cmake pkg-config ninja-build \
  python3.12-dev python3.12-venv python3-pip \
  git curl wget ffmpeg \
  libglib2.0-0 libegl1-mesa-dev libgl1-mesa-glx \
  libusb-1.0-0-dev \
  libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
  libswscale-dev libswresample-dev libavfilter-dev \
  libgeos-dev portaudio19-dev speech-dispatcher \
  v4l-utils intel-microcode linux-firmware
```

Verify: `python3.12 --version` should print 3.12.x.
Verify: `ffmpeg -version` should show ffmpeg 7.x.

### Phase 3: LeRobot + SO-101

```bash
python3.12 -m venv ~/lerobot-env
source ~/lerobot-env/bin/activate
pip install --upgrade pip
pip install "lerobot==0.5.0"
```

Verify: `python -c "import lerobot; print(lerobot.__version__)"` → `0.5.0`

### Phase 4: USB Serial (Feetech SO-101)

Create udev rule for Feetech serial adapters:
```bash
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout"' \
  | sudo tee /etc/udev/rules.d/99-feetech-serial.rules
sudo udevadm control --reload-rules
sudo usermod -aG dialout $USER
```

Tell user: "Serial permissions set. You may need to log out and back in
for group changes to take effect."

### Phase 5: Verification

Run each and confirm output:
1. `uname -r` — should contain "surface"
2. `python3.12 --version` — 3.12.x
3. `source ~/lerobot-env/bin/activate && python -c "import lerobot; print(lerobot.__version__)"` — 0.5.0
4. `lsmod | grep surface` — should show surface modules
5. `ls /dev/ttyACM*` — (only if servo controller is plugged in)

Print a summary of pass/fail for each check.

## Environment Notes
- No CUDA — Intel integrated GPU only. Training must be offloaded to cloud.
- Built-in Surface cameras do NOT work. Use external USB cameras.
- Feetech motor firmware updates require Windows.
- Python venv lives at ~/lerobot-env — always activate before using LeRobot.
```

**Step 2: Write memory/MEMORY.md**

```markdown
# Claude Memory — Surface Pro 7 LeRobot USB

## Hardware
- [hardware_surface-pro-7.md](hardware_surface-pro-7.md) — Surface Pro 7 specs and Linux notes

## Project
- [project_surface-lerobot.md](project_surface-lerobot.md) — Setup status and what needs to be done
```

**Step 3: Write memory/hardware_surface-pro-7.md**

```markdown
---
name: Surface Pro 7 Hardware
description: Hardware specs and Linux compatibility notes for the Surface Pro 7 used for LeRobot
type: reference
---

- Surface Pro 7, Intel i5-1035G4, 8GB RAM
- Intel WiFi 6 AX201 — works on stock Ubuntu kernel (iwlwifi)
- Type Cover keyboard — requires linux-surface kernel
- Touchscreen — requires linux-surface kernel + iptsd
- Built-in cameras — NOT working on Linux (IPU6, no driver)
- Intel Iris Plus Graphics — no CUDA, CPU-only for ML inference
- USB-A port x1, USB-C port x1, using multi-port adapter for more
- USB wireless keyboard with 2.4GHz dongle for input
```

**Step 4: Write memory/project_surface-lerobot.md**

```markdown
---
name: Surface LeRobot Setup Status
description: Tracks setup progress for LeRobot SO-101 on Surface Pro 7 bootable USB
type: project
---

Setup was initiated from a Windows machine (Bradley's main laptop).
The USB was flashed with Ubuntu 24.04.2 LTS and the user installed Ubuntu
onto the USB drive using the toram method.

setup.sh has been run — Claude Code is installed.

**Remaining setup phases:**
1. Install linux-surface kernel → reboot required
2. Install system packages (build tools, ffmpeg, libs)
3. Install LeRobot v0.5.0 in Python 3.12 venv with SO-101 support
4. Configure udev rules for Feetech serial adapters
5. Run verification checks

**Why:** This USB stick will be used to run LeRobot framework with an SO-101 robot arm (Feetech servos). The Surface Pro 7 is a dedicated device for this purpose.

**How to apply:** Follow the phases in CLAUDE.md exactly. After Phase 1, a reboot is required. The user will return and say "continue setup — phase 2" to resume.
```

**Step 5: Commit**

```bash
git add claude-context/
git commit -m "feat: add Claude context files for automated Surface setup"
```

---

### Task 5: Update README and Final Commit

**Files:**
- Modify: `README.md`

**Step 1: Update README with usage instructions**

Add a "Quick Start" section at the top that references both scripts and the boot guide:

```markdown
## Quick Start

### Phase 1 — Flash USB (on Windows)
1. Open PowerShell in this repo
2. Run: `.\flash.ps1`
3. Follow Rufus instructions to flash the USB

### Phase 2 — Install Ubuntu (on Surface)
Follow [docs/BOOT-GUIDE.md](docs/BOOT-GUIDE.md) for the toram install method.

### Phase 3 — Configure (on Surface, after Ubuntu installed)
```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/Quintinity/linux-usb.git ~/linux-usb
cd ~/linux-usb
chmod +x setup.sh
./setup.sh
claude
# Say: "continue setup"
```
```

**Step 2: Commit and push**

```bash
git add README.md
git commit -m "docs: add quick start guide to README"
git push
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Boot guide (manual steps) | `docs/BOOT-GUIDE.md` |
| 2 | Flash script (Windows) | `flash.ps1`, `.gitignore` |
| 3 | Bootstrap script (Surface) | `setup.sh` |
| 4 | Claude context files | `claude-context/CLAUDE.md`, `claude-context/memory/*` |
| 5 | README update | `README.md` |
