"""Tests for the LeRobotDataset v3 episode recorder."""

from pathlib import Path

import numpy as np
import pytest

from citizenry.episode_recorder import EpisodeRecorderV3


@pytest.fixture
def recorder(tmp_path):
    return EpisodeRecorderV3(
        output_root=tmp_path / "v3",
        repo_id="test/local",
        fps=30,
    )


def test_begin_close_creates_episode_dir(recorder):
    eid = recorder.begin_episode("teleop", {"target": "red_block"})
    assert isinstance(eid, str) and len(eid) > 0
    out = recorder.close_episode(success=True, notes="ok")
    assert out.exists()
    # v3 layout: at least one parquet chunk
    assert any(out.rglob("*.parquet"))


def test_record_frame_appends_to_chunk(recorder):
    recorder.begin_episode("teleop", {})
    for i in range(5):
        recorder.record_frame(
            frame_index=i,
            timestamp=float(i) / 30.0,
            image=np.zeros((96, 128, 3), dtype=np.uint8),
            joint_positions=[100, 200, 300, 400, 500, 600],
            joint_currents=[0.0]*6,
            joint_temperatures=[40.0]*6,
            joint_loads=[0.1]*6,
            action_positions=[100, 200, 300, 400, 500, 600],
            reward=0.0,
        )
    out = recorder.close_episode(success=True)
    # Verify the parquet has 5 rows
    import pyarrow.parquet as pq
    tables = [pq.read_table(p) for p in out.rglob("*.parquet")]
    total_rows = sum(t.num_rows for t in tables)
    assert total_rows == 5


def test_metadata_json_includes_node_and_policy_pubkeys(recorder):
    recorder.set_attribution(
        node_pubkey="ab" * 32,
        policy_pubkey="cd" * 32,
        governor_pubkey="ef" * 32,
        constitution_hash="01" * 16,
    )
    recorder.begin_episode("pick_and_place", {"target": "red_block"})
    recorder.close_episode(success=True, reward_total=1.0, duration_s=2.5)
    # The recorder writes its own attribution sidecar at the per-repo root:
    out = recorder.last_episode_dir
    sidecar = out.parent.parent / "attribution.json"  # at <repo_safe>/ root
    import json
    data = json.loads(sidecar.read_text())
    assert data["node_pubkey"] == "ab" * 32
    assert data["policy_pubkey"] == "cd" * 32
    assert data["governor_pubkey"] == "ef" * 32
    assert data["constitution_hash"] == "01" * 16


def test_two_episodes_share_or_advance_chunk(tmp_path):
    """With episodes_per_chunk=2, episodes 1+2 share chunk 0, episode 3 lands in chunk 1."""
    rec = EpisodeRecorderV3(
        output_root=tmp_path / "v3",
        repo_id="test/local",
        fps=30,
        episodes_per_chunk=2,
    )
    chunk_dirs = []
    for i in range(3):
        rec.begin_episode("teleop", {})
        rec.record_frame(
            frame_index=0, timestamp=0.0,
            image=np.zeros((48, 64, 3), dtype=np.uint8),
            joint_positions=[0]*6, joint_currents=[0.0]*6,
            joint_temperatures=[0.0]*6, joint_loads=[0.0]*6,
            action_positions=[0]*6,
        )
        chunk_dirs.append(rec.close_episode(success=True))
    # First two episodes in same chunk (chunk_0000), third in chunk_0001
    assert chunk_dirs[0] == chunk_dirs[1]
    assert chunk_dirs[2] != chunk_dirs[0]


def test_begin_episode_while_open_raises(tmp_path):
    rec = EpisodeRecorderV3(output_root=tmp_path / "v3", repo_id="test/local")
    rec.begin_episode("teleop", {})
    with pytest.raises(RuntimeError, match="while episode"):
        rec.begin_episode("another_task", {})


def test_mp4_failure_does_not_orphan_parquet(tmp_path, monkeypatch):
    """If the MP4 write raises, the parquet + json + attribution still land."""
    rec = EpisodeRecorderV3(output_root=tmp_path / "v3", repo_id="test/local", fps=30)
    rec.begin_episode("teleop", {})
    rec.record_frame(
        frame_index=0, timestamp=0.0,
        image=np.zeros((48, 64, 3), dtype=np.uint8),
        joint_positions=[0]*6, joint_currents=[0.0]*6,
        joint_temperatures=[0.0]*6, joint_loads=[0.0]*6,
        action_positions=[0]*6,
    )
    # Make _write_mp4 fail
    def boom(*args, **kwargs):
        raise RuntimeError("simulated MP4 failure")
    monkeypatch.setattr(rec, "_write_mp4", boom)
    out = rec.close_episode(success=True)
    # Parquet + JSON should still exist
    assert any(out.glob("episode_*.parquet"))
    assert any(out.glob("episode_*.json"))
