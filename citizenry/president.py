"""President — top-level governance across all governors and locations.

The president is the human's interface to the entire nation. Multiple
governors manage their local neighborhoods; the president sees them all,
routes commands across locations, and enforces nation-wide policy.

Governance hierarchy:
    President (human) → Governors (per location) → Citizens (per device)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from .protocol import MessageType, make_envelope
from .identity import load_or_create_identity, pubkey_hex, short_id


@dataclass
class GovernorRecord:
    """A known governor in the nation."""
    pubkey: str
    name: str
    location: str
    addr: tuple[str, int]
    citizen_count: int = 0
    capabilities: list[str] = field(default_factory=list)
    composite_capabilities: list[str] = field(default_factory=list)
    health: float = 1.0
    state: str = "idle"
    last_seen: float = 0.0
    laws: dict[str, Any] = field(default_factory=dict)
    growth_stage: str = "unknown"
    mood: str = "unknown"

    def is_online(self) -> bool:
        return time.time() - self.last_seen < 30  # 30s timeout for governors


@dataclass
class NationState:
    """Aggregated state of the entire nation."""
    total_governors: int = 0
    total_citizens: int = 0
    total_locations: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    active_contracts: int = 0
    composite_capabilities: list[str] = field(default_factory=list)
    warnings: int = 0
    immune_patterns: int = 0


class President:
    """The president oversees all governors across all locations.

    Routes commands to the right governor, aggregates fleet state,
    enforces nation-wide policy, and provides a unified view.
    """

    def __init__(self, name: str = "president"):
        self.name = name
        self._signing_key = load_or_create_identity(name)
        self.pubkey = pubkey_hex(self._signing_key)
        self.short_id = short_id(self.pubkey)

        self.governors: dict[str, GovernorRecord] = {}
        self.nation_laws: dict[str, Any] = {}
        self._command_history: list[dict] = []

    def register_governor(self, record: GovernorRecord) -> None:
        """Register a governor in the nation."""
        self.governors[record.pubkey] = record

    def get_governor(self, name: str) -> GovernorRecord | None:
        """Find a governor by name or location."""
        for g in self.governors.values():
            if g.name == name or g.location == name:
                return g
        return None

    def get_nation_state(self) -> NationState:
        """Aggregate state across all governors."""
        state = NationState()
        state.total_governors = len(self.governors)
        all_composites = set()
        for g in self.governors.values():
            state.total_citizens += g.citizen_count
            state.total_locations += 1
            for cap in g.composite_capabilities:
                all_composites.add(cap)
        state.composite_capabilities = sorted(all_composites)
        return state

    def route_command(self, command: str, target: str | None = None) -> list[tuple[GovernorRecord, str]]:
        """Route a command to the right governor(s).

        Args:
            command: Natural language command
            target: Governor name/location, or None for broadcast

        Returns:
            List of (governor, command) pairs to execute
        """
        self._command_history.append({
            "command": command,
            "target": target,
            "timestamp": time.time(),
        })

        if target:
            gov = self.get_governor(target)
            if gov:
                return [(gov, command)]
            return []

        # Broadcast to all governors
        return [(g, command) for g in self.governors.values() if g.is_online()]

    def broadcast_law(self, law_id: str, params: dict) -> list[str]:
        """Broadcast a nation-wide law to all governors.

        Returns list of governor names that received the law.
        """
        self.nation_laws[law_id] = params
        sent_to = []
        for g in self.governors.values():
            if g.is_online():
                sent_to.append(g.name)
        return sent_to

    def find_capability(self, capability: str) -> list[GovernorRecord]:
        """Find which governors have citizens with a given capability."""
        result = []
        for g in self.governors.values():
            if capability in g.capabilities or capability in g.composite_capabilities:
                result.append(g)
        return result

    def delegate_task(self, task_type: str, params: dict | None = None,
                      target_location: str | None = None) -> GovernorRecord | None:
        """Delegate a task to the best governor.

        If target_location specified, send there. Otherwise, find the
        governor with the most relevant capabilities and lowest load.
        """
        if target_location:
            gov = self.get_governor(target_location)
            if gov and gov.is_online():
                return gov
            return None

        # Find best governor for this task type
        candidates = []
        for g in self.governors.values():
            if not g.is_online():
                continue
            # Score based on citizen count (proxy for capacity) and health
            score = g.citizen_count * g.health
            candidates.append((g, score))

        if candidates:
            candidates.sort(key=lambda x: -x[1])
            return candidates[0][0]
        return None

    def nation_summary(self) -> str:
        """Natural language summary of the nation."""
        state = self.get_nation_state()
        parts = [f"Nation: {state.total_governors} governors, {state.total_citizens} citizens across {state.total_locations} locations."]

        for g in self.governors.values():
            status = "online" if g.is_online() else "offline"
            parts.append(f"  {g.name} ({g.location}): {g.citizen_count} citizens, {status}, mood: {g.mood}")

        if state.composite_capabilities:
            parts.append(f"Fleet capabilities: {', '.join(state.composite_capabilities)}")

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "id": self.short_id,
            "governors": {
                g.name: {
                    "location": g.location,
                    "citizens": g.citizen_count,
                    "online": g.is_online(),
                    "health": g.health,
                    "mood": g.mood,
                    "capabilities": g.capabilities,
                    "composites": g.composite_capabilities,
                }
                for g in self.governors.values()
            },
            "nation": self.get_nation_state().__dict__,
            "laws": self.nation_laws,
        }


# ── President CLI Commands ────────────────────────────────────────────────────

def parse_president_command(text: str) -> dict | None:
    """Parse a president-level command.

    Returns dict with: action, target, params
    """
    text = text.strip().lower()

    # Nation-wide commands
    if text in ("nation", "nation status", "fleet", "fleet status"):
        return {"action": "nation_status"}

    if text in ("governors", "locations", "who"):
        return {"action": "list_governors"}

    # Targeted commands: "tell home office to wave hello"
    if text.startswith("tell "):
        parts = text[5:].split(" to ", 1)
        if len(parts) == 2:
            return {"action": "delegate", "target": parts[0].strip(), "command": parts[1].strip()}

    # "at school: sort the blocks"
    if ": " in text and text.split(": ")[0].startswith("at "):
        location = text.split(": ")[0][3:].strip()
        command = text.split(": ", 1)[1].strip()
        return {"action": "delegate", "target": location, "command": command}

    # "all wave hello" — broadcast
    if text.startswith("all "):
        return {"action": "broadcast", "command": text[4:].strip()}

    # "law gentle everywhere"
    if text.startswith("law "):
        return {"action": "nation_law", "command": text[4:].strip()}

    return None
