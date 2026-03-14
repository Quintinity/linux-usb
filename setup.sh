#!/usr/bin/env bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}=== Linux USB Bootstrap ===${NC}"
echo -e "${CYAN}Getting Claude Code running on this machine${NC}"
echo ""

# Step 1: Install basic dependencies
echo -e "${YELLOW}[1/4] Installing git and curl...${NC}"
sudo apt update && sudo apt install -y git curl

# Step 2: Grant passwordless sudo so Claude Code can run sudo commands autonomously
echo -e "${YELLOW}[2/4] Configuring passwordless sudo for $USER...${NC}"
SUDOERS_FILE="/etc/sudoers.d/${USER}-nopasswd"
if [ ! -f "$SUDOERS_FILE" ]; then
    echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee "$SUDOERS_FILE" > /dev/null
    echo -e "${GREEN}Passwordless sudo configured.${NC}"
else
    echo -e "${GREEN}Passwordless sudo already configured, skipping.${NC}"
fi

# Step 3: Install Claude Code
echo -e "${YELLOW}[3/4] Installing Claude Code...${NC}"
if command -v claude &>/dev/null; then
    echo -e "${GREEN}Claude Code already installed, skipping.${NC}"
else
    curl -fsSL https://claude.ai/install.sh | bash
    export PATH="$HOME/.claude/bin:$PATH"
fi

# Step 4: Copy Claude context files
echo -e "${YELLOW}[4/4] Setting up Claude context...${NC}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Build the project memory path: ~/.claude/projects/<repo-path-with-dashes>/memory/
REPO_PATH_DASHED="$(echo "$REPO_DIR" | sed 's|/|-|g')"
MEMORY_DIR="$HOME/.claude/projects/${REPO_PATH_DASHED}/memory"

mkdir -p "$MEMORY_DIR"

if [ -d "$REPO_DIR/claude-context/memory" ]; then
    cp -v "$REPO_DIR/claude-context/memory/"* "$MEMORY_DIR/"
    echo -e "${GREEN}Copied memory files to $MEMORY_DIR${NC}"
else
    echo -e "${YELLOW}No claude-context/memory/ found, skipping memory copy.${NC}"
fi

if [ -f "$REPO_DIR/claude-context/CLAUDE.md" ]; then
    cp -v "$REPO_DIR/claude-context/CLAUDE.md" "$REPO_DIR/CLAUDE.md"
    echo -e "${GREEN}Copied CLAUDE.md to repo root.${NC}"
else
    echo -e "${YELLOW}No claude-context/CLAUDE.md found, skipping.${NC}"
fi

# Done
echo ""
echo -e "${GREEN}=== Bootstrap complete! ===${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Run: ${GREEN}claude${NC}"
echo -e "  2. Authenticate in browser when prompted"
echo -e "  3. Say: ${GREEN}continue setup${NC}"
echo ""
echo -e "${CYAN}Claude will then handle:${NC}"
echo "  - Installing linux-surface kernel for Surface Pro 7 hardware support"
echo "  - Installing system packages (Python 3.12, FFmpeg, build tools)"
echo "  - Setting up LeRobot v0.5.0 and its dependencies"
echo "  - Configuring serial port access for the SO-101 robot arm"
