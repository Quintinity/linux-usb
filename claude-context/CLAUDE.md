# Surface Pro 7 — LeRobot SO-101 Setup

This machine is a Surface Pro 7 running Ubuntu 24.04.2, being set up as a LeRobot SO-101 control station.

## Continue Setup

When the user says **"continue setup"**, execute the 5 phases below IN ORDER. Each phase must complete successfully before moving to the next. After Phase 1, the user must reboot — wait for them to return and say "continue setup — phase 2" before proceeding.

---

### Phase 1: linux-surface Kernel

Install the linux-surface kernel for proper hardware support (Type Cover, touchscreen, etc.):

```bash
wget -qO - https://raw.githubusercontent.com/linux-surface/linux-surface/master/pkg/keys/surface.asc \
  | gpg --dearmor | sudo dd of=/etc/apt/trusted.gpg.d/linux-surface.gpg
echo "deb [arch=amd64] https://pkg.surfacelinux.com/debian release main" \
  | sudo tee /etc/apt/sources.list.d/linux-surface.list
sudo apt update
sudo apt install -y linux-image-surface linux-headers-surface libwacom-surface iptsd
sudo update-grub
```

After this completes, tell the user: **"Phase 1 complete. Please reboot now. When you're back, say 'continue setup — phase 2'."**

Do NOT proceed to Phase 2 until the user returns after rebooting.

---

### Phase 2: System Packages

Install all required system dependencies:

```bash
sudo apt update && sudo apt install -y build-essential cmake pkg-config ninja-build python3.12-dev python3.12-venv python3-pip git curl wget ffmpeg libglib2.0-0 libegl1-mesa-dev libgl1 libusb-1.0-0-dev libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libswresample-dev libavfilter-dev libgeos-dev portaudio19-dev speech-dispatcher v4l-utils intel-microcode linux-firmware
```

**Note:** Keep this as a single line. Backslash line continuations break when the terminal wraps long lines.

**Verify:**
```bash
python3.12 --version
ffmpeg -version
```

Both commands must succeed before proceeding.

---

### Phase 3: LeRobot + SO-101

Create the Python virtual environment and install LeRobot:

```bash
python3.12 -m venv ~/lerobot-env
source ~/lerobot-env/bin/activate
pip install --upgrade pip
pip install "lerobot==0.5.0"
```

**Verify:**
```bash
source ~/lerobot-env/bin/activate
python -c "import lerobot; print(lerobot.__version__)"
```

Must print `0.5.0`.

---

### Phase 4: USB Serial (Feetech SO-101)

Configure udev rules so the Feetech servo controller is accessible without root:

```bash
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout"' \
  | sudo tee /etc/udev/rules.d/99-feetech-serial.rules
sudo udevadm control --reload-rules
sudo usermod -aG dialout $USER
```

---

### Phase 5: Verification

Run all checks to confirm the setup is complete:

```bash
uname -r                    # Must contain "surface"
python3.12 --version        # Must be 3.12.x
source ~/lerobot-env/bin/activate
python -c "import lerobot; print(lerobot.__version__)"  # Must be 0.5.0
lsmod | grep surface        # Should show surface modules
```

Report results to the user. If all pass, setup is complete.

---

## Environment Notes

- **No CUDA** — This machine has an Intel Iris Plus GPU (i5-1035G4). All training must be done in the cloud. This machine is for inference and data collection only.
- **Built-in cameras do not work** under Linux on the Surface Pro 7. Use USB cameras for LeRobot data collection.
- **Feetech servo firmware updates require Windows.** If servos need firmware updates, do that on a Windows machine first.
- **Python virtual environment** is at `~/lerobot-env`. Always activate it before running LeRobot commands.
- **USB ports:** 1x USB-A, 1x USB-C. A multi-port adapter is available for connecting multiple devices (cameras + servo controller).
- **Keyboard:** USB wireless keyboard (the Type Cover works after linux-surface kernel is installed).

---

## Lessons Learned (2026-03-14)

### Terminal line wrapping breaks multi-line bash commands
Long `apt install` commands using backslash continuations (`\`) break when the terminal wraps mid-line — the shell interprets the next line as a new command, causing package names to be run as commands and silently skipped. **Fix:** always write long apt install lines as a single unbroken line.

### Claude Code needs passwordless sudo to run commands autonomously
Without a NOPASSWD sudoers entry, Claude Code cannot run `sudo` commands — it has no terminal to enter a password. This forced the user to manually run every sudo command during Phase 2. **Fix:** `setup.sh` now adds the NOPASSWD entry before launching Claude, so all subsequent phases run unattended.

### Split long installs into logical groups if debugging
If running commands manually in a narrow terminal, split apt installs into thematic groups (build tools, Python, AV libs, etc.) rather than one giant command — easier to diagnose failures.

---

## Improvements for Next Install

- [x] Add NOPASSWD sudoers entry to `setup.sh` before launching Claude (eliminates all manual sudo steps)
- [x] Replace backslash-continuation apt commands with single-line versions
- [ ] Consider a `phase2.sh` script that can be run directly, bypassing terminal width issues entirely
- [ ] Add `sudo apt-get -y upgrade` after `apt update` in Phase 2 to pull in security patches on first boot
