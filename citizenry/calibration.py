"""Camera-to-Arm Calibration — guided, robust, any camera angle.

Detects gripper tip via frame differencing (no markers needed), guides
camera placement, collects calibration points, fits homography with
RANSAC, validates, and persists. Works overhead, angled, or side-mounted.

Usage:
    procedure = CalibrationProcedure(arm_bus, camera_cap)
    result = await procedure.run()
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .persistence import CITIZENRY_DIR


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class CalibrationPoint:
    """A single pixel ↔ servo correspondence."""
    pixel_x: float
    pixel_y: float
    servo_pan: int
    servo_lift: int
    servo_elbow: int
    is_inlier: bool = True


@dataclass
class PlacementScore:
    """Result of camera placement evaluation."""
    coverage_pct: float = 0.0       # Workspace area / frame area
    corners_visible: int = 0        # Out of 4
    centered: bool = False
    overall: str = "unknown"        # "good", "adjust", "bad"
    suggestions: list[str] = field(default_factory=list)


@dataclass
class CalibrationResult:
    """Result of a calibration procedure."""
    points: list[CalibrationPoint] = field(default_factory=list)
    homography: list[list[float]] | None = None  # 3x3 homography matrix
    inlier_count: int = 0
    outlier_count: int = 0
    reprojection_error: float = 0.0
    validation_error: float = 0.0
    placement: PlacementScore | None = None
    camera_resolution: tuple[int, int] = (640, 480)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "points": [
                {"px": p.pixel_x, "py": p.pixel_y,
                 "pan": p.servo_pan, "lift": p.servo_lift, "elbow": p.servo_elbow,
                 "inlier": p.is_inlier}
                for p in self.points
            ],
            "homography": self.homography,
            "inlier_count": self.inlier_count,
            "outlier_count": self.outlier_count,
            "reprojection_error": self.reprojection_error,
            "validation_error": self.validation_error,
            "camera_resolution": list(self.camera_resolution),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CalibrationResult:
        points = [
            CalibrationPoint(
                pixel_x=p["px"], pixel_y=p["py"],
                servo_pan=p["pan"], servo_lift=p["lift"], servo_elbow=p["elbow"],
                is_inlier=p.get("inlier", True),
            )
            for p in d.get("points", [])
        ]
        res = d.get("camera_resolution", [640, 480])
        return cls(
            points=points,
            homography=d.get("homography"),
            inlier_count=d.get("inlier_count", 0),
            outlier_count=d.get("outlier_count", 0),
            reprojection_error=d.get("reprojection_error", 0.0),
            validation_error=d.get("validation_error", 0.0),
            camera_resolution=tuple(res),
            timestamp=d.get("timestamp", 0.0),
        )


# ── Calibration poses ────────────────────────────────────────────────────────
# 10 poses spread across the workspace: 6 grid + 4 extra for robustness

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]

HOME = {"shoulder_pan": 2048, "shoulder_lift": 1400, "elbow_flex": 3000,
        "wrist_flex": 2048, "wrist_roll": 2048, "gripper": 1400}

CALIBRATION_POSES = [
    # Row 1: near (high lift, low elbow = close to base)
    {"shoulder_pan": 1700, "shoulder_lift": 1600, "elbow_flex": 2500},
    {"shoulder_pan": 2048, "shoulder_lift": 1600, "elbow_flex": 2500},
    {"shoulder_pan": 2400, "shoulder_lift": 1600, "elbow_flex": 2500},
    # Row 2: far (higher lift, lower elbow = extended)
    {"shoulder_pan": 1700, "shoulder_lift": 1800, "elbow_flex": 2200},
    {"shoulder_pan": 2048, "shoulder_lift": 1800, "elbow_flex": 2200},
    {"shoulder_pan": 2400, "shoulder_lift": 1800, "elbow_flex": 2200},
    # Extra: diagonal and mid-range for better coverage
    {"shoulder_pan": 1850, "shoulder_lift": 1700, "elbow_flex": 2350},
    {"shoulder_pan": 2250, "shoulder_lift": 1700, "elbow_flex": 2350},
    {"shoulder_pan": 1850, "shoulder_lift": 1500, "elbow_flex": 2650},
    {"shoulder_pan": 2250, "shoulder_lift": 1500, "elbow_flex": 2650},
]

# Workspace corners for placement check (4 extremes)
CORNER_POSES = [
    {"shoulder_pan": 1600, "shoulder_lift": 1600, "elbow_flex": 2400},  # far-left
    {"shoulder_pan": 2500, "shoulder_lift": 1600, "elbow_flex": 2400},  # far-right
    {"shoulder_pan": 1600, "shoulder_lift": 1800, "elbow_flex": 2200},  # near-left
    {"shoulder_pan": 2500, "shoulder_lift": 1800, "elbow_flex": 2200},  # near-right
]

# Validation poses (NOT used in calibration — for testing accuracy)
VALIDATION_POSES = [
    {"shoulder_pan": 1900, "shoulder_lift": 1650, "elbow_flex": 2450},
    {"shoulder_pan": 2200, "shoulder_lift": 1750, "elbow_flex": 2300},
    {"shoulder_pan": 2048, "shoulder_lift": 1700, "elbow_flex": 2400},
]


def _full_pose(partial: dict) -> dict:
    """Fill in missing motors with defaults."""
    return {**HOME, **partial, "gripper": 1400}


# ── Gripper Tip Detection ────────────────────────────────────────────────────

class GripperDetector:
    """Detect gripper tip position via frame differencing."""

    GRIPPER_OPEN = 1400
    GRIPPER_CLOSED = 2500
    DIFF_THRESHOLD = 30
    MIN_CONTOUR_AREA = 100

    @staticmethod
    def detect(frame_open: np.ndarray, frame_closed: np.ndarray) -> tuple[float, float] | None:
        """Detect gripper tip from open vs closed frame difference.

        Returns (pixel_x, pixel_y) or None if detection fails.
        """
        if frame_open is None or frame_closed is None:
            return None

        # Convert to grayscale
        gray_open = cv2.cvtColor(frame_open, cv2.COLOR_BGR2GRAY)
        gray_closed = cv2.cvtColor(frame_closed, cv2.COLOR_BGR2GRAY)

        # Absolute difference
        diff = cv2.absdiff(gray_open, gray_closed)

        # Threshold
        _, thresh = cv2.threshold(diff, GripperDetector.DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)

        # Morphological cleanup
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Filter by minimum area
        valid = [c for c in contours if cv2.contourArea(c) > GripperDetector.MIN_CONTOUR_AREA]
        if not valid:
            return None

        # Largest contour = gripper region
        largest = max(valid, key=cv2.contourArea)
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        return (cx, cy)

    @staticmethod
    def detect_by_color(
        frame: np.ndarray,
        lower_hsv: tuple = (35, 100, 100),
        upper_hsv: tuple = (85, 255, 255),
    ) -> tuple[float, float] | None:
        """Fallback: detect gripper tip by color (green tape).

        Returns (pixel_x, pixel_y) or None.
        """
        if frame is None:
            return None

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array(lower_hsv), np.array(upper_hsv))

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in contours if cv2.contourArea(c) > 200]
        if not valid:
            return None

        largest = max(valid, key=cv2.contourArea)
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        return (M["m10"] / M["m00"], M["m01"] / M["m00"])


# ── Camera Placement Guide ───────────────────────────────────────────────────

class CameraPlacementGuide:
    """Evaluate and guide camera placement for calibration."""

    @staticmethod
    def evaluate(
        corner_pixels: list[tuple[float, float] | None],
        frame_width: int = 640,
        frame_height: int = 480,
    ) -> PlacementScore:
        """Evaluate camera placement from detected corner positions.

        Args:
            corner_pixels: List of 4 pixel positions (or None if not visible)
            frame_width, frame_height: Camera resolution
        """
        score = PlacementScore()
        visible = [p for p in corner_pixels if p is not None]
        score.corners_visible = len(visible)

        if score.corners_visible < 2:
            score.overall = "bad"
            score.suggestions.append("Camera can't see the workspace. Point it at the arm's working area.")
            return score

        if score.corners_visible < 4:
            score.overall = "adjust"
            score.suggestions.append(f"Only {score.corners_visible}/4 workspace corners visible. Move camera further away or use wider angle.")

        # Compute workspace bounding box in pixel space
        xs = [p[0] for p in visible]
        ys = [p[1] for p in visible]
        ws_width = max(xs) - min(xs)
        ws_height = max(ys) - min(ys)
        ws_area = ws_width * ws_height
        frame_area = frame_width * frame_height
        score.coverage_pct = (ws_area / frame_area) * 100

        if score.coverage_pct < 15:
            score.suggestions.append("Camera too far — workspace is tiny in frame. Move closer.")
        elif score.coverage_pct > 80:
            score.suggestions.append("Camera too close — workspace fills entire frame. Move further away.")

        # Check centering
        ws_cx = (min(xs) + max(xs)) / 2
        ws_cy = (min(ys) + max(ys)) / 2
        frame_cx = frame_width / 2
        frame_cy = frame_height / 2
        off_x = abs(ws_cx - frame_cx) / frame_width
        off_y = abs(ws_cy - frame_cy) / frame_height

        if off_x > 0.25:
            direction = "right" if ws_cx > frame_cx else "left"
            score.suggestions.append(f"Workspace is off-center. Shift camera {direction}.")
        if off_y > 0.25:
            direction = "down" if ws_cy > frame_cy else "up"
            score.suggestions.append(f"Workspace is off-center. Shift camera {direction}.")

        score.centered = off_x < 0.25 and off_y < 0.25

        if score.corners_visible >= 3 and 15 <= score.coverage_pct <= 80 and score.centered:
            score.overall = "good"
        elif not score.suggestions:
            score.overall = "good"
        else:
            score.overall = "adjust" if score.corners_visible >= 3 else "bad"

        return score


# ── Homography Fitting ───────────────────────────────────────────────────────

def fit_homography(
    pixel_points: list[tuple[float, float]],
    servo_points: list[tuple[int, int, int]],
    ransac_threshold: float = 5.0,
) -> tuple[list[list[float]] | None, int, int, float]:
    """Fit a homography from pixel space to servo space using RANSAC.

    For the servo→pixel direction we fit pixel→(pan, lift) as a 2D homography,
    then handle elbow separately with a linear fit.

    Args:
        pixel_points: List of (x, y) pixel positions
        servo_points: List of (pan, lift, elbow) servo positions
        ransac_threshold: RANSAC inlier threshold

    Returns:
        (homography_3x3, inlier_count, outlier_count, reprojection_error)
    """
    n = len(pixel_points)
    if n < 4:
        return None, 0, n, float('inf')

    src = np.array(pixel_points, dtype=np.float32).reshape(-1, 1, 2)
    # We map pixel→(pan, lift) as a 2D homography
    dst_2d = np.array([(p, l) for p, l, _ in servo_points], dtype=np.float32).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src, dst_2d, cv2.RANSAC, ransac_threshold)
    if H is None:
        return None, 0, n, float('inf')

    inlier_mask = mask.ravel().tolist()
    inlier_count = sum(inlier_mask)
    outlier_count = n - inlier_count

    # Compute reprojection error on inliers
    predicted = cv2.perspectiveTransform(src, H)
    errors = np.sqrt(np.sum((predicted.reshape(-1, 2) - dst_2d.reshape(-1, 2)) ** 2, axis=1))
    inlier_errors = [errors[i] for i in range(n) if inlier_mask[i]]
    reproj_error = float(np.mean(inlier_errors)) if inlier_errors else float('inf')

    # Fit elbow separately (linear from pixel coords)
    # Use inliers only
    inlier_pixels = [pixel_points[i] for i in range(n) if inlier_mask[i]]
    inlier_elbows = [servo_points[i][2] for i in range(n) if inlier_mask[i]]

    if len(inlier_pixels) >= 3:
        A = np.array([[px, py, 1.0] for px, py in inlier_pixels])
        b = np.array(inlier_elbows)
        elbow_coeffs, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    else:
        elbow_coeffs = np.array([0, 0, 2500])  # Fallback: constant

    # Pack into a combined transform:
    # Row 0-2: 3x3 homography for (pan, lift)
    # Row 3: elbow linear coefficients [a, b, c] where elbow = a*px + b*py + c
    combined = np.zeros((4, 3))
    combined[:3, :3] = H
    combined[3, :] = elbow_coeffs

    return combined.tolist(), inlier_count, outlier_count, reproj_error


def apply_homography(
    pixel_x: float,
    pixel_y: float,
    transform: list[list[float]],
) -> dict:
    """Apply calibrated homography to map pixel → servo positions."""
    T = np.array(transform)

    # Homography for pan, lift (rows 0-2)
    H = T[:3, :3]
    pt = np.array([pixel_x, pixel_y, 1.0])
    result = H @ pt
    pan = result[0] / result[2]
    lift = result[1] / result[2]

    # Linear for elbow (row 3)
    elbow_coeffs = T[3, :]
    elbow = elbow_coeffs[0] * pixel_x + elbow_coeffs[1] * pixel_y + elbow_coeffs[2]

    return {
        "shoulder_pan": int(np.clip(pan, 1200, 2800)),
        "shoulder_lift": int(np.clip(lift, 1200, 2200)),
        "elbow_flex": int(np.clip(elbow, 2000, 3200)),
        "wrist_flex": 2048,
        "wrist_roll": 2048,
        "gripper": 1400,
    }


# ── Validation ───────────────────────────────────────────────────────────────

def compute_validation_error(
    pixel_points: list[tuple[float, float]],
    servo_points: list[tuple[int, int, int]],
    transform: list[list[float]],
) -> float:
    """Compute mean servo position error on validation points."""
    if not pixel_points or not transform:
        return float('inf')

    errors = []
    for (px, py), (true_pan, true_lift, true_elbow) in zip(pixel_points, servo_points):
        predicted = apply_homography(px, py, transform)
        err = np.sqrt(
            (predicted["shoulder_pan"] - true_pan) ** 2 +
            (predicted["shoulder_lift"] - true_lift) ** 2 +
            (predicted["elbow_flex"] - true_elbow) ** 2
        )
        errors.append(err)
    return float(np.mean(errors))


# ── Persistence ──────────────────────────────────────────────────────────────

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
