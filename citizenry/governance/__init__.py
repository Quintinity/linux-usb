"""citizenry.governance — Constitution loaders for specific deployments.

The base Constitution / Article / Law / ServoLimits dataclasses live in
``citizenry.constitution``. This subpackage holds deployment-specific
Constitution JSON files (EMEX 2026, lab, factory, ...) and a path-based
loader that returns a Constitution object compatible with the rest of the
citizenry runtime.

The EMEX deployment requires a few extra ServoLimit fields that the base
schema does not carry (visitor-safety percent torque cap, max-voltage halt
threshold, per-joint position envelope). Rather than mutate the wire-level
constitution (which would force every existing citizen to re-handshake),
this module wraps the base ServoLimits with an EMEX-aware view that exposes
those fields as attributes while leaving the base schema untouched.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from citizenry.constitution import (
    Article,
    Constitution as _BaseConstitution,
    Law,
    ServoLimits as _BaseServoLimits,
)


# ---------------------------------------------------------------------------
# EMEX-aware ServoLimits view
# ---------------------------------------------------------------------------

@dataclass
class ServoLimitsView:
    """Read-only view that exposes both base and deployment-specific limits.

    Base fields (max_torque, protection_current, max_temperature, ...) come
    from the wire-level ServoLimits. Deployment fields (max_torque_pct,
    max_voltage, position_envelope) come from the same JSON dict but live
    outside the base dataclass so older citizens ignore them safely.
    """

    base: _BaseServoLimits
    max_torque_pct: int = 100
    max_voltage: float = 7.4
    position_envelope: dict[str, dict[str, float]] = field(default_factory=dict)

    # Pass-through to the base dataclass so callers can use either naming.
    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)


@dataclass
class ConstitutionView:
    """A Constitution plus its EMEX-aware ServoLimitsView.

    Behaves like a normal Constitution for ``articles``, ``laws``,
    ``version``, ``governor_pubkey``, ``signature`` — and exposes the
    enriched ``servo_limits`` view.
    """

    base: _BaseConstitution
    servo_limits: ServoLimitsView

    @property
    def articles(self) -> list[Article]:
        return self.base.articles

    @property
    def laws(self) -> list[Law]:
        return self.base.laws

    @property
    def version(self) -> int:
        return self.base.version

    @property
    def governor_pubkey(self) -> str:
        return self.base.governor_pubkey

    @property
    def signature(self) -> str:
        return self.base.signature

    def verify(self) -> bool:
        return self.base.verify()


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

# Fields that belong to the base ServoLimits dataclass (so they round-trip
# cleanly through the existing wire format).
_BASE_SERVO_FIELDS = {
    "max_torque",
    "protection_current",
    "max_temperature",
    "overload_torque",
    "protective_torque",
    "min_voltage",
}


def load_constitution(path: str | Path) -> ConstitutionView:
    """Load a Constitution JSON file from disk.

    Unlike ``citizenry.persistence.load_constitution`` (which is keyed by
    citizen name and returns a plain dict), this loader takes a filesystem
    path and returns a fully parsed ``ConstitutionView`` whose
    ``servo_limits`` exposes both the base wire-level fields and any
    deployment-specific extensions (``max_torque_pct``, ``max_voltage``,
    ``position_envelope``).

    Raises FileNotFoundError if the path is missing and ValueError on
    malformed JSON.
    """
    p = Path(path)
    raw = p.read_text()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid Constitution JSON at {p}: {e}") from e

    sl_data = dict(data.get("servo_limits", {}))
    # Split fields between the base dataclass and the EMEX extensions so the
    # base ServoLimits constructor doesn't choke on unknown kwargs.
    base_kwargs = {k: v for k, v in sl_data.items() if k in _BASE_SERVO_FIELDS}
    ext_kwargs = {k: v for k, v in sl_data.items() if k not in _BASE_SERVO_FIELDS}

    base_data = dict(data)
    base_data["servo_limits"] = base_kwargs
    base = _BaseConstitution.from_dict(base_data)

    view = ServoLimitsView(
        base=base.servo_limits,
        max_torque_pct=int(ext_kwargs.get("max_torque_pct", 100)),
        max_voltage=float(ext_kwargs.get("max_voltage", 7.4)),
        position_envelope=ext_kwargs.get("position_envelope", {}) or {},
    )
    return ConstitutionView(base=base, servo_limits=view)


__all__ = [
    "Article",
    "Law",
    "ConstitutionView",
    "ServoLimitsView",
    "load_constitution",
]
