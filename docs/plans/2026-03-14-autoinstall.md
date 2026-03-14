# Autoinstall USB — Zero-Touch Ubuntu Setup

> **For Claude:** Future task — build a fully automated USB installer.

**Goal:** Create a USB stick that, when plugged into a Surface Pro 7 and booted, automatically installs Ubuntu 24.04, linux-surface kernel, LeRobot, and Claude Code — zero user interaction beyond the initial boot.

**Architecture:** Ubuntu autoinstall (cloud-init) with a custom ISO repack.

## How It Works

Ubuntu autoinstall uses a `user-data` YAML file that answers all installer prompts:
- Language, keyboard, timezone
- Disk selection (erase + install)
- User account creation
- Network config
- Post-install scripts (late-commands)

## Key Components

1. **autoinstall/user-data** — YAML config answering all installer prompts
2. **autoinstall/meta-data** — empty file (required by cloud-init)
3. **Custom ISO repack** — embed the autoinstall config into the Ubuntu ISO so it's detected automatically
4. **late-commands** — post-install script that runs inside the installed system to:
   - Install linux-surface kernel
   - Install system packages
   - Install Claude Code
   - Clone linux-usb repo
   - Set up LeRobot venv
   - Configure udev rules

## Example user-data

```yaml
#cloud-config
autoinstall:
  version: 1
  locale: en_NZ.UTF-8
  keyboard:
    layout: us
  identity:
    hostname: surface-lerobot
    username: bradley
    password: <hashed password>
  storage:
    layout:
      name: direct
  network:
    version: 2
    wifis:
      wlan0:
        access-points:
          "<SSID>":
            password: "<wifi-password>"
        dhcp4: true
  late-commands:
    - curtin in-target -- bash /target/linux-usb/setup-full.sh
```

## Considerations

- WiFi credentials need to be baked in or configured via ethernet
- linux-surface kernel requires a reboot mid-setup (late-commands run pre-reboot, so we'd need a first-boot systemd service for the remaining steps)
- Password must be hashed (use `mkpasswd --method=SHA-512`)
- ISO repack tools: `xorriso`, `7z`, or `cubic` (GUI)

## Status

**Deferred** — complete current manual install first, then build this for repeatable deployments.
