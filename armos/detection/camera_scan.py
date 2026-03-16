"""Camera Scanner — enumerate V4L2 cameras.

Scans /dev/video* for available cameras and reports their capabilities.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CameraInfo:
    """Information about a detected camera."""
    device_path: str
    name: str = "Unknown Camera"
    driver: str = ""
    bus_info: str = ""
    resolutions: list[tuple[int, int]] = None

    def __post_init__(self):
        if self.resolutions is None:
            self.resolutions = []


def scan_cameras() -> list[CameraInfo]:
    """Scan for V4L2 cameras on the system.

    Returns list of CameraInfo for each detected capture device.
    """
    cameras = []
    video_dir = Path("/dev")

    for dev in sorted(video_dir.glob("video*")):
        try:
            info = _probe_camera(str(dev))
            if info:
                cameras.append(info)
        except Exception:
            continue

    return cameras


def _probe_camera(device_path: str) -> CameraInfo | None:
    """Probe a single video device for camera capabilities."""
    try:
        import cv2
        cap = cv2.VideoCapture(device_path)
        if not cap.isOpened():
            return None

        # Try to read a frame to confirm it's a real capture device
        ret, _ = cap.read()
        if not ret:
            cap.release()
            return None

        # Get device name
        name = cap.getBackendName() or "USB Camera"

        # Get current resolution
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        resolutions = [(w, h)]

        cap.release()

        return CameraInfo(
            device_path=device_path,
            name=name,
            resolutions=resolutions,
        )
    except ImportError:
        return None
    except Exception:
        return None


def quick_check(device_path: str = "/dev/video0") -> bool:
    """Quick check if a camera is available at the given path."""
    try:
        import cv2
        cap = cv2.VideoCapture(device_path)
        ok = cap.isOpened()
        if ok:
            ret, _ = cap.read()
            ok = ret
        cap.release()
        return ok
    except Exception:
        return False
