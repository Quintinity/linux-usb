"""Leader citizen — reads a leader arm and emits teleop PROPOSE frames.

Runs on any node where a leader arm is physically attached. Co-located
with a follower's ManipulatorCitizen on the same node; teleop frames
go in-process via loopback multicast (or unicast directly to the
follower once neighbor discovery resolves the address).
"""

from __future__ import annotations

import asyncio
import time

from .citizen import Citizen, Neighbor, Presence
from .survey import HardwareMap, merge_capabilities

# Motor names matching SO-101 joint order
MOTOR_NAMES = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
]


class LeaderCitizen(Citizen):
    """Reads a leader arm and emits teleop PROPOSE frames.

    Responsibilities:
    - Open the Feetech bus on the leader arm port
    - Discover the follower (ManipulatorCitizen) via ADVERTISE
    - Stream teleop_frame PROPOSE messages to the follower at teleop_fps
    - Stop the loop on follower death; re-start on reconnect
    """

    def __init__(
        self,
        leader_port: str = "/dev/ttyACM1",
        teleop_fps: float = 60.0,
        auto_teleop: bool = False,
        hardware: HardwareMap | None = None,
        **kwargs,
    ):
        base_caps = ["teleop_source", "feetech_sts3215"]
        super().__init__(
            name=kwargs.pop("name", "leader"),
            citizen_type="leader",
            capabilities=merge_capabilities(base_caps, hardware),
            **kwargs,
        )
        self.hardware = hardware
        self.leader_port = leader_port
        self.teleop_fps = teleop_fps
        self._auto_teleop = auto_teleop

        # Follower discovery — set when a ManipulatorCitizen advertises
        self._follower_key: str | None = None
        self._follower_addr: tuple | None = None

        # Teleop state
        self._leader_bus = None
        self._teleop_active = False
        self._frames_sent = 0
        self._teleop_start: float = 0

        # Set to False during calibration to suppress auto-reconnect proposals
        self._reconnect_enabled: bool = True

    async def start(self):
        await super().start()
        self._log(f"leader ready — arm on {self.leader_port}")
        if self._auto_teleop:
            self._log("auto_teleop enabled — will start when follower discovered")

    # ── Neighbor lifecycle ──

    def _on_neighbor_joined(self, neighbor: Neighbor):
        """Track the first manipulator that joins; auto-propose teleop if enabled."""
        if "6dof_arm" in (neighbor.capabilities or []) and self._follower_key is None:
            self._follower_key = neighbor.pubkey
            self._follower_addr = neighbor.addr
            self._log(f"follower found: {neighbor.name}")

            if self._auto_teleop and not self._teleop_active:
                self._propose_teleop(neighbor)

    def _on_neighbor_presence_changed(self, neighbor: Neighbor, old_presence: Presence):
        """React to follower going dead or coming back."""
        if neighbor.pubkey != self._follower_key:
            return

        if neighbor.presence == Presence.PRESUMED_DEAD:
            self._log("FOLLOWER DEAD — pausing teleop")
            self._add_log("SAFETY", neighbor.name, "presumed dead — teleop paused")
            self._teleop_active = False
            self.state = "idle"

        elif neighbor.presence == Presence.DEGRADED:
            self._log(f"FOLLOWER DEGRADED — monitoring")
            self._add_log("WARNING", neighbor.name, "degraded — missed heartbeats")

        elif neighbor.presence == Presence.ONLINE and old_presence != Presence.ONLINE:
            if self._reconnect_enabled and not self._teleop_active:
                self._log("FOLLOWER BACK — re-proposing teleop")
                self._add_log("RECONNECT", neighbor.name, "back online — re-proposing teleop")
                self._propose_teleop(neighbor)

    def _propose_teleop(self, neighbor: Neighbor):
        """Send a teleop proposal to a manipulator."""
        self._log(f"proposing teleop to {neighbor.name}")
        self._follower_key = neighbor.pubkey
        self._follower_addr = neighbor.addr
        self.send_propose(
            neighbor.pubkey,
            {"task": "teleop", "source": "leader_arm", "fps": self.teleop_fps},
            neighbor.addr,
        )

    # ── Inbound message handlers ──

    def _handle_report(self, env, addr):
        """Handle REPORT messages — halt teleop immediately on fault from follower."""
        super()._handle_report(env, addr)

        body = env.body
        report_type = body.get("type", "unknown")

        if report_type == "fault":
            detail = body.get("detail", "unknown")
            self._log(f"FAULT from [{env.sender[:8]}]: {detail}")
            self._add_log("FAULT", env.sender[:8], detail)
            if env.sender == self._follower_key and self._teleop_active:
                self._teleop_active = False
                self.state = "idle"

    def _handle_accept_reject(self, env, addr):
        body = env.body
        task_name = body.get("task", "")

        if body.get("accepted") and task_name == "teleop":
            self._log("follower ACCEPTED teleop — starting arm read loop")
            self._add_log("ACCEPT", env.sender[:8], "teleop accepted")
            self._follower_key = env.sender
            self._follower_addr = addr
            self._teleop_active = True
            self._frames_sent = 0
            self._teleop_start = time.time()
            self.state = "teleop"
            self._tasks.append(asyncio.create_task(self._teleop_loop()))
        elif not body.get("accepted"):
            reason = body.get("reason", "unknown")
            self._log(f"follower REJECTED: {reason}")
            self._add_log("REJECT", env.sender[:8], reason)
            if env.sender == self._follower_key:
                self._follower_key = None
                self._follower_addr = None

    # ── Teleop loop ──

    async def _teleop_loop(self):
        """Read leader arm and stream positions to follower."""
        interval = 1.0 / self.teleop_fps

        bus = self._init_leader_bus()
        if bus is None:
            self._log("leader arm init failed — teleop aborted")
            self._teleop_active = False
            self.state = "idle"
            return

        self._log(f"teleop streaming at {self.teleop_fps} FPS")

        try:
            while self._teleop_active and self._running:
                t0 = time.time()

                # Check follower presence
                if self._follower_key and self._follower_key in self.neighbors:
                    n = self.neighbors[self._follower_key]
                    if n.presence == Presence.PRESUMED_DEAD:
                        self._log("follower presumed dead — stopping teleop")
                        break

                positions = self._read_leader_positions(bus)
                if positions and self._follower_key and self._follower_addr:
                    self.send_teleop(self._follower_key, positions, self._follower_addr)
                    self._frames_sent += 1

                    if self._frames_sent % 300 == 0:
                        elapsed = time.time() - self._teleop_start
                        fps = self._frames_sent / elapsed if elapsed > 0 else 0
                        self._log(f"teleop: {self._frames_sent} frames, {fps:.1f} avg FPS")

                elapsed = time.time() - t0
                sleep_time = max(0, interval - elapsed)
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            pass
        finally:
            self._cleanup_leader_bus(bus)
            self._teleop_active = False
            self.state = "idle"
            self._log(f"teleop ended — {self._frames_sent} frames sent")

    def _init_leader_bus(self):
        """Initialize the Feetech servo bus for the leader arm."""
        try:
            from lerobot.motors.feetech.feetech import FeetechMotorsBus
            from lerobot.motors.motors_bus import Motor, MotorNormMode

            motors = {
                name: Motor(i + 1, "sts3215",
                            MotorNormMode.RANGE_0_100 if name == "gripper" else MotorNormMode.RANGE_M100_100)
                for i, name in enumerate(MOTOR_NAMES)
            }
            bus = FeetechMotorsBus(port=self.leader_port, motors=motors)
            bus.connect()
            self._log(f"leader bus connected on {self.leader_port}")
            return bus
        except Exception as e:
            self._log(f"leader bus error: {e}")
            return None

    def _read_leader_positions(self, bus) -> dict | None:
        """Read current positions from all leader arm motors."""
        try:
            positions = bus.sync_read("Present_Position", normalize=False, num_retry=3)
            return {
                name: int(positions[name]) if not hasattr(positions[name], 'item')
                else int(positions[name].item())
                for name in MOTOR_NAMES
            }
        except Exception:
            return None

    def _cleanup_leader_bus(self, bus):
        try:
            if bus:
                bus.disconnect()
        except Exception:
            pass

    async def stop_teleop(self):
        """Stop the teleop loop."""
        self._teleop_active = False
        self.state = "idle"

    async def stop(self):
        self._teleop_active = False
        await super().stop()
