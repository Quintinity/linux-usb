"""Tests for the legacy → LeRobotDataset v3 migrator."""

import json
from pathlib import Path

import numpy as np
import pytest

from citizenry.dataset_v3_migrate import migrate_legacy_to_v3


def _seed_legacy_episode(root: Path, eid: int, frames: int = 3) -> None:
    """Create a fake legacy episode resembling the v1 layout."""
    ep_dir = root / f"episode_{eid:04d}"
    ep_dir.mkdir(parents=True, exist_ok=True)
    # v1 layout: one .npy of joint actions per frame, one .jpg per frame, plus a manifest.
    for i in range(frames):
        np.save(ep_dir / f"action_{i:05d}.npy",
                np.array([100, 200, 300, 400, 500, 600], dtype=np.int32))
        # tiny black JPEG via cv2
        import cv2
        cv2.imwrite(str(ep_dir / f"frame_{i:05d}.jpg"),
                    np.zeros((48, 64, 3), dtype=np.uint8))
    (ep_dir / "manifest.json").write_text(json.dumps({
        "task": "teleop", "frames": frames, "success": True, "fps": 30,
    }))


def test_migrate_one_episode_produces_v3_layout(tmp_path):
    legacy_root = tmp_path / "citizenry-datasets-legacy"
    out_root = tmp_path / "v3"
    _seed_legacy_episode(legacy_root, eid=1, frames=4)
    report = migrate_legacy_to_v3(
        legacy_paths=[legacy_root],
        output_root=out_root,
        repo_id="test/local",
        upload=False,
        delete_old=False,
        dry_run=False,
    )
    assert report["episodes_converted"] == 1
    assert report["frames_total"] == 4
    # The output should have at least one parquet under <repo_safe>/data/chunk_*/
    parquets = list((out_root / "test__local").rglob("*.parquet"))
    assert parquets, f"expected parquets in {out_root}"


def test_dry_run_writes_nothing(tmp_path):
    legacy_root = tmp_path / "legacy"
    out_root = tmp_path / "v3"
    _seed_legacy_episode(legacy_root, eid=1, frames=2)
    report = migrate_legacy_to_v3(
        legacy_paths=[legacy_root],
        output_root=out_root,
        repo_id="test/local",
        upload=False,
        delete_old=False,
        dry_run=True,
    )
    assert report["episodes_converted"] == 1  # counted
    # No parquets written
    assert not out_root.exists() or not list(out_root.rglob("*.parquet"))


def test_idempotent_rerun_skips_already_converted(tmp_path):
    legacy_root = tmp_path / "legacy"
    out_root = tmp_path / "v3"
    _seed_legacy_episode(legacy_root, eid=1, frames=2)
    # First run
    r1 = migrate_legacy_to_v3([legacy_root], out_root, "test/local", False, False, False)
    assert r1["episodes_converted"] == 1
    # Add a second legacy episode and re-run
    _seed_legacy_episode(legacy_root, eid=2, frames=3)
    r2 = migrate_legacy_to_v3([legacy_root], out_root, "test/local", False, False, False)
    assert r2["episodes_converted"] == 1  # only the new one
    assert r2["episodes_skipped"] == 1


def test_delete_old_removes_legacy_paths_after_success(tmp_path):
    legacy_root = tmp_path / "legacy"
    out_root = tmp_path / "v3"
    _seed_legacy_episode(legacy_root, eid=1, frames=2)
    migrate_legacy_to_v3(
        [legacy_root], out_root, "test/local",
        upload=False, delete_old=True, dry_run=False,
    )
    assert not (legacy_root / "episode_0001").exists()


def test_per_episode_error_does_not_abort_batch(tmp_path, monkeypatch):
    """A single corrupt episode is captured in report['errors'] but the
    batch continues."""
    legacy_root = tmp_path / "legacy"
    out_root = tmp_path / "v3"
    _seed_legacy_episode(legacy_root, eid=1, frames=2)
    _seed_legacy_episode(legacy_root, eid=2, frames=2)
    _seed_legacy_episode(legacy_root, eid=3, frames=2)

    # Make _convert_one raise on episode 0002 only
    from citizenry import dataset_v3_migrate
    real_convert = dataset_v3_migrate._convert_one

    def boom(legacy_dir, recorder, dry_run):
        if "episode_0002" in str(legacy_dir):
            raise RuntimeError("simulated corruption")
        return real_convert(legacy_dir, recorder, dry_run)

    monkeypatch.setattr(dataset_v3_migrate, "_convert_one", boom)

    report = dataset_v3_migrate.migrate_legacy_to_v3(
        [legacy_root], out_root, "test/local",
        upload=False, delete_old=False, dry_run=False,
    )
    # Episodes 1 and 3 converted; episode 2 captured as error
    assert report["episodes_converted"] == 2
    assert len(report["errors"]) == 1
    assert "episode_0002" in report["errors"][0]["path"]
    assert "simulated corruption" in report["errors"][0]["error"]
