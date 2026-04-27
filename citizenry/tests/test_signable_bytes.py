"""signable_bytes() must produce a deterministic, fixed-precision float format
so the C++ firmware can match it byte-for-byte.
"""
import json
from citizenry.protocol import Envelope


def test_signable_bytes_fixed_3dp_floats():
    env = Envelope(
        version=1, type=1,
        sender="abc123", recipient="*",
        timestamp=1234567890.0,
        ttl=6.0,
        body={"state": "ok"},
    )
    out = env.signable_bytes()
    # Floats must be formatted as %.3f, sorted keys, tight separators
    expected = (
        b'{"body":{"state":"ok"},'
        b'"recipient":"*",'
        b'"sender":"abc123",'
        b'"timestamp":1234567890.000,'
        b'"ttl":6.000,'
        b'"type":1,'
        b'"version":1}'
    )
    assert out == expected, f"got {out!r}\nexp {expected!r}"


def test_signable_bytes_subsecond_timestamp():
    env = Envelope(
        version=1, type=2,
        sender="ff", recipient="ee",
        timestamp=1700000000.123456,    # sub-ms precision in input
        ttl=0.5,
        body={},
    )
    out = env.signable_bytes()
    # 6th decimal must be truncated, ttl 0.5 → 0.500
    expected = (
        b'{"body":{},'
        b'"recipient":"ee",'
        b'"sender":"ff",'
        b'"timestamp":1700000000.123,'
        b'"ttl":0.500,'
        b'"type":2,'
        b'"version":1}'
    )
    assert out == expected, f"got {out!r}\nexp {expected!r}"
