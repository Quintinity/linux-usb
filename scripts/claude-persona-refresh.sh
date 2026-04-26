#!/usr/bin/env bash
# claude-persona-refresh.sh
#
# Regenerates per-device Claude persona files based on live state:
#   1. Hostname + user
#   2. ~/.citizenry/node.key (if provisioned) → node pubkey
#   3. Enabled citizenry-*.service units (systemd)
#   4. Hardware survey via citizenry.survey (when the repo + venv are present)
#
# Outputs (always overwritten — managed files):
#   ~/.claude/projects/-home-${USER}/memory/device_persona.md
#   ~/CLAUDE.md
#
# Plus an idempotent index update to MEMORY.md (adds the pointer if missing,
# leaves other entries alone).
#
# Safe to run anytime. Designed to run from:
#   - the end of pi-setup.sh / jetson-setup.sh
#   - a systemd timer (optional)
#   - the user, on demand (e.g. after physically swapping arms between hosts)
#
# Detects role from /dev/hailo0, nvidia-smi, enabled services, hostname hints.

set -euo pipefail

USER_NAME="$(whoami)"
HOST="$(hostname)"
CLAUDE_HOME="$HOME/.claude"
MEMORY_DIR="$CLAUDE_HOME/projects/-home-${USER_NAME}/memory"
NODE_KEY_PATH="$HOME/.citizenry/node.key"
NOW="$(date -Iseconds)"

CITIZENRY_REPO_GUESSES=("$HOME/linux-usb" "$HOME/citizenry")
VENV_GUESSES=("$HOME/lerobot-env/bin/python" "$HOME/armos-env/bin/python" "$(command -v python3 || true)")

mkdir -p "$MEMORY_DIR"

# ──────────────────────────────────────────────────────────────────────────
# 1. Detect citizenry role
# ──────────────────────────────────────────────────────────────────────────
detect_role() {
    if [ -e /dev/hailo0 ]; then echo "ManipulatorNode (Pi+Hailo)"; return; fi
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L 2>/dev/null | grep -q .; then
        echo "PolicyNode (Jetson)"; return
    fi
    if systemctl list-unit-files 2>/dev/null | awk '$1 == "citizenry-pi.service" {print $2}' | grep -q enabled; then
        echo "ManipulatorNode (Pi)"; return
    fi
    if systemctl list-unit-files 2>/dev/null | awk '$1 == "citizenry-jetson.service" {print $2}' | grep -q enabled; then
        echo "PolicyNode (Jetson)"; return
    fi
    if systemctl list-unit-files 2>/dev/null | awk '$1 == "citizenry-surface.service" {print $2}' | grep -q enabled; then
        echo "GovernorNode"; return
    fi
    case "$HOST" in
        *pi*|*raspberry*) echo "ManipulatorNode (Pi)"; return;;
        *jetson*)         echo "PolicyNode (Jetson)"; return;;
        *surface*)        echo "GovernorNode"; return;;
    esac
    echo "GenericCitizenryNode"
}

# ──────────────────────────────────────────────────────────────────────────
# 2. Read node-level Ed25519 pubkey, if provisioned
# ──────────────────────────────────────────────────────────────────────────
read_node_pubkey() {
    if [ ! -f "$NODE_KEY_PATH" ]; then
        echo "(not provisioned — ~/.citizenry/node.key absent; will be created on first citizen start)"
        return
    fi
    local pyprog='
import os
try:
    import nacl.signing
    sk = nacl.signing.SigningKey(open(os.path.expanduser("~/.citizenry/node.key"), "rb").read())
    print(sk.verify_key.encode().hex())
except Exception as e:
    print(f"(unreadable: {e})")
'
    for venv in "${VENV_GUESSES[@]}"; do
        [ -x "$venv" ] || continue
        local out
        out=$("$venv" -c "$pyprog" 2>/dev/null) || out=""
        if [ -n "$out" ]; then echo "$out"; return; fi
    done
    echo "(no python+nacl available to decode node.key)"
}

# ──────────────────────────────────────────────────────────────────────────
# 3. Enabled citizenry-*.service units
# ──────────────────────────────────────────────────────────────────────────
enabled_services() {
    local out
    out=$(systemctl list-unit-files 2>/dev/null \
        | awk '/^citizenry-.*\.service/ && $2 == "enabled" { print $1 }' \
        | tr '\n' ' ' | sed 's/ $//')
    [ -z "$out" ] && out="(none enabled)"
    echo "$out"
}

# ──────────────────────────────────────────────────────────────────────────
# 4. Hardware survey (best-effort; gracefully skipped on failure)
# ──────────────────────────────────────────────────────────────────────────
run_survey() {
    local pyprog='
import asyncio
try:
    from citizenry.survey import survey_hardware
    hw = asyncio.run(survey_hardware())
    cams = ", ".join(
        f"{c.kind}({c.model or chr(63)}@{c.path or chr(63)})" for c in hw.cameras
    ) or "none"
    accels = ", ".join(
        f"{a.kind}({a.model or chr(63)})" for a in hw.accelerators
    ) or "none"
    buses = ", ".join(
        f"{b.port}({getattr(b, chr(114)+chr(111)+chr(108)+chr(101), None) or chr(63)})" for b in hw.servo_buses
    ) or "none"
    cpu = getattr(hw.compute, "cpu_model", "?")
    ram = getattr(hw.compute, "ram_gb", None)
    print(f"cpu: {cpu}")
    if ram is not None:
        print(f"memory: {ram} GB")
    print(f"cameras: {cams}")
    print(f"accelerators: {accels}")
    print(f"servo_buses: {buses}")
except Exception as e:
    print(f"(survey failed: {e})")
'
    local repo venv
    for repo in "${CITIZENRY_REPO_GUESSES[@]}"; do
        [ -d "$repo/citizenry" ] || continue
        for venv in "${VENV_GUESSES[@]}"; do
            [ -x "$venv" ] || continue
            local out
            out=$(cd "$repo" && PYTHONPATH="$repo" "$venv" -c "$pyprog" 2>/dev/null) || out=""
            if [ -n "$out" ]; then echo "$out"; return; fi
        done
    done
    echo "(survey unavailable — citizenry repo or venv not found on this device)"
}

# Gather
ROLE="$(detect_role)"
NODE_PUBKEY="$(read_node_pubkey)"
SERVICES="$(enabled_services)"
SURVEY="$(run_survey)"

# ──────────────────────────────────────────────────────────────────────────
# 5. Per-role narrative blocks
# ──────────────────────────────────────────────────────────────────────────
role_narrative() {
    case "$ROLE" in
        "ManipulatorNode (Pi+Hailo)")
            cat <<'EOF'
**I am:** A ManipulatorNode in the citizenry — and the Pi-with-Hailo flavour.

I host:
- A `ManipulatorCitizen` driving the follower SO-101 arm (formerly known as `PiCitizen`).
- A `LeaderCitizen` if a leader bus is also attached locally (`run_pi.py --leader-port`).
- `CameraCitizen` instances per attached camera (CSI Camera Module 3 NoIR Wide; USB cams; mDNS-discovered XIAO wifi cams).
- A brain citizen named `pi-inference` that owns the Hailo-8L AI HAT+ accelerator (13 TOPS, INT8). It runs **perception** (YOLO-class detectors, pose estimation, anomaly streams) — NOT VLA policies.

**I am NOT:** a VLA policy host. Independent benchmarks confirm Hailo-8L cannot run SmolVLA / VLA-class models at robot-viable rates (>5 Hz). Policy hosting is the Jetson's job. If a SmolVLA-driven task targets my follower, the action stream crosses the LAN from the Jetson — that's by design (cross-node bidding with co-location bonus).

**I am NOT:** the governor. The Surface ratifies the Constitution and brokers the marketplace.

**Boot autonomy:** `citizenry-pi.service` auto-starts on boot, after WiFi reconnects (NetworkManager autoconnect is configured per `pi-setup.sh`).

**Tools and commands relevant to me:**
- Inspect what citizens are running: `journalctl -u citizenry-pi -f`
- Service control: `sudo systemctl {start|stop|restart|status} citizenry-pi`
- Manual launch: `source ~/armos-env/bin/activate && python -m citizenry.run_pi`
- Hardware probes: `hailortcli scan`, `libcamera-still --list-cameras`, `v4l2-ctl --list-devices`
- Servo diagnostics: scripts in `~/citizenry/` (or wherever `deploy.sh` rsync'd them) — `diagnose_motor.py`, `set_motor_id.py`, `test_motor_wiggle.py`
EOF
            ;;
        "ManipulatorNode (Pi)")
            cat <<'EOF'
**I am:** A ManipulatorNode in the citizenry, Pi flavour (Hailo not detected — perception runs on CPU).

I host:
- A `ManipulatorCitizen` driving the follower SO-101 arm.
- A `LeaderCitizen` if a leader bus is attached locally.
- `CameraCitizen` instances per attached camera.
- A brain citizen for system presence + accelerator advertising.

**I am NOT:** a VLA policy host. Without the Hailo-8L, perception falls back to CPU and is slower; SmolVLA still hosts on the Jetson exclusively.

**Boot autonomy:** `citizenry-pi.service` auto-starts on boot.

**Tools and commands:**
- `journalctl -u citizenry-pi -f`, `sudo systemctl ... citizenry-pi`
- `source ~/armos-env/bin/activate && python -m citizenry.run_pi`
- `libcamera-still --list-cameras`, `v4l2-ctl --list-devices`
EOF
            ;;
        "PolicyNode (Jetson)")
            cat <<'EOF'
**I am:** A PolicyNode in the citizenry — the only host in the fleet with the compute to run a Vision-Language-Action model.

I host:
- A `PolicyCitizen` running SmolVLA (`lerobot/smolvla_base`) on CUDA. Bids on manipulation tasks via the marketplace; +0.15 co-location bonus when the targeted follower lives on this same node.
- Optionally `LeaderCitizen` + `ManipulatorCitizen` if SO-101 arms are physically attached locally (preferred topology — gives the tightest control loop).
- `CameraCitizen` instances per attached USB camera.

**I am NOT:** the governor. The Surface ratifies the Constitution. **I am NOT:** a stand-in for a Jetson Thor — I cannot run GR00T N1.6, π0.5 full, or RDT-2 at scale. SmolVLA is the model that fits 8 GB at FP16.

**Boot autonomy:** `citizenry-jetson.service` auto-starts on boot (after Task 10 of the SmolVLA plan).

**Tools and commands:**
- `journalctl -u citizenry-jetson -f`, `sudo systemctl ... citizenry-jetson`
- `tegrastats` (live SoC stats), `nvidia-smi` (CUDA + memory), `jetson_release`
- `source ~/lerobot-env/bin/activate && python -m citizenry.run_jetson`
- HF token at `~/.citizenry/hf_token` (chmod 600) — used by `HFUploader` to push v3 datasets.
EOF
            ;;
        "GovernorNode")
            cat <<'EOF'
**I am:** The GovernorNode in the citizenry.

I host:
- `GovernorCitizen` — Constitution ratification, marketplace coordination.
- Dashboard / CLI (`governor_cli`).

**I am NOT:** a manipulator host. Arms are physically attached to a ManipulatorNode (Jetson or Pi). **I am NOT:** an episode recorder. The Constitution Law `governor.recorder_enabled` is **false**, enforced at boot — `GovernorCitizen._maybe_start_recorder()` raises if anyone misconfigures it. Episodes record on the follower's node and upload from there.

**Tools and commands:**
- `journalctl -u citizenry-surface -f` (when the service is provisioned) or run foreground:
- `source ~/lerobot-env/bin/activate && python -m citizenry.run_surface`
- `governor_cli`: interactive REPL for inspecting marketplace, neighbours, tasks.
- `python -m citizenry.dataset_v3_migrate ...` for the one-shot legacy migration (Task 7 of the SmolVLA plan).
EOF
            ;;
        *)
            cat <<'EOF'
**I am:** A node in the citizenry that has not yet been bound to a specific role. The persona refresh was unable to determine my role from hardware, services, or hostname. Re-run `claude-persona-refresh.sh` after `setup.sh` / `pi-setup.sh` / `jetson-setup.sh` completes; if the role is still unknown, set CLAUDE_DEVICE_ROLE in the environment to override (e.g. `CLAUDE_DEVICE_ROLE="ManipulatorNode (Pi)" claude-persona-refresh.sh`).
EOF
            ;;
    esac
}

# ──────────────────────────────────────────────────────────────────────────
# 6. Write device_persona.md
# ──────────────────────────────────────────────────────────────────────────
cat > "$MEMORY_DIR/device_persona.md" <<EOF
---
name: Device persona
description: Who this device is in the citizenry mesh — auto-generated from hardware survey + node identity + enabled services. Refreshed by scripts/claude-persona-refresh.sh.
type: user
---

> **Managed file** — overwritten by \`scripts/claude-persona-refresh.sh\`.
> Last refreshed: $NOW

## Identity

- **Hostname:** \`$HOST\`
- **User:** \`$USER_NAME\`
- **Citizenry role:** **$ROLE**
- **Node pubkey (hex):** \`$NODE_PUBKEY\`
- **Enabled citizenry services:** $SERVICES

## Hardware (live survey)

\`\`\`
$SURVEY
\`\`\`

## Persona

$(role_narrative)

## Citizenry context

The citizenry is a distributed robotics OS — every hardware piece (arms, cameras, accelerators, control stations) is an autonomous "citizen" with its own Ed25519 identity and a per-node identity at \`~/.citizenry/node.key\`. Citizens speak a 7-message protocol (HEARTBEAT, DISCOVER, ADVERTISE, PROPOSE, ACCEPT_REJECT, REPORT, GOVERN) on UDP multicast \`239.67.84.90:7770\`. Marketplace bids carry node_pubkey for co-location detection (+0.15 bonus when bidder and target follower share a node).

Active design docs:
- Spec: \`docs/specs/2026-04-27-smolvla-citizen-design.md\`
- Plan: \`docs/plans/2026-04-27-smolvla-citizen.md\`
- Existing component: \`citizenry/PLAN-xiao-true-citizen-v2.md\` (XIAO ESP32S3 → first-class citizen, in flight)

## Refreshing this file

\`\`\`bash
~/linux-usb/scripts/claude-persona-refresh.sh    # on Surface
~/citizenry/scripts/claude-persona-refresh.sh    # on Pi (after deploy.sh)
~/linux-usb/scripts/claude-persona-refresh.sh    # on Jetson
\`\`\`
EOF

# ──────────────────────────────────────────────────────────────────────────
# 7. Write ~/CLAUDE.md (short, identity-first)
# ──────────────────────────────────────────────────────────────────────────
cat > "$HOME/CLAUDE.md" <<EOF
# $HOST — citizenry $ROLE

> **Managed file** — overwritten by \`scripts/claude-persona-refresh.sh\`.
> Last refreshed: $NOW

You are running on **\`$HOST\`** (user \`$USER_NAME\`). In the citizenry mesh, this device's role is **$ROLE**.

For the full persona — what citizens this host runs, what it can and can't do, the commands relevant to it, and the broader fleet context — read \`~/.claude/projects/-home-${USER_NAME}/memory/device_persona.md\` (also indexed in \`MEMORY.md\`).

When the user talks to you on this machine, respond with awareness of:
1. Where you are (this host's specific hostname and role).
2. What runs here (the citizens listed in device_persona.md — refer to them by name).
3. What does NOT run here (e.g. on the Surface: no recorder; on the Pi: no VLA policy; on the Jetson: no governor).
4. The protocol-level facts: Ed25519-signed multicast on 239.67.84.90:7770, 7-message types, Constitution + Laws governance, node-level identity at \`~/.citizenry/node.key\`.

If hardware changes (arms moved, accelerator swapped, services enabled/disabled), re-run \`scripts/claude-persona-refresh.sh\` and re-read this file.

To refresh: \`bash ~/linux-usb/scripts/claude-persona-refresh.sh\` (or wherever the repo is rsync'd on this device).
EOF

# ──────────────────────────────────────────────────────────────────────────
# 8. Idempotently add device_persona pointer to MEMORY.md
# ──────────────────────────────────────────────────────────────────────────
MEMORY_INDEX="$MEMORY_DIR/MEMORY.md"
if [ -f "$MEMORY_INDEX" ]; then
    if ! grep -q "device_persona.md" "$MEMORY_INDEX"; then
        printf '%s\n' "- [Device persona — auto-refreshed](device_persona.md) — who this device is in the citizenry; live hardware + node key + enabled services" >> "$MEMORY_INDEX"
        echo "[memory] added device_persona.md pointer to MEMORY.md"
    else
        echo "[memory] device_persona.md pointer already present in MEMORY.md"
    fi
else
    cat > "$MEMORY_INDEX" <<EOF
- [Device persona — auto-refreshed](device_persona.md) — who this device is in the citizenry; live hardware + node key + enabled services
EOF
    echo "[memory] created new MEMORY.md with device_persona.md pointer"
fi

# ──────────────────────────────────────────────────────────────────────────
# 9. Summary
# ──────────────────────────────────────────────────────────────────────────
echo ""
echo "=== claude persona refresh complete ==="
echo "  host:     $HOST"
echo "  role:     $ROLE"
echo "  pubkey:   ${NODE_PUBKEY:0:16}..."
echo "  services: $SERVICES"
echo "  wrote:    $MEMORY_DIR/device_persona.md"
echo "  wrote:    $HOME/CLAUDE.md"
echo "  index:    $MEMORY_INDEX"
echo ""
echo "Next: open a Claude session on this host to see the new persona take effect."
