"""Memory System — episodic, semantic, and procedural memory.

Citizens remember what happened (episodic), what they know (semantic),
and how to do things (procedural). Memory consolidates during sleep.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from collections import deque

from .persistence import CITIZENRY_DIR


@dataclass
class Episode:
    """An episodic memory — what happened, where, when, outcome."""
    what: str                          # "pick_and_place red_block"
    where: dict[str, Any] = field(default_factory=dict)   # Joint positions, location
    when: float = field(default_factory=time.time)
    outcome: str = ""                  # "success", "failed", "interrupted"
    importance: float = 0.5            # 0-1, affects retention
    details: dict[str, Any] = field(default_factory=dict)
    consolidated: bool = False         # True after sleep processing

    def to_dict(self) -> dict:
        return {
            "what": self.what, "where": self.where, "when": self.when,
            "outcome": self.outcome, "importance": self.importance,
            "details": self.details, "consolidated": self.consolidated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Episode:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SemanticFact:
    """A piece of semantic knowledge — what the citizen knows about the world."""
    subject: str       # "red_block"
    relation: str      # "usually_at", "weighs", "color_is"
    object: str        # "left_table", "50g", "red"
    confidence: float = 0.5
    source: str = ""   # "observation", "told_by_governor", "consolidated"
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"subject": self.subject, "relation": self.relation,
                "object": self.object, "confidence": round(self.confidence, 2)}


@dataclass
class Procedure:
    """A procedural memory — how to do something."""
    skill_name: str
    context: str = ""                  # "round_objects", "heavy_objects"
    parameters: dict[str, float] = field(default_factory=dict)
    success_rate: float = 0.5
    attempt_count: int = 0
    last_used: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "skill": self.skill_name, "context": self.context,
            "params": self.parameters, "success": round(self.success_rate, 2),
            "attempts": self.attempt_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Procedure:
        return cls(
            skill_name=d.get("skill", ""), context=d.get("context", ""),
            parameters=d.get("params", {}), success_rate=d.get("success", 0.5),
            attempt_count=d.get("attempts", 0),
        )


class CitizenMemory:
    """The complete memory system for a citizen."""

    MAX_EPISODES = 500
    MAX_FACTS = 200
    MAX_PROCEDURES = 100

    def __init__(self):
        self.episodes: deque[Episode] = deque(maxlen=self.MAX_EPISODES)
        self.facts: list[SemanticFact] = []
        self.procedures: dict[str, list[Procedure]] = {}  # skill → [procedures]

    def remember_episode(self, what: str, outcome: str, importance: float = 0.5, **details):
        """Record an episodic memory."""
        ep = Episode(what=what, outcome=outcome, importance=importance, details=details)
        self.episodes.append(ep)

    def learn_fact(self, subject: str, relation: str, obj: str, confidence: float = 0.5, source: str = "observation"):
        """Add or update a semantic fact."""
        # Check for existing
        for fact in self.facts:
            if fact.subject == subject and fact.relation == relation:
                # Update with EMA
                fact.object = obj
                fact.confidence = fact.confidence * 0.7 + confidence * 0.3
                fact.updated_at = time.time()
                return
        self.facts.append(SemanticFact(subject, relation, obj, confidence, source))
        if len(self.facts) > self.MAX_FACTS:
            # Remove lowest confidence
            self.facts.sort(key=lambda f: f.confidence)
            self.facts = self.facts[-self.MAX_FACTS:]

    def store_procedure(self, skill: str, context: str, parameters: dict, success: bool):
        """Store or update a procedural memory."""
        if skill not in self.procedures:
            self.procedures[skill] = []

        # Find matching context
        for proc in self.procedures[skill]:
            if proc.context == context:
                alpha = 0.2
                proc.success_rate = proc.success_rate + alpha * ((1.0 if success else 0.0) - proc.success_rate)
                proc.attempt_count += 1
                proc.parameters = parameters  # Use latest params
                proc.last_used = time.time()
                return

        self.procedures[skill].append(Procedure(
            skill_name=skill, context=context, parameters=parameters,
            success_rate=1.0 if success else 0.0, attempt_count=1,
        ))
        # Limit per skill
        if len(self.procedures[skill]) > 20:
            self.procedures[skill].sort(key=lambda p: p.success_rate)
            self.procedures[skill] = self.procedures[skill][-20:]

    def recall_procedure(self, skill: str, context: str = "") -> Procedure | None:
        """Recall the best procedure for a skill + context."""
        procs = self.procedures.get(skill, [])
        if not procs:
            return None
        # Prefer matching context
        matching = [p for p in procs if p.context == context]
        if matching:
            return max(matching, key=lambda p: p.success_rate)
        return max(procs, key=lambda p: p.success_rate)

    def query_facts(self, subject: str = "", relation: str = "") -> list[SemanticFact]:
        """Query semantic memory."""
        results = self.facts
        if subject:
            results = [f for f in results if f.subject == subject]
        if relation:
            results = [f for f in results if f.relation == relation]
        return results

    def recent_episodes(self, count: int = 10) -> list[Episode]:
        return list(self.episodes)[-count:]

    def unconsolidated_count(self) -> int:
        return sum(1 for e in self.episodes if not e.consolidated)

    def stats(self) -> dict:
        return {
            "episodes": len(self.episodes),
            "unconsolidated": self.unconsolidated_count(),
            "facts": len(self.facts),
            "procedures": sum(len(v) for v in self.procedures.values()),
        }

    def save(self, name: str):
        """Persist memory to disk."""
        CITIZENRY_DIR.mkdir(parents=True, exist_ok=True)
        path = CITIZENRY_DIR / f"{name}.memory.json"
        data = {
            "episodes": [e.to_dict() for e in self.episodes],
            "facts": [f.to_dict() for f in self.facts],
            "procedures": {k: [p.to_dict() for p in v] for k, v in self.procedures.items()},
        }
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2) + "\n")
            tmp.replace(path)
        except OSError:
            if tmp.exists():
                tmp.unlink()

    def load(self, name: str):
        """Load memory from disk."""
        path = CITIZENRY_DIR / f"{name}.memory.json"
        try:
            data = json.loads(path.read_text())
            for e in data.get("episodes", []):
                self.episodes.append(Episode.from_dict(e))
            for f in data.get("facts", []):
                self.facts.append(SemanticFact(**{k: v for k, v in f.items() if k in SemanticFact.__dataclass_fields__}))
            for skill, procs in data.get("procedures", {}).items():
                self.procedures[skill] = [Procedure.from_dict(p) for p in procs]
        except (OSError, json.JSONDecodeError):
            pass
