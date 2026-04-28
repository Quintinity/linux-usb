"""Tests for the EMEX 2026 Constitution.

Validates that the EMEX-specific Constitution JSON loads correctly and
that the safety caps required for visitor-facing operation (torque, voltage,
position envelope) are present and within bounds.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# Resolve the JSON path relative to this test file so the test runs from any cwd.
HERE = Path(__file__).resolve().parent
EMEX_CONST_PATH = HERE / "emex_constitution.json"


def test_emex_constitution_loads_and_validates():
    """Required by EMEX 2026 Phase 0 plan, Task 17."""
    from citizenry.governance import load_constitution

    c = load_constitution(str(EMEX_CONST_PATH))
    assert c.articles, "must have at least one Article"
    assert c.servo_limits.max_torque_pct <= 60, "EMEX safety: torque cap"
    assert c.servo_limits.max_voltage <= 7.4, "EMEX safety: voltage cap"


def test_emex_constitution_has_position_envelope():
    """Visitor-facing operation requires a hard position envelope."""
    from citizenry.governance import load_constitution

    c = load_constitution(str(EMEX_CONST_PATH))
    env = c.servo_limits.position_envelope
    assert env, "EMEX safety: position envelope must be defined"
    # Each joint should have a (min, max) range in degrees.
    for joint, bounds in env.items():
        assert "min_deg" in bounds and "max_deg" in bounds, \
            f"joint {joint} missing min_deg/max_deg"
        assert bounds["min_deg"] < bounds["max_deg"], \
            f"joint {joint} has inverted bounds"


def test_emex_constitution_has_governor_relax_law():
    """The Governor CLI must be allowed to relax the torque cap to 75%
    via signed amendment — this is the demo handle."""
    from citizenry.governance import load_constitution

    c = load_constitution(str(EMEX_CONST_PATH))
    relax_laws = [law for law in c.laws if law.id == "governor_torque_relax"]
    assert relax_laws, "must have a governor_torque_relax Law"
    law = relax_laws[0]
    assert law.params.get("max_torque_pct_when_relaxed") == 75
    assert law.params.get("requires_signed_amendment") is True


def test_emex_constitution_articles_cover_safety():
    """The Articles must explicitly forbid leaving the demo envelope
    and require halt on overvoltage."""
    from citizenry.governance import load_constitution

    c = load_constitution(str(EMEX_CONST_PATH))
    titles = [a.title.lower() for a in c.articles]
    text_blob = " ".join(a.text.lower() for a in c.articles)
    assert any("envelope" in t or "envelope" in text_blob for t in titles) or \
        "envelope" in text_blob, \
        "must have an Article about the demo envelope"
    assert "voltage" in text_blob, \
        "must have an Article about voltage halt"
