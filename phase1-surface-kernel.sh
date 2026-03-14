#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[1/4] Importing linux-surface GPG key...${NC}"
wget -qO - https://raw.githubusercontent.com/linux-surface/linux-surface/master/pkg/keys/surface.asc \
  | gpg --dearmor | sudo dd of=/etc/apt/trusted.gpg.d/linux-surface.gpg

echo -e "${YELLOW}[2/4] Adding linux-surface repository...${NC}"
echo "deb [arch=amd64] https://pkg.surfacelinux.com/debian release main" \
  | sudo tee /etc/apt/sources.list.d/linux-surface.list

echo -e "${YELLOW}[3/4] Installing surface kernel packages...${NC}"
sudo apt update
sudo apt install -y linux-image-surface linux-headers-surface libwacom-surface iptsd

echo -e "${YELLOW}[4/4] Updating GRUB...${NC}"
sudo update-grub

echo ""
echo -e "${GREEN}Phase 1 complete!${NC}"
echo "Please reboot now, then come back and say: continue setup -- phase 2"
