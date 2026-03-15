"""Tests for symbiosis contracts."""

import time
import pytest
from citizenry.symbiosis import (
    SymbiosisContract, ContractStatus, ContractManager,
)


class TestSymbiosisContract:
    def test_create(self):
        c = SymbiosisContract(
            provider="aaa",
            consumer="bbb",
            provider_capability="video_stream",
            consumer_capability="6dof_arm",
            composite_capability="visual_pick_and_place",
        )
        assert c.status == ContractStatus.PROPOSED
        assert c.composite_capability == "visual_pick_and_place"

    def test_roundtrip(self):
        c = SymbiosisContract(
            provider="aaa",
            consumer="bbb",
            status=ContractStatus.ACTIVE,
        )
        d = c.to_dict()
        c2 = SymbiosisContract.from_dict(d)
        assert c2.provider == "aaa"
        assert c2.status == ContractStatus.ACTIVE

    def test_to_propose_body(self):
        c = SymbiosisContract(
            provider_capability="video_stream",
            consumer_capability="6dof_arm",
            composite_capability="visual_pick_and_place",
        )
        body = c.to_propose_body()
        assert body["task"] == "symbiosis_propose"
        assert body["composite"] == "visual_pick_and_place"

    def test_from_propose_body(self):
        body = {
            "task": "symbiosis_propose",
            "contract_id": "test123",
            "provider_cap": "video_stream",
            "consumer_cap": "6dof_arm",
            "composite": "visual_pick_and_place",
            "health_check_hz": 1.0,
        }
        c = SymbiosisContract.from_propose_body(body, "sender_key", "recipient_key")
        assert c.id == "test123"
        assert c.provider == "sender_key"
        assert c.consumer == "recipient_key"
        assert c.health_check_interval == 1.0

    def test_health_check(self):
        c = SymbiosisContract(status=ContractStatus.ACTIVE)
        c.last_health_check = time.time()
        assert c.is_healthy()
        c.missed_checks = 3
        assert not c.is_healthy()

    def test_record_health_check_resets(self):
        c = SymbiosisContract(status=ContractStatus.ACTIVE)
        c.missed_checks = 2
        c.record_health_check()
        assert c.missed_checks == 0

    def test_check_timeout_breaks_contract(self):
        c = SymbiosisContract(
            status=ContractStatus.ACTIVE,
            health_check_interval=0.1,
        )
        c.last_health_check = time.time() - 1.0  # 10 intervals ago
        assert c.check_timeout()
        assert c.status == ContractStatus.BROKEN


class TestContractManager:
    def test_propose_and_accept(self):
        mgr = ContractManager()
        c = mgr.propose("aaa", "bbb", "video_stream", "6dof_arm", "visual_pick")
        assert c.status == ContractStatus.PROPOSED
        accepted = mgr.accept(c.id)
        assert accepted is not None
        assert accepted.status == ContractStatus.ACTIVE

    def test_get_composite_capabilities(self):
        mgr = ContractManager()
        c = mgr.propose("aaa", "bbb", "video", "arm", "visual_pick")
        mgr.accept(c.id)
        caps = mgr.get_composite_capabilities()
        assert "visual_pick" in caps

    def test_no_composite_from_proposed(self):
        mgr = ContractManager()
        mgr.propose("aaa", "bbb", "video", "arm", "visual_pick")
        # Not accepted yet
        caps = mgr.get_composite_capabilities()
        assert caps == []

    def test_remove_citizen_breaks_contracts(self):
        mgr = ContractManager()
        c = mgr.propose("aaa", "bbb", "video", "arm", "visual_pick")
        mgr.accept(c.id)
        broken = mgr.remove_citizen("aaa")
        assert len(broken) == 1
        assert broken[0].status == ContractStatus.BROKEN

    def test_record_health(self):
        mgr = ContractManager()
        c = mgr.propose("aaa", "bbb", "video", "arm", "visual_pick")
        mgr.accept(c.id)
        c.missed_checks = 2
        mgr.record_health("aaa")
        assert c.missed_checks == 0

    def test_serialization(self):
        mgr = ContractManager()
        c = mgr.propose("aaa", "bbb", "video", "arm", "visual_pick")
        mgr.accept(c.id)
        data = mgr.to_list()
        mgr2 = ContractManager.from_list(data)
        assert len(mgr2.get_active()) == 1
