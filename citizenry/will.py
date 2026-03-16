"""Dead Citizen's Will — final broadcast before shutdown.

When a citizen detects imminent shutdown, it broadcasts a "will" containing
current tasks, partial results, and knowledge to preserve. Neighbors absorb
the knowledge and tasks re-enter the marketplace.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class CitizenWill:
    """The final testament of a departing citizen."""

    citizen_name: str = ""
    citizen_pubkey: str = ""
    citizen_type: str = ""
    reason: str = "shutdown"  # shutdown, crash, low_battery, thermal
    current_task_id: str | None = None
    current_task_type: str | None = None
    partial_results: dict[str, Any] = field(default_factory=dict)
    xp: dict[str, int] = field(default_factory=dict)
    active_contracts: list[str] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    uptime_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_report_body(self) -> dict:
        """Convert to a REPORT message body."""
        return {
            "type": "will",
            "citizen": self.citizen_name,
            "citizen_pubkey": self.citizen_pubkey,
            "citizen_type": self.citizen_type,
            "reason": self.reason,
            "current_task_id": self.current_task_id,
            "current_task_type": self.current_task_type,
            "partial_results": self.partial_results,
            "xp": self.xp,
            "active_contracts": self.active_contracts,
            "warnings": self.warnings,
            "uptime_seconds": self.uptime_seconds,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_report_body(cls, body: dict) -> CitizenWill:
        return cls(
            citizen_name=body.get("citizen", ""),
            citizen_pubkey=body.get("citizen_pubkey", ""),
            citizen_type=body.get("citizen_type", ""),
            reason=body.get("reason", "unknown"),
            current_task_id=body.get("current_task_id"),
            current_task_type=body.get("current_task_type"),
            partial_results=body.get("partial_results", {}),
            xp=body.get("xp", {}),
            active_contracts=body.get("active_contracts", []),
            warnings=body.get("warnings", {}),
            uptime_seconds=body.get("uptime_seconds", 0.0),
            timestamp=body.get("timestamp", time.time()),
        )


def create_will(citizen) -> CitizenWill:
    """Create a will from a citizen's current state."""
    current_task_id = None
    current_task_type = None
    if hasattr(citizen, '_current_task_id'):
        current_task_id = citizen._current_task_id
    if hasattr(citizen, '_current_task_type'):
        current_task_type = citizen._current_task_type

    active_contracts = [c.id for c in citizen.contracts.get_active()]

    warnings = [w.to_report_body() for w in citizen.mycelium.active_warnings[:5]]

    return CitizenWill(
        citizen_name=citizen.name,
        citizen_pubkey=citizen.pubkey,
        citizen_type=citizen.citizen_type,
        current_task_id=current_task_id,
        current_task_type=current_task_type,
        xp=dict(citizen.skill_tree.xp),
        active_contracts=active_contracts,
        warnings=warnings,
        uptime_seconds=time.time() - citizen.start_time if citizen.start_time else 0,
    )
