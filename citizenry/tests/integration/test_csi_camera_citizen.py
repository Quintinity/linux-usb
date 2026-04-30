"""Hardware-gated integration test for the Jetson CSI camera citizen.

Auto-skips on any host that doesn't expose a Tegra-driven /dev/video*.
Runs on the Jetson because /sys/class/video4linux/video0/device/uevent
contains DRIVER=tegra. No env-var toggle needed — the gate IS the
sensor.
"""

from pathlib import Path

import pytest


def _has_tegra_video() -> bool:
    for entry in Path("/sys/class/video4linux").glob("video*"):
        uevent = entry / "device" / "uevent"
        if not uevent.exists():
            continue
        try:
            text = uevent.read_text()
        except OSError:
            continue
        if "DRIVER=tegra" in text:
            return True
    return False


pytestmark = pytest.mark.skipif(
    not _has_tegra_video(),
    reason="requires a Tegra-driven /dev/video* (Jetson IMX219/IMX477/etc)",
)


def test_capture_returns_valid_jpeg_base64():
    """End-to-end: shell out to gst-launch via _capture_frame_b64,
    decode the base64 result, verify it's a JPEG."""
    import base64

    from citizenry.csi_camera_citizen import CSICameraCitizen

    cit = CSICameraCitizen(resolution=(640, 480), framerate=30, jpeg_quality=70)
    cit._init_camera()
    assert cit._camera_ok, "gst-launch + nvarguscamerasrc must be usable"

    b64 = cit._capture_frame_b64()
    assert b64 is not None, "_capture_frame_b64 must return a string"
    raw = base64.b64decode(b64)
    assert raw.startswith(b"\xff\xd8\xff"), "decoded bytes must be a JPEG (SOI marker)"
    assert raw.endswith(b"\xff\xd9"), "decoded bytes must end with JPEG EOI"
    # Sanity bound — a 640x480 q=70 JPEG should be a few KB at minimum
    # (empty/black frames compress small but never to <200B).
    assert len(raw) > 200, f"JPEG suspiciously small: {len(raw)} bytes"
