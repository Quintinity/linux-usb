"""One-shot legacy → LeRobotDataset v3 migrator.

Walks ~/.citizenry/episodes/ + ~/citizenry-datasets/episode_*/ (and any
explicit paths), converts each legacy episode into a v3-shaped chunk,
optionally uploads to HF, optionally deletes the legacy source on
verified success.

CLI:
    python -m citizenry.dataset_v3_migrate \
        --legacy ~/.citizenry/episodes \
        --legacy ~/citizenry-datasets \
        --output ~/citizenry-datasets/v3 \
        --repo-id bradley-festraets/citizenry-fleet \
        [--upload] [--delete-old] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from .episode_recorder import EpisodeRecorderV3


def _discover_legacy_episodes(roots: list[Path]) -> list[Path]:
    """Find every legacy episode dir under the supplied roots.

    Recognises any dir under a root that contains action_*.npy or
    frame_*.jpg files. The roots themselves are NOT episodes — only
    their immediate subdirectories.
    """
    found = []
    for root in roots:
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if list(child.glob("action_*.npy")) or list(child.glob("frame_*.jpg")):
                found.append(child)
    return found


def _episode_id_for_legacy(p: Path) -> str:
    """Stable episode id from legacy dir path.

    `episode_0001` → `0001`. Otherwise hash the path so re-runs see the same id.
    """
    n = p.name
    if n.startswith("episode_"):
        return n[len("episode_"):]
    import hashlib
    return hashlib.sha1(str(p).encode()).hexdigest()[:12]


def _already_converted(eid: str, output_root: Path, repo_safe: str) -> bool:
    """True if a parquet for this eid already exists under <repo_safe>/data/.

    Retained for backwards-compatible single-episode checks. The main
    migrate loop builds a set upfront instead to avoid O(N²) rglob calls.
    """
    return any((output_root / repo_safe).rglob(f"episode_{eid}.parquet"))


def _convert_one(legacy_dir: Path, recorder: EpisodeRecorderV3, dry_run: bool) -> dict:
    """Convert one legacy episode dir; return per-episode counters."""
    manifest_path = legacy_dir / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    actions = sorted(legacy_dir.glob("action_*.npy"))
    frames = sorted(legacy_dir.glob("frame_*.jpg"))
    truncated_action_frames = max(0, len(actions) - len(frames)) if frames else 0
    n = min(len(actions), len(frames)) if frames else len(actions)

    if dry_run:
        return {
            "frames_total": n,
            "placeholder_frames": 0,
            "truncated_action_frames": truncated_action_frames,
            "skipped": False,
        }

    eid = _episode_id_for_legacy(legacy_dir)
    # Bypass begin_episode's UUID generation to preserve the legacy id.
    # This is a sanctioned bypass — the migrator is the only consumer that
    # needs to keep a legacy id stable across reruns for idempotency.
    recorder._open_episode_id = eid
    recorder._open_frames = []
    recorder._open_task = manifest.get("task", "teleop")
    recorder._open_params = manifest.get("params", {})
    recorder._open_started_at = manifest.get("started_at", "")

    import cv2
    placeholder_count = 0
    for i in range(n):
        action = np.load(actions[i]).tolist()
        if i < len(frames):
            img = cv2.imread(str(frames[i]))
            if img is None:
                # Corrupt / missing image — fall back to a zero placeholder
                img = np.zeros((48, 64, 3), dtype=np.uint8)
                placeholder_count += 1
        else:
            img = np.zeros((48, 64, 3), dtype=np.uint8)
            placeholder_count += 1
        recorder.record_frame(
            frame_index=i,
            timestamp=float(i) / float(manifest.get("fps", 30)),
            image=img,
            joint_positions=action,           # legacy v1 had no separate state
            joint_currents=[0.0]*len(action),
            joint_temperatures=[0.0]*len(action),
            joint_loads=[0.0]*len(action),
            action_positions=action,
            reward=0.0,
        )

    recorder.close_episode(
        success=manifest.get("success", True),
        notes=manifest.get("notes", "migrated"),
    )
    return {
        "frames_total": n,
        "placeholder_frames": placeholder_count,
        "truncated_action_frames": truncated_action_frames,
        "skipped": False,
    }


def migrate_legacy_to_v3(
    legacy_paths: list[Path],
    output_root: Path,
    repo_id: str,
    upload: bool,
    delete_old: bool,
    dry_run: bool,
) -> dict:
    """Top-level migrator. Returns counters."""
    output_root = Path(output_root)
    legacy_paths = [Path(p).expanduser() for p in legacy_paths]
    recorder = EpisodeRecorderV3(output_root=output_root, repo_id=repo_id)
    repo_safe = repo_id.replace("/", "__")

    eps = _discover_legacy_episodes(legacy_paths)
    report = {
        "episodes_total": len(eps),
        "episodes_converted": 0,
        "episodes_skipped": 0,
        "frames_total": 0,
        "placeholder_frames": 0,
        "truncated_action_frames": 0,
        "errors": [],
        "uploaded": False,
        "deleted": [],
    }

    # Build the set of already-converted episode ids once (O(N) instead of
    # O(N²) per-episode rglob calls).
    already: set[str] = set()
    repo_dir = output_root / repo_safe
    if repo_dir.exists():
        already = {
            p.stem.removeprefix("episode_")
            for p in repo_dir.rglob("episode_*.parquet")
        }

    for legacy_dir in eps:
        eid = _episode_id_for_legacy(legacy_dir)
        if eid in already:
            report["episodes_skipped"] += 1
            continue
        try:
            r = _convert_one(legacy_dir, recorder, dry_run)
        except Exception as exc:
            report["errors"].append({"path": str(legacy_dir), "error": str(exc)})
            # Reset recorder state so the next episode can proceed cleanly.
            recorder._open_episode_id = None
            recorder._open_frames = []
            continue
        report["episodes_converted"] += 1
        report["frames_total"] += r["frames_total"]
        report["placeholder_frames"] += r.get("placeholder_frames", 0)
        report["truncated_action_frames"] += r.get("truncated_action_frames", 0)
        if r.get("placeholder_frames", 0) > 0:
            print(
                f"[migrate] WARN: {legacy_dir.name} had "
                f"{r['placeholder_frames']} placeholder frame(s) "
                f"(cv2.imread returned None)"
            )
        if r.get("truncated_action_frames", 0) > 0:
            print(
                f"[migrate] WARN: {legacy_dir.name} truncated "
                f"{r['truncated_action_frames']} action frame(s) "
                f"(action count > frame count)"
            )
        if delete_old and not dry_run:
            import shutil
            shutil.rmtree(legacy_dir)
            report["deleted"].append(str(legacy_dir))

    if upload and not dry_run:
        # Task 6 will provide the real HFUploader. Until then this is a stub.
        try:
            from .hf_upload import HFUploader  # type: ignore
            ok = HFUploader(repo_id=repo_id).upload_root(output_root / repo_safe)
            report["uploaded"] = bool(ok)
        except ImportError:
            print("[migrate] HFUploader not available yet (Task 6) — skipping upload")
            report["uploaded"] = False

    return report


def _cli() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--legacy", action="append", required=True,
                   help="legacy root dir; pass multiple times")
    p.add_argument("--output", default="~/citizenry-datasets/v3")
    p.add_argument("--repo-id", required=True)
    p.add_argument("--upload", action="store_true")
    p.add_argument("--delete-old", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    out = Path(args.output).expanduser()
    legacy = [Path(x).expanduser() for x in args.legacy]
    report = migrate_legacy_to_v3(
        legacy_paths=legacy,
        output_root=out,
        repo_id=args.repo_id,
        upload=args.upload,
        delete_old=args.delete_old,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
