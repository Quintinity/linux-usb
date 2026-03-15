"""Cryptographic Citizen Identity.

Every device generates an Ed25519 keypair at first boot.
The public key IS the identity.
"""

import json
import os
from pathlib import Path

import nacl.signing
import nacl.encoding


IDENTITY_DIR = Path.home() / ".citizenry"


def _ensure_dir():
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True)


def generate_keypair() -> nacl.signing.SigningKey:
    """Generate a new Ed25519 signing key."""
    return nacl.signing.SigningKey.generate()


def save_identity(signing_key: nacl.signing.SigningKey, name: str) -> Path:
    """Save a keypair to disk. Returns the path to the identity file."""
    _ensure_dir()
    path = IDENTITY_DIR / f"{name}.key"
    path.write_bytes(signing_key.encode())
    path.chmod(0o600)
    return path


def load_identity(name: str) -> nacl.signing.SigningKey:
    """Load a keypair from disk."""
    path = IDENTITY_DIR / f"{name}.key"
    return nacl.signing.SigningKey(path.read_bytes())


def load_or_create_identity(name: str) -> nacl.signing.SigningKey:
    """Load existing identity or create a new one."""
    try:
        return load_identity(name)
    except FileNotFoundError:
        key = generate_keypair()
        save_identity(key, name)
        return key


def pubkey_hex(signing_key: nacl.signing.SigningKey) -> str:
    """Get the hex-encoded public key (the citizen ID)."""
    return signing_key.verify_key.encode(encoder=nacl.encoding.RawEncoder).hex()


def short_id(pubkey_hex_str: str) -> str:
    """First 8 chars of the public key hex — for display."""
    return pubkey_hex_str[:8]
