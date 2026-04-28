"""PolicyCitizen — wraps a runner (e.g. SmolVLARunner) and bids on
manipulation tasks via the marketplace.

Co-location preferred: when the target follower's node_pubkey matches
this citizen's node_pubkey, the bid score includes the spec's +0.15
bonus. Cross-node bids are valid but unbonused.
"""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np

from .citizen import Citizen
from .marketplace import Bid, Task, compute_bid_score
from .skills import default_policy_skills

CO_LOCATION_BONUS = 0.15

MOTOR_NAMES = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
]


class PolicyCitizen(Citizen):
    def __init__(
        self,
        runner,                             # SmolVLARunner-like
        observation_cameras: tuple[str, str] = ("wrist", "base"),
        **kwargs,
    ):
        super().__init__(
            name=kwargs.pop("name", "policy"),
            citizen_type="policy",
            capabilities=kwargs.pop("capabilities", ["policy.imitation", "vla.smolvla_base", "cuda_inference"]),
            **kwargs,
        )
        self.runner = runner
        self.skill_tree.merge_definitions(default_policy_skills())
        # Award baseline XP so the skill is reported as level 1
        self.skill_tree.award_xp("imitation:smolvla_base", base_xp=10)
        # Default — overridden at runtime by the Constitution Law
        # policy_citizen.observation_cameras (see camera_role_pair() below).
        self._default_observation_cameras = observation_cameras
        self._active_task_id: str | None = None
        self._action_loop_task: asyncio.Task | None = None

    # --- Camera selection ---

    def camera_role_pair(self) -> tuple[str, str]:
        """Resolve the active [primary, secondary] camera role names from the
        Constitution Law policy_citizen.observation_cameras, falling back to
        the constructor default.
        """
        v = self._law("policy_citizen.observation_cameras",
                      default=list(self._default_observation_cameras))
        if not isinstance(v, (list, tuple)) or len(v) < 2:
            return self._default_observation_cameras
        return (v[0], v[1])

    # --- Bidding ---

    def build_bid(
        self,
        task: Task,
        target_follower_pubkey: str,
        target_follower_node_pubkey: str,
    ) -> Bid | None:
        """Produce a Bid for the given task targeting a specific follower.

        Returns None when this citizen is ineligible.
        """
        # Capability gate — claim manipulator caps on behalf of the targeted follower
        for cap in task.required_capabilities:
            if cap not in self._available_capabilities_for_follower(target_follower_pubkey):
                return None
        # Skill gate — heuristic: refuse manipulation skills we don't claim explicitly
        for sk in task.required_skills:
            if not self.skill_tree.has_skill(sk):
                # Allow common manipulation skills via our generic imitation
                if sk not in {"pick_and_place", "imitation:smolvla_base"}:
                    return None
        skill_level = self.skill_tree.skill_level("imitation:smolvla_base")
        bonus = (CO_LOCATION_BONUS
                 if target_follower_node_pubkey == self.node_pubkey else 0.0)
        score = compute_bid_score(
            skill_level=skill_level,
            current_load=0.0,
            health=self.health,
            fatigue=0.0,
            co_location_bonus=bonus,
        )
        return Bid(
            citizen_pubkey=self.pubkey,
            task_id=task.id,
            score=score,
            skill_level=skill_level,
            current_load=0.0,
            health=self.health,
            estimated_duration=float(task.params.get("estimated_duration", 5.0)),
            node_pubkey=self.node_pubkey,
            target_follower_pubkey=target_follower_pubkey,
        )

    def _available_capabilities_for_follower(self, target_follower_pubkey: str = "") -> list[str]:
        """Caps the policy can satisfy on behalf of the follower.

        When a target follower's neighbor entry is known, claim ITS advertised
        capabilities. When the follower isn't on the network yet, fall back to
        a conservative manipulator-arm default.
        """
        out = list(self.capabilities)
        n = self.neighbors.get(target_follower_pubkey) if target_follower_pubkey else None
        if n is not None and getattr(n, "capabilities", None):
            for cap in n.capabilities:
                if cap not in out:
                    out.append(cap)
        else:
            # Follower not yet known — conservative default
            out.extend(["6dof_arm", "gripper"])
        return out

    # --- Action loop ---

    async def execute_task(self, task: Task, target_follower_pubkey: str) -> None:
        """Drive the follower for the duration of the task.

        Reads cameras + state from neighbor REPORTs, calls runner.act(),
        emits PROPOSE(teleop_frame, ttl=0.1) per action step.
        """
        self._active_task_id = task.id
        try:
            while self._active_task_id == task.id:
                obs = await self._assemble_observation()  # TODO: returns stub zeros until camera-cache layer lands
                if obs is None:
                    await asyncio.sleep(0.05)
                    continue
                chunk = self.runner.act(obs)  # shape (T, D)
                for action_row in chunk:
                    if self._active_task_id != task.id:
                        break
                    await self._emit_teleop(action_row, target_follower_pubkey)
                    await asyncio.sleep(1.0 / 30.0)  # ~30 Hz
        finally:
            self._active_task_id = None

    async def _assemble_observation(self) -> dict[str, Any] | None:
        """Pull the latest frame from each named camera neighbor + state from
        the target follower's last REPORT. Returns None if observation is stale.

        Real production wiring: the camera neighbors push frames via ADVERTISE
        and PolicyCitizen caches the latest. For now this returns a stub
        observation — real wiring lands when the camera-frame caching layer
        is built (out of Task 9 scope).
        """
        return {
            "observation.images.wrist": np.zeros((96, 128, 3), dtype=np.uint8),
            "observation.images.base":  np.zeros((96, 128, 3), dtype=np.uint8),
            "observation.state": np.zeros(6, dtype=np.float32),
        }

    async def _emit_teleop(self, action_row: np.ndarray, target_follower_pubkey: str) -> None:
        if len(action_row) < len(MOTOR_NAMES):
            self._log(
                f"policy: action_row has {len(action_row)} dims, expected {len(MOTOR_NAMES)}; dropping frame"
            )
            return
        # Build positions dict matching the existing wire format that
        # ManipulatorCitizen accepts (see Citizen.send_teleop in citizen.py).
        # Positions are integer servo ticks keyed by motor name.
        positions = {
            name: int(round(float(action_row[i])))
            for i, name in enumerate(MOTOR_NAMES)
        }
        # Resolve the follower's unicast address from the neighbor table.
        addr = self._neighbor_addr(target_follower_pubkey)
        if addr is None:
            self._log(f"policy: no addr for follower {target_follower_pubkey[:8]}; skipping frame")
            return
        # Inherited helper: builds {"task":"teleop_frame","positions":...} with TTL_TELEOP=0.1
        self.send_teleop(target_follower_pubkey, positions, addr)

    def _neighbor_addr(self, pubkey: str) -> tuple | None:
        """Look up a neighbor's unicast (host, port) by pubkey."""
        n = self.neighbors.get(pubkey)
        if n is None:
            return None
        return getattr(n, "addr", None)
