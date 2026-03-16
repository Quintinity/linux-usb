"""Universal Episode Recorder — records every robot action as a training episode.

Every operation (teleop, calibration, tasks, reflexes) produces an episode
with synchronized camera frames + joint states + actions. Episodes are stored
in LeRobot-compatible format for training and in JSONL for Claude analysis.

Usage:
    recorder = EpisodeRecorder(citizen)
    recorder.begin_episode("pick_and_place", {"target": "red_block"})
    # During operation:
    recorder.record_frame(camera_frame, joint_positions, action_positions)
    # On completion:
    recorder.end_episode(success=True, notes="picked up red block")
"""

from __future__ import annotations

import json
import time
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .persistence import CITIZENRY_DIR

EPISODES_DIR = CITIZENRY_DIR / "episodes"

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]


@dataclass
class EpisodeFrame:
    """A single frame in an episode — observation + state + action."""
    frame_index: int
    timestamp: float
    # Observation
    image_path: str = ""           # Path to saved JPEG
    # State (what the robot IS doing)
    joint_positions: list[int] = field(default_factory=list)  # 6 raw servo positions
    joint_currents: list[float] = field(default_factory=list)  # 6 current readings (mA)
    joint_temperatures: list[float] = field(default_factory=list)  # 6 temperatures
    joint_loads: list[float] = field(default_factory=list)  # 6 load percentages
    # Action (what the robot was TOLD to do)
    action_positions: list[int] = field(default_factory=list)  # 6 target positions
    # Meta
    reward: float = 0.0
    done: bool = False

    def to_dict(self) -> dict:
        return {
            "idx": self.frame_index,
            "t": round(self.timestamp, 4),
            "state": self.joint_positions,
            "action": self.action_positions,
            "current": self.joint_currents,
            "reward": self.reward,
            "done": self.done,
            "image": self.image_path,
        }


@dataclass
class EpisodeMetadata:
    """Metadata for a complete episode."""
    episode_id: int
    task: str                      # "teleop", "pick_and_place", "calibration", "basic_gesture/wave"
    citizen_name: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_s: float = 0.0
    frame_count: int = 0
    fps: float = 0.0
    success: bool = False
    reward_total: float = 0.0
    notes: str = ""
    params: dict = field(default_factory=dict)  # Task-specific params
    # Performance metrics
    avg_current_ma: float = 0.0
    max_temperature: float = 0.0
    position_error_mean: float = 0.0  # Mean |target - actual|

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "task": self.task,
            "citizen": self.citizen_name,
            "started_at": self.started_at,
            "duration_s": round(self.duration_s, 2),
            "frames": self.frame_count,
            "fps": round(self.fps, 1),
            "success": self.success,
            "reward_total": round(self.reward_total, 2),
            "notes": self.notes,
            "params": self.params,
            "avg_current_ma": round(self.avg_current_ma, 1),
            "max_temperature": round(self.max_temperature, 1),
            "position_error_mean": round(self.position_error_mean, 1),
        }


class EpisodeRecorder:
    """Records every robot operation as a training episode."""

    def __init__(self, citizen_name: str = ""):
        self.citizen_name = citizen_name
        self._current_episode: list[EpisodeFrame] = []
        self._metadata: EpisodeMetadata | None = None
        self._episode_dir: Path | None = None
        self._episode_count = self._count_existing_episodes()
        self._recording = False
        self._camera_cap = None

    def begin_episode(self, task: str, params: dict | None = None,
                      camera_index: int = -1):
        """Start recording a new episode."""
        if self._recording:
            self.end_episode(success=False, notes="interrupted by new episode")

        self._episode_count += 1
        ep_id = self._episode_count

        self._episode_dir = EPISODES_DIR / f"episode_{ep_id:06d}"
        self._episode_dir.mkdir(parents=True, exist_ok=True)
        (self._episode_dir / "frames").mkdir(exist_ok=True)

        self._metadata = EpisodeMetadata(
            episode_id=ep_id,
            task=task,
            citizen_name=self.citizen_name,
            started_at=time.time(),
            params=params or {},
        )
        self._current_episode = []
        self._recording = True

        # Open camera if requested
        if camera_index >= 0:
            try:
                import cv2
                self._camera_cap = cv2.VideoCapture(camera_index)
                self._camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self._camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            except Exception:
                self._camera_cap = None

    def record_frame(
        self,
        joint_positions: dict[str, int] | list[int] | None = None,
        action_positions: dict[str, int] | list[int] | None = None,
        joint_currents: dict[str, float] | list[float] | None = None,
        joint_temperatures: list[float] | None = None,
        joint_loads: list[float] | None = None,
        camera_frame: np.ndarray | None = None,
        reward: float = 0.0,
    ):
        """Record a single frame of the episode."""
        if not self._recording:
            return

        frame_idx = len(self._current_episode)

        # Convert dict → list if needed
        state = self._to_list(joint_positions)
        action = self._to_list(action_positions) or state  # Default action = current state
        currents = self._to_list(joint_currents) if joint_currents else []

        # Save camera frame
        image_path = ""
        if camera_frame is not None:
            import cv2
            fname = f"{frame_idx:06d}.jpg"
            fpath = self._episode_dir / "frames" / fname
            cv2.imwrite(str(fpath), camera_frame)
            image_path = fname
        elif self._camera_cap is not None:
            import cv2
            ret, frame = self._camera_cap.read()
            if ret:
                fname = f"{frame_idx:06d}.jpg"
                fpath = self._episode_dir / "frames" / fname
                cv2.imwrite(str(fpath), frame)
                image_path = fname

        ep_frame = EpisodeFrame(
            frame_index=frame_idx,
            timestamp=time.time() - self._metadata.started_at,
            image_path=image_path,
            joint_positions=state,
            action_positions=action,
            joint_currents=currents,
            joint_temperatures=joint_temperatures or [],
            joint_loads=joint_loads or [],
            reward=reward,
        )
        self._current_episode.append(ep_frame)

    def end_episode(self, success: bool = False, notes: str = "",
                    final_reward: float = 0.0) -> EpisodeMetadata | None:
        """End the current episode and save."""
        if not self._recording or not self._metadata:
            return None

        self._recording = False

        # Mark last frame as done
        if self._current_episode:
            self._current_episode[-1].done = True
            if final_reward:
                self._current_episode[-1].reward = final_reward

        # Update metadata
        self._metadata.ended_at = time.time()
        self._metadata.duration_s = self._metadata.ended_at - self._metadata.started_at
        self._metadata.frame_count = len(self._current_episode)
        self._metadata.success = success
        self._metadata.notes = notes

        if self._metadata.duration_s > 0 and self._metadata.frame_count > 0:
            self._metadata.fps = self._metadata.frame_count / self._metadata.duration_s

        # Compute metrics from frames
        self._compute_metrics()

        # Save
        self._save_episode()

        # Release camera
        if self._camera_cap:
            self._camera_cap.release()
            self._camera_cap = None

        return self._metadata

    def _compute_metrics(self):
        """Compute aggregate metrics from episode frames."""
        if not self._current_episode:
            return

        all_currents = []
        all_temps = []
        all_errors = []

        for f in self._current_episode:
            if f.joint_currents:
                all_currents.extend(f.joint_currents)
            if f.joint_temperatures:
                all_temps.extend(f.joint_temperatures)
            if f.joint_positions and f.action_positions:
                for s, a in zip(f.joint_positions, f.action_positions):
                    all_errors.append(abs(s - a))

        if all_currents:
            self._metadata.avg_current_ma = sum(all_currents) / len(all_currents)
        if all_temps:
            self._metadata.max_temperature = max(all_temps)
        if all_errors:
            self._metadata.position_error_mean = sum(all_errors) / len(all_errors)
        self._metadata.reward_total = sum(f.reward for f in self._current_episode)

    def _save_episode(self):
        """Save episode to disk."""
        if not self._episode_dir:
            return

        # Save metadata
        meta_path = self._episode_dir / "metadata.json"
        meta_path.write_text(json.dumps(self._metadata.to_dict(), indent=2))

        # Save frames as JSONL (for Claude analysis)
        frames_path = self._episode_dir / "frames.jsonl"
        with open(frames_path, "w") as f:
            for frame in self._current_episode:
                f.write(json.dumps(frame.to_dict()) + "\n")

        # Save as numpy arrays (for LeRobot conversion)
        if self._current_episode:
            states = np.array([f.joint_positions for f in self._current_episode
                              if f.joint_positions], dtype=np.float32)
            actions = np.array([f.action_positions for f in self._current_episode
                               if f.action_positions], dtype=np.float32)
            if states.size > 0:
                np.save(self._episode_dir / "states.npy", states)
            if actions.size > 0:
                np.save(self._episode_dir / "actions.npy", actions)

    def _to_list(self, data) -> list:
        """Convert dict or list to list of 6 motor values."""
        if data is None:
            return []
        if isinstance(data, dict):
            return [data.get(name, 0) for name in MOTOR_NAMES]
        return list(data)

    def _count_existing_episodes(self) -> int:
        if not EPISODES_DIR.exists():
            return 0
        return len([d for d in EPISODES_DIR.iterdir() if d.is_dir()])

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def current_frame_count(self) -> int:
        return len(self._current_episode)


# ── Episode browsing ──────────────────────────────────────────────────────────

def list_episodes(limit: int = 20) -> list[dict]:
    """List recent episodes with metadata."""
    episodes = []
    if not EPISODES_DIR.exists():
        return episodes
    for d in sorted(EPISODES_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_path = d / "metadata.json"
        if meta_path.exists():
            try:
                episodes.append(json.loads(meta_path.read_text()))
            except Exception:
                episodes.append({"episode_id": d.name, "error": "corrupt"})
        if len(episodes) >= limit:
            break
    return episodes


def load_episode(episode_id: int) -> dict:
    """Load a complete episode for analysis."""
    ep_dir = EPISODES_DIR / f"episode_{episode_id:06d}"
    if not ep_dir.exists():
        return {"error": f"episode {episode_id} not found"}

    data = {}

    # Metadata
    meta_path = ep_dir / "metadata.json"
    if meta_path.exists():
        data["metadata"] = json.loads(meta_path.read_text())

    # Frames
    frames_path = ep_dir / "frames.jsonl"
    if frames_path.exists():
        data["frames"] = [json.loads(line) for line in frames_path.read_text().strip().split("\n") if line]

    # Numpy arrays
    states_path = ep_dir / "states.npy"
    if states_path.exists():
        data["states_shape"] = list(np.load(states_path).shape)

    actions_path = ep_dir / "actions.npy"
    if actions_path.exists():
        data["actions_shape"] = list(np.load(actions_path).shape)

    # Image count
    frames_dir = ep_dir / "frames"
    if frames_dir.exists():
        data["image_count"] = len([f for f in frames_dir.iterdir() if f.suffix == ".jpg"])

    return data


def get_episode_summary(episode_id: int) -> str:
    """Get a natural language summary of an episode for Claude analysis."""
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
