"""Thin wrapper around lerobot.policies.smolvla for in-citizenry use.

Not citizenry-aware. Knows nothing about the marketplace, the Constitution,
or any Citizen. Pure: load model, take observation, return action chunk.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _load_smolvla_policy(model_id: str, device: str = "cuda"):
    """Lazy import so tests can monkeypatch this.

    Defers the heavy lerobot import until the runner is actually loaded —
    means unit tests that patch this function never touch torch/lerobot.
    """
    # lerobot 0.4.x flattened the package — policies live at lerobot.policies.*.
    # Earlier versions / some forks still use lerobot.common.policies.*.
    try:
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    except ModuleNotFoundError:
        from lerobot.common.policies.smolvla.modeling_smolvla import SmolVLAPolicy  # legacy fallback
    return SmolVLAPolicy.from_pretrained(model_id).to(device).eval()


class SmolVLARunner:
    def __init__(
        self,
        model_id: str = "lerobot/smolvla_base",
        device: str = "cuda",
    ):
        self.model_id = model_id
        self.device = device
        self._policy = None

    def load(self) -> None:
        self._policy = _load_smolvla_policy(self.model_id, self.device)

    def act(self, observation: dict[str, Any]) -> np.ndarray:
        """Run one forward pass; return an action chunk of shape (T, action_dim).

        Caller is responsible for converting servo ticks <-> model action units.
        SmolVLA-specific scaling lives in this runner; PolicyCitizen stays
        ignorant of it.
        """
        if self._policy is None:
            raise RuntimeError("SmolVLARunner not loaded — call .load() first")
        return self._policy.select_action(observation)
