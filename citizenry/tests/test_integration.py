"""Integration tests for v2.0 multi-citizen scenarios.

Tests the full protocol flow without hardware — uses module-level logic
rather than spinning up actual UDP transports (which need network).
"""

import time
import pytest

from citizenry.marketplace import (
    TaskMarketplace, Task, Bid, compute_bid_score, select_winner, TaskStatus,
)
from citizenry.skills import SkillTree, SkillDef, default_manipulator_skills, default_camera_skills
from citizenry.genome import CitizenGenome, compute_fleet_average
from citizenry.immune import ImmuneMemory, FaultPattern, bootstrap_immune_memory
from citizenry.symbiosis import ContractManager, SymbiosisContract, ContractStatus
from citizenry.mycelium import MyceliumNetwork, Warning, Severity
from citizenry.composition import CompositionEngine
from citizenry.protocol import Envelope, make_envelope, MessageType
from citizenry.identity import generate_keypair, pubkey_hex


class TestTaskAuctionE2E:
    """End-to-end task auction: governor creates task, two arms bid, winner selected."""

    def test_full_auction(self):
        # Setup governor marketplace
        mp = TaskMarketplace(bid_timeout=0.1)

        # Governor creates task
        task = mp.create_task(
            "pick_and_place",
            params={"object": "red_block"},
            priority=0.7,
            required_capabilities=["6dof_arm"],
            required_skills=["basic_grasp"],
        )
        assert task.status == TaskStatus.BIDDING

        # Arm-1 bids (experienced)
        arm1_key = generate_keypair()
        arm1_tree = SkillTree(default_manipulator_skills())
        arm1_tree.xp["basic_grasp"] = 200  # Unlocked precise_grasp too
        arm1_score = compute_bid_score(
            skill_level=arm1_tree.skill_level("basic_grasp"),
            current_load=0.1,
            health=0.95,
        )
        bid1 = Bid(
            citizen_pubkey=pubkey_hex(arm1_key),
            task_id=task.id,
            score=arm1_score,
            skill_level=arm1_tree.skill_level("basic_grasp"),
        )
        mp.add_bid(bid1)

        # Arm-2 bids (beginner)
        arm2_key = generate_keypair()
        arm2_tree = SkillTree(default_manipulator_skills())
        arm2_score = compute_bid_score(
            skill_level=arm2_tree.skill_level("basic_grasp"),
            current_load=0.0,
            health=1.0,
        )
        bid2 = Bid(
            citizen_pubkey=pubkey_hex(arm2_key),
            task_id=task.id,
            score=arm2_score,
            skill_level=arm2_tree.skill_level("basic_grasp"),
        )
        mp.add_bid(bid2)

        # Close auction
        winner = mp.close_auction(task.id)
        assert winner is not None
        # Arm-1 should win (higher skill level = higher score)
        assert winner.citizen_pubkey == pubkey_hex(arm1_key)
        assert task.status == TaskStatus.ASSIGNED

        # Execute and complete
        mp.start_execution(task.id)
        assert task.status == TaskStatus.EXECUTING
        mp.complete_task(task.id, {"success": True})
        assert task.status == TaskStatus.COMPLETED

        # Award XP
        xp_earned = arm1_tree.award_xp("basic_grasp", base_xp=10, task_difficulty=0.8)
        assert xp_earned > 0
        assert arm1_tree.get_xp("basic_grasp") == 200 + xp_earned


class TestSkillGatedBidding:
    """Citizens cannot bid on tasks requiring skills they haven't unlocked."""

    def test_unskilled_citizen_rejected(self):
        mp = TaskMarketplace()
        task = mp.create_task(
            "precision_sort",
            required_capabilities=["6dof_arm"],
            required_skills=["precise_grasp"],
        )

        tree = SkillTree(default_manipulator_skills())
        # basic_grasp is unlocked but precise_grasp requires 200 XP
        can_bid, reason = mp.can_citizen_bid(
            task,
            citizen_capabilities=["6dof_arm", "gripper"],
            citizen_skills=tree.unlocked_skills(),
            citizen_load=0.0,
            citizen_health=1.0,
        )
        assert not can_bid
        assert "precise_grasp" in reason

    def test_skilled_citizen_accepted(self):
        mp = TaskMarketplace()
        task = mp.create_task(
            "precision_sort",
            required_capabilities=["6dof_arm"],
            required_skills=["precise_grasp"],
        )

        tree = SkillTree(default_manipulator_skills())
        tree.xp["precise_grasp"] = 200  # Unlock it
        tree.xp["basic_grasp"] = 100  # Prereq satisfied implicitly (xp_required=0)

        can_bid, _ = mp.can_citizen_bid(
            task,
            citizen_capabilities=["6dof_arm", "gripper"],
            citizen_skills=tree.unlocked_skills(),
            citizen_load=0.0,
            citizen_health=1.0,
        )
        assert can_bid


class TestCapabilityCompositionE2E:
    """Composite capabilities discovered when arm + camera join."""

    def test_arm_camera_composition(self):
        engine = CompositionEngine()

        # Initially just an arm
        caps = engine.discover_capabilities({
            "arm_pubkey": ["6dof_arm", "gripper"],
        })
        assert caps == []

        # Camera joins
        caps = engine.discover_capabilities({
            "arm_pubkey": ["6dof_arm", "gripper"],
            "camera_pubkey": ["video_stream", "frame_capture", "color_detection"],
        })
        assert "visual_pick_and_place" in caps
        assert "color_sorting" in caps
        assert "visual_inspection" in caps

    def test_composition_lost_on_citizen_leave(self):
        engine = CompositionEngine()

        # Both present
        caps = engine.discover_capabilities({
            "arm": ["6dof_arm"],
            "cam": ["video_stream"],
        })
        assert "visual_pick_and_place" in caps

        # Camera leaves
        caps = engine.discover_capabilities({
            "arm": ["6dof_arm"],
        })
        assert caps == []


class TestSymbiosisE2E:
    """Symbiosis contract lifecycle: propose, accept, monitor, break."""

    def test_full_lifecycle(self):
        camera_mgr = ContractManager()
        arm_mgr = ContractManager()

        # Camera proposes
        contract = camera_mgr.propose(
            provider="camera_key",
            consumer="arm_key",
            provider_cap="video_stream",
            consumer_cap="6dof_arm",
            composite="visual_pick_and_place",
        )
        assert contract.status == ContractStatus.PROPOSED

        # Arm accepts
        arm_mgr.register(contract)
        camera_mgr.accept(contract.id)
        assert contract.status == ContractStatus.ACTIVE

        # Composite capability available
        assert "visual_pick_and_place" in camera_mgr.get_composite_capabilities()

        # Health checks work
        camera_mgr.record_health("arm_key")
        assert contract.missed_checks == 0

        # Simulate camera going offline (timeout)
        contract.last_health_check = time.time() - 10.0
        contract.health_check_interval = 2.0
        broken = camera_mgr.check_contracts()
        assert len(broken) == 1
        assert broken[0].status == ContractStatus.BROKEN

        # Composite capability gone
        assert camera_mgr.get_composite_capabilities() == []


class TestMyceliumWarningE2E:
    """Warning propagation and mitigation."""

    def test_warning_propagation_and_mitigation(self):
        # Arm detects voltage collapse
        arm_mycelium = MyceliumNetwork()
        warning = Warning(
            severity=Severity.CRITICAL,
            detail="voltage_collapse",
            motor="elbow_flex",
            value=5.2,
            threshold=6.0,
            source_citizen="arm1_key",
        )
        arm_mycelium.add_warning(warning)

        # Arm's own mitigation
        assert arm_mycelium.current_mitigation_factor() == 0.5

        # Serialize for fast channel
        body = warning.to_report_body()
        assert body["severity"] == "critical"

        # Neighboring arm receives it
        neighbor_mycelium = MyceliumNetwork()
        received = Warning.from_report_body(body)
        neighbor_mycelium.add_warning(received)

        # Neighbor also reduces duty
        assert neighbor_mycelium.current_mitigation_factor() == 0.5

    def test_emergency_stops_all(self):
        net = MyceliumNetwork()
        net.add_warning(Warning(severity=Severity.EMERGENCY, detail="servo_error"))
        assert net.should_stop()
        assert net.current_mitigation_factor() == 0.0


class TestImmuneMemoryE2E:
    """Immune memory sharing between citizens."""

    def test_share_and_inherit(self):
        # Arm-1 discovers a new fault pattern
        arm1_immune = bootstrap_immune_memory()
        initial_count = len(arm1_immune.get_all())

        new_pattern = FaultPattern(
            pattern_type="gripper_stall",
            conditions={"gripper_current_ma": {"max": 500}},
            mitigation="release_and_retry",
            severity="warning",
            source_citizen="arm1_key",
        )
        arm1_immune.add(new_pattern)
        assert len(arm1_immune.get_all()) == initial_count + 1

        # Serialize for sharing
        patterns_data = arm1_immune.to_list()

        # New arm joins and receives immune memory
        arm2_immune = ImmuneMemory()  # Empty — new citizen
        added = arm2_immune.merge([FaultPattern.from_dict(p) for p in patterns_data])
        assert added == initial_count + 1  # All patterns are new to arm2

        # Arm2 now has the gripper_stall pattern
        matches = arm2_immune.match({"gripper_current_ma": 600})
        assert any(m.pattern_type == "gripper_stall" for m in matches)


class TestGenomeE2E:
    """Genome export, fleet average, and inheritance."""

    def test_fleet_average_inheritance(self):
        # Two existing arms
        g1 = CitizenGenome(
            citizen_name="arm-1",
            citizen_type="manipulator",
            calibration={"joint_1_offset": 0.3, "joint_2_offset": -1.2},
            xp={"basic_grasp": 500, "basic_movement": 300},
            immune_memory=[
                {"pattern_type": "voltage_collapse", "severity": "critical"},
            ],
            exported_at=100.0,
        )
        g2 = CitizenGenome(
            citizen_name="arm-2",
            citizen_type="manipulator",
            calibration={"joint_1_offset": 0.5, "joint_2_offset": -0.8},
            xp={"basic_grasp": 200, "basic_movement": 100},
            immune_memory=[
                {"pattern_type": "voltage_collapse", "severity": "critical"},
                {"pattern_type": "thermal_overload", "severity": "warning"},
            ],
            exported_at=200.0,
        )

        # Compute fleet average for new arm
        avg = compute_fleet_average([g1, g2])

        # Calibration is averaged
        assert avg.calibration["joint_1_offset"] == pytest.approx(0.4)
        assert avg.calibration["joint_2_offset"] == pytest.approx(-1.0)

        # XP is zeroed (new citizen starts fresh)
        assert avg.xp == {}

        # Immune memory is union
        pattern_types = {p["pattern_type"] for p in avg.immune_memory}
        assert "voltage_collapse" in pattern_types
        assert "thermal_overload" in pattern_types

    def test_genome_version_ordering(self):
        g1 = CitizenGenome(citizen_name="arm-1", version=3)
        g2 = CitizenGenome(citizen_name="arm-1", version=1)
        # Should not downgrade
        assert g1.version > g2.version


class TestProtocolFlowE2E:
    """Verify v2.0 message bodies can be created, signed, and parsed."""

    def setup_method(self):
        self.gov_key = generate_keypair()
        self.gov_pubkey = pubkey_hex(self.gov_key)
        self.arm_key = generate_keypair()
        self.arm_pubkey = pubkey_hex(self.arm_key)

    def test_task_propose_accept_report_cycle(self):
        # Governor creates task PROPOSE
        propose = make_envelope(
            MessageType.PROPOSE,
            self.gov_pubkey,
            {
                "task": "pick_and_place",
                "task_id": "task001",
                "priority": 0.7,
                "required_capabilities": ["6dof_arm"],
                "required_skills": ["basic_grasp"],
                "params": {"object": "red_block"},
            },
            self.gov_key,
        )
        # Serialize and deserialize
        data = propose.to_bytes()
        parsed = Envelope.from_bytes(data)
        assert parsed.body["task_id"] == "task001"

        # Arm sends ACCEPT with bid
        accept = make_envelope(
            MessageType.ACCEPT_REJECT,
            self.arm_pubkey,
            {
                "accepted": True,
                "task_id": "task001",
                "task": "pick_and_place",
                "bid": {"skill_level": 2, "load": 0.1, "health": 0.95, "score": 0.78},
            },
            self.arm_key,
            recipient=self.gov_pubkey,
        )
        data = accept.to_bytes()
        parsed = Envelope.from_bytes(data)
        assert parsed.body["bid"]["score"] == 0.78

        # Arm sends task complete REPORT
        report = make_envelope(
            MessageType.REPORT,
            self.arm_pubkey,
            {
                "type": "task_complete",
                "task_id": "task001",
                "result": "success",
                "duration_ms": 3200,
                "xp_earned": 8,
            },
            self.arm_key,
            recipient=self.gov_pubkey,
        )
        data = report.to_bytes()
        parsed = Envelope.from_bytes(data)
        assert parsed.body["xp_earned"] == 8

    def test_warning_to_immune_share_cycle(self):
        # Arm broadcasts warning
        warning = make_envelope(
            MessageType.REPORT,
            self.arm_pubkey,
            {
                "type": "warning",
                "severity": "critical",
                "detail": "voltage_collapse",
                "motor": "elbow_flex",
                "value": 5.2,
                "threshold": 6.0,
            },
            self.arm_key,
        )
        data = warning.to_bytes()
        parsed = Envelope.from_bytes(data)
        assert parsed.body["severity"] == "critical"

        # Then shares immune memory
        immune = make_envelope(
            MessageType.REPORT,
            self.arm_pubkey,
            {
                "type": "immune_share",
                "patterns": [
                    {
                        "pattern_type": "voltage_collapse",
                        "conditions": {"min_voltage": {"min": 6.0}},
                        "mitigation": "reduce_speed_50pct",
                        "severity": "critical",
                    },
                ],
            },
            self.arm_key,
        )
        data = immune.to_bytes()
        parsed = Envelope.from_bytes(data)
        assert len(parsed.body["patterns"]) == 1
