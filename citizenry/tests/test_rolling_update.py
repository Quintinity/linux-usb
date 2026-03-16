"""Tests for rolling policy updates."""

import pytest
from citizenry.rolling_update import RolloutPlan, CitizenRolloutState, RolloutStatus, RollingUpdater


class TestRolloutPlan:
    def test_create(self):
        plan = RolloutPlan(policy_type="law_update")
        assert plan.status == RolloutStatus.PENDING
        assert plan.progress == 0.0

    def test_progress(self):
        plan = RolloutPlan(
            citizens=[
                CitizenRolloutState(pubkey="a", name="a"),
                CitizenRolloutState(pubkey="b", name="b"),
            ],
            success_count=1,
        )
        assert plan.progress == 0.5

    def test_failure_rate(self):
        plan = RolloutPlan(success_count=3, failure_count=1)
        assert plan.failure_rate == 0.25

    def test_should_halt(self):
        plan = RolloutPlan(
            citizens=[CitizenRolloutState(pubkey=str(i), name=str(i)) for i in range(5)],
            failure_threshold=0.2,
            success_count=2,
            failure_count=1,
        )
        assert plan.should_halt()  # 33% > 20%

    def test_should_not_halt(self):
        plan = RolloutPlan(
            citizens=[CitizenRolloutState(pubkey=str(i), name=str(i)) for i in range(10)],
            failure_threshold=0.2,
            success_count=4,
            failure_count=0,
        )
        assert not plan.should_halt()

    def test_to_dict(self):
        plan = RolloutPlan(policy_type="law_update", success_count=2)
        d = plan.to_dict()
        assert d["policy_type"] == "law_update"
        assert d["success"] == 2


class TestRollingUpdater:
    def test_create_rollout(self):
        from unittest.mock import MagicMock
        gov = MagicMock()
        n1 = MagicMock(pubkey="aaa", name="arm-1")
        n2 = MagicMock(pubkey="bbb", name="arm-2")
        gov.neighbors = {"aaa": n1, "bbb": n2}

        updater = RollingUpdater(gov)
        plan = updater.create_rollout("law_update", {"law_id": "teleop_max_fps", "params": {"fps": 30}})

        assert len(plan.citizens) == 2
        assert plan.policy_type == "law_update"
        assert plan.status == RolloutStatus.PENDING

    def test_create_with_specific_citizens(self):
        from unittest.mock import MagicMock
        gov = MagicMock()
        gov.neighbors = {}

        updater = RollingUpdater(gov)
        plan = updater.create_rollout(
            "law_update",
            {"law_id": "test"},
            citizen_pubkeys=[("aaa", "arm-1")],
        )
        assert len(plan.citizens) == 1
        assert plan.citizens[0].name == "arm-1"
