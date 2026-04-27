#!/usr/bin/env bash
# install-claude-persona-watch.sh
#
# Installs user-scope systemd units that auto-refresh the device's Claude
# persona on relevant state changes:
#
#   claude-persona.service   — runs claude-persona-refresh.sh (oneshot)
#   claude-persona.path      — fires on ~/.citizenry/node.key creation/change
#   claude-persona.timer     — fires hourly as a catch-all (covers service
#                              enable/disable, hostname changes, etc., that
#                              the path unit can't observe directly)
#
# Idempotent. Re-running just rewrites the unit files and re-enables.
#
# Requires: systemd, sudo (for loginctl enable-linger).

set -euo pipefail

USER_NAME="$(whoami)"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"

# ──────────────────────────────────────────────────────────────────────────
# claude-persona.service — runs the refresh script with whatever path it
# finds on this device. The refresh script itself lives in different
# spots depending on how the device was provisioned:
#   Surface:  ~/linux-usb/scripts/claude-persona-refresh.sh
#   Pi:       ~/citizenry/scripts/... (after deploy.sh) or ~/claude-persona-refresh.sh (after scp)
#   Jetson:   ~/linux-usb/scripts/... or ~/claude-persona-refresh.sh
# ──────────────────────────────────────────────────────────────────────────
cat > "$UNIT_DIR/claude-persona.service" <<'UNIT'
[Unit]
Description=Refresh per-device Claude persona files

[Service]
Type=oneshot
# Find the refresh script wherever it lives on this device, then run it.
# %h is the user's home directory (resolved by systemd at unit-load time).
ExecStart=/bin/bash -c 'for p in "%h/linux-usb/scripts/claude-persona-refresh.sh" "%h/citizenry/scripts/claude-persona-refresh.sh" "%h/claude-persona-refresh.sh"; do [ -f "$p" ] && exec bash "$p"; done; echo "claude-persona-refresh.sh not found in any expected location" >&2; exit 1'
StandardOutput=journal
StandardError=journal
# Don't loop forever if the script is misbehaving.
TimeoutStartSec=60
UNIT

# ──────────────────────────────────────────────────────────────────────────
# claude-persona.path — fires when ~/.citizenry/node.key appears or changes.
# That's the cleanest trigger for "the citizenry stack has been provisioned"
# and warrants a fresh persona generation.
# ──────────────────────────────────────────────────────────────────────────
cat > "$UNIT_DIR/claude-persona.path" <<'UNIT'
[Unit]
Description=Watch ~/.citizenry/node.key for citizenry provisioning events

[Path]
# Fires on file modification, attribute change, or creation.
PathChanged=%h/.citizenry/node.key
# Also fire if the file already exists at unit start (catches initial activation).
PathExists=%h/.citizenry/node.key
# Trigger the refresh service.
Unit=claude-persona.service

[Install]
WantedBy=default.target
UNIT

# ──────────────────────────────────────────────────────────────────────────
# claude-persona.timer — hourly catch-all for changes that the path unit
# can't see (citizenry-*.service enable/disable, hostname changes, hardware
# attached/removed). Cheap; the script itself is fast (<1s).
# ──────────────────────────────────────────────────────────────────────────
cat > "$UNIT_DIR/claude-persona.timer" <<'UNIT'
[Unit]
Description=Periodic Claude persona refresh (catch-all for state we can't watch directly)

[Timer]
# 5 minutes after boot, then every 1 hour.
OnBootSec=5min
OnUnitActiveSec=1h
Unit=claude-persona.service

[Install]
WantedBy=timers.target
UNIT

# ──────────────────────────────────────────────────────────────────────────
# Enable lingering so user units run without an active login session.
# Without this, the path watcher dies when Bradley logs out.
# ──────────────────────────────────────────────────────────────────────────
if ! loginctl show-user "$USER_NAME" 2>/dev/null | grep -q '^Linger=yes'; then
    if sudo -n true 2>/dev/null; then
        sudo loginctl enable-linger "$USER_NAME"
        echo "[persona-watch] enabled linger for $USER_NAME"
    else
        echo "[persona-watch] WARN: could not enable lingering (no passwordless sudo)."
        echo "[persona-watch]       Run: sudo loginctl enable-linger $USER_NAME"
    fi
else
    echo "[persona-watch] linger already enabled for $USER_NAME"
fi

# ──────────────────────────────────────────────────────────────────────────
# Reload + enable + start
# ──────────────────────────────────────────────────────────────────────────
systemctl --user daemon-reload
systemctl --user enable --now claude-persona.path
systemctl --user enable --now claude-persona.timer

# Fire the refresh once now so the device has a current persona without
# waiting for the path event or the 5-minute boot timer to elapse.
systemctl --user start claude-persona.service || true

echo ""
echo "=== claude-persona watcher installed ==="
echo "  units: $UNIT_DIR/claude-persona.{service,path,timer}"
echo ""
echo "  status:    systemctl --user status claude-persona.path claude-persona.timer"
echo "  fire now:  systemctl --user start claude-persona.service"
echo "  logs:      journalctl --user -u claude-persona.service -n 40 --no-pager"
echo "  remove:    systemctl --user disable --now claude-persona.{path,timer} && \\"
echo "             rm $UNIT_DIR/claude-persona.{service,path,timer}"
