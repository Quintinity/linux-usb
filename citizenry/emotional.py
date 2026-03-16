"""Emotional State Signals — composite metrics from telemetry.

Not sentiment. Composite metrics derived from real data:
- Fatigue: f(temperature, error_rate, uptime, power_consumption)
- Confidence: success rate on recent tasks
- Curiosity: novelty of current situation relative to experience

These drive scheduling (fatigued citizens rest) and make the dashboard
immediately intuitive.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class EmotionalState:
    """Composite emotional metrics for a citizen."""

    fatigue: float = 0.0       # 0.0 = fresh, 1.0 = exhausted
    confidence: float = 0.5    # 0.0 = uncertain, 1.0 = fully confident
    curiosity: float = 0.0     # 0.0 = routine, 1.0 = novel situation
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "fatigue": round(self.fatigue, 2),
            "confidence": round(self.confidence, 2),
            "curiosity": round(self.curiosity, 2),
        }

    @classmethod
    def from_dict(cls, d: dict) -> EmotionalState:
        return cls(
            fatigue=d.get("fatigue", 0.0),
            confidence=d.get("confidence", 0.5),
            curiosity=d.get("curiosity", 0.0),
            timestamp=d.get("timestamp", 0.0),
        )

    @property
    def mood(self) -> str:
        """Human-readable mood label."""
        if self.fatigue > 0.7:
            return "exhausted"
        if self.fatigue > 0.4:
            return "tired"
        if self.confidence > 0.8 and self.fatigue < 0.3:
            return "focused"
        if self.confidence < 0.3:
            return "uncertain"
        if self.curiosity > 0.6:
            return "curious"
        if self.fatigue < 0.2 and self.confidence > 0.5:
            return "energized"
        return "steady"


def compute_emotional_state(
    max_temperature: float = 30.0,
    uptime_hours: float = 0.0,
    warning_count: int = 0,
    tasks_completed: int = 0,
    tasks_failed: int = 0,
    immune_matches: int = 0,
    novel_neighbors: int = 0,
) -> EmotionalState:
    """Compute emotional state from telemetry and task history.

    All inputs are real values from citizen state — no simulation.
    """
    # Fatigue: temperature + uptime + warnings
    temp_factor = max(0.0, (max_temperature - 30) / 35)  # 0 at 30C, 1 at 65C
    uptime_factor = min(1.0, uptime_hours / 8.0)  # Full fatigue at 8h
    warning_factor = min(1.0, warning_count / 5.0)
    fatigue = min(1.0, temp_factor * 0.4 + uptime_factor * 0.4 + warning_factor * 0.2)

    # Confidence: success rate
    total_tasks = tasks_completed + tasks_failed
    if total_tasks > 0:
        confidence = tasks_completed / total_tasks
    else:
        confidence = 0.5  # No data = neutral

    # Curiosity: novel situations
    curiosity = 0.0
    if novel_neighbors > 0:
        curiosity += min(0.5, novel_neighbors * 0.2)
    if immune_matches > 0:
        curiosity += min(0.3, immune_matches * 0.1)
    if total_tasks < 5:
        curiosity += 0.2  # New citizen is curious
    curiosity = min(1.0, curiosity)

    return EmotionalState(
        fatigue=fatigue,
        confidence=confidence,
        curiosity=curiosity,
        timestamp=time.time(),
    )
