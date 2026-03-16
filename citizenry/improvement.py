"""Self-Improvement — performance tracking, strategy selection, failure analysis.

Citizens analyze their own performance and adapt. Includes UCB1 bandit
for strategy selection, performance windowing, and failure diagnosis.
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerformanceRecord:
    """A single task attempt record."""
    skill: str
    success: bool
    duration_ms: int = 0
    strategy: str = "default"
    timestamp: float = field(default_factory=time.time)


class PerformanceTracker:
    """Sliding window success rate per skill with trend detection."""

    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.records: dict[str, deque] = {}  # skill → deque of bools

    def record(self, skill: str, success: bool):
        if skill not in self.records:
            self.records[skill] = deque(maxlen=self.window_size)
        self.records[skill].append(success)

    def success_rate(self, skill: str) -> float:
        records = self.records.get(skill)
        if not records:
            return 0.0
        return sum(1 for r in records if r) / len(records)

    def trend(self, skill: str) -> float:
        """Positive = improving, negative = degrading."""
        records = self.records.get(skill)
        if not records or len(records) < 10:
            return 0.0
        items = list(records)
        half = len(items) // 2
        old = sum(1 for r in items[:half] if r) / half
        new = sum(1 for r in items[half:] if r) / (len(items) - half)
        return new - old

    def is_regressing(self, skill: str, threshold: float = -0.15) -> bool:
        return self.trend(skill) < threshold

    def proficiency(self, skill: str) -> float:
        """Overall proficiency combining success rate and volume."""
        rate = self.success_rate(skill)
        volume = len(self.records.get(skill, []))
        volume_factor = min(1.0, volume / self.window_size)
        return rate * volume_factor


class StrategySelector:
    """UCB1 bandit for selecting task strategies.

    Each task type has multiple approaches. UCB1 balances exploring
    new approaches vs exploiting the best known one.
    """

    def __init__(self):
        self.strategies: dict[str, dict[str, dict]] = {}  # task → {strategy → {count, reward}}

    def register_strategies(self, task_type: str, strategies: list[str]):
        if task_type not in self.strategies:
            self.strategies[task_type] = {}
        for s in strategies:
            if s not in self.strategies[task_type]:
                self.strategies[task_type][s] = {"count": 0, "reward": 0.0}

    def select(self, task_type: str) -> str:
        """Select a strategy using UCB1."""
        strats = self.strategies.get(task_type, {})
        if not strats:
            return "default"

        total = sum(s["count"] for s in strats.values())
        if total == 0:
            return list(strats.keys())[0]

        # Try each strategy at least once
        for name, data in strats.items():
            if data["count"] == 0:
                return name

        # UCB1: argmax(mean_reward + sqrt(2*ln(total)/count))
        best_name = ""
        best_score = -1.0
        for name, data in strats.items():
            mean = data["reward"] / data["count"]
            exploration = math.sqrt(2 * math.log(total) / data["count"])
            score = mean + exploration
            if score > best_score:
                best_score = score
                best_name = name
        return best_name

    def update(self, task_type: str, strategy: str, reward: float):
        if task_type in self.strategies and strategy in self.strategies[task_type]:
            self.strategies[task_type][strategy]["count"] += 1
            self.strategies[task_type][strategy]["reward"] += reward


@dataclass
class FailureAnalysis:
    """Structured analysis of a task failure."""
    task_type: str
    phase: str = ""                    # Which phase failed
    telemetry_at_failure: dict = field(default_factory=dict)
    hypothesis: str = ""               # e.g., "approach_too_fast"
    corrective_action: str = ""        # e.g., "reduce_approach_velocity"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "task": self.task_type, "phase": self.phase,
            "hypothesis": self.hypothesis, "correction": self.corrective_action,
        }


class FailureAnalyzer:
    """Diagnose task failures from telemetry context."""

    def analyze(self, task_type: str, telemetry: dict, phase: str = "") -> FailureAnalysis:
        """Analyze a failure and suggest corrective action."""
        analysis = FailureAnalysis(task_type=task_type, phase=phase, telemetry_at_failure=telemetry)

        # Simple rule-based diagnosis
        max_load = telemetry.get("max_load_pct", 0)
        max_temp = telemetry.get("max_temperature", 0)
        min_voltage = telemetry.get("min_voltage", 12)

        if min_voltage < 7:
            analysis.hypothesis = "voltage_collapse"
            analysis.corrective_action = "reduce_simultaneous_movement"
        elif max_temp > 55:
            analysis.hypothesis = "thermal_stress"
            analysis.corrective_action = "add_cooling_pause"
        elif max_load > 85:
            analysis.hypothesis = "overload"
            analysis.corrective_action = "reduce_speed_or_payload"
        elif phase == "approach":
            analysis.hypothesis = "approach_too_fast"
            analysis.corrective_action = "reduce_approach_velocity"
        elif phase == "grasp":
            analysis.hypothesis = "grip_insufficient"
            analysis.corrective_action = "increase_grip_force"
        else:
            analysis.hypothesis = "unknown"
            analysis.corrective_action = "retry_with_default_params"

        return analysis

    def history_count(self, hypothesis: str, history: list[FailureAnalysis]) -> int:
        return sum(1 for a in history if a.hypothesis == hypothesis)


class PracticeGoalGenerator:
    """Generate practice goals for idle time based on learning progress."""

    def generate(self, tracker: PerformanceTracker, skill_names: list[str]) -> list[str]:
        """Return skills to practice, ordered by learning potential."""
        goals = []
        for skill in skill_names:
            rate = tracker.success_rate(skill)
            trend = tracker.trend(skill)

            # Zone of proximal development: moderate success + improving trend
            if 0.4 < rate < 0.85 and trend > -0.1:
                goals.append((skill, trend + 0.5))  # Prioritize improving skills
            # Regressing skills need remedial practice
            elif tracker.is_regressing(skill):
                goals.append((skill, 1.0))  # High priority
            # Low-attempt skills need exploration
            elif len(tracker.records.get(skill, [])) < 5:
                goals.append((skill, 0.3))

        goals.sort(key=lambda g: -g[1])
        return [g[0] for g in goals]
