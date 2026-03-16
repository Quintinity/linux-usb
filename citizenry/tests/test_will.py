"""Tests for dead citizen's will."""

import pytest
from citizenry.will import CitizenWill, create_will


class TestCitizenWill:
    def test_create(self):
        w = CitizenWill(citizen_name="arm-1", reason="shutdown")
        assert w.citizen_name == "arm-1"
        assert w.reason == "shutdown"

    def test_to_report_body(self):
        w = CitizenWill(
            citizen_name="arm-1",
            citizen_type="manipulator",
            current_task_id="task123",
            xp={"basic_grasp": 50},
        )
        body = w.to_report_body()
        assert body["type"] == "will"
        assert body["citizen"] == "arm-1"
        assert body["current_task_id"] == "task123"
        assert body["xp"] == {"basic_grasp": 50}

    def test_from_report_body(self):
        body = {
            "type": "will",
            "citizen": "cam-1",
            "citizen_type": "sensor",
            "reason": "thermal",
            "uptime_seconds": 3600.0,
        }
        w = CitizenWill.from_report_body(body)
        assert w.citizen_name == "cam-1"
        assert w.reason == "thermal"
        assert w.uptime_seconds == 3600.0

    def test_roundtrip(self):
        w = CitizenWill(
            citizen_name="test",
            current_task_id="t1",
            active_contracts=["c1", "c2"],
        )
        body = w.to_report_body()
        w2 = CitizenWill.from_report_body(body)
        assert w2.current_task_id == "t1"
        assert w2.active_contracts == ["c1", "c2"]


class TestCreateWill:
    def test_from_mock_citizen(self):
        from unittest.mock import MagicMock
        citizen = MagicMock()
        citizen.name = "arm-1"
        citizen.pubkey = "aabbccdd"
        citizen.citizen_type = "manipulator"
        citizen._current_task_id = "task123"
        citizen._current_task_type = "pick_and_place"
        citizen.contracts.get_active.return_value = []
        citizen.mycelium.active_warnings = []
        citizen.skill_tree.xp = {"basic_grasp": 100}
        citizen.start_time = 1000.0

        w = create_will(citizen)
        assert w.citizen_name == "arm-1"
        assert w.current_task_id == "task123"
        assert w.xp == {"basic_grasp": 100}
