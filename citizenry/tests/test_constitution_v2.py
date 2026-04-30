"""Constitution v2 schema and v1 backward-compat round-trip."""
import json
from pathlib import Path

import pytest
from nacl.signing import SigningKey

from citizenry.constitution import Constitution, Article, Law, ServoLimits


FIXTURES = Path(__file__).parent / "fixtures"


def test_v2_default_fields():
    c = Constitution()
    assert c.version == 2
    assert c.authority_pubkey == ""
    assert c.node_key_version == 1
    assert c.tool_manifest_pinning == {}
    assert c.policy_pinning == {}
    assert c.embassy_topics == {}
    assert c.compliance_artefacts == {}


def test_v2_to_dict_includes_new_fields():
    c = Constitution()
    d = c.to_dict()
    for k in (
        "version",
        "authority_pubkey",
        "node_key_version",
        "tool_manifest_pinning",
        "policy_pinning",
        "embassy_topics",
        "compliance_artefacts",
        "governor_pubkey",
        "articles",
        "laws",
        "servo_limits",
        "signature",
    ):
        assert k in d, f"missing key {k!r} in v2 to_dict()"


def test_v1_dict_round_trips_into_v2():
    raw = (FIXTURES / "constitution_v1_sample.json").read_text()
    v1_dict = json.loads(raw)
    c = Constitution.from_dict(v1_dict)
    assert c.version == 1
    assert c.governor_pubkey == v1_dict["governor_pubkey"]
    # New v2 fields default cleanly
    assert c.authority_pubkey == ""
    assert c.node_key_version == 1
    assert c.tool_manifest_pinning == {}
    # Round-trip back to dict and back to object preserves data
    again = Constitution.from_dict(c.to_dict())
    assert again.version == 1
    assert again.governor_pubkey == v1_dict["governor_pubkey"]


def test_v2_from_dict_accepts_full_payload():
    payload = {
        "version": 2,
        "governor_pubkey": "",
        "authority_pubkey": "ab" * 32,
        "node_key_version": 3,
        "articles": [],
        "laws": [],
        "servo_limits": {},
        "tool_manifest_pinning": {"bus-mcp": "sha256:abc"},
        "policy_pinning": {"smolvla-pickplace-v3": "hf:rev:def"},
        "embassy_topics": {"opcua_namespace": "ns/quintinity/cell1"},
        "compliance_artefacts": {"aibom_url": "https://example/aibom.cdx.json"},
        "signature": "",
    }
    c = Constitution.from_dict(payload)
    assert c.version == 2
    assert c.authority_pubkey == "ab" * 32
    assert c.node_key_version == 3
    assert c.tool_manifest_pinning == {"bus-mcp": "sha256:abc"}
    assert c.policy_pinning == {"smolvla-pickplace-v3": "hf:rev:def"}
    assert c.embassy_topics == {"opcua_namespace": "ns/quintinity/cell1"}
    assert c.compliance_artefacts == {"aibom_url": "https://example/aibom.cdx.json"}
