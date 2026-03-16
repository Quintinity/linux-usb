"""Soul — personality, purpose, preferences, and values.

What makes each citizen unique beyond its capabilities. A soul develops
slowly through experience, creating behavioral individuality.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PersonalityProfile:
    """Big Five (OCEAN) personality dimensions + armOS-specific traits.

    Values range 0.0-1.0. Drift slowly based on task outcomes.
    """
    # Big Five
    openness: float = 0.5          # Willingness to try new approaches
    conscientiousness: float = 0.5 # Thoroughness, precision preference
    extraversion: float = 0.5      # Eagerness to collaborate, bid on tasks
    agreeableness: float = 0.5     # Willingness to yield in conflicts
    neuroticism: float = 0.5       # Sensitivity to warnings and faults

    # armOS-specific
    movement_style: float = 0.5    # 0=slow+smooth, 1=fast+aggressive
    exploration_drive: float = 0.5 # Tendency to try untested approaches
    social_drive: float = 0.5      # Preference for collaborative tasks

    def drift(self, trait: str, delta: float, rate: float = 0.01):
        """Slowly drift a trait. Rate limits the change per event."""
        current = getattr(self, trait, 0.5)
        clamped_delta = max(-rate, min(rate, delta))
        setattr(self, trait, max(0.0, min(1.0, current + clamped_delta)))

    def to_dict(self) -> dict:
        return {
            "openness": round(self.openness, 3),
            "conscientiousness": round(self.conscientiousness, 3),
            "extraversion": round(self.extraversion, 3),
            "agreeableness": round(self.agreeableness, 3),
            "neuroticism": round(self.neuroticism, 3),
            "movement_style": round(self.movement_style, 3),
            "exploration_drive": round(self.exploration_drive, 3),
            "social_drive": round(self.social_drive, 3),
        }

    @classmethod
    def from_dict(cls, d: dict) -> PersonalityProfile:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class GoalEntry:
    """A goal in the hierarchy."""
    description: str
    priority: int  # 0=survival, 1=constitutional, 2=assigned, 3=self-improvement, 4=curiosity
    active: bool = True
    created_at: float = field(default_factory=time.time)


class GoalHierarchy:
    """5-tier goal hierarchy. Higher priority always wins."""

    SURVIVAL = 0
    CONSTITUTIONAL = 1
    ASSIGNED = 2
    SELF_IMPROVEMENT = 3
    CURIOSITY = 4

    def __init__(self):
        self.goals: list[GoalEntry] = [
            GoalEntry("Protect own hardware from damage", self.SURVIVAL),
            GoalEntry("Obey constitutional safety rules", self.CONSTITUTIONAL),
            GoalEntry("Never harm humans or other citizens", self.SURVIVAL),
        ]

    def add_goal(self, description: str, priority: int):
        self.goals.append(GoalEntry(description, priority))

    def get_active(self, max_priority: int = 4) -> list[GoalEntry]:
        return sorted(
            [g for g in self.goals if g.active and g.priority <= max_priority],
            key=lambda g: g.priority,
        )

    def has_idle_goals(self) -> bool:
        """Check if there are curiosity/self-improvement goals to pursue when idle."""
        return any(g.active and g.priority >= self.SELF_IMPROVEMENT for g in self.goals)


@dataclass
class BehavioralPreferences:
    """Learned preferences for how to perform tasks."""
    approach_speed: float = 0.5     # 0=slow, 1=fast
    grip_force: float = 0.5        # 0=gentle, 1=firm
    precision_bias: float = 0.5    # 0=fast+rough, 1=slow+precise
    retry_patience: float = 0.5    # 0=give up fast, 1=keep trying

    # Per-task success rates by approach style
    task_style_scores: dict[str, dict[str, float]] = field(default_factory=dict)

    def record_outcome(self, task_type: str, style: str, success: bool):
        """Record task outcome for preference learning."""
        if task_type not in self.task_style_scores:
            self.task_style_scores[task_type] = {}
        scores = self.task_style_scores[task_type]
        # Exponential moving average
        alpha = 0.1
        current = scores.get(style, 0.5)
        scores[style] = current + alpha * ((1.0 if success else 0.0) - current)

    def best_style(self, task_type: str) -> str | None:
        """Get the best-performing style for a task type."""
        scores = self.task_style_scores.get(task_type, {})
        if not scores:
            return None
        return max(scores, key=scores.get)

    def to_dict(self) -> dict:
        return {
            "approach_speed": self.approach_speed,
            "grip_force": self.grip_force,
            "precision_bias": self.precision_bias,
            "retry_patience": self.retry_patience,
            "task_styles": self.task_style_scores,
        }

    @classmethod
    def from_dict(cls, d: dict) -> BehavioralPreferences:
        prefs = cls(
            approach_speed=d.get("approach_speed", 0.5),
            grip_force=d.get("grip_force", 0.5),
            precision_bias=d.get("precision_bias", 0.5),
            retry_patience=d.get("retry_patience", 0.5),
        )
        prefs.task_style_scores = d.get("task_styles", {})
        return prefs


@dataclass
class CitizenSoul:
    """The complete soul of a citizen."""
    personality: PersonalityProfile = field(default_factory=PersonalityProfile)
    goals: GoalHierarchy = field(default_factory=GoalHierarchy)
    preferences: BehavioralPreferences = field(default_factory=BehavioralPreferences)
    life_events: list[dict] = field(default_factory=list)
    born_at: float = field(default_factory=time.time)

    def record_life_event(self, event_type: str, detail: str):
        self.life_events.append({
            "type": event_type,
            "detail": detail,
            "timestamp": time.time(),
        })
        # Keep last 500 events
        if len(self.life_events) > 500:
            self.life_events = self.life_events[-500:]

    def on_task_success(self, task_type: str):
        """Personality drifts on success: more confident, more open."""
        self.personality.drift("openness", 0.005)
        self.personality.drift("neuroticism", -0.003)
        self.personality.drift("conscientiousness", 0.002)

    def on_task_failure(self, task_type: str):
        """Personality drifts on failure: more cautious, more neurotic."""
        self.personality.drift("neuroticism", 0.005)
        self.personality.drift("openness", -0.002)
        self.personality.drift("movement_style", -0.003)  # Slow down

    def on_pain_event(self):
        """Pain makes the citizen more cautious."""
        self.personality.drift("neuroticism", 0.01)
        self.personality.drift("movement_style", -0.005)

    def on_collaboration(self):
        """Successful collaboration increases social traits."""
        self.personality.drift("extraversion", 0.005)
        self.personality.drift("agreeableness", 0.003)
        self.personality.drift("social_drive", 0.005)

    def to_dict(self) -> dict:
        return {
            "personality": self.personality.to_dict(),
            "preferences": self.preferences.to_dict(),
            "life_events_count": len(self.life_events),
            "born_at": self.born_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CitizenSoul:
        soul = cls()
        if "personality" in d:
            soul.personality = PersonalityProfile.from_dict(d["personality"])
        if "preferences" in d:
            soul.preferences = BehavioralPreferences.from_dict(d["preferences"])
        soul.born_at = d.get("born_at", time.time())
        return soul
