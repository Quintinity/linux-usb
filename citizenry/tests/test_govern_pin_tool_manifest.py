"""GOVERN body type: pin_tool_manifest — sha256 pin of an MCP server's tool surface."""
import time

from citizenry.citizen import Citizen
from citizenry.protocol import Envelope, MessageType


def _env(body: dict) -> Envelope:
    return Envelope(
        version=1,
        type=int(MessageType.GOVERN),
        sender="ab" * 32,
        recipient="*",
        timestamp=time.time(),
        ttl=3600.0,
        body=body,
        signature="cd" * 64,
    )


def test_pin_tool_manifest_records_sha(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-pin-tm", citizen_type="test", capabilities=[])
    c._handle_govern(_env({
        "type": "pin_tool_manifest",
        "server": "bus-mcp",
        "sha256": "1" * 64,
    }), addr=("127.0.0.1", 0))
    assert c.tool_manifest_pinning == {"bus-mcp": "1" * 64}


def test_pin_tool_manifest_replaces_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-pin-tm-replace", citizen_type="test", capabilities=[])
    c._handle_govern(_env({
        "type": "pin_tool_manifest", "server": "bus-mcp", "sha256": "1" * 64,
    }), addr=("127.0.0.1", 0))
    c._handle_govern(_env({
        "type": "pin_tool_manifest", "server": "bus-mcp", "sha256": "2" * 64,
    }), addr=("127.0.0.1", 0))
    assert c.tool_manifest_pinning["bus-mcp"] == "2" * 64


def test_pin_tool_manifest_rejects_short_sha(monkeypatch, tmp_path):
    """Sha256 hex must be exactly 64 chars."""
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-pin-tm-bad", citizen_type="test", capabilities=[])
    c._handle_govern(_env({
        "type": "pin_tool_manifest", "server": "bus-mcp", "sha256": "abc",
    }), addr=("127.0.0.1", 0))
    assert "bus-mcp" not in c.tool_manifest_pinning
