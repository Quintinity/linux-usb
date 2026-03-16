#!/bin/bash
set -euo pipefail

# armOS USB Flash Script (Linux/macOS)
# Usage: sudo ./image/flash.sh path/to/armos.iso /dev/sdX

ISO="${1:-}"
DEVICE="${2:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [[ -z "$ISO" || -z "$DEVICE" ]]; then
    echo "Usage: sudo $0 <iso-file> <device>"
    echo ""
    echo "Example: sudo $0 armos-v2.0.iso /dev/sdb"
    echo ""
    echo "Available USB devices:"
    lsblk -d -o NAME,SIZE,TYPE,TRAN | grep -E "usb|removable" || echo "  (none found — plug in a USB stick)"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Must run as root: sudo $0 $*${NC}"
    exit 1
fi

if [[ ! -f "$ISO" ]]; then
    echo -e "${RED}ISO not found: $ISO${NC}"
    exit 1
fi

if [[ ! -b "$DEVICE" ]]; then
    echo -e "${RED}Device not found: $DEVICE${NC}"
    exit 1
fi

SIZE=$(du -h "$ISO" | cut -f1)
echo -e "${YELLOW}WARNING: This will ERASE all data on $DEVICE${NC}"
echo "  ISO: $ISO ($SIZE)"
echo "  Device: $DEVICE"
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo -e "${GREEN}Flashing...${NC}"
dd if="$ISO" of="$DEVICE" bs=4M status=progress conv=fsync
sync

echo -e "${GREEN}Done! Remove the USB stick and boot from it.${NC}"
