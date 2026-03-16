"""Camera-to-Arm Calibration — build a transform from pixel to servo space.

Moves the arm to known positions, captures the arm tip location via camera,
and computes an affine transform mapping camera pixels → servo positions.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .persistence import CITIZENRY_DIR


@dataclass
class CalibrationPoint:
    """A single calibration correspondence."""
    pixel_x: float
    pixel_y: float
    servo_pan: int
    servo_lift: int
    servo_elbow: int


@dataclass
class CalibrationResult:
    """Result of a calibration procedure."""
    points: list[CalibrationPoint] = field(default_factory=list)
    transform_matrix: list[list[float]] | None = None  # 3x3 affine
    error_pixels: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "points": [
                {"px": p.pixel_x, "py": p.pixel_y,
                 "pan": p.servo_pan, "lift": p.servo_lift, "elbow": p.servo_elbow}
                for p in self.points
            ],
            "transform": self.transform_matrix,
            "error": self.error_pixels,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CalibrationResult:
        points = [
            CalibrationPoint(
                pixel_x=p["px"], pixel_y=p["py"],
                servo_pan=p["pan"], servo_lift=p["lift"], servo_elbow=p["elbow"],
            )
            for p in d.get("points", [])
        ]
        return cls(
            points=points,
            transform_matrix=d.get("transform"),
            error_pixels=d.get("error", 0.0),
            timestamp=d.get("timestamp", 0.0),
        )


# Calibration poses — known arm positions to move to during calibration
CALIBRATION_POSES = [
    {"shoulder_pan": 1700, "shoulder_lift": 1600, "elbow_flex": 2500,
     "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 1400},
    {"shoulder_pan": 2048, "shoulder_lift": 1600, "elbow_flex": 2500,
     "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 1400},
    {"shoulder_pan": 2400, "shoulder_lift": 1600, "elbow_flex": 2500,
     "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 1400},
    {"shoulder_pan": 1700, "shoulder_lift": 1800, "elbow_flex": 2200,
     "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 1400},
    {"shoulder_pan": 2048, "shoulder_lift": 1800, "elbow_flex": 2200,
     "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 1400},
    {"shoulder_pan": 2400, "shoulder_lift": 1800, "elbow_flex": 2200,
     "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 1400},
]


def compute_affine_transform(
    pixel_coords: list[tuple[float, float]],
    servo_coords: list[tuple[int, int, int]],
) -> tuple[np.ndarray, float]:
    """Compute affine transform from pixel space to servo space.

    Args:
        pixel_coords: List of (x, y) pixel positions
        servo_coords: List of (pan, lift, elbow) servo positions

    Returns:
        (transform_matrix, mean_error)
        transform_matrix is 3x3 mapping [px, py, 1] → [pan, lift, elbow]
    """
    n = len(pixel_coords)
    if n < 3:
        raise ValueError("Need at least 3 calibration points")

    # Build source matrix (pixels, homogeneous)
    A = np.zeros((n, 3))
    for i, (px, py) in enumerate(pixel_coords):
        A[i] = [px, py, 1.0]

    # Build target matrix (servos)
    B = np.zeros((n, 3))
    for i, (pan, lift, elbow) in enumerate(servo_coords):
        B[i] = [pan, lift, elbow]

    # Least-squares solve: A @ T = B → T = pinv(A) @ B
    T, residuals, rank, sv = np.linalg.lstsq(A, B, rcond=None)

    # Compute mean error
    predicted = A @ T
    errors = np.sqrt(np.sum((predicted - B) ** 2, axis=1))
    mean_error = float(np.mean(errors))

    return T.T.tolist(), mean_error  # Transpose for [3x3] convention


def apply_calibrated_transform(
    pixel_x: float,
    pixel_y: float,
    transform: list[list[float]],
) -> dict:
    """Apply calibrated transform to map pixel → servo positions."""
    T = np.array(transform)  # 3x3
    pixel_vec = np.array([pixel_x, pixel_y, 1.0])
    servo_vec = T @ pixel_vec

    return {
        "shoulder_pan": int(np.clip(servo_vec[0], 1200, 2800)),
        "shoulder_lift": int(np.clip(servo_vec[1], 1200, 2200)),
        "elbow_flex": int(np.clip(servo_vec[2], 2000, 3200)),
        "wrist_flex": 2048,
        "wrist_roll": 2048,
        "gripper": 1400,  # Open for pick
    }


def save_calibration(name: str, result: CalibrationResult) -> Path:
    """Save calibration to disk."""
    CITIZENRY_DIR.mkdir(parents=True, exist_ok=True)
    path = CITIZENRY_DIR / f"{name}.calibration.json"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(result.to_dict(), indent=2) + "\n")
        tmp.replace(path)
    except OSError:
        if tmp.exists():
            tmp.unlink()
        raise
    return path


def load_calibration(name: str) -> CalibrationResult | None:
    """Load calibration from disk."""
    path = CITIZENRY_DIR / f"{name}.calibration.json"
    try:
        return CalibrationResult.from_dict(json.loads(path.read_text()))
    except (OSError, json.JSONDecodeError):
        return None
