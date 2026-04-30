"""ConstitutionView exposes the v2 fields added in Constitution."""
import json
from pathlib import Path

import pytest

from citizenry.governance import load_constitution


def test_view_exposes_v2_fields(tmp_path):
    payload = {
        "version": 2,
        "governor_pubkey": "",
        "authority_pubkey": "ab" * 32,
        "node_key_version": 7,
        "articles": [],
        "laws": [],
        "servo_limits": {},
        "tool_manifest_pinning": {"bus-mcp": "sha256:abc"},
        "policy_pinning": {"smolvla-pickplace-v3": "hf:rev:def"},
        "embassy_topics": {"opcua_namespace": "ns/q/cell1"},
        "compliance_artefacts": {"aibom_url": "https://x/aibom.cdx.json"},
        "signature": "",
    }
    p = tmp_path / "c.json"
    p.write_text(json.dumps(payload))
    view = load_constitution(p)
    assert view.authority_pubkey == "ab" * 32
    assert view.node_key_version == 7
    assert view.tool_manifest_pinning == {"bus-mcp": "sha256:abc"}
    assert view.policy_pinning == {"smolvla-pickplace-v3": "hf:rev:def"}
    assert view.embassy_topics == {"opcua_namespace": "ns/q/cell1"}
    assert view.compliance_artefacts == {"aibom_url": "https://x/aibom.cdx.json"}


def test_view_v1_constitution_returns_empty_v2_fields(tmp_path):
    """A v1 Constitution loaded through the view yields empty v2 dicts."""
    payload = {
        "version": 1,
        "governor_pubkey": "ef" * 32,
        "articles": [],
        "laws": [],
        "servo_limits": {},
        "signature": "",
    }
    p = tmp_path / "v1.json"
    p.write_text(json.dumps(payload))
    view = load_constitution(p)
    assert view.authority_pubkey == ""
    assert view.node_key_version == 1
    assert view.tool_manifest_pinning == {}
    assert view.policy_pinning == {}
    assert view.embassy_topics == {}
    assert view.compliance_artefacts == {}
