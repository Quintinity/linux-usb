#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# armOS — Raspberry Pi 5 + AI HAT+ Setup Script
# ============================================================================
# Run this ON the Pi after first boot (via SSH or local terminal).
# Installs: Python 3.11, LeRobot 0.5.0, Hailo runtime, picamera2,
#           Feetech servo SDK, armOS diagnostic tools, udev rules.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Quintinity/linux-usb/main/pi-setup.sh | bash
#   OR
#   git clone https://github.com/Quintinity/linux-usb.git ~/linux-usb && cd ~/linux-usb && chmod +x pi-setup.sh && ./pi-setup.sh
# ============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;91m'
NC='\033[0m'

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  armOS — Raspberry Pi 5 Setup${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# ── Step 1: Verify we're on RPi 5 ───────────────────────────────────────────
echo -e "${YELLOW}[1/9] Checking hardware...${NC}"
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model | tr -d '\0')
    echo -e "  ${GREEN}Board: $MODEL${NC}"
else
    echo -e "  ${RED}Cannot detect board model. Are you on a Raspberry Pi?${NC}"
    exit 1
fi

# Check for AI HAT
if [ -e /dev/hailo0 ] || lspci 2>/dev/null | grep -qi hailo; then
    echo -e "  ${GREEN}AI HAT: Detected${NC}"
    HAS_HAILO=true
else
    echo -e "  ${YELLOW}AI HAT: Not detected (will install support anyway)${NC}"
    HAS_HAILO=false
fi

# Check for CSI camera
if libcamera-hello --list-cameras 2>/dev/null | grep -q "imx708"; then
    echo -e "  ${GREEN}Camera: Pi Camera Module 3 detected${NC}"
elif libcamera-hello --list-cameras 2>/dev/null | grep -q "Available"; then
    echo -e "  ${YELLOW}Camera: CSI camera detected (not Module 3)${NC}"
else
    echo -e "  ${YELLOW}Camera: No CSI camera detected (will work with USB cameras)${NC}"
fi

# ── Step 2: System update + core packages ────────────────────────────────────
echo -e "${YELLOW}[2/9] Installing system packages...${NC}"
sudo apt update
sudo apt install -y git curl wget build-essential cmake pkg-config \
    python3-dev python3-venv python3-pip \
    libglib2.0-0 libegl1-mesa-dev libgl1 \
    libusb-1.0-0-dev v4l-utils ffmpeg \
    libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
    libswscale-dev libswresample-dev libavfilter-dev \
    libgeos-dev portaudio19-dev \
    python3-picamera2 --no-install-recommends \
    dkms

# ── Step 3: Install Python 3.11 (if on Trixie with 3.13) ────────────────────
echo -e "${YELLOW}[3/9] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f1,2)

if [ "$PYTHON_MAJOR_MINOR" = "3.11" ] || [ "$PYTHON_MAJOR_MINOR" = "3.12" ]; then
    echo -e "  ${GREEN}Python $PYTHON_VERSION — compatible with LeRobot${NC}"
    PYTHON_CMD=python3
else
    echo -e "  ${YELLOW}Python $PYTHON_VERSION — installing Python 3.11 for LeRobot compatibility...${NC}"
    sudo apt install -y python3.11 python3.11-dev python3.11-venv || {
        # If not in repos, build from source
        echo -e "  ${YELLOW}Building Python 3.11 from source...${NC}"
        sudo apt install -y libffi-dev libssl-dev zlib1g-dev libbz2-dev \
            libreadline-dev libsqlite3-dev liblzma-dev
        cd /tmp
        wget -q https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
        tar xzf Python-3.11.9.tgz
        cd Python-3.11.9
        ./configure --enable-optimizations --prefix=/usr/local
        make -j$(nproc)
        sudo make altinstall
        cd ~
    }
    PYTHON_CMD=python3.11
fi

# ── Step 4: Install Hailo runtime ────────────────────────────────────────────
echo -e "${YELLOW}[4/9] Installing Hailo AI HAT support...${NC}"
if dpkg -l | grep -q hailo-all 2>/dev/null; then
    echo -e "  ${GREEN}hailo-all already installed${NC}"
else
    sudo apt install -y hailo-all || {
        echo -e "  ${YELLOW}hailo-all not available in repos — AI HAT features will be unavailable${NC}"
        echo -e "  ${YELLOW}Install manually later: sudo apt install hailo-all${NC}"
    }
fi

# Verify Hailo
if [ -e /dev/hailo0 ]; then
    hailortcli fw-control identify 2>/dev/null && echo -e "  ${GREEN}Hailo device responding${NC}" || true
fi

# ── Step 5: Create Python venv with system site-packages ─────────────────────
echo -e "${YELLOW}[5/9] Creating Python virtual environment...${NC}"
VENV_DIR=~/armos-env

if [ -d "$VENV_DIR" ]; then
    echo -e "  ${GREEN}Venv already exists at $VENV_DIR${NC}"
else
    # --system-site-packages needed for picamera2 (depends on system libcamera)
    $PYTHON_CMD -m venv --system-site-packages "$VENV_DIR"
    echo -e "  ${GREEN}Created venv at $VENV_DIR${NC}"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip

# ── Step 6: Install LeRobot ──────────────────────────────────────────────────
echo -e "${YELLOW}[6/9] Installing LeRobot v0.5.0...${NC}"
pip install "lerobot==0.5.0" || {
    echo -e "  ${YELLOW}LeRobot 0.5.0 failed — trying from source...${NC}"
    pip install "lerobot>=0.4.0"
}

# Install Feetech SDK
pip install feetech-servo-sdk

# Verify
python -c "import lerobot; print(f'LeRobot {lerobot.__version__} installed')" || {
    echo -e "  ${RED}LeRobot import failed — check errors above${NC}"
}

# ── Step 7: Apply LeRobot patches (sync_read retry fix) ─────────────────────
echo -e "${YELLOW}[7/9] Applying LeRobot patches...${NC}"

SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")

# Patch 1: sync_read retries in follower
FOLLOWER_FILE="$SITE_PACKAGES/lerobot/robots/so_follower/so_follower.py"
if [ -f "$FOLLOWER_FILE" ]; then
    if grep -q 'num_retry=10' "$FOLLOWER_FILE"; then
        echo -e "  ${GREEN}Follower retry patch already applied${NC}"
    else
        sed -i 's/self.bus.sync_read("Present_Position")/self.bus.sync_read("Present_Position", num_retry=10)/' "$FOLLOWER_FILE"
        echo -e "  ${GREEN}Applied follower sync_read retry patch${NC}"
    fi
fi

# Patch 2: sync_read retries in leader
LEADER_FILE="$SITE_PACKAGES/lerobot/teleoperators/so_leader/so_leader.py"
if [ -f "$LEADER_FILE" ]; then
    if grep -q 'num_retry=10' "$LEADER_FILE"; then
        echo -e "  ${GREEN}Leader retry patch already applied${NC}"
    else
        sed -i 's/self.bus.sync_read("Present_Position")/self.bus.sync_read("Present_Position", num_retry=10)/' "$LEADER_FILE"
        echo -e "  ${GREEN}Applied leader sync_read retry patch${NC}"
    fi
fi

# Patch 3: port flush on retry in motors_bus
MOTORS_FILE="$SITE_PACKAGES/lerobot/motors/motors_bus.py"
if [ -f "$MOTORS_FILE" ]; then
    if grep -q 'clearPort' "$MOTORS_FILE"; then
        echo -e "  ${GREEN}Port flush patch already applied${NC}"
    else
        sed -i '/self._setup_sync_reader(motor_ids, addr, length)/a\        for n_try in range(1 + num_retry):\n            if n_try > 0:\n                self.port_handler.clearPort()' "$MOTORS_FILE" 2>/dev/null || {
            echo -e "  ${YELLOW}Port flush patch requires manual application${NC}"
        }
    fi
fi

# ── Step 8: Configure udev rules and permissions ─────────────────────────────
echo -e "${YELLOW}[8/9] Configuring USB serial access...${NC}"

# Feetech servo controller udev rule
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0660", GROUP="dialout"' \
    | sudo tee /etc/udev/rules.d/99-feetech-serial.rules > /dev/null

sudo udevadm control --reload-rules
sudo usermod -aG dialout "$USER"
echo -e "  ${GREEN}Udev rules configured${NC}"

# Remove brltty if present (steals Feetech serial ports)
if dpkg -l | grep -q "ii  brltty" 2>/dev/null; then
    sudo apt remove -y brltty
    echo -e "  ${GREEN}Removed brltty (was stealing serial ports)${NC}"
fi

# ── Step 9: Copy diagnostic tools ───────────────────────────────────────────
echo -e "${YELLOW}[9/9] Setting up diagnostic tools...${NC}"

SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "$HOME/linux-usb")"

if [ -f "$SCRIPT_DIR/diagnose_arms.py" ]; then
    mkdir -p ~/armos-tools
    cp -v "$SCRIPT_DIR/diagnose_arms.py" ~/armos-tools/
    cp -v "$SCRIPT_DIR/monitor_arm.py" ~/armos-tools/
    cp -v "$SCRIPT_DIR/exercise_arm.py" ~/armos-tools/
    cp -v "$SCRIPT_DIR/teleop_monitor.py" ~/armos-tools/
    echo -e "  ${GREEN}Diagnostic tools copied to ~/armos-tools/${NC}"
else
    echo -e "  ${YELLOW}Diagnostic tools not found locally — clone the repo:${NC}"
    echo -e "  ${CYAN}git clone https://github.com/Quintinity/linux-usb.git ~/linux-usb${NC}"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  armOS RPi 5 Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${CYAN}Quick start:${NC}"
echo -e "  source ~/armos-env/bin/activate"
echo ""
echo -e "${CYAN}Detect hardware:${NC}"
echo -e "  ls /dev/ttyUSB* /dev/ttyACM*"
echo ""
echo -e "${CYAN}Test servo connection:${NC}"
echo -e "  python ~/armos-tools/diagnose_arms.py"
echo ""
echo -e "${CYAN}Monitor servos:${NC}"
echo -e "  python ~/armos-tools/monitor_arm.py --port /dev/ttyUSB0"
echo ""
echo -e "${CYAN}Run teleop (if leader arm connected):${NC}"
echo -e "  lerobot-teleoperate --robot.type=so101_follower --robot.port=/dev/ttyUSB0 --robot.id=follower --teleop.type=so101_leader --teleop.port=/dev/ttyUSB1 --teleop.id=leader"
echo ""
if [ "$HAS_HAILO" = true ]; then
    echo -e "${CYAN}Test Hailo:${NC}"
    echo -e "  hailortcli fw-control identify"
    echo ""
fi
echo -e "${YELLOW}NOTE: Log out and back in (or reboot) for dialout group to take effect.${NC}"
echo ""
