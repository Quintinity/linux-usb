"""Per-citizen cache of the latest camera frames + follower states.

PolicyCitizen feeds this to SmolVLA. Updates come from neighbor ADVERTISE
bodies (frame: bytes) and REPORT bodies (state: list[int]).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class _FrameEntry:
    frame: np.ndarray
    timestamp: float


@dataclass
class _StateEntry:
    state: np.ndarray
    timestamp: float


class ObservationCache:
    """Stores the most recent observation per camera role and follower pubkey.

    Keys:
      - frames are keyed by ``camera_role`` (e.g. "wrist", "base")
      - states are keyed by ``follower_pubkey`` (the manipulator citizen's hex pubkey)

    Reads return ``None`` when the entry is missing or older than ``max_age_s``.
    """

    def __init__(self):
        self._frames: dict[str, _FrameEntry] = {}   # keyed by camera role
        self._states: dict[str, _StateEntry] = {}   # keyed by follower pubkey

    def update_frame(self, camera_role: str, frame: np.ndarray, timestamp: float | None = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        self._frames[camera_role] = _FrameEntry(frame=frame, timestamp=ts)

    def update_state(self, follower_pubkey: str, state, timestamp: float | None = None) -> None:
        s = state if isinstance(state, np.ndarray) else np.array(state)
        ts = timestamp if timestamp is not None else time.time()
        self._states[follower_pubkey] = _StateEntry(state=s, timestamp=ts)

    def latest_frame(self, camera_role: str, max_age_s: float = 1.0, now: float | None = None) -> np.ndarray | None:
        e = self._frames.get(camera_role)
        if e is None:
            return None
        t_now = now if now is not None else time.time()
        if t_now - e.timestamp > max_age_s:
            return None
        return e.frame

    def latest_state(self, follower_pubkey: str, max_age_s: float = 1.0, now: float | None = None) -> np.ndarray | None:
        e = self._states.get(follower_pubkey)
        if e is None:
            return None
        t_now = now if now is not None else time.time()
        if t_now - e.timestamp > max_age_s:
            return None
        return e.state
