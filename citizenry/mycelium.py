"""Mycelium Warning Network — safety warning propagation.

Two channels:
- Fast: UDP multicast REPORT for critical/emergency (< 100ms)
- Slow: Warnings array piggybacked on heartbeats (2s cycle)

Recipients apply proportional mitigation based on severity.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    INFO = 0
    WARNING = 1
    CRITICAL = 2
    EMERGENCY = 3


SEVERITY_NAMES = {
    Severity.INFO: "info",
    Severity.WARNING: "warning",
    Severity.CRITICAL: "critical",
    Severity.EMERGENCY: "emergency",
}

# Map severity to string for serialization
SEVERITY_FROM_STR = {v: k for k, v in SEVERITY_NAMES.items()}


@dataclass
class Warning:
    """A safety warning from a citizen."""

    severity: Severity = Severity.INFO
    detail: str = ""
    motor: str = ""
    value: float = 0.0
    threshold: float = 0.0
    source_citizen: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_report_body(self) -> dict:
        return {
            "type": "warning",
            "severity": SEVERITY_NAMES[self.severity],
            "detail": self.detail,
            "motor": self.motor,
            "value": self.value,
            "threshold": self.threshold,
            "source_citizen": self.source_citizen,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_report_body(cls, body: dict) -> Warning:
        sev_str = body.get("severity", "info")
        return cls(
            severity=SEVERITY_FROM_STR.get(sev_str, Severity.INFO),
            detail=body.get("detail", ""),
            motor=body.get("motor", ""),
            value=body.get("value", 0.0),
            threshold=body.get("threshold", 0.0),
            source_citizen=body.get("source_citizen", ""),
            timestamp=body.get("timestamp", time.time()),
        )


# Mitigation factors by severity
MITIGATION_FACTORS = {
    Severity.INFO: 1.0,       # No reduction
    Severity.WARNING: 0.75,   # 25% duty reduction
    Severity.CRITICAL: 0.50,  # 50% duty reduction
    Severity.EMERGENCY: 0.0,  # Full stop
}

# How long a warning stays active before decay (seconds)
WARNING_DECAY_TIME = 60.0


class MyceliumNetwork:
    """Manages warning propagation and mitigation for a citizen."""

    def __init__(self):
        self.active_warnings: list[Warning] = []
        self._warning_history: list[Warning] = []

    def add_warning(self, warning: Warning) -> None:
        """Add a new warning."""
        # Deduplicate: don't add if same detail from same source within 5s
        for w in self.active_warnings:
            if (w.detail == warning.detail
                    and w.source_citizen == warning.source_citizen
                    and time.time() - w.timestamp < 5.0):
                return
        self.active_warnings.append(warning)
        self._warning_history.append(warning)

    def decay_warnings(self) -> list[Warning]:
        """Remove expired warnings. Returns list of removed warnings."""
        now = time.time()
        expired = [w for w in self.active_warnings
                   if now - w.timestamp > WARNING_DECAY_TIME]
        self.active_warnings = [w for w in self.active_warnings
                                if now - w.timestamp <= WARNING_DECAY_TIME]
        return expired

    def current_mitigation_factor(self) -> float:
        """Get the current duty cycle factor based on active warnings.

        Returns a float in [0, 1] where 1.0 = no reduction and 0.0 = full stop.
        Uses the most severe active warning.
        """
        if not self.active_warnings:
            return 1.0
        max_severity = max(w.severity for w in self.active_warnings)
        return MITIGATION_FACTORS.get(max_severity, 1.0)

    def should_stop(self) -> bool:
        """Check if any emergency warning requires a full stop."""
        return any(w.severity == Severity.EMERGENCY for w in self.active_warnings)

    def get_slow_channel_payload(self) -> list[dict]:
        """Get warnings for heartbeat piggyback (slow channel)."""
        return [
            w.to_report_body()
            for w in self.active_warnings
            if w.severity <= Severity.WARNING  # Only info/warning on slow channel
        ]

    def get_fast_channel_warnings(self) -> list[Warning]:
        """Get warnings that need immediate multicast (fast channel)."""
        return [
            w for w in self.active_warnings
            if w.severity >= Severity.CRITICAL
            and time.time() - w.timestamp < 2.0  # Only fresh warnings
        ]

    def active_count(self) -> int:
        return len(self.active_warnings)

    def history_count(self) -> int:
        return len(self._warning_history)
