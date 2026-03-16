"""Visual Task Coordination — camera-guided manipulation.

Orchestrates camera + arm citizens to perform vision-guided tasks:
- visual_pick_and_place: camera detects object → arm picks it up
- color_sorting: camera detects colors → arm sorts by color
- visual_inspection: camera captures workspace → report to governor

These tasks use the symbiosis contract between camera and arm citizens
and are coordinated by the governor through the marketplace.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DetectedObject:
    """An object detected by the camera."""
    color: str
    bbox: list[int]  # [x, y, w, h] in pixels
    area: int
    center_x: float = 0.0  # Normalized [0, 1]
    center_y: float = 0.0  # Normalized [0, 1]

    @classmethod
    def from_detection(cls, d: dict, frame_width: int = 640, frame_height: int = 480) -> DetectedObject:
        bbox = d.get("bbox", [0, 0, 0, 0])
        cx = (bbox[0] + bbox[2] / 2) / frame_width
        cy = (bbox[1] + bbox[3] / 2) / frame_height
        return cls(
            color=d.get("color", "unknown"),
            bbox=bbox,
            area=d.get("area", 0),
            center_x=cx,
            center_y=cy,
        )


# ── Workspace mapping ────────────────────────────────────────────────────────
# Maps normalized camera coordinates [0,1] to SO-101 servo positions.
# These are approximate — real calibration would use a proper camera-to-robot
# transform. For now we use a simple linear mapping from the camera frame
# to the arm's reachable workspace.

# SO-101 workspace bounds (raw servo positions)
WORKSPACE = {
    "shoulder_pan": {"min": 1500, "max": 2600, "home": 2048},   # Left-right
    "shoulder_lift": {"min": 1200, "max": 2200, "home": 1400},  # Up-down (lower = higher)
    "elbow_flex": {"min": 2000, "max": 3200, "home": 3000},     # Reach
    "wrist_flex": {"min": 1500, "max": 2500, "home": 2048},
    "wrist_roll": {"min": 1500, "max": 2500, "home": 2048},
    "gripper": {"open": 1400, "closed": 2500, "home": 2048},
}


def camera_to_arm_position(cx: float, cy: float, reach: float = 0.5) -> dict:
    """Convert normalized camera coordinates to arm servo positions.

    Args:
        cx: Normalized x position [0=left, 1=right]
        cy: Normalized y position [0=top, 1=bottom]
        reach: How far to reach [0=close, 1=far]

    Returns:
        Dict of motor_name → servo position for the SO-101.
    """
    ws = WORKSPACE
    # Map camera X to shoulder pan (mirror: camera left = arm right)
    pan = int(ws["shoulder_pan"]["max"] - cx * (ws["shoulder_pan"]["max"] - ws["shoulder_pan"]["min"]))
    # Map camera Y to shoulder lift (top of frame = lower lift value = higher position)
    lift = int(ws["shoulder_lift"]["min"] + cy * (ws["shoulder_lift"]["max"] - ws["shoulder_lift"]["min"]))
    # Reach determines elbow extension
    elbow = int(ws["elbow_flex"]["max"] - reach * (ws["elbow_flex"]["max"] - ws["elbow_flex"]["min"]))

    return {
        "shoulder_pan": pan,
        "shoulder_lift": lift,
        "elbow_flex": elbow,
        "wrist_flex": ws["wrist_flex"]["home"],
        "wrist_roll": ws["wrist_roll"]["home"],
        "gripper": ws["gripper"]["open"],
    }


HOME_POSITION = {
    "shoulder_pan": WORKSPACE["shoulder_pan"]["home"],
    "shoulder_lift": WORKSPACE["shoulder_lift"]["home"],
    "elbow_flex": WORKSPACE["elbow_flex"]["home"],
    "wrist_flex": WORKSPACE["wrist_flex"]["home"],
    "wrist_roll": WORKSPACE["wrist_roll"]["home"],
    "gripper": WORKSPACE["gripper"]["home"],
}


@dataclass
class VisualPickAndPlaceResult:
    """Result of a visual pick-and-place operation."""
    success: bool = False
    detected_objects: list[DetectedObject] = field(default_factory=list)
    picked_object: DetectedObject | None = None
    pick_position: dict | None = None
    place_position: dict | None = None
    duration_ms: int = 0
    error: str = ""


def plan_pick_and_place(
    detections: list[dict],
    target_color: str | None = None,
    frame_width: int = 640,
    frame_height: int = 480,
) -> tuple[DetectedObject | None, dict | None]:
    """Plan a pick-and-place from camera detections.

    Args:
        detections: List of detection dicts from camera color_detection
        target_color: Color to pick (None = pick largest object)
        frame_width: Camera frame width
        frame_height: Camera frame height

    Returns:
        (target_object, arm_position) or (None, None) if no valid target.
    """
    if not detections:
        return None, None

    objects = [DetectedObject.from_detection(d, frame_width, frame_height) for d in detections]

    # Filter by color if specified
    if target_color:
        objects = [o for o in objects if o.color == target_color]

    if not objects:
        return None, None

    # Pick the largest object
    target = max(objects, key=lambda o: o.area)

    # Convert to arm position
    arm_pos = camera_to_arm_position(target.center_x, target.center_y, reach=0.6)

    return target, arm_pos


# ── Sort planning ─────────────────────────────────────────────────────────────

# Sorting bin positions (approximate servo positions for left/center/right bins)
SORT_BINS = {
    "red": {"shoulder_pan": 2400, "shoulder_lift": 1600, "elbow_flex": 2500,
            "wrist_flex": 2048, "wrist_roll": 2048, "gripper": WORKSPACE["gripper"]["open"]},
    "green": {"shoulder_pan": 2048, "shoulder_lift": 1600, "elbow_flex": 2500,
              "wrist_flex": 2048, "wrist_roll": 2048, "gripper": WORKSPACE["gripper"]["open"]},
    "blue": {"shoulder_pan": 1700, "shoulder_lift": 1600, "elbow_flex": 2500,
             "wrist_flex": 2048, "wrist_roll": 2048, "gripper": WORKSPACE["gripper"]["open"]},
    "yellow": {"shoulder_pan": 1500, "shoulder_lift": 1600, "elbow_flex": 2500,
               "wrist_flex": 2048, "wrist_roll": 2048, "gripper": WORKSPACE["gripper"]["open"]},
}


def plan_sort_sequence(
    detections: list[dict],
    frame_width: int = 640,
    frame_height: int = 480,
) -> list[tuple[DetectedObject, dict, dict]]:
    """Plan a sorting sequence from camera detections.

    Returns list of (object, pick_position, place_position) tuples.
    """
    objects = [DetectedObject.from_detection(d, frame_width, frame_height) for d in detections]
    sequence = []

    for obj in sorted(objects, key=lambda o: -o.area):  # Largest first
        pick_pos = camera_to_arm_position(obj.center_x, obj.center_y, reach=0.6)
        place_pos = SORT_BINS.get(obj.color)
        if place_pos:
            sequence.append((obj, pick_pos, place_pos))

    return sequence
