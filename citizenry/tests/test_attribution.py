"""Tests for the episode recorder's attribution sidecar wiring on ManipulatorCitizen.

Task D1 of the citizenry-usability plan: every episode recorded by a manipulator
must carry non-null ``policy_pubkey``, ``governor_pubkey``, and
``constitution_hash`` (alongside the always-present ``node_pubkey``). This is
the data layer behind Quintinity's "auditable AI" pitch — given a recorded
episode you can prove who taught the arm, who governed the safety envelope,
and which exact constitution was in force.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from citizenry.manipulator_citizen import ManipulatorCitizen


def _make_manipulator(tmp_path, monkeypatch) -> ManipulatorCitizen:
    """Construct a ManipulatorCitizen wired to a tmp dir for identity + datasets."""
    from citizenry import identity, node_identity
    monkeypatch.setattr(identity, "IDENTITY_DIR", tmp_path)
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    # Redirect the recorder's output root away from the user's home dir.
    real_home = Path.home
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    try:
        m = ManipulatorCitizen()
    finally:
        monkeypatch.setattr(Path, "home", real_home)
    return m


def test_constitution_hash_is_none_until_constitution_set(tmp_path, monkeypatch):
    m = _make_manipulator(tmp_path, monkeypatch)
    assert m.constitution is None
    assert m.constitution_hash is None


def test_constitution_hash_is_stable_sha256_prefix(tmp_path, monkeypatch):
    m = _make_manipulator(tmp_path, monkeypatch)
    const = {"version": 3, "laws": [{"id": "x", "params": {"v": 1}}]}
    m.constitution = const
    expected = hashlib.sha256(
        json.dumps(const, sort_keys=True).encode()
    ).hexdigest()[:16]
    assert m.constitution_hash == expected
    # Stability: same dict order-insensitively produces the same hash.
    m.constitution = {"laws": [{"id": "x", "params": {"v": 1}}], "version": 3}
    assert m.constitution_hash == expected


def test_governor_pubkey_property_mirrors_governor_key(tmp_path, monkeypatch):
    m = _make_manipulator(tmp_path, monkeypatch)
    assert m.governor_pubkey is None
    m._governor_key = "ff" * 32
    assert m.governor_pubkey == "ff" * 32


def test_attribution_sidecar_carries_real_pubkeys(tmp_path, monkeypatch):
    """All four attribution fields are populated and reach the recorder."""
    m = _make_manipulator(tmp_path, monkeypatch)

    policy_pk = "cd" * 32
    governor_pk = "ef" * 32
    const = {"version": 1, "laws": [{"id": "dataset.fps", "params": {"value": 30}}]}

    # Simulate the live state at the moment an episode begins:
    #   - a teleop policy is actively driving us
    #   - a governor has been seen
    #   - a constitution has been received
    m._active_policy_pubkey = policy_pk
    m._governor_key = governor_pk
    m.constitution = const

    m._refresh_attribution()
    attrib = m._recorder._attribution

    assert attrib["node_pubkey"] == m.node_pubkey
    assert attrib["node_pubkey"] is not None
    assert attrib["policy_pubkey"] == policy_pk
    assert attrib["governor_pubkey"] == governor_pk
    expected_hash = hashlib.sha256(
        json.dumps(const, sort_keys=True).encode()
    ).hexdigest()[:16]
    assert attrib["constitution_hash"] == expected_hash
    # All four fields are non-null — the auditable-AI invariant.
    assert all(v is not None for v in attrib.values())


def test_attribution_sidecar_persists_to_disk_with_real_pubkeys(tmp_path, monkeypatch):
    """attribution.json on disk carries all four fields after a real episode close.

    Goes through the actual JSON write path in ``EpisodeRecorder.close_episode``
    (episode_recorder.py lines 162-168) — exercises real begin/record/close
    instead of just the in-memory ``_attribution`` dict.
    """
    m = _make_manipulator(tmp_path, monkeypatch)

    policy_pk = "cd" * 32
    governor_pk = "ef" * 32
    const = {"version": 1, "laws": [{"id": "dataset.fps", "params": {"value": 30}}]}

    m._active_policy_pubkey = policy_pk
    m._governor_key = governor_pk
    m.constitution = const
    m._refresh_attribution()

    rec = m._recorder
    rec.begin_episode("teleop", {"target": "red_block"})
    rec.record_frame(
        frame_index=0,
        timestamp=0.0,
        image=np.zeros((96, 128, 3), dtype=np.uint8),
        joint_positions=[100, 200, 300, 400, 500, 600],
        joint_currents=[0.0] * 6,
        joint_temperatures=[40.0] * 6,
        joint_loads=[0.1] * 6,
        action_positions=[100, 200, 300, 400, 500, 600],
        reward=0.0,
    )
    rec.close_episode(success=True, notes="ok", duration_s=0.0)

    # Sidecar lives at <output_root>/<repo_safe>/attribution.json (not under
    # the chunk dir — it's per-recorder).
    repo_safe = rec.repo_id.replace("/", "__")
    sidecar_path = rec.output_root / repo_safe / "attribution.json"
    assert sidecar_path.exists(), f"attribution.json missing at {sidecar_path}"

    data = json.loads(sidecar_path.read_text())
    expected_hash = hashlib.sha256(
        json.dumps(const, sort_keys=True).encode()
    ).hexdigest()[:16]

    assert data["node_pubkey"] == m.node_pubkey
    assert data["policy_pubkey"] == policy_pk
    assert data["governor_pubkey"] == governor_pk
    assert data["constitution_hash"] == expected_hash
    # All four fields present and non-null — the auditable-AI invariant.
    for field in ("node_pubkey", "policy_pubkey", "governor_pubkey", "constitution_hash"):
        assert field in data
        assert data[field] is not None


def test_handle_teleop_frame_records_active_policy(tmp_path, monkeypatch):
    """Every accepted teleop frame stamps env.sender as the active policy."""
    m = _make_manipulator(tmp_path, monkeypatch)
    m._teleop_active = True
    # _write_positions touches hardware; replace with a no-op success.
    m._write_positions = lambda positions: True

    class _Env:
        sender = "aa" * 32

    m._handle_teleop_frame(_Env(), {"positions": {"shoulder_pan": 100}})
    assert m._active_policy_pubkey == "aa" * 32

    # A subsequent frame from a different policy updates the field.
    class _Env2:
        sender = "bb" * 32

    m._handle_teleop_frame(_Env2(), {"positions": {"shoulder_pan": 101}})
    assert m._active_policy_pubkey == "bb" * 32


def test_handle_teleop_frame_ignored_when_not_active(tmp_path, monkeypatch):
    """If teleop isn't active, frames are dropped and policy isn't stamped."""
    m = _make_manipulator(tmp_path, monkeypatch)
    m._teleop_active = False

    class _Env:
        sender = "aa" * 32

    m._handle_teleop_frame(_Env(), {"positions": {"shoulder_pan": 100}})
    assert m._active_policy_pubkey is None


def test_governor_disconnect_clears_active_policy(tmp_path, monkeypatch):
    """When the governor is presumed dead, active policy clears too."""
    from citizenry.citizen import Neighbor, Presence
    m = _make_manipulator(tmp_path, monkeypatch)
    m._governor_key = "ef" * 32
    m._active_policy_pubkey = "cd" * 32
    m._teleop_active = True
    m._disable_torque = lambda: None  # avoid touching hardware

    dead_governor = Neighbor(
        pubkey="ef" * 32,
        name="gov",
        citizen_type="governor",
        capabilities=[],
        addr=("127.0.0.1", 9999),
        presence=Presence.PRESUMED_DEAD,
    )
    m._on_neighbor_presence_changed(dead_governor, Presence.ONLINE)
    assert m._teleop_active is False
    assert m._active_policy_pubkey is None
