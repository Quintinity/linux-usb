"""Deprecated shim — SurfaceCitizen split into GovernorCitizen + LeaderCitizen.

This re-export will be removed after Task 12.

For new code, instantiate GovernorCitizen and LeaderCitizen separately.
"""

from .governor_citizen import GovernorCitizen
from .leader_citizen import LeaderCitizen

# Motor names kept here for any importers (e.g. choreo.py) that reference
# surface_citizen.MOTOR_NAMES directly.
MOTOR_NAMES = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
]


class SurfaceCitizen(GovernorCitizen):
    """Composes Governor + Leader for hosts that still need the combined behaviour.

    New code should instantiate GovernorCitizen and LeaderCitizen separately.
    """

    def __init__(
        self,
        leader_port: str = "/dev/ttyACM1",
        teleop_fps: float = 60.0,
        auto_teleop: bool = False,
        hardware=None,
        **kwargs,
    ):
        super().__init__(hardware=hardware, **kwargs)
        self.leader_port = leader_port
        self.teleop_fps = teleop_fps

        # The leader companion is an independent citizen on the same node. It has its own identity, key, and neighbor table.
        self._leader_companion = LeaderCitizen(
            leader_port=leader_port,
            teleop_fps=teleop_fps,
            auto_teleop=auto_teleop,
            hardware=hardware,
        )

    # ── Proxy leader attrs so the Dashboard can introspect them ──

    @property
    def _teleop_active(self) -> bool:
        return self._leader_companion._teleop_active

    @_teleop_active.setter
    def _teleop_active(self, value: bool):
        self._leader_companion._teleop_active = value

    @property
    def _frames_sent(self) -> int:
        return self._leader_companion._frames_sent

    @property
    def _teleop_start(self) -> float:
        return self._leader_companion._teleop_start

    @property
    def _follower_key(self) -> str | None:
        return self._leader_companion._follower_key

    @_follower_key.setter
    def _follower_key(self, value):
        self._leader_companion._follower_key = value

    @property
    def _follower_addr(self) -> tuple | None:
        return self._leader_companion._follower_addr

    @_follower_addr.setter
    def _follower_addr(self, value):
        self._leader_companion._follower_addr = value

    async def start(self):
        await super().start()
        await self._leader_companion.start()
        self._log(f"surface governor + leader companion started on {self.leader_port}")

    async def stop(self):
        await self._leader_companion.stop()
        await super().stop()

    async def stop_teleop(self):
        """Stop the teleop loop on the companion."""
        await self._leader_companion.stop_teleop()
