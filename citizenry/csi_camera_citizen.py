"""Jetson CSI camera citizen — IMX219 (or any nvarguscamerasrc-visible sensor).

Subclasses CameraCitizen so the wire contract is identical to
``run_wifi_camera.py``: same ADVERTISE / heartbeat fields (inherited
unchanged), same ``capabilities`` triple, same REPORT(frame_capture)
inline-base64 ``frame`` body. The only difference is HOW frames are
produced — Jetson's cv2 wheel is built without GStreamer, so we shell
out to ``gst-launch-1.0`` with the verified nvarguscamerasrc pipeline
instead of opening cv2.VideoCapture.

A targeted PROPOSE (recipient == self.pubkey) short-circuits the
marketplace bid round-trip and executes directly, matching the XIAO
firmware. Broadcast PROPOSEs still bid normally so the local PolicyCitizen
on the same node can pick co-located camera-source bids and earn the
+0.15 bonus.
"""

from __future__ import annotations

import base64
import subprocess
import tempfile
import threading
from pathlib import Path

from .camera_citizen import CameraCitizen


# Verified-working pipeline form (Bradley, 2026-04-30 18:26 NZST on
# jetson-orin-001). Argus library handles digital scaling internally so
# non-native resolutions (e.g. 640x480) come out of nvarguscamerasrc
# directly; nvvidconv just hands NVMM → I420 to jpegenc.
#   nvarguscamerasrc sensor-id=N <props> ! video/x-raw(memory:NVMM),W,H,F/1
#     ! nvvidconv ! video/x-raw,format=I420 ! jpegenc ! filesink


class CSICameraCitizen(CameraCitizen):
    def __init__(
        self,
        resolution: tuple[int, int] = (640, 480),
        framerate: int = 30,
        name: str = "jetson-csi-imx219",
        camera_role: str | None = None,
        sensor_id: int = 0,
        wbmode: int = 1,
        exposuretimerange: str | None = None,
        gainrange: str | None = None,
        jpeg_quality: int = 70,
    ):
        super().__init__(
            camera_index=0,
            resolution=resolution,
            name=name,
            camera_role=camera_role,
        )
        self._framerate = framerate
        self._sensor_id = sensor_id
        self._wbmode = wbmode
        self._exposuretimerange = exposuretimerange
        self._gainrange = gainrange
        self._jpeg_quality = jpeg_quality
        self._capture_lock = threading.Lock()
        self._tmp = Path(tempfile.gettempdir()) / "jetson_csi_capture.jpg"

    def _init_camera(self) -> None:
        try:
            r = subprocess.run(
                ["gst-launch-1.0", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            self._camera_ok = r.returncode == 0
        except FileNotFoundError:
            self._log("gst-launch-1.0 not found — degraded")
            self._camera_ok = False
            return
        except Exception as e:
            self._log(f"CSI init error: {e}")
            self._camera_ok = False
            return
        if not self._camera_ok:
            self._log("gst-launch-1.0 not usable — degraded")

    def _build_pipeline(self) -> list[str]:
        w, h = self.resolution
        src_props = [
            f"sensor-id={self._sensor_id}",
            f"wbmode={self._wbmode}",
            "num-buffers=1",
        ]
        if self._exposuretimerange:
            src_props.append(f"exposuretimerange={self._exposuretimerange}")
        if self._gainrange:
            src_props.append(f"gainrange={self._gainrange}")
        return [
            "gst-launch-1.0", "-e",
            "nvarguscamerasrc", *src_props,
            "!", f"video/x-raw(memory:NVMM),width={w},height={h},framerate={self._framerate}/1",
            "!", "nvvidconv",
            "!", "video/x-raw,format=I420",
            "!", "jpegenc", f"quality={self._jpeg_quality}",
            "!", "filesink", f"location={self._tmp}",
        ]

    def _capture_frame_b64(self) -> str | None:
        if not self._camera_ok:
            return None
        cmd = self._build_pipeline()
        with self._capture_lock:
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=8)
            except subprocess.TimeoutExpired:
                self._log("gst-launch capture timed out")
                return None
            if r.returncode != 0 or not self._tmp.exists() or self._tmp.stat().st_size == 0:
                self._log(f"gst-launch failed (rc={r.returncode})")
                return None
            return base64.b64encode(self._tmp.read_bytes()).decode("ascii")

    def _handle_propose(self, env, addr) -> None:
        body = env.body
        task = body.get("task", "")
        if env.recipient == self.pubkey and task == "frame_capture":
            self._handle_frame_capture(env, addr, body)
            return
        super()._handle_propose(env, addr)
