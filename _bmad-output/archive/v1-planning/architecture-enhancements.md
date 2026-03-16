# armOS Architecture Enhancements -- Business Alignment

**Date:** 2026-03-15
**Author:** Winston (Architect)
**Status:** Draft
**Scope:** New architectural sections required by vision, business plan, and market research. These are additive to `architecture.md` -- they do not replace anything in the existing document.

---

## Table of Contents

1. [Cloud Training Pipeline](#1-cloud-training-pipeline)
2. [Telemetry and Product Analytics](#2-telemetry-and-product-analytics)
3. [Profile Marketplace](#3-profile-marketplace)
4. [Education Fleet Management](#4-education-fleet-management)
5. [Partnership Integration Points](#5-partnership-integration-points)
6. [Foxglove / rerun.io Bridge](#6-foxglove--rerunio-bridge)
7. [ADRs for Enhancements](#7-adrs-for-enhancements)

---

## 1. Cloud Training Pipeline

**Business driver:** Cloud training is the primary monetization path (business plan Section 3.3). Users collect data on armOS (no GPU), upload to cloud, receive trained policies. Projected at $5-20 per training run, targeting 500+ runs/month by Year 2.

### 1.1 End-to-End Data Flow

```
armOS (local)                              Cloud
+------------------+                       +---------------------------+
| 1. Collect data  |                       |                           |
|    (LeRobot fmt) |                       |                           |
+--------+---------+                       |                           |
         |                                 |                           |
+--------v---------+    HTTPS POST         | +---------------------+  |
| 2. Package       | -------------------> | | 4. Validate dataset |  |
|    dataset       |    multipart/form     | +----------+----------+  |
|    (tar.gz)      |    or tus.io resume   |            |             |
+--------+---------+                       | +----------v----------+  |
         |                                 | | 5. Queue training   |  |
+--------v---------+    WebSocket/SSE      | |    (LeRobot CLI)    |  |
| 3. Track         | <------------------- | +----------+----------+  |
|    progress      |    status updates     |            |             |
+--------+---------+                       | +----------v----------+  |
         |                                 | | 6. Export policy     |  |
+--------v---------+    HTTPS GET          | |    (.pt file)       |  |
| 7. Download      | <------------------- | +---------------------+  |
|    policy file   |    signed URL         |                           |
+------------------+                       +---------------------------+
```

### 1.2 Local Components (armOS Side)

#### Dataset Packager

Converts a LeRobot recording session into an uploadable artifact.

```python
class DatasetPackager:
    """Packages recorded episodes into a cloud-uploadable archive."""

    def package(self, recording_dir: Path, metadata: RecordingMetadata) -> Path:
        """Create a tar.gz archive with:
        - episodes/ (LeRobot HDF5 or Parquet format)
        - metadata.json (robot profile, episode count, duration, camera config)
        - manifest.json (per-file SHA256 checksums for integrity verification)

        Returns path to the archive file.
        """

    def estimate_upload_size(self, recording_dir: Path) -> int:
        """Estimate archive size in bytes before packaging."""

    def validate_local(self, recording_dir: Path) -> list[ValidationError]:
        """Pre-flight checks: episode count > 0, no corrupted frames,
        checksums valid. Catches problems before wasting upload bandwidth."""
```

#### Upload Client

```python
class CloudUploadClient:
    """Handles dataset upload with resumable transfers."""

    def __init__(self, api_base: str = "https://api.armos.dev"):
        self._api_base = api_base

    def upload(self, archive_path: Path, api_key: str,
               on_progress: Callable[[int, int], None] = None) -> str:
        """Upload dataset archive. Returns a job_id.

        Uses tus.io resumable upload protocol so users on slow or
        unreliable connections can resume interrupted uploads.
        """

    def get_status(self, job_id: str, api_key: str) -> TrainingStatus:
        """Poll training job status. Returns queued/training/complete/failed."""

    def subscribe_status(self, job_id: str, api_key: str) -> Iterator[TrainingStatus]:
        """Server-Sent Events stream for real-time status updates."""

    def download_policy(self, job_id: str, api_key: str, dest: Path) -> Path:
        """Download the trained policy file (.pt) to dest."""
```

#### TUI Integration

The training pipeline surfaces in the TUI as a new workflow step after data collection:

```
[Record Episodes] -> [Review Dataset] -> [Upload to Cloud] -> [Monitor Training] -> [Download Policy] -> [Run Inference]
```

The `armos train --upload` CLI command provides the non-TUI path.

### 1.3 Cloud API Contract

The cloud service is a separate deployment (not part of the armOS USB image). The API contract is defined here so the local client can be built and tested against a mock.

```
POST   /v1/datasets              Upload dataset archive (tus.io endpoint)
GET    /v1/jobs/{job_id}         Get training job status
GET    /v1/jobs/{job_id}/events  SSE stream of status updates
GET    /v1/jobs/{job_id}/policy  Download trained policy (signed URL redirect)
POST   /v1/jobs/{job_id}/cancel  Cancel a queued or running job
GET    /v1/account/usage         Current billing period usage and limits
```

Authentication: API key in `Authorization: Bearer <key>` header. Keys are provisioned via the armOS web dashboard (armos.dev). Keys are stored locally in `~/.config/armos/cloud.yaml` (permissions 0600).

### 1.4 Training Backend (Cloud Side -- Design Only)

The cloud backend is out of scope for the armOS codebase but the architecture is documented here for consistency.

- **Compute:** Lambda Labs or vast.ai spot GPU instances, provisioned on demand.
- **Orchestration:** A lightweight job queue (Redis + worker pattern). No Kubernetes for v1 -- over-engineering for < 50 concurrent jobs.
- **Training runtime:** Containerized LeRobot training CLI with pinned dependencies matching the armOS version.
- **Storage:** S3-compatible object store (Cloudflare R2 for cost) for datasets and policy artifacts.
- **Billing:** Stripe usage-based billing. Metered by GPU-minutes consumed.

### 1.5 Offline Fallback

If the user has their own GPU machine, `armos train --local` generates a training script and dataset archive that can be transferred via USB or SCP. The cloud service is the easy path, not the only path. This aligns with Core Principle 3 (works offline).

### 1.6 Security Considerations

- Dataset archives may contain camera images of users' environments. The privacy policy must state that uploaded datasets are used solely for the user's training job and deleted after 30 days (or configurable retention).
- Policy files are model weights, not executable code. They are safe to download and load via `torch.load(..., weights_only=True)` (PyTorch 2.6+ safe loading).
- API keys are scoped per-user. No shared keys.

---

## 2. Telemetry and Product Analytics

**Business driver:** The data flywheel from the vision document -- more users produce more telemetry data, which improves defaults, which reduces problems, which attracts more users. Also required for the education fleet management dashboard (Section 4).

### 2.1 Design Principles

1. **Opt-in only.** First boot asks: "Help improve armOS by sharing anonymous usage data?" Default is OFF. Consent is stored in `~/.config/armos/telemetry.yaml`.
2. **Transparent.** `armos telemetry show` prints exactly what would be sent. `armos telemetry export` dumps it to a JSON file for inspection.
3. **Anonymous.** No user identity, no IP address logging, no camera data, no dataset content. Only aggregate hardware and usage metrics.
4. **Local-first.** All telemetry is collected to a local SQLite database regardless of consent. The opt-in controls whether it is ever transmitted. The local database powers the personal dashboard (`armos stats`).

### 2.2 What Is Collected

```yaml
# Telemetry event schema
event:
  type: enum  # session_start, session_end, hardware_detected, calibration_complete,
              # teleop_session, diagnostic_result, error_occurred, training_uploaded
  timestamp: ISO8601
  armos_version: str
  session_id: UUIDv4  # Random per-boot, not tied to user

# Hardware context (collected once per session)
hardware:
  cpu_model: str          # e.g. "Intel i5-1035G4"
  ram_gb: int
  usb_controllers: list   # Vendor/product IDs only (no serial numbers)
  robot_profile: str      # e.g. "so101" (profile name, not instance)
  servo_count: int
  camera_count: int

# Session metrics (collected per teleop/recording session)
session:
  duration_seconds: float
  teleop_latency_p50_ms: float
  teleop_latency_p95_ms: float
  teleop_latency_p99_ms: float
  comm_errors: int
  comm_retries: int
  episodes_recorded: int
  servo_warnings: dict    # {warning_type: count}

# Diagnostic results (collected per diagnostic run)
diagnostic:
  check_name: str
  result: enum  # pass, warn, fail
  # NO detailed diagnostic data -- just the check name and result
```

### 2.3 Transmission

- **Protocol:** HTTPS POST to `https://telemetry.armos.dev/v1/events`
- **Batching:** Events are buffered locally and transmitted in batches every 24 hours (or on graceful shutdown). No real-time streaming.
- **Payload:** JSON array of events. Gzip compressed. Typical batch is < 10 KB.
- **Failure handling:** If transmission fails (no internet, server down), events remain in the local buffer. No retry loop -- the next 24-hour cycle will include them. Buffer is capped at 90 days of events; older events are dropped.
- **Server:** Simple append-only event store. No user accounts. No correlation across sessions (session_id is random per-boot).

### 2.4 Analytics Pipeline (Server Side -- Design Only)

```
HTTPS POST -> append to event log -> daily batch ETL -> DuckDB warehouse
                                                             |
                                                   Grafana dashboard
                                                             |
                                           "What hardware is most common?"
                                           "What check fails most often?"
                                           "What is the median teleop latency?"
                                           "Are SO-101 users on firmware < 3.10?"
```

The analytics feed directly into product decisions:
- High failure rate on a specific check -> improve the default profile setting
- Specific CPU model has high latency -> investigate and optimize
- Most users have only 1 camera -> deprioritize multi-camera features

### 2.5 Local Database Schema

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL,  -- JSON
    transmitted INTEGER DEFAULT 0
);

CREATE INDEX idx_events_transmitted ON events(transmitted);
CREATE INDEX idx_events_type ON events(event_type);
```

Stored at `~/.local/share/armos/telemetry.db`. This database also powers the personal `armos stats` command, which shows the user their own usage patterns (total hours of teleop, episodes recorded, hardware health trends) regardless of whether they opted in to remote telemetry.

---

## 3. Profile Marketplace

**Business driver:** Community profiles create the network effect described in the vision -- each new profile makes armOS more valuable (business plan Section 3.5). Projected 20-30% commission on paid listings, launching Year 2.

### 3.1 Architecture Decision: Git-Based, Not App Store

Profiles are YAML files. They belong in Git, not in a custom app store backend. The marketplace is a curated Git repository with a web frontend, following the model of Homebrew taps, Arduino Library Manager, and Helm chart repositories.

```
GitHub: armos-community/profiles (the canonical registry)
    |
    | git clone / sparse checkout
    |
armOS local: /usr/share/armos/profiles/          (shipped with ISO, read-only)
             ~/.config/armos/profiles/            (user-installed, writable)
             ~/.config/armos/profiles/registry.yaml  (installed profile index)
```

### 3.2 Profile Registry Format

The registry is a single `registry.yaml` in the community repo root:

```yaml
# armos-community/profiles/registry.yaml
profiles:
  - name: so101
    version: "1.2.0"
    author: armos-team
    description: "HuggingFace SO-101 6-DOF arm (leader/follower pair)"
    hardware: [feetech-sts3215, ch340]
    license: Apache-2.0
    path: profiles/so101/
    verified: true       # Tested by armOS team on real hardware
    downloads: 0         # Tracked by GitHub traffic or download counter

  - name: koch-v1.1
    version: "1.0.0"
    author: community-user
    description: "Koch v1.1 arm with Dynamixel XL-330 servos"
    hardware: [dynamixel-xl330, ftdi-ft232]
    license: MIT
    path: profiles/koch-v1.1/
    verified: false
    downloads: 0

  - name: so101-tuned-fast
    version: "0.9.0"
    author: robotics-lab-mit
    description: "SO-101 with aggressive PID tuning for fast pick-and-place"
    hardware: [feetech-sts3215, ch340]
    license: CC-BY-4.0
    path: profiles/so101-tuned-fast/
    verified: false
    paid: true
    price_usd: 5.00
    downloads: 0
```

### 3.3 Profile Package Structure

Each profile in the registry is a directory:

```
profiles/so101/
    profile.yaml          # The robot profile (same format as architecture.md Section 5)
    README.md             # Human-readable description, photos, setup notes
    calibration/          # Optional: reference calibration for this hardware
        default.json
    diagnostics/          # Optional: profile-specific diagnostic checks
        power_supply.py
    CHANGELOG.md
    LICENSE
```

### 3.4 CLI Commands

```bash
armos profile list                    # List installed profiles
armos profile search "koch"           # Search the community registry
armos profile install koch-v1.1       # Download and install from registry
armos profile install ./my-profile/   # Install from local directory
armos profile update                  # Update all installed profiles
armos profile publish                 # Validate and submit a PR to the community repo
armos profile verify so101            # Run the profile's diagnostic suite against connected hardware
```

### 3.5 Contribution Workflow

```
Contributor                         armos-community/profiles repo
    |                                        |
    | 1. armos profile publish               |
    |   -> validates YAML schema             |
    |   -> runs diagnostic checks locally    |
    |   -> creates a fork + branch           |
    |   -> opens a PR                        |
    |                                        |
    |                               2. CI validates:
    |                                  - YAML schema
    |                                  - No executable code in profile.yaml
    |                                  - License file present
    |                                  - README present
    |                                  - Diagnostic scripts pass linting
    |                                        |
    |                               3. Maintainer reviews:
    |                                  - Hardware compatibility claims
    |                                  - "verified" badge (if tested)
    |                                        |
    |                               4. Merge -> profile available
```

### 3.6 Paid Profiles (Year 2)

For paid profiles, the marketplace adds a thin payment layer:

- Buyer clicks "Install" on armos.dev web UI
- Payment via Stripe Checkout ($5-50 per profile, set by author)
- On success, buyer receives a license key
- `armos profile install koch-tuned --license-key <key>` unlocks the download
- License keys are tied to an armos.dev account, not a machine. Users can install on multiple machines.
- Revenue split: 70% author / 30% armOS (matches App Store conventions)

The paid layer is a web service addition. The core profile format and CLI remain the same for free and paid profiles.

### 3.7 HuggingFace Hub Integration

For profiles that include trained policies (not just hardware configuration), the policy weights are stored on HuggingFace Hub rather than in the Git repo (Git is not designed for large binary files).

```yaml
# In profile.yaml
policies:
  pick_and_place:
    source: huggingface
    repo_id: armos-community/so101-pick-place
    revision: main
    file: policy.pt
    description: "Pick-and-place policy trained on 200 demonstrations"
```

`armos profile install` detects the HuggingFace reference and downloads from Hub using the `huggingface_hub` Python library (already a LeRobot dependency). This keeps the profile registry lean while leveraging HuggingFace's infrastructure for model hosting.

---

## 4. Education Fleet Management

**Business driver:** Education licensing at $50-200/seat/year (business plan Section 3.4). A classroom with 30 arms needs centralized management, not 30 individual setups.

### 4.1 Architecture: Hub and Spoke

```
                        +----------------------+
                        |   Fleet Hub          |
                        |   (instructor laptop |
                        |    or lab server)    |
                        |                      |
                        |   FastAPI + SQLite   |
                        |   Web dashboard      |
                        +----------+-----------+
                                   |
                    mDNS discovery  |  HTTP/WebSocket
                  (armos-hub.local) |
              +--------------------+--------------------+
              |                    |                    |
    +---------v------+   +---------v------+   +---------v------+
    | Station 1      |   | Station 2      |   | Station N      |
    | (student USB)  |   | (student USB)  |   | (student USB)  |
    | armos-agent    |   | armos-agent    |   | armos-agent    |
    +----------------+   +----------------+   +----------------+
```

### 4.2 Fleet Hub (Instructor Side)

The Fleet Hub is a FastAPI web application that runs on the instructor's machine (or a dedicated lab server). It is included in the armOS image but disabled by default -- enabled via `armos fleet hub start`.

```python
class FleetHub:
    """Central management server for a classroom fleet."""

    # Station management
    def register_station(self, station: StationInfo) -> str:
        """Accept a station registration. Returns a station_id."""

    def list_stations(self) -> list[StationStatus]:
        """List all registered stations with current status."""

    def get_station(self, station_id: str) -> StationStatus:
        """Detailed status for one station: hardware, diagnostics, current activity."""

    # Configuration push
    def push_profile(self, profile_name: str, station_ids: list[str]) -> None:
        """Push a robot profile to selected stations."""

    def push_config_override(self, overrides: dict, station_ids: list[str]) -> None:
        """Push configuration overrides (e.g., lock down teleop FPS for beginners)."""

    # Classroom mode
    def lock_stations(self, station_ids: list[str]) -> None:
        """Lock stations to prevent students from changing configuration."""

    def unlock_stations(self, station_ids: list[str]) -> None:
        """Unlock stations."""

    # Data collection coordination
    def start_recording_all(self, task_name: str) -> None:
        """Signal all stations to begin a recording session for a given task."""

    def collect_datasets(self, station_ids: list[str], dest: Path) -> None:
        """Download recorded datasets from selected stations to the hub."""
```

### 4.3 Fleet Agent (Student Side)

Every armOS station runs a lightweight agent that registers with the hub on the local network.

```python
class FleetAgent:
    """Runs on each student station. Reports status, accepts commands from hub."""

    def __init__(self):
        self._hub_url: Optional[str] = None  # Discovered via mDNS or manual config

    def discover_hub(self) -> Optional[str]:
        """Use mDNS (zeroconf) to find armos-hub.local on the LAN."""

    def register(self) -> None:
        """Register this station with the hub. Sends hardware info, profile, status."""

    def heartbeat_loop(self) -> None:
        """Send status updates to hub every 10 seconds via WebSocket."""

    def handle_command(self, command: FleetCommand) -> None:
        """Execute a command from the hub (push_profile, lock, start_recording, etc.)."""
```

### 4.4 Discovery Protocol

- **Primary:** mDNS via `zeroconf` Python library. The hub advertises `_armos-hub._tcp.local.` on the LAN. Stations discover it automatically on boot.
- **Fallback:** Manual hub URL in `~/.config/armos/fleet.yaml` for networks where mDNS is blocked.
- **Security:** The hub generates a classroom join code (6-digit alphanumeric) displayed on the instructor's screen. Students enter it once on first connection. This prevents unauthorized stations from joining. The join code maps to an HMAC key used to sign subsequent WebSocket messages.

### 4.5 Station Status Model

```python
@dataclass
class StationStatus:
    station_id: str
    hostname: str
    student_name: Optional[str]        # Set by student in TUI
    ip_address: str
    armos_version: str
    robot_profile: Optional[str]       # e.g., "so101"
    hardware_status: HardwareStatus    # CONNECTED / PARTIAL / DISCONNECTED
    activity: Activity                 # IDLE / CALIBRATING / TELEOP / RECORDING / ERROR
    last_heartbeat: datetime
    diagnostics_summary: dict          # {check_name: pass/warn/fail}
    episodes_recorded: int
    errors_last_hour: int
```

### 4.6 Web Dashboard

The hub serves a web dashboard at `http://armos-hub.local:8080/`:

```
+----------------------------------------------------------------+
|  armOS Fleet Dashboard            [Classroom: Robotics 101]    |
+----------------------------------------------------------------+
|                                                                 |
|  Stations Online: 28/30          Errors: 2                     |
|                                                                 |
|  +----+----+----+----+----+----+----+----+----+----+           |
|  | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 |         |
|  | OK | OK | !! | OK | OK | OK | -- | OK | OK | OK |           |
|  +----+----+----+----+----+----+----+----+----+----+           |
|  | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 |         |
|  | OK | OK | OK | OK | OK | OK | OK | OK | !! | OK |           |
|  +----+----+----+----+----+----+----+----+----+----+           |
|                                                                 |
|  [Start Recording All]  [Collect Datasets]  [Lock All]         |
+----------------------------------------------------------------+
```

Station tiles are color-coded: green (OK), yellow (warning), red (error), gray (offline). Clicking a tile shows detailed status and diagnostics for that station.

### 4.7 Network Requirements

- All communication is LAN-only. No cloud dependency for fleet management.
- Hub and stations must be on the same subnet (or have mDNS routing configured).
- Bandwidth: minimal for status (< 1 KB/heartbeat). Dataset collection is the heavy operation -- a 50-episode dataset is ~500 MB. Over gigabit LAN, 30 stations can transfer simultaneously in under 5 minutes.
- The hub runs on the instructor's armOS USB or on a dedicated Linux machine. It does not require special hardware.

---

## 5. Partnership Integration Points

**Business driver:** Hardware partnerships are a primary distribution channel (business plan Section 3.2). Seeed Studio, Feetech, HuggingFace, and NVIDIA are named targets.

### 5.1 Integration Architecture

```
+---------------------------+
|     Partner Ecosystem     |
+---------------------------+
|                           |
| Seeed Studio / Feetech   |-----> Robot Profile (YAML)
|   - Hardware specs        |       + Verified badge
|   - Servo register maps   |       + Official diagnostics
|   - Default PID values    |       + Co-branded name
|                           |
| HuggingFace               |-----> LeRobot Bridge Layer
|   - LeRobot API           |       + Dataset upload to Hub
|   - Dataset format        |       + Model download from Hub
|   - Model hosting (Hub)   |       + "Certified for armOS" badge
|                           |
| NVIDIA                    |-----> Inference Runtime Plugin
|   - OpenVINO (Intel)      |       + Model format conversion
|   - TensorRT (Jetson)     |       + Hardware-accelerated inference
|                           |
| Foxglove / rerun.io       |-----> Data Export Bridge
|   - MCAP format           |       (See Section 6)
|   - Arrow IPC format      |
+---------------------------+
```

### 5.2 Seeed Studio / Feetech Integration

These partners provide hardware. The integration is through official robot profiles.

**What armOS provides to partners:**
- A verified, tested robot profile for their hardware.
- Reduced support burden -- armOS diagnoses the problems their customers currently email them about.
- An `armos-<partner>-edition.iso` co-branded image (same ISO, different GRUB splash screen and default profile).
- A "Works with armOS" badge SVG for their product listings.

**What partners provide to armOS:**
- Access to pre-release hardware for profile development.
- Register maps and firmware documentation (Feetech's STS3215 datasheet is incomplete -- direct contact yields undocumented registers).
- Distribution: USB sticks bundled with kits, or a download link in their wiki.

**Technical integration point:** The partner's profile is a YAML file in `armos-community/profiles/` marked `verified: true` and `partner: seeed-studio`. No code changes are needed in armOS core.

### 5.3 HuggingFace Integration

HuggingFace is the upstream dependency (LeRobot) and the model/dataset hosting platform.

**Integration points:**

1. **LeRobot Bridge (already in architecture.md Section 7):** armOS wraps LeRobot for data collection and inference. The bridge layer isolates armOS from LeRobot API changes.

2. **Dataset Upload to HuggingFace Hub:**
   ```python
   # In armos/cloud/huggingface.py
   from huggingface_hub import HfApi

   def upload_dataset(dataset_path: Path, repo_id: str, token: str) -> str:
       """Upload a LeRobot dataset to HuggingFace Hub.
       Returns the dataset URL."""
       api = HfApi()
       api.upload_folder(
           folder_path=dataset_path,
           repo_id=repo_id,
           repo_type="dataset",
           token=token,
       )
       return f"https://huggingface.co/datasets/{repo_id}"
   ```

3. **Policy Download from HuggingFace Hub:**
   ```python
   def download_policy(repo_id: str, filename: str = "policy.pt",
                       revision: str = "main") -> Path:
       """Download a trained policy from HuggingFace Hub.
       Returns local path to the downloaded file."""
       from huggingface_hub import hf_hub_download
       return Path(hf_hub_download(repo_id=repo_id, filename=filename,
                                    revision=revision))
   ```

4. **"Certified for armOS" Badge:** A metadata field in HuggingFace model cards indicating the policy was trained on armOS-collected data and tested on armOS inference. This is a marketing tool, not a technical requirement.

### 5.4 NVIDIA / Intel Inference Optimization

armOS runs on Intel integrated graphics (no CUDA). But two optimization paths exist:

1. **Intel OpenVINO (MVP-adjacent):** Convert PyTorch policy models to OpenVINO IR format for 2-5x inference speedup on Intel CPUs. The conversion is a one-line call (`mo --input_model policy.pt`). armOS can ship `openvino-runtime` in the ISO and automatically convert downloaded policies.

2. **NVIDIA Jetson (Growth scope):** If armOS expands to ARM/Jetson, TensorRT conversion provides GPU-accelerated inference. This is a separate ISO build target, not a modification to the x86 image.

**Integration point:** An `InferenceBackend` abstraction in the AI integration layer:

```python
class InferenceBackend(ABC):
    @abstractmethod
    def load_policy(self, policy_path: Path) -> Any: ...

    @abstractmethod
    def predict(self, observation: dict) -> dict: ...

class PyTorchBackend(InferenceBackend): ...    # Default, always available
class OpenVINOBackend(InferenceBackend): ...   # Optional, if openvino installed
class TensorRTBackend(InferenceBackend): ...   # Jetson only
```

Backend selection is automatic based on available hardware, overridable via `--backend openvino`.

---

## 6. Foxglove / rerun.io Bridge

**Business driver:** The business plan (Appendix B) positions Foxglove and rerun.io as complementary tools -- armOS owns "getting started," they own "power user analysis." A data bridge makes armOS more valuable to advanced users without competing with well-funded visualization tools.

### 6.1 Architecture Decision: Export, Not Embed

armOS does NOT embed Foxglove or rerun viewers. Instead, it exports data in their native formats. Users open the exported files in Foxglove Studio or rerun Viewer on their own machine.

**Rationale:**
- Foxglove Studio is a 200+ MB Electron app. Too large for the USB image.
- rerun Viewer requires a GPU for rendering. armOS targets Intel integrated graphics.
- Both tools are actively developed; embedding a version creates a maintenance liability.
- Export is simpler, more flexible, and respects the tools' business models.

### 6.2 Foxglove Export (MCAP Format)

Foxglove's native format is [MCAP](https://mcap.dev/), an open container format for multimodal time-series data. MCAP supports arbitrary message schemas (Protobuf, JSON Schema, ROS2 messages, etc.).

```python
class FoxgloveExporter:
    """Exports armOS telemetry sessions to MCAP files for Foxglove Studio."""

    def export_session(self, session_dir: Path, output_path: Path) -> Path:
        """Convert an armOS telemetry/recording session to MCAP.

        Channels written:
        - /servo/{id}/position     (float64, per-servo position in degrees)
        - /servo/{id}/velocity     (float64, per-servo velocity)
        - /servo/{id}/load         (float64, per-servo load percentage)
        - /servo/{id}/voltage      (float64, per-servo voltage)
        - /servo/{id}/temperature  (int32, per-servo temp in Celsius)
        - /diagnostics             (JSON, diagnostic check results)
        - /camera/{name}/image     (compressed image, JPEG)
        - /command/goal_positions  (float64[], commanded joint positions)

        Schema: JSON Schema (no Protobuf dependency).
        """
```

**Dependencies:** `mcap` (Python library, ~50 KB, MIT license). Already supports JSON Schema encoding. No Protobuf compilation step needed.

**CLI:**
```bash
armos export foxglove ./session-2026-03-15/ -o session.mcap
# User opens session.mcap in Foxglove Studio on their own machine
```

### 6.3 rerun.io Export (Arrow IPC / .rrd Format)

rerun's native format is `.rrd` (rerun recording data), which is based on Apache Arrow IPC. The `rerun-sdk` Python package provides the writer.

```python
class RerunExporter:
    """Exports armOS telemetry sessions to rerun .rrd files."""

    def export_session(self, session_dir: Path, output_path: Path) -> Path:
        """Convert an armOS telemetry/recording session to .rrd.

        Entities logged:
        - /robot/joint/{name}/position    (Scalar)
        - /robot/joint/{name}/velocity    (Scalar)
        - /robot/joint/{name}/load        (Scalar)
        - /robot/servo/{id}/voltage       (Scalar)
        - /robot/servo/{id}/temperature   (Scalar)
        - /camera/{name}                  (Image)
        - /diagnostics/{check}            (TextLog)

        Uses rerun's timeline concept: one "frame" timeline for
        teleop cycles, one "wall_clock" timeline for real time.
        """
```

**Dependencies:** `rerun-sdk` (~15 MB). This is heavier than mcap but still reasonable for the ISO. Consider making it an optional install (`armos install rerun-export`).

**CLI:**
```bash
armos export rerun ./session-2026-03-15/ -o session.rrd
# User opens session.rrd in rerun Viewer on their own machine
```

### 6.4 Live Streaming (Growth Scope)

For real-time visualization during teleop (not just post-hoc export), both tools support network streaming:

- **Foxglove:** WebSocket server on `ws://localhost:8765` using the Foxglove WebSocket protocol. Foxglove Studio connects and renders live.
- **rerun:** `rr.serve()` spins up a web server that the rerun web viewer connects to.

The live streaming bridge runs as an optional sidecar process:

```bash
armos teleop --foxglove-live    # Starts teleop + Foxglove WS server
armos teleop --rerun-live       # Starts teleop + rerun serve
```

This is Growth scope because it adds latency to the teleop loop (serializing and transmitting every frame). The export path is MVP-adjacent.

### 6.5 Data Format Mapping

| armOS Internal | Foxglove MCAP | rerun .rrd | ROS2 (future bridge) |
|---------------|---------------|------------|---------------------|
| ServoTelemetry | JSON Schema channel | Scalar entities | sensor_msgs/JointState |
| Camera frame | compressed_image | Image archetype | sensor_msgs/Image |
| Diagnostic result | JSON channel | TextLog entity | diagnostic_msgs/DiagnosticArray |
| Goal positions | JSON Schema channel | Scalar entities | trajectory_msgs/JointTrajectory |

This mapping table ensures all three export targets (Foxglove, rerun, ROS2) can be served from the same internal data model. The internal telemetry stream (architecture.md Section 6) is the single source of truth.

---

## 7. ADRs for Enhancements

### ADR-8: Cloud Training API Protocol

**Status:** Proposed
**Context:** The cloud training service needs a protocol between armOS (local) and the training backend (cloud).
**Decision:** HTTPS REST API with tus.io for resumable uploads and Server-Sent Events for status streaming. No gRPC, no custom protocol.
**Rationale:** HTTPS works through firewalls and proxies without configuration. tus.io is the standard for resumable uploads (used by Vimeo, GitHub, Cloudflare). SSE is simpler than WebSocket for unidirectional status updates. The target users are on home/university networks where exotic protocols are likely blocked.
**Consequences:** Higher overhead than gRPC for status polling. Acceptable -- status updates are infrequent (every few seconds during training).

### ADR-9: Telemetry Storage Format

**Status:** Proposed
**Context:** Telemetry data is collected locally and optionally transmitted to the analytics server.
**Decision:** SQLite for local storage. JSON-over-HTTPS for transmission. DuckDB for server-side analytics.
**Rationale:** SQLite is zero-config, ships with Python, and handles concurrent reads from the `armos stats` command while the telemetry collector writes. DuckDB is columnar and optimized for the aggregate queries the analytics dashboard needs. JSON-over-HTTPS is the simplest transmission format and is trivially debuggable with curl.
**Consequences:** Local SQLite database grows over time. Mitigated by 90-day retention cap and VACUUM on startup.

### ADR-10: Profile Distribution Mechanism

**Status:** Proposed
**Context:** Community robot profiles need to be discoverable, installable, and updatable.
**Decision:** Git repository as the canonical registry, with `armos profile install` performing sparse checkout of individual profiles. HuggingFace Hub for binary policy weights.
**Rationale:** Git is the lingua franca of open-source contribution. A GitHub PR workflow for new profiles provides review, CI validation, and an audit trail. Homebrew and Helm have proven this model works at scale. HuggingFace Hub is already a dependency (via LeRobot) and is purpose-built for hosting model weights.
**Alternatives considered:** (a) PyPI packages per profile -- too heavy for YAML files. (b) Custom HTTP API -- unnecessary infrastructure. (c) HuggingFace Hub for everything -- Hub is not designed for small YAML files with PR-based review workflows.
**Consequences:** Requires Git on the armOS image (already present). Requires network for `armos profile install` (but installed profiles work offline). Paid profiles require a separate license key mechanism layered on top.

### ADR-11: Fleet Management Discovery Protocol

**Status:** Proposed
**Context:** Education fleet management requires stations to find the instructor's hub on the LAN.
**Decision:** mDNS via `zeroconf` Python library, with manual URL fallback.
**Rationale:** mDNS is zero-configuration on most LANs. The `zeroconf` library is pure Python, ~100 KB, and well-maintained. University networks sometimes block mDNS, hence the manual fallback. The 6-digit join code provides lightweight authentication without requiring PKI or user accounts.
**Consequences:** Adds `zeroconf` as a dependency (~100 KB). Fleet features are disabled by default and only activate when `armos fleet` commands are used.

### ADR-12: Visualization Bridge Strategy

**Status:** Proposed
**Context:** Foxglove ($58M raised) and rerun.io ($20M raised) are well-funded visualization tools. armOS should integrate, not compete.
**Decision:** Export-only for MVP (MCAP and .rrd file export). Live streaming as Growth scope. No embedded viewers.
**Rationale:** Embedding viewers adds hundreds of MB to the ISO and creates version coupling with actively developed external tools. Export files are stable and version-independent. Users who need visualization already have these tools installed on their development machines. The export path positions armOS as a data source, not a visualization tool.
**Consequences:** Users must install Foxglove or rerun separately. This is acceptable -- these are power-user tools, not beginner workflows. The `mcap` library is tiny; `rerun-sdk` is 15 MB and may be made optional.

---

## 8. Implementation Priority

These enhancements map to the vision's three horizons:

| Enhancement | Horizon | When to Build | Dependency |
|------------|---------|---------------|------------|
| Foxglove/rerun export (file) | H1 (MVP-adjacent) | Sprint 7-8 | Telemetry stream from architecture.md |
| Telemetry local DB + `armos stats` | H1 (MVP-adjacent) | Sprint 7-8 | Metrics module from architect review rec #21 |
| Profile marketplace (Git-based) | H2 (Platform) | Month 7-9 | Profile system from architecture.md Section 5 |
| Cloud training client (local side) | H2 (Platform) | Month 7-9 | Data collection pipeline from architecture.md Section 7 |
| Telemetry transmission (opt-in) | H2 (Platform) | Month 9-10 | Local telemetry DB |
| Fleet management (hub + agent) | H2 (Platform) | Month 10-12 | Web dashboard from architecture.md Section 8 |
| Cloud training backend (server) | H2 (Platform) | Month 9-12 | Cloud API contract (Section 1.3) |
| Paid profiles + license keys | H2 (Platform) | Month 12+ | Profile marketplace |
| Live Foxglove/rerun streaming | H2 (Platform) | Month 12+ | Export bridge |
| OpenVINO inference optimization | H2 (Platform) | Month 10-12 | Inference backend abstraction |
| NVIDIA Jetson support | H3 (Intelligence) | Month 18+ | ARM ISO build pipeline |

**Key principle:** The local-side components (export, telemetry DB, upload client) should be built before their server-side counterparts. This lets users benefit from local tooling immediately while the cloud infrastructure is developed.

---

*Architecture enhancements for armOS business alignment -- Winston (Architect)*
