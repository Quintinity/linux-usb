"""Federated Learning Foundations — model weight sharing format.

Defines the data structures and protocol for sharing learned model weights
across citizens without sharing raw sensor data. This is the foundation
for fleet-wide learning in v3.0+.

No actual training happens here — this defines the envelope format,
announcement protocol, and weight registry so that when training
infrastructure is added later, the protocol is ready.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelWeightEnvelope:
    """A package of model weights for sharing across citizens.

    Weights are opaque blobs — the citizenry protocol transports them,
    citizens with matching model_type can apply them.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    model_type: str = ""        # e.g., "grasp_policy", "sort_policy"
    version: int = 1
    source_citizen: str = ""    # pubkey of the citizen that trained this
    source_name: str = ""
    task_type: str = ""         # Task this model was trained on
    metrics: dict[str, float] = field(default_factory=dict)  # e.g., {"accuracy": 0.95, "loss": 0.02}
    weight_format: str = "numpy_dict"  # "numpy_dict", "safetensors", "onnx"
    weight_size_bytes: int = 0
    # Weights themselves are NOT included in the envelope —
    # they're transferred via a separate data channel (file share, HTTP, etc.)
    weight_path: str = ""       # Path or URL to the actual weights
    created_at: float = field(default_factory=time.time)
    episodes_trained: int = 0
    citizen_type: str = ""      # Only citizens of matching type should apply

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_type": self.model_type,
            "version": self.version,
            "source_citizen": self.source_citizen,
            "source_name": self.source_name,
            "task_type": self.task_type,
            "metrics": self.metrics,
            "weight_format": self.weight_format,
            "weight_size_bytes": self.weight_size_bytes,
            "weight_path": self.weight_path,
            "created_at": self.created_at,
            "episodes_trained": self.episodes_trained,
            "citizen_type": self.citizen_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ModelWeightEnvelope:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def to_announce_body(self) -> dict:
        """Convert to a REPORT message body for weight announcement."""
        return {
            "type": "model_weights_available",
            "envelope": self.to_dict(),
        }


@dataclass
class WeightRequest:
    """A request from a citizen to download model weights."""
    requester_pubkey: str
    envelope_id: str
    timestamp: float = field(default_factory=time.time)

    def to_propose_body(self) -> dict:
        return {
            "task": "weight_transfer",
            "envelope_id": self.envelope_id,
            "requester": self.requester_pubkey,
        }


class WeightRegistry:
    """Registry of available model weights across the fleet.

    The governor maintains this registry. Citizens announce new weights
    via REPORT messages, and other citizens can request them.
    """

    def __init__(self):
        self.weights: dict[str, ModelWeightEnvelope] = {}  # id → envelope
        self.by_type: dict[str, list[str]] = {}  # model_type → [ids]

    def register(self, envelope: ModelWeightEnvelope) -> None:
        """Register new model weights."""
        self.weights[envelope.id] = envelope
        self.by_type.setdefault(envelope.model_type, []).append(envelope.id)

    def get_latest(self, model_type: str) -> ModelWeightEnvelope | None:
        """Get the latest version of a model type."""
        ids = self.by_type.get(model_type, [])
        if not ids:
            return None
        candidates = [self.weights[id] for id in ids if id in self.weights]
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.version)

    def get_best(self, model_type: str, metric: str = "accuracy") -> ModelWeightEnvelope | None:
        """Get the best-performing model of a type by metric."""
        ids = self.by_type.get(model_type, [])
        candidates = [self.weights[id] for id in ids if id in self.weights]
        scored = [e for e in candidates if metric in e.metrics]
        if not scored:
            return None
        return max(scored, key=lambda e: e.metrics[metric])

    def list_types(self) -> list[str]:
        return list(self.by_type.keys())

    def count(self) -> int:
        return len(self.weights)

    def to_list(self) -> list[dict]:
        return [e.to_dict() for e in self.weights.values()]
