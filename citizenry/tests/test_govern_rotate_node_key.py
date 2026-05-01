"""GOVERN body type: rotate_node_key — bumps node_key_version on receivers."""
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


def _isolate(monkeypatch, tmp_path):
    """Redirect ~/.citizenry to tmp_path so per-citizen keys don't leak."""
    citizenry_dir = tmp_path / ".citizenry"
    citizenry_dir.mkdir()
    from citizenry import identity as identity_module
    from citizenry import node_identity as node_module
    monkeypatch.setattr(identity_module, "IDENTITY_DIR", citizenry_dir)
    monkeypatch.setattr(node_module, "IDENTITY_DIR", citizenry_dir)


def test_rotate_node_key_bumps_version(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-rotate", citizen_type="test", capabilities=[])
    assert c.node_key_version == 1
    c._handle_govern(_env({
        "type": "rotate_node_key",
        "old_node_pubkey": "a" * 64,
        "new_node_pubkey": "b" * 64,
        "version": 2,
    }), addr=("127.0.0.1", 0))
    assert c.node_key_version == 2


def test_rotate_node_key_records_pubkey_for_marketplace(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-rotate-pk", citizen_type="test", capabilities=[])
    c._handle_govern(_env({
        "type": "rotate_node_key",
        "old_node_pubkey": "a" * 64,
        "new_node_pubkey": "b" * 64,
        "version": 2,
    }), addr=("127.0.0.1", 0))
    assert c.stale_node_pubkeys == {"a" * 64}


def test_rotate_node_key_rejects_old_version(monkeypatch, tmp_path):
    """Receiving an older rotate (version < current) is ignored."""
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-rotate-old", citizen_type="test", capabilities=[])
    c.node_key_version = 5
    c._handle_govern(_env({
        "type": "rotate_node_key",
        "old_node_pubkey": "a" * 64,
        "new_node_pubkey": "b" * 64,
        "version": 3,
    }), addr=("127.0.0.1", 0))
    assert c.node_key_version == 5
    assert c.stale_node_pubkeys == set()


def test_rotate_node_key_ignores_equal_version(monkeypatch, tmp_path):
    """Receiving a rotate at the current version is a noop (idempotency)."""
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-rotate-equal", citizen_type="test", capabilities=[])
    c.node_key_version = 5
    c._handle_govern(_env({
        "type": "rotate_node_key",
        "old_node_pubkey": "a" * 64,
        "new_node_pubkey": "b" * 64,
        "version": 5,
    }), addr=("127.0.0.1", 0))
    assert c.node_key_version == 5
    assert c.stale_node_pubkeys == set()


def test_rotate_node_key_rejects_non_hex_pubkey(monkeypatch, tmp_path):
    """Pubkeys must be valid hex even when length is 64."""
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-rotate-nonhex", citizen_type="test", capabilities=[])
    c._handle_govern(_env({
        "type": "rotate_node_key",
        "old_node_pubkey": "z" * 64,
        "new_node_pubkey": "b" * 64,
        "version": 2,
    }), addr=("127.0.0.1", 0))
    assert c.node_key_version == 1
    assert c.stale_node_pubkeys == set()


def test_rotate_node_key_handles_malformed_version(monkeypatch, tmp_path):
    """Non-int version is treated as malformed (does not raise)."""
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-rotate-bad-version", citizen_type="test", capabilities=[])
    c._handle_govern(_env({
        "type": "rotate_node_key",
        "old_node_pubkey": "a" * 64,
        "new_node_pubkey": "b" * 64,
        "version": "two",
    }), addr=("127.0.0.1", 0))
    assert c.node_key_version == 1
    assert c.stale_node_pubkeys == set()
