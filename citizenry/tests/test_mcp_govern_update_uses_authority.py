"""MCP server's govern_update path signs Constitution amendments with Authority.

Smell #1 fix: Constitution-amendment broadcast paths (MCP govern_update tool
and the EMEX governor tablet) must sign payloads with authority.key, not the
node/citizen key. The multicast envelopes that carry the payloads continue to
be signed by the node/citizen key. Two layers, two distinct keys.

Companion to test_governor_citizen_signs_with_authority.py (Task 8).
"""
import json
from pathlib import Path

import pytest
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder

from citizenry.constitution import default_constitution


def _setup_isolated_keys(monkeypatch, tmp_path):
    """Match the pattern from test_governor_citizen_signs_with_authority.py.

    Module-level constants in identity.py and authority.py are computed
    at import time, so we have to patch them directly — setenv("HOME") alone
    is a no-op."""
    citizenry_dir = tmp_path / ".citizenry"
    citizenry_dir.mkdir()

    from citizenry import authority as authority_module
    from citizenry import identity as identity_module
    from citizenry import node_identity as node_module

    monkeypatch.setattr(identity_module, "IDENTITY_DIR", citizenry_dir)
    monkeypatch.setattr(authority_module, "AUTHORITY_DIR", citizenry_dir)
    monkeypatch.setattr(authority_module, "_KEY_PATH", citizenry_dir / "authority.key")
    monkeypatch.setattr(node_module, "IDENTITY_DIR", citizenry_dir)

    auth = SigningKey.generate()
    (citizenry_dir / "authority.key").write_bytes(auth.encode())
    (citizenry_dir / "authority.key").chmod(0o600)
    node = SigningKey.generate()
    (citizenry_dir / "node.key").write_bytes(node.encode())
    (citizenry_dir / "node.key").chmod(0o600)
    # Pre-place a v2 Constitution that the server will mutate.
    c = default_constitution()
    c.sign(auth)
    (citizenry_dir / "governor.constitution.json").write_text(json.dumps(c.to_dict()))
    return tmp_path, auth, node


def test_resign_constitution_with_authority(monkeypatch, tmp_path):
    """After a govern_update mutation, the on-disk Constitution must verify
    against the Authority key, not the node key."""
    tmp_path, auth, node = _setup_isolated_keys(monkeypatch, tmp_path)
    from citizenry.mcp.citizen_mcp_server import _resign_constitution_with_authority

    cfg_path = tmp_path / ".citizenry" / "governor.constitution.json"
    data = json.loads(cfg_path.read_text())
    data["laws"] = [
        {"id": "test_new_law", "description": "added by mcp", "params": {"v": 1}}
    ]
    new_dict = _resign_constitution_with_authority(data)
    auth_pub = VerifyKey(auth.verify_key.encode())
    node_pub = VerifyKey(node.verify_key.encode())
    from citizenry.constitution import Constitution
    c = Constitution.from_dict(new_dict)
    assert c.verify(auth_pub) is True
    assert c.verify(node_pub) is False
    assert c.authority_pubkey == auth.verify_key.encode(encoder=HexEncoder).decode()


def test_emex_tablet_sign_dict_uses_authority(monkeypatch, tmp_path):
    """GovernorTabletServer._sign_dict must sign Constitution dicts with the
    Authority key, not its own per-citizen key."""
    tmp_path, auth, node = _setup_isolated_keys(monkeypatch, tmp_path)
    from citizenry.cli.governor_emex_tablet import GovernorTabletServer
    # GovernorTabletServer wraps the EMEX constitution; we just need to call
    # the signing helper. Default constructor loads the on-disk EMEX baseline,
    # then signs it via _sign_dict — which is exactly what we want to verify.
    tablet = GovernorTabletServer()

    # Build a sane Constitution dict (default_constitution-shaped) so the
    # canonical bytes the helper signs match what Constitution._signable_payload
    # will reconstruct on verify. Add a sentinel law for traceability.
    base = default_constitution()
    raw_dict = base.to_dict()
    raw_dict["signature"] = ""
    raw_dict["authority_pubkey"] = ""
    raw_dict["governor_pubkey"] = ""
    raw_dict["laws"] = [{"id": "x", "description": "y", "params": {"v": 1}}]

    signed = tablet._sign_dict(raw_dict)
    auth_pub = VerifyKey(auth.verify_key.encode())
    node_pub = VerifyKey(node.verify_key.encode())
    from citizenry.constitution import Constitution
    c = Constitution.from_dict(signed)
    assert c.verify(auth_pub) is True
    assert c.verify(node_pub) is False
    assert c.authority_pubkey == auth.verify_key.encode(encoder=HexEncoder).decode()
