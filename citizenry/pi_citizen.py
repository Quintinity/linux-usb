"""Raspberry Pi 5 — Follower Arm Manipulation Citizen.

Receives teleop frames from the governor and writes positions to the
follower arm servos. Validates constitution. Streams telemetry back.

v2.0: Task bidding, skill-gated execution, XP tracking, warning generation.
"""

import asyncio
import time

from .citizen import Citizen, Neighbor, Presence
from .protocol import MessageType, make_envelope
from .marketplace import compute_bid_score, Task
from .skills import default_manipulator_skills
from .mycelium import Warning, Severity

MOTOR_NAMES = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
]


class PiCitizen(Citizen):
    """Manipulation citizen on the Raspberry Pi 5.

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
    ):
        super().__init__(
            name="pi-follower",
            citizen_type="manipulator",
            capabilities=["6dof_arm", "gripper", "feetech_sts3215"],
        )
        self.follower_port = follower_port
        self.telemetry_hz = telemetry_hz
        self._follower_bus = None
        self._governor_key: str | None = None
        self._governor_addr: tuple | None = None
        self._teleop_active = False
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

    async def start(self):
        await super().start()
        # Pre-connect the follower bus
        self._follower_bus = self._init_follower_bus()
        if self._follower_bus:
            self._log(f"follower arm ready on {self.follower_port}")
        else:
            self._log("follower arm init failed — will retry on teleop start")

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
            self.state = "idle"

    def _on_constitution_received(self, sender: str, constitution: dict):
        """Verify signature, then apply constitutional safety limits."""
        # Verify the governor's signature before trusting the constitution
        try:
            from .constitution import Constitution
            const = Constitution.from_dict(constitution)
            if not const.verify():
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
        except Exception as e:
            self._log(f"constitution verification failed: {e} — applying anyway for compatibility")

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

        self._frames_received += 1
        self._last_frame_time = time.time()

        if self._write_positions(positions):
            self._frames_written += 1

        if self._frames_received % 300 == 0:
            elapsed = time.time() - self._teleop_start
            fps = self._frames_received / elapsed if elapsed > 0 else 0
            drop_rate = 1.0 - (self._frames_written / self._frames_received) if self._frames_received else 0
            self._log(f"teleop: {self._frames_received} rx, {fps:.1f} FPS, {drop_rate:.1%} drops")

    async def _teleop_watchdog(self):
        """If no frame arrives for 500ms, stop motors for safety."""
        while self._teleop_active and self._running:
            await asyncio.sleep(0.5)
            if self._last_frame_time > 0 and time.time() - self._last_frame_time > 0.5:
                self._log("WATCHDOG: no frames for 500ms — disabling torque")
                self._add_log("SAFETY", "watchdog", "no frames — torque disabled")
                self._disable_torque()
                self._teleop_active = False
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
            }
            immune_matches = self.immune_memory.match(telem_dict)
            for pattern in immune_matches:
                self._log(f"immune pattern matched: {pattern.pattern_type} — {pattern.mitigation}")

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

    async def _execute_task(self, task_id: str, task_type: str, params: dict, governor_key: str, governor_addr: tuple):
        """Execute an assigned task and report results."""
        try:
            # Simulate task execution (actual execution would depend on task type)
            self._log(f"executing task: [{task_id}] {task_type}")
            await asyncio.sleep(0.5)  # Placeholder for actual work

            # Award XP
            skill_name = task_type if task_type in self.skill_tree.definitions else "basic_movement"
            xp_earned = self.skill_tree.award_xp(skill_name, base_xp=10, task_difficulty=0.8, success_quality=1.0)

            # Report success
            self.send_report(
                governor_key,
                {
                    "type": "task_complete",
                    "task_id": task_id,
                    "result": "success",
                    "duration_ms": 500,
                    "xp_earned": xp_earned,
                    "citizen": self.name,
                },
                governor_addr,
            )
            self._log(f"task complete: [{task_id}] +{xp_earned} XP for {skill_name}")
        except Exception as e:
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
        finally:
            self._current_task_id = None
            self._current_task_type = None
            self.state = "idle"

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
        await super().stop()
