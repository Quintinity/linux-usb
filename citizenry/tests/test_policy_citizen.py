"""Tests for PolicyCitizen — bidding, follower targeting, action emission."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from citizenry.policy_citizen import PolicyCitizen


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
