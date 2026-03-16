"""Data Collection — record camera + arm episodes for LeRobot training.

Records observation frames (camera) + action positions (arm servo positions)
as LeRobot-compatible datasets. Integrates with the citizenry protocol
so the governor can say "start recording" / "stop recording".
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class RecordingSession:
    """Tracks a data collection session."""
    task_label: str = "teleoperation"
    episode_count: int = 0
    frame_count: int = 0
    is_recording: bool = False
    started_at: float = 0.0
    fps: int = 30
    dataset_path: str = ""


class DataCollector:
    """Records camera frames + arm positions as LeRobot training data.

    Usage:
        collector = DataCollector(governor, repo_id="user/my-dataset")
        collector.start_recording(task="pick and place")
        # ... frames are added automatically from teleop ...
        collector.stop_recording()  # saves episode
        collector.finalize()        # closes dataset, computes stats
    """

    def __init__(
        self,
        governor,
        repo_id: str = "local/citizenry-data",
        fps: int = 30,
        output_dir: str | None = None,
    ):
        self.governor = governor
        self.repo_id = repo_id
        self.fps = fps
        self.output_dir = output_dir or str(Path.home() / "citizenry-datasets")
        self.session = RecordingSession()
        self._dataset = None
        self._frame_buffer: list[dict] = []

    def start_recording(self, task: str = "teleoperation") -> bool:
        """Start recording a new episode."""
        if self.session.is_recording:
            return False

        self.session = RecordingSession(
            task_label=task,
            is_recording=True,
            started_at=time.time(),
            fps=self.fps,
        )
        self._frame_buffer = []

        # Try to create LeRobot dataset
        try:
            self._init_dataset()
            self.governor._log(f"recording started: {task} @ {self.fps} FPS")
            return True
        except Exception as e:
            self.governor._log(f"recording failed to start: {e}")
            # Fall back to simple frame buffer
            self.governor._log("recording in buffer mode (no lerobot)")
            return True

    def add_frame(
        self,
        camera_frame: np.ndarray | None = None,
        arm_positions: dict[str, int] | None = None,
    ):
        """Add a frame to the current recording."""
        if not self.session.is_recording:
            return

        frame_data = {
            "timestamp": time.time() - self.session.started_at,
            "frame_index": self.session.frame_count,
            "task": self.session.task_label,
        }

        if arm_positions:
            # Convert to numpy array in joint order
            motor_names = ["shoulder_pan", "shoulder_lift", "elbow_flex",
                          "wrist_flex", "wrist_roll", "gripper"]
            positions = np.array([arm_positions.get(n, 2048) for n in motor_names], dtype=np.float32)
            frame_data["action_joint_pos"] = positions

        if camera_frame is not None:
            frame_data["observation_camera_rgb"] = camera_frame

        self._frame_buffer.append(frame_data)
        self.session.frame_count += 1

        # Write to lerobot dataset if available
        if self._dataset is not None:
            try:
                self._dataset.add_frame(frame_data)
            except Exception:
                pass

    def stop_recording(self) -> dict:
        """Stop recording and save the episode."""
        if not self.session.is_recording:
            return {"error": "not recording"}

        self.session.is_recording = False
        duration = time.time() - self.session.started_at

        # Save episode to lerobot if available
        if self._dataset is not None:
            try:
                self._dataset.save_episode()
                self.session.episode_count += 1
            except Exception as e:
                self.governor._log(f"episode save failed: {e}")

        result = {
            "episode": self.session.episode_count,
            "frames": self.session.frame_count,
            "duration_s": round(duration, 1),
            "fps_actual": round(self.session.frame_count / duration, 1) if duration > 0 else 0,
            "task": self.session.task_label,
        }

        self.governor._log(
            f"episode saved: {result['frames']} frames, "
            f"{result['duration_s']}s, {result['fps_actual']} FPS"
        )

        # Save buffer to disk as fallback
        if self._dataset is None and self._frame_buffer:
            self._save_buffer_fallback()

        self._frame_buffer = []
        return result

    def finalize(self):
        """Finalize the dataset — compute stats, close writers."""
        if self._dataset is not None:
            try:
                self._dataset.finalize()
                self.governor._log(f"dataset finalized: {self.repo_id}")
            except Exception as e:
                self.governor._log(f"finalize failed: {e}")

    def _init_dataset(self):
        """Try to create a LeRobot dataset."""
        try:
            from lerobot.datasets.lerobot_dataset import LeRobotDataset

            # Define features for SO-101 + camera
            features = {
                "observation_camera_rgb": {
                    "dtype": "image",
                    "shape": (480, 640, 3),
                    "names": ["height", "width", "channels"],
                },
                "action_joint_pos": {
                    "dtype": "float32",
                    "shape": (6,),
                    "names": ["shoulder_pan", "shoulder_lift", "elbow_flex",
                             "wrist_flex", "wrist_roll", "gripper"],
                },
            }

            self._dataset = LeRobotDataset.create(
                repo_id=self.repo_id,
                fps=self.fps,
                features=features,
                use_videos=False,  # PNG frames for simplicity
            )
            self.session.dataset_path = str(self._dataset.root)
        except ImportError:
            self._dataset = None
            self.governor._log("lerobot not available — using buffer mode")
        except Exception as e:
            self._dataset = None
            self.governor._log(f"dataset creation failed: {e}")

    def _save_buffer_fallback(self):
        """Save frame buffer as simple numpy files."""
        output = Path(self.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        ep_dir = output / f"episode_{self.session.episode_count:04d}"
        ep_dir.mkdir(exist_ok=True)

        for i, frame in enumerate(self._frame_buffer):
            if "action_joint_pos" in frame:
                np.save(ep_dir / f"action_{i:06d}.npy", frame["action_joint_pos"])
            if "observation_camera_rgb" in frame:
                np.save(ep_dir / f"obs_{i:06d}.npy", frame["observation_camera_rgb"])

        self.governor._log(f"buffer saved to {ep_dir} ({len(self._frame_buffer)} frames)")
