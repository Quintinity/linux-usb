#!/usr/bin/env bash
# Provisions the Jetson Orin Nano Super for citizenry-jetson.service.
#
# Run once on the Jetson:
#   bash jetson-setup.sh
#
# Idempotent: safe to re-run; skips steps already completed.

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;91m'
NC='\033[0m'

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  citizenry Jetson setup${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""

# ── Step 1: Verify environment ───────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Verifying environment...${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}python3 not found — install Python 3 first${NC}"
    exit 1
fi
echo -e "  ${GREEN}python3: $(python3 --version)${NC}"

if ! python3 -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
    echo -e "${RED}torch with CUDA not available.${NC}"
    echo -e "${YELLOW}On JetPack 6 install torch via: pip install torch torchvision (wheel from Jetson)${NC}"
    exit 1
fi
echo -e "  ${GREEN}torch+CUDA: OK${NC}"

# ── Step 2: HF token prompt (idempotent) ─────────────────────────────────────
echo -e "${YELLOW}[2/4] HuggingFace token...${NC}"

if [ -f "$HOME/.citizenry/hf_token" ]; then
    echo -e "  ${GREEN}HF token already installed at ~/.citizenry/hf_token${NC}"
else
    echo -ne "  ${CYAN}Paste HuggingFace read/write token (input hidden): ${NC}"
    read -r -s TOKEN
    echo
    if [ -z "$TOKEN" ]; then
        echo -e "  ${YELLOW}Empty token — skipping. Set manually: echo -n TOKEN > ~/.citizenry/hf_token${NC}"
    else
        mkdir -p "$HOME/.citizenry"
        echo -n "$TOKEN" > "$HOME/.citizenry/hf_token"
        chmod 600 "$HOME/.citizenry/hf_token"
        echo -e "  ${GREEN}HF token installed${NC}"
    fi
fi

# ── Step 3: systemd unit ──────────────────────────────────────────────────────
echo -e "${YELLOW}[3/4] Installing citizenry-jetson.service...${NC}"

sudo tee /etc/systemd/system/citizenry-jetson.service > /dev/null <<EOF
[Unit]
Description=armOS Jetson Citizen — policy host
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
Environment=PYTHONPATH=$HOME
ExecStart=$HOME/lerobot-env/bin/python -m citizenry.run_jetson
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable citizenry-jetson.service
echo -e "  ${GREEN}citizenry-jetson.service installed and enabled${NC}"
echo -e "  ${CYAN}Logs: journalctl -u citizenry-jetson -f${NC}"

# ── Step 4: Claude persona auto-refresh watcher ───────────────────────────────
echo -e "${YELLOW}[4/4] Installing Claude persona auto-refresh watcher...${NC}"

# Installs three user-scope systemd units:
#   claude-persona.service  — runs claude-persona-refresh.sh (oneshot)
#   claude-persona.path     — fires when ~/.citizenry/node.key appears/changes
#   claude-persona.timer    — hourly catch-all for state changes the path can't observe
# Plus enables linger so user units run without an active login.
# Plus fires the service once so the device has a current persona right now.
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "$HOME/linux-usb")"

if [ -f "$SCRIPT_DIR/scripts/install-claude-persona-watch.sh" ]; then
    bash "$SCRIPT_DIR/scripts/install-claude-persona-watch.sh" \
        || echo -e "  ${YELLOW}watcher install exited non-zero — continuing${NC}"
elif [ -f "$HOME/install-claude-persona-watch.sh" ]; then
    bash "$HOME/install-claude-persona-watch.sh" \
        || echo -e "  ${YELLOW}watcher install exited non-zero — continuing${NC}"
else
    echo -e "  ${YELLOW}install-claude-persona-watch.sh not found locally — skipping${NC}"
    echo -e "  ${CYAN}To install manually: copy scripts/install-claude-persona-watch.sh from the Surface and run it.${NC}"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}=== Jetson setup complete! ===${NC}"
echo ""
echo -e "${CYAN}Status:   sudo systemctl status citizenry-jetson${NC}"
echo -e "${CYAN}Logs:     journalctl -u citizenry-jetson -f${NC}"
echo -e "${CYAN}Start:    sudo systemctl start citizenry-jetson${NC}"
echo -e "${CYAN}Stop:     sudo systemctl stop citizenry-jetson${NC}"
echo ""
echo -e "${CYAN}Manual run:${NC}"
echo -e "  source ~/lerobot-env/bin/activate && python -m citizenry.run_jetson"
echo ""
echo -e "${YELLOW}NOTE: citizenry-jetson.service starts automatically on next boot.${NC}"
echo ""
