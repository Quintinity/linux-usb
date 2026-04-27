"""Per-node Ed25519 identity.

Distinct from per-citizen identity (citizenry/identity.py): the node key
binds together every citizen spawned by the same machine so that
co-located bidders can be detected in the marketplace.

Stored at ~/.citizenry/node.key (raw 32 bytes, mode 0600).
"""

from __future__ import annotations

from pathlib import Path

import nacl.signing
import nacl.encoding


IDENTITY_DIR = Path.home() / ".citizenry"


class NodeKeyCorruptError(RuntimeError):
    """Raised when ~/.citizenry/node.key exists but is not a valid Ed25519 seed."""


def _ensure_dir() -> None:
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True)


def _key_path() -> Path:
    return IDENTITY_DIR / "node.key"


def get_or_create_node_signing_key() -> nacl.signing.SigningKey:
    """Load existing node key or generate one on first call."""
    _ensure_dir()
    p = _key_path()
    if p.exists():
        raw = p.read_bytes()
        if len(raw) != 32:
            raise NodeKeyCorruptError(
                f"{p} has length {len(raw)}, expected 32. "
                "Delete or restore from backup before starting any citizen."
            )
        return nacl.signing.SigningKey(raw)
    key = nacl.signing.SigningKey.generate()
    p.write_bytes(key.encode())
    p.chmod(0o600)
    return key


def get_node_pubkey() -> str:
    """Hex-encoded Ed25519 public key for this node."""
    sk = get_or_create_node_signing_key()
    return sk.verify_key.encode(encoder=nacl.encoding.RawEncoder).hex()
