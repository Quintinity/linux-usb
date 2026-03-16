"""Consciousness Stream — natural language state narration.

Template-based narration of citizen state (no LLM required on Pi).
Optional Claude API narration on Surface for richer output.
"""

from __future__ import annotations

import time


_TEMPLATES = {
    "idle": "Idle. Health {health:.0%}. {neighbor_count} neighbors online. Mood: {mood}.",
    "teleop": "Streaming teleop at {fps:.0f} FPS. {frames} frames sent. Health {health:.0%}.",
    "executing": "Executing {task}. {motor} load at {load:.0f}%. Confidence: {confidence:.0%}.",
    "bidding": "Evaluating task {task}. Skill level {skill}. Current load {load:.0%}.",
    "calibrating": "Calibrating point {point}/{total}. Reprojection error: {error:.1f}px.",
    "recording": "Recording episode. {frames} frames captured. Task: {task_label}.",
    "degraded": "Warning: {warning}. Reducing duty cycle to {mitigation:.0%}.",
    "emergency_stop": "EMERGENCY STOP. All torque disabled. Waiting for governor.",
    "offline": "Going offline. Broadcasting will. Uptime: {uptime:.0f}s.",
}

# Rate limit: max 1 narration per 5 seconds
_MIN_INTERVAL = 5.0
_last_narration_time: float = 0.0


def narrate(citizen) -> str | None:
    """Generate a consciousness narration for a citizen.

    Returns a natural language string, or None if rate-limited.
    """
    global _last_narration_time
    now = time.time()
    if now - _last_narration_time < _MIN_INTERVAL:
        return None
    _last_narration_time = now

    state = citizen.state
    template = _TEMPLATES.get(state, _TEMPLATES["idle"])

    # Build context dict
    ctx = {
        "health": citizen.health,
        "neighbor_count": len(citizen.neighbors),
        "mood": citizen.emotional_state.mood if hasattr(citizen, 'emotional_state') else "steady",
        "confidence": citizen.emotional_state.confidence if hasattr(citizen, 'emotional_state') else 0.5,
        "load": 0.0,
        "fps": 0.0,
        "frames": 0,
        "task": "",
        "motor": "",
        "skill": 0,
        "warning": "",
        "mitigation": 1.0,
        "uptime": now - citizen.start_time if citizen.start_time else 0,
        "point": 0,
        "total": 10,
        "error": 0.0,
        "task_label": "",
    }

    # Fill in state-specific context
    if hasattr(citizen, '_frames_sent'):
        ctx["frames"] = citizen._frames_sent
    if hasattr(citizen, 'teleop_fps'):
        ctx["fps"] = citizen.teleop_fps
    if hasattr(citizen, '_current_task_type') and citizen._current_task_type:
        ctx["task"] = citizen._current_task_type

    if citizen.mycelium.active_warnings:
        w = citizen.mycelium.active_warnings[0]
        ctx["warning"] = w.detail
        ctx["mitigation"] = citizen.mycelium.current_mitigation_factor()

    try:
        return template.format(**ctx)
    except (KeyError, ValueError):
        return f"{state}. Health {citizen.health:.0%}."


def narrate_to_report(citizen) -> dict | None:
    """Generate a consciousness REPORT body.

    Returns dict for REPORT message, or None if rate-limited.
    """
    text = narrate(citizen)
    if text is None:
        return None
    return {
        "type": "consciousness",
        "citizen": citizen.name,
        "narration": text,
        "state": citizen.state,
        "timestamp": time.time(),
    }
