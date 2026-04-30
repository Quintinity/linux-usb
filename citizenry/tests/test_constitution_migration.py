"""v1 → v2 Constitution migration."""
import json
from pathlib import Path

import pytest
from nacl.signing import SigningKey

from citizenry.constitution import Constitution, default_constitution
from citizenry.scripts.migrate_constitution import migrate_v1_dict, migrate_file


def _v1_payload(governor_pubkey: str) -> dict:
    return {
        "version": 1,
        "governor_pubkey": governor_pubkey,
        "articles": [
            {"number": 1, "title": "Test", "text": "A test article."}
        ],
        "laws": [
            {"id": "x", "description": "y", "params": {"v": 1}}
        ],
        "servo_limits": {"max_torque": 500},
        "signature": "deadbeef",
    }


def test_migrate_v1_dict_sets_v2_fields():
    auth = SigningKey.generate()
    auth_pub = auth.verify_key.encode().hex()
    v1 = _v1_payload(governor_pubkey="cafebabe" * 8)
    v2 = migrate_v1_dict(v1, authority_signing_key=auth)
    assert v2["version"] == 2
    assert v2["authority_pubkey"] == auth_pub
    # legacy field mirrored (so old verifiers still pass)
    assert v2["governor_pubkey"] == auth_pub
    assert v2["node_key_version"] == 1
    assert v2["tool_manifest_pinning"] == {}
    assert v2["policy_pinning"] == {}


def test_migrated_constitution_verifies_with_authority():
    auth = SigningKey.generate()
    v1 = _v1_payload(governor_pubkey="cafebabe" * 8)
    v2 = migrate_v1_dict(v1, authority_signing_key=auth)
    c = Constitution.from_dict(v2)
    assert c.verify() is True


def test_migrate_file_atomic_with_backup(tmp_path):
    auth = SigningKey.generate()
    target = tmp_path / "governor.constitution.json"
    target.write_text(json.dumps(_v1_payload(governor_pubkey="d" * 64)))
    migrate_file(target, authority_signing_key=auth)
    backup = tmp_path / "governor.constitution.v1.bak.json"
    assert backup.exists(), "v1 backup must be created"
    assert json.loads(backup.read_text())["version"] == 1
    after = json.loads(target.read_text())
    assert after["version"] == 2
    c = Constitution.from_dict(after)
    assert c.verify() is True


def test_migrate_file_idempotent_on_v2(tmp_path):
    """Running migration twice does not break a v2 file."""
    auth = SigningKey.generate()
    target = tmp_path / "governor.constitution.json"
    target.write_text(json.dumps(_v1_payload(governor_pubkey="e" * 64)))
    migrate_file(target, authority_signing_key=auth)
    first = target.read_text()
    # Second call should detect v2 and noop (no re-sign).
    migrate_file(target, authority_signing_key=auth)
    second = target.read_text()
    assert first == second
