"""Proprioception — internal body awareness via forward kinematics.

Converts raw servo positions into spatial understanding: where is my gripper?
How close am I to joint limits? What force am I exerting? Am I about to
self-collide?

Uses DH (Denavit-Hartenberg) parameters for the SO-101 6-DOF arm.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ── SO-101 DH Parameters ─────────────────────────────────────────────────────
# Link lengths in mm (approximate for SO-101 / Feetech STS3215)
L1 = 45.0    # Base to shoulder height
L2 = 105.0   # Shoulder to elbow
L3 = 105.0   # Elbow to wrist
L4 = 90.0    # Wrist to gripper tip

# Servo position range
POS_MIN = 0
POS_MAX = 4095
POS_CENTER = 2048

# Capsule radii for collision detection (mm)
LINK_RADII = [30.0, 25.0, 20.0, 20.0, 15.0]  # base, upper arm, forearm, wrist, gripper

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]


@dataclass
class JointState:
    """State of a single joint."""
    name: str
    position_raw: int = 2048
    angle_deg: float = 0.0
    angle_rad: float = 0.0
    velocity: float = 0.0
    load_pct: float = 0.0
    current_ma: float = 0.0
    temperature_c: float = 0.0
    limit_proximity: float = 0.0  # 0.0 = center, 1.0 = at limit
    estimated_torque_nm: float = 0.0


@dataclass
class CartesianPoint:
    """A point in 3D space (mm)."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def distance_to(self, other: CartesianPoint) -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass
class BodyState:
    """Integrated body state — the robot's spatial self-knowledge."""
    joints: dict[str, JointState] = field(default_factory=dict)
    gripper_position: CartesianPoint = field(default_factory=CartesianPoint)
    elbow_position: CartesianPoint = field(default_factory=CartesianPoint)
    wrist_position: CartesianPoint = field(default_factory=CartesianPoint)
    link_points: list[CartesianPoint] = field(default_factory=list)
    workspace_extent: float = 0.0  # Distance from base to gripper (mm)
    near_joint_limit: bool = False
    near_self_collision: bool = False
    estimated_payload_g: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "gripper": self.gripper_position.to_list(),
            "workspace_extent": round(self.workspace_extent, 1),
            "near_limit": self.near_joint_limit,
            "near_self_collision": self.near_self_collision,
            "payload_g": round(self.estimated_payload_g, 1),
        }


def servo_to_angle(position: int, center: int = POS_CENTER, scale: float = 360.0 / 4096) -> float:
    """Convert raw servo position to angle in degrees from center."""
    return (position - center) * scale


def servo_to_radians(position: int) -> float:
    """Convert raw servo position to radians from center."""
    return math.radians(servo_to_angle(position))


def joint_limit_proximity(position: int, margin: int = 200) -> float:
    """How close to joint limits (0.0 = center, 1.0 = at limit)."""
    dist_to_min = position - POS_MIN
    dist_to_max = POS_MAX - position
    nearest = min(dist_to_min, dist_to_max)
    return max(0.0, 1.0 - nearest / (POS_CENTER - margin))


def estimate_torque(current_ma: float, kt: float = 0.0167) -> float:
    """Estimate torque from motor current (STS3215 torque constant)."""
    return abs(current_ma / 1000.0) * kt


def estimate_payload(gripper_current_ma: float, arm_weight_g: float = 50.0) -> float:
    """Rough payload estimate from gripper holding current."""
    # Simplified: payload proportional to gripper current above baseline
    baseline_ma = 30.0
    excess = max(0.0, abs(gripper_current_ma) - baseline_ma)
    return excess * 0.5  # ~0.5g per mA excess (very rough)


def forward_kinematics(positions: dict[str, int]) -> BodyState:
    """Compute forward kinematics for SO-101 arm.

    Simplified planar FK (shoulder_pan rotates the plane, other joints
    operate within it). Returns full BodyState with link positions.
    """
    # Extract angles
    pan = servo_to_radians(positions.get("shoulder_pan", POS_CENTER))
    lift = servo_to_radians(positions.get("shoulder_lift", POS_CENTER))
    elbow = servo_to_radians(positions.get("elbow_flex", POS_CENTER))
    wflex = servo_to_radians(positions.get("wrist_flex", POS_CENTER))

    # Compute joint states
    joints = {}
    for name in MOTOR_NAMES:
        pos = positions.get(name, POS_CENTER)
        joints[name] = JointState(
            name=name,
            position_raw=pos,
            angle_deg=servo_to_angle(pos),
            angle_rad=servo_to_radians(pos),
            limit_proximity=joint_limit_proximity(pos),
        )

    # Forward kinematics in the pan-rotated plane
    # Base at origin, Z up, arm extends in XZ plane rotated by pan
    cos_pan = math.cos(pan)
    sin_pan = math.sin(pan)

    # Shoulder joint
    shoulder = CartesianPoint(0, 0, L1)

    # Elbow
    elbow_x_plane = L2 * math.cos(lift)
    elbow_z = L1 + L2 * math.sin(lift)
    elbow_pt = CartesianPoint(
        elbow_x_plane * cos_pan,
        elbow_x_plane * sin_pan,
        elbow_z,
    )

    # Wrist
    combined_angle = lift + elbow
    wrist_x_plane = elbow_x_plane + L3 * math.cos(combined_angle)
    wrist_z = elbow_z + L3 * math.sin(combined_angle)
    wrist_pt = CartesianPoint(
        wrist_x_plane * cos_pan,
        wrist_x_plane * sin_pan,
        wrist_z,
    )

    # Gripper tip
    full_angle = combined_angle + wflex
    grip_x_plane = wrist_x_plane + L4 * math.cos(full_angle)
    grip_z = wrist_z + L4 * math.sin(full_angle)
    gripper_pt = CartesianPoint(
        grip_x_plane * cos_pan,
        grip_x_plane * sin_pan,
        grip_z,
    )

    # Link points for collision checking
    base = CartesianPoint(0, 0, 0)
    link_points = [base, shoulder, elbow_pt, wrist_pt, gripper_pt]

    # Workspace extent
    extent = base.distance_to(gripper_pt)

    # Near joint limit check
    near_limit = any(j.limit_proximity > 0.8 for j in joints.values())

    return BodyState(
        joints=joints,
        gripper_position=gripper_pt,
        elbow_position=elbow_pt,
        wrist_position=wrist_pt,
        link_points=link_points,
        workspace_extent=extent,
        near_joint_limit=near_limit,
        near_self_collision=False,  # TODO: capsule check
    )
