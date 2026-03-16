"""Learning Loop — analyze episodes and improve robot behavior.

The self-improvement cycle:
1. RECORD: Every operation produces an episode
2. ANALYZE: Batch-analyze episodes for patterns
3. LEARN: Update skill parameters, strategies, avoidance zones
4. VERIFY: Test improvements on next episodes

This module provides the analysis and learning logic. Claude (or a local LLM)
can inspect episodes via get_episode_summary() and suggest improvements.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from .episode_recorder import list_episodes, load_episode, EPISODES_DIR


@dataclass
class LearningInsight:
    """An insight extracted from episode analysis."""
    insight_type: str    # "success_pattern", "failure_pattern", "parameter_suggestion", "skill_gap"
    description: str
    confidence: float = 0.5
    affected_task: str = ""
    suggested_action: str = ""
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.insight_type,
            "description": self.description,
            "confidence": self.confidence,
            "task": self.affected_task,
            "action": self.suggested_action,
        }


def analyze_recent_episodes(count: int = 20) -> list[LearningInsight]:
    """Analyze recent episodes and extract learning insights."""
    episodes = list_episodes(count)
    insights = []

    if not episodes:
        return [LearningInsight(
            insight_type="no_data",
            description="No episodes recorded yet. Perform some tasks to generate training data.",
        )]

    # Group by task type
    by_task: dict[str, list[dict]] = {}
    for ep in episodes:
        task = ep.get("task", "unknown")
        by_task.setdefault(task, []).append(ep)

    for task, eps in by_task.items():
        successes = [e for e in eps if e.get("success")]
        failures = [e for e in eps if not e.get("success")]
        total = len(eps)

        if total == 0:
            continue

        success_rate = len(successes) / total

        # Insight: task success rate
        if success_rate < 0.5 and total >= 3:
            insights.append(LearningInsight(
                insight_type="failure_pattern",
                description=f"{task}: only {success_rate:.0%} success rate ({len(successes)}/{total})",
                confidence=min(1.0, total / 10.0),
                affected_task=task,
                suggested_action="analyze_failures",
                data={"success_rate": success_rate, "total": total},
            ))
        elif success_rate > 0.8 and total >= 5:
            insights.append(LearningInsight(
                insight_type="success_pattern",
                description=f"{task}: strong performance at {success_rate:.0%} ({len(successes)}/{total})",
                confidence=min(1.0, total / 10.0),
                affected_task=task,
            ))

        # Insight: high current / thermal issues
        high_current_eps = [e for e in eps if e.get("avg_current_ma", 0) > 300]
        if high_current_eps:
            insights.append(LearningInsight(
                insight_type="parameter_suggestion",
                description=f"{task}: {len(high_current_eps)}/{total} episodes had high current (>300mA)",
                affected_task=task,
                suggested_action="reduce_speed_or_torque",
                data={"high_current_count": len(high_current_eps)},
            ))

        hot_eps = [e for e in eps if e.get("max_temperature", 0) > 50]
        if hot_eps:
            insights.append(LearningInsight(
                insight_type="parameter_suggestion",
                description=f"{task}: {len(hot_eps)}/{total} episodes exceeded 50°C",
                affected_task=task,
                suggested_action="add_cooling_pauses",
            ))

        # Insight: high position error in failures
        failed_errors = [e.get("position_error_mean", 0) for e in failures if e.get("position_error_mean")]
        success_errors = [e.get("position_error_mean", 0) for e in successes if e.get("position_error_mean")]
        if failed_errors and success_errors:
            avg_fail_error = sum(failed_errors) / len(failed_errors)
            avg_success_error = sum(success_errors) / len(success_errors)
            if avg_fail_error > avg_success_error * 1.5:
                insights.append(LearningInsight(
                    insight_type="failure_pattern",
                    description=f"{task}: failed episodes have {avg_fail_error:.0f} avg position error vs {avg_success_error:.0f} for successes",
                    affected_task=task,
                    suggested_action="improve_accuracy",
                ))

    # Insight: skill gaps (tasks never attempted)
    known_tasks = {"basic_gesture/wave", "basic_gesture/nod", "basic_gesture/grip",
                   "pick_and_place", "color_detection", "color_sorting"}
    attempted = set(by_task.keys())
    unattempted = known_tasks - attempted
    if unattempted:
        insights.append(LearningInsight(
            insight_type="skill_gap",
            description=f"Never attempted: {', '.join(unattempted)}",
            suggested_action="practice_untried_tasks",
        ))

    return insights


def generate_improvement_plan(insights: list[LearningInsight]) -> list[dict]:
    """From insights, generate a concrete improvement plan."""
    plan = []

    for insight in insights:
        if insight.insight_type == "failure_pattern" and insight.suggested_action == "analyze_failures":
            plan.append({
                "action": "review_failed_episodes",
                "task": insight.affected_task,
                "description": f"Load failed episodes for {insight.affected_task} and identify common failure mode",
            })
        elif insight.suggested_action == "reduce_speed_or_torque":
            plan.append({
                "action": "adjust_parameters",
                "task": insight.affected_task,
                "description": f"Reduce approach speed by 20% for {insight.affected_task} to lower current draw",
                "params": {"speed_reduction": 0.2},
            })
        elif insight.suggested_action == "add_cooling_pauses":
            plan.append({
                "action": "add_rest_period",
                "task": insight.affected_task,
                "description": f"Add 2s cooling pause between {insight.affected_task} episodes",
                "params": {"pause_s": 2.0},
            })
        elif insight.insight_type == "skill_gap":
            plan.append({
                "action": "practice",
                "description": insight.description,
            })

    return plan


def get_learning_report() -> str:
    """Generate a natural language learning report for Claude/user."""
    insights = analyze_recent_episodes(50)
    plan = generate_improvement_plan(insights)

    parts = ["=== Learning Report ===\n"]

    # Episode stats
    episodes = list_episodes(50)
    total = len(episodes)
    successes = sum(1 for e in episodes if e.get("success"))
    parts.append(f"Total episodes: {total}")
    parts.append(f"Overall success rate: {successes}/{total} ({successes/total:.0%})" if total > 0 else "No episodes yet")

    # Insights
    parts.append(f"\nInsights ({len(insights)}):")
    for i in insights:
        marker = "✓" if i.insight_type == "success_pattern" else "⚠" if i.insight_type == "failure_pattern" else "?"
        parts.append(f"  {marker} {i.description}")

    # Plan
    if plan:
        parts.append(f"\nImprovement Plan ({len(plan)} actions):")
        for p in plan:
            parts.append(f"  → {p['description']}")

    return "\n".join(parts)
