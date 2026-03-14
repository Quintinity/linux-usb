# linux-usb

Bootable Linux USB for running [HuggingFace LeRobot](https://github.com/huggingface/lerobot) v0.5.0 with an SO-101 robot arm on a Microsoft Surface Pro 7.

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

## What You Need

- **USB stick:** 64GB+ USB 3.0 (SanDisk recommended)
- **USB wireless keyboard** with 2.4GHz dongle (Surface Type Cover won't work until linux-surface kernel is installed)
- **Multi-port USB adapter** (for keyboard dongle + USB stick simultaneously)
- Surface Pro 7 with Secure Boot disabled

## How It Works

1. `flash.ps1` downloads Ubuntu 24.04.2 LTS and launches Rufus to flash the USB
2. You install Ubuntu onto the USB using the [toram method](docs/BOOT-GUIDE.md) (loads live image into RAM so the same USB can be reformatted)
3. `setup.sh` installs Claude Code and gives it full context about your setup
4. Claude Code takes over and installs everything else:
   - linux-surface kernel (keyboard, trackpad, touchscreen)
   - System packages (Python 3.12, FFmpeg, build tools)
   - LeRobot v0.5.0 in a Python venv
   - Feetech servo udev rules for SO-101

## Notes

- **GPU**: Intel Iris Plus — no CUDA. Training should be offloaded to cloud. Inference and data collection work fine on CPU.
- **Cameras**: Built-in Surface cameras don't work on Linux. Use external USB cameras.
- **Battery**: Expect shorter battery life than Windows.
- **Feetech firmware**: Motor firmware updates require Windows.
