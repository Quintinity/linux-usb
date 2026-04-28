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
    # The recorder writes its own attribution sidecar:
    out = recorder.last_episode_dir
    sidecar = out.parent.parent / "attribution.json"  # at <repo_safe>/ root
    if not sidecar.exists():
        # alt location: inside the chunk dir
        sidecar_alt = out / "attribution.json"
        if sidecar_alt.exists():
            sidecar = sidecar_alt
    import json
    data = json.loads(sidecar.read_text())
    assert data["node_pubkey"] == "ab" * 32
    assert data["policy_pubkey"] == "cd" * 32
    assert data["governor_pubkey"] == "ef" * 32
    assert data["constitution_hash"] == "01" * 16
