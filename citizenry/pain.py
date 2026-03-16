"""Pain — motivational damage signal with avoidance learning.

Pain is not fault detection (immune memory does that). Pain creates
AVOIDANCE MEMORIES: "that hurt, never do that again." Pain drives
behavior change through spatial avoidance zones.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PainEvent:
    """A pain event with intensity and context."""
    source: str              # Motor/joint that experienced pain
    pain_type: str           # "overcurrent", "thermal", "overload", "collision"
    intensity: float         # 0.0-1.0 (sigmoid-scaled)
    joint_positions: dict[str, int] = field(default_factory=dict)
    task_at_time: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "pain_type": self.pain_type,
            "intensity": round(self.intensity, 3),
            "joint_positions": self.joint_positions,
            "task": self.task_at_time,
            "timestamp": self.timestamp,
        }


@dataclass
class AvoidanceZone:
    """A region in joint space to avoid — learned from pain."""
    center_positions: dict[str, int]   # Joint positions at pain center
    radius: float                       # Avoidance radius (in servo position units)
    intensity: float                    # Original pain intensity
    created_at: float = field(default_factory=time.time)
    decay_rate: float = 0.001          # Intensity decays over time
    trigger_count: int = 1

    def current_intensity(self) -> float:
        """Intensity decays over time but never fully disappears."""
        age = time.time() - self.created_at
        decayed = self.intensity * math.exp(-self.decay_rate * age)
        return max(0.01, decayed)  # Never fully forget

    def contains(self, positions: dict[str, int]) -> float:
        """Check if positions are inside this zone. Returns 0-1 overlap."""
        total_dist_sq = 0
        count = 0
        for joint, center in self.center_positions.items():
            if joint in positions:
                diff = positions[joint] - center
                total_dist_sq += diff * diff
                count += 1
        if count == 0:
            return 0.0
        dist = math.sqrt(total_dist_sq / count)
        if dist >= self.radius:
            return 0.0
        return (1.0 - dist / self.radius) * self.current_intensity()

    def to_dict(self) -> dict:
        return {
            "center": self.center_positions,
            "radius": self.radius,
            "intensity": self.intensity,
            "created_at": self.created_at,
            "triggers": self.trigger_count,
        }


def compute_pain_intensity(
    value: float,
    threshold: float,
    max_value: float,
    steepness: float = 5.0,
) -> float:
    """Sigmoid-scaled pain intensity from sensor value."""
    if value <= threshold:
        return 0.0
    normalized = (value - threshold) / (max_value - threshold)
    return 1.0 / (1.0 + math.exp(-steepness * (normalized - 0.5)))


# Adjacent joints for referred pain detection
JOINT_ADJACENCY = {
    "shoulder_pan": ["shoulder_lift"],
    "shoulder_lift": ["shoulder_pan", "elbow_flex"],
    "elbow_flex": ["shoulder_lift", "wrist_flex"],
    "wrist_flex": ["elbow_flex", "wrist_roll"],
    "wrist_roll": ["wrist_flex", "gripper"],
    "gripper": ["wrist_roll"],
}


class PainMemory:
    """Manages pain events and avoidance zones."""

    MAX_ZONES = 50
    MAX_EVENTS = 200

    def __init__(self):
        self.events: list[PainEvent] = []
        self.zones: list[AvoidanceZone] = []
        self.sensitivity: float = 1.0  # Increases with repeated pain

    def record_pain(self, event: PainEvent):
        """Record a pain event and create/strengthen avoidance zone."""
        self.events.append(event)
        if len(self.events) > self.MAX_EVENTS:
            self.events = self.events[-self.MAX_EVENTS:]

        # Check if there's an existing zone near this position
        for zone in self.zones:
            overlap = zone.contains(event.joint_positions)
            if overlap > 0.3:
                # Strengthen existing zone
                zone.intensity = min(1.0, zone.intensity + 0.1)
                zone.trigger_count += 1
                zone.radius = min(zone.radius * 1.1, 500)  # Grow slightly
                self.sensitivity = min(2.0, self.sensitivity + 0.05)
                return

        # Create new avoidance zone
        radius = 100 + event.intensity * 200  # 100-300 servo units
        zone = AvoidanceZone(
            center_positions=dict(event.joint_positions),
            radius=radius,
            intensity=event.intensity,
        )
        self.zones.append(zone)

        # Prune old/weak zones
        if len(self.zones) > self.MAX_ZONES:
            self.zones.sort(key=lambda z: z.current_intensity())
            self.zones = self.zones[-self.MAX_ZONES:]

    def check_avoidance(self, positions: dict[str, int]) -> float:
        """Check if target positions are in any avoidance zone.

        Returns max avoidance signal (0 = safe, 1 = strong avoidance).
        """
        max_avoidance = 0.0
        for zone in self.zones:
            overlap = zone.contains(positions)
            max_avoidance = max(max_avoidance, overlap)
        return max_avoidance * self.sensitivity

    def check_referred_pain(self, source_joint: str, load_pct: float) -> list[str]:
        """Check for referred pain in adjacent joints."""
        if load_pct < 50:
            return []
        adjacent = JOINT_ADJACENCY.get(source_joint, [])
        return [j for j in adjacent]  # Return joints that might be stressed

    def total_pain_events(self) -> int:
        return len(self.events)

    def active_zones(self) -> int:
        return len([z for z in self.zones if z.current_intensity() > 0.05])

    def to_dict(self) -> dict:
        return {
            "sensitivity": self.sensitivity,
            "total_events": len(self.events),
            "active_zones": self.active_zones(),
            "zones": [z.to_dict() for z in self.zones],
        }
