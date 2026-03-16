"""Task Marketplace — auction-based task allocation.

Citizens bid on tasks via PROPOSE/ACCEPT_REJECT. The governor (or any
coordinator) selects the winning bid based on composite score.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    PENDING = "pending"
    BIDDING = "bidding"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """A unit of work that can be auctioned to citizens."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    priority: float = 0.5
    required_capabilities: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None
    result: dict | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    broadcast_count: int = 0
    max_broadcasts: int = 3

    def to_propose_body(self) -> dict:
        """Convert to a PROPOSE message body."""
        return {
            "task": self.type,
            "task_id": self.id,
            "priority": self.priority,
            "required_capabilities": self.required_capabilities,
            "required_skills": self.required_skills,
            "params": self.params,
        }

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_propose_body(cls, body: dict) -> Task:
        return cls(
            id=body.get("task_id", uuid.uuid4().hex[:12]),
            type=body.get("task", ""),
            params=body.get("params", {}),
            priority=body.get("priority", 0.5),
            required_capabilities=body.get("required_capabilities", []),
            required_skills=body.get("required_skills", []),
        )


@dataclass
class Bid:
    """A citizen's bid on a task."""

    citizen_pubkey: str
    task_id: str
    score: float = 0.0
    skill_level: int = 0
    current_load: float = 0.0
    health: float = 1.0
    estimated_duration: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_accept_body(cls, body: dict, sender_pubkey: str) -> Bid:
        bid_data = body.get("bid", {})
        return cls(
            citizen_pubkey=sender_pubkey,
            task_id=body.get("task_id", ""),
            score=bid_data.get("score", 0.0),
            skill_level=bid_data.get("skill_level", 0),
            current_load=bid_data.get("load", 0.0),
            health=bid_data.get("health", 1.0),
            estimated_duration=bid_data.get("estimated_duration", 0.0),
        )


# Default scoring weights — configurable via governor laws
DEFAULT_WEIGHTS = {
    "capability": 0.4,
    "availability": 0.3,
    "health": 0.3,
}


def compute_bid_score(
    skill_level: int,
    current_load: float,
    health: float,
    fatigue: float = 0.0,
    weights: dict[str, float] | None = None,
) -> float:
    """Compute composite bid score with fatigue modifier.

    score = (capability_weight * (skill_level / 10)
           + availability_weight * (1 - load)
           + health_weight * health) * (1.0 - 0.3 * fatigue)

    All components normalized to [0, 1]. Skill level capped at 10.
    Fatigue reduces the score by up to 30% (FR-4.3).
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    skill_norm = min(skill_level, 10) / 10.0
    avail = max(0.0, 1.0 - current_load)
    h = max(0.0, min(1.0, health))
    base = w["capability"] * skill_norm + w["availability"] * avail + w["health"] * h
    fatigue_modifier = 1.0 - 0.3 * max(0.0, min(1.0, fatigue))
    return base * fatigue_modifier


def select_winner(bids: list[Bid]) -> Bid | None:
    """Select the winning bid. Highest score wins; deterministic tiebreak."""
    if not bids:
        return None
    # Sort by score descending, then by pubkey hash ascending for tiebreak
    return sorted(
        bids,
        key=lambda b: (-b.score, hashlib.sha256(b.citizen_pubkey.encode()).hexdigest()),
    )[0]


class TaskMarketplace:
    """Manages the lifecycle of tasks and their auctions."""

    def __init__(self, bid_timeout: float = 2.0):
        self.bid_timeout = bid_timeout
        self.tasks: dict[str, Task] = {}
        self.bids: dict[str, list[Bid]] = {}  # task_id → bids
        self.completed_tasks: list[Task] = []

    def create_task(
        self,
        task_type: str,
        params: dict | None = None,
        priority: float = 0.5,
        required_capabilities: list[str] | None = None,
        required_skills: list[str] | None = None,
    ) -> Task:
        """Create a new task and put it in bidding state."""
        task = Task(
            type=task_type,
            params=params or {},
            priority=priority,
            required_capabilities=required_capabilities or [],
            required_skills=required_skills or [],
            status=TaskStatus.BIDDING,
        )
        self.tasks[task.id] = task
        self.bids[task.id] = []
        return task

    def add_bid(self, bid: Bid) -> bool:
        """Add a bid for a task. Returns False if task not in bidding state."""
        task = self.tasks.get(bid.task_id)
        if not task or task.status != TaskStatus.BIDDING:
            return False
        self.bids.setdefault(bid.task_id, []).append(bid)
        return True

    def close_auction(self, task_id: str, weights: dict | None = None) -> Bid | None:
        """Close bidding and select a winner. Returns winning bid or None."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        bids = self.bids.get(task_id, [])
        winner = select_winner(bids)
        if winner:
            task.status = TaskStatus.ASSIGNED
            task.assigned_to = winner.citizen_pubkey
        else:
            task.status = TaskStatus.PENDING  # No bids — can re-broadcast
            task.broadcast_count += 1
        return winner

    def start_execution(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.ASSIGNED:
            task.status = TaskStatus.EXECUTING
            return True
        return False

    def complete_task(self, task_id: str, result: dict | None = None) -> bool:
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.EXECUTING:
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()
            self.completed_tasks.append(task)
            return True
        return False

    def fail_task(self, task_id: str, reason: str = "") -> Task | None:
        """Mark task as failed and return it for re-auction if eligible."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        task.status = TaskStatus.FAILED
        task.result = {"error": reason}
        # Re-auction if under max broadcasts
        if task.broadcast_count < task.max_broadcasts:
            task.status = TaskStatus.BIDDING
            task.assigned_to = None
            self.bids[task.id] = []
            return task
        return None

    def get_active_tasks(self) -> list[Task]:
        return [t for t in self.tasks.values() if t.status in (
            TaskStatus.BIDDING, TaskStatus.ASSIGNED, TaskStatus.EXECUTING
        )]

    def can_citizen_bid(
        self,
        task: Task,
        citizen_capabilities: list[str],
        citizen_skills: list[str],
        citizen_load: float,
        citizen_health: float,
    ) -> tuple[bool, str]:
        """Check if a citizen is eligible to bid on a task."""
        # Check capabilities
        for cap in task.required_capabilities:
            if cap not in citizen_capabilities:
                return False, f"missing capability: {cap}"
        # Check skills
        for skill in task.required_skills:
            if skill not in citizen_skills:
                return False, f"missing skill: {skill}"
        # Check health
        if citizen_health < 0.2:
            return False, "health too low"
        # Check load
        if citizen_load > 0.9:
            return False, "too busy"
        return True, "eligible"
