"""Reflex Engine — immediate stimulus→response without governor.

Runs a tight loop checking servo telemetry against declarative rules.
Reflexes fire locally on the Pi, bypassing the governor entirely.
The governor is notified AFTER the reflex fires.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable


class ReflexPriority(IntEnum):
    """Reflex priority — higher = more urgent, cannot be suppressed."""
    BACKGROUND = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    EMERGENCY = 4  # Cannot be overridden


@dataclass
class ReflexRule:
    """A declarative condition→action reflex."""
    name: str
    condition: Callable[[dict], bool]  # Takes telemetry dict, returns True if triggered
    action: str                        # Action name (e.g., "reduce_velocity", "disable_torque")
    priority: ReflexPriority = ReflexPriority.NORMAL
    cooldown_s: float = 1.0            # Minimum seconds between firings
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    last_fired: float = 0.0
    fire_count: int = 0

    def can_fire(self) -> bool:
        return time.time() - self.last_fired >= self.cooldown_s

    def record_fire(self):
        self.last_fired = time.time()
        self.fire_count += 1


@dataclass
class ReflexEvent:
    """Record of a reflex firing."""
    rule_name: str
    action: str
    priority: int
    telemetry_snapshot: dict
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "rule": self.rule_name,
            "action": self.action,
            "priority": self.priority,
            "timestamp": self.timestamp,
        }


class TelemetryWindow:
    """Rolling window of telemetry readings for rate-of-change detection."""

    def __init__(self, size: int = 10):
        self.size = size
        self.readings: list[dict] = []

    def add(self, reading: dict):
        self.readings.append(reading)
        if len(self.readings) > self.size:
            self.readings.pop(0)

    def rate_of_change(self, key: str) -> float:
        """Compute rate of change for a key over the window."""
        vals = [r.get(key) for r in self.readings if r.get(key) is not None]
        if len(vals) < 2:
            return 0.0
        return (vals[-1] - vals[0]) / max(1, len(vals) - 1)

    def latest(self) -> dict:
        return self.readings[-1] if self.readings else {}


# ── Default Reflex Table ──────────────────────────────────────────────────────

def _overcurrent(t: dict) -> bool:
    return (t.get("total_current_ma") or 0) > 4000

def _voltage_collapse(t: dict) -> bool:
    return (t.get("min_voltage") or 99) < 6.0

def _thermal_warning(t: dict) -> bool:
    return (t.get("max_temperature") or 0) > 60

def _thermal_critical(t: dict) -> bool:
    return (t.get("max_temperature") or 0) > 70

def _servo_error(t: dict) -> bool:
    return bool(t.get("has_errors"))

def _high_load(t: dict) -> bool:
    return (t.get("max_load_pct") or 0) > 90


DEFAULT_REFLEX_TABLE = [
    ReflexRule(
        name="overcurrent_protection",
        condition=_overcurrent,
        action="reduce_velocity_50pct",
        priority=ReflexPriority.CRITICAL,
        cooldown_s=2.0,
        description="Total current > 4A: reduce all velocities 50%",
    ),
    ReflexRule(
        name="voltage_collapse",
        condition=_voltage_collapse,
        action="disable_torque",
        priority=ReflexPriority.EMERGENCY,
        cooldown_s=5.0,
        description="Voltage < 6V: disable torque immediately",
    ),
    ReflexRule(
        name="thermal_warning",
        condition=_thermal_warning,
        action="reduce_velocity_25pct",
        priority=ReflexPriority.HIGH,
        cooldown_s=5.0,
        description="Temperature > 60C: reduce speed 25%",
    ),
    ReflexRule(
        name="thermal_critical",
        condition=_thermal_critical,
        action="disable_torque",
        priority=ReflexPriority.EMERGENCY,
        cooldown_s=10.0,
        description="Temperature > 70C: disable torque",
    ),
    ReflexRule(
        name="servo_error",
        condition=_servo_error,
        action="disable_torque",
        priority=ReflexPriority.EMERGENCY,
        cooldown_s=5.0,
        description="Servo error flag: disable torque",
    ),
    ReflexRule(
        name="high_load",
        condition=_high_load,
        action="reduce_velocity_25pct",
        priority=ReflexPriority.NORMAL,
        cooldown_s=2.0,
        description="Load > 90%: reduce speed 25%",
    ),
]


class ReflexEngine:
    """Evaluates reflex rules against telemetry and fires actions."""

    def __init__(self, rules: list[ReflexRule] | None = None):
        self.rules = rules or list(DEFAULT_REFLEX_TABLE)
        self.window = TelemetryWindow(size=10)
        self.event_log: list[ReflexEvent] = []
        self._max_log = 100

    def evaluate(self, telemetry: dict) -> list[ReflexEvent]:
        """Evaluate all rules against current telemetry.

        Returns list of fired reflex events (highest priority first).
        """
        self.window.add(telemetry)
        fired = []

        for rule in self.rules:
            if not rule.can_fire():
                continue
            try:
                if rule.condition(telemetry):
                    rule.record_fire()
                    event = ReflexEvent(
                        rule_name=rule.name,
                        action=rule.action,
                        priority=rule.priority,
                        telemetry_snapshot=dict(telemetry),
                    )
                    fired.append(event)
                    self.event_log.append(event)
            except Exception:
                continue

        # Trim log
        if len(self.event_log) > self._max_log:
            self.event_log = self.event_log[-self._max_log:]

        # Sort by priority (highest first)
        fired.sort(key=lambda e: -e.priority)
        return fired

    def add_rule(self, rule: ReflexRule):
        self.rules.append(rule)

    def get_stats(self) -> dict:
        return {
            "total_rules": len(self.rules),
            "total_fires": sum(r.fire_count for r in self.rules),
            "recent_events": len(self.event_log),
            "rules": {r.name: r.fire_count for r in self.rules if r.fire_count > 0},
        }
