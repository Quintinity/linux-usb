"""Tests for the citizen-mcp server.

Covers the wiring between MCP tool calls and the citizenry mesh:

  * the spec'd ``build_server()`` returns a server exposing exactly three
    named tools (``get_status``, ``govern_update``, ``propose_task``);
  * ``propose_task`` builds and multicasts a signed PROPOSE envelope whose
    body matches the ``Task.from_propose_body`` schema;
  * ``govern_update`` mutates the EMEX Constitution, re-signs the raw dict
    using the canonical-JSON pattern (the same shape as the T21 tablet UI),
    bumps the version, and multicasts a GOVERN envelope;
  * ``get_status`` listens on a private (non-default) multicast group for a
    short window and reports the heartbeats it captured. We use a private
    group so the test never collides with whatever real citizens may be
    running on the host.

We never mock nacl — every signature we assert on must verify under the
node's real Ed25519 pubkey. The tests do, however, swap the multicast
group/port for an ephemeral one to keep them hermetic.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import socket
import struct
import threading
import time
from pathlib import Path

import nacl.signing
import pytest


@pytest.fixture
def tmp_identity(tmp_path, monkeypatch):
    """Use a throwaway ~/.citizenry directory so tests don't trample real keys."""
    monkeypatch.setenv("HOME", str(tmp_path))
    from citizenry import identity
    importlib.reload(identity)
    # Make sure the citizen-mcp module picks up the reloaded identity module
    # when it imports load_or_create_identity at construction time.
    from citizenry.mcp import citizen_mcp_server
    importlib.reload(citizen_mcp_server)
    return tmp_path


# ---------------------------------------------------------------------------
# Tool surface
# ---------------------------------------------------------------------------


def test_citizen_mcp_exposes_three_actions(tmp_identity):
    from citizenry.mcp.citizen_mcp_server import build_server
    s = build_server()
    names = sorted(t.name for t in s.list_tools())
    assert names == ["get_status", "govern_update", "propose_task"]


# ---------------------------------------------------------------------------
# propose_task: builds and multicasts a signed PROPOSE envelope
# ---------------------------------------------------------------------------


def _open_listener(port: int, group: str = "239.67.84.91") -> socket.socket:
    """Open a UDP listener bound to a private multicast group/port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", port))
    mreq = struct.pack("4sl", socket.inet_aton(group), socket.INADDR_ANY)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    s.settimeout(2.0)
    return s


def test_propose_task_multicasts_signed_envelope(tmp_identity, monkeypatch):
    from citizenry.mcp import citizen_mcp_server
    from citizenry.protocol import Envelope, MessageType

    # Move the broadcast onto a private group/port for the test.
    test_group = "239.67.84.91"
    test_port = 27770
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_GROUP", test_group)
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_PORT", test_port)

    listener = _open_listener(test_port, test_group)
    try:
        srv = citizen_mcp_server.build_server()
        result = srv.call_tool_sync(
            "propose_task",
            {"task_type": "kit_sort", "params": {"target": "tray_a"}, "priority": 0.7},
        )
        assert "task_id" in result
        assert "envelope_signature_short" in result
        assert len(result["envelope_signature_short"]) == 8

        data, _addr = listener.recvfrom(65535)
        env = Envelope.from_bytes(data)
        assert env.type == int(MessageType.PROPOSE)
        assert env.body["task"] == "kit_sort"
        assert env.body["task_id"] == result["task_id"]
        assert env.body["params"] == {"target": "tray_a"}
        assert env.body["priority"] == 0.7

        # Verify the envelope under the server's pubkey.
        vk = nacl.signing.VerifyKey(bytes.fromhex(env.sender))
        assert env.verify(vk)
        assert env.signature.startswith(result["envelope_signature_short"])
    finally:
        listener.close()


# ---------------------------------------------------------------------------
# govern_update: mutates Constitution, re-signs dict, multicasts GOVERN
# ---------------------------------------------------------------------------


def test_govern_update_signs_amended_constitution(tmp_identity, monkeypatch, tmp_path):
    from citizenry.mcp import citizen_mcp_server
    from citizenry.protocol import Envelope, MessageType

    # Stand up a writable copy of the EMEX Constitution.
    src = Path(__file__).resolve().parent.parent / "governance" / "emex_constitution.json"
    constitution_path = tmp_path / "constitution.json"
    constitution_path.write_text(src.read_text())

    test_group = "239.67.84.91"
    test_port = 27771
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_GROUP", test_group)
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_PORT", test_port)

    listener = _open_listener(test_port, test_group)
    try:
        srv = citizen_mcp_server.build_server()
        result = srv.call_tool_sync(
            "govern_update",
            {
                "path": str(constitution_path),
                "mutator": {"set_servo_limits": {"max_torque_pct": 70}},
            },
        )

        assert result["version"] >= 2  # baseline is v1
        assert len(result["envelope_signature_short"]) == 8

        data, _addr = listener.recvfrom(65535)
        env = Envelope.from_bytes(data)
        assert env.type == int(MessageType.GOVERN)
        assert env.body["type"] == "constitution"
        c = env.body["constitution"]

        # The wire constitution must have the EMEX max_torque_pct intact.
        assert c["servo_limits"]["max_torque_pct"] == 70
        # Version was bumped.
        assert c["version"] == result["version"]

        # Verify the *Constitution* signature using the canonical-JSON shape
        # — the same logic _sign_dict uses. We're not allowed to round-trip
        # through Constitution.from_dict because that strips EMEX fields.
        payload = dict(c)
        payload.pop("signature", None)
        signable = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        nacl.signing.VerifyKey(bytes.fromhex(c["governor_pubkey"])).verify(
            signable, bytes.fromhex(c["signature"])
        )

        # And verify the GOVERN envelope itself.
        vk = nacl.signing.VerifyKey(bytes.fromhex(env.sender))
        assert env.verify(vk)
    finally:
        listener.close()


def test_govern_update_law_patch(tmp_identity, monkeypatch, tmp_path):
    """The {law_id, patch} mutator shape must update an existing law's params."""
    from citizenry.mcp import citizen_mcp_server
    from citizenry.protocol import Envelope

    src = Path(__file__).resolve().parent.parent / "governance" / "emex_constitution.json"
    constitution_path = tmp_path / "constitution.json"
    constitution_path.write_text(src.read_text())

    test_group = "239.67.84.91"
    test_port = 27772
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_GROUP", test_group)
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_PORT", test_port)

    listener = _open_listener(test_port, test_group)
    try:
        srv = citizen_mcp_server.build_server()
        srv.call_tool_sync(
            "govern_update",
            {
                "path": str(constitution_path),
                "mutator": {
                    "law_id": "governor_torque_relax",
                    "patch": {"params": {"currently_relaxed": True}},
                },
            },
        )
        data, _addr = listener.recvfrom(65535)
        env = Envelope.from_bytes(data)
        c = env.body["constitution"]
        relax = next(l for l in c["laws"] if l["id"] == "governor_torque_relax")
        assert relax["params"]["currently_relaxed"] is True
        # Original keys preserved (we patched, not replaced).
        assert "auto_revert_seconds" in relax["params"]
    finally:
        listener.close()


# ---------------------------------------------------------------------------
# get_status: heartbeat-snapshot listener
# ---------------------------------------------------------------------------


def test_get_status_collects_heartbeats(tmp_identity, monkeypatch):
    """Spin up a fake heartbeat broadcaster and confirm get_status hears it."""
    from citizenry.identity import generate_keypair, pubkey_hex
    from citizenry.mcp import citizen_mcp_server
    from citizenry.protocol import MessageType, make_envelope

    test_group = "239.67.84.91"
    test_port = 27773
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_GROUP", test_group)
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_PORT", test_port)

    fake_key = generate_keypair()
    fake_pubkey = pubkey_hex(fake_key)

    stop = threading.Event()

    def emit():
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL,
                          struct.pack("b", 1))
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        try:
            while not stop.is_set():
                env = make_envelope(
                    MessageType.HEARTBEAT,
                    fake_pubkey,
                    {
                        "name": "fake-citizen",
                        "state": "idle",
                        "health": 0.9,
                        "emotional_state": {"valence": 0.7, "arousal": 0.3},
                    },
                    fake_key,
                )
                sender.sendto(env.to_bytes(), (test_group, test_port))
                time.sleep(0.2)
        finally:
            sender.close()

    t = threading.Thread(target=emit, daemon=True)
    t.start()
    try:
        srv = citizen_mcp_server.build_server()
        result = srv.call_tool_sync("get_status", {"wait_seconds": 1.5})
    finally:
        stop.set()
        t.join(timeout=2.0)

    assert result["snapshot_window_s"] == 1.5
    assert any(c["pubkey"] == fake_pubkey for c in result["citizens"])
    found = next(c for c in result["citizens"] if c["pubkey"] == fake_pubkey)
    assert found["name"] == "fake-citizen"
    assert found["state"] == "ONLINE"
    assert found["emotional_state"] == {"valence": 0.7, "arousal": 0.3}


def test_get_status_clamps_wait_seconds(tmp_identity, monkeypatch):
    """Out-of-range wait_seconds must clamp to [0.1, 10] without failing."""
    from citizenry.mcp import citizen_mcp_server

    test_group = "239.67.84.91"
    test_port = 27774
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_GROUP", test_group)
    monkeypatch.setattr(citizen_mcp_server, "MULTICAST_PORT", test_port)

    srv = citizen_mcp_server.build_server()
    result = srv.call_tool_sync("get_status", {"wait_seconds": 99})
    assert result["snapshot_window_s"] == 10.0
