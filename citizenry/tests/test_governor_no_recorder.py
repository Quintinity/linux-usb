"""Tests that GovernorCitizen refuses to start a recorder."""

import pytest

from citizenry.governor_citizen import GovernorCitizen


def test_governor_does_not_construct_a_recorder(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    g = GovernorCitizen()
    assert getattr(g, "_recorder_v1", None) is None
    assert getattr(g, "_recorder_v3", None) is None


def test_governor_refuses_when_law_explicitly_enables_recorder(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    g = GovernorCitizen()
    # Even if the Constitution somehow has governor.recorder_enabled=true,
    # the governor citizen never instantiates a recorder.
    g.constitution = {"laws": {"governor.recorder_enabled": True}}
    with pytest.raises(RuntimeError, match="GovernorCitizen does not record"):
        g._maybe_start_recorder()  # the guard method we add below
