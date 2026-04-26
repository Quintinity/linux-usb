#!/usr/bin/env bash
set -euo pipefail

# Deploy citizenry package from Surface Pro 7 to Raspberry Pi 5
# Run from the linux-usb repo root:
#   ./citizenry/deploy.sh              # deploy only
#   ./citizenry/deploy.sh --start      # deploy and start pi citizen
#   ./citizenry/deploy.sh --stop       # stop pi citizen
#   ./citizenry/deploy.sh 192.168.1.85 # specify IP

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()    { echo -e "${YELLOW}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PI_HOST="192.168.1.86"
SSH_USER="bradley"
REMOTE_DIR="~/citizenry"
REMOTE_VENV="~/lerobot-env"
DO_START=false
DO_STOP=false

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] [PI_IP]

Deploy the citizenry package to the Raspberry Pi 5.

Arguments:
  PI_IP           IP address of the Pi (default: 192.168.1.85)

Options:
  --start         Deploy and start the pi citizen after deployment
  --stop          Stop any running citizenry process on the Pi (no deploy)
  -h, --help      Show this help message

Examples:
  $(basename "$0")                  # deploy only
  $(basename "$0") --start          # deploy and start
  $(basename "$0") --stop           # stop running citizen
  $(basename "$0") 192.168.1.90     # deploy to a different IP
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)  usage ;;
        --start)    DO_START=true; shift ;;
        --stop)     DO_STOP=true; shift ;;
        -*)         error "Unknown option: $1"; usage ;;
        *)          PI_HOST="$1"; shift ;;
    esac
done

SSH_TARGET="${SSH_USER}@${PI_HOST}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
remote() {
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "$SSH_TARGET" "$@"
}

check_connectivity() {
    info "Checking connectivity to ${PI_HOST}..."
    if ! remote "echo ok" &>/dev/null; then
        error "Cannot reach ${SSH_TARGET}. Is the Pi online and SSH enabled?"
        exit 1
    fi
    success "Connected to ${SSH_TARGET}"
}

# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------
stop_citizen() {
    info "Stopping any running citizenry processes on ${PI_HOST}..."
    remote "pkill -f 'python.*citizenry' 2>/dev/null || true; pkill -f 'python.*run_pi' 2>/dev/null || true"
    success "Citizenry processes stopped"
}

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
deploy() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local citizenry_dir="$script_dir"

    if [[ ! -f "${citizenry_dir}/__init__.py" ]]; then
        error "Cannot find citizenry package at ${citizenry_dir}. Run from the repo root."
        exit 1
    fi

    info "Deploying citizenry/ to ${SSH_TARGET}:${REMOTE_DIR}..."

    # Create remote directory and sync files (exclude pycache and deploy script itself)
    rsync -avz --delete \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='deploy.sh' \
        "${citizenry_dir}/" \
        "${SSH_TARGET}:citizenry/"

    success "Files synced to ${SSH_TARGET}:${REMOTE_DIR}"

    # Install Python dependencies if missing
    info "Checking Python dependencies on Pi..."
    remote bash <<'DEPS'
        source ~/lerobot-env/bin/activate 2>/dev/null || { echo "VENV_MISSING"; exit 1; }
        MISSING=""
        python -c "import nacl" 2>/dev/null || MISSING="$MISSING pynacl"
        python -c "import scservo_sdk" 2>/dev/null || MISSING="$MISSING feetech-servo-sdk"
        if [ -n "$MISSING" ]; then
            echo "Installing missing packages:$MISSING"
            pip install $MISSING
        else
            echo "All dependencies present"
        fi
DEPS
    success "Dependencies ready"

    # Verify deployment with import check
    info "Verifying deployment..."
    remote bash <<'VERIFY'
        source ~/lerobot-env/bin/activate
        cd ~
        python -c "
import importlib
for mod in ['citizenry', 'citizenry.pi_citizen', 'citizenry.protocol', 'citizenry.transport', 'citizenry.marketplace', 'citizenry.skills']:
    importlib.import_module(mod)
    print(f'  OK: {mod}')
print('All imports succeeded')
"
VERIFY
    success "Deployment verified"
}

# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------
start_citizen() {
    info "Starting pi citizen on ${PI_HOST}..."
    remote bash <<'START'
        source ~/lerobot-env/bin/activate
        cd ~
        nohup python -m citizenry.run_pi > ~/citizenry.log 2>&1 &
        PID=$!
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            echo "Pi citizen started (PID $PID), logging to ~/citizenry.log"
        else
            echo "FAILED to start pi citizen — check ~/citizenry.log"
            exit 1
        fi
START
    success "Pi citizen is running on ${PI_HOST}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
check_connectivity

if $DO_STOP; then
    stop_citizen
    if ! $DO_START; then
        exit 0
    fi
fi

# Unless we're only stopping, deploy
if ! $DO_STOP || $DO_START; then
    deploy
fi

if $DO_START; then
    start_citizen
fi

success "Done!"
