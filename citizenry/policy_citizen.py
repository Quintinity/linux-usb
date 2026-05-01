"""PolicyCitizen — wraps a runner (e.g. SmolVLARunner) and bids on
manipulation tasks via the marketplace.

Co-location preferred: when the target follower's node_pubkey matches
this citizen's node_pubkey, the bid score includes the spec's +0.15
bonus. Cross-node bids are valid but unbonused.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import numpy as np

from .citizen import Citizen
from .marketplace import Bid, Task, TaskStatus, compute_bid_score
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
            # Smell #5 fix: marketplace must suppress co-location bonus if our
            # node_pubkey is in the stale set populated by GOVERN(rotate_node_key).
            bidder_node_pubkey=self.node_pubkey,
            stale_node_pubkeys=self.stale_node_pubkeys,
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

        Reads cameras + state from the ObservationCache (populated by the base
        Citizen handlers as ADVERTISE/REPORT bodies arrive), calls runner.act(),
        emits PROPOSE(teleop_frame, ttl=0.1) per action step.

        When the observation is stale or missing (e.g. no cameras have pushed
        frames yet), the loop sleeps and retries until either the data shows up
        or the task is cancelled — black-input inference is never sent to the
        runner.
        """
        self._active_task_id = task.id
        # Free-text instruction passed to SmolVLA's language path. Falls back to
        # an empty string so the model has something to tokenize even when the
        # marketplace task didn't carry one.
        task_text = str(
            task.params.get("text")
            or task.params.get("instruction")
            or task.params.get("prompt")
            or ""
        )
        # Diagnostic counters — surfaced once per second so a stuck loop or
        # a chronically-empty observation cache shows up in the journal even
        # when the manipulator's own per-300-frames counter hasn't tripped.
        n_iter = 0
        n_emit = 0
        n_obs_none = 0
        last_log = 0.0
        self._last_obs_miss = ""
        loop = asyncio.get_event_loop()
        try:
            while self._active_task_id == task.id:
                n_iter += 1
                obs = await self._assemble_observation(target_follower_pubkey)
                if obs is None:
                    n_obs_none += 1
                    await asyncio.sleep(0.05)
                else:
                    # Offload the model forward pass to a worker thread so the
                    # event loop keeps draining incoming sensor REPORTs while
                    # the cold-start ~1.5s chunk inference is in flight. After
                    # the queue is primed, subsequent calls are <50ms anyway.
                    chunk = await asyncio.to_thread(
                        self.runner.act, obs, task_text
                    )  # shape (T, D), in ticks
                    for action_row in chunk:
                        if self._active_task_id != task.id:
                            break
                        await self._emit_teleop(
                            action_row,
                            target_follower_pubkey,
                            current_state=obs.get("observation.state"),
                        )
                        n_emit += 1
                        await asyncio.sleep(1.0 / 30.0)  # ~30 Hz
                now = loop.time()
                if now - last_log >= 1.0:
                    miss = f" miss=[{self._last_obs_miss}]" if self._last_obs_miss else ""
                    self._log(
                        f"task [{task.id[:8]}] progress: iter={n_iter} emit={n_emit} "
                        f"obs_none={n_obs_none}{miss}"
                    )
                    last_log = now
        finally:
            self._active_task_id = None

    # Staleness window for cached frames + state. Set generously because:
    #   - SmolVLA's first cold forward pass takes ~1.5s on Orin Nano,
    #   - torch CUDA ops hold the GIL and don't release reliably even when
    #     wrapped in asyncio.to_thread, so inbound REPORTs can backlog,
    #   - manipulator telemetry runs at 2 Hz so the cache is naturally
    #     populated only every 500 ms even on a healthy link.
    # The manipulator-side teleop watchdog still enforces real safety on the
    # arm; this knob just decides "is the policy's view fresh enough to feed
    # to the model" and a stale-but-real state is far better than blocking.
    OBS_MAX_AGE_S: float = 30.0

    async def _assemble_observation(self, target_follower_pubkey: str) -> dict[str, Any] | None:
        """Pull the latest frame from each named camera + state from the target
        follower's last REPORT. Returns None when state OR all camera roles are
        stale/missing — caller's loop will retry rather than feed black pixels
        into the model.

        Inputs come from ``self.observations`` (an ObservationCache populated
        transparently by the Citizen base handlers).

        Secondary camera is optional. If it's stale, the primary frame is used
        for both slots — the SmolVLA runner expands to whatever camera count
        the model expects, and a duplicated real frame is always preferable to
        a black input.
        """
        primary_role, secondary_role = self.camera_role_pair()
        primary = self.observations.latest_frame(primary_role, max_age_s=self.OBS_MAX_AGE_S)
        secondary = self.observations.latest_frame(secondary_role, max_age_s=self.OBS_MAX_AGE_S)
        state = self.observations.latest_state(target_follower_pubkey, max_age_s=self.OBS_MAX_AGE_S)
        if state is None or primary is None:
            # Surface which leg is missing so an empty cache after a long
            # inference doesn't silently retry forever. Includes the actual
            # age of any present-but-too-old entry so we can tell the
            # difference between "never received" and "received but stale".
            import time as _t
            now_s = _t.time()
            f_age = (
                f"{(now_s - self.observations._frames[primary_role].timestamp):.2f}s"
                if primary_role in self.observations._frames else "MISS"
            )
            s_age = (
                f"{(now_s - self.observations._states[target_follower_pubkey].timestamp):.2f}s"
                if target_follower_pubkey in self.observations._states else "MISS"
            )
            self._last_obs_miss = (
                f"state={'OK' if state is not None else 'STALE'} (age={s_age}) "
                f"frame[{primary_role}]={'OK' if primary is not None else 'STALE'} (age={f_age}) "
                f"frames_cached={list(self.observations._frames.keys())}"
            )
            return None
        if secondary is None:
            secondary = primary
        return {
            f"observation.images.{primary_role}": primary,
            f"observation.images.{secondary_role}": secondary,
            "observation.state": state.astype(np.float32),
        }

    # Cap each motor's per-frame delta so a wild model output can't yank the
    # arm into a high-load collision faster than the safety load-watchdog can
    # react. 80 ticks at 30 Hz is ~2400 ticks/s — covers any real motion path
    # the SO-101 needs but bounds the worst-case slew rate.
    MAX_DELTA_TICKS_PER_FRAME: int = 80

    async def _emit_teleop(
        self,
        action_row: np.ndarray,
        target_follower_pubkey: str,
        current_state: np.ndarray | None = None,
    ) -> None:
        if len(action_row) < len(MOTOR_NAMES):
            self._log(
                f"policy: action_row has {len(action_row)} dims, expected {len(MOTOR_NAMES)}; dropping frame"
            )
            return
        # Action rows arrive in servo ticks (denormalized inside the runner).
        # Apply a per-frame slew cap relative to the last known state so a
        # wild prediction can't be the first thing that hits the motors.
        target = np.asarray(action_row, dtype=np.float32)
        if current_state is not None:
            cs = np.asarray(current_state, dtype=np.float32).reshape(-1)
            if len(cs) >= len(MOTOR_NAMES):
                delta = target[: len(MOTOR_NAMES)] - cs[: len(MOTOR_NAMES)]
                cap = float(self.MAX_DELTA_TICKS_PER_FRAME)
                delta = np.clip(delta, -cap, cap)
                target = cs[: len(MOTOR_NAMES)] + delta

        positions = {
            name: int(round(float(target[i])))
            for i, name in enumerate(MOTOR_NAMES)
        }
        # Resolve the follower's unicast address from the neighbor table.
        addr = self._neighbor_addr(target_follower_pubkey)
        if addr is None:
            self._log(f"policy: no addr for follower {target_follower_pubkey[:8]}; skipping frame")
            return
        # Inherited helper: builds {"task":"teleop_frame","positions":...} with TTL_TELEOP=0.1
        self.send_teleop(target_follower_pubkey, positions, addr)
        # Log a sample of every ~30th emitted frame so we can see the actual
        # tick values the model is targeting without flooding the journal.
        self._frames_emitted_total = getattr(self, "_frames_emitted_total", 0) + 1
        if self._frames_emitted_total % 30 == 0:
            self._log(
                f"policy: emit #{self._frames_emitted_total} → "
                + " ".join(f"{k}={v}" for k, v in positions.items())
            )

    def _neighbor_addr(self, pubkey: str) -> tuple | None:
        """Look up a neighbor's unicast (host, port) by pubkey."""
        n = self.neighbors.get(pubkey)
        if n is None:
            return None
        return getattr(n, "addr", None)

    # --- Direct-trigger PROPOSE handler ---
    #
    # Marketplace bidding for policy citizens isn't fully wired up yet — the
    # governor doesn't pair tasks with manipulator targets, and policies
    # don't have a place in the existing manipulator auction protocol. To
    # unblock end-to-end demos, we accept a direct PROPOSE of the form:
    #
    #   {"task": "imitation_run",
    #    "task_id":  "<id>",
    #    "target_follower_pubkey": "<hex pubkey>",
    #    "text": "<prompt>",
    #    "duration_s": <float, optional>}
    #
    # The handler claims the target follower for teleop and runs the
    # existing inference + denorm + emit loop until the duration elapses
    # or a stop is requested.

    DEFAULT_RUN_DURATION_S: float = 10.0

    def _handle_propose(self, env, addr):
        body = env.body or {}
        task = body.get("task", "")
        if task == "imitation_run":
            asyncio.get_event_loop().create_task(
                self._run_imitation_from_propose(env, addr, body)
            )

    async def _run_imitation_from_propose(self, env, addr, body: dict) -> None:
        target_pubkey = body.get("target_follower_pubkey", "") or ""
        text = str(body.get("text", "") or "")
        duration_s = float(body.get("duration_s", self.DEFAULT_RUN_DURATION_S))
        task_id = body.get("task_id") or "imitation-" + os.urandom(4).hex()

        target_addr = self._neighbor_addr(target_pubkey)
        if not target_pubkey or target_addr is None:
            self._log(
                f"imitation_run [{task_id}]: no addr for follower "
                f"{target_pubkey[:8] if target_pubkey else '<empty>'}"
            )
            return

        if self._active_task_id is not None:
            self._log(
                f"imitation_run [{task_id}]: another task {self._active_task_id} "
                f"is already running; rejecting"
            )
            return

        # Claim the follower for teleop. Manipulator's _handle_teleop_proposal
        # enables torque + sets governor_key (the policy in this case) as the
        # only sender it will accept frames from.
        self.send_propose(
            target_pubkey,
            {"task": "teleop", "source": "policy_imitation", "fps": 30},
            target_addr,
        )
        # Give the manipulator a beat to enable torque before the first frame.
        await asyncio.sleep(0.4)

        fake_task = Task(
            id=task_id,
            type="imitation_run",
            params={"text": text, "target_follower_pubkey": target_pubkey},
            status=TaskStatus.EXECUTING,
        )
        self._log(
            f"imitation_run [{task_id}] starting — target {target_pubkey[:8]}, "
            f"duration {duration_s:.1f}s, prompt={text!r}"
        )

        async def _stop_later():
            await asyncio.sleep(duration_s)
            if self._active_task_id == task_id:
                self._active_task_id = None
                self._log(f"imitation_run [{task_id}]: duration elapsed, stopping")

        stop_task = asyncio.get_event_loop().create_task(_stop_later())
        try:
            await self.execute_task(fake_task, target_pubkey)
        finally:
            stop_task.cancel()
            self._log(f"imitation_run [{task_id}] complete")
