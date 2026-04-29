# citizenry

Distributed robotics OS where every piece of hardware is an autonomous
Ed25519-signed citizen sharing a constitution and a marketplace.

The repo started life as a bootable Linux USB for a Surface Pro 7
running LeRobot. It has since grown into a small mesh of independent
citizens — a governor, a manipulator/perception node, and a policy node —
that auction tasks to each other over Ed25519-signed multicast and
record episodes with cryptographic provenance.

## The mesh

```
            multicast 239.67.84.90:7770   (Ed25519-signed envelopes)
        ┌─────────────────────────────────────────────────┐
        │                                                 │
   ┌────┴─────┐          ┌──────────────┐         ┌───────┴──────┐
   │ Surface  │◄────────►│     Pi 5     │◄───────►│   Jetson     │
   │ governor │          │ pi-inference │         │ jetson-policy│
   │ 26c8bdf6 │          │   974b9268   │         │   a1778dd7   │
   └──────────┘          └──────────────┘         └──────────────┘
   constitution           SO-101 arms              SmolVLA on CUDA
   + marketplace          Hailo-8L NPU             bids on manipulation
   + ledgers              cameras + teleop         imitation policy
```

Each citizen carries its own Ed25519 keypair. The governor signs the
Constitution and Laws; every other citizen verifies before applying.
Every heartbeat, bid, attribution, and episode record on the wire is
signed by the citizen that emitted it.

## What it does today

- **Marketplace task auctions** — the governor proposes a task, citizens
  bid, the marketplace picks the best bidder by skill + health +
  co-location bonus.
- **SmolVLA-driven manipulation** — the Jetson hosts a SmolVLA base
  model, bids on `pick_and_place` tasks, and drives a follower arm via
  teleop frames.
- **Episode recording with cryptographic provenance** — every recorded
  episode carries `policy_pubkey`, `governor_pubkey`, and
  `constitution_hash` in its sidecar.
- **v3 dataset format with HF auto-upload** — datasets push to Hugging
  Face Hub, then soft-delete locally after a confirmed upload.
- **Constitution + Laws governance** — the governor signs Articles and
  Laws; all citizens verify before applying. 7 message types, 3 ledger
  types (heartbeat, attribution, episode).

## Quickstart

Clone the repo and bootstrap the Surface as the governor host:

```bash
git clone https://github.com/Quintinity/linux-usb.git ~/linux-usb && cd ~/linux-usb
bash setup.sh     # Surface bootstrap — installs Claude Code + passwordless sudo
# Say "continue setup" to Claude Code when it launches.
```

`setup.sh` is the entry point on a fresh host. If you are starting from
a brand-new Surface Pro 7 with no OS installed, see
[docs/setup-surface-usb.md](docs/setup-surface-usb.md) for the bootable
USB workflow that gets you to the point where `setup.sh` can run.

Once the citizenry is up on the Surface, run the demo:

```bash
source ~/lerobot-env/bin/activate
python -m citizenry.governor_cli demo --task-type basic_gesture/wave
```

This brings up the governor, discovers any citizens currently announcing
on the mesh, runs one marketplace round, and prints the winning bid
along with the resulting attribution record.

## Architecture

The system is a small handful of long-running processes — one per
citizen — that talk only over signed multicast. There is no central
broker; the governor is just another citizen with elevated authority to
sign Articles and Laws.

The deepest design write-up is
[docs/specs/2026-04-27-smolvla-citizen-design.md](docs/specs/2026-04-27-smolvla-citizen-design.md),
which covers SmolVLA-as-citizen end-to-end: the policy citizen
lifecycle, teleop frame routing, attribution sidecar, and how the
Constitution gates what skills a citizen is allowed to bid on.

For the narrative of what the citizenry is and where it came from, read
[citizenry/SOUL.md](citizenry/SOUL.md). For the philosophy of how new
citizens and capabilities are added without breaking older nodes, read
[citizenry/GROWTH.md](citizenry/GROWTH.md).

## Adding a device

Onboarding a new citizen — generating its keypair, registering its
pubkey with the governor, and provisioning its skills — will be driven
by `bash scripts/add-device.sh` once that lands. **Coming soon.**

Until then, see the per-device persona docs in `~/.claude/projects/` on
each host and the matching `~/CLAUDE.md` for the device's role
definition. The Surface is the governor; the Pi runs the manipulator
and perception citizens; the Jetson hosts the SmolVLA policy citizen.

## For Quintinity context

The citizenry is the technical foundation Quintinity Ltd is building
toward auditable AI for manufacturing — every action a robot takes is
signed, attributable, and replayable from cryptographic provenance.
Strategy and partner-pricing details live in an internal Quintinity
strategy doc (Quintinity team only).
