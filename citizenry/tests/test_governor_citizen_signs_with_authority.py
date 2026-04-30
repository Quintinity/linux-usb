"""Smell #1 fix: GovernorCitizen signs Constitution amendments with Authority key.

The per-citizen governor.key remains the identity for heartbeat/advertise
mesh traffic; only Constitution and Law amendments switch to authority.key.
"""
import os
from pathlib import Path

import pytest
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder

from citizenry import authority as authority_module
from citizenry import identity as identity_module
from citizenry.constitution import default_constitution


def _setup_isolated_keys(monkeypatch, tmp_path):
    """Redirect both identity and authority key dirs into tmp_path/.citizenry,
    pre-seed distinct authority + governor keys, return them."""
    citizenry_dir = tmp_path / ".citizenry"
    citizenry_dir.mkdir()

    # Redirect module-level constants so loaders write/read into tmp_path.
    monkeypatch.setattr(identity_module, "IDENTITY_DIR", citizenry_dir)
    monkeypatch.setattr(authority_module, "AUTHORITY_DIR", citizenry_dir)
    monkeypatch.setattr(authority_module, "_KEY_PATH", citizenry_dir / "authority.key")

    # Pre-create distinct authority and governor identities so we can verify
    # the signature provenance.
    auth_key = SigningKey.generate()
    (citizenry_dir / "authority.key").write_bytes(auth_key.encode())
    (citizenry_dir / "authority.key").chmod(0o600)
    gov_key = SigningKey.generate()
    (citizenry_dir / "governor.key").write_bytes(gov_key.encode())
    (citizenry_dir / "governor.key").chmod(0o600)
    return auth_key, gov_key


def test_governor_signs_with_authority_key(monkeypatch, tmp_path):
    """Loading the GovernorCitizen and asking it to ratify a fresh Constitution
    must produce a signature verifiable with the Authority pubkey, not the
    governor citizen's pubkey."""
    auth_key, gov_key = _setup_isolated_keys(monkeypatch, tmp_path)

    from citizenry.governor_citizen import GovernorCitizen

    g = GovernorCitizen(name="governor")
    c = default_constitution()
    g.ratify_constitution(c)

    auth_pub = VerifyKey(auth_key.verify_key.encode())
    gov_pub = VerifyKey(gov_key.verify_key.encode())

    # The Constitution must verify against the Authority key.
    assert c.verify(auth_pub) is True
    # And NOT against the governor citizen key.
    assert c.verify(gov_pub) is False
    # authority_pubkey on the Constitution must match the authority key, not the governor key.
    assert c.authority_pubkey == auth_key.verify_key.encode(encoder=HexEncoder).decode()


def test_governor_heartbeat_still_signed_with_governor_key(monkeypatch, tmp_path):
    """Confirm the per-citizen governor key remains the heartbeat/advertise
    identity (no regression on existing mesh signatures)."""
    auth_key, gov_key = _setup_isolated_keys(monkeypatch, tmp_path)

    from citizenry.governor_citizen import GovernorCitizen

    g = GovernorCitizen(name="governor")
    # Heartbeat envelope sender must be the governor citizen pubkey, not Authority.
    gov_pub_hex = gov_key.verify_key.encode(encoder=HexEncoder).decode()
    assert g.pubkey == gov_pub_hex
