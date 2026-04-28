"""Skill Trees & XP — citizens earn capabilities through experience.

Skills form a DAG. Each skill has prerequisites and an XP threshold.
XP is awarded on successful task completion.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SkillDef:
    """Definition of a single skill in the tree."""

    name: str
    description: str = ""
    prerequisites: list[str] = field(default_factory=list)
    xp_required: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> SkillDef:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class SkillTree:
    """Manages skill definitions and XP for a citizen."""

    def __init__(self, definitions: dict[str, SkillDef] | None = None):
        self.definitions: dict[str, SkillDef] = definitions or {}
        self.xp: dict[str, int] = {}

    def add_definition(self, skill: SkillDef) -> None:
        self.definitions[skill.name] = skill

    def has_skill(self, skill_name: str) -> bool:
        """Check if the citizen has unlocked a skill."""
        defn = self.definitions.get(skill_name)
        if defn is None:
            return False
        # Check XP threshold
        if self.xp.get(skill_name, 0) < defn.xp_required:
            return False
        # Check prerequisites
        for prereq in defn.prerequisites:
            if not self.has_skill(prereq):
                return False
        return True

    def unlocked_skills(self) -> list[str]:
        """Return all currently unlocked skills."""
        return [name for name in self.definitions if self.has_skill(name)]

    def skill_level(self, skill_name: str) -> int:
        """Return the skill level (0 if not unlocked, 1+ based on XP beyond threshold)."""
        if not self.has_skill(skill_name):
            return 0
        defn = self.definitions[skill_name]
        excess_xp = self.xp.get(skill_name, 0) - defn.xp_required
        # Level 1 at threshold, +1 per 100 XP beyond
        return 1 + max(0, excess_xp) // 100

    def award_xp(
        self,
        skill_name: str,
        base_xp: int = 10,
        task_difficulty: float = 1.0,
        success_quality: float = 1.0,
    ) -> int:
        """Award XP for a skill. Returns the amount awarded."""
        xp = int(base_xp * task_difficulty * success_quality)
        if xp <= 0:
            return 0
        self.xp[skill_name] = self.xp.get(skill_name, 0) + xp
        return xp

    def get_xp(self, skill_name: str) -> int:
        return self.xp.get(skill_name, 0)

    def to_dict(self) -> dict:
        return {
            "definitions": {k: v.to_dict() for k, v in self.definitions.items()},
            "xp": dict(self.xp),
        }

    @classmethod
    def from_dict(cls, d: dict) -> SkillTree:
        tree = cls()
        for name, defn_dict in d.get("definitions", {}).items():
            tree.definitions[name] = SkillDef.from_dict(defn_dict)
        tree.xp = dict(d.get("xp", {}))
        return tree

    def merge_definitions(self, definitions: dict[str, SkillDef]) -> None:
        """Merge new definitions without overwriting existing XP."""
        for name, defn in definitions.items():
            self.definitions[name] = defn


def default_manipulator_skills() -> dict[str, SkillDef]:
    """Default skill tree for manipulator citizens (SO-101 arms)."""
    return {
        "basic_movement": SkillDef(
            name="basic_movement",
            description="Basic joint movements and positioning",
            prerequisites=[],
            xp_required=0,
        ),
        "precise_movement": SkillDef(
            name="precise_movement",
            description="Precise positioning within 2mm accuracy",
            prerequisites=["basic_movement"],
            xp_required=100,
        ),
        "tool_use": SkillDef(
            name="tool_use",
            description="Manipulate tools and instruments",
            prerequisites=["precise_movement"],
            xp_required=500,
        ),
        "basic_grasp": SkillDef(
            name="basic_grasp",
            description="Grasp objects with the gripper",
            prerequisites=[],
            xp_required=0,
        ),
        "precise_grasp": SkillDef(
            name="precise_grasp",
            description="Grasp small or delicate objects",
            prerequisites=["basic_grasp"],
            xp_required=200,
        ),
        "delicate_grasp": SkillDef(
            name="delicate_grasp",
            description="Grasp fragile objects without damage",
            prerequisites=["precise_grasp"],
            xp_required=1000,
        ),
        "basic_gesture": SkillDef(
            name="basic_gesture",
            description="Simple gestures like waving",
            prerequisites=[],
            xp_required=0,
        ),
        "complex_gesture": SkillDef(
            name="complex_gesture",
            description="Multi-step choreographed gestures",
            prerequisites=["basic_gesture"],
            xp_required=150,
        ),
        "pick_and_place": SkillDef(
            name="pick_and_place",
            description="Pick up objects and place them at target locations",
            prerequisites=["basic_grasp", "basic_movement"],
            xp_required=50,
        ),
    }


def default_policy_skills() -> dict[str, SkillDef]:
    """Default skill tree for policy citizens (e.g. SmolVLA)."""
    return {
        "imitation": SkillDef(
            name="imitation",
            description="Behaviour cloning / imitation learning policies",
            prerequisites=[],
            xp_required=0,
        ),
        "imitation:smolvla_base": SkillDef(
            name="imitation:smolvla_base",
            description="SmolVLA 450M pretrained on SO-100/101 community data",
            prerequisites=["imitation"],
            xp_required=0,
        ),
    }


def default_camera_skills() -> dict[str, SkillDef]:
    """Default skill tree for camera citizens."""
    return {
        "frame_capture": SkillDef(
            name="frame_capture",
            description="Capture single frames on demand",
            prerequisites=[],
            xp_required=0,
        ),
        "color_detection": SkillDef(
            name="color_detection",
            description="Detect colored regions in frames",
            prerequisites=["frame_capture"],
            xp_required=0,
        ),
        "object_tracking": SkillDef(
            name="object_tracking",
            description="Track objects across frames",
            prerequisites=["color_detection"],
            xp_required=100,
        ),
    }
