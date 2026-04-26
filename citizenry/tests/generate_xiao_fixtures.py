"""Generate gold-master fixtures for XIAO firmware interop tests.

Output: ../../xiao-citizen/tests/fixtures.json
Each fixture has: {name, signing_key (hex), envelope_dict, signable_bytes (hex), signature (hex)}.
The C++ tests load the fixtures and verify they can:
  (a) reconstruct the exact signable_bytes from the envelope_dict
  (b) verify the signature against signing_key.verify_key
"""
import json
import os
from pathlib import Path

import nacl.signing

from citizenry.protocol import Envelope, MessageType, make_envelope


# Stable test keypair so fixtures are reproducible.
TEST_SEED = bytes.fromhex(
    "c0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ff"
)
KEY = nacl.signing.SigningKey(TEST_SEED)
PUBKEY = KEY.verify_key.encode().hex()


def _fixture(name, env: Envelope) -> dict:
    sig_bytes = env.signable_bytes()
    # Full on-the-wire bytes (Envelope.to_bytes()): JSON dump including the
    # `signature` field, sort_keys=True, no whitespace. The dispatcher tests
    # parse this and re-verify against the canonical signable_bytes.
    wire_bytes = env.to_bytes()
    return {
        "name": name,
        "signing_seed_hex": TEST_SEED.hex(),
        "verify_key_hex": PUBKEY,
        "envelope": {
            "version": env.version,
            "type": env.type,
            "sender": env.sender,
            "recipient": env.recipient,
            "timestamp": env.timestamp,
            "ttl": env.ttl,
            "body": env.body,
        },
        "signable_bytes_hex": sig_bytes.hex(),
        "signature_hex": env.signature,
        "wire_hex": wire_bytes.hex(),
    }


def main():
    fixtures = []

    fixtures.append(_fixture(
        "discover_minimal",
        make_envelope(MessageType.DISCOVER, PUBKEY,
                      {"name": "xiao-cam-test", "type": "sensor", "unicast_port": 0},
                      KEY)
    ))

    fixtures.append(_fixture(
        "heartbeat_simple",
        make_envelope(MessageType.HEARTBEAT, PUBKEY,
                      {"name": "xiao-cam-test", "state": "ok", "health": 1.0,
                       "unicast_port": 50000, "uptime": 12.5},
                      KEY)
    ))

    fixtures.append(_fixture(
        "advertise_with_caps",
        make_envelope(MessageType.ADVERTISE, PUBKEY,
                      {"name": "xiao-cam-test", "type": "sensor",
                       "capabilities": ["video_stream", "frame_capture"],
                       "health": 1.0, "state": "ok",
                       "unicast_port": 50000, "has_constitution": False},
                      KEY)
    ))

    fixtures.append(_fixture(
        "propose_frame_capture",
        make_envelope(MessageType.PROPOSE, PUBKEY,
                      {"task": "frame_capture", "task_id": "abc-123",
                       "resolution": [320, 240]},
                      KEY,
                      recipient="ff" * 32)
    ))

    fixtures.append(_fixture(
        "report_with_jpeg_b64",
        make_envelope(MessageType.REPORT, PUBKEY,
                      {"task_id": "abc-123", "result": "success",
                       "frame": "iVBORw0KGgo="},   # tiny base64
                      KEY,
                      recipient="ff" * 32)
    ))

    fixtures.append(_fixture(
        "govern_constitution_v1",
        make_envelope(MessageType.GOVERN, PUBKEY,
                      {"version": 1, "values": ["safety", "energy_aware"],
                       "rules": []},
                      KEY,
                      recipient="ff" * 32)
    ))

    fixtures.append(_fixture(
        "ttl_subsecond",
        make_envelope(MessageType.HEARTBEAT, PUBKEY, {}, KEY, ttl=0.1)
    ))

    fixtures.append(_fixture(
        "nested_body",
        make_envelope(MessageType.HEARTBEAT, PUBKEY,
                      {"a": {"b": {"c": [1, 2, 3]}}, "z": True, "n": None},
                      KEY)
    ))

    # Phase 2 dispatcher fixtures.
    # `discover_from_xiao` mirrors the body the XIAO will emit (name encodes
    # the MAC suffix). `report_govern_ack` is the shape the GOVERN handler
    # will send back to the governor.
    fixtures.append(_fixture(
        "discover_from_xiao",
        make_envelope(MessageType.DISCOVER, PUBKEY,
                      {"name": "xiao-cam-934c", "type": "sensor",
                       "unicast_port": 51404},
                      KEY)
    ))

    fixtures.append(_fixture(
        "heartbeat_from_xiao",
        make_envelope(MessageType.HEARTBEAT, PUBKEY,
                      {"name": "xiao-cam-934c", "state": "ok", "health": 1.0,
                       "unicast_port": 51404, "uptime": 42.125},
                      KEY)
    ))

    fixtures.append(_fixture(
        "advertise_from_xiao",
        make_envelope(MessageType.ADVERTISE, PUBKEY,
                      {"name": "xiao-cam-934c", "type": "sensor",
                       "capabilities": ["video_stream", "frame_capture"],
                       "health": 1.0, "state": "ok",
                       "unicast_port": 51404, "has_constitution": True},
                      KEY,
                      recipient="ee" * 32)
    ))

    fixtures.append(_fixture(
        "report_govern_ack",
        make_envelope(MessageType.REPORT, PUBKEY,
                      {"task": "govern_ack", "result": "success",
                       "constitution_version": 1},
                      KEY,
                      recipient="ee" * 32)
    ))

    out_dir = Path(__file__).resolve().parents[2] / "xiao-citizen" / "tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "fixtures.json"
    out.write_text(json.dumps({"fixtures": fixtures}, indent=2, sort_keys=True))
    print(f"wrote {out} with {len(fixtures)} fixtures")


if __name__ == "__main__":
    main()
