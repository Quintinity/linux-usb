"""Authority signing key — single-key for v2.0 (multi-sig is v2.1)."""
import os
import tempfile
from pathlib import Path

import pytest

from citizenry import authority


@pytest.fixture
def isolated_home(monkeypatch, tmp_path):
    """Redirect ~/.citizenry to a temp dir for the duration of the test."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    # Re-resolve module-level constants that captured Path.home()
    monkeypatch.setattr(authority, "AUTHORITY_DIR", fake_home / ".citizenry")
    monkeypatch.setattr(
        authority, "_KEY_PATH", fake_home / ".citizenry" / "authority.key"
    )
    return fake_home


def test_load_or_create_authority_key_is_idempotent(isolated_home):
    k1 = authority.load_or_create_authority_key()
    k2 = authority.load_or_create_authority_key()
    assert k1.encode() == k2.encode()


def test_authority_key_is_persisted_with_mode_0600(isolated_home):
    authority.load_or_create_authority_key()
    p = isolated_home / ".citizenry" / "authority.key"
    assert p.exists()
    assert (p.stat().st_mode & 0o777) == 0o600
    assert len(p.read_bytes()) == 32


def test_authority_pubkey_hex_is_64_chars(isolated_home):
    pub = authority.authority_pubkey_hex()
    assert isinstance(pub, str)
    assert len(pub) == 64
    int(pub, 16)  # must parse as hex


def test_corrupt_authority_key_raises(isolated_home):
    p = isolated_home / ".citizenry" / "authority.key"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"not32bytes")
    with pytest.raises(authority.AuthorityKeyCorruptError):
        authority.load_or_create_authority_key()


def test_load_or_create_warns_on_fresh_mint(isolated_home, caplog):
    """A freshly-minted Authority key emits a WARNING log line."""
    import logging
    caplog.set_level(logging.WARNING, logger="citizenry.authority")
    authority.load_or_create_authority_key()
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("Minted fresh Authority key" in r.message for r in warnings), (
        f"expected fresh-mint warning, got: {[r.message for r in warnings]}"
    )


def test_load_or_create_silent_on_existing_key(isolated_home, caplog):
    """Loading an existing key does NOT emit the fresh-mint warning."""
    import logging
    # First call mints the key.
    authority.load_or_create_authority_key()
    caplog.clear()
    caplog.set_level(logging.WARNING, logger="citizenry.authority")
    # Second call should be silent on the warn path.
    authority.load_or_create_authority_key()
    assert not any(
        "Minted fresh" in r.message for r in caplog.records
    ), "fresh-mint warning fired on existing key"
