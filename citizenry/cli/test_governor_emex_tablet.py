"""Smoke tests for the EMEX 2026 tablet governor.

Covers the load -> mutate -> sign -> verify loop for each of the three
amendment paths. We don't bring up the aiohttp server here — we exercise
the GovernorTabletServer in-memory and check that the resulting GOVERN
envelope verifies under the node's published pubkey.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import nacl.encoding
import nacl.signing
import pytest

from citizenry.cli.governor_emex_tablet import (
    EMEX_CONSTITUTION_PATH,
    GovernorTabletServer,
    PAUSE_LAW_ID,
    TORQUE_PCT_RELAXED,
    TORQUE_PCT_RESTRICTED,
)
from citizenry.protocol import (
    MULTICAST_GROUP,
    MULTICAST_PORT,
    Envelope,
    MessageType,
    make_envelope,
)


@pytest.fixture
def tmp_identity(tmp_path, monkeypatch):
    """Use a throwaway ~/.citizenry directory so tests don't trample real keys."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # citizenry.identity reads Path.home() at import; reload to pick up new HOME.
    import importlib
    from citizenry import identity
    importlib.reload(identity)
    return tmp_path


def test_baseline_constitution_is_signed_by_node(tmp_identity):
    srv = GovernorTabletServer(constitution_path=EMEX_CONSTITUTION_PATH)
    snap = srv.state_snapshot()
    assert snap["max_torque_pct"] == 60, "EMEX baseline must enforce 60% cap"
    assert not snap["paused"]

    # Verify the embedded Constitution signature against the node pubkey.
    c = srv.current_dict
    payload = dict(c)
    payload.pop("signature", None)
    signable = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    pubkey = bytes.fromhex(c["governor_pubkey"])
    nacl.signing.VerifyKey(pubkey).verify(signable, bytes.fromhex(c["signature"]))


def test_relax_amendment_signs_and_envelope_verifies(tmp_identity):
    srv = GovernorTabletServer(constitution_path=EMEX_CONSTITUTION_PATH)

    loop = asyncio.new_event_loop()
    try:
        result = srv.apply_relax(loop)
    finally:
        # Cancel the background revert task so the loop closes cleanly.
        if srv._revert_task:
            srv._revert_task.cancel()
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()

    assert srv.current_dict["servo_limits"]["max_torque_pct"] == TORQUE_PCT_RELAXED
    assert result["version"] == srv.current_dict["version"]
    assert result["auto_revert_at"] is not None

    # Re-verify the Constitution signature with the node's pubkey.
    c = srv.current_dict
    payload = dict(c); payload.pop("signature", None)
    signable = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    nacl.signing.VerifyKey(bytes.fromhex(c["governor_pubkey"])).verify(
        signable, bytes.fromhex(c["signature"])
    )

    # Build an envelope identical to the one the server multicasts and verify it.
    env = make_envelope(
        MessageType.GOVERN,
        srv.pubkey_hex,
        {"type": "constitution", "constitution": c},
        srv.signing_key,
        recipient="*",
    )
    assert env.verify(srv.signing_key.verify_key)


def test_restrict_drops_torque_to_50(tmp_identity):
    srv = GovernorTabletServer(constitution_path=EMEX_CONSTITUTION_PATH)
    srv.apply_restrict()
    assert srv.current_dict["servo_limits"]["max_torque_pct"] == TORQUE_PCT_RESTRICTED
    assert not any(l.get("id") == PAUSE_LAW_ID for l in srv.current_dict["laws"])


def test_pause_pins_envelope_and_adds_pause_law(tmp_identity):
    srv = GovernorTabletServer(constitution_path=EMEX_CONSTITUTION_PATH)
    srv.apply_pause()

    # Every axis should now be a single-point envelope.
    env = srv.current_dict["servo_limits"]["position_envelope"]
    for axis, lim in env.items():
        assert lim["min_deg"] == lim["max_deg"], f"{axis} not pinned"

    assert any(l.get("id") == PAUSE_LAW_ID for l in srv.current_dict["laws"])
    assert srv.state_snapshot()["paused"]


def test_relax_after_pause_clears_pause_law(tmp_identity):
    srv = GovernorTabletServer(constitution_path=EMEX_CONSTITUTION_PATH)
    srv.apply_pause()
    loop = asyncio.new_event_loop()
    try:
        srv.apply_relax(loop)
    finally:
        if srv._revert_task:
            srv._revert_task.cancel()
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()
    assert not any(l.get("id") == PAUSE_LAW_ID for l in srv.current_dict["laws"])
