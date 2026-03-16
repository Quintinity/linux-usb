"""Dialogue — bidirectional natural language conversation between citizens.

Governor can ask citizens questions. Citizens can compose natural language
responses from their internal state (soul, memory, pain, growth, etc.).
Citizens can also proactively request things from the governor.

All dialogue uses existing PROPOSE/REPORT messages — no new protocol types.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DialogueMessage:
    """A message in a conversation between citizens."""
    sender: str
    recipient: str
    text: str
    message_type: str = "dialogue"  # "dialogue", "question", "request", "status_report"
    timestamp: float = field(default_factory=time.time)

    def to_body(self) -> dict:
        return {
            "task": "dialogue",
            "text": self.text,
            "dialogue_type": self.message_type,
            "timestamp": self.timestamp,
        }

    def to_report_body(self) -> dict:
        return {
            "type": "dialogue_response",
            "text": self.text,
            "dialogue_type": self.message_type,
            "timestamp": self.timestamp,
        }


# ── Citizen Self-Report Composer ──────────────────────────────────────────────

class CitizenVoice:
    """Composes natural language responses from citizen internal state.

    The citizen's "voice" — how it describes itself when asked.
    """

    def __init__(self, citizen):
        self.citizen = citizen

    def how_are_you(self) -> str:
        """Compose a natural language status report."""
        c = self.citizen
        parts = []

        # Emotional state / mood
        mood = c.emotional_state.mood if hasattr(c, 'emotional_state') else "steady"
        fatigue = c.emotional_state.fatigue if hasattr(c, 'emotional_state') else 0

        if mood == "exhausted":
            parts.append("I'm exhausted.")
        elif mood == "tired":
            parts.append("I'm getting tired.")
        elif mood == "focused":
            parts.append("I'm feeling focused and ready.")
        elif mood == "uncertain":
            parts.append("I'm not very confident right now.")
        elif mood == "curious":
            parts.append("I'm curious — looking for new things to try.")
        elif mood == "energized":
            parts.append("I'm feeling great — energized and ready to work.")
        else:
            parts.append("I'm doing okay.")

        # Growth stage
        if hasattr(c, 'growth_tracker'):
            stage = c.growth_tracker.get_stage().name.lower()
            tasks = c.growth_tracker.maturation.total_tasks
            rate = c.growth_tracker.maturation.success_rate
            parts.append(f"I'm at the {stage} stage with {tasks} tasks completed ({rate:.0%} success rate).")

        # Pain
        if hasattr(c, 'pain_memory'):
            zones = c.pain_memory.active_zones()
            events = c.pain_memory.total_pain_events()
            if events > 0:
                parts.append(f"I've experienced {events} pain events and have {zones} avoidance zones.")
            if c.pain_memory.sensitivity > 1.2:
                parts.append("I'm a bit sensitized — being extra careful.")

        # Performance
        if hasattr(c, 'performance'):
            for skill, records in c.performance.records.items():
                rate = c.performance.success_rate(skill)
                trend = c.performance.trend(skill)
                if c.performance.is_regressing(skill):
                    parts.append(f"Worried about {skill} — success rate is dropping ({rate:.0%}).")
                elif rate > 0.85:
                    parts.append(f"Feeling confident about {skill} ({rate:.0%} success).")

        # Metabolism
        if hasattr(c, 'metabolism_tracker'):
            state = c.metabolism_tracker.state
            if state.brownout_stage.value != "normal":
                parts.append(f"Power warning: {state.brownout_stage.value}. Voltage is low.")

        # Memory
        if hasattr(c, 'memory'):
            stats = c.memory.stats()
            if stats["unconsolidated"] > 20:
                parts.append(f"I have {stats['unconsolidated']} unconsolidated memories — could use some rest to process them.")

        # Sleep
        if hasattr(c, 'sleep_engine'):
            hrs = (time.time() - c.sleep_engine.last_sleep_time) / 3600
            if hrs > 4:
                parts.append(f"I haven't slept in {hrs:.1f} hours.")

        # Soul personality
        if hasattr(c, 'soul'):
            p = c.soul.personality
            if p.neuroticism > 0.7:
                parts.append("I've been feeling anxious about faults lately.")
            if p.exploration_drive > 0.7:
                parts.append("I'd love to try something new.")

        return " ".join(parts) if parts else "All systems nominal."

    def what_do_you_remember(self, topic: str = "") -> str:
        """Report what the citizen remembers about a topic."""
        c = self.citizen
        if not hasattr(c, 'memory'):
            return "I don't have a memory system yet."

        parts = []

        if topic:
            # Search semantic memory
            facts = c.memory.query_facts(subject=topic)
            if facts:
                for f in facts[:5]:
                    parts.append(f"{f.subject} {f.relation} {f.object} (confidence: {f.confidence:.0%})")

            # Search episodic memory
            episodes = [e for e in c.memory.recent_episodes(50) if topic.lower() in e.what.lower()]
            if episodes:
                parts.append(f"I remember {len(episodes)} episodes involving {topic}.")
                latest = episodes[-1]
                parts.append(f"Most recent: {latest.what} — {latest.outcome}")

            # Search procedural memory
            proc = c.memory.recall_procedure(topic)
            if proc:
                parts.append(f"I know how to {proc.skill_name} in context '{proc.context}' with {proc.success_rate:.0%} success rate.")
        else:
            stats = c.memory.stats()
            parts.append(f"I have {stats['episodes']} memories, know {stats['facts']} facts, and {stats['procedures']} procedures.")

        return " ".join(parts) if parts else f"I don't know anything about {topic} yet."

    def what_hurts(self) -> str:
        """Report pain state."""
        c = self.citizen
        if not hasattr(c, 'pain_memory'):
            return "No pain awareness."

        events = c.pain_memory.total_pain_events()
        zones = c.pain_memory.active_zones()

        if events == 0:
            return "Nothing hurts. No pain events recorded."

        parts = [f"I've had {events} pain events."]
        if zones > 0:
            parts.append(f"I have {zones} active avoidance zones.")
        if c.pain_memory.sensitivity > 1.5:
            parts.append("I'm very sensitized right now — minor issues feel worse.")

        # Most recent pain
        if c.pain_memory.events:
            last = c.pain_memory.events[-1]
            age = time.time() - last.timestamp
            parts.append(f"Last pain: {last.pain_type} in {last.source} ({age:.0f}s ago, intensity {last.intensity:.1f}).")

        return " ".join(parts)

    def what_are_your_goals(self) -> str:
        """Report current goals."""
        c = self.citizen
        if not hasattr(c, 'soul'):
            return "No goal system."

        goals = c.soul.goals.get_active()
        parts = [f"I have {len(goals)} active goals:"]
        for g in goals[:5]:
            tier = ["SURVIVAL", "CONSTITUTIONAL", "ASSIGNED", "SELF-IMPROVEMENT", "CURIOSITY"][g.priority]
            parts.append(f"  [{tier}] {g.description}")
        return "\n".join(parts)


# ── Proactive Requests ────────────────────────────────────────────────────────

class CitizenNeeds:
    """Detects when a citizen needs something and composes a request."""

    def __init__(self, citizen):
        self.citizen = citizen
        self._last_request_time: float = 0
        self._request_cooldown: float = 60.0  # Max 1 request per minute

    def check_needs(self) -> DialogueMessage | None:
        """Check if the citizen needs to request something from the governor.

        Returns a DialogueMessage if there's a need, None otherwise.
        """
        if time.time() - self._last_request_time < self._request_cooldown:
            return None

        c = self.citizen
        request = self._check_needs_internal(c)
        if request:
            self._last_request_time = time.time()
        return request

    def _check_needs_internal(self, c) -> DialogueMessage | None:
        # Priority 1: Sleep needed
        if hasattr(c, 'sleep_engine') and hasattr(c, 'emotional_state'):
            pressure = c.sleep_engine.compute_pressure(
                uptime_hours=(time.time() - c.start_time) / 3600 if c.start_time else 0,
                fatigue=c.emotional_state.fatigue,
                unconsolidated=c.memory.unconsolidated_count() if hasattr(c, 'memory') else 0,
            )
            if pressure.should_sleep:
                return DialogueMessage(
                    sender=c.name, recipient="governor",
                    text=f"Governor, I need to sleep. Sleep pressure is {pressure.pressure:.0%}. "
                         f"I have {c.memory.unconsolidated_count() if hasattr(c, 'memory') else '?'} "
                         f"unconsolidated memories to process.",
                    message_type="request",
                )

        # Priority 2: Performance regression
        if hasattr(c, 'performance'):
            for skill in list(c.performance.records.keys()):
                if c.performance.is_regressing(skill):
                    rate = c.performance.success_rate(skill)
                    return DialogueMessage(
                        sender=c.name, recipient="governor",
                        text=f"Governor, my {skill} success rate has dropped to {rate:.0%}. "
                             f"Can I switch to practice mode to recover?",
                        message_type="request",
                    )

        # Priority 3: Power issues
        if hasattr(c, 'metabolism_tracker'):
            if c.metabolism_tracker.state.brownout_stage.value in ("caution", "critical"):
                return DialogueMessage(
                    sender=c.name, recipient="governor",
                    text=f"Governor, I'm experiencing power issues "
                         f"({c.metabolism_tracker.state.brownout_stage.value}). "
                         f"Can you reduce the number of simultaneous tasks?",
                    message_type="request",
                )

        # Priority 4: Calibration stale
        if hasattr(c, 'sleep_engine'):
            hrs_since_sleep = (time.time() - c.sleep_engine.last_sleep_time) / 3600
            if hrs_since_sleep > 6:
                return DialogueMessage(
                    sender=c.name, recipient="governor",
                    text=f"Governor, I haven't had maintenance in {hrs_since_sleep:.1f} hours. "
                         f"My calibration might be drifting.",
                    message_type="request",
                )

        return None


# ── Question Parser ───────────────────────────────────────────────────────────

def parse_question(text: str) -> str:
    """Parse a governor's question to determine what to respond with."""
    text = text.lower().strip()

    if any(w in text for w in ("how are you", "how do you feel", "status", "how's it going")):
        return "how_are_you"
    if any(w in text for w in ("remember", "recall", "know about", "memory")):
        return "what_do_you_remember"
    if any(w in text for w in ("hurt", "pain", "damage", "broken")):
        return "what_hurts"
    if any(w in text for w in ("goal", "want", "purpose", "trying to")):
        return "what_are_your_goals"
    if any(w in text for w in ("specializ", "good at", "best at", "expert")):
        return "specialization"
    if any(w in text for w in ("tired", "sleep", "rest", "fatigue")):
        return "sleep_status"
    if any(w in text for w in ("growth", "stage", "maturity", "level")):
        return "growth_status"

    return "how_are_you"  # Default fallback


def compose_response(citizen, question_type: str, topic: str = "") -> str:
    """Compose a response to a governor's question."""
    voice = CitizenVoice(citizen)

    if question_type == "how_are_you":
        return voice.how_are_you()
    elif question_type == "what_do_you_remember":
        return voice.what_do_you_remember(topic)
    elif question_type == "what_hurts":
        return voice.what_hurts()
    elif question_type == "what_are_your_goals":
        return voice.what_are_your_goals()
    elif question_type == "specialization":
        if hasattr(citizen, 'growth_tracker'):
            tops = citizen.growth_tracker.specialization.top_specializations()
            if tops:
                return f"I'm best at: {', '.join(f'{t} ({s:.0%})' for t, s in tops)}"
        return "I haven't specialized yet."
    elif question_type == "sleep_status":
        if hasattr(citizen, 'sleep_engine'):
            stats = citizen.sleep_engine.stats()
            return f"Sleep status: {'sleeping' if stats['sleeping'] else 'awake'}. " \
                   f"{stats['hours_since_sleep']}h since last sleep. {stats['total_sleeps']} total sleeps."
        return "No sleep system."
    elif question_type == "growth_status":
        if hasattr(citizen, 'growth_tracker'):
            s = citizen.growth_tracker.stats()
            return f"Stage: {s['stage']}. {s['total_tasks']} tasks, {s['success_rate']:.0%} success. " \
                   f"Breadth: {s['breadth']:.0%}."
        return "No growth tracking."

    return voice.how_are_you()
