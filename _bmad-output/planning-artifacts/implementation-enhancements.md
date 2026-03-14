# Implementation Enhancements: Business Strategy to Code

**Author:** Amelia (Developer)
**Date:** 2026-03-15
**Status:** Proposal
**Context:** New implementation work driven by the business plan, market research, product validation, and cross-review findings. These items are NOT covered by the current epics (0-10) and must be added or spiked before the relevant phases begin.

---

## 1. New Stories Needed for Business Features

The business plan describes revenue streams and product capabilities (telemetry, cloud hooks, profile sharing, demo mode) that have zero coverage in the current epics. These need stories.

### Story B1: Anonymous Telemetry Collection (opt-in)

**Business driver:** Data flywheel (vision doc moat #5), usage analytics dashboard (business plan 3.4), leading indicators tracking (business plan Appendix A).

**As a** product owner,
**I want** armOS to collect anonymous usage telemetry (hardware detected, boot count, teleop session duration, diagnostic pass/fail rates) with explicit opt-in,
**So that** we can track adoption metrics, identify the most common hardware configurations, and prioritize support.

**Acceptance criteria:**
- First boot displays a clear opt-in prompt: "Share anonymous usage data to improve armOS? [y/N]"
- Choice is persisted in `~/.config/armos/settings.yaml` as `telemetry_enabled: true|false`
- If enabled, events are queued to a local SQLite file (`~/.local/share/armos/telemetry.db`)
- Events are batched and uploaded via HTTPS POST when internet is available (never blocks offline workflows)
- The `armos telemetry show` command displays exactly what data would be sent
- The `armos telemetry off` command disables collection and deletes the local queue
- No PII is ever collected. Hardware serial numbers are hashed with a per-install salt.
- NFR22 ("No user data transmitted without explicit action") is satisfied by the opt-in gate

**Size:** L
**Phase:** Growth (v0.5), but the local SQLite collection can land in MVP if the upload is deferred
**Sprint:** After Sprint 6

---

### Story B2: Cloud Training Pipeline -- Upload Hook

**Business driver:** Cloud training service (business plan 3.3), $5-20/run pricing, closes the "no GPU on armOS" gap.

**As a** user who has collected demonstration data,
**I want** to upload my dataset to armOS Cloud for GPU training and download the trained policy,
**So that** I can go from data collection to a working policy without setting up a GPU environment.

**Acceptance criteria:**
- `armos cloud login` authenticates via browser OAuth flow (HuggingFace Hub token or armOS account)
- `armos cloud upload --dataset ./my-dataset` uploads a LeRobot-format dataset to the cloud service
- `armos cloud status` shows training job progress
- `armos cloud download --job <id>` retrieves the trained policy checkpoint
- Upload uses resumable multipart upload (datasets can be multi-GB)
- All communication is HTTPS. No data leaves the machine without an explicit `upload` command (NFR22)
- Works behind corporate proxies (respects `HTTPS_PROXY` env var)

**Size:** XL
**Phase:** Growth (v0.5)
**Dependencies:** Story 9.3 (data collection must work first), cloud backend (separate project)

---

### Story B3: Profile Sharing via HuggingFace Hub

**Business driver:** Community robot profile repository (vision Horizon 2), marketplace (business plan 3.5), network effect moat.

**As a** community member who has tuned a robot profile,
**I want** to publish my profile to a shared repository and browse/download profiles others have published,
**So that** new users can get pre-tuned configs for their specific hardware setup.

**Acceptance criteria:**
- `armos profile publish --name "so101-wowrobo-resin"` pushes a profile YAML + calibration to HuggingFace Hub under the `armos-community/profiles` organization
- `armos profile search "so101"` lists matching profiles from the Hub with star counts and last-updated dates
- `armos profile install <hub-id>` downloads a profile into `~/.config/armos/profiles/`
- Profiles on the Hub include a `tested_hardware` field listing which machines they have been validated on
- Profiles are validated against the JSON schema before upload (Story 3.2's schema)
- Works offline: `armos profile list` always shows locally installed profiles regardless of network

**Size:** L
**Phase:** Growth (v0.5)
**Dependencies:** Story 3.1 (profile loader), HuggingFace Hub API spike (see Spike S1)

---

### Story B4: Demo Mode (Kiosk)

**Business driver:** Maker Faire demos (business plan 6.4), YouTube demo video (business plan 6.1), university open houses. The business plan's entire marketing strategy depends on a flawless 90-second demo.

**As a** person demonstrating armOS at a booth or in a video,
**I want** a single-command demo mode that boots into a locked-down, self-recovering teleop session,
**So that** the demo cannot be interrupted by accidental keypresses, crashes, or configuration issues.

**Acceptance criteria:**
- `armos demo` launches a full-screen TUI with: large "armOS" header, live camera feed, leader-follower teleop, and a telemetry panel
- If the servo bus disconnects, demo mode auto-reconnects (up to 30 seconds) and resumes
- If any unhandled exception occurs, demo mode restarts itself within 3 seconds
- Demo mode disables all keyboard shortcuts except Escape (which requires a 3-second hold to exit)
- A GRUB boot option "armOS Demo Mode" boots directly into demo mode without login
- The demo session auto-starts teleop using the default profile with no user interaction required

**Size:** M
**Phase:** MVP (v0.1) -- this is marketing-critical for launch
**Dependencies:** Stories 6.2 (teleop), 7.1 (TUI framework)

---

### Story B5: Fleet Deployment Image Cloning

**Business driver:** Education licensing (business plan 3.4), classroom mode, fleet deployment.

**As an** educator setting up 30 armOS stations,
**I want** to configure one USB stick and clone its state (calibrations, profiles, settings) to all others,
**So that** I don't have to configure each station individually.

**Acceptance criteria:**
- `armos fleet export` creates a `.armos-config.tar.gz` containing all user-writable state
- `armos fleet import <file>` applies the config bundle to the current machine
- The flash.ps1 script accepts an optional `--config <file>` flag to embed the config into the image during flashing
- Calibration data is exported but marked as "needs re-validation" on import (different hardware may have different servo characteristics)

**Size:** M
**Phase:** Growth (v0.5)
**Dependencies:** Story 8.2 (persistent storage), Story 8.3 (flash script)

---

## 2. Technical Spikes (Time-boxed Research)

These should happen early because they de-risk downstream work. Each spike produces a written finding document, not code.

### Spike S1: HuggingFace Hub API for Profile Sharing (2 days)

**Question:** Can we use the `huggingface_hub` Python library to store and retrieve YAML robot profiles as Hub datasets or model repos? What are the rate limits, authentication requirements, and storage costs?

**Deliverables:**
- Working prototype: push a YAML file to Hub, retrieve it, list available files
- Document: authentication flow, rate limits, storage model (dataset vs model repo vs Space), cost at 1,000 profiles
- Decision: use Hub or build a custom registry

**When:** Sprint 3 (before profile system is finalized)

---

### Spike S2: Foxglove MCAP Format for Telemetry Logging (1 day)

**Question:** The business plan identifies Foxglove as "integrate rather than compete." Should armOS write telemetry logs in MCAP format so users can open them in Foxglove Studio?

**Deliverables:**
- Prototype: write servo telemetry (position, voltage, temperature, load) into an MCAP file
- Document: MCAP schema for servo data, file sizes for a 10-minute session, Foxglove Studio compatibility
- Decision: adopt MCAP as the telemetry log format, or use a simpler format (CSV, Parquet) and provide a converter

**When:** Sprint 4 (when telemetry stories start)

---

### Spike S3: Cloud Training Pipeline Prototype (3 days)

**Question:** What is the minimum infrastructure to accept a LeRobot dataset upload, run a training job on a rented GPU, and return a policy checkpoint?

**Deliverables:**
- Prototype: upload a dataset to an S3 bucket, trigger a training job on Modal/Lambda/vast.ai, retrieve the checkpoint
- Document: cost per training run (compute + storage + egress), estimated margin at $10/run pricing, latency from upload to trained policy
- Decision: build or buy (Modal functions vs custom infra vs partner with existing platform)

**When:** Sprint 5-6 (after data collection works)

---

### Spike S4: ISO Distribution Strategy (1 day)

**Question:** The business plan says "pre-flashed USB sticks sold directly." But users also need to download the ISO. At 8-16GB, how do we distribute it cheaply?

**Deliverables:**
- Cost analysis: GitHub Releases (free but 2GB limit), HuggingFace Hub (free, unlimited), Cloudflare R2 (cheap egress), BitTorrent, direct download
- Decision: primary and fallback distribution channels
- Prototype: upload a test ISO to the chosen platform, measure download speed from 3 regions

**When:** Sprint 6 (before ISO build is finalized)

---

### Spike S5: OTA Update Mechanism for Live USB (2 days)

**Question:** How does a user update their armOS USB stick without re-flashing? Can we do package-level updates on the persistent partition?

**Deliverables:**
- Prototype: install the `armos` Python package to the persistent partition, verify it survives reboot
- Document: what can be updated in-place (Python packages, profiles, configs) vs what requires re-flash (kernel, squashfs, live-build image)
- Decision: support OTA for the armos package and profiles, require re-flash for base OS changes

**When:** Sprint 6 (alongside ISO build stories)

---

## 3. SDK/API Design: armOS Plugin SDK

If hardware partners (Feetech, ROBOTIS, Waveshare) want to ship armOS support with their products, they need a clear integration path. This section defines what the plugin SDK looks like.

### Plugin Types

| Plugin Type | What It Does | Example |
|-------------|-------------|---------|
| **Servo Protocol** | Implements `ServoProtocol` ABC for a new servo family | `armos-dynamixel` |
| **Robot Profile** | YAML file describing a complete robot configuration | `so101-waveshare.yaml` |
| **Sensor Driver** | Provides a data stream from a non-servo sensor | `armos-realsense` (depth camera) |
| **Application** | Adds a new CLI command or TUI panel | `armos-ros2-bridge` |

### Servo Protocol Plugin Structure

The architect review (Issue 2.1) recommends Python entry points. Here is the concrete structure:

```
armos-dynamixel/
  pyproject.toml          # entry-points: armos.servo_protocols -> dynamixel
  src/
    armos_dynamixel/
      __init__.py
      plugin.py           # class DynamixelPlugin(ServoProtocol)
      registers.py        # protocol-specific register maps
  tests/
    test_conformance.py   # inherits ServoProtocolConformanceTests
    test_dynamixel.py     # protocol-specific tests
  README.md
```

**pyproject.toml entry point:**

```toml
[project.entry-points."armos.servo_protocols"]
dynamixel = "armos_dynamixel.plugin:DynamixelPlugin"
```

**Discovery in armos core:**

```python
from importlib.metadata import entry_points

def get_protocol(name: str) -> type[ServoProtocol]:
    eps = entry_points(group="armos.servo_protocols")
    for ep in eps:
        if ep.name == name:
            return ep.load()
    raise PluginNotFoundError(name)
```

### Plugin Developer Workflow

1. `pip install armos` (installs the core SDK including the ABC and test base classes)
2. Create a new package using `armos plugin init dynamixel` (scaffolding command)
3. Implement `ServoProtocol` methods in `plugin.py`
4. Run `pytest` -- the conformance test suite validates the ABC contract automatically
5. Test against real hardware using `armos diagnose --protocol dynamixel`
6. Publish to PyPI: `pip install armos-dynamixel` makes it available system-wide
7. On armOS, the plugin is auto-discovered via entry points when installed to the persistent partition

### New Stories for SDK

**Story SDK1: Plugin Scaffolding Command** (S)

`armos plugin init <name>` generates a new directory with pyproject.toml, src layout, conformance test imports, and a README template.

**Story SDK2: ServoProtocolConformanceTests Base Class** (M)

A pytest base class that any plugin can subclass. Tests: connect/disconnect lifecycle, ping, sync_read/write round-trip, telemetry range validation, retry behavior, flush_port. The QA review (C5) already calls for this.

**Story SDK3: Plugin Documentation and Developer Guide** (M)

A docs page: "How to add support for a new servo protocol." Includes the entry point mechanism, the conformance tests, and a worked example (Feetech as reference).

---

## 4. Packaging for Distribution

### ISO Distribution Decision Matrix

| Channel | Max Size | Cost (1,000 downloads/mo) | Speed | Reliability | Recommended? |
|---------|----------|--------------------------|-------|-------------|-------------|
| GitHub Releases | 2GB per asset | Free | Fast (CDN) | High | No -- ISO exceeds limit |
| HuggingFace Hub | Unlimited | Free | Fast (CDN) | High | **Yes -- primary** |
| Cloudflare R2 | Unlimited | ~$5/mo (egress free) | Fast | High | Yes -- backup |
| BitTorrent | Unlimited | ~$0 | Variable | Depends on seeds | Yes -- community mirror |
| Direct website (S3) | Unlimited | ~$50/mo at scale | Fast | High | No -- expensive |

### Recommended Distribution Strategy

1. **Primary:** HuggingFace Hub. Create an `armos/armos-usb` repository. Each release is a tagged commit with the ISO as an LFS file. Users download via `huggingface-cli download armos/armos-usb armos-v0.1.0.iso` or direct browser link. Free, fast, reliable, and aligns with the HuggingFace partnership strategy.

2. **Fallback:** Cloudflare R2 bucket with a custom download page at `download.armos.dev`. Near-zero cost even at scale thanks to free egress.

3. **Community:** Seed a BitTorrent after each release. Include a magnet link on the download page. Power users and institutions with good bandwidth become seeders.

4. **Pre-flashed USB sticks:** Partner with a fulfillment house (or manual fulfillment initially). Flash ISOs onto 32GB USB 3.0 drives. Sell on the website and Amazon for $15-25.

### New Story

**Story D1: ISO Distribution Pipeline** (M)

`make release` builds the ISO, computes SHA256, uploads to HuggingFace Hub as a tagged release, generates the BitTorrent file, and updates the download page. Acceptance criteria: a fresh machine can download and verify the ISO in under 10 minutes on a 50Mbps connection.

---

## 5. Versioning and Update Strategy

### Version Scheme

armOS has two versioned artifacts that must stay coordinated:

| Artifact | Version Source | Example |
|----------|---------------|---------|
| `armos` Python package | `setuptools-scm` from git tags | `0.1.0`, `0.1.1.dev3+gabc1234` |
| armOS ISO image | Embedded in `/etc/armos-release` at build time | `armos-0.1.0-20260915` |

The ISO version includes a date suffix because the same armos package version can be rebuilt with updated system packages.

### Update Channels

| What Changed | Update Method | User Action |
|-------------|--------------|-------------|
| `armos` Python package (bug fix, new feature) | `armos update` (pip install from PyPI or bundled wheel) | Run one command, no reboot |
| Robot profiles | `armos profile install <hub-id>` | Run one command, no reboot |
| System packages (security patches) | `sudo apt upgrade` on persistent partition | Run one command, may need reboot |
| Kernel or base OS (major release) | Re-flash USB with new ISO | Download new ISO, re-flash, re-import config via `armos fleet import` |

### The `armos update` Command

```
armos update [--check]    # Check for available updates
armos update [--apply]    # Download and install the latest armos package
```

This updates only the Python package on the persistent partition. It does NOT update the base squashfs image. For a full OS update, the user re-flashes.

### New Stories

**Story V1: armos update Command** (M)

Checks PyPI (or a bundled index on HuggingFace Hub) for a newer `armos` package version. Downloads and installs it into the persistent partition's virtualenv. Verifies the new version loads correctly before committing.

**Story V2: ISO Version Metadata** (S)

The ISO build (Story 8.1) writes `/etc/armos-release` with the version, build date, git hash, and armos package version. `armos --version` reads and displays this.

---

## 6. Developer Experience: Contributing a Dynamixel Plugin

This is the end-to-end workflow for an external contributor. If this workflow is painful, no one will contribute plugins.

### Prerequisites

```bash
pip install armos             # Installs core package + ServoProtocol ABC
pip install armos[dev]        # Adds pytest, ruff, mypy, conformance tests
```

### Step-by-Step

```bash
# 1. Scaffold the plugin
armos plugin init dynamixel
cd armos-dynamixel

# 2. Implement the protocol
$EDITOR src/armos_dynamixel/plugin.py
# Fill in: connect, disconnect, ping, scan_bus, sync_read_positions,
#          sync_write_positions, get_telemetry, read_register, write_register,
#          enable_torque, disable_torque, flush_port

# 3. Run conformance tests (no hardware needed)
pytest tests/test_conformance.py
# Tests use MockServoProtocol patterns to validate the ABC contract

# 4. Run against real hardware
armos diagnose --protocol dynamixel --port /dev/ttyUSB0
# Runs the standard diagnostic suite through the new plugin

# 5. Create a robot profile
cat > profiles/koch-v1.1.yaml << 'EOF'
name: Koch v1.1
protocol: dynamixel
...
EOF

# 6. Publish
pip install build twine
python -m build
twine upload dist/*
# Now anyone can: pip install armos-dynamixel
```

### What We Need to Build for This

| Item | Current Status | Work Needed |
|------|---------------|-------------|
| `ServoProtocol` ABC | Designed (Story 2.1) | Ship it |
| `ServoProtocolConformanceTests` | Not in epics | Add Story SDK2 |
| `armos plugin init` scaffolding | Not in epics | Add Story SDK1 |
| `armos diagnose --protocol <name>` flag | Not in epics | Add to Story 4.1 acceptance criteria |
| `armos[dev]` extras in pyproject.toml | Not in epics | Add to Story 1.1 |
| Developer guide documentation | Not in epics | Add Story SDK3 |

---

## 7. CI/CD for ISO Builds

### Pipeline Design

The QA review (Section 9) already proposes a 7-stage CI pipeline. Here is the ISO-specific portion with concrete implementation guidance.

### GitHub Actions Workflow: `build-iso.yml`

```yaml
name: Build ISO
on:
  push:
    tags: ['v*']        # Build on version tags
  workflow_dispatch:     # Manual trigger for testing

jobs:
  build:
    runs-on: ubuntu-24.04
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v4

      - name: Build ISO in Docker
        run: |
          docker build -f Dockerfile.build -t armos-builder .
          docker run --privileged -v $PWD/output:/output armos-builder

      - name: Smoke test ISO in QEMU
        run: |
          sudo apt-get install -y qemu-system-x86 ovmf expect
          bash tests/iso/test-iso.sh output/armos-*.iso

      - name: Upload ISO artifact
        uses: actions/upload-artifact@v4
        with:
          name: armos-iso
          path: output/armos-*.iso

      - name: Upload to HuggingFace Hub
        if: startsWith(github.ref, 'refs/tags/v')
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          pip install huggingface_hub
          python scripts/upload-release.py output/armos-*.iso
```

### Dockerfile.build

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y \
    live-build debootstrap squashfs-tools xorriso \
    grub-efi-amd64-bin grub-pc-bin mtools
COPY build/ /build/
WORKDIR /build
ENTRYPOINT ["bash", "build-iso.sh"]
```

### QEMU Smoke Test (`tests/iso/test-iso.sh`)

Per the QA review (M8), the smoke test validates:
1. ISO boots to login prompt under UEFI (OVMF firmware)
2. `armos --version` returns the expected version
3. `armos profile list` includes SO-101
4. No kernel panics or systemd failures in `dmesg`

The test uses `expect` to interact with the QEMU serial console and times out after 120 seconds.

### Testing a Bootable ISO in CI -- What Works and What Doesn't

| Approach | Tests Boot? | Tests Hardware? | Tests USB Persistence? | CI Feasible? |
|----------|------------|----------------|----------------------|-------------|
| QEMU with OVMF | Yes (UEFI) | No | No (no USB passthrough) | **Yes** |
| QEMU with USB passthrough | Yes | Limited | Partial | Only on self-hosted runners |
| VirtualBox in CI | Yes | No | No | Slow, needs nested virtualization |
| Real hardware via self-hosted runner | Yes | **Yes** | **Yes** | **Yes, but expensive** |

**Recommendation:** QEMU smoke test in GitHub Actions (free, every tag push). Self-hosted runner with real SO-101 hardware for nightly or weekly integration tests.

### New Stories

**Story CI1: Dockerfile.build for Reproducible ISO Builds** (M)

Create a Dockerfile that produces identical ISO images regardless of the build machine. Pin all package versions. The architect review (Issue 4.2) specifically calls for this.

**Story CI2: QEMU ISO Smoke Test** (M)

Implement `tests/iso/test-iso.sh` using QEMU + OVMF + expect. Validate boot, version, profile availability, and no critical errors.

**Story CI3: GitHub Actions ISO Build Workflow** (S)

Wire up the Docker build + QEMU test + artifact upload into a GitHub Actions workflow triggered on version tags.

**Story CI4: Self-Hosted Runner with Hardware** (M, deferred)

Set up a Raspberry Pi or spare laptop as a GitHub Actions self-hosted runner with an SO-101 connected. Runs the full E2E test suite against real hardware on a nightly schedule.

---

## 8. Summary: All New Stories and Spikes

### Business Feature Stories

| ID | Title | Size | Phase | Dependencies |
|----|-------|------|-------|-------------|
| B1 | Anonymous Telemetry Collection | L | Growth | Settings system |
| B2 | Cloud Training Upload Hook | XL | Growth | 9.3 (data collection), cloud backend |
| B3 | Profile Sharing via HuggingFace Hub | L | Growth | 3.1, Spike S1 |
| B4 | Demo Mode (Kiosk) | M | MVP | 6.2, 7.1 |
| B5 | Fleet Deployment Image Cloning | M | Growth | 8.2, 8.3 |

### Technical Spikes

| ID | Title | Duration | When |
|----|-------|----------|------|
| S1 | HuggingFace Hub API for Profiles | 2 days | Sprint 3 |
| S2 | Foxglove MCAP Telemetry Format | 1 day | Sprint 4 |
| S3 | Cloud Training Pipeline Prototype | 3 days | Sprint 5-6 |
| S4 | ISO Distribution Strategy | 1 day | Sprint 6 |
| S5 | OTA Update Mechanism for Live USB | 2 days | Sprint 6 |

### SDK Stories

| ID | Title | Size | Phase |
|----|-------|------|-------|
| SDK1 | Plugin Scaffolding Command | S | Growth |
| SDK2 | ServoProtocolConformanceTests | M | MVP (Sprint 2) |
| SDK3 | Plugin Developer Guide | M | Growth |

### Distribution and Versioning Stories

| ID | Title | Size | Phase |
|----|-------|------|-------|
| D1 | ISO Distribution Pipeline | M | MVP (Sprint 6) |
| V1 | armos update Command | M | Growth |
| V2 | ISO Version Metadata | S | MVP (Sprint 6) |

### CI/CD Stories

| ID | Title | Size | Phase |
|----|-------|------|-------|
| CI1 | Dockerfile.build for ISO | M | MVP (Sprint 6) |
| CI2 | QEMU ISO Smoke Test | M | MVP (Sprint 6) |
| CI3 | GitHub Actions ISO Build Workflow | S | MVP (Sprint 6) |
| CI4 | Self-Hosted Runner with Hardware | M | Growth |

### Total New Work

- **5 business feature stories** (2M + 2L + 1XL)
- **5 technical spikes** (9 days total)
- **3 SDK stories** (1S + 2M)
- **3 distribution/versioning stories** (1S + 2M)
- **4 CI/CD stories** (1S + 3M)

### What Fits in MVP vs Growth

**Add to MVP (v0.1) -- required for launch:**
- B4 (Demo Mode) -- marketing-critical
- SDK2 (Conformance Tests) -- enables plugin ecosystem from day one
- D1, V2, CI1, CI2, CI3 (distribution and CI) -- required to ship the ISO
- S1, S2 (HuggingFace Hub and MCAP spikes) -- inform design decisions before they become expensive

**Defer to Growth (v0.5):**
- B1 (Telemetry), B2 (Cloud Upload), B3 (Profile Sharing), B5 (Fleet Cloning)
- SDK1 (Scaffolding), SDK3 (Developer Guide)
- V1 (Update Command)
- CI4 (Self-Hosted Runner)
- S3, S4, S5 (Cloud training, distribution, OTA spikes)

---

*Implementation enhancements for armOS -- bridging business strategy to development work.*
