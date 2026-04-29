"""USB Camera Citizen — sense capability for the citizenry.

Wraps a USB camera via OpenCV, advertises video_stream/frame_capture/
color_detection capabilities, and responds to task proposals.
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

from .citizen import Citizen, Neighbor
from .protocol import MessageType, TTL_HEARTBEAT, make_envelope


# Default frame broadcast rate. 5 Hz = 200 ms. Tunable via the Constitution
# Law `camera.broadcast_interval_s` once a constitution is ratified — see
# `constitution.py` for the law definition.
DEFAULT_BROADCAST_INTERVAL_S = 0.2


class CameraCitizen(Citizen):
    """Camera citizen that provides visual sensing capabilities.

    Runs on the Surface Pro 7 (or any machine with a USB camera).
    Provides frame capture on demand and color detection.

    When constructed with ``camera_role`` set (e.g. "wrist", "base"), the
    citizen continuously broadcasts JPEG frames every ~200 ms. PolicyCitizens
    listening on the multicast group cache these frames keyed by camera_role
    and feed them to the policy as observations. Without a role, the citizen
    only responds to on-demand frame_capture proposals.
    """

    def __init__(
        self,
        camera_index: int = 0,
        resolution: tuple[int, int] = (640, 480),
        name: str = "camera-sense",
        camera_role: str | None = None,
    ):
        super().__init__(
            name=name,
            citizen_type="sensor",
            capabilities=["video_stream", "frame_capture", "color_detection"],
        )
        self.camera_index = camera_index
        self.resolution = resolution
        self.camera_role = camera_role
        self._cap = None
        self._frame_count = 0
        self._last_frame_time: float = 0
        self._camera_ok = False
        self._pending_task: dict | None = None
        self._broadcast_task: asyncio.Task | None = None
        # Rate-limit "frame broadcast error" log lines so a persistently bad
        # camera doesn't drown the log at 5 Hz.
        self._last_broadcast_err_log: float = 0.0

    async def start(self):
        await super().start()
        self._init_camera()
        if self._camera_ok:
            role_str = f" role={self.camera_role}" if self.camera_role else ""
            self._log(f"camera ready — index {self.camera_index} @ {self.resolution[0]}x{self.resolution[1]}{role_str}")
        else:
            self._log("camera not available — running in degraded mode")
            self.health = 0.5

        # Periodic frame broadcast: only meaningful when a role is set, since
        # PolicyCitizen's observation cache keys frames by camera_role. Without
        # a role, the broadcast bandwidth is wasted (no consumer can route it).
        if self.camera_role and self._camera_ok:
            self._broadcast_task = asyncio.create_task(self._frame_broadcast_loop())

    def _init_camera(self):
        """Initialize OpenCV video capture."""
        try:
            import cv2
            self._cap = cv2.VideoCapture(self.camera_index)
            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                self._camera_ok = True
            else:
                self._camera_ok = False
                self._cap = None
        except ImportError:
            self._log("opencv not installed — camera disabled")
            self._camera_ok = False
        except Exception as e:
            self._log(f"camera init error: {e}")
            self._camera_ok = False

    def _handle_propose(self, env, addr):
        body = env.body
        task = body.get("task", "")

        # v2.0: Marketplace tasks have task_id — route to bidding first
        if body.get("task_id") and task not in ("teleop", "teleop_frame", "symbiosis_propose"):
            self._handle_marketplace_propose(env, addr, body)
        elif task == "frame_capture":
            self._handle_frame_capture(env, addr, body)
        elif task == "color_detection":
            self._handle_color_detection(env, addr, body)
        elif task not in ("teleop", "teleop_frame", "symbiosis_propose"):
            self.send_reject(env.sender, f"unknown task: {task}", addr)

    def _handle_marketplace_propose(self, env, addr, body):
        """Evaluate a marketplace task and bid if we have the required capabilities."""
        from .marketplace import Task, compute_bid_score
        task = Task.from_propose_body(body)

        for cap in task.required_capabilities:
            if cap not in self.capabilities:
                self.send_reject(env.sender, f"missing capability: {cap}", addr)
                return

        for skill in task.required_skills:
            if not self.skill_tree.has_skill(skill):
                self.send_reject(env.sender, f"missing skill: {skill}", addr)
                return

        score = compute_bid_score(skill_level=1, current_load=0.1, health=self.health)

        # Use the neighbor's known unicast address for reliable delivery
        reply_addr = addr
        if env.sender in self.neighbors:
            reply_addr = self.neighbors[env.sender].addr

        from .protocol import make_envelope, MessageType as MT
        env_out = make_envelope(
            MT.ACCEPT_REJECT,
            self.pubkey,
            {
                "accepted": True,
                "task_id": task.id,
                "task": task.type,
                "bid": {"skill_level": 1, "load": 0.1, "health": self.health, "score": score},
            },
            self._signing_key,
            recipient=env.sender,
        )
        self._unicast.send(env_out, reply_addr)
        self.messages_sent += 1
        self._log(f"bid sent: [{task.id}] {task.type} score={score:.2f}")
        # Track pending task for execution on assignment
        self._pending_task = {"id": task.id, "type": task.type, "params": body.get("params", {}), "governor": env.sender, "addr": reply_addr}

    def _handle_govern(self, env, addr):
        """Handle governance — including task assignments."""
        body = env.body
        gov_type = body.get("type", "")

        if gov_type == "task_assign":
            task_id = body.get("task_id", "")
            task_type = body.get("task", "")
            self._log(f"task assigned: [{task_id}] {task_type}")
            self._add_log("TASK", self.name, f"assigned [{task_id}] {task_type}")
            import asyncio
            asyncio.get_event_loop().create_task(
                self._execute_camera_task(task_id, task_type, body.get("params", {}), env.sender, addr)
            )
        else:
            super()._handle_govern(env, addr)

    async def _execute_camera_task(self, task_id: str, task_type: str, params: dict, governor_key: str, governor_addr: tuple):
        """Execute a camera task with real capture/detection."""
        import time as _time
        t0 = _time.time()
        try:
            if task_type in ("color_detection", "color_sorting"):
                detections = self._detect_colors()
                duration_ms = int((_time.time() - t0) * 1000)
                skill_name = "color_detection" if "color_detection" in self.skill_tree.definitions else "frame_capture"
                xp_earned = self.skill_tree.award_xp(skill_name, base_xp=10, task_difficulty=0.8, success_quality=1.0)
                self.send_report(
                    governor_key,
                    {
                        "type": "task_complete",
                        "task_id": task_id,
                        "result": "success",
                        "duration_ms": duration_ms,
                        "xp_earned": xp_earned,
                        "citizen": self.name,
                        "detections": detections,
                        "detection_count": len(detections),
                    },
                    governor_addr,
                )
                self._log(f"task complete: [{task_id}] {len(detections)} colors detected, +{xp_earned} XP")

            elif task_type in ("frame_capture", "visual_inspection"):
                frame_b64 = self._capture_frame_b64()
                duration_ms = int((_time.time() - t0) * 1000)
                xp_earned = self.skill_tree.award_xp("frame_capture", base_xp=10, task_difficulty=0.5, success_quality=1.0)
                self.send_report(
                    governor_key,
                    {
                        "type": "task_complete",
                        "task_id": task_id,
                        "result": "success" if frame_b64 else "failed",
                        "duration_ms": duration_ms,
                        "xp_earned": xp_earned,
                        "citizen": self.name,
                        "frame_size_kb": len(frame_b64) / 1024 if frame_b64 else 0,
                    },
                    governor_addr,
                )
                self._log(f"task complete: [{task_id}] frame captured, +{xp_earned} XP")

            else:
                self.send_report(
                    governor_key,
                    {"type": "task_complete", "task_id": task_id, "result": "failed", "reason": f"unknown task type: {task_type}", "citizen": self.name},
                    governor_addr,
                )
        except Exception as e:
            self._log(f"task failed: [{task_id}] {e}")
            self.send_report(
                governor_key,
                {"type": "task_complete", "task_id": task_id, "result": "failed", "reason": str(e), "citizen": self.name},
                governor_addr,
            )

    def _handle_frame_capture(self, env, addr, body):
        """Capture a frame and return it as base64 JPEG."""
        if not self._camera_ok:
            self.send_reject(env.sender, "camera not available", addr)
            return

        self.send_accept(env.sender, body, addr)

        frame_b64 = self._capture_frame_b64()
        if frame_b64:
            report_body: dict[str, Any] = {
                "type": "frame_capture",
                "task_id": body.get("task_id", ""),
                "frame": frame_b64,
                "width": self.resolution[0],
                "height": self.resolution[1],
                "timestamp": time.time(),
            }
            # Include camera_role so PolicyCitizen's observation cache can key
            # this frame correctly. Omit when unset rather than sending None,
            # so on-demand captures from role-less cameras stay clean.
            if self.camera_role:
                report_body["camera_role"] = self.camera_role
            self.send_report(env.sender, report_body, addr)
        else:
            self.send_report(
                env.sender,
                {
                    "type": "task_complete",
                    "task_id": body.get("task_id", ""),
                    "result": "failed",
                    "reason": "frame capture failed",
                },
                addr,
            )

    def _handle_color_detection(self, env, addr, body):
        """Detect colored regions and return bounding boxes."""
        if not self._camera_ok:
            self.send_reject(env.sender, "camera not available", addr)
            return

        self.send_accept(env.sender, body, addr)

        detections = self._detect_colors()
        self.send_report(
            env.sender,
            {
                "type": "color_detection",
                "task_id": body.get("task_id", ""),
                "detections": detections,
                "width": self.resolution[0],
                "height": self.resolution[1],
                "timestamp": time.time(),
            },
            addr,
        )

    def _capture_frame_b64(self) -> str | None:
        """Capture a single frame and return as base64-encoded JPEG."""
        if not self._cap:
            return None
        try:
            import cv2
            ret, frame = self._cap.read()
            if not ret:
                return None
            self._frame_count += 1
            self._last_frame_time = time.time()
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return base64.b64encode(buffer).decode("ascii")
        except Exception:
            return None

    def _detect_colors(self) -> list[dict]:
        """Detect colored regions in the current frame.

        Returns list of {color, bbox: [x,y,w,h], area} dicts.
        """
        if not self._cap:
            return []
        try:
            import cv2
            import numpy as np

            ret, frame = self._cap.read()
            if not ret:
                return []

            self._frame_count += 1
            self._last_frame_time = time.time()

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            detections = []

            # Color ranges in HSV
            color_ranges = {
                "red": [(0, 100, 100), (10, 255, 255)],
                "green": [(35, 100, 100), (85, 255, 255)],
                "blue": [(100, 100, 100), (130, 255, 255)],
                "yellow": [(20, 100, 100), (35, 255, 255)],
            }

            for color_name, (lower, upper) in color_ranges.items():
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                # Also check red wrap-around
                if color_name == "red":
                    mask2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
                    mask = mask | mask2

                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area > 500:  # Min area threshold
                        x, y, w, h = cv2.boundingRect(cnt)
                        detections.append({
                            "color": color_name,
                            "bbox": [int(x), int(y), int(w), int(h)],
                            "area": int(area),
                        })

            return detections
        except ImportError:
            return []
        except Exception:
            return []

    def _on_constitution_received(self, sender: str, constitution: dict):
        """Camera accepts constitution but has no servos to configure."""
        self._log(f"constitution received from [{sender[:8]}] — acknowledged")
        # Report back
        for pubkey, n in self.neighbors.items():
            if n.citizen_type == "governor":
                self.send_report(
                    pubkey,
                    {
                        "type": "constitution_applied",
                        "citizen": self.name,
                        "version": constitution.get("version", 0),
                        "servo_limits_applied": False,
                    },
                    n.addr,
                )
                break

    async def stop(self):
        # Cancel the broadcast loop first so it doesn't try to read from a
        # capture device that we're about to release. Swallow CancelledError
        # — that's the expected resolution of awaiting a cancelled task.
        if self._broadcast_task is not None:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            except Exception:
                # Don't let a buggy broadcast loop block citizen shutdown.
                pass
            self._broadcast_task = None

        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
        await super().stop()

    # ── Frame broadcast (continuous observation feed) ──

    async def _frame_broadcast_loop(self):
        """Periodically broadcast a JPEG frame so PolicyCitizens can fill their cache.

        Runs only while ``self._running and self._camera_ok``. Reads the
        broadcast interval from the Constitution Law
        ``camera.broadcast_interval_s`` (default 0.2 s = 5 Hz). A bad single
        frame is logged (rate-limited) but does not kill the loop.
        """
        interval = float(self._law(
            "camera.broadcast_interval_s",
            default=DEFAULT_BROADCAST_INTERVAL_S,
        ))
        # Without a role there's no point broadcasting — frames can't be
        # cached. The start() guard already prevents this, but keep the check
        # defensive in case the role is cleared mid-run.
        if not self.camera_role:
            return

        while self._running and self._camera_ok:
            try:
                frame_b64 = self._capture_frame_b64()
                if frame_b64 and self.camera_role:
                    self._broadcast_frame(frame_b64)
            except Exception as e:
                now = time.time()
                # Rate-limit error logging to once per 5 seconds.
                if now - self._last_broadcast_err_log > 5.0:
                    self._log(f"frame broadcast error: {e}")
                    self._last_broadcast_err_log = now
            await asyncio.sleep(interval)

    def _broadcast_frame(self, frame_b64: str) -> None:
        """Send a frame_stream REPORT to the multicast group (recipient='*').

        Built directly via ``make_envelope`` + ``self._multicast.send`` to
        match the broadcast pattern used by ``_send_advertise``. We can't use
        ``send_report`` here because it requires a unicast addr.
        """
        body = {
            "type": "frame_stream",
            "frame": frame_b64,
            "camera_role": self.camera_role,
            "width": self.resolution[0],
            "height": self.resolution[1],
            "timestamp": time.time(),
        }
        env = make_envelope(
            MessageType.REPORT,
            self.pubkey,
            body,
            self._signing_key,
            recipient="*",
            ttl=TTL_HEARTBEAT,  # frames are ephemeral; short TTL is fine
        )
        self._multicast.send(env)
        self.messages_sent += 1
