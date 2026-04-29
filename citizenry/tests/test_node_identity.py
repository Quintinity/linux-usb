"""Tests for the per-node Ed25519 identity layer."""

import pytest
from pathlib import Path

import nacl.signing

from citizenry import node_identity


def test_get_or_create_generates_on_first_call(tmp_path, monkeypatch):
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    key = node_identity.get_or_create_node_signing_key()
    assert isinstance(key, nacl.signing.SigningKey)
    assert (tmp_path / "node.key").exists()
    assert (tmp_path / "node.key").stat().st_mode & 0o777 == 0o600


def test_get_or_create_returns_same_key_on_subsequent_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    k1 = node_identity.get_or_create_node_signing_key()
    k2 = node_identity.get_or_create_node_signing_key()
    assert k1.encode() == k2.encode()


def test_get_node_pubkey_is_64_hex_chars(tmp_path, monkeypatch):
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    pk = node_identity.get_node_pubkey()
    assert len(pk) == 64
    int(pk, 16)  # raises if not hex


def test_corrupt_key_refuses_to_load(tmp_path, monkeypatch):
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    (tmp_path / "node.key").write_bytes(b"\x00" * 5)  # too short
    with pytest.raises(node_identity.NodeKeyCorruptError):
        node_identity.get_or_create_node_signing_key()
