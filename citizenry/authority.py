"""Authority signing key — the root identity that ratifies Constitution amendments.

In v2.0 this is a single Ed25519 key at ``~/.citizenry/authority.key``.
v2.1 will introduce multi-sig (2-of-3 with offline keys); the public surface
of this module is designed to remain stable across that transition.

Distinct from:
- ``citizenry.node_identity`` (per-machine identity for transport / co-location).
- ``citizenry.identity`` (per-citizen role identities).

Authority signs Constitution and Law amendments only. It must never sign
runtime mesh messages — those are signed by role identities.
"""
from __future__ import annotations

from pathlib import Path

import nacl.signing
import nacl.encoding

import logging

_log = logging.getLogger(__name__)


AUTHORITY_DIR = Path.home() / ".citizenry"
_KEY_PATH = AUTHORITY_DIR / "authority.key"


class AuthorityKeyCorruptError(RuntimeError):
    """Raised when ~/.citizenry/authority.key exists but is not a valid Ed25519 seed."""


def _ensure_dir() -> None:
    AUTHORITY_DIR.mkdir(parents=True, exist_ok=True)


def load_or_create_authority_key() -> nacl.signing.SigningKey:
    """Load or generate the Authority signing key.

    Idempotent. Persists at ``~/.citizenry/authority.key`` with mode 0600.
    """
    _ensure_dir()
    if _KEY_PATH.exists():
        raw = _KEY_PATH.read_bytes()
        if len(raw) != 32:
            raise AuthorityKeyCorruptError(
                f"{_KEY_PATH} has length {len(raw)}, expected 32. "
                "Restore from backup before issuing GOVERN."
            )
        return nacl.signing.SigningKey(raw)
    key = nacl.signing.SigningKey.generate()
    _KEY_PATH.write_bytes(key.encode())
    _KEY_PATH.chmod(0o600)
    pub_hex = key.verify_key.encode(encoder=nacl.encoding.RawEncoder).hex()
    _log.warning(
        "Minted fresh Authority key at %s (pubkey=%s…). "
        "If this host previously had an authority.key, restore from backup "
        "before broadcasting any GOVERN amendments — citizens with cached "
        "constitutions will reject this new root identity.",
        _KEY_PATH, pub_hex[:12],
    )
    return key


def authority_pubkey_hex() -> str:
    """Hex-encoded Ed25519 public key of the Authority."""
    sk = load_or_create_authority_key()
    return sk.verify_key.encode(encoder=nacl.encoding.RawEncoder).hex()
