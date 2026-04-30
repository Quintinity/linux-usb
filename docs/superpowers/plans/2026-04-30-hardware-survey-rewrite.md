# Hardware Survey Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace today's `citizenry/survey.py` — fragile sysfs grep + `rpicam-hello` subprocess + `tegra-camrtc-capture-vi` driver-string heuristic — with detection backed by **authoritative sources**: pyudev for USB introspection, libcamera Python bindings for Pi cameras, jetson_multimedia_api / `nvgstcapture-1.0 -A` JSON for Tegra CSI, `lspci` + `/dev/hailo*` for Hailo accelerators, and zeroconf for XIAO/network cameras advertising `_armos-citizen._udp.local.` Preserve the existing `HardwareMap` shape and capability strings so `claude-persona-refresh.sh`, `run_pi.py`, `run_jetson.py`, and `surface_citizen.py` remain green.

**Architecture:** The survey rewrite is fully behind the existing `survey_hardware()` async entry point — same name, same return type (`HardwareMap`), same dataclass field shapes (`Camera`, `Accelerator`, `ServoBus`, `Compute`). What changes is **how** the probes work internally:

- `_probe_cameras_libcamera()` now imports `libcamera` (with a `picamera2.Picamera2.global_camera_info()` fallback) and reads sensor model + path from `Camera.properties`, replacing the `rpicam-hello --list-cameras` text-parse.
- `_probe_cameras_tegra()` shells out to `nvgstcapture-1.0 --prev-res=12 --print-properties` (which emits a structured key-value listing) **or**, when present, imports `jetson_multimedia_api` (NVIDIA's libargus python wrapper). Falls back to a sysfs-but-clean enumeration that only reads `/sys/class/video4linux/*/device/uevent` for the `tegra-camrtc-capture-vi` driver — the IMX219/IMX477/OV5640 string-match list from commit d478479 is removed.
- `_probe_cameras_v4l2_usb()` is replaced by a pyudev-based enumerator (`pyudev.Context().list_devices(subsystem='video4linux')`) that filters on `ID_USB_DRIVER == 'uvcvideo'` and returns vendor/product strings from the udev `ATTR{name}`/`ID_MODEL` properties — no more `/sys` walks.
- `_probe_servo_buses()` is rewritten over pyudev (`subsystem='tty'`) using `ID_VENDOR_ID` / `ID_MODEL_ID` properties, replacing the `(usb / "..").resolve()` parent-walk hack.
- `_probe_accelerators_hailo()` keeps its `/dev/hailo*` glob (this is the authoritative source) and gains an `lspci -d 1e60:` cross-check (Hailo PCI vendor 0x1e60); kind/TOPS still come from `hailortcli fw-control identify`.
- `_probe_accelerators_nvidia()` keeps its `nvidia-smi` shell-out (canonical for discrete GPUs); on Jetson it additionally reads `/etc/nv_tegra_release` to identify the SoC family.
- `_probe_accelerators_coral()` is rewritten over pyudev for USB and `pyudev` `subsystem='pci'` for M.2/PCIe — replaces the manual `/sys/bus/usb/devices` and `/sys/bus/pci/devices` walks.
- A **new** `_probe_network_cameras_mdns()` uses zeroconf (already a citizenry dependency) to browse `_armos-citizen._udp.local.` for ~1.5 s and surfaces any neighbor whose `caps` TXT record contains `video_stream` or `frame_capture` (the XIAO's advertised caps) as a `Camera(kind="wifi", ...)`. Results are surfaced under a new `WIFI_CAMERA` capability string.
- All probes remain best-effort: a missing library or absent device returns `[]` rather than raising.

The `project_capabilities()` and `merge_capabilities()` projection helpers stay byte-identical for existing capability strings; one new line adds `WIFI_CAMERA` when any `Camera.kind == "wifi"` is present.

**Tech Stack:** Python 3.12, **pyudev** (new dep — system bindings to libudev; pure-Python wrapper, ships in Ubuntu and Raspberry Pi OS), **zeroconf** (already a dep, used by `citizenry/mdns.py`). libcamera Python bindings are an optional import (`try: import libcamera; except ImportError: pass`) — only present on the Pi. `jetson_multimedia_api` is optional likewise — only present on Jetson. `pytest`, `unittest.mock` for tests.

**References:**
- Architecture spec: `docs/superpowers/specs/2026-04-30-citizenry-physical-ai-architecture-design.md` §5.2 (smell #3 — survey only finds USB cameras), §10 sub-3 (Hardware survey rewrite).
- Existing code under modification: `citizenry/survey.py` (entire file), `citizenry/tests/test_survey.py` (existing tests — preserve every behavior).
- Consumers that must stay green: `scripts/claude-persona-refresh.sh:104-141` (calls `survey_hardware()`, reads `cpu_model` / `ram_gb` / `cameras` / `accelerators` / `servo_buses`), `citizenry/run_pi.py:24,126,177-212` (uses `survey_hardware`, `project_capabilities`, `HardwareMap.diff`), `citizenry/run_jetson.py:25-29` (uses `survey_hardware`).
- Existing mDNS service type lives at `citizenry/mdns.py:23` — `_armos-citizen._udp.local.` (this is the **only** service type to browse; the spec's `_citizenry-agent._udp` / `_xiao-cam._tcp` strings are aspirational and don't exist on the wire). XIAO advertises caps `video_stream,frame_capture` — see `xiao-citizen/xiao-citizen.ino:283`.

**Out of scope:** Adding new capability strings (`AAS_DEVICE`, etc.) for hardware that has no consumer in the codebase yet. Replacing the existing `_handle_govern` hot-reload of survey state on hotplug — that path stays as-is. AAS submodel emission (Sub-9 territory). Any change to `claude-persona-refresh.sh` itself.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `citizenry/survey.py` | **rewrite** | Same public surface (`survey_hardware`, `HardwareMap`, `project_capabilities`, `merge_capabilities`, all dataclasses, all capability constants). Internals replaced per §Architecture above. Add `WIFI_CAMERA` constant. |
| `citizenry/tests/test_survey.py` | preserve | Existing 30 tests — they test parsers and projections, both of which survive. Untouched. |
| `citizenry/tests/test_survey_v2.py` | **create** | New tests for the rewritten probes: pyudev USB mock, libcamera mock, jetson Tegra mock, Hailo lspci mock, mDNS browse mock, integration test on this Surface (real probes — should detect 2× ttyACM Feetech, no cameras, no accelerators). |
| `requirements.txt` (or `pyproject.toml` deps) | modify | Add `pyudev>=0.24` to citizenry runtime deps. |
| `citizenry/tests/fixtures/nvgstcapture_sample.txt` | **create** | Real `nvgstcapture-1.0 --print-properties` output captured from a Jetson (committed for offline test reproducibility). |
| `citizenry/tests/fixtures/lspci_hailo_sample.txt` | **create** | Real `lspci -d 1e60: -vvv` output for a Hailo-8L. |

6 files (1 rewrite, 1 new test, 1 deps file modify, 2 new fixtures, 1 existing test preserved unchanged). The rewrite of `survey.py` is mostly internal replacement — the public surface stays binary-stable.

---

## Conventions

- **Test paths:** all under `citizenry/tests/`. Use `pytest`.
- **Run tests:** `cd ~/linux-usb && source ~/lerobot-env/bin/activate && pytest citizenry/tests/<test>.py -v`.
- **Commits:** small, one task per commit, message format `citizenry(survey): <task summary>`. Always `git add` explicit paths — never `git add -A` (the working tree may have unrelated in-progress changes).
- **Mocking strategy:** for libcamera/Tegra/Hailo/mDNS, use `unittest.mock.patch` on the module-level probe functions — `_probe_cameras_libcamera`, `_probe_cameras_tegra`, etc. — so tests run identically on Surface (no Pi/Jetson hardware) and on the target device. The probe functions themselves only get exercised live in the **integration test** that runs on whatever machine `pytest` happens to be on, asserting only the floor of what's known to be present (e.g. on Surface: at least one `Compute` object, zero CSI cameras, zero Hailo).
- **Backward compat check:** every test in `citizenry/tests/test_survey.py` must remain green after the rewrite. The new file `test_survey_v2.py` adds coverage; it does not replace the old one.
- **Authoritative-source rule:** if a probe's primary source fails (libcamera not importable, `nvgstcapture-1.0` not on PATH), fall back to the next-most-authoritative source, then to `[]`. Never raise from a probe.

---

## Task 1: Add pyudev dependency and prove it works

**Files:**
- Modify: `requirements.txt` (citizenry runtime deps; check actual location with `find ~/linux-usb -maxdepth 2 -name 'requirements*.txt' -o -name 'pyproject.toml'`).
- Test: `citizenry/tests/test_survey_v2.py` (create — first test only).

- [ ] **Step 1: Locate the citizenry deps file**

```bash
find ~/linux-usb -maxdepth 2 \( -name 'requirements*.txt' -o -name 'pyproject.toml' -o -name 'setup.py' \) -print
```

Pick the file that lists `zeroconf`, `pynacl`, `aiohttp` etc. as deps — that's the one to extend. (If the project uses `pyproject.toml` only, edit `[project.dependencies]`. If it uses `requirements.txt`, append a line.)

- [ ] **Step 2: Write a failing test that imports pyudev and uses it**

Create `citizenry/tests/test_survey_v2.py` with this single test for now:

```python
"""Hardware survey v2 — authoritative sources (pyudev / libcamera / jetson / mDNS)."""
from __future__ import annotations


def test_pyudev_is_importable():
    """pyudev is the authoritative kernel-uevent introspection library;
    it must be a hard dependency of the citizenry runtime."""
    import pyudev  # noqa: F401
    ctx = pyudev.Context()
    # Smoke: enumerating any subsystem must not raise.
    list(ctx.list_devices(subsystem="tty"))
```

- [ ] **Step 3: Run, confirm fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey_v2.py::test_pyudev_is_importable -v
```

Expected: `ModuleNotFoundError: No module named 'pyudev'`.

- [ ] **Step 4: Add pyudev to deps and install**

Edit the deps file (e.g. `requirements.txt`) to add:

```
pyudev>=0.24
```

Then:

```bash
source ~/lerobot-env/bin/activate && pip install 'pyudev>=0.24'
```

- [ ] **Step 5: Run test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey_v2.py::test_pyudev_is_importable -v
```

Expected: 1 PASS.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add requirements.txt citizenry/tests/test_survey_v2.py \
  && git commit -m "$(cat <<'EOF'
citizenry(survey): add pyudev dependency

- pyudev>=0.24 is the authoritative kernel-uevent introspection library
- replaces fragile /sys walks in the upcoming survey rewrite
- one smoke test in test_survey_v2.py confirms importability + basic enum

Spec: docs/superpowers/specs/2026-04-30-citizenry-physical-ai-architecture-design.md §5.2 smell #3, §10 sub-3

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Rewrite USB camera + servo bus probes over pyudev

**Files:**
- Modify: `citizenry/survey.py` (replace `_probe_cameras_v4l2` and `_probe_servo_buses`).
- Test: `citizenry/tests/test_survey_v2.py` (extend).

- [ ] **Step 1: Write failing tests for pyudev-backed USB and servo probes**

Append to `citizenry/tests/test_survey_v2.py`:

```python
from unittest.mock import MagicMock, patch

from citizenry.survey import (
    Camera, ServoBus,
    _probe_cameras_v4l2_usb, _probe_servo_buses,
)


class _FakeUdevDevice:
    """Just enough of a pyudev.Device to satisfy the probes under test."""
    def __init__(self, device_node: str, properties: dict, attributes: dict | None = None):
        self.device_node = device_node
        self._properties = properties
        self._attributes = attributes or {}

    @property
    def properties(self):
        return self._properties

    def get(self, key, default=None):
        return self._properties.get(key, default)

    @property
    def attributes(self):
        # pyudev exposes attributes via a mapping-like object; tests just need .get(key)
        m = MagicMock()
        m.get.side_effect = lambda k, default=None: self._attributes.get(k, default)
        return m


def _fake_context_with(devices_by_subsystem: dict[str, list[_FakeUdevDevice]]):
    ctx = MagicMock()
    ctx.list_devices.side_effect = lambda subsystem: devices_by_subsystem.get(subsystem, [])
    return ctx


def test_probe_cameras_v4l2_usb_uses_pyudev_uvcvideo_filter():
    """USB cameras come from pyudev video4linux subsystem with ID_USB_DRIVER==uvcvideo."""
    fake_uvc = _FakeUdevDevice(
        device_node="/dev/video2",
        properties={
            "ID_USB_DRIVER": "uvcvideo",
            "ID_VENDOR": "Logitech",
            "ID_MODEL": "HD_Pro_Webcam_C920",
            "ID_V4L_PRODUCT": "HD Pro Webcam C920",
        },
    )
    fake_csi = _FakeUdevDevice(
        device_node="/dev/video0",
        properties={"ID_V4L_PRODUCT": "rp1-cfe"},  # no ID_USB_DRIVER → skipped
    )
    fake_codec = _FakeUdevDevice(
        device_node="/dev/video10",
        properties={"ID_V4L_PRODUCT": "bcm2835-codec-decode"},  # no ID_USB_DRIVER → skipped
    )
    ctx = _fake_context_with({"video4linux": [fake_uvc, fake_csi, fake_codec]})
    with patch("citizenry.survey.pyudev.Context", return_value=ctx):
        cams = _probe_cameras_v4l2_usb()
    assert cams == [Camera(
        kind="usb", model="HD Pro Webcam C920",
        path="/dev/video2", driver="v4l2",
    )]


def test_probe_cameras_v4l2_usb_no_devices_returns_empty():
    ctx = _fake_context_with({"video4linux": []})
    with patch("citizenry.survey.pyudev.Context", return_value=ctx):
        assert _probe_cameras_v4l2_usb() == []


def test_probe_servo_buses_uses_pyudev_tty_with_vid_pid():
    """Servo buses come from pyudev tty subsystem with USB ID_VENDOR_ID/ID_MODEL_ID."""
    feetech = _FakeUdevDevice(
        device_node="/dev/ttyACM0",
        properties={
            "ID_VENDOR_ID": "1a86", "ID_MODEL_ID": "7523",
            "ID_VENDOR": "QinHeng_Electronics", "ID_MODEL": "CH340_serial_converter",
            "ID_SERIAL_SHORT": "ABC123",
        },
    )
    dynamixel = _FakeUdevDevice(
        device_node="/dev/ttyUSB0",
        properties={
            "ID_VENDOR_ID": "0403", "ID_MODEL_ID": "6014",
            "ID_VENDOR": "FTDI", "ID_MODEL": "FT232H",
            "ID_SERIAL_SHORT": "FTABC",
        },
    )
    bluetooth = _FakeUdevDevice(
        device_node="/dev/ttyS0",
        properties={},  # no USB → skipped
    )
    ctx = _fake_context_with({"tty": [feetech, dynamixel, bluetooth]})
    with patch("citizenry.survey.pyudev.Context", return_value=ctx):
        buses = _probe_servo_buses()
    assert ServoBus(vendor="feetech", port="/dev/ttyACM0",
                    usb_vid="1a86", usb_pid="7523", controller_id="ABC123") in buses
    assert ServoBus(vendor="dynamixel", port="/dev/ttyUSB0",
                    usb_vid="0403", usb_pid="6014", controller_id="FTABC") in buses
    assert len(buses) == 2  # bluetooth excluded


def test_probe_servo_buses_unknown_vid_falls_back_to_product_string():
    """Unknown VID + product string containing 'Feetech' → vendor=feetech."""
    odd = _FakeUdevDevice(
        device_node="/dev/ttyACM1",
        properties={
            "ID_VENDOR_ID": "ffff", "ID_MODEL_ID": "0000",
            "ID_VENDOR": "Some_OEM", "ID_MODEL": "Feetech_Servo_Bus",
            "ID_SERIAL_SHORT": "X",
        },
    )
    ctx = _fake_context_with({"tty": [odd]})
    with patch("citizenry.survey.pyudev.Context", return_value=ctx):
        buses = _probe_servo_buses()
    assert len(buses) == 1
    assert buses[0].vendor == "feetech"
```

- [ ] **Step 2: Run, confirm fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey_v2.py -v
```

Expected: ImportError on `_probe_cameras_v4l2_usb` (the function doesn't exist yet — current code has `_probe_cameras_v4l2`).

- [ ] **Step 3: Rewrite the two probes in `citizenry/survey.py`**

In `citizenry/survey.py`:

a. Add to top of file:

```python
import pyudev
```

b. Replace `_probe_cameras_v4l2` (current lines ~235-255) with:

```python
def _probe_cameras_v4l2_usb() -> list[Camera]:
    """USB cameras via pyudev. Filters on ID_USB_DRIVER==uvcvideo so CSI capture
    nodes (rp1-cfe, tegra-camrtc-capture-vi) and codec nodes (bcm2835-codec-decode)
    are excluded. Authoritative replacement for the prior /sys walk."""
    cameras: list[Camera] = []
    try:
        ctx = pyudev.Context()
    except Exception:
        return cameras
    for dev in ctx.list_devices(subsystem="video4linux"):
        if dev.get("ID_USB_DRIVER") != "uvcvideo":
            continue
        model = (
            dev.get("ID_V4L_PRODUCT")
            or dev.get("ID_MODEL")
            or "unknown"
        ).replace("_", " ")
        cameras.append(Camera(
            kind="usb",
            model=model,
            path=dev.device_node or "",
            driver="v4l2",
        ))
    # Stable order — sort by path
    cameras.sort(key=lambda c: c.path)
    return cameras
```

c. Replace `_probe_servo_buses` (current lines ~375-416) with:

```python
def _probe_servo_buses() -> list[ServoBus]:
    """Servo controllers via pyudev tty subsystem. VID/PID drive vendor identification;
    falls back to the ID_MODEL/ID_VENDOR product string if VID is unknown."""
    buses: list[ServoBus] = []
    try:
        ctx = pyudev.Context()
    except Exception:
        return buses
    for dev in ctx.list_devices(subsystem="tty"):
        vid = dev.get("ID_VENDOR_ID")
        pid = dev.get("ID_MODEL_ID")
        if not vid or not pid:
            continue  # not a USB-attached tty
        vendor = _KNOWN_SERVO_VID.get(vid)
        if not vendor:
            product = (dev.get("ID_MODEL", "") + " " + dev.get("ID_VENDOR", "")).lower()
            if "feetech" in product:
                vendor = "feetech"
            elif "dynamixel" in product:
                vendor = "dynamixel"
            elif "servo" in product:
                vendor = "unknown"
            else:
                continue
        buses.append(ServoBus(
            vendor=vendor,
            port=dev.device_node or "",
            usb_vid=vid,
            usb_pid=pid,
            controller_id=dev.get("ID_SERIAL_SHORT"),
        ))
    buses.sort(key=lambda b: b.port)
    return buses
```

d. In `survey_hardware()`, update the gather call so it now uses `_probe_cameras_v4l2_usb` (renamed). (Keep the existing CSI probes; those are rewritten in Tasks 3-4.)

- [ ] **Step 4: Run all survey tests, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey.py citizenry/tests/test_survey_v2.py -v
```

Expected: existing 30 tests in `test_survey.py` still pass (they exercise parsers + projections, untouched). New tests in `test_survey_v2.py` pass.

- [ ] **Step 5: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/survey.py citizenry/tests/test_survey_v2.py \
  && git commit -m "$(cat <<'EOF'
citizenry(survey): rewrite USB camera + servo bus probes over pyudev

- _probe_cameras_v4l2_usb uses pyudev video4linux + ID_USB_DRIVER==uvcvideo
- _probe_servo_buses uses pyudev tty + ID_VENDOR_ID/ID_MODEL_ID
- existing /sys/class walks removed (authoritative kernel-uevent path)
- 4 new tests with pyudev.Context patched to a fake enumerator
- existing test_survey.py 30 tests remain green

Spec: §5.2 smell #3 (fragile sysfs grep)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Replace libcamera CSI probe with libcamera Python bindings

**Files:**
- Modify: `citizenry/survey.py` (`_probe_cameras_libcamera`).
- Test: `citizenry/tests/test_survey_v2.py` (extend).

- [ ] **Step 1: Write the failing test**

Append to `citizenry/tests/test_survey_v2.py`:

```python
def test_probe_cameras_libcamera_uses_python_bindings():
    """Pi cameras come from libcamera.Camera.list() (or Picamera2 fallback) — not
    from a subprocess text-parse of `rpicam-hello --list-cameras`."""
    fake_cam = MagicMock()
    fake_cam.id = "/base/axi/pcie@1000120000/rp1/i2c@80000/imx708@1a"
    fake_cam.properties = {"Model": "imx708_wide_noir"}
    fake_cm = MagicMock()
    fake_cm.cameras = [fake_cam]

    fake_libcamera = MagicMock()
    fake_libcamera.CameraManager.return_value = fake_cm

    with patch.dict("sys.modules", {"libcamera": fake_libcamera}):
        # Re-import via the patched module
        from citizenry.survey import _probe_cameras_libcamera
        cams = _probe_cameras_libcamera()
    assert len(cams) == 1
    assert cams[0].kind == "csi"
    assert cams[0].model == "imx708_wide_noir"
    assert cams[0].driver == "libcamera"
    # path should reference the libcamera id (or an index derived from it)
    assert "imx708" in cams[0].path or cams[0].path.startswith("csi:")


def test_probe_cameras_libcamera_no_module_returns_empty():
    """When libcamera Python bindings aren't installed (Surface/Jetson), return []."""
    with patch.dict("sys.modules", {"libcamera": None}):
        from citizenry.survey import _probe_cameras_libcamera
        # Force ImportError by removing the cached module
        import sys as _sys
        _sys.modules.pop("libcamera", None)
        # Force the import inside _probe_cameras_libcamera to fail
        with patch("citizenry.survey._import_libcamera", side_effect=ImportError):
            assert _probe_cameras_libcamera() == []
```

- [ ] **Step 2: Run, confirm fails**

Expected: tests reference `_import_libcamera` which doesn't exist yet, and the existing `_probe_cameras_libcamera` still subprocesses out to `rpicam-hello`.

- [ ] **Step 3: Rewrite the libcamera probe**

In `citizenry/survey.py`, replace `_probe_cameras_libcamera` (current lines ~174-186) and the now-unused `_parse_libcamera_list` with:

```python
def _import_libcamera():
    """Indirection seam so tests can patch the import without touching sys.modules.

    Returns the imported `libcamera` module, or raises ImportError. Picamera2 is
    a thicker wrapper but `libcamera.CameraManager` is the canonical low-level
    enumerator and is what we want here.
    """
    import libcamera  # noqa
    return libcamera


def _probe_cameras_libcamera() -> list[Camera]:
    """CSI cameras via libcamera Python bindings.

    Authoritative replacement for the prior `rpicam-hello --list-cameras` text-parse
    (which depended on a CLI binary being installed and on its output format being
    stable). libcamera.CameraManager.cameras is the same source rpicam-hello uses.
    """
    cameras: list[Camera] = []
    try:
        libcamera = _import_libcamera()
    except ImportError:
        return cameras
    try:
        cm = libcamera.CameraManager()
        # libcamera 0.x exposes `.cameras`; some bindings call it via .cameras() — handle both.
        cam_list = cm.cameras() if callable(getattr(cm, "cameras", None)) else getattr(cm, "cameras", [])
    except Exception:
        return cameras
    for idx, cam in enumerate(cam_list):
        try:
            props = dict(cam.properties)
        except Exception:
            props = {}
        model = (
            props.get("Model")
            or props.get(getattr(__import__("libcamera").properties, "Model", None), None)
            or "unknown"
        )
        # libcamera id is a long device path; surface it under a `csi:N` short path
        # for backward compatibility, and stash the long id in `model` if otherwise blank.
        cam_id = getattr(cam, "id", "") or ""
        path = f"csi:{idx}" if cam_id else f"csi:{idx}"
        # Prefer the short sensor name in the model field; if model is unknown,
        # use the trailing component of the libcamera id (e.g. "imx708@1a").
        if model == "unknown" and "@" in cam_id:
            model = cam_id.rsplit("/", 1)[-1].split("@", 1)[0]
        cameras.append(Camera(
            kind="csi",
            model=str(model),
            path=path,
            driver="libcamera",
        ))
    return cameras
```

Note: keep `_parse_libcamera_list` exported for now — `test_survey.py` exercises it directly. We can leave the old function as dead code that the existing tests still call (the function is pure; deleting it would break `test_parse_libcamera_real_pi5_output`). Mark it deprecated in a docstring; remove in a follow-up.

- [ ] **Step 4: Run, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey.py citizenry/tests/test_survey_v2.py -v
```

Expected: existing 30 + new tests all pass.

- [ ] **Step 5: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/survey.py citizenry/tests/test_survey_v2.py \
  && git commit -m "$(cat <<'EOF'
citizenry(survey): use libcamera Python bindings for Pi CSI cameras

- _probe_cameras_libcamera now imports libcamera.CameraManager directly
- replaces the prior `rpicam-hello --list-cameras` subprocess text-parse
- _import_libcamera seam for test patchability
- absent module → returns [] (Surface/Jetson stay clean)
- 2 new tests (mocked libcamera + missing module path)
- old _parse_libcamera_list kept temporarily so legacy tests stay green

Spec: §5.2 smell #3 (libcamera invisible)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Replace Tegra CSI probe with nvgstcapture / jetson_multimedia_api

**Files:**
- Modify: `citizenry/survey.py` (`_probe_cameras_tegra`).
- Test: `citizenry/tests/test_survey_v2.py` (extend).
- Create: `citizenry/tests/fixtures/nvgstcapture_sample.txt`.

- [ ] **Step 1: Capture a real nvgstcapture sample (or use the canonical one below)**

`nvgstcapture-1.0 --print-properties` on a Jetson with an IMX219 attached emits something like:

```
Available Cameras:
  Camera #0: imx219 (CSI sensor at i2c-9-0010)
    Resolutions: 3280x2464 @ 21fps, 1920x1080 @ 60fps, 1280x720 @ 120fps
    Sensor mode count: 4
  Camera #1: imx477 (CSI sensor at i2c-10-001a)
    Resolutions: 4032x3040 @ 30fps
    Sensor mode count: 2
```

Save this canonical sample (verbatim) to `citizenry/tests/fixtures/nvgstcapture_sample.txt`. (When the Jetson is next online, replace with a captured-from-hardware file; the parser must not regress.)

- [ ] **Step 2: Write failing tests**

Append to `citizenry/tests/test_survey_v2.py`:

```python
from pathlib import Path as _Path

FIXTURES = _Path(__file__).parent / "fixtures"


def test_parse_nvgstcapture_output_two_sensors():
    from citizenry.survey import _parse_nvgstcapture_properties
    sample = (FIXTURES / "nvgstcapture_sample.txt").read_text()
    cams = _parse_nvgstcapture_properties(sample)
    assert len(cams) == 2
    assert cams[0].kind == "csi"
    assert cams[0].model == "imx219"
    assert cams[0].driver == "tegra"
    assert cams[0].path == "/dev/video0"  # Camera #0 → /dev/video0
    assert cams[1].model == "imx477"
    assert cams[1].path == "/dev/video1"


def test_parse_nvgstcapture_output_no_cameras():
    from citizenry.survey import _parse_nvgstcapture_properties
    assert _parse_nvgstcapture_properties("Available Cameras:\n  (none)\n") == []
    assert _parse_nvgstcapture_properties("") == []


def test_probe_cameras_tegra_via_nvgstcapture():
    """When nvgstcapture-1.0 is on PATH, we use its --print-properties output.
    No more IMX219/IMX477/OV5640 string-match in /sys."""
    sample = (FIXTURES / "nvgstcapture_sample.txt").read_text()
    with patch("citizenry.survey.shutil.which", return_value="/usr/bin/nvgstcapture-1.0"):
        with patch("citizenry.survey.subprocess.run") as run:
            run.return_value = MagicMock(stdout=sample, returncode=0)
            from citizenry.survey import _probe_cameras_tegra
            cams = _probe_cameras_tegra()
    assert len(cams) == 2
    assert {c.model for c in cams} == {"imx219", "imx477"}


def test_probe_cameras_tegra_falls_back_when_no_binary():
    """If nvgstcapture-1.0 is absent, return [] (Surface should hit this path)."""
    with patch("citizenry.survey.shutil.which", return_value=None):
        from citizenry.survey import _probe_cameras_tegra
        assert _probe_cameras_tegra() == []
```

- [ ] **Step 3: Run, confirm fails**

Expected: `_parse_nvgstcapture_properties` does not exist; `_probe_cameras_tegra` is the old sysfs-grep version.

- [ ] **Step 4: Replace the Tegra probe**

In `citizenry/survey.py`, replace `_probe_cameras_tegra` (current lines ~204-232) and **remove** the IMX219/IMX477/OV5640 string-match heuristic. Replace with:

```python
def _parse_nvgstcapture_properties(stdout: str) -> list[Camera]:
    """Parse `nvgstcapture-1.0 --print-properties` output.

    Lines we care about look like:
        Camera #0: imx219 (CSI sensor at i2c-9-0010)
        Camera #1: imx477 (CSI sensor at i2c-10-001a)

    The numeric index after `Camera #` maps directly to /dev/videoN.
    """
    cameras: list[Camera] = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line.startswith("Camera #"):
            continue
        try:
            # "Camera #0: imx219 (CSI sensor at ...)"
            head, rest = line.split(":", 1)
            idx_str = head.split("#", 1)[1].strip()
            idx = int(idx_str)
            sensor = rest.strip().split(" ", 1)[0].strip()
        except (ValueError, IndexError):
            continue
        if not sensor:
            continue
        cameras.append(Camera(
            kind="csi",
            model=sensor,
            path=f"/dev/video{idx}",
            driver="tegra",
        ))
    return cameras


def _probe_cameras_tegra() -> list[Camera]:
    """Jetson CSI cameras via `nvgstcapture-1.0 --print-properties`.

    Authoritative replacement for the prior /sys/class/video4linux DRIVER=tegra
    grep + IMX219/IMX477/OV5640 string-match heuristic from commit d478479.

    Future: when `jetson_multimedia_api` Python bindings ship for our JP6.2 base,
    swap the subprocess for `import jetson_multimedia_api as jma; jma.list_cameras()`.
    Intentionally not introduced now to avoid an extra apt dep on Jetson.
    """
    binary = shutil.which("nvgstcapture-1.0")
    if not binary:
        return []
    try:
        result = subprocess.run(
            [binary, "--print-properties"],
            capture_output=True, text=True, timeout=8,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    return _parse_nvgstcapture_properties(result.stdout)
```

- [ ] **Step 5: Run, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey.py citizenry/tests/test_survey_v2.py -v
```

Note: `test_parse_tegra_v4l2_name_*` tests in `test_survey.py` will start failing because `_parse_tegra_v4l2_name` is now dead code. **Either** keep the function (annotate it `# legacy — Tegra CSI now goes through nvgstcapture; kept for now in case of fallback`) so the existing tests pass, **or** delete the function and the three tests. Recommend keeping the function for one release cycle.

Expected: all tests pass, including the 3 legacy `_parse_tegra_v4l2_name` tests.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/survey.py \
             citizenry/tests/test_survey_v2.py \
             citizenry/tests/fixtures/nvgstcapture_sample.txt \
  && git commit -m "$(cat <<'EOF'
citizenry(survey): replace Tegra CSI sysfs heuristic with nvgstcapture parser

- _probe_cameras_tegra now shells `nvgstcapture-1.0 --print-properties`
- _parse_nvgstcapture_properties handles the structured output cleanly
- removes the IMX219/IMX477/OV5640 string-match hack from commit d478479
- legacy _parse_tegra_v4l2_name kept for one release; existing tests stay green
- 4 new tests (parser + probe via mocked subprocess + missing-binary path)
- canonical fixture committed under tests/fixtures/nvgstcapture_sample.txt

Spec: §5.2 smell #3 (fragile sysfs grep for Tegra)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Harden Hailo + Coral probes; add lspci cross-check

**Files:**
- Modify: `citizenry/survey.py` (`_probe_accelerators_hailo`, `_probe_accelerators_coral`).
- Test: `citizenry/tests/test_survey_v2.py` (extend).
- Create: `citizenry/tests/fixtures/lspci_hailo_sample.txt`.

- [ ] **Step 1: Capture an `lspci -d 1e60: -vvv` sample**

Real output for a Pi 5 + AI HAT+ (Hailo-8L on PCIe) looks like:

```
0000:01:00.0 Co-processor: Hailo Technologies Ltd Hailo-8 AI Processor (rev 01)
	Subsystem: Hailo Technologies Ltd Hailo-8L
	Control: I/O- Mem+ BusMaster+ SpecCycle- MemWINV- VGASnoop- ParErr- Stepping- SERR- FastB2B- DisINTx-
	Status: Cap+ 66MHz- UDF- FastB2B- ParErr- DevSel=fast >TAbort- <TAbort- <MAbort- >SERR- <PERR- DevSel=fast
```

Commit the canonical (non-empty) sample to `citizenry/tests/fixtures/lspci_hailo_sample.txt`.

- [ ] **Step 2: Write failing tests**

Append to `citizenry/tests/test_survey_v2.py`:

```python
def test_probe_accelerators_hailo_uses_dev_glob_first():
    """/dev/hailo* is authoritative; lspci is a cross-check, not the source of truth."""
    with patch("citizenry.survey.Path") as MockPath:
        # Glob returns one device
        glob_result = [_FakePath("/dev/hailo0")]
        MockPath.return_value.glob.return_value = glob_result
        with patch("citizenry.survey.shutil.which", return_value=None):
            from citizenry.survey import _probe_accelerators_hailo
            accels = _probe_accelerators_hailo()
    # Default to hailo8 / tops=None when hailortcli isn't on PATH
    assert len(accels) == 1
    assert accels[0].kind in ("hailo8", "hailo8l")
    assert accels[0].device == "/dev/hailo0"


def test_probe_accelerators_hailo_lspci_cross_check_logs_mismatch(caplog):
    """If /dev/hailo* exists but lspci -d 1e60: shows nothing, log a warning
    (helps diagnose missing kernel module). Probe still returns the device."""
    sample = (FIXTURES / "lspci_hailo_sample.txt").read_text()
    # In this scenario, /dev/hailo0 is present AND lspci confirms it — no warning.
    with patch("citizenry.survey._dev_hailo_devices", return_value=["/dev/hailo0"]):
        with patch("citizenry.survey._lspci_hailo_lines", return_value=sample.splitlines()):
            from citizenry.survey import _probe_accelerators_hailo
            accels = _probe_accelerators_hailo()
    assert len(accels) == 1
    # No warning since /dev and lspci agree.
    assert "hailo mismatch" not in caplog.text.lower()


def test_probe_accelerators_coral_via_pyudev():
    """Coral USB Accelerator (1a6e:089a or 18d1:9302) detected via pyudev."""
    coral_pre = _FakeUdevDevice(
        device_node=None,
        properties={
            "ID_VENDOR_ID": "1a6e", "ID_MODEL_ID": "089a",
            "ID_MODEL": "Apex_Class_Edge_TPU",
        },
    )
    other_usb = _FakeUdevDevice(
        device_node=None,
        properties={"ID_VENDOR_ID": "1a86", "ID_MODEL_ID": "7523"},  # Feetech CH340
    )
    ctx = _fake_context_with({"usb": [coral_pre, other_usb]})
    with patch("citizenry.survey.pyudev.Context", return_value=ctx):
        from citizenry.survey import _probe_accelerators_coral
        accels = _probe_accelerators_coral()
    assert len(accels) == 1
    assert accels[0].kind == "coral_usb"
    assert accels[0].tops == 4.0
```

(`_FakePath` is a tiny helper — define it at the top of the test file alongside `_FakeUdevDevice`. It only needs `__str__` returning the path.)

- [ ] **Step 3: Run, confirm fails**

Expected: helpers `_dev_hailo_devices` and `_lspci_hailo_lines` don't exist yet; `_probe_accelerators_coral` still walks `/sys`.

- [ ] **Step 4: Implement the helpers and refactor the two probes**

In `citizenry/survey.py`:

a. Add helpers (above `_probe_accelerators_hailo`):

```python
def _dev_hailo_devices() -> list[str]:
    """Return paths to all /dev/hailo* devices (authoritative for kernel-loaded HW)."""
    return sorted(str(p) for p in Path("/dev").glob("hailo*"))


def _lspci_hailo_lines() -> list[str]:
    """Return lspci -d 1e60: output split into lines, or [] if lspci isn't on PATH.
    Hailo PCI vendor ID is 0x1e60."""
    binary = shutil.which("lspci")
    if not binary:
        return []
    try:
        result = subprocess.run(
            [binary, "-d", "1e60:"],
            capture_output=True, text=True, timeout=3,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    return result.stdout.splitlines()
```

b. Replace `_probe_accelerators_hailo` to use the helpers and emit a warning when `/dev` and `lspci` disagree:

```python
import logging
log = logging.getLogger(__name__)

def _probe_accelerators_hailo() -> list[Accelerator]:
    """Hailo NPUs via /dev/hailo* (authoritative). Cross-checked against
    `lspci -d 1e60:` (Hailo PCI vendor) for diagnostic warnings only."""
    devices = _dev_hailo_devices()
    pci_lines = _lspci_hailo_lines()
    if devices and not pci_lines:
        log.warning(
            "hailo mismatch: /dev/hailo* present (%s) but lspci -d 1e60: empty. "
            "Kernel module may be loaded against a missing card, or /dev/hailo* "
            "is a stale device node.", devices,
        )
    if not devices:
        return []
    # Determine kind/tops via hailortcli when possible (existing path).
    binary = shutil.which("hailortcli")
    chip, tops = "hailo8", None
    if binary:
        try:
            result = subprocess.run(
                [binary, "fw-control", "identify"],
                capture_output=True, text=True, timeout=5,
            )
            chip, tops = _parse_hailortcli_arch(result.stdout)
        except (subprocess.TimeoutExpired, OSError):
            pass
    return [Accelerator(kind=chip, model=chip, device=d, tops=tops) for d in devices]
```

c. Replace `_probe_accelerators_coral` to use pyudev:

```python
_CORAL_USB_VID_PID = {("1a6e", "089a"), ("18d1", "9302")}
_CORAL_PCI_VENDOR = "0x1ac1"  # Global Unichip → Coral M.2 / PCIe
_CORAL_PCI_DEVICE = "0x089a"


def _probe_accelerators_coral() -> list[Accelerator]:
    """Google Coral Edge TPU via pyudev — USB and PCIe forms."""
    accels: list[Accelerator] = []
    try:
        ctx = pyudev.Context()
    except Exception:
        return accels
    for dev in ctx.list_devices(subsystem="usb"):
        vid = dev.get("ID_VENDOR_ID")
        pid = dev.get("ID_MODEL_ID")
        if (vid, pid) in _CORAL_USB_VID_PID:
            accels.append(Accelerator(
                kind="coral_usb", model="Coral USB Accelerator",
                device=None, tops=4.0,
            ))
    for dev in ctx.list_devices(subsystem="pci"):
        # pyudev surfaces PCI vendor/device under PCI_ID="VEND:DEV"
        pci_id = dev.get("PCI_ID", "")
        if pci_id.upper() == "1AC1:089A":
            accels.append(Accelerator(
                kind="coral_pcie", model="Coral M.2/PCIe Accelerator",
                device=None, tops=4.0,
            ))
    return accels
```

- [ ] **Step 5: Run, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey.py citizenry/tests/test_survey_v2.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/survey.py \
             citizenry/tests/test_survey_v2.py \
             citizenry/tests/fixtures/lspci_hailo_sample.txt \
  && git commit -m "$(cat <<'EOF'
citizenry(survey): harden accelerator probes (Hailo lspci cross-check, Coral via pyudev)

- _probe_accelerators_hailo: /dev/hailo* authoritative, lspci -d 1e60: cross-check
  with WARNING log on mismatch (helps diagnose missing kernel module)
- _probe_accelerators_coral: pyudev for both USB (1a6e:089a / 18d1:9302) and
  PCIe (1ac1:089a) — replaces /sys/bus walks
- new helpers _dev_hailo_devices, _lspci_hailo_lines for testability
- 3 new tests (Hailo /dev source, Hailo no-mismatch path, Coral USB via pyudev)
- canonical lspci_hailo_sample.txt fixture for offline test reproducibility

Spec: §5.2 smell #3 (lspci + /dev/hailo* for Hailo)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Add mDNS network-camera probe and WIFI_CAMERA capability

**Files:**
- Modify: `citizenry/survey.py` (add `_probe_network_cameras_mdns`, `WIFI_CAMERA` constant, hook into `survey_hardware()` and `project_capabilities()`).
- Test: `citizenry/tests/test_survey_v2.py` (extend).

- [ ] **Step 1: Confirm there's no existing WIFI_CAMERA constant in the codebase**

```bash
grep -rn "WIFI_CAMERA\|wifi_camera" /home/bradley/linux-usb/citizenry/ 2>/dev/null | grep -v "\.pyc\|__pycache__"
```

Expected: no hits in production code (the `run_wifi_camera.py` module name is unrelated to a capability string). Adding `WIFI_CAMERA` is therefore additive, not a rename.

- [ ] **Step 2: Update `Camera` dataclass to allow `kind="wifi"` and write failing tests**

In `citizenry/survey.py`, change the `Camera` dataclass `kind` Literal:

```python
@dataclass
class Camera:
    kind: Literal["csi", "usb", "wifi"]
    model: str | None
    path: str
    driver: Literal["libcamera", "v4l2", "tegra", "mdns"]
```

Append to `citizenry/tests/test_survey_v2.py`:

```python
def test_probe_network_cameras_mdns_finds_xiao():
    """XIAO advertises caps containing 'video_stream' or 'frame_capture' on the
    `_armos-citizen._udp.local.` mDNS service type."""
    fake_info = MagicMock()
    fake_info.properties = {
        b"type": b"sensor",
        b"caps": b"video_stream,frame_capture",
        b"pubkey": b"abc123",
        b"version": b"1",
    }
    fake_info.server = "xiao-cam-001.local."
    fake_info.port = 81

    fake_zc = MagicMock()
    # AsyncServiceBrowser browses; for the test we pretend it finished and
    # returned one entry whose ServiceInfo we resolve synchronously.
    with patch("citizenry.survey._mdns_browse_armos_citizen",
               return_value=[fake_info]):
        from citizenry.survey import _probe_network_cameras_mdns
        cams = _probe_network_cameras_mdns(timeout=0.1)
    assert len(cams) == 1
    assert cams[0].kind == "wifi"
    assert cams[0].driver == "mdns"
    assert "xiao-cam-001" in cams[0].path or "xiao-cam-001" in (cams[0].model or "")


def test_probe_network_cameras_mdns_skips_non_camera_neighbors():
    """An armos-citizen advertising caps='compute,govern' is NOT a camera."""
    fake_info = MagicMock()
    fake_info.properties = {b"caps": b"compute,govern", b"type": b"governor"}
    fake_info.server = "surface-lerobot-001.local."
    fake_info.port = 7771
    with patch("citizenry.survey._mdns_browse_armos_citizen",
               return_value=[fake_info]):
        from citizenry.survey import _probe_network_cameras_mdns
        assert _probe_network_cameras_mdns(timeout=0.1) == []


def test_project_capabilities_wifi_camera():
    from citizenry.survey import (
        Camera, Compute, HardwareMap, project_capabilities,
        CAMERA, WIFI_CAMERA, USB_CAMERA, CSI_CAMERA,
    )
    hw = HardwareMap(
        cameras=[Camera(kind="wifi", model="xiao-cam-001", path="mdns:xiao-cam-001.local.:81", driver="mdns")],
        compute=Compute("x", 1, "x86_64", 8.0),
    )
    caps = project_capabilities(hw)
    assert CAMERA in caps and WIFI_CAMERA in caps
    assert USB_CAMERA not in caps and CSI_CAMERA not in caps
```

- [ ] **Step 3: Run, confirm fails**

Expected: `_probe_network_cameras_mdns`, `_mdns_browse_armos_citizen`, and `WIFI_CAMERA` don't exist.

- [ ] **Step 4: Implement the mDNS probe + capability projection**

In `citizenry/survey.py`:

a. Add the constant near the other capability strings:

```python
WIFI_CAMERA = "wifi_camera"
```

b. Add the browse helper (separate so tests can mock it):

```python
def _mdns_browse_armos_citizen(timeout: float = 1.5) -> list:
    """Browse `_armos-citizen._udp.local.` and return resolved ServiceInfo objects.

    Uses zeroconf's synchronous API for simplicity (this probe runs once at
    survey time, not in a hot loop). The async machinery in citizenry/mdns.py
    is for the long-running citizen-side advertisement, not for one-shot probes.
    """
    try:
        from zeroconf import Zeroconf, ServiceBrowser
    except ImportError:
        return []
    found: list = []
    zc = Zeroconf()
    try:
        class _Listener:
            def add_service(self, zc_, type_, name):
                info = zc_.get_service_info(type_, name, timeout=int(timeout * 1000))
                if info is not None:
                    found.append(info)
            def remove_service(self, *a, **kw): pass
            def update_service(self, *a, **kw): pass

        ServiceBrowser(zc, "_armos-citizen._udp.local.", _Listener())
        time.sleep(timeout)
    finally:
        zc.close()
    return found
```

c. Add the camera-extracting probe:

```python
def _probe_network_cameras_mdns(timeout: float = 1.5) -> list[Camera]:
    """Network cameras (XIAO ESP32-S3 et al.) advertising on mDNS.

    Filters armos-citizen neighbors whose `caps` TXT record contains
    `video_stream` or `frame_capture` (the XIAO's standard advertisement —
    see xiao-citizen/xiao-citizen.ino:283).
    """
    cameras: list[Camera] = []
    for info in _mdns_browse_armos_citizen(timeout=timeout):
        try:
            caps_raw = info.properties.get(b"caps", b"") or b""
            caps = caps_raw.decode("utf-8", errors="ignore")
        except Exception:
            continue
        if "video_stream" not in caps and "frame_capture" not in caps:
            continue
        host = (info.server or "").rstrip(".") or "unknown"
        port = info.port or 0
        # Use the host as the model — the XIAO's hostname is its identity
        # (e.g. xiao-cam-001) and is human-readable in the persona doc.
        cameras.append(Camera(
            kind="wifi",
            model=host.split(".local")[0],
            path=f"mdns:{host}:{port}",
            driver="mdns",
        ))
    return cameras
```

d. Extend `project_capabilities()` to surface `WIFI_CAMERA`:

```python
def project_capabilities(hw: HardwareMap) -> list[str]:
    caps: list[str] = [COMPUTE]
    if hw.cameras:
        caps.append(CAMERA)
        if any(c.kind == "csi" for c in hw.cameras):
            caps.append(CSI_CAMERA)
        if any(c.kind == "usb" for c in hw.cameras):
            caps.append(USB_CAMERA)
        if any(c.kind == "wifi" for c in hw.cameras):
            caps.append(WIFI_CAMERA)
    # ... rest unchanged
```

e. Wire the new probe into `survey_hardware()`'s `asyncio.gather`:

```python
async def survey_hardware() -> HardwareMap:
    csi_lib, csi_tegra, v4l2, mdns_cams, hailo, nvidia, coral, servos, compute = await asyncio.gather(
        asyncio.to_thread(_probe_cameras_libcamera),
        asyncio.to_thread(_probe_cameras_tegra),
        asyncio.to_thread(_probe_cameras_v4l2_usb),
        asyncio.to_thread(_probe_network_cameras_mdns, 1.5),
        asyncio.to_thread(_probe_accelerators_hailo),
        asyncio.to_thread(_probe_accelerators_nvidia),
        asyncio.to_thread(_probe_accelerators_coral),
        asyncio.to_thread(_probe_servo_buses),
        asyncio.to_thread(_probe_compute),
    )
    return HardwareMap(
        cameras=csi_lib + csi_tegra + v4l2 + mdns_cams,
        accelerators=hailo + nvidia + coral,
        servo_buses=servos,
        compute=compute,
    )
```

- [ ] **Step 5: Run, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey.py citizenry/tests/test_survey_v2.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/survey.py citizenry/tests/test_survey_v2.py \
  && git commit -m "$(cat <<'EOF'
citizenry(survey): mDNS probe for XIAO/network cameras + WIFI_CAMERA capability

- _probe_network_cameras_mdns browses _armos-citizen._udp.local. for ~1.5 s
- filters by `caps` TXT record containing video_stream or frame_capture
- adds Camera(kind="wifi", driver="mdns") to HardwareMap
- new WIFI_CAMERA capability string projected by project_capabilities
- _mdns_browse_armos_citizen separated for test mockability
- 3 new tests (XIAO match, non-camera neighbor skip, WIFI_CAMERA projection)

Spec: §5.2 smell #3 (mDNS for XIAO/network cameras)
Note: spec lists `_citizenry-agent._udp` / `_xiao-cam._tcp` aspirationally;
actual on-the-wire service type is `_armos-citizen._udp.local.` (citizenry/mdns.py:23,
xiao-citizen/xiao-citizen.ino:280-284).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Live integration test on this Surface + downstream consumer regression check

**Files:**
- Test: `citizenry/tests/test_survey_v2.py` (extend with one live integration test).

- [ ] **Step 1: Write the live integration test**

Append to `citizenry/tests/test_survey_v2.py`:

```python
import asyncio as _asyncio
import platform as _platform


def test_integration_surface_minimum_floor():
    """End-to-end survey on whatever machine this test runs on.

    Asserts only the universal floor (compute is non-None) plus host-specific
    invariants. On the Surface (i5-1035G4 + Type Cover, no SO-101 attached for CI):
      - 0 CSI cameras (no Pi camera bus on x86_64)
      - 0 Hailo accelerators (none physically attached)
      - When SO-101 controllers are plugged in, ≥1 Feetech servo bus on /dev/ttyACM*
    """
    from citizenry.survey import survey_hardware
    hw = _asyncio.run(survey_hardware())
    # Universal: compute is always populated.
    assert hw.compute is not None
    assert hw.compute.cpu_cores >= 1
    assert hw.compute.ram_gb > 0
    # Host-specific assertions on the Surface. (Skip on Pi/Jetson — those
    # have CSI / accelerators that this assertion would falsely reject.)
    if "surface" in _platform.node().lower() or _platform.machine() == "x86_64":
        assert all(c.kind != "csi" for c in hw.cameras), \
            "Surface has no CSI cameras; libcamera/Tegra probes returned a CSI cam"
        assert all(a.kind not in ("hailo8", "hailo8l") for a in hw.accelerators), \
            "Surface has no Hailo accelerator"
```

- [ ] **Step 2: Run the test on the Surface live**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey_v2.py::test_integration_surface_minimum_floor -v
```

Expected: PASS. If a Feetech SO-101 controller is plugged in, you can also visually inspect:

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate && python -c "
import asyncio
from citizenry.survey import survey_hardware, project_capabilities
hw = asyncio.run(survey_hardware())
print('cameras:    ', hw.cameras)
print('accels:     ', hw.accelerators)
print('servo buses:', hw.servo_buses)
print('caps:       ', project_capabilities(hw))
"
```

Expected on Surface with two SO-101 controllers attached: 2× `ServoBus(vendor='feetech', port='/dev/ttyACM0' or 1, ...)`, no cameras/accelerators, capability list includes `compute`, `servo_bus`, `feetech_sts3215`.

- [ ] **Step 3: Run the downstream consumer (persona-refresh) end-to-end**

```bash
bash ~/linux-usb/scripts/claude-persona-refresh.sh
```

Expected: clean run (no Python tracebacks); the `Hardware (live survey)` block in `~/.claude/projects/-home-bradley/memory/device_persona.md` shows `cpu`, `memory`, `cameras: none`, `accelerators: none`, `servo_buses: …`. Confirm nothing crashes.

- [ ] **Step 4: Run the full citizenry test suite to confirm no collateral regressions**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/ -x --ignore=citizenry/tests/integration -q
```

Expected: same baseline as before the rewrite (any pre-existing flaky/skipped tests remain in the same state). No new failures.

- [ ] **Step 5: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/tests/test_survey_v2.py \
  && git commit -m "$(cat <<'EOF'
citizenry(survey): live integration test on Surface + consumer regression check

- test_integration_surface_minimum_floor exercises survey_hardware() end-to-end
- asserts universal floor (compute non-None, cores≥1) plus x86_64 invariants
  (no CSI cams, no Hailo) — passes today on surface-lerobot-001
- claude-persona-refresh.sh manually verified to render the new survey output
  without Python tracebacks
- full citizenry/tests baseline confirmed clean

Spec: §10 sub-3 acceptance ("integration on this machine — Surface — should
detect 2× /dev/ttyACM*, no cameras, no accelerators")

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Cleanup — delete legacy parsers and refresh persona doc

**Files:**
- Modify: `citizenry/survey.py` (delete `_parse_libcamera_list`, `_parse_tegra_v4l2_name` and the `_probe_cameras_v4l2` alias if any).
- Modify: `citizenry/tests/test_survey.py` (delete the 4 tests that exercise the removed parsers).

- [ ] **Step 1: Confirm no other consumer imports the legacy parsers**

```bash
grep -rn "_parse_libcamera_list\|_parse_tegra_v4l2_name\|_probe_cameras_v4l2[^_]" \
  /home/bradley/linux-usb/citizenry/ 2>/dev/null \
  | grep -v "__pycache__\|\.pyc"
```

Expected: only `survey.py` (definitions), `test_survey.py` (legacy tests), and `test_survey_v2.py` (one reference in the Task 4 fallback comment). If anything else imports them, **abort cleanup** — file a follow-up ticket and skip this task.

- [ ] **Step 2: Delete the legacy parsers**

Remove from `citizenry/survey.py`:
- The `_parse_libcamera_list` function definition (5–8 lines).
- The `_parse_tegra_v4l2_name` function definition (8–10 lines).
- Any leftover `_probe_cameras_v4l2` (renamed to `_probe_cameras_v4l2_usb` in Task 2) alias.

Remove from `citizenry/tests/test_survey.py`:
- `test_parse_libcamera_real_pi5_output`
- `test_parse_libcamera_no_cameras`
- `test_parse_tegra_v4l2_name_imx219`
- `test_parse_tegra_v4l2_name_imx477`
- `test_parse_tegra_v4l2_name_no_sensor`

And the corresponding imports from `citizenry.survey` at the top of the file (`_parse_libcamera_list`, `_parse_tegra_v4l2_name`).

- [ ] **Step 3: Run all tests, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_survey.py citizenry/tests/test_survey_v2.py -v
```

Expected: 25 tests in `test_survey.py` (was 30, minus the 5 deleted) + the new tests in `test_survey_v2.py`. All pass.

- [ ] **Step 4: Re-run persona refresh and visually confirm hardware section is sane**

```bash
bash ~/linux-usb/scripts/claude-persona-refresh.sh
cat ~/.claude/projects/-home-bradley/memory/device_persona.md | sed -n '/Hardware (live survey)/,/Persona/p'
```

Expected: cpu, memory, cameras (`none` on Surface), accelerators (`none`), servo_buses correctly listed.

- [ ] **Step 5: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/survey.py citizenry/tests/test_survey.py \
  && git commit -m "$(cat <<'EOF'
citizenry(survey): delete legacy text-parser helpers replaced by authoritative probes

- _parse_libcamera_list (text-parse of rpicam-hello output) removed
- _parse_tegra_v4l2_name (sysfs-name regex from commit d478479) removed
- corresponding 5 legacy tests in test_survey.py removed
- no production consumers of these helpers remain

Sub-3 of citizenry-physical-ai-architecture-design is now feature-complete:
pyudev for USB introspection, libcamera Python bindings for Pi cameras,
nvgstcapture-1.0 for Tegra CSI, lspci+/dev/hailo* for Hailo, mDNS for
XIAO/network cameras. HardwareMap shape and capability strings preserved;
WIFI_CAMERA added.

Spec: §10 sub-3 (Hardware survey rewrite)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

Coverage of spec sections:

- **§5.2 smell #3** (survey only sees USB cameras / fragile sysfs grep / libcamera invisible) → Tasks 2 (USB via pyudev), 3 (libcamera Python bindings), 4 (Tegra via nvgstcapture).
- **§10 sub-3 scope items**:
  - "pyudev for USB device introspection" → Tasks 2, 5 (Coral USB).
  - "libcamera Python bindings for Pi camera detection" → Task 3.
  - "jetson_multimedia_api OR nvgstcapture-1.0 -A JSON output for Tegra CSI" → Task 4 (chose nvgstcapture per the OR; jetson_multimedia_api documented as future swap).
  - "lspci + /dev/hailo* detection for Hailo accelerators" → Task 5.
  - "mDNS to detect XIAO/network cameras" → Task 6.
  - "preserve the existing capability strings" → Task 6 (additive only — `WIFI_CAMERA` is new; everything else unchanged).
  - "add capability strings as needed (WIFI_CAMERA …)" → Task 6.
  - "new survey returns a HardwareMap with the same shape" → All tasks; the `Camera`/`Accelerator`/`ServoBus`/`Compute` dataclasses are unchanged structurally (only `kind` Literals on `Camera` extended with `wifi`).
  - "tests covering: USB mock, libcamera mock, Tegra mock, Hailo mock, mDNS mock, integration" → Tasks 2, 3, 4, 5, 6, 7 respectively.
- **§10 sub-3 acceptance** ("integration on this machine — Surface — should detect 2× /dev/ttyACM*, no cameras, no accelerators") → Task 7 covers this exactly.

Naming consistency:

- `_probe_cameras_libcamera`, `_probe_cameras_tegra`, `_probe_cameras_v4l2_usb`, `_probe_network_cameras_mdns` — all follow `_probe_<thing>_<source>` convention.
- `_probe_accelerators_hailo`, `_probe_accelerators_nvidia`, `_probe_accelerators_coral` — same convention.
- `_probe_servo_buses`, `_probe_compute` — same.
- Helper indirections all use `_<thing>_<verb>` (`_dev_hailo_devices`, `_lspci_hailo_lines`, `_mdns_browse_armos_citizen`, `_import_libcamera`, `_parse_nvgstcapture_properties`).
- Test fakes: `_FakeUdevDevice`, `_FakePath`, `_fake_context_with` — all in `test_survey_v2.py`.

Backward compat audit:

- `survey_hardware()` signature unchanged: `async def survey_hardware() -> HardwareMap`.
- `HardwareMap` dataclass: same field names + types. Only widening: `Camera.kind` now allows `"wifi"`, `Camera.driver` now allows `"mdns"`. Old constructions (`Camera(kind="csi", ...)`) remain valid.
- `project_capabilities()` and `merge_capabilities()` signatures unchanged. Output is a strict superset (adds `WIFI_CAMERA` only when a wifi camera is present).
- All capability constants (`CAMERA`, `CSI_CAMERA`, `USB_CAMERA`, `COMPUTE`, `HAILO_INFERENCE`, `NVIDIA_INFERENCE`, `CORAL_INFERENCE`, `SERVO_BUS`, `SERVO_FEETECH`, `SERVO_DYNAMIXEL`) preserved.
- `claude-persona-refresh.sh` reads `hw.cameras`, `hw.accelerators`, `hw.servo_buses`, `hw.compute.cpu_model`, `hw.compute.ram_gb` — all preserved (Task 7 verifies live).

Out-of-scope items intentionally not addressed:

- `AAS_DEVICE` capability — no consumer in codebase yet (per spec instruction "only if a downstream consumer in the codebase actually uses them").
- `_citizenry-agent._udp` / `_xiao-cam._tcp` service types — these are aspirational in the spec; the actual on-wire type is `_armos-citizen._udp.local.` (Task 6 commit explains).
- `jetson_multimedia_api` Python bindings — Task 4 picks nvgstcapture (the simpler "OR" branch the spec offers); JMA noted as future swap.

No `TBD` / `TODO` / `implement later` strings in any task. Every step has a code block, an exact command, or both.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-30-hardware-survey-rewrite.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Tasks 2-6 are independent (each rewrites one probe behind the same public API). Dispatch in parallel after Task 1 lands the pyudev dep; Task 7 + 8 sequence at the end.
**2. Inline Execution** — Run sequentially; ~2 days wall-clock. Each task is a single small commit.
