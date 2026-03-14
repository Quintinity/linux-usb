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

1. **Flash** — `flash.ps1` downloads Ubuntu 24.04.2 LTS, verifies its SHA-256 checksum, and launches Rufus to flash a bootable USB
2. **Install** — You install Ubuntu onto the USB using the [toram method](docs/BOOT-GUIDE.md) (loads the live image into RAM so the same USB can be reformatted as the install target)
3. **Bootstrap** — `setup.sh` installs Claude Code, configures passwordless sudo, and copies setup instructions into Claude's context
4. **AI-driven setup** — You launch `claude` and say "continue setup". Claude Code then drives a 5-phase install autonomously:

| Phase | What it does |
|-------|-------------|
| 1. linux-surface kernel | Adds the linux-surface repo and installs the patched kernel for Type Cover, touchscreen, and trackpad support. Requires a reboot before continuing. |
| 2. System packages | Installs build tools, Python 3.12, FFmpeg, video/audio libraries, and firmware updates in a single `apt install` pass. |
| 3. LeRobot + SO-101 | Creates a Python 3.12 venv at `~/lerobot-env` and installs [LeRobot v0.5.0](https://github.com/huggingface/lerobot). |
| 4. USB serial | Writes udev rules so the Feetech servo controller is accessible without root and adds the user to the `dialout` group. |
| 5. Verification | Checks kernel version, Python version, LeRobot import, and loaded surface modules. Reports pass/fail. |

The key idea: all the domain knowledge lives in `CLAUDE.md`, so Claude Code handles the entire post-install configuration — no manual steps beyond one reboot after Phase 1.

## Notes

- **GPU**: Intel Iris Plus — no CUDA. Training should be offloaded to cloud. Inference and data collection work fine on CPU.
- **Cameras**: Built-in Surface cameras don't work on Linux. Use external USB cameras.
- **Battery**: Expect shorter battery life than Windows.
- **Feetech firmware**: Motor firmware updates require Windows.
