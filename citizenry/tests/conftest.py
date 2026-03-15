"""Shared test fixtures for citizenry v2.0 tests."""

import pytest
import nacl.signing

from citizenry.protocol import Envelope, make_envelope, MessageType
from citizenry.identity import generate_keypair, pubkey_hex


@pytest.fixture
def signing_key():
    """A fresh Ed25519 signing key for tests."""
    return generate_keypair()


@pytest.fixture
def pubkey(signing_key):
    """Hex-encoded public key."""
    return pubkey_hex(signing_key)


@pytest.fixture
def second_signing_key():
    """A second keypair for two-party tests."""
    return generate_keypair()


@pytest.fixture
def second_pubkey(second_signing_key):
    return pubkey_hex(second_signing_key)


@pytest.fixture
def third_signing_key():
    return generate_keypair()


@pytest.fixture
def third_pubkey(third_signing_key):
    return pubkey_hex(third_signing_key)


@pytest.fixture
def make_signed_envelope(signing_key, pubkey):
    """Factory for creating signed envelopes."""
    def _make(msg_type, body, recipient="*", ttl=10.0):
        return make_envelope(msg_type, pubkey, body, signing_key, recipient=recipient, ttl=ttl)
    return _make
