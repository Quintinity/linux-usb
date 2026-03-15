"""Tests for skill trees and XP tracking."""

import pytest
from citizenry.skills import (
    SkillDef, SkillTree, default_manipulator_skills, default_camera_skills,
)


class TestSkillDef:
    def test_roundtrip(self):
        s = SkillDef(name="grasp", description="Grasp things", prerequisites=["move"], xp_required=100)
        d = s.to_dict()
        s2 = SkillDef.from_dict(d)
        assert s2.name == "grasp"
        assert s2.prerequisites == ["move"]
        assert s2.xp_required == 100


class TestSkillTree:
    def test_base_skills_unlocked(self):
        tree = SkillTree(default_manipulator_skills())
        assert tree.has_skill("basic_movement")
        assert tree.has_skill("basic_grasp")
        assert tree.has_skill("basic_gesture")

    def test_advanced_skills_locked(self):
        tree = SkillTree(default_manipulator_skills())
        assert not tree.has_skill("precise_movement")
        assert not tree.has_skill("tool_use")
        assert not tree.has_skill("delicate_grasp")

    def test_unlock_with_xp(self):
        tree = SkillTree(default_manipulator_skills())
        assert not tree.has_skill("precise_movement")
        tree.xp["precise_movement"] = 100
        assert tree.has_skill("precise_movement")

    def test_prerequisite_chain(self):
        tree = SkillTree(default_manipulator_skills())
        # tool_use requires precise_movement which requires basic_movement
        tree.xp["tool_use"] = 500
        assert not tree.has_skill("tool_use")  # Missing prereq
        tree.xp["precise_movement"] = 100
        assert tree.has_skill("tool_use")

    def test_award_xp(self):
        tree = SkillTree(default_manipulator_skills())
        awarded = tree.award_xp("basic_grasp", base_xp=10, task_difficulty=1.0, success_quality=1.0)
        assert awarded == 10
        assert tree.get_xp("basic_grasp") == 10

    def test_award_xp_with_difficulty(self):
        tree = SkillTree(default_manipulator_skills())
        awarded = tree.award_xp("basic_grasp", base_xp=10, task_difficulty=0.5, success_quality=0.8)
        assert awarded == 4  # int(10 * 0.5 * 0.8)

    def test_award_zero_xp(self):
        tree = SkillTree(default_manipulator_skills())
        awarded = tree.award_xp("basic_grasp", base_xp=0)
        assert awarded == 0

    def test_skill_level(self):
        tree = SkillTree(default_manipulator_skills())
        assert tree.skill_level("basic_movement") == 1  # Unlocked at 0 XP
        tree.xp["basic_movement"] = 250
        assert tree.skill_level("basic_movement") == 3  # 1 + 250//100

    def test_skill_level_locked(self):
        tree = SkillTree(default_manipulator_skills())
        assert tree.skill_level("precise_movement") == 0

    def test_unlocked_skills(self):
        tree = SkillTree(default_manipulator_skills())
        unlocked = tree.unlocked_skills()
        assert "basic_movement" in unlocked
        assert "basic_grasp" in unlocked
        assert "precise_movement" not in unlocked

    def test_serialization(self):
        tree = SkillTree(default_manipulator_skills())
        tree.xp["basic_grasp"] = 50
        d = tree.to_dict()
        tree2 = SkillTree.from_dict(d)
        assert tree2.get_xp("basic_grasp") == 50
        assert tree2.has_skill("basic_movement")

    def test_merge_definitions(self):
        tree = SkillTree(default_manipulator_skills())
        tree.xp["basic_grasp"] = 100
        new_defs = default_camera_skills()
        tree.merge_definitions(new_defs)
        assert "frame_capture" in tree.definitions
        assert tree.get_xp("basic_grasp") == 100  # Preserved

    def test_pick_and_place_requires_two_prereqs(self):
        tree = SkillTree(default_manipulator_skills())
        # pick_and_place requires basic_grasp AND basic_movement (both at 0 XP)
        tree.xp["pick_and_place"] = 50
        assert tree.has_skill("pick_and_place")


class TestDefaultTrees:
    def test_manipulator_tree_valid(self):
        defs = default_manipulator_skills()
        assert len(defs) >= 7
        # All prerequisites reference existing skills
        for skill in defs.values():
            for prereq in skill.prerequisites:
                assert prereq in defs, f"{skill.name} references unknown prereq {prereq}"

    def test_camera_tree_valid(self):
        defs = default_camera_skills()
        assert len(defs) >= 2
        for skill in defs.values():
            for prereq in skill.prerequisites:
                assert prereq in defs
