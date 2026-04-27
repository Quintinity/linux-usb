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
