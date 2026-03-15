"""Capability Composition — discover composite capabilities.

When citizens with complementary capabilities are in the same neighborhood,
composite capabilities emerge automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CompositionRule:
    """A rule that defines how capabilities combine."""

    required_capabilities: list[str]
    composite_capability: str
    description: str = ""
    min_citizens: int = 1  # Can require capabilities from different citizens

    def matches(self, available_capabilities: set[str]) -> bool:
        """Check if all required capabilities are available."""
        return all(cap in available_capabilities for cap in self.required_capabilities)


# Default composition rules
DEFAULT_RULES = [
    CompositionRule(
        required_capabilities=["6dof_arm", "video_stream"],
        composite_capability="visual_pick_and_place",
        description="Visual guided manipulation — arm + camera",
        min_citizens=2,
    ),
    CompositionRule(
        required_capabilities=["6dof_arm", "color_detection"],
        composite_capability="color_sorting",
        description="Sort objects by color — arm + color-aware camera",
        min_citizens=2,
    ),
    CompositionRule(
        required_capabilities=["6dof_arm", "frame_capture"],
        composite_capability="visual_inspection",
        description="Visual workspace inspection — arm positions + camera frames",
        min_citizens=2,
    ),
]


class CompositionEngine:
    """Discovers composite capabilities from a set of citizen capabilities."""

    def __init__(self, rules: list[CompositionRule] | None = None):
        self.rules = rules or list(DEFAULT_RULES)

    def add_rule(self, rule: CompositionRule) -> None:
        self.rules.append(rule)

    def discover(
        self,
        citizen_capabilities: dict[str, list[str]],
    ) -> list[CompositionRule]:
        """Given a map of citizen_pubkey → capabilities, find all composite capabilities.

        Args:
            citizen_capabilities: Map from citizen pubkey to their capability list.

        Returns:
            List of matching CompositionRules.
        """
        # Collect all capabilities across all citizens
        all_caps: set[str] = set()
        for caps in citizen_capabilities.values():
            all_caps.update(caps)

        matches = []
        for rule in self.rules:
            if rule.matches(all_caps):
                # Check min_citizens: capabilities must come from enough citizens
                if rule.min_citizens > 1:
                    # Verify the required caps come from at least min_citizens different citizens
                    contributing = set()
                    for pubkey, caps in citizen_capabilities.items():
                        for req_cap in rule.required_capabilities:
                            if req_cap in caps:
                                contributing.add(pubkey)
                    if len(contributing) >= rule.min_citizens:
                        matches.append(rule)
                else:
                    matches.append(rule)
        return matches

    def discover_capabilities(
        self,
        citizen_capabilities: dict[str, list[str]],
    ) -> list[str]:
        """Convenience: return just the composite capability names."""
        return [r.composite_capability for r in self.discover(citizen_capabilities)]
