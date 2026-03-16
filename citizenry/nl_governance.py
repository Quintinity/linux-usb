"""Natural Language Governance — translate human intent to formal policy.

The governor's aide: interprets natural language commands and translates
them into formal GOVERN messages (law updates, task creation, policy changes).

Works without an LLM by pattern-matching common governance phrases.
Can optionally use Claude API for complex commands.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GovernanceAction:
    """A parsed governance action from natural language."""
    action_type: str  # "law_update", "task_create", "emergency_stop", "policy_change"
    params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "params": self.params,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }


# ── Pattern-based NL parsing (no LLM needed) ─────────────────────────────────

# Torque/force patterns
_GENTLE_PATTERNS = [
    (r"(?:be\s+)?gentle", "reduce_torque", 0.7),
    (r"reduce\s+(?:torque|force|strength)", "reduce_torque", None),
    (r"(?:be\s+)?careful", "reduce_torque", 0.8),
    (r"soft(?:er)?(?:\s+touch)?", "reduce_torque", 0.7),
    (r"delicate", "reduce_torque", 0.6),
]

# Speed patterns
_SPEED_PATTERNS = [
    (r"slow(?:er)?\s*(?:down)?", "reduce_speed", None),
    (r"fast(?:er)?", "increase_speed", None),
    (r"speed\s+up", "increase_speed", None),
    (r"full\s+speed", "increase_speed", 1.0),
    (r"half\s+speed", "reduce_speed", 0.5),
]

# Stop patterns
_STOP_PATTERNS = [
    (r"stop(?:\s+(?:everything|all|now))?", "emergency_stop", None),
    (r"halt", "emergency_stop", None),
    (r"freeze", "emergency_stop", None),
    (r"e[\-\s]?stop", "emergency_stop", None),
    (r"kill", "emergency_stop", None),
]

# Task patterns
_TASK_PATTERNS = [
    (r"wave(?:\s+hello)?", "task_create", {"type": "basic_gesture", "params": {"gesture": "wave"}}),
    (r"say\s+hi", "task_create", {"type": "basic_gesture", "params": {"gesture": "wave"}}),
    (r"nod", "task_create", {"type": "basic_gesture", "params": {"gesture": "nod"}}),
    (r"grip|grab|grasp", "task_create", {"type": "basic_gesture", "params": {"gesture": "grip"}}),
    (r"go\s+home|home\s+position", "task_create", {"type": "basic_movement", "params": {}}),
    (r"sort(?:\s+(?:the\s+)?(?:blocks|objects|colors))?", "task_create", {"type": "color_sorting", "params": {}}),
    (r"(?:what\s+do\s+you\s+)?see|look|detect(?:\s+colors)?", "task_create", {"type": "color_detection", "params": {}}),
    (r"take\s+(?:a\s+)?(?:photo|picture|snapshot|frame)", "task_create", {"type": "frame_capture", "params": {}}),
    (r"pick(?:\s+(?:up|and\s+place))?", "task_create", {"type": "pick_and_place", "params": {}}),
]

# Law patterns
_LAW_PATTERNS = [
    (r"(?:set\s+)?(?:teleop\s+)?fps\s+(?:to\s+)?(\d+)", "law_update", lambda m: {"law_id": "teleop_max_fps", "params": {"fps": int(m.group(1))}}),
    (r"(?:set\s+)?idle\s+timeout\s+(?:to\s+)?(\d+)", "law_update", lambda m: {"law_id": "idle_timeout", "params": {"seconds": int(m.group(1))}}),
    (r"(?:set\s+)?heartbeat\s+(?:to\s+)?(\d+(?:\.\d+)?)", "law_update", lambda m: {"law_id": "heartbeat_interval", "params": {"seconds": float(m.group(1))}}),
]

# Percentage extraction
_PCT_RE = re.compile(r"(\d+)\s*%")
_FRACTION_RE = re.compile(r"by\s+(\d+(?:\.\d+)?)")


def _extract_factor(text: str, default: float) -> float:
    """Extract a scaling factor from text like '30%' or 'by 0.3'."""
    m = _PCT_RE.search(text)
    if m:
        pct = int(m.group(1))
        return 1.0 - pct / 100.0 if pct <= 100 else default

    m = _FRACTION_RE.search(text)
    if m:
        val = float(m.group(1))
        if val > 1:
            return 1.0 - val / 100.0
        return 1.0 - val

    return default


def parse_command(text: str) -> GovernanceAction | None:
    """Parse a natural language command into a governance action.

    Returns None if the command is not recognized.

    Examples:
        "be gentle" → reduce torque to 70%
        "slow down" → reduce FPS by 50%
        "stop" → emergency stop
        "wave hello" → create wave gesture task
        "sort the blocks" → create color_sorting task
        "set fps to 30" → update teleop_max_fps law
        "reduce torque by 30%" → reduce max_torque by 30%
    """
    text = text.strip().lower()

    # Emergency stop (highest priority)
    for pattern, action, _ in _STOP_PATTERNS:
        if re.search(pattern, text):
            return GovernanceAction(
                action_type="emergency_stop",
                confidence=1.0,
                explanation=f"Emergency stop triggered by: '{text}'",
            )

    # Law updates with specific values
    for pattern, action, extractor in _LAW_PATTERNS:
        m = re.search(pattern, text)
        if m:
            params = extractor(m) if callable(extractor) else extractor
            return GovernanceAction(
                action_type="law_update",
                params=params,
                confidence=0.9,
                explanation=f"Law update: {params}",
            )

    # Torque adjustments
    for pattern, action, default_factor in _GENTLE_PATTERNS:
        if re.search(pattern, text):
            factor = _extract_factor(text, default_factor or 0.7)
            max_torque = int(500 * factor)  # Default max is 500
            return GovernanceAction(
                action_type="law_update",
                params={
                    "law_id": "servo_limits",
                    "params": {"max_torque": max_torque},
                },
                confidence=0.85,
                explanation=f"Reduce torque to {factor:.0%} (max_torque={max_torque})",
            )

    # Speed adjustments
    for pattern, action, default_factor in _SPEED_PATTERNS:
        if re.search(pattern, text):
            if action == "reduce_speed":
                factor = _extract_factor(text, default_factor or 0.5)
                fps = max(5, int(60 * factor))
            else:
                fps = 60
            return GovernanceAction(
                action_type="law_update",
                params={"law_id": "teleop_max_fps", "params": {"fps": fps}},
                confidence=0.85,
                explanation=f"Speed → {fps} FPS",
            )

    # Task creation
    for pattern, action, task_info in _TASK_PATTERNS:
        if re.search(pattern, text):
            # Check for target color
            color_match = re.search(r"(red|green|blue|yellow)", text)
            params = dict(task_info.get("params", {}))
            if color_match:
                params["target_color"] = color_match.group(1)

            return GovernanceAction(
                action_type="task_create",
                params={
                    "type": task_info["type"],
                    "params": params,
                    "required_capabilities": _caps_for_task(task_info["type"]),
                    "required_skills": _skills_for_task(task_info["type"]),
                },
                confidence=0.8,
                explanation=f"Create task: {task_info['type']}",
            )

    return None


def _caps_for_task(task_type: str) -> list[str]:
    """Required capabilities for a task type."""
    return {
        "basic_gesture": ["6dof_arm"],
        "basic_movement": ["6dof_arm"],
        "pick_and_place": ["6dof_arm"],
        "color_detection": ["color_detection"],
        "color_sorting": ["6dof_arm", "color_detection"],
        "frame_capture": ["frame_capture"],
        "visual_inspection": ["frame_capture"],
    }.get(task_type, [])


def _skills_for_task(task_type: str) -> list[str]:
    """Required skills for a task type."""
    return {
        "basic_gesture": ["basic_gesture"],
        "basic_movement": ["basic_movement"],
        "pick_and_place": ["pick_and_place"],
        "color_sorting": [],
        "color_detection": [],
        "frame_capture": [],
    }.get(task_type, [])


# ── Governor integration ──────────────────────────────────────────────────────

class GovernorAide:
    """Processes natural language commands for the governor.

    Usage:
        aide = GovernorAide(surface_citizen)
        result = aide.execute("wave hello")
        result = aide.execute("be gentle")
        result = aide.execute("sort the blocks by color")
    """

    def __init__(self, governor):
        self.governor = governor
        self.history: list[tuple[str, GovernanceAction | None]] = []

    def execute(self, command: str) -> GovernanceAction | None:
        """Parse and execute a natural language command."""
        action = parse_command(command)
        self.history.append((command, action))

        if action is None:
            return None

        if action.action_type == "emergency_stop":
            self._do_emergency_stop()
        elif action.action_type == "law_update":
            self._do_law_update(action.params)
        elif action.action_type == "task_create":
            self._do_task_create(action.params)

        return action

    def _do_emergency_stop(self):
        """Send emergency stop to all citizens."""
        for pubkey, neighbor in self.governor.neighbors.items():
            self.governor.send_govern(
                pubkey,
                {"type": "emergency_stop"},
                neighbor.addr,
            )

    def _do_law_update(self, params: dict):
        """Update a law and broadcast to all citizens."""
        law_id = params.get("law_id", "")
        law_params = params.get("params", {})
        self.governor.update_law(law_id, law_params)

    def _do_task_create(self, params: dict):
        """Create a task through the marketplace or coordinator for composite tasks."""
        task_type = params.get("type", "")

        # Composite tasks go through the coordinator
        if task_type in ("color_sorting",) and hasattr(self.governor, '_coordinator'):
            import asyncio
            asyncio.get_event_loop().create_task(
                self.governor._coordinator.execute_color_sorting()
            )
            return

        if task_type == "pick_and_place" and hasattr(self.governor, '_coordinator'):
            target_color = params.get("params", {}).get("target_color")
            import asyncio
            asyncio.get_event_loop().create_task(
                self.governor._coordinator.execute_visual_pick_and_place(target_color=target_color)
            )
            return

        # Simple tasks go directly to marketplace
        self.governor.create_task(
            task_type=task_type,
            params=params.get("params", {}),
            priority=0.7,
            required_capabilities=params.get("required_capabilities", []),
            required_skills=params.get("required_skills", []),
        )
