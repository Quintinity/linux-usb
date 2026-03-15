"""Immune Memory — fault pattern learning and sharing.

When a citizen detects and recovers from a fault, it creates an immune
memory entry. These entries are shared across the mesh so all citizens
can preemptively mitigate known failure modes.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class FaultPattern:
    """A learned fault pattern with its mitigation."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    pattern_type: str = ""          # e.g., "voltage_collapse", "thermal_overload"
    conditions: dict[str, Any] = field(default_factory=dict)
    mitigation: str = ""            # e.g., "reduce_speed_50pct"
    severity: str = "warning"       # info, warning, critical, emergency
    source_citizen: str = ""        # pubkey of the citizen that first detected it
    learned_at: float = field(default_factory=time.time)
    occurrences: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> FaultPattern:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ImmuneMemory:
    """Database of known fault patterns with matching and pruning."""

    MAX_PATTERNS = 1000

    def __init__(self):
        self.patterns: dict[str, FaultPattern] = {}
        self._last_triggered: dict[str, float] = {}

    def add(self, pattern: FaultPattern) -> None:
        """Add or update a fault pattern."""
        # Check if we already have a pattern of this type
        existing = self._find_by_type(pattern.pattern_type)
        if existing:
            existing.occurrences += 1
            existing.learned_at = max(existing.learned_at, pattern.learned_at)
            self._last_triggered[existing.id] = time.time()
            return

        self.patterns[pattern.id] = pattern
        self._last_triggered[pattern.id] = time.time()

        # Prune if over limit (LRU by last triggered)
        if len(self.patterns) > self.MAX_PATTERNS:
            self._prune()

    def match(self, telemetry: dict) -> list[FaultPattern]:
        """Check telemetry against known fault patterns.

        Returns list of matching patterns with their mitigations.
        """
        matches = []
        for pattern in self.patterns.values():
            if self._check_conditions(pattern.conditions, telemetry):
                self._last_triggered[pattern.id] = time.time()
                pattern.occurrences += 1
                matches.append(pattern)
        return matches

    def _check_conditions(self, conditions: dict, telemetry: dict) -> bool:
        """Check if telemetry matches fault conditions."""
        for key, threshold in conditions.items():
            value = telemetry.get(key)
            if value is None:
                continue
            if isinstance(threshold, dict):
                if "min" in threshold and value < threshold["min"]:
                    return True
                if "max" in threshold and value > threshold["max"]:
                    return True
            elif isinstance(threshold, (int, float)):
                # Default: trigger if value exceeds threshold
                if value > threshold:
                    return True
        return False

    def get_all(self) -> list[FaultPattern]:
        return list(self.patterns.values())

    def merge(self, patterns: list[FaultPattern]) -> int:
        """Merge patterns from another citizen. Returns count of new patterns added."""
        added = 0
        for p in patterns:
            if not self._find_by_type(p.pattern_type):
                self.patterns[p.id] = p
                self._last_triggered[p.id] = time.time()
                added += 1
            else:
                existing = self._find_by_type(p.pattern_type)
                existing.occurrences += p.occurrences
        return added

    def to_list(self) -> list[dict]:
        return [p.to_dict() for p in self.patterns.values()]

    @classmethod
    def from_list(cls, data: list[dict]) -> ImmuneMemory:
        mem = cls()
        for d in data:
            mem.add(FaultPattern.from_dict(d))
        return mem

    def _find_by_type(self, pattern_type: str) -> FaultPattern | None:
        for p in self.patterns.values():
            if p.pattern_type == pattern_type:
                return p
        return None

    def _prune(self) -> None:
        """Remove least-recently-triggered patterns to stay under MAX_PATTERNS."""
        if len(self.patterns) <= self.MAX_PATTERNS:
            return
        by_time = sorted(
            self.patterns.keys(),
            key=lambda pid: self._last_triggered.get(pid, 0),
        )
        to_remove = len(self.patterns) - self.MAX_PATTERNS
        for pid in by_time[:to_remove]:
            del self.patterns[pid]
            self._last_triggered.pop(pid, None)


# Pre-defined fault patterns from hardware experience
KNOWN_PATTERNS = [
    FaultPattern(
        id="voltage_collapse",
        pattern_type="voltage_collapse",
        conditions={"min_voltage": {"min": 6.0}},
        mitigation="reduce_all_speeds_50pct",
        severity="critical",
        source_citizen="bootstrap",
    ),
    FaultPattern(
        id="thermal_overload",
        pattern_type="thermal_overload",
        conditions={"max_temperature": {"max": 60.0}},
        mitigation="reduce_speed_25pct_affected_joint",
        severity="warning",
        source_citizen="bootstrap",
    ),
    FaultPattern(
        id="overcurrent",
        pattern_type="overcurrent",
        conditions={"total_current_ma": {"max": 4000.0}},
        mitigation="reduce_all_velocities_50pct",
        severity="critical",
        source_citizen="bootstrap",
    ),
    FaultPattern(
        id="servo_error_flag",
        pattern_type="servo_error_flag",
        conditions={"has_errors": True},
        mitigation="disable_torque_and_report",
        severity="emergency",
        source_citizen="bootstrap",
    ),
]


def bootstrap_immune_memory() -> ImmuneMemory:
    """Create an immune memory with known fault patterns from hardware experience."""
    mem = ImmuneMemory()
    for p in KNOWN_PATTERNS:
        mem.add(p)
    return mem
