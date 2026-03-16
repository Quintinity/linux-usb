"""Sleep Cycle — periodic maintenance, memory consolidation, dream replay.

4-phase cycle: DROWSY → LIGHT_SLEEP → DEEP_SLEEP → REM.
Sleep is active maintenance, not idle time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class SleepPhase(IntEnum):
    AWAKE = 0
    DROWSY = 1       # Transition — reduce activity
    LIGHT_SLEEP = 2  # Memory consolidation
    DEEP_SLEEP = 3   # Heavy maintenance
    REM = 4          # Dream replay


# Wake thresholds by sleep depth
WAKE_THRESHOLDS = {
    SleepPhase.DROWSY: {"emergency", "critical", "warning", "task_assigned"},
    SleepPhase.LIGHT_SLEEP: {"emergency", "critical", "task_assigned"},
    SleepPhase.DEEP_SLEEP: {"emergency", "critical"},
    SleepPhase.REM: {"emergency"},
}


@dataclass
class SleepPressure:
    """How urgently the citizen needs sleep."""
    uptime_hours: float = 0.0
    fatigue: float = 0.0
    unconsolidated_episodes: int = 0
    hours_since_last_sleep: float = 0.0

    @property
    def pressure(self) -> float:
        """0.0 = wide awake, 1.0 = desperate for sleep."""
        uptime_factor = min(1.0, self.uptime_hours / 8.0)
        fatigue_factor = self.fatigue
        episode_factor = min(1.0, self.unconsolidated_episodes / 50.0)
        time_factor = min(1.0, self.hours_since_last_sleep / 4.0)
        return max(uptime_factor, fatigue_factor, episode_factor, time_factor)

    @property
    def should_sleep(self) -> bool:
        return self.pressure > 0.7


@dataclass
class SleepSession:
    """A single sleep session."""
    started_at: float = 0.0
    ended_at: float = 0.0
    current_phase: SleepPhase = SleepPhase.AWAKE
    episodes_consolidated: int = 0
    facts_extracted: int = 0
    procedures_refined: int = 0
    immune_patterns_pruned: int = 0
    calibration_checked: bool = False
    dreams_replayed: int = 0


class SleepEngine:
    """Manages the sleep cycle for a citizen."""

    PHASE_DURATIONS = {
        SleepPhase.DROWSY: 5.0,       # 5 seconds transition
        SleepPhase.LIGHT_SLEEP: 30.0,  # 30 seconds consolidation
        SleepPhase.DEEP_SLEEP: 20.0,   # 20 seconds maintenance
        SleepPhase.REM: 15.0,          # 15 seconds replay
    }

    def __init__(self):
        self.current_session: SleepSession | None = None
        self.history: list[SleepSession] = []
        self.last_sleep_time: float = time.time()

    def compute_pressure(self, uptime_hours: float, fatigue: float,
                         unconsolidated: int) -> SleepPressure:
        hours_since = (time.time() - self.last_sleep_time) / 3600
        return SleepPressure(
            uptime_hours=uptime_hours,
            fatigue=fatigue,
            unconsolidated_episodes=unconsolidated,
            hours_since_last_sleep=hours_since,
        )

    def start_sleep(self) -> SleepSession:
        """Begin a sleep session."""
        session = SleepSession(started_at=time.time(), current_phase=SleepPhase.DROWSY)
        self.current_session = session
        return session

    def advance_phase(self) -> SleepPhase:
        """Advance to the next sleep phase."""
        if not self.current_session:
            return SleepPhase.AWAKE
        current = self.current_session.current_phase
        if current == SleepPhase.DROWSY:
            self.current_session.current_phase = SleepPhase.LIGHT_SLEEP
        elif current == SleepPhase.LIGHT_SLEEP:
            self.current_session.current_phase = SleepPhase.DEEP_SLEEP
        elif current == SleepPhase.DEEP_SLEEP:
            self.current_session.current_phase = SleepPhase.REM
        elif current == SleepPhase.REM:
            self.end_sleep()
            return SleepPhase.AWAKE
        return self.current_session.current_phase

    def end_sleep(self):
        """End the current sleep session."""
        if self.current_session:
            self.current_session.ended_at = time.time()
            self.current_session.current_phase = SleepPhase.AWAKE
            self.history.append(self.current_session)
            self.last_sleep_time = time.time()
            self.current_session = None

    def should_wake(self, event_type: str) -> bool:
        """Check if an event should wake the citizen."""
        if not self.current_session:
            return False
        phase = self.current_session.current_phase
        allowed = WAKE_THRESHOLDS.get(phase, set())
        return event_type in allowed

    @property
    def is_sleeping(self) -> bool:
        return self.current_session is not None and self.current_session.current_phase != SleepPhase.AWAKE

    @property
    def phase(self) -> SleepPhase:
        if self.current_session:
            return self.current_session.current_phase
        return SleepPhase.AWAKE

    def stats(self) -> dict:
        return {
            "sleeping": self.is_sleeping,
            "phase": self.phase.name,
            "total_sleeps": len(self.history),
            "hours_since_sleep": round((time.time() - self.last_sleep_time) / 3600, 1),
        }
