"""Tests for president governance layer."""

import time
import pytest
from citizenry.president import (
    President, GovernorRecord, NationState,
    parse_president_command,
)


class TestGovernorRecord:
    def test_create(self):
        g = GovernorRecord(pubkey="aaa", name="home-gov", location="Home", addr=("192.168.1.80", 8080))
        assert g.name == "home-gov"

    def test_is_online(self):
        g = GovernorRecord(pubkey="aaa", name="gov", location="Home", addr=("1.2.3.4", 80), last_seen=time.time())
        assert g.is_online()

    def test_is_offline(self):
        g = GovernorRecord(pubkey="aaa", name="gov", location="Home", addr=("1.2.3.4", 80), last_seen=0)
        assert not g.is_online()


class TestPresident:
    def _make_president(self):
        p = President("test-president")
        p.register_governor(GovernorRecord(
            pubkey="gov1", name="home-gov", location="Home",
            addr=("192.168.1.80", 8080), citizen_count=3,
            capabilities=["compute", "govern"], composite_capabilities=["visual_pick_and_place"],
            last_seen=time.time(), mood="focused",
        ))
        p.register_governor(GovernorRecord(
            pubkey="gov2", name="school-gov", location="School",
            addr=("192.168.2.80", 8080), citizen_count=5,
            capabilities=["compute", "govern"], composite_capabilities=["color_sorting"],
            last_seen=time.time(), mood="steady",
        ))
        return p

    def test_register(self):
        p = self._make_president()
        assert len(p.governors) == 2

    def test_get_governor_by_name(self):
        p = self._make_president()
        g = p.get_governor("home-gov")
        assert g is not None
        assert g.location == "Home"

    def test_get_governor_by_location(self):
        p = self._make_president()
        g = p.get_governor("School")
        assert g is not None
        assert g.name == "school-gov"

    def test_nation_state(self):
        p = self._make_president()
        state = p.get_nation_state()
        assert state.total_governors == 2
        assert state.total_citizens == 8
        assert "visual_pick_and_place" in state.composite_capabilities

    def test_route_command_targeted(self):
        p = self._make_president()
        routes = p.route_command("wave hello", target="Home")
        assert len(routes) == 1
        assert routes[0][0].name == "home-gov"

    def test_route_command_broadcast(self):
        p = self._make_president()
        routes = p.route_command("be gentle")
        assert len(routes) == 2

    def test_broadcast_law(self):
        p = self._make_president()
        sent = p.broadcast_law("max_torque", {"value": 350})
        assert len(sent) == 2

    def test_find_capability(self):
        p = self._make_president()
        govs = p.find_capability("visual_pick_and_place")
        assert len(govs) == 1
        assert govs[0].name == "home-gov"

    def test_delegate_task(self):
        p = self._make_president()
        gov = p.delegate_task("pick_and_place", target_location="Home")
        assert gov is not None
        assert gov.name == "home-gov"

    def test_delegate_best(self):
        p = self._make_president()
        gov = p.delegate_task("pick_and_place")
        assert gov is not None  # Should pick the one with most citizens

    def test_nation_summary(self):
        p = self._make_president()
        summary = p.nation_summary()
        assert "home-gov" in summary
        assert "school-gov" in summary


class TestParsePresidentCommand:
    def test_nation_status(self):
        cmd = parse_president_command("nation status")
        assert cmd["action"] == "nation_status"

    def test_list_governors(self):
        cmd = parse_president_command("governors")
        assert cmd["action"] == "list_governors"

    def test_tell_command(self):
        cmd = parse_president_command("tell home office to wave hello")
        assert cmd["action"] == "delegate"
        assert cmd["target"] == "home office"
        assert cmd["command"] == "wave hello"

    def test_at_command(self):
        cmd = parse_president_command("at school: sort the blocks")
        assert cmd["action"] == "delegate"
        assert cmd["target"] == "school"
        assert cmd["command"] == "sort the blocks"

    def test_broadcast(self):
        cmd = parse_president_command("all be gentle")
        assert cmd["action"] == "broadcast"
        assert cmd["command"] == "be gentle"

    def test_unknown(self):
        cmd = parse_president_command("banana")
        assert cmd is None
