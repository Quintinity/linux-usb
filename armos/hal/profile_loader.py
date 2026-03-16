"""Robot Profile Loader — load and match profiles from JSON templates.

Profiles are genome templates that define motor configurations, protection
limits, capabilities, and skills for known robot models.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .servo_driver import MotorInfo


PROFILES_DIR = Path(__file__).parent / "profiles"


@dataclass
class MotorConfig:
    """Configuration for a single motor in a profile."""
    id: int
    model: str
    range: tuple[int, int] = (0, 4095)
    home: int = 2048


@dataclass
class RobotProfile:
    """A complete robot profile loaded from JSON."""
    name: str
    driver: str  # "feetech", "dynamixel"
    motor_count: int
    motors: dict[str, MotorConfig] = field(default_factory=dict)
    protection: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)

    def motor_ids(self) -> list[int]:
        return [m.id for m in self.motors.values()]

    def home_positions(self) -> dict[str, int]:
        return {name: m.home for name, m in self.motors.items()}

    def to_genome_dict(self) -> dict:
        """Convert to a genome-compatible dict."""
        return {
            "citizen_name": self.name.lower().replace(" ", "-"),
            "citizen_type": "manipulator",
            "hardware": {
                "profile": self.name,
                "driver": self.driver,
                "motor_count": self.motor_count,
            },
            "calibration": self.home_positions(),
            "protection": self.protection,
        }


def load_profile(name: str) -> RobotProfile | None:
    """Load a profile by name (e.g., 'so101', 'koch_v1')."""
    path = PROFILES_DIR / f"{name}.json"
    if not path.exists():
        return None
    return _parse_profile(json.loads(path.read_text()))


def load_all_profiles() -> list[RobotProfile]:
    """Load all available profiles."""
    profiles = []
    for path in PROFILES_DIR.glob("*.json"):
        try:
            profiles.append(_parse_profile(json.loads(path.read_text())))
        except Exception:
            continue
    return profiles


def match_profile(
    driver_type: str,
    motors: list[MotorInfo],
) -> RobotProfile | None:
    """Match detected motors against known profiles.

    Args:
        driver_type: "feetech" or "dynamixel"
        motors: List of detected motors

    Returns:
        Best matching profile, or None if no match.
    """
    profiles = load_all_profiles()
    motor_count = len(motors)

    for profile in profiles:
        if profile.driver != driver_type:
            continue
        if profile.motor_count != motor_count:
            continue
        # Check motor IDs match
        detected_ids = sorted(m.id for m in motors)
        profile_ids = sorted(profile.motor_ids())
        if detected_ids == profile_ids:
            return profile

    # Fallback: match by driver + motor count only
    for profile in profiles:
        if profile.driver == driver_type and profile.motor_count == motor_count:
            return profile

    return None


def _parse_profile(data: dict) -> RobotProfile:
    """Parse a profile from JSON data."""
    motors = {}
    for name, config in data.get("motors", {}).items():
        motors[name] = MotorConfig(
            id=config["id"],
            model=config.get("model", "unknown"),
            range=tuple(config.get("range", [0, 4095])),
            home=config.get("home", 2048),
        )

    return RobotProfile(
        name=data["name"],
        driver=data["driver"],
        motor_count=data.get("motor_count", len(motors)),
        motors=motors,
        protection=data.get("protection", {}),
        capabilities=data.get("capabilities", []),
        skills=data.get("skills", []),
    )
