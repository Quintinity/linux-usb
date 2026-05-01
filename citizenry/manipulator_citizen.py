"""Follower-arm manipulation citizen.

Hardware-agnostic — runs on any node with a Feetech servo bus attached. Today: Pi or Jetson.
"""

import asyncio
import time
from pathlib import Path

import numpy as np

from .citizen import Citizen, Neighbor, Presence
from .episode_recorder import EpisodeRecorder
from .protocol import MessageType, make_envelope
from .marketplace import compute_bid_score, Task
from .skills import default_manipulator_skills
from .mycelium import Warning, Severity
from .survey import HardwareMap, merge_capabilities

MOTOR_NAMES = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
]


class ManipulatorCitizen(Citizen):
    """Follower-arm manipulation citizen.

    Hardware-agnostic — runs on any node with a Feetech servo bus attached.

    Responsibilities:
    - Drive the follower arm servos
    - Accept teleop commands from the governor
    - Validate and apply constitution (safety limits)
    - Stream telemetry REPORTs back to governor
    - Report health and faults
    """

    def __init__(
        self,
        follower_port: str = "/dev/ttyACM0",
        telemetry_hz: float = 2.0,
        hardware: HardwareMap | None = None,
    ):
        base_caps = ["6dof_arm", "gripper", "feetech_sts3215"]
        super().__init__(
            name="pi-follower",
            citizen_type="manipulator",
            capabilities=merge_capabilities(base_caps, hardware),
        )
        self.hardware = hardware
        self.follower_port = follower_port
        self.telemetry_hz = telemetry_hz
        self._follower_bus = None
        self._governor_key: str | None = None
        self._governor_addr: tuple | None = None
        self._teleop_active = False
        self._active_policy_pubkey: str | None = None
        self._frames_received = 0
        self._frames_written = 0
        self._last_frame_time: float = 0
        self._teleop_start: float = 0

        # Safety limits from constitution
        self._servo_limits: dict | None = None

        # v2.0: Initialize with default manipulator skills
        self.skill_tree.merge_definitions(default_manipulator_skills())
        self._current_task_id: str | None = None
        self._current_task_type: str | None = None

        # Episode recorder — always record locally; upload only when configured.
        #   - Uses repo_id="local/citizenry-data" as fallback so episodes always
        #     land on disk even before a constitution is ratified.
        #   - The HF uploader (created in start()) only activates when the governor
        #     sets dataset.hf_repo_id to a real Hugging Face repo.
        #   - _on_constitution_received updates attribution (policy/governor keys)
        #     when a new constitution arrives.
        self._recorder = EpisodeRecorder(
            output_root=Path.home() / "citizenry-datasets" / "v3",
            repo_id=self._law("dataset.hf_repo_id", default="local/citizenry-data"),
            fps=int(self._law("dataset.fps", default=30)),
        )
        self._refresh_attribution()

        # HF uploader — enabled when both Constitution Laws are favourable:
        #   dataset.hf_repo_id     defaults to "" (empty disables uploads)
        #   dataset.upload_after_episode defaults to True
        self._uploader = None
        self._uploader_task: asyncio.Task | None = None

    async def start(self):
        await super().start()
        # Pre-connect the follower bus
        self._follower_bus = self._init_follower_bus()
        if self._follower_bus:
            self._log(f"follower arm ready on {self.follower_port}")
        else:
            self._log("follower arm init failed — will retry on teleop start")

        # Start HF upload watcher if configured.
        if self._law("dataset.upload_after_episode", default=True):
            repo_id = self._law("dataset.hf_repo_id", default="")
            if repo_id:
                from .hf_upload import HFUploader
                delete = self._law("dataset.delete_after_upload", default=True)
                cap = int(self._law("dataset.max_local_episodes", default=50))
                retry_interval = float(self._law("dataset.retry_interval_s", default=300))
                self._uploader = HFUploader(repo_id=repo_id)
                repo_safe = self._recorder.repo_id.replace("/", "__")
                dataset_root = self._recorder.output_root / repo_safe
                self._uploader_task = asyncio.create_task(
                    self._uploader.watch(
                        dataset_root,
                        poll_interval=retry_interval,
                        delete_on_success=delete,
                        cap_local_episodes=cap,
                    )
                )
                self._log(f"HF uploader started → {repo_id} (delete={delete}, cap={cap})")

    @property
    def governor_pubkey(self) -> str | None:
        """The pubkey of the governor we're following (None if no governor seen yet).

        Surfaces ``_governor_key`` under the name used by the attribution
        sidecar — keeps call sites readable and makes the attribute reachable
        without ``getattr`` defensiveness.
        """
        return self._governor_key

    def _refresh_attribution(self) -> None:
        """Push current provenance values into the episode recorder.

        Call sites: __init__, _on_constitution_received, and pre-begin_episode
        in _execute_task. The watchdog and governor-disconnect paths clear
        ``_active_policy_pubkey`` directly without invoking this — the next
        episode-begin refresh will pick up the cleared value. The recorder's
        ``set_attribution`` is idempotent and just stores into a dict, so
        calling it repeatedly is cheap.
        """
        self._recorder.set_attribution(
            node_pubkey=self.node_pubkey,
            policy_pubkey=self._active_policy_pubkey,
            governor_pubkey=self.governor_pubkey,
            constitution_hash=self.constitution_hash,
        )

    def _on_neighbor_joined(self, neighbor: Neighbor):
        """Track the governor."""
        if neighbor.citizen_type == "governor":
            self._governor_key = neighbor.pubkey
            self._governor_addr = neighbor.addr
            self._log(f"governor found: {neighbor.name}")

    def _on_neighbor_presence_changed(self, neighbor: Neighbor, old_presence: Presence):
        """If governor goes dead, safe-stop teleop."""
        if neighbor.pubkey == self._governor_key and neighbor.presence == Presence.PRESUMED_DEAD:
            self._log("GOVERNOR DEAD — disabling torque for safety")
            self._add_log("SAFETY", "self", "governor dead — torque disabled")
            self._disable_torque()
            self._teleop_active = False
            self._active_policy_pubkey = None
            self.state = "idle"

    def _on_constitution_received(self, sender: str, constitution: dict):
        """Verify signature, then apply constitutional safety limits.

        Uses the wire-tolerant ``verify_constitution_dict`` helper so EMEX
        extension fields (``max_torque_pct``, ``position_envelope``, etc.)
        don't trip the base-dataclass round-trip path.
        """
        from .authority import verify_constitution_dict
        if not verify_constitution_dict(constitution):
            self._log(f"CONSTITUTION REJECTED — invalid signature from [{sender[:8]}]")
            self._add_log("SECURITY", sender[:8], "constitution signature invalid — rejected")
            if self._governor_key and self._governor_addr:
                self.send_report(
                    self._governor_key,
                    {"type": "constitution_rejected", "citizen": self.name, "reason": "invalid_signature"},
                    self._governor_addr,
                )
            return
        self._log("constitution signature verified OK")

        servo_limits = constitution.get("servo_limits")
        if servo_limits:
            self._servo_limits = servo_limits
            self._apply_servo_limits(servo_limits)

        # Persist constitution for restarts
        try:
            from .persistence import save_constitution
            save_constitution(self.name, constitution)
        except Exception:
            pass

        # Refresh recorder attribution now that we have constitution keys.
        self._refresh_attribution()

        # Report back that we applied it
        if self._governor_key and self._governor_addr:
            self.send_report(
                self._governor_key,
                {
                    "type": "constitution_applied",
                    "citizen": self.name,
                    "version": constitution.get("version", 0),
                    "servo_limits_applied": servo_limits is not None,
                },
                self._governor_addr,
            )

    def _apply_servo_limits(self, limits: dict):
        """Write safety limits to servo EEPROM via the bus."""
        if not self._follower_bus:
            self._log("cannot apply servo limits — bus not connected")
            return

        try:
            bus = self._follower_bus
            max_torque = limits.get("max_torque", 500)
            protection_current = limits.get("protection_current", 250)

            # Disable torque to write EEPROM
            bus.disable_torque()

            for motor_name in MOTOR_NAMES:
                try:
                    bus.write("Max_Torque_Limit", motor_name, max_torque)
                    bus.write("Protection_Current", motor_name, protection_current)
                except Exception as e:
                    self._log(f"limit write failed for {motor_name}: {e}")

            self._log(f"servo limits applied — max_torque={max_torque}, protection_current={protection_current}")
            self._add_log("GOVERN", "self", f"limits: torque={max_torque} current={protection_current}")
        except Exception as e:
            self._log(f"apply servo limits failed: {e}")

    def _handle_propose(self, env, addr):
        body = env.body
        task = body.get("task", "")

        if task == "teleop":
            self._handle_teleop_proposal(env, addr, body)
        elif task == "teleop_frame":
            self._handle_teleop_frame(env, body)
        elif task == "symbiosis_propose":
            self._handle_symbiosis_propose(env, addr, body)
        elif task == "dialogue":
            self._handle_dialogue(env, addr, body)
        elif task == "calibrate":
            self._handle_calibrate(env, addr, body)
        elif task == "self_calibrate":
            self._handle_self_calibrate(env, addr, body)
        elif body.get("task_id"):
            # v2.0: Marketplace task proposal — evaluate and bid
            self._handle_marketplace_propose(env, addr, body)

    def _handle_teleop_proposal(self, env, addr, body):
        """Governor wants to start teleop — accept or reject."""
        if self._follower_bus is None:
            self._follower_bus = self._init_follower_bus()

        if self._follower_bus is None:
            self.send_reject(env.sender, "follower arm not available", addr)
            return

        self._governor_key = env.sender
        self._governor_addr = addr
        self._teleop_active = True
        self._teleop_start = time.time()
        self._frames_received = 0
        self._frames_written = 0
        # Reset the watchdog clock. Without this, the previous session's
        # _last_frame_time leaks into a new accept and the watchdog trips
        # immediately because "no frames for N seconds" is true the moment
        # we re-enable the loop.
        self._last_frame_time = 0.0
        self.state = "teleop"

        # Enable torque on all motors
        self._enable_torque()

        self.send_accept(env.sender, body, addr)
        self._log("teleop ACCEPTED — torque enabled, ready for frames")

        # Start watchdog and telemetry streaming
        asyncio.get_event_loop().create_task(self._teleop_watchdog())
        asyncio.get_event_loop().create_task(self._telemetry_loop())

    def _handle_teleop_frame(self, env, body):
        """Received a teleop position frame — write to servos."""
        if not self._teleop_active:
            return

        positions = body.get("positions")
        if not positions:
            return

        # Track which policy is driving us — every accepted frame's sender
        # is the current authority over this manipulator. Stamped onto the
        # episode attribution sidecar so recordings carry policy provenance.
        # Envelope routing (citizen.py recipient filter) guarantees this frame
        # is addressed to us, so no body-level target_follower_pubkey check is
        # needed — env.sender is the active policy.
        self._active_policy_pubkey = env.sender
        self._frames_received += 1
        self._last_frame_time = time.time()

        if self._write_positions(positions):
            self._frames_written += 1

        if self._frames_received % 300 == 0:
            elapsed = time.time() - self._teleop_start
            fps = self._frames_received / elapsed if elapsed > 0 else 0
            drop_rate = 1.0 - (self._frames_written / self._frames_received) if self._frames_received else 0
            self._log(f"teleop: {self._frames_received} rx, {fps:.1f} FPS, {drop_rate:.1%} drops")

    # Watchdog timeout. Generous to handle VLA cold-start: SmolVLA on Orin
    # Nano needs (~0.5s state-cache fill) + (~1.5s first-chunk forward) +
    # (~33ms emit + scheduling jitter). 8s leaves headroom; once the action
    # queue is primed, frames flow at ~30Hz so the watchdog only matters
    # for the first cycle.
    TELEOP_WATCHDOG_S: float = 8.0

    async def _teleop_watchdog(self):
        """If no frame arrives for TELEOP_WATCHDOG_S, stop motors for safety."""
        while self._teleop_active and self._running:
            await asyncio.sleep(0.5)
            if (
                self._last_frame_time > 0
                and time.time() - self._last_frame_time > self.TELEOP_WATCHDOG_S
            ):
                self._log(
                    f"WATCHDOG: no frames for {self.TELEOP_WATCHDOG_S}s — disabling torque"
                )
                self._add_log("SAFETY", "watchdog", "no frames — torque disabled")
                self._disable_torque()
                self._teleop_active = False
                self._active_policy_pubkey = None
                self.state = "idle"

                if self._governor_key and self._governor_addr:
                    self.send_report(
                        self._governor_key,
                        {
                            "type": "fault",
                            "citizen": self.name,
                            "detail": "teleop_timeout",
                            "frames_received": self._frames_received,
                            "frames_written": self._frames_written,
                        },
                        self._governor_addr,
                    )
                break

    # ── v2.0: Marketplace bidding ──

    def _handle_marketplace_propose(self, env, addr, body):
        """Evaluate a marketplace task and bid if capable."""
        task = Task.from_propose_body(body)

        # Check capabilities
        for cap in task.required_capabilities:
            if cap not in self.capabilities:
                self.send_reject(env.sender, f"missing capability: {cap}", addr)
                return

        # Check skills
        for skill in task.required_skills:
            if not self.skill_tree.has_skill(skill):
                self.send_reject(env.sender, f"missing skill: {skill}", addr)
                return

        # Check availability
        if self._teleop_active or self._current_task_id:
            self.send_reject(env.sender, "busy", addr)
            return

        # Compute bid score
        best_skill = 0
        for skill in task.required_skills:
            level = self.skill_tree.skill_level(skill)
            best_skill = max(best_skill, level)
        if not task.required_skills:
            best_skill = 1  # Default level for unskilled tasks

        load = 0.1 if self.state == "idle" else 0.7
        score = compute_bid_score(best_skill, load, self.health)

        # Send bid
        from .protocol import make_envelope, MessageType as MT
        env_out = make_envelope(
            MT.ACCEPT_REJECT,
            self.pubkey,
            {
                "accepted": True,
                "task_id": task.id,
                "task": task.type,
                "bid": {
                    "skill_level": best_skill,
                    "load": load,
                    "health": self.health,
                    "score": score,
                },
            },
            self._signing_key,
            recipient=env.sender,
        )
        self._unicast.send(env_out, addr)
        self.messages_sent += 1
        self._log(f"bid sent: [{task.id}] {task.type} score={score:.2f}")
        self._add_log("BID", self.name, f"[{task.id}] score={score:.2f}")

    def _handle_symbiosis_propose(self, env, addr, body):
        """Evaluate and accept/reject a symbiosis proposal."""
        from .symbiosis import SymbiosisContract
        contract = SymbiosisContract.from_propose_body(body, env.sender, self.pubkey)

        # Check if we have the consumer capability
        if contract.consumer_capability not in self.capabilities:
            self.send_reject(env.sender, f"missing capability: {contract.consumer_capability}", addr)
            return

        # Accept and register
        contract.status = contract.status.__class__("active")
        self.contracts.register(contract)

        from .protocol import make_envelope, MessageType as MT
        env_out = make_envelope(
            MT.ACCEPT_REJECT,
            self.pubkey,
            {"accepted": True, "task": "symbiosis_propose", "contract_id": contract.id},
            self._signing_key,
            recipient=env.sender,
        )
        self._unicast.send(env_out, addr)
        self.messages_sent += 1
        self._log(f"symbiosis accepted: {contract.composite_capability} with [{env.sender[:8]}]")
        self._add_log("CONTRACT", self.name, f"accepted: {contract.composite_capability}")

    def _handle_dialogue(self, env, addr, body):
        """Respond to a dialogue question from the governor."""
        from .dialogue import parse_question, compose_response
        question = body.get("text", "how are you")
        q_type = parse_question(question)
        response_text = compose_response(self, q_type)
        self._log(f"dialogue: '{question}' → '{response_text[:60]}...'")
        self.send_report(
            env.sender,
            {
                "type": "dialogue_response",
                "citizen": self.name,
                "question": question,
                "response": response_text,
            },
            addr,
        )

    def _handle_self_calibrate(self, env, addr, body):
        """Run self-calibration with mode selection."""
        mode_str = body.get("mode", "staged")
        self.send_accept(env.sender, body, addr)
        self._log(f"self-calibration starting — mode: {mode_str}")
        import asyncio
        asyncio.get_event_loop().create_task(
            self._run_self_calibration(env.sender, addr, mode_str)
        )

    async def _run_self_calibration(self, governor_key: str, governor_addr: tuple, mode_str: str = "staged"):
        """Execute self-calibration and report results."""
        try:
            from .self_calibration import self_calibrate_all, CalibrationMode

            mode_map = {
                "staged": CalibrationMode.GRAVITY_STAGED,
                "current": CalibrationMode.CURRENT_SENSING,
                "camera": CalibrationMode.CAMERA_GUIDED,
                "manual": CalibrationMode.MANUAL,
            }
            mode = mode_map.get(mode_str, CalibrationMode.GRAVITY_STAGED)

            if not self._follower_bus:
                self._follower_bus = self._init_follower_bus()
            if not self._follower_bus:
                self.send_report(governor_key,
                    {"type": "self_calibration_complete", "citizen": self.name, "error": "arm not connected"},
                    governor_addr)
                return

            result = self_calibrate_all(
                self._follower_bus,
                mode=mode,
                log_fn=lambda msg: self._log(f"cal: {msg}"),
            )

            # Save limits to genome
            self.genome.calibration["motor_limits"] = {
                name: limits.to_dict() for name, limits in result.motors.items()
            }

            # Report to governor
            self.send_report(
                governor_key,
                {
                    "type": "self_calibration_complete",
                    "citizen": self.name,
                    "motors": {k: v.to_dict() for k, v in result.motors.items()},
                    "duration_s": result.duration_s,
                },
                governor_addr,
            )
            self._log(f"self-calibration complete in {result.duration_s:.1f}s")

        except Exception as e:
            self._log(f"self-calibration error: {e}")
            self.send_report(governor_key,
                {"type": "self_calibration_complete", "citizen": self.name, "error": str(e)},
                governor_addr)

    def _handle_calibrate(self, env, addr, body):
        """Run camera-arm calibration locally on the Pi."""
        self.send_accept(env.sender, body, addr)
        self._log("calibration starting — arm will move to 10+ positions")
        asyncio.get_event_loop().create_task(
            self._run_calibration(env.sender, addr)
        )

    async def _run_calibration(self, governor_key: str, governor_addr: tuple):
        """Execute the full calibration procedure locally."""
        try:
            import cv2
            from .calibration import (
                CALIBRATION_POSES, CORNER_POSES, VALIDATION_POSES,
                GripperDetector, CameraPlacementGuide, fit_homography,
                compute_validation_error, CalibrationResult, CalibrationPoint,
                save_calibration, _full_pose,
            )

            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self._report_calibration_error(governor_key, governor_addr, "camera not available")
                return

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            if not self._follower_bus:
                self._follower_bus = self._init_follower_bus()
            if not self._follower_bus:
                cap.release()
                self._report_calibration_error(governor_key, governor_addr, "arm not available")
                return

            self._enable_torque()
            detector = GripperDetector()
            collected_points = []
            pixel_pts = []
            servo_pts = []

            # Phase 1: Placement check via corners
            self._log("calibration phase 1: checking camera placement")
            corner_pixels = []
            for i, pose in enumerate(CORNER_POSES):
                full = _full_pose(pose)
                full["gripper"] = GripperDetector.GRIPPER_OPEN
                await self._smooth_move(full, duration=0.8)
                await asyncio.sleep(0.5)
                ret, frame_open = cap.read()
                full["gripper"] = GripperDetector.GRIPPER_CLOSED
                self._write_positions(full)
                await asyncio.sleep(0.5)
                ret2, frame_closed = cap.read()

                tip = detector.detect(frame_open, frame_closed)
                corner_pixels.append(tip)
                self._log(f"  corner {i+1}/4: {'detected' if tip else 'not visible'}")

            placement = CameraPlacementGuide.evaluate(corner_pixels)
            self._log(f"  placement: {placement.overall} ({placement.corners_visible}/4 corners, {placement.coverage_pct:.0f}% coverage)")
            for s in placement.suggestions:
                self._log(f"  suggestion: {s}")

            # Phase 2: Collect calibration points
            self._log("calibration phase 2: collecting 10 calibration points")
            for i, pose in enumerate(CALIBRATION_POSES):
                full = _full_pose(pose)
                full["gripper"] = GripperDetector.GRIPPER_OPEN
                await self._smooth_move(full, duration=0.6)
                await asyncio.sleep(0.5)
                ret, frame_open = cap.read()

                full["gripper"] = GripperDetector.GRIPPER_CLOSED
                self._write_positions(full)
                await asyncio.sleep(0.5)
                ret2, frame_closed = cap.read()

                tip = detector.detect(frame_open, frame_closed)
                if tip is None:
                    tip = detector.detect_by_color(frame_open)

                if tip:
                    px, py = tip
                    pan = pose["shoulder_pan"]
                    lift = pose["shoulder_lift"]
                    elbow = pose["elbow_flex"]
                    pixel_pts.append((px, py))
                    servo_pts.append((pan, lift, elbow))
                    collected_points.append(CalibrationPoint(px, py, pan, lift, elbow))
                    self._log(f"  point {i+1}/10: ({px:.0f}, {py:.0f}) → pan={pan} lift={lift} elbow={elbow}")
                else:
                    self._log(f"  point {i+1}/10: detection failed — skipping")

            # Move home
            await self._smooth_move(_full_pose({"shoulder_pan": 2048, "shoulder_lift": 1400, "elbow_flex": 3000}), duration=0.8)
            self._disable_torque()

            if len(pixel_pts) < 4:
                cap.release()
                self._report_calibration_error(governor_key, governor_addr,
                    f"only {len(pixel_pts)} points detected, need at least 4")
                return

            # Phase 3: Fit homography
            self._log("calibration phase 3: fitting homography")
            transform, inliers, outliers, reproj_error = fit_homography(pixel_pts, servo_pts)

            if transform is None:
                cap.release()
                self._report_calibration_error(governor_key, governor_addr, "homography fit failed")
                return

            self._log(f"  homography: {inliers} inliers, {outliers} outliers, error={reproj_error:.1f}")

            # Phase 4: Validation
            self._log("calibration phase 4: validation on held-out poses")
            val_pixel = []
            val_servo = []
            self._enable_torque()
            for i, pose in enumerate(VALIDATION_POSES):
                full = _full_pose(pose)
                full["gripper"] = GripperDetector.GRIPPER_OPEN
                await self._smooth_move(full, duration=0.6)
                await asyncio.sleep(0.5)
                ret, frame_open = cap.read()
                full["gripper"] = GripperDetector.GRIPPER_CLOSED
                self._write_positions(full)
                await asyncio.sleep(0.5)
                ret2, frame_closed = cap.read()

                tip = detector.detect(frame_open, frame_closed)
                if tip:
                    val_pixel.append(tip)
                    val_servo.append((pose["shoulder_pan"], pose["shoulder_lift"], pose["elbow_flex"]))
                    self._log(f"  validation {i+1}/3: detected")
                else:
                    self._log(f"  validation {i+1}/3: detection failed")

            await self._smooth_move(_full_pose({"shoulder_pan": 2048, "shoulder_lift": 1400, "elbow_flex": 3000}), duration=0.8)
            self._disable_torque()
            cap.release()

            val_error = compute_validation_error(val_pixel, val_servo, transform) if val_pixel else float('inf')
            self._log(f"  validation error: {val_error:.1f}")

            # Phase 5: Save
            result = CalibrationResult(
                points=collected_points,
                homography=transform,
                inlier_count=inliers,
                outlier_count=outliers,
                reprojection_error=reproj_error,
                validation_error=val_error,
                placement=placement,
            )
            save_calibration("calibration", result)
            self._log(f"calibration saved — {len(collected_points)} points, error={reproj_error:.1f}")

            # Report to governor
            self.send_report(
                governor_key,
                {
                    "type": "calibration_complete",
                    "citizen": self.name,
                    "points": len(collected_points),
                    "inliers": inliers,
                    "outliers": outliers,
                    "reprojection_error": reproj_error,
                    "validation_error": val_error,
                    "placement": placement.overall,
                    "suggestions": placement.suggestions,
                    "calibration": result.to_dict(),
                },
                governor_addr,
            )

        except Exception as e:
            self._log(f"calibration error: {e}")
            self._report_calibration_error(governor_key, governor_addr, str(e))
        finally:
            self._disable_torque()

    def _report_calibration_error(self, governor_key: str, governor_addr: tuple, error: str):
        self.send_report(
            governor_key,
            {"type": "calibration_complete", "citizen": self.name, "error": error},
            governor_addr,
        )

    async def _telemetry_loop(self):
        """Stream servo telemetry back to governor at telemetry_hz."""
        interval = 1.0 / self.telemetry_hz
        while self._teleop_active and self._running:
            await asyncio.sleep(interval)
            if not self._governor_key or not self._governor_addr:
                continue
            if not self._follower_bus:
                continue

            telemetry = self._read_telemetry()
            if telemetry:
                self.send_report(
                    self._governor_key,
                    telemetry,
                    self._governor_addr,
                )

    def _read_telemetry(self) -> dict | None:
        """Read telemetry from follower arm, check safety, generate warnings."""
        try:
            from .telemetry import read_telemetry, telemetry_to_report, check_safety
            telem = read_telemetry(self._follower_bus)
            report = telemetry_to_report(telem)

            # Check safety limits
            limits = {}
            if self._servo_limits:
                limits["min_voltage"] = self._servo_limits.get("min_voltage", 6.0)
                limits["max_temperature"] = self._servo_limits.get("max_temperature", 65)
            violations = check_safety(telem, limits)
            if violations:
                report["violations"] = violations
                for v in violations:
                    self._log(f"SAFETY: {v}")
                    # v2.0: Generate mycelium warnings for violations
                    severity = Severity.CRITICAL if "voltage" in v.lower() else Severity.WARNING
                    warning = Warning(
                        severity=severity,
                        detail=v,
                        source_citizen=self.pubkey,
                    )
                    self.mycelium.add_warning(warning)
                    # Broadcast fast-channel warning
                    self._broadcast_warning(warning)

            # v2.0: Check telemetry against immune memory
            telem_dict = {
                "min_voltage": report.get("min_voltage"),
                "max_temperature": report.get("max_temperature"),
                "total_current_ma": report.get("total_current_ma"),
                "has_errors": report.get("has_errors"),
                "max_load_pct": report.get("max_load_pct"),
            }
            immune_matches = self.immune_memory.match(telem_dict)
            for pattern in immune_matches:
                self._log(f"immune pattern matched: {pattern.pattern_type} — {pattern.mitigation}")

            # v4.0: Feed telemetry to biological subsystems
            self._on_telemetry_received(telem_dict)

            return report
        except ImportError:
            return None
        except Exception:
            return None

    def _broadcast_warning(self, warning: Warning):
        """Broadcast a critical/emergency warning via multicast (fast channel)."""
        if warning.severity >= Severity.CRITICAL:
            env = make_envelope(
                MessageType.REPORT,
                self.pubkey,
                warning.to_report_body(),
                self._signing_key,
            )
            self._multicast.send(env)
            self.messages_sent += 1

    def _init_follower_bus(self):
        """Initialize the Feetech servo bus for the follower arm."""
        try:
            from lerobot.motors.feetech.feetech import FeetechMotorsBus
            from lerobot.motors.motors_bus import Motor, MotorNormMode

            motors = {
                name: Motor(i + 1, "sts3215",
                            MotorNormMode.RANGE_0_100 if name == "gripper" else MotorNormMode.RANGE_M100_100)
                for i, name in enumerate(MOTOR_NAMES)
            }
            bus = FeetechMotorsBus(port=self.follower_port, motors=motors)
            bus.connect()
            return bus
        except Exception as e:
            self._log(f"follower bus error: {e}")
            return None

    def _enable_torque(self):
        if self._follower_bus:
            try:
                self._follower_bus.enable_torque()
                self._log("torque enabled")
            except Exception as e:
                self._log(f"torque enable failed: {e}")

    def _disable_torque(self):
        if self._follower_bus:
            try:
                self._follower_bus.disable_torque()
                self._log("torque disabled")
            except Exception as e:
                self._log(f"torque disable failed: {e}")

    def _write_positions(self, positions: dict) -> bool:
        """Write goal positions to follower arm servos."""
        if not self._follower_bus:
            return False
        try:
            goal = {name: positions.get(name, 2048) for name in MOTOR_NAMES}
            self._follower_bus.sync_write("Goal_Position", goal, normalize=False)
            return True
        except Exception:
            return False

    def _handle_govern(self, env, addr):
        """Extended governance handling — task assignments + base handling."""
        body = env.body
        gov_type = body.get("type", "")

        if gov_type == "task_assign":
            task_id = body.get("task_id", "")
            task_type = body.get("task", "")
            self._current_task_id = task_id
            self._current_task_type = task_type
            self.state = "executing"
            self._log(f"task assigned: [{task_id}] {task_type}")
            self._add_log("TASK", self.name, f"assigned [{task_id}] {task_type}")
            # Execute task async
            asyncio.get_event_loop().create_task(
                self._execute_task(task_id, task_type, body.get("params", {}), env.sender, addr)
            )
        else:
            # Delegate to base class for constitution, laws, genome, skills, etc.
            super()._handle_govern(env, addr)

    def _read_all_positions(self) -> dict[str, int]:
        """Read current positions from all servos."""
        if not self._follower_bus:
            return {}
        try:
            positions = self._follower_bus.sync_read("Present_Position", normalize=False, num_retry=3)
            return {
                name: int(positions[name]) if not hasattr(positions[name], 'item')
                else int(positions[name].item())
                for name in MOTOR_NAMES
            }
        except Exception:
            return {}

    def _read_all_currents(self) -> list[float]:
        """Read current draw from all servos."""
        if not self._follower_bus:
            return []
        ph = self._follower_bus.packet_handler
        port = self._follower_bus.port_handler
        currents = []
        for mid in range(1, 7):
            try:
                val, r, _ = ph.read2ByteTxRx(port, mid, 69)
                if r == 0:
                    currents.append((val & 0x7FFF) * 6.5)
                else:
                    currents.append(0.0)
            except Exception:
                currents.append(0.0)
        return currents

    async def _execute_task(self, task_id: str, task_type: str, params: dict, governor_key: str, governor_addr: tuple):
        """Execute an assigned task with real servo movements and report results."""
        t0 = time.time()

        # Begin episode recording — refresh attribution first so the sidecar
        # captures whichever policy/governor/constitution are live right now.
        episode_task = f"{task_type}/{params.get('gesture', '')}".rstrip('/')
        self._refresh_attribution()
        self._recorder.begin_episode(episode_task, params=params)

        try:
            self._log(f"executing task: [{task_id}] {task_type}")

            # Record initial state
            positions = self._read_all_positions()
            currents = self._read_all_currents()
            self._recorder.record_frame(
                frame_index=0,
                timestamp=0.0,
                image=np.zeros((96, 128, 3), dtype=np.uint8),
                joint_positions=list(positions.values()) if isinstance(positions, dict) else (positions or []),
                joint_currents=currents or [],
                joint_temperatures=[],
                joint_loads=[],
                action_positions=list(positions.values()) if isinstance(positions, dict) else (positions or []),
                reward=0.0,
            )

            if task_type == "basic_gesture":
                await self._exec_gesture(params)
            elif task_type == "pick_and_place":
                await self._exec_pick_and_place(params)
            elif task_type in ("basic_movement", "precise_movement"):
                await self._exec_move(params)
            else:
                await asyncio.sleep(1.0)

            # Record final state
            final_positions = self._read_all_positions()
            final_currents = self._read_all_currents()
            fp_list = list(final_positions.values()) if isinstance(final_positions, dict) else (final_positions or [])
            self._recorder.record_frame(
                frame_index=self._recorder.frame_count,
                timestamp=(time.time() - t0),
                image=np.zeros((96, 128, 3), dtype=np.uint8),
                joint_positions=fp_list,
                joint_currents=final_currents or [],
                joint_temperatures=[],
                joint_loads=[],
                action_positions=fp_list,
                reward=1.0,
            )

            duration_ms = int((time.time() - t0) * 1000)
            skill_name = task_type if task_type in self.skill_tree.definitions else "basic_movement"
            quality = 1.0 if duration_ms < 10000 else 0.8
            xp_earned = self.skill_tree.award_xp(skill_name, base_xp=10, task_difficulty=0.8, success_quality=quality)

            # End episode as success
            await asyncio.to_thread(
                self._recorder.close_episode,
                success=True,
                notes=f"{task_type} {duration_ms}ms +{xp_earned}XP",
                duration_s=duration_ms / 1000.0,
            )

            self.send_report(
                governor_key,
                {
                    "type": "task_complete",
                    "task_id": task_id,
                    "result": "success",
                    "duration_ms": duration_ms,
                    "xp_earned": xp_earned,
                    "citizen": self.name,
                    "episode_dir": str(self._recorder.last_episode_dir),
                },
                governor_addr,
            )
            self._log(f"task complete: [{task_id}] {duration_ms}ms +{xp_earned} XP")
            self._on_task_completed(task_type, skill_name, True, duration_ms)
        except Exception as e:
            self._log(f"task failed: [{task_id}] {e}")
            if self._recorder._open_episode_id is not None:
                await asyncio.to_thread(
                    self._recorder.close_episode,
                    success=False,
                    notes=str(e),
                )
            self.send_report(
                governor_key,
                {
                    "type": "task_complete",
                    "task_id": task_id,
                    "result": "failed",
                    "reason": str(e),
                    "citizen": self.name,
                },
                governor_addr,
            )
            self._on_task_completed(task_type, task_type, False)
        finally:
            self._current_task_id = None
            self._current_task_type = None
            self.state = "idle"

    # ── Real task executors ──

    async def _exec_gesture(self, params: dict):
        """Execute a gesture on the follower arm (wave, nod, etc.)."""
        if not self._follower_bus:
            raise RuntimeError("arm not connected")

        gesture = params.get("gesture", "wave")
        HOME = {n: 2048 for n in MOTOR_NAMES}
        HOME["shoulder_lift"] = 1400
        HOME["elbow_flex"] = 3000

        if gesture == "wave":
            poses = [
                HOME,
                {"shoulder_pan": 2400, "shoulder_lift": 1600, "elbow_flex": 2500, "wrist_flex": 2048, "wrist_roll": 1600, "gripper": 2048},
                {"shoulder_pan": 1700, "shoulder_lift": 1600, "elbow_flex": 2500, "wrist_flex": 2048, "wrist_roll": 2500, "gripper": 2048},
                {"shoulder_pan": 2400, "shoulder_lift": 1600, "elbow_flex": 2500, "wrist_flex": 2048, "wrist_roll": 1600, "gripper": 2048},
                {"shoulder_pan": 1700, "shoulder_lift": 1600, "elbow_flex": 2500, "wrist_flex": 2048, "wrist_roll": 2500, "gripper": 2048},
                HOME,
            ]
        elif gesture == "nod":
            poses = [
                HOME,
                {**HOME, "wrist_flex": 1700},
                {**HOME, "wrist_flex": 2400},
                {**HOME, "wrist_flex": 1700},
                HOME,
            ]
        elif gesture == "grip":
            poses = [
                HOME,
                {**HOME, "gripper": 1400},  # open
                {**HOME, "gripper": 2500},  # close
                {**HOME, "gripper": 1400},  # open
                HOME,
            ]
        else:
            poses = [HOME]

        self._enable_torque()
        try:
            for pose in poses:
                await self._smooth_move(pose, duration=0.5)
                await asyncio.sleep(0.3)
        finally:
            self._disable_torque()

    async def _exec_pick_and_place(self, params: dict):
        """Execute a pick-and-place sequence."""
        if not self._follower_bus:
            raise RuntimeError("arm not connected")

        HOME = {"shoulder_pan": 2048, "shoulder_lift": 1400, "elbow_flex": 3000, "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 2048}
        REACH = {"shoulder_pan": 2048, "shoulder_lift": 1800, "elbow_flex": 2200, "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 1400}
        GRASP = {**REACH, "gripper": 2500}
        LIFT = {"shoulder_pan": 2048, "shoulder_lift": 1500, "elbow_flex": 2500, "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 2500}
        PLACE = {**LIFT, "shoulder_pan": 2400}
        RELEASE = {**PLACE, "gripper": 1400}

        self._enable_torque()
        try:
            for pose in [HOME, REACH, GRASP, LIFT, PLACE, RELEASE, HOME]:
                await self._smooth_move(pose, duration=0.6)
                await asyncio.sleep(0.2)
        finally:
            self._disable_torque()

    async def _exec_move(self, params: dict):
        """Move to a specific pose from params, or home."""
        if not self._follower_bus:
            raise RuntimeError("arm not connected")

        target = params.get("positions", {
            "shoulder_pan": 2048, "shoulder_lift": 1400, "elbow_flex": 3000,
            "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 2048,
        })
        self._enable_torque()
        try:
            await self._smooth_move(target, duration=1.0)
            await asyncio.sleep(0.5)
        finally:
            self._disable_torque()

    async def _smooth_move(self, target: dict, duration: float = 0.5):
        """Smoothly interpolate from current position to target over duration."""
        if not self._follower_bus:
            return
        try:
            current = self._follower_bus.sync_read("Present_Position", normalize=False)
            current_pos = {
                name: int(current[name]) if not hasattr(current[name], 'item') else int(current[name].item())
                for name in MOTOR_NAMES
            }
        except Exception:
            # Can't read current position — just write target directly
            self._write_positions(target)
            await asyncio.sleep(duration)
            return

        steps = max(1, int(duration * 30))  # 30 steps/sec
        record_every = max(1, steps // 5)  # Record ~5 frames per move
        for i in range(steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)  # Ease in-out
            pose = {
                name: int(current_pos.get(name, 2048) + (target.get(name, 2048) - current_pos.get(name, 2048)) * t)
                for name in MOTOR_NAMES
            }
            self._write_positions(pose)

            # Record frame during movement (every few steps)
            if self._recorder._open_episode_id is not None and i % record_every == 0:
                actual = self._read_all_positions()
                actual_list = list(actual.values()) if isinstance(actual, dict) and actual else list(pose.values())
                pose_list = list(pose.values())
                self._recorder.record_frame(
                    frame_index=self._recorder.frame_count,
                    timestamp=float(i) / steps * duration,
                    image=np.zeros((96, 128, 3), dtype=np.uint8),
                    joint_positions=actual_list,
                    joint_currents=[],
                    joint_temperatures=[],
                    joint_loads=[],
                    action_positions=pose_list,
                    reward=0.5,
                )

            await asyncio.sleep(duration / steps)

    def _on_law_updated(self, sender: str, law_id: str, params: dict):
        """Apply law changes from the governor."""
        if law_id == "teleop_max_fps" and "fps" in params:
            self._log(f"law: teleop FPS cap updated to {params['fps']}")
        elif law_id == "idle_timeout" and "seconds" in params:
            self._log(f"law: idle timeout updated to {params['seconds']}s")
        elif law_id == "heartbeat_interval" and "seconds" in params:
            self.heartbeat_interval = params["seconds"]
            self._log(f"law: heartbeat interval updated to {params['seconds']}s")

        # Report acknowledgment
        if self._governor_key and self._governor_addr:
            self.send_report(
                self._governor_key,
                {"type": "law_applied", "citizen": self.name, "law_id": law_id},
                self._governor_addr,
            )

    def _on_emergency_stop(self, sender: str):
        """Emergency stop — kill torque immediately."""
        self._log("EMERGENCY STOP — disabling torque NOW")
        self._add_log("SAFETY", "ESTOP", "emergency stop received")
        self._disable_torque()
        self._teleop_active = False
        self.state = "emergency_stop"

    async def stop(self):
        self._teleop_active = False
        self._disable_torque()
        if self._follower_bus:
            try:
                self._follower_bus.disconnect()
            except Exception:
                pass
        if self._uploader_task is not None:
            self._uploader_task.cancel()
            try:
                await self._uploader_task
            except asyncio.CancelledError:
                pass
            self._uploader_task = None
        await super().stop()
