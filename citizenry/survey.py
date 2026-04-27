"""Hardware self-survey for citizens.

Probes the local machine and produces a structured `HardwareMap` plus a
flat `capabilities` list compatible with the existing mDNS/Citizen layer.

Slice 1 scope: cameras (libcamera CSI + V4L2 USB) and compute. Future
slices add accelerators, servo buses, audio, and heartbeat enrichment.
"""

import asyncio
import platform
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

# Capability strings — single source of truth.
CAMERA = "camera"
CSI_CAMERA = "csi_camera"
USB_CAMERA = "usb_camera"
COMPUTE = "compute"
HAILO_INFERENCE = "hailo_inference"
NVIDIA_INFERENCE = "nvidia_inference"
CORAL_INFERENCE = "coral_inference"
SERVO_BUS = "servo_bus"
SERVO_FEETECH = "feetech_sts3215"
SERVO_DYNAMIXEL = "dynamixel"


@dataclass
class Camera:
    kind: Literal["csi", "usb"]
    model: str | None
    path: str
    driver: Literal["libcamera", "v4l2"]


@dataclass
class Accelerator:
    kind: Literal["hailo8l", "hailo8", "nvidia", "coral_usb", "coral_pcie"]
    model: str | None
    device: str | None
    tops: float | None


@dataclass
class ServoBus:
    vendor: Literal["feetech", "dynamixel", "unknown"]
    port: str
    usb_vid: str
    usb_pid: str
    controller_id: str | None


@dataclass
class Compute:
    cpu_model: str
    cpu_cores: int
    arch: str
    ram_gb: float


@dataclass
class HardwareDelta:
    cameras_added: list[Camera] = field(default_factory=list)
    cameras_removed: list[Camera] = field(default_factory=list)
    accelerators_added: list[Accelerator] = field(default_factory=list)
    accelerators_removed: list[Accelerator] = field(default_factory=list)
    servo_buses_added: list[ServoBus] = field(default_factory=list)
    servo_buses_removed: list[ServoBus] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any((
            self.cameras_added, self.cameras_removed,
            self.accelerators_added, self.accelerators_removed,
            self.servo_buses_added, self.servo_buses_removed,
        ))

    def summary(self) -> str:
        parts = []
        for added, removed, label in (
            (self.cameras_added, self.cameras_removed, "cam"),
            (self.accelerators_added, self.accelerators_removed, "acc"),
            (self.servo_buses_added, self.servo_buses_removed, "srv"),
        ):
            if added:
                parts.append(f"+{len(added)} {label}")
            if removed:
                parts.append(f"-{len(removed)} {label}")
        return ", ".join(parts) if parts else "no change"


@dataclass
class HardwareMap:
    cameras: list[Camera] = field(default_factory=list)
    accelerators: list[Accelerator] = field(default_factory=list)
    servo_buses: list[ServoBus] = field(default_factory=list)
    compute: Compute | None = None
    surveyed_at: float = field(default_factory=time.time)

    def diff(self, other: "HardwareMap") -> HardwareDelta:
        """Return what's in self but not in other (added) and vice versa (removed).
        Identity keys: camera.path, (accelerator.kind, accelerator.device), servo.port."""
        def by_key(items, key_fn):
            return {key_fn(x): x for x in items}
        cur_cam = by_key(self.cameras, lambda c: c.path)
        prev_cam = by_key(other.cameras, lambda c: c.path)
        cur_acc = by_key(self.accelerators, lambda a: (a.kind, a.device))
        prev_acc = by_key(other.accelerators, lambda a: (a.kind, a.device))
        cur_srv = by_key(self.servo_buses, lambda b: b.port)
        prev_srv = by_key(other.servo_buses, lambda b: b.port)
        return HardwareDelta(
            cameras_added=[v for k, v in cur_cam.items() if k not in prev_cam],
            cameras_removed=[v for k, v in prev_cam.items() if k not in cur_cam],
            accelerators_added=[v for k, v in cur_acc.items() if k not in prev_acc],
            accelerators_removed=[v for k, v in prev_acc.items() if k not in cur_acc],
            servo_buses_added=[v for k, v in cur_srv.items() if k not in prev_srv],
            servo_buses_removed=[v for k, v in prev_srv.items() if k not in cur_srv],
        )

    def to_compact_dict(self) -> dict:
        """Compact form for HEARTBEAT — short keys, fixed-position tuples,
        keep payload under MTU even with several devices."""
        out: dict = {"v": 1}
        if self.cameras:
            out["cam"] = [[c.kind, c.model or "", c.path] for c in self.cameras]
        if self.accelerators:
            out["acc"] = [
                [a.kind, a.device or "", a.tops if a.tops is not None else 0]
                for a in self.accelerators
            ]
        if self.servo_buses:
            out["srv"] = [[b.vendor, b.port] for b in self.servo_buses]
        if self.compute:
            out["cpu"] = [
                self.compute.cpu_model,
                self.compute.cpu_cores,
                self.compute.arch,
                self.compute.ram_gb,
            ]
        return out

    def to_full_dict(self) -> dict:
        """Verbose form for ADVERTISE / dashboard."""
        return {
            "v": 1,
            "cameras": [asdict(c) for c in self.cameras],
            "accelerators": [asdict(a) for a in self.accelerators],
            "servo_buses": [asdict(b) for b in self.servo_buses],
            "compute": asdict(self.compute) if self.compute else None,
            "surveyed_at": self.surveyed_at,
        }


def _parse_libcamera_list(stdout: str) -> list[Camera]:
    """Parse `rpicam-hello --list-cameras` output into Camera objects."""
    cameras = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if " : " not in line:
            continue
        idx_part, _, rest = line.partition(" : ")
        if not idx_part.strip().isdigit():
            continue
        num = int(idx_part.strip())
        model = rest.split(" [", 1)[0].strip()
        cameras.append(Camera(kind="csi", model=model, path=f"csi:{num}", driver="libcamera"))
    return cameras


def _probe_cameras_libcamera() -> list[Camera]:
    """CSI cameras via rpicam-hello / libcamera-hello. No-op if absent."""
    binary = shutil.which("rpicam-hello") or shutil.which("libcamera-hello")
    if not binary:
        return []
    try:
        result = subprocess.run(
            [binary, "--list-cameras"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    return _parse_libcamera_list(result.stdout)


def _probe_cameras_v4l2() -> list[Camera]:
    """USB cameras via /sys/class/video4linux. Filters out CSI/codec subdevices."""
    cameras = []
    sysfs = Path("/sys/class/video4linux")
    if not sysfs.exists():
        return cameras
    for entry in sorted(sysfs.iterdir()):
        try:
            uevent = (entry / "device" / "uevent").read_text()
        except OSError:
            continue
        # Restrict to USB Video Class — keeps out rp1-cfe, pispbe, codecs.
        if "DRIVER=uvcvideo" not in uevent:
            continue
        name = "unknown"
        try:
            name = (entry / "name").read_text().strip()
        except OSError:
            pass
        cameras.append(Camera(kind="usb", model=name, path=f"/dev/{entry.name}", driver="v4l2"))
    return cameras


def _parse_cpuinfo(text: str) -> tuple[str, int]:
    """Return (cpu_model, cpu_cores) from /proc/cpuinfo content."""
    cpu_model = "unknown"
    cpu_cores = 0
    for line in text.splitlines():
        if line.startswith("processor"):
            cpu_cores += 1
        elif cpu_model == "unknown" and (
            line.startswith("model name") or line.startswith("Model")
        ):
            cpu_model = line.split(":", 1)[1].strip()
    return cpu_model, cpu_cores


def _parse_meminfo(text: str) -> float:
    """Return total RAM in GB from /proc/meminfo content."""
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            return round(int(line.split()[1]) / (1024 * 1024), 1)
    return 0.0


def _parse_hailortcli_arch(stdout: str) -> tuple[str, float | None]:
    """Return (kind, tops) from `hailortcli fw-control identify` output."""
    for raw in stdout.splitlines():
        line = raw.strip()
        if line.startswith("Device Architecture"):
            arch = line.split(":", 1)[1].strip().lower()
            if "8l" in arch:
                return "hailo8l", 13.0
            if "8" in arch:
                return "hailo8", 26.0
    return "hailo8", None


def _probe_accelerators_hailo() -> list[Accelerator]:
    """Hailo NPUs via /dev/hailoN; chip kind via hailortcli when present."""
    devices = sorted(Path("/dev").glob("hailo*"))
    if not devices:
        return []
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
    return [
        Accelerator(kind=chip, model=chip, device=str(d), tops=tops)
        for d in devices
    ]


def _probe_accelerators_nvidia() -> list[Accelerator]:
    """NVIDIA GPUs via nvidia-smi (skipped if binary absent)."""
    binary = shutil.which("nvidia-smi")
    if not binary:
        return []
    try:
        result = subprocess.run(
            [binary, "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    accels = []
    for line in result.stdout.strip().splitlines():
        name = line.strip()
        if name:
            accels.append(Accelerator(kind="nvidia", model=name, device=None, tops=None))
    return accels


def _probe_accelerators_coral() -> list[Accelerator]:
    """Google Coral Edge TPU — USB Accelerator and PCIe/M.2 forms."""
    accels = []
    # USB Accelerator: 1a6e:089a (Global Unichip pre-init) or 18d1:9302 (Google post-init).
    usb = Path("/sys/bus/usb/devices")
    if usb.exists():
        for entry in usb.iterdir():
            try:
                vid = (entry / "idVendor").read_text().strip()
                pid = (entry / "idProduct").read_text().strip()
            except OSError:
                continue
            if (vid, pid) in {("1a6e", "089a"), ("18d1", "9302")}:
                accels.append(Accelerator(
                    kind="coral_usb", model="Coral USB Accelerator",
                    device=None, tops=4.0,
                ))
    # PCIe / M.2 Edge TPU: vendor 0x1ac1 device 0x089a.
    pci = Path("/sys/bus/pci/devices")
    if pci.exists():
        for entry in pci.iterdir():
            try:
                vendor = (entry / "vendor").read_text().strip()
                device = (entry / "device").read_text().strip()
            except OSError:
                continue
            if vendor == "0x1ac1" and device == "0x089a":
                accels.append(Accelerator(
                    kind="coral_pcie", model="Coral M.2/PCIe Accelerator",
                    device=None, tops=4.0,
                ))
    return accels


_KNOWN_SERVO_VID = {
    "1a86": "feetech",      # CH340 — common Feetech adapter
    "0403": "dynamixel",    # FTDI — Dynamixel U2D2 et al.
}


def _probe_servo_buses() -> list[ServoBus]:
    """Servo controllers via /sys/class/tty, with vendor-string fallback."""
    buses = []
    tty = Path("/sys/class/tty")
    if not tty.exists():
        return buses
    for entry in sorted(tty.iterdir()):
        device = entry / "device"
        if not device.exists():
            continue
        try:
            usb = (device / "..").resolve()
            if not (usb / "idVendor").exists():
                continue
            vid = (usb / "idVendor").read_text().strip()
            pid = (usb / "idProduct").read_text().strip()
        except OSError:
            continue
        vendor = _KNOWN_SERVO_VID.get(vid)
        if not vendor:
            try:
                product = (usb / "product").read_text().strip().lower()
            except OSError:
                continue
            if "feetech" in product:
                vendor = "feetech"
            elif "dynamixel" in product:
                vendor = "dynamixel"
            elif "servo" in product:
                vendor = "unknown"
            else:
                continue
        serial = None
        try:
            serial = (usb / "serial").read_text().strip()
        except OSError:
            pass
        buses.append(ServoBus(
            vendor=vendor, port=f"/dev/{entry.name}",
            usb_vid=vid, usb_pid=pid, controller_id=serial,
        ))
    return buses


def _probe_compute() -> Compute:
    cpu_model, cpu_cores = "unknown", 0
    ram_gb = 0.0
    try:
        cpu_model, cpu_cores = _parse_cpuinfo(Path("/proc/cpuinfo").read_text())
    except OSError:
        pass
    try:
        ram_gb = _parse_meminfo(Path("/proc/meminfo").read_text())
    except OSError:
        pass
    return Compute(
        cpu_model=cpu_model,
        cpu_cores=cpu_cores,
        arch=platform.machine(),
        ram_gb=ram_gb,
    )


async def survey_hardware() -> HardwareMap:
    """Run all probes in parallel via to_thread (most are blocking syscalls)."""
    csi, v4l2, hailo, nvidia, coral, servos, compute = await asyncio.gather(
        asyncio.to_thread(_probe_cameras_libcamera),
        asyncio.to_thread(_probe_cameras_v4l2),
        asyncio.to_thread(_probe_accelerators_hailo),
        asyncio.to_thread(_probe_accelerators_nvidia),
        asyncio.to_thread(_probe_accelerators_coral),
        asyncio.to_thread(_probe_servo_buses),
        asyncio.to_thread(_probe_compute),
    )
    return HardwareMap(
        cameras=csi + v4l2,
        accelerators=hailo + nvidia + coral,
        servo_buses=servos,
        compute=compute,
    )


def project_capabilities(hw: HardwareMap) -> list[str]:
    """Project a HardwareMap into the flat capability strings used by mDNS."""
    caps: list[str] = [COMPUTE]
    if hw.cameras:
        caps.append(CAMERA)
        if any(c.kind == "csi" for c in hw.cameras):
            caps.append(CSI_CAMERA)
        if any(c.kind == "usb" for c in hw.cameras):
            caps.append(USB_CAMERA)
    for a in hw.accelerators:
        if a.kind in ("hailo8l", "hailo8") and HAILO_INFERENCE not in caps:
            caps.append(HAILO_INFERENCE)
        elif a.kind == "nvidia" and NVIDIA_INFERENCE not in caps:
            caps.append(NVIDIA_INFERENCE)
        elif a.kind in ("coral_usb", "coral_pcie") and CORAL_INFERENCE not in caps:
            caps.append(CORAL_INFERENCE)
    if hw.servo_buses:
        caps.append(SERVO_BUS)
        if any(b.vendor == "feetech" for b in hw.servo_buses) and SERVO_FEETECH not in caps:
            caps.append(SERVO_FEETECH)
        if any(b.vendor == "dynamixel" for b in hw.servo_buses) and SERVO_DYNAMIXEL not in caps:
            caps.append(SERVO_DYNAMIXEL)
    return caps


def merge_capabilities(base: list[str], hw: HardwareMap | None) -> list[str]:
    """Union base caps with hardware-projected caps, preserving order."""
    if hw is None:
        return list(base)
    seen: set[str] = set()
    merged: list[str] = []
    for c in list(base) + project_capabilities(hw):
        if c not in seen:
            seen.add(c)
            merged.append(c)
    return merged
