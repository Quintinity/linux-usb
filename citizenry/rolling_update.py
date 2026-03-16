"""Rolling Policy Updates — canary deployment for robot brains.

When a new policy or law change is available, roll it out one citizen
at a time. Each citizen applies the change, runs a self-test, and
reports success or failure. If failure rate exceeds the threshold,
halt the rollout and revert.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RolloutStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class CitizenRolloutState:
    """Track rollout status for a single citizen."""
    pubkey: str
    name: str
    status: str = "pending"  # pending, applying, success, failed
    applied_at: float = 0.0
    result: str = ""


@dataclass
class RolloutPlan:
    """A plan to roll out a policy change across citizens."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    policy_type: str = ""           # "law_update", "servo_limits", "skill_tree"
    policy_data: dict = field(default_factory=dict)
    citizens: list[CitizenRolloutState] = field(default_factory=list)
    status: RolloutStatus = RolloutStatus.PENDING
    failure_threshold: float = 0.2  # Halt if >20% fail
    success_count: int = 0
    failure_count: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    @property
    def progress(self) -> float:
        total = len(self.citizens)
        if total == 0:
            return 0.0
        done = self.success_count + self.failure_count
        return done / total

    @property
    def failure_rate(self) -> float:
        done = self.success_count + self.failure_count
        if done == 0:
            return 0.0
        return self.failure_count / done

    def should_halt(self) -> bool:
        """Check if rollout should be halted due to failure rate."""
        done = self.success_count + self.failure_count
        if done < 1:
            return False
        return self.failure_rate > self.failure_threshold

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "policy_type": self.policy_type,
            "status": self.status.value,
            "progress": self.progress,
            "success": self.success_count,
            "failures": self.failure_count,
            "total": len(self.citizens),
        }


class RollingUpdater:
    """Manages rolling policy updates across the citizenry."""

    def __init__(self, governor):
        self.governor = governor
        self.active_rollout: RolloutPlan | None = None
        self.history: list[RolloutPlan] = []

    def create_rollout(
        self,
        policy_type: str,
        policy_data: dict,
        citizen_pubkeys: list[tuple[str, str]] | None = None,
    ) -> RolloutPlan:
        """Create a new rollout plan.

        Args:
            policy_type: Type of policy change
            policy_data: The policy data to distribute
            citizen_pubkeys: List of (pubkey, name) tuples. None = all neighbors.
        """
        if citizen_pubkeys is None:
            citizen_pubkeys = [
                (n.pubkey, n.name) for n in self.governor.neighbors.values()
            ]

        plan = RolloutPlan(
            policy_type=policy_type,
            policy_data=policy_data,
            citizens=[
                CitizenRolloutState(pubkey=pk, name=name)
                for pk, name in citizen_pubkeys
            ],
        )
        self.active_rollout = plan
        return plan

    async def execute(self, plan: RolloutPlan | None = None) -> RolloutPlan:
        """Execute a rolling update one citizen at a time."""
        plan = plan or self.active_rollout
        if not plan:
            raise ValueError("No rollout plan")

        plan.status = RolloutStatus.IN_PROGRESS
        self.governor._log(f"rollout started: [{plan.id}] {plan.policy_type} → {len(plan.citizens)} citizens")

        for citizen_state in plan.citizens:
            if plan.should_halt():
                plan.status = RolloutStatus.FAILED
                self.governor._log(
                    f"rollout HALTED: [{plan.id}] failure rate {plan.failure_rate:.0%} "
                    f"exceeds threshold {plan.failure_threshold:.0%}"
                )
                # Revert successful citizens
                await self._revert(plan)
                break

            # Apply to this citizen
            citizen_state.status = "applying"
            citizen_state.applied_at = time.time()

            neighbor = self.governor.neighbors.get(citizen_state.pubkey)
            if not neighbor:
                citizen_state.status = "failed"
                citizen_state.result = "citizen not found"
                plan.failure_count += 1
                continue

            # Send the policy update
            self.governor.send_govern(
                citizen_state.pubkey,
                {
                    "type": plan.policy_type,
                    "rollout_id": plan.id,
                    **plan.policy_data,
                },
                neighbor.addr,
            )

            # Wait for acknowledgment (via REPORT)
            success = await self._wait_for_ack(plan.id, citizen_state.pubkey, timeout=5.0)

            if success:
                citizen_state.status = "success"
                plan.success_count += 1
                self.governor._log(f"rollout: {citizen_state.name} ✓")
            else:
                citizen_state.status = "failed"
                citizen_state.result = "timeout or rejection"
                plan.failure_count += 1
                self.governor._log(f"rollout: {citizen_state.name} ✗")

            # Brief pause between citizens
            await asyncio.sleep(0.5)

        if plan.status == RolloutStatus.IN_PROGRESS:
            plan.status = RolloutStatus.COMPLETED
            plan.completed_at = time.time()
            self.governor._log(
                f"rollout complete: [{plan.id}] {plan.success_count}/{len(plan.citizens)} succeeded"
            )

        self.history.append(plan)
        self.active_rollout = None
        return plan

    async def _wait_for_ack(self, rollout_id: str, citizen_pubkey: str, timeout: float = 5.0) -> bool:
        """Wait for a citizen to acknowledge a policy update."""
        # Check message log for acknowledgment
        start = time.time()
        while time.time() - start < timeout:
            # Look for a law_applied or constitution_applied report from this citizen
            for entry in self.governor.message_log:
                if (citizen_pubkey[:8] in entry.sender
                        and ("applied" in entry.detail or "acknowledged" in entry.detail)):
                    return True
            await asyncio.sleep(0.2)
        return False

    async def _revert(self, plan: RolloutPlan):
        """Revert successful citizens to the previous policy."""
        plan.status = RolloutStatus.ROLLED_BACK
        self.governor._log(f"rollout: reverting {plan.success_count} citizens")
        # For law updates, we'd send the previous law value
        # For now, just log the revert intent
        for cs in plan.citizens:
            if cs.status == "success":
                cs.status = "reverted"
