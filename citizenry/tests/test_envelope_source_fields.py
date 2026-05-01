"""source_ip / source_port live on the Envelope dataclass but are NOT signed
and NOT serialized on the wire. They are populated by the transport layer
after a packet is received."""
import json

import pytest
from nacl.signing import SigningKey, VerifyKey

from citizenry.protocol import Envelope


def _baseline_env() -> Envelope:
    return Envelope(
        version=1,
        type=1,
        sender="ab" * 32,
        recipient="*",
        timestamp=1700000000.0,
        ttl=6.0,
        body={"state": "ok"},
    )


def test_source_fields_default_empty():
    e = _baseline_env()
    assert e.source_ip == ""
    assert e.source_port == 0


def test_source_fields_not_in_signable_bytes():
    e = _baseline_env()
    canonical_before = e.signable_bytes()
    e.source_ip = "192.168.1.42"
    e.source_port = 50001
    canonical_after = e.signable_bytes()
    assert canonical_before == canonical_after, (
        "source_ip / source_port leaked into signable_bytes — would break "
        "all existing signatures and cross-language interop"
    )


def test_signature_survives_source_field_population():
    sk = SigningKey.generate()
    e = _baseline_env()
    e.sign(sk)
    sig_before = e.signature
    e.source_ip = "10.0.0.5"
    e.source_port = 51234
    assert e.signature == sig_before
    assert e.verify(sk.verify_key) is True


def test_source_fields_not_in_to_bytes_wire():
    e = _baseline_env()
    e.source_ip = "10.0.0.5"
    e.source_port = 51234
    raw = e.to_bytes()
    decoded = json.loads(raw.decode())
    assert "source_ip" not in decoded, "source_ip leaked onto wire"
    assert "source_port" not in decoded, "source_port leaked onto wire"


def test_from_bytes_yields_default_source_fields():
    """An envelope reconstructed from wire bytes carries empty source fields
    until the transport populates them."""
    e = _baseline_env()
    raw = e.to_bytes()
    e2 = Envelope.from_bytes(raw)
    assert e2.source_ip == ""
    assert e2.source_port == 0
