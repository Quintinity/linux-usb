# Quick Tech Spec: Raspberry Pi 5 + AI HAT Support for armOS

**Date:** 2026-03-15
**Author:** Barry (Quick Flow Solo Dev)
**Status:** Implementation-Ready Draft
**Type:** Quick Spec -- RPi 5 Platform Expansion
**References:** architecture.md Section 18, frontier-hardware-ecosystem.md Section 2.1, frontier-ai-intelligence.md Section 7, epics.md

---

## 1. Scope

### What is being built

Five deliverables that bring armOS to the Raspberry Pi 5 platform with hardware-accelerated **vision** (object detection, pose estimation) via the Hailo AI HAT, and CPU-based policy inference with optional cloud offload:

1. **armOS pip package on ARM/RPi OS** -- the existing `armos` Python package installs and runs on `aarch64` Raspberry Pi OS (Bookworm) without modification to the host OS beyond a pip install and udev rule.

2. **HailoBackend vision plugin** -- a new `VisionBackend` subclass that uses the HailoRT Python API to run object detection (YOLO) and pose estimation on the Hailo-8L (13 TOPS) or Hailo-8 (26 TOPS) accelerator. **Note:** Research confirmed Hailo cannot compile transformer-based robot policies (ACT, Octo, diffusion). Policy inference remains CPU-only locally or cloud-offloaded via LeRobot PolicyServer.

3. **RPi 5 robot profile** -- a YAML profile (`rpi5-so101`) that describes the RPi 5 + SO-101 arm hardware configuration, including USB-serial port patterns, camera device paths (USB and CSI via libcamera), and Hailo device detection.

4. **RPi 5 SD card image** (stretch goal) -- a pre-built `.img` file based on Raspberry Pi OS Lite with armOS, HailoRT, and all dependencies pre-installed. Flash, boot, plug in arm, go.

5. **LeKiwi mobile base profile** -- extends the RPi 5 profile with 3 additional Feetech STS3215 drive motors for the omnidirectional base, matching the LeRobot LeKiwi configuration.

### What is NOT being built

- No custom kernel or kernel modules (stock RPi OS kernel supports AI HAT natively since 2025).
- No NVIDIA Jetson support (separate spec, Horizon 3).
- No CAN bus servo driver (separate epic).
- No cloud training pipeline changes (existing cloud pipeline works regardless of edge platform).
- No new TUI -- the existing Textual TUI runs on RPi 5 over SSH or local terminal.

---

## 2. Delivery Format Decision

### Options

| Option | Effort | Time to Ship | UX Quality | Maintenance Burden |
|--------|--------|-------------|------------|-------------------|
| **A: pip install on stock RPi OS** | Low | 2-3 weeks | Good (requires terminal) | Low -- piggybacks on RPi OS updates |
| **B: Custom RPi OS image** | High | 6-8 weeks | Excellent (flash and go) | High -- must rebuild on every RPi OS update |
| **C: Docker container on RPi OS** | Medium | 3-4 weeks | Fair (Docker adds complexity) | Medium -- Docker + USB passthrough is fragile |

### Recommendation: Ship A first, then B

**Option A (pip install) ships first.** Rationale:

- Fastest path to real hardware validation. We need RPi 5 + Hailo running armOS to benchmark inference latency before committing to an image build pipeline.
- The armOS package is already pure Python with no compiled extensions. ARM compatibility requires only testing, not porting.
- LeKiwi users already have Raspberry Pi OS running. Asking them to `pip install armos` in an existing venv is the lowest friction path.
- Option B (SD card image) becomes straightforward once A works -- it is just Option A baked into a pi-gen build. Ship B as Story R4 after R1-R3 validate the stack.

**Skip Option C (Docker).** On RPi 5, Docker adds ~100MB overhead, USB device passthrough requires `--privileged` (security concern on an embedded robot), and the RPi community expects native packages, not containers. Docker makes sense for x86 dev machines, not for embedded deployment.

---

## 3. Hailo Integration

### 3.1 Architecture

The existing `InferenceBackend` ABC (architecture.md Section 7) defines the plugin interface:

```python
class InferenceBackend(ABC):
    def load_policy(self, policy_path: Path) -> Any: ...
    def predict(self, observation: dict) -> dict: ...
```

Current implementations: `PyTorchBackend`, `OpenVINOBackend`, `TensorRTBackend` (stub).

The new `HailoBackend` slots in as a fourth implementation:

```python
class HailoBackend(InferenceBackend):
    """Inference backend for Hailo-8/8L via AI HAT+."""

    def __init__(self, device_id: str = "/dev/hailo0"):
        from hailo_platform import HailoRTClient  # HailoRT >= 4.20
        self._client = HailoRTClient(device_id)
        self._hef = None

    def load_policy(self, policy_path: Path) -> None:
        """Load a compiled .hef model file."""
        self._hef = self._client.load_hef(str(policy_path))
        self._input_vstream = self._hef.create_input_vstreams()
        self._output_vstream = self._hef.create_output_vstreams()

    def predict(self, observation: dict) -> dict:
        """Run inference on Hailo accelerator."""
        # Pack observation tensors into input format
        input_data = self._pack_observation(observation)
        self._input_vstream.send(input_data)
        output_data = self._output_vstream.recv()
        return self._unpack_actions(output_data)
```

### 3.2 Model Conversion Pipeline

ONNX models (the armOS standard interchange format) must be compiled to Hailo Executable Format (.hef) before they can run on the Hailo accelerator. This is a one-time offline step.

```
[ONNX model] --> [Hailo Dataflow Compiler (DFC)] --> [.hef file] --> [HailoRT on device]
```

**Key constraint:** The Hailo Dataflow Compiler runs on x86 Linux only (not on the RPi itself). The conversion must happen on a dev machine or in CI, and the `.hef` file is distributed alongside the ONNX model.

**CLI command:**

```bash
armos model compile --backend hailo --input policy.onnx --output policy.hef
```

This wraps the DFC Docker container (`hailo_ai/hailo_dataflow_compiler`) so users do not need to install the DFC toolchain directly. For CI, the same Docker image runs in GitHub Actions.

### 3.3 Target Models (Priority Order)

**CRITICAL UPDATE:** Research (see `research-rpi5-ai-hat.md`) confirmed that the Hailo Dataflow Compiler **cannot compile transformer-based robot policies** (ACT, Octo, diffusion models). The Hailo model zoo is entirely vision-focused. There is no ONNX Runtime execution provider for Hailo.

| Model | Use Case | ONNX Size | Expected Hailo Latency | Priority |
|-------|----------|-----------|----------------------|----------|
| **YOLOv8s** | Object detection | ~22 MB | 2-5ms (431+ FPS confirmed) | **P0** -- proven in Hailo model zoo |
| **YOLO-World-S** | Open-vocab object detection | ~50 MB | 10-25ms | **P1** -- enables "pick up the red block" |
| **YOLOv8s-Pose** | Human/robot pose estimation | ~25 MB | 3-8ms | P1 -- hand tracking for teleop |
| **MobileNetV3** | Image classification | ~10 MB | <2ms | P2 -- scene understanding |

**Robot policy models (ACT, Octo, diffusion) run on:**
- **CPU locally** (Octo-Small: 1-3 Hz on RPi 5 — sufficient for slow manipulation)
- **Remote GPU server** via LeRobot PolicyServer + ZeroMQ (30+ Hz, requires network)

### 3.4 Expected Performance

| Metric | RPi 5 CPU Only | RPi 5 + Hailo-8L (13 TOPS) | Notes |
|--------|---------------|---------------------------|-------|
| YOLO object detection | 200-400ms | 2-5ms (431+ FPS) | Hailo excels here |
| YOLO-World open-vocab | 500-1500ms | 10-25ms | Hailo excels here |
| Octo-Small policy | 150-400ms (1-3 Hz) | **Same (CPU only)** | Hailo cannot run transformers |
| ACT policy | 200-600ms | **Same (CPU only)** | Hailo cannot run transformers |
| Policy via cloud server | N/A | 30-60 Hz via ZeroMQ | Requires GPU server on LAN |
| Power draw | ~8W | ~12W (CPU + HAT) | 27W PSU required |

### 3.5 Revised Architecture

The AI HAT's value is **real-time vision**, not policy inference. The correct architecture is:

```
┌─────────────────────────────────────────────────┐
│  RPi 5 + AI HAT                                 │
│                                                  │
│  Camera → [Hailo: YOLO @ 100+ FPS] → detections │
│                       ↓                          │
│  detections + servo state → [CPU: Octo @ 2 Hz]  │
│        OR                                        │
│  detections + servo state → [Cloud: Octo @ 30Hz] │
│                       ↓                          │
│  actions → [Servo control loop @ 60 Hz]          │
└─────────────────────────────────────────────────┘
```

The Hailo handles perception (what objects are where), the CPU or cloud handles decisions (what to do), and the servo loop handles execution.

---

## 4. Hardware Requirements

### Minimum Configuration (teleoperation only)

| Component | Product | Price | Notes |
|-----------|---------|-------|-------|
| SBC | Raspberry Pi 5 4GB | $60 | Minimum RAM for armOS + LeRobot |
| Power | RPi 5 USB-C PSU (27W) | $12 | Official 5.1V/5A supply required |
| Storage | 32GB microSD (A2) | $10 | 16GB too tight with LeRobot datasets |
| USB-serial | CH340 adapter (included with SO-101) | $0 | Same adapter as x86 setup |
| Camera | **RPi Camera Module 3 Wide** (CSI) | $35 | 102° HFOV, 12MP, autofocus, 120fps. CSI has 4x lower latency than USB (~200ms vs ~800ms) and <5% CPU vs ~17%. |
| Robot arm | SO-101 | $220 | Feetech STS3215 x6 |
| **Total** | | **~$317-352** | Teleoperation and data collection |

### Recommended Configuration (autonomous inference)

| Component | Product | Price | Notes |
|-----------|---------|-------|-------|
| SBC | Raspberry Pi 5 8GB | $90 | Headroom for model loading |
| AI accelerator | AI HAT+ with Hailo-8L | $70 | 13 TOPS, M.2 Key M on HAT+ board |
| Power | RPi 5 USB-C PSU (27W) | $12 | 27W supply mandatory with AI HAT |
| Storage | 64GB microSD (A2) | $15 | Room for multiple HEF models + datasets |
| Active cooling | Official RPi 5 Active Cooler | $5 | Required under sustained inference load |
| USB-serial | CH340 adapter | $0 | Included with SO-101 |
| Camera | **RPi Camera Module 3 Wide** (CSI) | $35 | 102° HFOV, 12MP, autofocus lockable to fixed distance. 200ms latency vs 800ms USB. Frees USB port for servo controller. |
| Robot arm | SO-101 | $220 | Feetech STS3215 x6 |
| **Total** | | **~$437** | Autonomous policy execution |

### Upgrade: Hailo-8 (full)

| Component | Product | Price | Notes |
|-----------|---------|-------|-------|
| AI accelerator | AI HAT+ with Hailo-8 | $110 | 26 TOPS, 2x the Hailo-8L. Same M.2 form factor. |

Swap-in upgrade. No software changes -- HailoRT abstracts the chip variant.

### Power Supply Notes

- The official 27W (5.1V/5A) USB-C PSU is mandatory when the AI HAT+ is installed. The standard 15W supply causes undervoltage throttling under inference load.
- The SO-101 arm has its own 12V supply for servos. The RPi does not power the servos.
- LeKiwi mobile base adds 3 more STS3215 servos on the same 12V bus -- no additional RPi power draw.

---

## 5. Stories Breakdown

### Epic R: Raspberry Pi 5 + AI HAT Platform Support

**Product Scope:** Growth (v0.5)
**Dependencies:** Requires MVP Epic 1 (package structure), Epic 2 (HAL/ServoProtocol), Epic 3 (profiles), and Epic 7 (AI integration layer) to be complete or near-complete.

---

### Story R1: armOS pip Package Works on ARM/RPi OS

**Size:** M (5 story points)
**Sprint:** Can begin once Epic 1 + Epic 2 are complete (Sprint 5+)

As a **LeKiwi builder**,
I want to install armOS on my existing Raspberry Pi OS with `pip install armos`,
so that I can use armOS without replacing my operating system.

**Tasks:**
1. Add `aarch64` to the supported platforms in `pyproject.toml`.
2. Replace any x86-specific dependencies (if any) with platform-conditional alternatives.
3. Ensure `pyudev`, `pyserial`, and `textual` install cleanly on RPi OS Bookworm.
4. Add ARM CI runner (GitHub Actions `ubuntu-24.04-arm` or self-hosted RPi 5) to run the test suite on `aarch64`.
5. Write an install guide: `docs/rpi5-quickstart.md`.
6. Create udev rule installer that works on RPi OS (same as x86, but verify path and group).

**Acceptance Criteria:**

**Given** a Raspberry Pi 5 running Raspberry Pi OS Bookworm (64-bit)
**When** I run `pip install armos` in a Python 3.12 venv
**Then** the package installs without errors and `armos --version` prints the version

**Given** armOS is installed on RPi 5 with an SO-101 arm connected via USB
**When** I run `armos detect`
**Then** the CH340 adapter and all 6 servos are detected, identical to x86 behavior

**Given** the armOS test suite
**When** I run `pytest` on the RPi 5 CI runner
**Then** all tests pass with no `aarch64`-specific failures

---

### Story R2: HailoBackend Inference Plugin

**Size:** L (8 story points)
**Sprint:** Can begin once architecture.md Section 7 InferenceBackend ABC is implemented
**Depends on:** R1 (armOS runs on RPi 5)

As a **robotics researcher**,
I want armOS to run vision models (YOLO, pose estimation) on the Hailo AI HAT accelerator,
so that my RPi 5 can do real-time object detection for manipulation tasks instead of CPU-only at 2-5 FPS.

**Tasks:**
1. Implement `HailoBackend(InferenceBackend)` using HailoRT Python API (>= 4.20).
2. Implement `armos model compile --backend hailo` wrapping the Hailo DFC Docker container.
3. Add backend auto-detection: if `/dev/hailo0` exists and `hailo_platform` is importable, prefer `HailoBackend` over `PyTorchBackend`.
4. Convert Octo-Small ONNX model to HEF and validate output matches PyTorch reference within tolerance (atol=1e-3).
5. Add fallback: if Hailo device is present but model is not compiled to HEF, print actionable error with compile command.
6. Benchmark: measure and log inference latency per predict() call. Expose via telemetry stream.

**Acceptance Criteria:**

**Given** a RPi 5 with AI HAT+ (Hailo-8L) and HailoRT installed
**When** I run `armos model compile --backend hailo --input octo_small.onnx --output octo_small.hef`
**Then** the HEF file is generated and the command prints the model input/output tensor shapes

**Given** a compiled HEF model and a running SO-101 arm
**When** I run `armos teleop --policy octo_small.hef --backend hailo`
**Then** inference runs on the Hailo accelerator at >= 20 Hz and servo commands are sent at the profile's control frequency

**Given** a RPi 5 without an AI HAT installed
**When** I run `armos teleop --policy octo_small.onnx`
**Then** armOS falls back to PyTorchBackend (or OpenVINOBackend if available) and logs a warning suggesting the AI HAT for better performance

**Given** the HailoBackend predict() method
**When** I compare its output to PyTorchBackend on the same input
**Then** the outputs match within atol=1e-3 for all output tensors

---

### Story R3: RPi 5 Robot Profile and Hardware Detection

**Size:** S (3 story points)
**Sprint:** Parallel with R1
**Depends on:** Epic 3 (profile system) complete

As a **first-time RPi 5 user**,
I want armOS to detect that I am running on a Raspberry Pi 5 and auto-select the correct profile,
so that I do not have to manually configure device paths and platform quirks.

**Tasks:**
1. Add platform detection: read `/proc/device-tree/model` for "Raspberry Pi 5" string.
2. Create `rpi5-so101.yaml` profile with RPi 5-specific defaults:
   - Serial port patterns: `/dev/ttyUSB*` (CH340) and `/dev/ttyAMA*` (GPIO UART).
   - Camera: prefer `/dev/video0` (USB) or detect CSI camera via `libcamera-hello --list-cameras`.
   - Hailo: detect `/dev/hailo0` and set `inference_backend: hailo` if present, else `pytorch`.
   - Thermal: set conservative servo frequency if CPU temp > 80C (RPi 5 throttles at 85C).
3. Add `armos detect --platform` command that prints detected platform and available accelerators.
4. Auto-suggest profile on first run based on detected platform.

**Acceptance Criteria:**

**Given** armOS is running on a Raspberry Pi 5
**When** I run `armos detect --platform`
**Then** the output includes "Platform: Raspberry Pi 5", RAM amount, and "AI Accelerator: Hailo-8L" (or "none")

**Given** a RPi 5 with an SO-101 arm connected and no existing profile selected
**When** I run `armos` for the first time (first-run wizard)
**Then** the wizard suggests the `rpi5-so101` profile and applies it on confirmation

**Given** the `rpi5-so101` profile is active and a Pi Camera Module 3 Wide is connected via CSI
**When** I run `armos detect`
**Then** the CSI camera is listed as "imx708_wide" with "CSI" interface type, preferred over any USB cameras

**Given** a Pi Camera Module 3 Wide connected via CSI
**When** armOS captures frames for data collection
**Then** frames are captured via `picamera2` (not OpenCV), autofocus is locked to the configured `lens_position`, and capture latency is under 50ms per frame

---

### Story R4: RPi 5 SD Card Image Build Pipeline

**Size:** L (8 story points)
**Sprint:** After R1-R3 validated on real hardware (stretch goal)
**Depends on:** R1, R3

As a **classroom instructor**,
I want to download a pre-built SD card image with armOS pre-installed,
so that I can flash 30 RPi 5 boards for my students without running pip install on each one.

**Tasks:**
1. Create a `pi-gen` stage that installs armOS into a Python 3.12 venv, HailoRT, udev rules, and the `rpi5-so101` profile.
2. Configure auto-login to a non-root user with armOS first-run wizard on login.
3. Pre-download Octo-Small HEF model so the image is fully offline-capable.
4. Add GitHub Actions workflow to build the `.img.xz` file on every tagged release.
5. Host image on HuggingFace Hub (same as x86 ISO distribution).
6. Image size target: under 4GB compressed (fits on 16GB SD card with room for datasets).

**Acceptance Criteria:**

**Given** a fresh RPi 5 with no SD card
**When** I flash the armOS image to a 16GB microSD and boot
**Then** the system boots to a login prompt within 60 seconds and the first-run wizard launches on login

**Given** the armOS SD card image is booted with an SO-101 arm connected
**When** I complete the first-run wizard
**Then** I can run teleoperation within 2 minutes of first boot, with no internet connection required

**Given** a new armOS release is tagged on GitHub
**When** the CI pipeline runs
**Then** a new `.img.xz` file is built, tested in QEMU (basic boot check), and uploaded to HuggingFace Hub

---

### Story R5: LeKiwi Mobile Base Profile

**Size:** M (5 story points)
**Sprint:** After R1 validates SO-101 on RPi 5
**Depends on:** R1, R3

As a **LeKiwi builder**,
I want an armOS profile for the LeKiwi mobile base,
so that I can control both the arm and the omnidirectional drive from a single armOS instance.

**Tasks:**
1. Create `lekiwi.yaml` profile extending `rpi5-so101` with 3 additional STS3215 servos (IDs 7, 8, 9) for the Kiwi drive wheels.
2. Add a `drive` servo group type (distinct from `arm` group) in the profile schema.
3. Implement Kiwi drive kinematics: translate (vx, vy, omega) velocity commands into per-wheel speeds for 3 omniwheels at 120-degree spacing.
4. Add `armos teleop --mode mobile` that accepts keyboard velocity commands (WASD + QE for rotation) and drives the base while the arm is controlled by a leader arm or policy.
5. Integrate with LeRobot's LeKiwi configuration so `lerobot` commands work with the armOS-managed hardware.

**Acceptance Criteria:**

**Given** a LeKiwi robot with RPi 5 and armOS installed
**When** I run `armos detect`
**Then** all 9 servos are detected: 6 arm servos (IDs 1-6) and 3 drive servos (IDs 7-9)

**Given** the `lekiwi` profile is active
**When** I run `armos teleop --mode mobile` and press the W key
**Then** all 3 drive wheels spin at equal speed producing forward translation, and the arm remains stationary

**Given** a LeKiwi with the `lekiwi` profile
**When** I run `armos exercise --group drive`
**Then** the base executes a square pattern (forward, strafe right, backward, strafe left) at low speed and reports drive servo health

---

## 6. Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Hailo DFC confirmed unable to compile transformer policies (ACT, Octo).** Research validated this — Hailo model zoo has zero robotics models. | **Confirmed** | High | **MITIGATED:** R2 scope revised to vision models only (YOLO, pose). Policy inference stays CPU or cloud. This is now a design decision, not a risk. |
| 2 | **HailoRT Python API instability.** HailoRT is evolving rapidly; API breaking changes between minor versions. | Medium | Medium | Pin HailoRT version in requirements. Test against specific HailoRT release (4.20.0). Wrap all Hailo calls in the HailoBackend class so API changes are contained. |
| 3 | **RPi 5 thermal throttling under sustained inference.** The BCM2712 throttles at 85C. Hailo HAT adds heat. | Medium | Low | Require active cooler in hardware requirements. Monitor CPU temp in telemetry. Reduce inference frequency if temp > 80C (graceful degradation, not crash). |
| 4 | **USB bandwidth contention.** RPi 5 has limited USB 3.0 bandwidth shared across all ports. Running USB camera + CH340 serial simultaneously may cause dropped frames or serial errors. | Low | Medium | Recommend CSI camera (bypasses USB bus entirely) in the RPi 5 profile. If USB camera is used, test at 640x480@15fps (low bandwidth) before recommending higher resolutions. |
| 5 | **LeRobot 0.5.0 has ARM-specific bugs.** LeRobot CI runs on x86. Untested on aarch64. | Medium | Medium | Run LeRobot import + basic inference test on RPi 5 in R1. If LeRobot has ARM issues, file upstream PRs. armOS's `lerobot_patches.py` module (already exists for sync_read retry fixes) can carry temporary patches. |
| 6 | **Pi-gen image build is slow and fragile.** Custom RPi OS images are notoriously finicky to build in CI. | High | Low (R4 is stretch) | Defer R4 until R1-R3 prove the pip-install path works. If pi-gen proves too fragile, use the simpler approach: publish a shell script that installs armOS on a stock RPi OS image. |
| 7 | **Hailo-8L supply constraints.** Raspberry Pi AI HAT+ has had intermittent stock issues. | Low | Low | Support both Hailo-8L and Hailo-8 variants. HailoRT abstracts the difference. Also support CPU-only fallback (armOS works without AI HAT, just slower). |

---

## 7. Sprint Plan Integration

### Can this run in parallel with x86 MVP?

**Yes, partially.** Here is the dependency analysis:

```
x86 MVP Sprints:           0  1  2  3  4  5  6  7  8  (launch)
                           |  |  |  |  |  |  |  |  |
Epic 1 (package)           [=====]
Epic 2 (HAL/servo)            [========]
Epic 3 (profiles)                 [========]
Epic 5 (telemetry)                   [=====]
Epic 7 (AI integration)                   [========]
                                              |
                                              v
RPi 5 Stories:             .  .  .  .  .  R1 R3 R2 R4  (parallel track)
                                          |  |  |  |
                           R1: pip ARM ---|  |  |  |
                           R3: profile ------|  |  |
                           R2: Hailo -----------|  |
                           R4: SD image -----------|
                           R5: LeKiwi ------ (after R1+R3)
```

**Stories R1 and R3 can start in Sprint 5** (after Epics 1-3 deliver the package structure, HAL, and profile system). They are low-risk and validate the platform.

**Story R2 (Hailo) should start in Sprint 6-7** after the InferenceBackend ABC from Epic 7 is implemented. It is the critical path for the AI HAT value proposition.

**Story R4 (SD image) is Sprint 8+** and should only begin after R1-R3 prove the stack works on real hardware. This is explicitly a stretch goal.

**Story R5 (LeKiwi) can start as soon as R1 and R3 are done** -- it does not depend on Hailo. A LeKiwi user gets value from teleoperation and data collection even without AI inference.

### What blocks what

| Story | Blocked by (x86 MVP) | Blocked by (RPi epic) |
|-------|----------------------|----------------------|
| R1 | Epic 1 (package), Epic 2 (HAL) | -- |
| R2 | Epic 7 (AI integration) | R1 |
| R3 | Epic 3 (profiles) | -- |
| R4 | -- | R1, R3 |
| R5 | -- | R1, R3 |

### Resource requirement

One developer can execute R1, R3, and R5 with a physical RPi 5 + SO-101 on their desk. R2 additionally requires an AI HAT+ ($70-110). R4 requires CI infrastructure for image builds.

**Recommended approach:** Assign RPi 5 stories to a single developer as a parallel track starting Sprint 5. This developer needs the physical hardware. The x86 MVP team is not blocked or slowed -- the RPi work consumes no x86 sprint capacity.

### Story Point Summary

| Story | Size | Points | Priority |
|-------|------|--------|----------|
| R1: pip on ARM | M | 5 | P0 |
| R2: HailoBackend | L | 8 | P0 |
| R3: RPi 5 profile | S | 3 | P0 |
| R4: SD card image | L | 8 | P2 (stretch) |
| R5: LeKiwi profile | M | 5 | P1 |
| **Total** | | **29** | |

---

## Appendix A: Hailo Model Conversion Reference

### One-time setup (x86 dev machine)

```bash
# Pull the Hailo DFC Docker image (x86 only)
docker pull hailo_ai/hailo_dataflow_compiler:4.20.0

# Convert ONNX to HEF
docker run --rm -v $(pwd):/models hailo_ai/hailo_dataflow_compiler:4.20.0 \
  hailo compiler --onnx /models/octo_small.onnx \
  --output /models/octo_small.hef \
  --hw-arch hailo8l
```

### On RPi 5 (runtime only)

```bash
# Install HailoRT (runtime, not compiler)
sudo apt install hailort-driver hailort-pcie-driver
pip install hailort==4.20.0

# Verify
python -c "from hailo_platform import HailoRTClient; print('Hailo OK')"
```

## Appendix B: RPi 5 Profile YAML Sketch

```yaml
# profiles/rpi5-so101.yaml
name: rpi5-so101
description: SO-101 arm on Raspberry Pi 5
platform:
  board: raspberry-pi-5
  min_ram_gb: 4
  recommended_ram_gb: 8

hardware:
  servo_controller:
    protocol: feetech_sts
    port_patterns:
      - /dev/ttyUSB*
      - /dev/ttyAMA*
    baudrate: 1000000
    servo_ids: [1, 2, 3, 4, 5, 6]

  cameras:
    - type: csi
      backend: picamera2  # libcamera Python bindings
      model: imx708_wide  # Pi Camera Module 3 Wide
      resolution: [640, 480]
      fps: 30
      autofocus: manual    # Lock focus for consistent manipulation frames
      lens_position: 4.0   # ~25cm working distance (tune per mount)
      priority: primary    # Prefer CSI over USB (4x lower latency)
    - type: usb
      path: /dev/video*
      resolution: [640, 480]
      fps: 30
      priority: fallback

  accelerator:
    type: hailo
    device: /dev/hailo0
    required: false  # works without AI HAT, just slower

inference:
  backend: auto  # hailo if available, else pytorch
  default_model: octo_small
  models:
    octo_small:
      onnx: models/octo_small.onnx
      hef: models/octo_small.hef
      frequency_hz: 30

servo_protection:
  max_temperature_c: 65
  max_current_ma: 1200
  stall_threshold_ms: 500

thermal:
  cpu_throttle_temp_c: 80
  reduce_inference_hz_above: 75
```
