"""Tests for multi-location architecture."""

import pytest
from citizenry.multi_location import (
    Location, Embassy, CrossLocationMessage, LocationRegistry, LOCATION_LAWS,
)


class TestLocation:
    def test_create(self):
        loc = Location(id="home", name="Home Office", subnet="192.168.1.0/24")
        assert loc.name == "Home Office"

    def test_to_dict(self):
        loc = Location(id="lab", name="School Lab", citizen_count=3)
        d = loc.to_dict()
        assert d["name"] == "School Lab"
        assert d["citizen_count"] == 3


class TestEmbassy:
    def test_create(self):
        loc = Location(id="home", name="Home")
        emb = Embassy(location=loc, is_local=True)
        assert emb.is_local
        assert not emb.connected

    def test_to_dict(self):
        loc = Location(id="home")
        emb = Embassy(location=loc, peers=["10.0.0.2"])
        d = emb.to_dict()
        assert d["peers"] == ["10.0.0.2"]


class TestLocationRegistry:
    def test_register(self):
        reg = LocationRegistry()
        reg.register(Location(id="home", name="Home", subnet="192.168.1.0/24"))
        reg.register(Location(id="lab", name="Lab", subnet="192.168.2.0/24"))
        assert len(reg.to_list()) == 2

    def test_get_remote(self):
        reg = LocationRegistry()
        reg.register(Location(id="home"))
        reg.register(Location(id="lab"))
        reg.set_local("home")
        remote = reg.get_remote()
        assert len(remote) == 1
        assert remote[0].id == "lab"

    def test_get_by_subnet(self):
        reg = LocationRegistry()
        reg.register(Location(id="home", subnet="192.168.1.0/24"))
        reg.register(Location(id="lab", subnet="192.168.2.0/24"))
        loc = reg.get_by_subnet("192.168.1.85")
        assert loc is not None
        assert loc.id == "home"

    def test_get_by_subnet_unknown(self):
        reg = LocationRegistry()
        reg.register(Location(id="home", subnet="192.168.1.0/24"))
        assert reg.get_by_subnet("10.0.0.1") is None


class TestLocationLaws:
    def test_laws_exist(self):
        assert "cross_location_heartbeat_interval" in LOCATION_LAWS
        assert "cross_location_task_routing" in LOCATION_LAWS
        assert "embassy_failover_timeout" in LOCATION_LAWS


class TestCrossLocationMessage:
    def test_create(self):
        msg = CrossLocationMessage(
            source_location="home",
            dest_location="lab",
            message_type=1,
        )
        assert msg.ttl_hops == 3
        assert msg.dest_location == "lab"
