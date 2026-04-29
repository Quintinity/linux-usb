"""Tests for Citizen._law helper and node_pubkey wiring."""

import pytest


def test_citizen_law_returns_default_before_constitution(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Citizen
    c = Citizen(name="t", citizen_type="manipulator", capabilities=[])
    assert c._law("any.key", "fallback") == "fallback"


def test_citizen_law_reads_ratified_constitution(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Citizen
    c = Citizen(name="t", citizen_type="manipulator", capabilities=[])
    c.constitution = {"laws": {"episode_recorder_format": "v3"}}
    assert c._law("episode_recorder_format", "v1") == "v3"
    assert c._law("missing", "fallback") == "fallback"


def test_citizen_inherits_node_pubkey(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Citizen
    c = Citizen(name="t", citizen_type="manipulator", capabilities=[])
    assert len(c.node_pubkey) == 64
    assert c.genome.node_pubkey == c.node_pubkey


def test_citizen_accepts_explicit_node_pubkey(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Citizen
    explicit = "cd" * 32
    c = Citizen(name="t2", citizen_type="sensor", capabilities=[], node_pubkey=explicit)
    assert c.node_pubkey == explicit
    assert c.genome.node_pubkey == explicit


def test_citizen_law_reads_wire_format_constitution(tmp_path, monkeypatch):
    """Wire format: laws is a list of {"id": ..., "params": {"value": ...}} dicts."""
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Citizen
    c = Citizen(name="t", citizen_type="manipulator", capabilities=[])
    c.constitution = {
        "laws": [
            {"id": "episode_recorder_format", "description": "format choice", "params": {"value": "v3"}},
            {"id": "dataset.hf_repo_id", "description": "repo", "params": {"value": "user/repo"}},
            {"id": "structured_law", "description": "non-simple", "params": {"min": 1, "max": 10}},
        ]
    }
    assert c._law("episode_recorder_format", "v1") == "v3"
    assert c._law("dataset.hf_repo_id", "") == "user/repo"
    assert c._law("missing", "fallback") == "fallback"
    # Structured law without "value" returns default (use dedicated helpers instead)
    assert c._law("structured_law", "fallback") == "fallback"


def test_citizen_law_handles_unknown_laws_shape(tmp_path, monkeypatch):
    """Defensive: if laws is something weird (not a dict or list), return default."""
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Citizen
    c = Citizen(name="t", citizen_type="manipulator", capabilities=[])
    c.constitution = {"laws": "this is not valid"}
    assert c._law("anything", "fallback") == "fallback"


def test_neighbor_carries_node_pubkey_from_advertise(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Neighbor, Presence
    # Just verify the dataclass has the field with sensible default
    n = Neighbor(
        pubkey="abc",
        name="x",
        citizen_type="manipulator",
        capabilities=[],
        addr=("127.0.0.1", 9000),
        state="online",
    )
    assert hasattr(n, "node_pubkey")
    assert n.node_pubkey is None
    # Field can be set
    n2 = Neighbor(
        pubkey="abc",
        name="x",
        citizen_type="manipulator",
        capabilities=[],
        addr=("127.0.0.1", 9000),
        state="online",
        node_pubkey="cd" * 32,
    )
    assert n2.node_pubkey == "cd" * 32
