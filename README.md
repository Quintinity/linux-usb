# linux-usb

Bootable Linux USB for running [HuggingFace LeRobot](https://github.com/huggingface/lerobot) on a Microsoft Surface laptop.

## Distro

**Ubuntu 24.04 LTS** — matches LeRobot's tested environment, has linux-surface kernel packages.

## What You Need

- USB stick: **64GB+ USB 3.0** (full install, not just live boot)
- USB keyboard + mouse (Surface keyboard won't work until linux-surface kernel is installed)
- The Surface laptop with Secure Boot disabled

## Setup Overview

1. Download Ubuntu 24.04 LTS ISO
2. Flash to USB with Rufus (GPT / UEFI)
3. Boot Surface from USB, run full installer **targeting the USB stick itself**
4. Install linux-surface kernel (for keyboard, trackpad, WiFi)
5. Install LeRobot dependencies
6. Install LeRobot

## LeRobot System Requirements

- Python >= 3.12
- PyTorch >= 2.2.1
- FFmpeg 7.x (with libsvtav1)
- USB serial access (`/dev/ttyACMx`) for robot arms
- USB cameras via OpenCV

## System Packages

```bash
sudo apt update && sudo apt install -y \
  build-essential cmake pkg-config ninja-build python3.12-dev python3.12-venv \
  git curl ffmpeg \
  libglib2.0-0 libegl1-mesa-dev libgl1-mesa-glx \
  libusb-1.0-0-dev \
  libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
  libswscale-dev libswresample-dev libavfilter-dev \
  libgeos-dev portaudio19-dev speech-dispatcher \
  v4l-utils
```

## linux-surface Kernel

```bash
wget -qO - https://raw.githubusercontent.com/linux-surface/linux-surface/master/pkg/keys/surface.asc \
  | gpg --dearmor | sudo dd of=/etc/apt/trusted.gpg.d/linux-surface.gpg

echo "deb [arch=amd64] https://pkg.surfacelinux.com/debian release main" \
  | sudo tee /etc/apt/sources.list.d/linux-surface.list

sudo apt update
sudo apt install -y linux-image-surface linux-headers-surface libwacom-surface iptsd
sudo update-grub && sudo reboot
```

## LeRobot Install

```bash
python3.12 -m venv ~/lerobot-env
source ~/lerobot-env/bin/activate
pip install --upgrade pip
pip install lerobot

# Verify
python -c "import lerobot; print(lerobot.__version__)"
```

## USB Serial Permissions (for robot arms)

```bash
# Quick fix
sudo chmod 666 /dev/ttyACM0

# Permanent: add udev rule
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="*", MODE="0666"' \
  | sudo tee /etc/udev/rules.d/99-serial.rules
sudo udevadm control --reload-rules
```

## Notes

- **GPU**: Surface laptops have Intel integrated graphics — no CUDA. Training should be offloaded to cloud GPU. Inference and data collection work fine on CPU.
- **Cameras**: Built-in Surface cameras won't work. Use external USB cameras.
- **Battery**: Expect shorter battery life than Windows.
- **Feetech firmware**: Motor firmware updates require Windows — keep a Windows partition or separate machine.
