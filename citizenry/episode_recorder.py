"""Episode Recorder — records robot episodes in LeRobotDataset v3 layout.

Records every robot action as a training episode in v3 format (Parquet chunks
+ MP4 video). Use ManipulatorCitizen._recorder to access this in production.

Usage:
    recorder = EpisodeRecorder(output_root=..., repo_id="local/citizenry-data", fps=30)
    recorder.begin_episode("pick_and_place", {"target": "red_block"})
    # During operation:
    recorder.record_frame(frame_index=..., timestamp=..., image=..., ...)
    # On completion:
    recorder.close_episode(success=True, notes="picked up red block")
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .persistence import CITIZENRY_DIR

EPISODES_DIR = CITIZENRY_DIR / "episodes"

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]


# ── LeRobotDataset v3 writer ──────────────────────────────────────────────────


class EpisodeRecorder:
    """Records episodes directly into a LeRobotDataset v3-style layout.

    Output layout (rooted at output_root):
        output_root/<repo_safe>/
          data/chunk_NNN/episode_*.parquet
          data/chunk_NNN/episode_*.json
          videos/chunk_NNN/episode_*_<cam>.mp4
          attribution.json   <- per-recorder sidecar

    On close_episode(), Parquet+MP4 chunks are finalized; HFUploader
    (Task 6) detects new content via output_root mtime and uploads.
    """

    def __init__(
        self,
        output_root,           # Path | str
        repo_id: str = "local/citizenry-data",
        fps: int = 30,
        camera_names: tuple = ("base",),
        episodes_per_chunk: int = 500,
    ):
        self.output_root = Path(output_root)
        self.repo_id = repo_id
        self.fps = int(fps)
        self.camera_names = tuple(camera_names)
        self.episodes_per_chunk = int(episodes_per_chunk)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._open_episode_id: str | None = None
        self._open_frames: list = []
        self._open_task: str = ""
        self._open_params: dict = {}
        self._open_started_at: str = ""
        self.last_episode_dir = None
        # Attribution sidecar fields:
        self._attribution: dict = {}

    def set_attribution(
        self,
        node_pubkey: str,
        policy_pubkey: str | None = None,
        governor_pubkey: str | None = None,
        constitution_hash: str | None = None,
    ) -> None:
        self._attribution = {
            "node_pubkey": node_pubkey,
            "policy_pubkey": policy_pubkey,
            "governor_pubkey": governor_pubkey,
            "constitution_hash": constitution_hash,
        }

    @property
    def frame_count(self) -> int:
        """Number of frames recorded in the currently open episode."""
        return len(self._open_frames)

    def begin_episode(self, task: str, params: dict) -> str:
        """Open a new episode with a fresh UUID-based id.

        NOTE: citizenry/dataset_v3_migrate.py bypasses this method and sets
        _open_episode_id, _open_frames, _open_task, _open_params, and
        _open_started_at directly to preserve legacy episode ids across
        re-runs. If you rename or restructure those fields, update the
        migrator in lockstep.
        """
        if self._open_episode_id is not None:
            raise RuntimeError(
                f"begin_episode while episode {self._open_episode_id} is open"
            )
        self._open_episode_id = uuid.uuid4().hex[:12]
        self._open_frames = []
        self._open_task = task
        self._open_params = params or {}
        self._open_started_at = datetime.now(timezone.utc).isoformat()
        return self._open_episode_id

    def record_frame(
        self,
        frame_index: int,
        timestamp: float,
        image,            # np.ndarray HxWx3 uint8 (one camera for now)
        joint_positions,
        joint_currents,
        joint_temperatures,
        joint_loads,
        action_positions,
        reward: float = 0.0,
        done: bool = False,
        camera_name: str = "base",
    ) -> None:
        if self._open_episode_id is None:
            raise RuntimeError("record_frame without begin_episode")
        self._open_frames.append({
            "frame_index": frame_index,
            "timestamp": float(timestamp),
            "image": image,
            "camera_name": camera_name,
            "observation.state": list(joint_positions),
            "observation.current": list(joint_currents),
            "observation.temperature": list(joint_temperatures),
            "observation.load": list(joint_loads),
            "action": list(action_positions),
            "reward": float(reward),
            "done": bool(done),
        })

    def close_episode(
        self,
        success: bool,
        notes: str = "",
        reward_total: float = 0.0,
        duration_s: float = 0.0,
    ):
        if self._open_episode_id is None:
            raise RuntimeError("close_episode without begin_episode")
        eid = self._open_episode_id
        out = self._write_chunk(
            eid=eid,
            frames=self._open_frames,
            task=self._open_task,
            params=self._open_params,
            success=success,
            notes=notes,
            reward_total=reward_total,
            duration_s=duration_s,
            started_at=self._open_started_at,
        )
        # Write attribution sidecar at the per-repo root (NOT the chunk dir
        # — sidecar is shared across chunks).
        if self._attribution:
            repo_safe = self.repo_id.replace("/", "__")
            sidecar = self.output_root / repo_safe / "attribution.json"
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            sidecar.write_text(json.dumps(self._attribution, indent=2))
        self.last_episode_dir = out
        # Reset open-episode state
        self._open_episode_id = None
        self._open_frames = []
        return out

    # ---- internal ----

    def _write_chunk(
        self,
        eid: str,
        frames,
        task: str,
        params: dict,
        success: bool,
        notes: str,
        reward_total: float,
        duration_s: float,
        started_at: str,
    ):
        """Write one episode as a v3 chunk under output_root/<repo_safe>/."""
        import pyarrow as pa
        import pyarrow.parquet as pq
        # Build the table
        if not frames:
            cols = {
                "frame_index": [],
                "timestamp": [],
                "observation.state": [],
                "observation.current": [],
                "observation.temperature": [],
                "observation.load": [],
                "action": [],
                "reward": [],
                "done": [],
            }
        else:
            cols = {k: [f[k] for f in frames]
                    for k in (
                        "frame_index", "timestamp",
                        "observation.state", "observation.current",
                        "observation.temperature", "observation.load",
                        "action", "reward", "done",
                    )}
        table = pa.table(cols)
        repo_safe = self.repo_id.replace("/", "__")
        chunk_idx = self._next_chunk_index(repo_safe)
        chunk_dir = self.output_root / repo_safe / "data" / f"chunk_{chunk_idx:04d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = chunk_dir / f"episode_{eid}.parquet"
        pq.write_table(table, parquet_path)
        # MP4 per camera (only "base" camera is wired here; multi-camera
        # extension lands in Task 8 enhancement / PolicyCitizen integration)
        video_root = self.output_root / repo_safe / "videos" / f"chunk_{chunk_idx:04d}"
        video_root.mkdir(parents=True, exist_ok=True)
        if frames:
            try:
                self._write_mp4(
                    path=video_root / f"episode_{eid}_base.mp4",
                    images=[f["image"] for f in frames],
                )
            except Exception as e:
                # Don't orphan the parquet — log and continue.
                # The per-episode JSON below will reflect the frame count;
                # consumers detect missing videos via os.path.exists.
                print(f"[recorder] WARN: MP4 write failed for {eid}: {e}")
        # Per-episode metadata (chunk-level, not dataset-level)
        meta_path = chunk_dir / f"episode_{eid}.json"
        meta_path.write_text(json.dumps({
            "episode_id": eid,
            "task": task,
            "params": params,
            "success": success,
            "notes": notes,
            "reward_total": reward_total,
            "duration_s": duration_s,
            "started_at": started_at,
            "frame_count": len(frames),
        }, indent=2))
        return chunk_dir

    def _next_chunk_index(self, repo_safe: str) -> int:
        d = self.output_root / repo_safe / "data"
        if not d.exists():
            return 0
        total_episodes = sum(1 for _ in d.glob("chunk_*/episode_*.parquet"))
        return total_episodes // self.episodes_per_chunk

    def _write_mp4(self, path, images) -> None:
        import cv2
        if not images:
            return
        h, w = images[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(path), fourcc, self.fps, (w, h))
        try:
            for img in images:
                writer.write(img)
        finally:
            writer.release()


# ── Legacy v1 episode browsing helpers ───────────────────────────────────────
# These helpers read the old ~/.citizenry/episodes/ JSONL layout that was
# written by the removed v1 EpisodeRecorder class. The v1 data was migrated
# and deleted, so these functions return empty results in practice. They are
# retained for compatibility with governor_cli.py and learning_loop.py callers
# that still reference them; those callers can be cleaned up in a future task.

def list_episodes(limit: int = 20) -> list[dict]:
    """List recent v1-format episodes (returns empty after migration)."""
    import json as _json
    episodes = []
    if not EPISODES_DIR.exists():
        return episodes
    for d in sorted(EPISODES_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_path = d / "metadata.json"
        if meta_path.exists():
            try:
                episodes.append(_json.loads(meta_path.read_text()))
            except Exception:
                episodes.append({"episode_id": d.name, "error": "corrupt"})
        if len(episodes) >= limit:
            break
    return episodes


def load_episode(episode_id: int) -> dict:
    """Load a v1-format episode (returns error dict after migration)."""
    ep_dir = EPISODES_DIR / f"episode_{episode_id:06d}"
    if not ep_dir.exists():
        return {"error": f"episode {episode_id} not found"}

    import json as _json
    data = {}

    meta_path = ep_dir / "metadata.json"
    if meta_path.exists():
        data["metadata"] = _json.loads(meta_path.read_text())

    frames_path = ep_dir / "frames.jsonl"
    if frames_path.exists():
        data["frames"] = [_json.loads(line) for line in frames_path.read_text().strip().split("\n") if line]

    states_path = ep_dir / "states.npy"
    if states_path.exists():
        data["states_shape"] = list(np.load(states_path).shape)

    actions_path = ep_dir / "actions.npy"
    if actions_path.exists():
        data["actions_shape"] = list(np.load(actions_path).shape)

    frames_dir = ep_dir / "frames"
    if frames_dir.exists():
        data["image_count"] = len([f for f in frames_dir.iterdir() if f.suffix == ".jpg"])

    return data


def get_episode_summary(episode_id: int) -> str:
    """Get a natural language summary of a v1-format episode."""
    data = load_episode(episode_id)
    if "error" in data:
        return data["error"]

    meta = data.get("metadata", {})
    frames = data.get("frames", [])

    parts = [f"Episode {meta.get('episode_id', '?')}: {meta.get('task', '?')}"]
    parts.append(f"Citizen: {meta.get('citizen', '?')}")
    parts.append(f"Duration: {meta.get('duration_s', 0):.1f}s, {meta.get('frames', 0)} frames at {meta.get('fps', 0):.1f} FPS")
    parts.append(f"Success: {meta.get('success', False)}")
    parts.append(f"Reward: {meta.get('reward_total', 0):.2f}")

    if meta.get("avg_current_ma"):
        parts.append(f"Avg current: {meta['avg_current_ma']:.0f}mA")
    if meta.get("max_temperature"):
        parts.append(f"Max temperature: {meta['max_temperature']:.0f}C")
    if meta.get("position_error_mean"):
        parts.append(f"Mean position error: {meta['position_error_mean']:.0f}")

    if frames:
        first = frames[0]
        last = frames[-1]
        parts.append(f"Start state: {first.get('state', [])}")
        parts.append(f"End state: {last.get('state', [])}")
        parts.append(f"Start action: {first.get('action', [])}")
        parts.append(f"End action: {last.get('action', [])}")

    if meta.get("notes"):
        parts.append(f"Notes: {meta['notes']}")

    return "\n".join(parts)
