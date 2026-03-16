"""Growth — developmental stages, earned autonomy, and specialization.

Citizens mature from NEWBORN (fully supervised) to ELDER (can teach others).
Autonomy is earned per-skill, not globally. Specialization emerges from
accumulated experience.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class DevelopmentalStage(IntEnum):
    NEWBORN = 0    # Just created, no experience
    INFANT = 1     # Basic calibration complete, can follow teleop
    JUVENILE = 2   # Can execute simple tasks with supervision
    ADULT = 3      # Can execute tasks independently
    EXPERT = 4     # High proficiency, can coordinate
    ELDER = 5      # Can teach other citizens, mentor


class AutonomyLevel(IntEnum):
    TELEOP_ONLY = 0    # Only teleop, no autonomous actions
    SUPERVISED = 1     # Can execute tasks with governor approval
    ASSISTED = 2       # Can execute tasks, governor monitors
    AUTONOMOUS = 3     # Full autonomous operation
    SELF_GOVERNING = 4 # Can assign tasks to others


STAGE_THRESHOLDS = {
    DevelopmentalStage.INFANT: {"total_tasks": 5, "success_rate": 0.0},
    DevelopmentalStage.JUVENILE: {"total_tasks": 20, "success_rate": 0.5},
    DevelopmentalStage.ADULT: {"total_tasks": 100, "success_rate": 0.7},
    DevelopmentalStage.EXPERT: {"total_tasks": 500, "success_rate": 0.85},
    DevelopmentalStage.ELDER: {"total_tasks": 2000, "success_rate": 0.9},
}

AUTONOMY_REQUIREMENTS = {
    AutonomyLevel.SUPERVISED: {"consecutive_successes": 5, "proficiency": 0.5},
    AutonomyLevel.ASSISTED: {"consecutive_successes": 10, "proficiency": 0.7},
    AutonomyLevel.AUTONOMOUS: {"consecutive_successes": 20, "proficiency": 0.85},
    AutonomyLevel.SELF_GOVERNING: {"consecutive_successes": 50, "proficiency": 0.95},
}


@dataclass
class MaturationState:
    """Tracks a citizen's developmental progress."""
    stage: DevelopmentalStage = DevelopmentalStage.NEWBORN
    total_tasks: int = 0
    total_successes: int = 0
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    autonomy_per_skill: dict[str, AutonomyLevel] = field(default_factory=dict)
    milestones: list[dict] = field(default_factory=list)
    stage_entered_at: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.total_successes / self.total_tasks

    def record_task(self, success: bool, skill: str = ""):
        self.total_tasks += 1
        if success:
            self.total_successes += 1
            self.consecutive_successes += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0


@dataclass
class SpecializationProfile:
    """Tracks emergent specialization from accumulated experience."""
    task_performance: dict[str, dict] = field(default_factory=dict)
    # task_type → {"attempts": N, "successes": N, "ema_rate": float}

    def record(self, task_type: str, success: bool):
        if task_type not in self.task_performance:
            self.task_performance[task_type] = {"attempts": 0, "successes": 0, "ema_rate": 0.5}
        p = self.task_performance[task_type]
        p["attempts"] += 1
        if success:
            p["successes"] += 1
        alpha = 0.1
        p["ema_rate"] = p["ema_rate"] + alpha * ((1.0 if success else 0.0) - p["ema_rate"])

    def specialization_score(self, task_type: str) -> float:
        """How specialized this citizen is for a task type (0-1)."""
        p = self.task_performance.get(task_type)
        if not p or p["attempts"] < 10:
            return 0.0
        return p["ema_rate"]

    def top_specializations(self, n: int = 3) -> list[tuple[str, float]]:
        scored = [(t, self.specialization_score(t)) for t in self.task_performance]
        scored.sort(key=lambda x: -x[1])
        return scored[:n]

    def breadth(self) -> float:
        """How broadly experienced (0 = specialist, 1 = generalist)."""
        if not self.task_performance:
            return 0.0
        rates = [p["ema_rate"] for p in self.task_performance.values() if p["attempts"] >= 5]
        if len(rates) < 2:
            return 0.0
        mean = sum(rates) / len(rates)
        variance = sum((r - mean) ** 2 for r in rates) / len(rates)
        # Low variance = generalist, high variance = specialist
        return max(0.0, 1.0 - variance * 4)


class GrowthTracker:
    """Manages developmental progression for a citizen."""

    def __init__(self):
        self.maturation = MaturationState()
        self.specialization = SpecializationProfile()

    def record_task(self, skill: str, task_type: str, success: bool):
        """Record a task attempt and check for stage/autonomy promotions."""
        self.maturation.record_task(success, skill)
        self.specialization.record(task_type, success)

        # Check stage promotion
        self._check_stage_promotion()
        # Check autonomy promotion for this skill
        self._check_autonomy(skill)

    def _check_stage_promotion(self):
        """Check if citizen should advance to next developmental stage."""
        m = self.maturation
        next_stage = DevelopmentalStage(min(m.stage + 1, DevelopmentalStage.ELDER))
        if next_stage == m.stage:
            return

        req = STAGE_THRESHOLDS.get(next_stage)
        if req and m.total_tasks >= req["total_tasks"] and m.success_rate >= req["success_rate"]:
            old = m.stage
            m.stage = next_stage
            m.stage_entered_at = time.time()
            m.milestones.append({
                "type": "stage_promotion",
                "from": old.name, "to": next_stage.name,
                "timestamp": time.time(),
            })

    def _check_autonomy(self, skill: str):
        """Check if autonomy should be promoted for a skill."""
        m = self.maturation
        current = m.autonomy_per_skill.get(skill, AutonomyLevel.TELEOP_ONLY)
        next_level = AutonomyLevel(min(current + 1, AutonomyLevel.SELF_GOVERNING))
        if next_level == current:
            return

        req = AUTONOMY_REQUIREMENTS.get(next_level)
        if not req:
            return

        # Demotion: 3 consecutive failures → drop one level
        if m.consecutive_failures >= 3 and current > AutonomyLevel.TELEOP_ONLY:
            m.autonomy_per_skill[skill] = AutonomyLevel(current - 1)
            return

        if (m.consecutive_successes >= req["consecutive_successes"]):
            m.autonomy_per_skill[skill] = next_level

    def get_stage(self) -> DevelopmentalStage:
        return self.maturation.stage

    def get_autonomy(self, skill: str) -> AutonomyLevel:
        return self.maturation.autonomy_per_skill.get(skill, AutonomyLevel.TELEOP_ONLY)

    def stats(self) -> dict:
        return {
            "stage": self.maturation.stage.name,
            "total_tasks": self.maturation.total_tasks,
            "success_rate": round(self.maturation.success_rate, 2),
            "specializations": self.specialization.top_specializations(),
            "breadth": round(self.specialization.breadth(), 2),
        }
