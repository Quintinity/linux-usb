"""Tests for PolicyCitizen — bidding, follower targeting, action emission."""

import asyncio
from unittest.mock import MagicMock

import numpy as np
import pytest

from citizenry.policy_citizen import MOTOR_NAMES, PolicyCitizen


def _make_policy(tmp_path, monkeypatch, node_pubkey: str = "ab" * 32) -> PolicyCitizen:
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    runner = MagicMock()
    runner.act.return_value = np.zeros((50, 6), dtype=np.float32)
    return PolicyCitizen(runner=runner, node_pubkey=node_pubkey)


def test_policy_advertises_imitation_skill(tmp_path, monkeypatch):
    p = _make_policy(tmp_path, monkeypatch)
    assert "policy.imitation" in p.capabilities
    assert "vla.smolvla_base" in p.capabilities
    assert p.skill_tree.has_skill("imitation:smolvla_base")


def test_policy_bid_includes_node_pubkey_and_target_follower(tmp_path, monkeypatch):
    p = _make_policy(tmp_path, monkeypatch, node_pubkey="ab" * 32)
    from citizenry.marketplace import Task
    task = Task(
        type="pick_and_place",
        params={"follower_pubkey": "f1"*16},
        required_capabilities=["6dof_arm"],
        required_skills=["pick_and_place"],
    )
    bid = p.build_bid(task=task, target_follower_pubkey="f1"*16,
                       target_follower_node_pubkey="ab" * 32)
    assert bid is not None
    assert bid.node_pubkey == "ab" * 32
    assert bid.target_follower_pubkey == "f1" * 16
    # Co-located → expect the +0.15 bonus rolled into score
    assert bid.score >= 0.15


def test_policy_bid_no_bonus_when_remote(tmp_path, monkeypatch):
    p = _make_policy(tmp_path, monkeypatch, node_pubkey="ab" * 32)
    from citizenry.marketplace import Task
    task = Task(
        type="pick_and_place",
        params={"follower_pubkey": "f1"*16},
        required_capabilities=["6dof_arm"],
    )
    bid_local = p.build_bid(task, "f1"*16, target_follower_node_pubkey="ab" * 32)
    bid_remote = p.build_bid(task, "f1"*16, target_follower_node_pubkey="zz" * 32)
    assert bid_local is not None and bid_remote is not None
    # Local should be exactly 0.15 higher
    assert bid_local.score == pytest.approx(bid_remote.score + 0.15)


def test_policy_no_bid_when_capability_missing(tmp_path, monkeypatch):
    p = _make_policy(tmp_path, monkeypatch)
    from citizenry.marketplace import Task
    task = Task(
        type="some_specialized_task",
        required_capabilities=["nonexistent_capability"],
    )
    assert p.build_bid(task, target_follower_pubkey="f", target_follower_node_pubkey="x") is None


def test_camera_role_pair_reads_constitution_law(tmp_path, monkeypatch):
    p = _make_policy(tmp_path, monkeypatch)
    # No constitution → falls back to default
    assert p.camera_role_pair() == ("wrist", "base")
    # Set Law in dict format
    p.constitution = {"laws": {"policy_citizen.observation_cameras": ["camA", "camB"]}}
    assert p.camera_role_pair() == ("camA", "camB")
    # Set Law in wire format
    p.constitution = {
        "laws": [{"id": "policy_citizen.observation_cameras",
                  "params": {"value": ["camX", "camY"]}}]
    }
    assert p.camera_role_pair() == ("camX", "camY")


@pytest.mark.asyncio
async def test_execute_task_emits_teleop_when_neighbor_resolves(tmp_path, monkeypatch):
    """execute_task emits teleop for one action chunk then we cancel."""
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    runner = MagicMock()
    # Return a 5-step chunk (smaller than 50) for faster test
    runner.act.return_value = np.zeros((5, 6), dtype=np.float32)
    p = PolicyCitizen(runner=runner, node_pubkey="ab" * 32)
    # Inject a fake neighbor at the target follower pubkey
    from citizenry.citizen import Neighbor
    fake_addr = ("127.0.0.1", 9999)
    p.neighbors["follower_pk"] = Neighbor(
        pubkey="follower_pk",
        name="fake-manipulator",
        citizen_type="manipulator",
        capabilities=["6dof_arm"],
        addr=fake_addr,
    )
    # Stub send_teleop so we can count calls without networking
    sent = []
    def fake_send_teleop(recipient, positions, addr):
        sent.append((recipient, dict(positions), addr))
    monkeypatch.setattr(p, "send_teleop", fake_send_teleop)
    from citizenry.marketplace import Task
    task = Task(type="pick_and_place", params={"follower_pubkey": "follower_pk"})
    # Run the action loop briefly then cancel
    coro_task = asyncio.create_task(p.execute_task(task, "follower_pk"))
    await asyncio.sleep(0.05)  # let one chunk start emitting
    p._active_task_id = None  # signal exit
    await asyncio.wait_for(coro_task, timeout=2.0)
    # Should have emitted at least one teleop
    assert len(sent) >= 1
    # Each call's positions dict should have 6 motor entries
    rec, positions, addr = sent[0]
    assert rec == "follower_pk"
    assert addr == fake_addr
    assert len(positions) == 6


@pytest.mark.asyncio
async def test_execute_task_skips_when_neighbor_unresolved(tmp_path, monkeypatch):
    """If neighbor lookup returns None, _emit_teleop logs and skips — no crash."""
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    runner = MagicMock()
    runner.act.return_value = np.zeros((3, 6), dtype=np.float32)
    p = PolicyCitizen(runner=runner, node_pubkey="ab" * 32)
    # No neighbor injected — _neighbor_addr returns None
    sent = []
    monkeypatch.setattr(p, "send_teleop", lambda *a, **k: sent.append(a))
    from citizenry.marketplace import Task
    task = Task(type="pick_and_place", params={"follower_pubkey": "unknown_pk"})
    coro_task = asyncio.create_task(p.execute_task(task, "unknown_pk"))
    await asyncio.sleep(0.05)
    p._active_task_id = None
    await asyncio.wait_for(coro_task, timeout=2.0)
    # Should have emitted ZERO teleop frames (neighbor unresolved)
    assert len(sent) == 0


def test_emit_teleop_drops_frame_with_short_action_row(tmp_path, monkeypatch):
    """A fine-tuned model with fewer action dims doesn't crash the policy."""
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    runner = MagicMock()
    p = PolicyCitizen(runner=runner, node_pubkey="ab" * 32)
    sent = []
    monkeypatch.setattr(p, "send_teleop", lambda *a, **k: sent.append(a))
    # Inject the neighbor so addr resolves
    from citizenry.citizen import Neighbor
    p.neighbors["follower_pk"] = Neighbor(
        pubkey="follower_pk", name="fake", citizen_type="manipulator",
        capabilities=["6dof_arm"], addr=("127.0.0.1", 9999),
    )
    short_action = np.zeros(3, dtype=np.float32)  # only 3 dims, expected 6
    asyncio.run(p._emit_teleop(short_action, "follower_pk"))
    assert len(sent) == 0  # frame dropped
