# Hardware Self-Survey — Implementation Plan

## 1. Overview

Add a `survey.py` module that probes the local machine and returns a structured `HardwareMap`. Both `surface_citizen.py` and `pi_citizen.py` (and the brain-only fallback inside `run_pi.py`) call it at construction time, **before** `super().__init__()` runs, to populate `capabilities`. The full structured map is stashed on the citizen instance and piggybacks on `HEARTBEAT` bodies under a new `hw` key. `run_pi.py` re-runs the survey on each hotplug tick and diffs against last-seen state to drive citizen spawn/teardown. The protocol stays version-1 — additions are purely additive optional keys.

## 2. File-Level Changes (Dependency Order)

| # | File | Change |
|---|------|--------|
| 1 | **`citizenry/survey.py`** *(new)* | New module. Defines dataclasses `Camera`, `Accelerator`, `ServoBus`, `Compute`, `Audio`, `HardwareMap` plus async `survey_hardware(prior: HardwareMap \| None = None) -> HardwareMap` and pure `project_capabilities(hw: HardwareMap) -> list[str]`. Per-category detector helpers prefixed `_probe_*`. No new deps beyond stdlib + optional `psutil`. |
| 2 | **`citizenry/citizen.py`** (lines 81–91, 256–296) | (a) `__init__` gains optional `hardware: HardwareMap \| None = None` param; if provided, stored on `self.hardware`. If `capabilities` arg is empty/None and `hardware` is provided, auto-derive via `project_capabilities`. (b) `_send_heartbeat` (line 256) appends `body["hw"] = self.hardware.to_compact_dict()` when present. (c) `_handle_heartbeat` (line 411) parses `env.body.get("hw")` into `n.hardware` (new field on `Neighbor`). |
| 3 | **`citizenry/citizen.py`** `Neighbor` dataclass (~line 56) | Add `hardware: dict \| None = None` field — kept as raw dict on neighbor side to avoid coupling. |
| 4 | **`citizenry/pi_citizen.py`** (lines 35–45) | `__init__` accepts optional `hardware: HardwareMap \| None`. If not given, calls `survey.survey_hardware()` once at boot. Pass merged `capabilities` list = base manipulator caps **unioned with** projected caps to `super().__init__`. Stash full map on `self.hardware`. |
| 5 | **`citizenry/surface_citizen.py`** (lines 42–52) | Same treatment: survey at init, union projection with `["compute","govern","teleop_source"]`, stash full map. |
| 6 | **`citizenry/camera_citizen.py`** (~line 33) | Pass projected camera capabilities through too — primarily so the new richer camera detector (CSI vs USB, resolutions) surfaces in heartbeat. |
| 7 | **`citizenry/run_pi.py`** | Major refactor — see §6. Replace `_find_servo_ports` and `_find_cameras` with calls into `survey`. Brain-only path (~line 83) gets full survey too so even an arms-less Pi advertises `hailo_inference`, `csi_camera`, etc. |
| 8 | **`citizenry/run_surface.py`** | Optional: log the survey result on startup for visibility. |
| 9 | **`citizenry/protocol.py`** | **No code change required.** The envelope is `body: dict`, so the new `hw` key is automatically forward/backward compatible. Add a docstring near `MessageType.HEARTBEAT` documenting the optional `hw` field. |
| 10 | **`citizenry/dashboard.py`, `web_dashboard.py`** | (Defer.) Read `n.hardware` to render the rich panel. Out of scope for first slice. |

## 3. New `survey.py` API

```python
@dataclass
class Camera:
    kind: Literal["csi","usb","integrated"]
    model: str | None         # "imx708", "Logitech C920", ...
    path: str                 # /dev/video0  OR  "csi:0" for libcamera-only
    driver: Literal["v4l2","libcamera","opencv"]
    resolutions: list[tuple[int,int,float]]  # (w,h,fps), best-effort

@dataclass
class Accelerator:
    kind: Literal["hailo8l","hailo8","nvidia","coral_usb","coral_pcie"]
    model: str | None
    device: str | None        # /dev/hailo0
    tops: float | None

@dataclass
class ServoBus:
    vendor: Literal["feetech","dynamixel","unknown"]
    port: str                 # /dev/ttyACM0
    usb_vid: str
    usb_pid: str
    controller_id: str | None # serial number from sysfs

@dataclass
class Compute:
    cpu_model: str
    cpu_cores: int
    arch: str                 # "x86_64", "aarch64"
    ram_gb: float
    gpu: str | None           # "Intel Iris Plus", None

@dataclass
class Audio:
    inputs: list[str]
    outputs: list[str]

@dataclass
class HardwareMap:
    cameras: list[Camera]
    accelerators: list[Accelerator]
    servo_buses: list[ServoBus]
    compute: Compute
    audio: Audio | None
    surveyed_at: float

    def to_compact_dict(self) -> dict: ...   # for heartbeat
    def to_full_dict(self) -> dict: ...      # for ADVERTISE / dashboard
    def diff(self, other: "HardwareMap") -> HardwareDelta: ...

async def survey_hardware(prior: HardwareMap | None = None) -> HardwareMap
def project_capabilities(hw: HardwareMap) -> list[str]
```

`survey_hardware` runs detectors in parallel via `asyncio.to_thread` since most are blocking syscalls. `prior` lets cheap detectors skip if nothing changed (caching for the hotplug loop).

## 4. Detection Strategy Per Category

**Cameras (the load-bearing fix).** Three-stage probe, in order:

1. **libcamera/picamera2** — `Picamera2.global_camera_info()` returns `[{Id, Model, Location, Rotation, Num}]` for IMX708 etc. This catches the Pi 5 CSI camera that `run_pi.py:196–218` misses entirely. Fallback to shelling `libcamera-hello --list-cameras --json` if picamera2 isn't installed (pi-only). **First win.**
2. **V4L2 sysfs walk** — `Path("/sys/class/video4linux").iterdir()`, read `/name` and `/device/uevent` for each. Far more reliable than `cv2.VideoCapture`; the existing `num > 3` filter (run_pi.py:202) is exactly the bug.
3. **OpenCV probe** — only as a last-resort liveness check, and only on devices V4L2 says are capture-capable. Drop the hard `num > 3` cap.

For CSI cameras, set `path = "csi:<Num>"` and `driver = "libcamera"`. For USB, prefer `/dev/video<lowest-with-capture-cap>` and read `vendor`/`product` from sysfs.

**Accelerators.**
- *Hailo (first win — Pi has one today):* `Path("/dev/hailo0").exists()` then `hailortcli scan` parsed for chip type. Sysfs path: `/sys/class/hailo_chardev/hailo0/board_name`. Don't import `hailo_platform` — keep it shell-only so the dep stays optional.
- *NVIDIA:* shell `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader` if binary exists.
- *Google Coral:* USB VID `1a6e`/`18d1` for USB Accelerator; PCIe via `/sys/bus/pci/devices/*/device` (Edge TPU PCIe is `089a`).
- *Apple/Intel NPUs:* defer.

**Servo buses.** Extend the existing `_find_servo_ports` (run_pi.py:172–193). Add Robotis U2D2 (`0x0403:0x6014`), Waveshare bus servo adapters, and a generic CDC-ACM fallback that matches by USB *product string* containing "feetech", "dynamixel", or "servo". Pull `serial` attribute from sysfs into `controller_id` so the dashboard can disambiguate two identical adapters.

**Compute.** Pure stdlib: parse `/proc/cpuinfo` for `model name`, `/proc/meminfo` for `MemTotal`, `platform.machine()` for arch. GPU detection optional (`lspci | grep -i vga`, or skip on Pi). `psutil` is OK if you want CPU count without parsing.

**Audio.** `arecord -l` and `aplay -l` (or parse `/proc/asound/cards`). Defer to slice 2 — citizens don't act on audio yet.

## 5. Capability Projection Rule

Single source of truth at the top of `survey.py`:

```python
CSI_CAMERA       = "csi_camera"
USB_CAMERA       = "usb_camera"
CAMERA           = "camera"             # umbrella
HAILO_INFERENCE  = "hailo_inference"
NVIDIA_INFERENCE = "nvidia_inference"
CORAL_INFERENCE  = "coral_inference"
SERVO_FEETECH    = "feetech_sts3215"   # already used — keep
SERVO_DYNAMIXEL  = "dynamixel"
SERVO_BUS        = "servo_bus"          # umbrella
ARM_6DOF         = "6dof_arm"           # set only if 6 servos enumerate
GRIPPER          = "gripper"            # set only if a 7th servo enumerates
COMPUTE          = "compute"
GOVERN           = "govern"
TELEOP_SOURCE    = "teleop_source"
MICROPHONE       = "microphone"
SPEAKER          = "speaker"
```

Projection rule (deterministic, idempotent):
- Any `Camera` → emit `"camera"` plus `"csi_camera"` or `"usb_camera"` per-instance.
- Any `Accelerator` of kind `hailo*` → `"hailo_inference"`. NVIDIA → `"nvidia_inference"`. Coral → `"coral_inference"`.
- Any `ServoBus` → `"servo_bus"` plus vendor-specific (`"feetech_sts3215"`, `"dynamixel"`).
- 6-DOF arm enumeration is **not** done by `survey.py` — `pi_citizen.py` decides once it actually opens the bus. `"6dof_arm"`/`"gripper"` stay on `PiCitizen.__init__`'s static list. Final caps = `set(static_caps) | set(project_capabilities(hw))`.
- Compute is always emitted as `"compute"`.

This keeps existing `"6dof_arm" in neighbor.capabilities` checks at `surface_citizen.py:144,173` working unchanged.

## 6. Heartbeat Protocol Change

Smallest possible additive change. Add **one optional key** to body:

```python
"hw": {
  "v": 1,                                        # schema version
  "cam":  [["csi","imx708","csi:0"], ...],       # [kind, model, path]
  "acc":  [["hailo8l","/dev/hailo0",13]],        # [kind, device, tops]
  "srv":  [["feetech","/dev/ttyACM0"]],          # [vendor, port]
  "cpu":  ["Cortex-A76", 4, "aarch64", 8.0],     # [model, cores, arch, ram_gb]
  "aud":  [1,1]                                  # [n_in, n_out]; omit if none
}
```

Compact tuples (not nested objects) keep heartbeat under MTU even with several cameras. Old citizens that don't know `hw` will simply ignore it — `_handle_heartbeat` reads body keys with `.get(...)`, no schema enforcement. `Neighbor.hardware` defaults to `None`. **No `PROTOCOL_VERSION` bump needed.**

Send the **full** `to_full_dict()` (with resolutions, controller IDs, audio device names) on `ADVERTISE` only — heartbeat carries the compact form every 2s.

## 7. Hotplug Integration

Current `_hotplug_loop` (run_pi.py:106–169) tracks two sets and diffs strings. Replace with:

1. Cache `last_hw: HardwareMap` after the initial survey.
2. Each tick (3s): `current = await survey_hardware(prior=last_hw)`.
3. Compute `delta = current.diff(last_hw)` returning `{added: [...], removed: [...]}` per category.
4. For each `delta.added` servo bus → spawn `PiCitizen(follower_port=bus.port, hardware=current)`. For each removed → stop the citizen keyed by that port. Same for cameras.
5. **Always** call `_announce_hardware_change()` on the brain citizen if any delta exists — this triggers an immediate ADVERTISE so the governor doesn't have to wait for the next heartbeat.
6. Update `last_hw = current`.

Cap detector wall-time at ~500ms with `asyncio.wait_for` per probe so a hung `hailortcli` can't stall hotplug.

When the brain-only Pi detects a delta, it should not respawn itself — only update its own `self.hardware` and `self.capabilities` and force an ADVERTISE. `self._send_advertise()` already exists at citizen.py:233.

## 8. Open Questions

1. **picamera2 install footprint.** Pulls `libcamera` python bindings. Acceptable, or shell out to `libcamera-hello` and parse JSON? *Recommendation:* shell first, picamera2 only if shelling fails — keeps deploy.sh untouched.
2. **Capability mutability.** Once survey can change caps at runtime, do we want a debounce (require a delta to persist for 2 ticks) to avoid flapping on USB renumeration?
3. **Test framework.** `citizenry/tests/` exists — is there a runner configured? Picking pytest would let survey detectors be tested with sysfs fixtures.
4. **mDNS TXT record bloat.** Caps joined with `,` in `mdns.py:78`. With richer projection we may exceed practical TXT limits if many caps stack. Truncate, or move full caps off mDNS and rely on ADVERTISE entirely?
5. **Should the brain citizen rename itself?** Hardcoded `"pi-brain"`. With Hailo present, maybe `"pi-inference"` reads better in the dashboard.
6. **Camera resolutions list — ship or defer?** V4L2 modes are cheap; libcamera modes require opening the camera. Defer libcamera resolutions to slice 2.

## 9. Implementation Order

**Slice 1 — unblock the CSI camera bug (smallest valuable PR):**
- `survey.py` skeleton with only `_probe_cameras` (libcamera-shell + V4L2 sysfs) and `Compute`.
- `project_capabilities` covering camera + compute only.
- Wire into `run_pi.py` brain-only path so it advertises `csi_camera` today.
- No protocol/heartbeat change yet — caps go through the existing flat list.

**Slice 2 — accelerators & servo extensions:**
- `_probe_accelerators` (Hailo first, NVIDIA, Coral).
- `_probe_servo_buses` superset of current `_find_servo_ports`.
- `PiCitizen` and `SurfaceCitizen` start calling survey.

**Slice 3 — heartbeat enrichment:**
- Add compact `hw` key to heartbeat body.
- Add `Neighbor.hardware` field.
- ADVERTISE carries full dict.

**Slice 4 — hotplug integration:**
- Replace `_hotplug_loop` set-diffing with `HardwareMap.diff()`.
- Mid-life ADVERTISE on delta.
- Brain citizen self-mutates capabilities on delta.

**Slice 5 (defer):** audio, dashboard rendering, mDNS TXT strategy, runtime cap-change debounce.
