#!/bin/bash
set -euo pipefail

# armOS USB Image Builder
# Produces a bootable Ubuntu 24.04 live ISO with citizenry pre-installed.
#
# Usage:
#   sudo ./image/build.sh              # Build the ISO
#   sudo ./image/build.sh clean        # Clean build artifacts
#
# Requirements:
#   sudo apt-get install -y live-build

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/live-build"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${YELLOW}[BUILD]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

if [[ "${1:-}" == "clean" ]]; then
    info "Cleaning build artifacts..."
    cd "$BUILD_DIR"
    lb clean --purge 2>/dev/null || true
    success "Clean complete"
    exit 0
fi

# Check we're root
if [[ $EUID -ne 0 ]]; then
    error "Must run as root: sudo ./image/build.sh"
    exit 1
fi

# Check live-build is installed
if ! command -v lb &>/dev/null; then
    error "live-build not installed. Run: sudo apt-get install -y live-build"
    exit 1
fi

cd "$BUILD_DIR"

info "Configuring live-build..."
lb config \
    --distribution noble \
    --architectures amd64 \
    --binary-images iso-hybrid \
    --bootappend-live "boot=live components persistence username=armos" \
    --debian-installer false \
    --apt-recommends false \
    --memtest none \
    --bootloaders "syslinux,grub-efi" \
    2>&1

info "Building ISO (this takes 10-30 minutes)..."
lb build 2>&1

ISO=$(find . -name "*.hybrid.iso" -type f | head -1)
if [[ -z "$ISO" ]]; then
    error "ISO build failed — no output file found"
    exit 1
fi

SIZE=$(du -h "$ISO" | cut -f1)
SHA=$(sha256sum "$ISO" | cut -d' ' -f1)

success "ISO built successfully!"
echo "  File: $ISO"
echo "  Size: $SIZE"
echo "  SHA256: $SHA"

# Write checksum
echo "$SHA  $(basename $ISO)" > "${ISO%.iso}.sha256"
success "Checksum written"
