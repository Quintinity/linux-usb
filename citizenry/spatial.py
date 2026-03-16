"""Spatial Awareness — collision prevention and workspace management.

Ensures no two objects occupy the same space. Capsule-based collision
geometry, zone management, and flight plan broadcasting.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from .proprioception import CartesianPoint, LINK_RADII


class ZoneType(Enum):
    EXCLUSIVE = "exclusive"  # One citizen only
    SHARED = "shared"        # Mutex via PROPOSE/ACCEPT
    FORBIDDEN = "forbidden"  # No citizen may enter


@dataclass
class Capsule:
    """A capsule (line segment + radius) for collision geometry."""
    start: np.ndarray  # 3D point
    end: np.ndarray    # 3D point
    radius: float

    @staticmethod
    def from_points(p1: CartesianPoint, p2: CartesianPoint, radius: float) -> Capsule:
        return Capsule(
            start=np.array([p1.x, p1.y, p1.z]),
            end=np.array([p2.x, p2.y, p2.z]),
            radius=radius,
        )


@dataclass
class WorkspaceZone:
    """A defined zone in the workspace."""
    name: str
    zone_type: ZoneType
    center: np.ndarray        # 3D center point (mm)
    radius: float             # Zone radius (mm)
    owner: str = ""           # Citizen pubkey (for exclusive zones)
    locked_by: str = ""       # Citizen currently holding mutex (shared zones)

    def contains(self, point: np.ndarray) -> bool:
        return float(np.linalg.norm(point - self.center)) <= self.radius


@dataclass
class FlightPlan:
    """A declared trajectory intent for conflict checking."""
    citizen_pubkey: str
    citizen_name: str
    start_positions: dict[str, int]
    end_positions: dict[str, int]
    bounding_min: np.ndarray = field(default_factory=lambda: np.zeros(3))
    bounding_max: np.ndarray = field(default_factory=lambda: np.zeros(3))
    priority: float = 0.5
    timestamp: float = field(default_factory=time.time)
    ttl: float = 5.0  # Expires after 5 seconds

    def is_expired(self) -> bool:
        return time.time() > self.timestamp + self.ttl

    def to_propose_body(self) -> dict:
        return {
            "task": "flight_plan",
            "start": self.start_positions,
            "end": self.end_positions,
            "bbox_min": self.bounding_min.tolist(),
            "bbox_max": self.bounding_max.tolist(),
            "priority": self.priority,
        }


def capsule_distance(c1: Capsule, c2: Capsule) -> float:
    """Compute minimum distance between two capsules.

    Returns the distance between the closest points on the two line
    segments, minus the radii. Negative = collision.
    """
    d1 = c1.end - c1.start
    d2 = c2.end - c2.start
    r = c1.start - c2.start

    a = float(np.dot(d1, d1))
    e = float(np.dot(d2, d2))
    f = float(np.dot(d2, r))

    if a <= 1e-6 and e <= 1e-6:
        # Both degenerate to points
        dist = float(np.linalg.norm(r))
        return dist - c1.radius - c2.radius

    if a <= 1e-6:
        s = 0.0
        t = max(0.0, min(1.0, f / e))
    else:
        c = float(np.dot(d1, r))
        if e <= 1e-6:
            t = 0.0
            s = max(0.0, min(1.0, -c / a))
        else:
            b = float(np.dot(d1, d2))
            denom = a * e - b * b
            if abs(denom) > 1e-6:
                s = max(0.0, min(1.0, (b * f - c * e) / denom))
            else:
                s = 0.0
            t = (b * s + f) / e
            if t < 0:
                t = 0.0
                s = max(0.0, min(1.0, -c / a))
            elif t > 1:
                t = 1.0
                s = max(0.0, min(1.0, (b - c) / a))

    closest1 = c1.start + s * d1
    closest2 = c2.start + t * d2
    dist = float(np.linalg.norm(closest1 - closest2))
    return dist - c1.radius - c2.radius


def check_arm_collision(
    arm1_points: list[CartesianPoint],
    arm2_points: list[CartesianPoint],
    radii: list[float] | None = None,
) -> tuple[bool, float]:
    """Check if two arms are colliding.

    Args:
        arm1_points, arm2_points: Link endpoint positions (from FK)
        radii: Link radii (defaults to LINK_RADII)

    Returns:
        (colliding, min_distance) where min_distance < 0 means collision
    """
    radii = radii or LINK_RADII

    min_dist = float('inf')

    for i in range(len(arm1_points) - 1):
        c1 = Capsule.from_points(arm1_points[i], arm1_points[i + 1],
                                  radii[min(i, len(radii) - 1)])
        for j in range(len(arm2_points) - 1):
            c2 = Capsule.from_points(arm2_points[j], arm2_points[j + 1],
                                      radii[min(j, len(radii) - 1)])
            dist = capsule_distance(c1, c2)
            min_dist = min(min_dist, dist)

    return min_dist < 0, min_dist


def check_self_collision(
    link_points: list[CartesianPoint],
    radii: list[float] | None = None,
    skip_adjacent: bool = True,
) -> tuple[bool, float]:
    """Check if an arm is self-colliding.

    Args:
        link_points: Link endpoint positions from FK
        radii: Link radii
        skip_adjacent: Skip adjacent link pairs (they always touch)

    Returns:
        (colliding, min_distance)
    """
    radii = radii or LINK_RADII
    min_dist = float('inf')
    n = len(link_points) - 1  # Number of links

    for i in range(n):
        for j in range(i + (2 if skip_adjacent else 1), n):
            c1 = Capsule.from_points(link_points[i], link_points[i + 1],
                                      radii[min(i, len(radii) - 1)])
            c2 = Capsule.from_points(link_points[j], link_points[j + 1],
                                      radii[min(j, len(radii) - 1)])
            dist = capsule_distance(c1, c2)
            min_dist = min(min_dist, dist)

    return min_dist < 0, min_dist


class ZoneManager:
    """Manages workspace zones and flight plans."""

    def __init__(self):
        self.zones: list[WorkspaceZone] = []
        self.active_flights: dict[str, FlightPlan] = {}  # citizen_pubkey → plan

    def add_zone(self, zone: WorkspaceZone):
        self.zones.append(zone)

    def register_flight(self, plan: FlightPlan):
        self.active_flights[plan.citizen_pubkey] = plan

    def check_flight_conflict(self, plan: FlightPlan) -> list[str]:
        """Check if a flight plan conflicts with active flights.

        Returns list of conflicting citizen pubkeys.
        """
        conflicts = []
        for pk, other in self.active_flights.items():
            if pk == plan.citizen_pubkey:
                continue
            if other.is_expired():
                continue
            # Bounding box overlap check
            if self._bbox_overlap(plan, other):
                conflicts.append(pk)
        return conflicts

    def cleanup_expired(self):
        expired = [pk for pk, p in self.active_flights.items() if p.is_expired()]
        for pk in expired:
            del self.active_flights[pk]

    def _bbox_overlap(self, a: FlightPlan, b: FlightPlan) -> bool:
        """Check if two flight plan bounding boxes overlap."""
        for i in range(3):
            if a.bounding_max[i] < b.bounding_min[i] or b.bounding_max[i] < a.bounding_min[i]:
                return False
        return True
