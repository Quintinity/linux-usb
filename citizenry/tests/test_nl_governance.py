"""Tests for natural language governance."""

import pytest
from citizenry.nl_governance import parse_command, GovernanceAction, GovernorAide


class TestParseCommand:
    # Emergency stop
    def test_stop(self):
        a = parse_command("stop")
        assert a.action_type == "emergency_stop"

    def test_halt(self):
        a = parse_command("halt")
        assert a.action_type == "emergency_stop"

    def test_estop(self):
        a = parse_command("e-stop")
        assert a.action_type == "emergency_stop"

    def test_stop_everything(self):
        a = parse_command("stop everything")
        assert a.action_type == "emergency_stop"

    # Torque adjustments
    def test_be_gentle(self):
        a = parse_command("be gentle")
        assert a.action_type == "law_update"
        assert a.params["law_id"] == "servo_limits"
        assert a.params["params"]["max_torque"] < 500

    def test_reduce_torque_30_pct(self):
        a = parse_command("reduce torque by 30%")
        assert a.action_type == "law_update"
        assert a.params["params"]["max_torque"] == 350  # 500 * 0.7

    def test_careful(self):
        a = parse_command("be careful")
        assert a.action_type == "law_update"
        assert a.params["law_id"] == "servo_limits"

    def test_delicate(self):
        a = parse_command("delicate")
        assert a.action_type == "law_update"
        assert a.params["params"]["max_torque"] < 400

    # Speed adjustments
    def test_slow_down(self):
        a = parse_command("slow down")
        assert a.action_type == "law_update"
        assert a.params["law_id"] == "teleop_max_fps"
        assert a.params["params"]["fps"] < 60

    def test_speed_up(self):
        a = parse_command("speed up")
        assert a.action_type == "law_update"
        assert a.params["params"]["fps"] == 60

    def test_half_speed(self):
        a = parse_command("half speed")
        assert a.action_type == "law_update"
        assert a.params["params"]["fps"] == 30

    # Law updates
    def test_set_fps(self):
        a = parse_command("set fps to 25")
        assert a.action_type == "law_update"
        assert a.params["law_id"] == "teleop_max_fps"
        assert a.params["params"]["fps"] == 25

    def test_set_idle_timeout(self):
        a = parse_command("set idle timeout to 600")
        assert a.action_type == "law_update"
        assert a.params["law_id"] == "idle_timeout"
        assert a.params["params"]["seconds"] == 600

    def test_set_heartbeat(self):
        a = parse_command("set heartbeat to 1.5")
        assert a.action_type == "law_update"
        assert a.params["law_id"] == "heartbeat_interval"
        assert a.params["params"]["seconds"] == 1.5

    # Task creation
    def test_wave(self):
        a = parse_command("wave hello")
        assert a.action_type == "task_create"
        assert a.params["type"] == "basic_gesture"
        assert a.params["params"]["gesture"] == "wave"

    def test_nod(self):
        a = parse_command("nod")
        assert a.action_type == "task_create"
        assert a.params["type"] == "basic_gesture"

    def test_sort_blocks(self):
        a = parse_command("sort the blocks")
        assert a.action_type == "task_create"
        assert a.params["type"] == "color_sorting"

    def test_what_do_you_see(self):
        a = parse_command("what do you see")
        assert a.action_type == "task_create"
        assert a.params["type"] == "color_detection"

    def test_take_photo(self):
        a = parse_command("take a photo")
        assert a.action_type == "task_create"
        assert a.params["type"] == "frame_capture"

    def test_pick_and_place(self):
        a = parse_command("pick and place")
        assert a.action_type == "task_create"
        assert a.params["type"] == "pick_and_place"

    def test_pick_up_red(self):
        a = parse_command("pick up the red block")
        assert a.action_type == "task_create"
        assert a.params["params"].get("target_color") == "red"

    # Unrecognized
    def test_unrecognized(self):
        a = parse_command("make me a sandwich")
        assert a is None

    # Case insensitivity
    def test_case_insensitive(self):
        a = parse_command("STOP")
        assert a.action_type == "emergency_stop"

    def test_wave_caps(self):
        a = parse_command("Wave Hello")
        assert a.action_type == "task_create"


class TestGovernorAide:
    def test_execute_records_history(self):
        from unittest.mock import MagicMock
        gov = MagicMock()
        gov.neighbors = {}
        aide = GovernorAide(gov)
        aide.execute("wave hello")
        assert len(aide.history) == 1
        assert aide.history[0][0] == "wave hello"

    def test_execute_unknown_returns_none(self):
        from unittest.mock import MagicMock
        gov = MagicMock()
        gov.neighbors = {}
        aide = GovernorAide(gov)
        result = aide.execute("banana")
        assert result is None

    def test_emergency_stop_sends_govern(self):
        from unittest.mock import MagicMock
        gov = MagicMock()
        gov.neighbors = {"key1": MagicMock(pubkey="key1", addr=("1.2.3.4", 9000))}
        aide = GovernorAide(gov)
        aide.execute("stop")
        gov.send_govern.assert_called_once()
