"""GOVERN body type: pin_policy — formal provenance-bearing policy pin."""
import time

from citizenry.citizen import Citizen
from citizenry.protocol import Envelope, MessageType


def _make_envelope(body: dict) -> Envelope:
    return Envelope(
        version=1,
        type=int(MessageType.GOVERN),
        sender="ab" * 32,
        recipient="*",
        timestamp=time.time(),
        ttl=3600.0,
        body=body,
        signature="cd" * 64,
    )


def _isolate(monkeypatch, tmp_path):
    """Redirect ~/.citizenry to tmp_path so per-citizen keys don't leak.

    Module-level path constants in `identity` and `node_identity` are
    captured at import time, so `monkeypatch.setenv("HOME", ...)` alone
    is a no-op against them.
    """
    citizenry_dir = tmp_path / ".citizenry"
    citizenry_dir.mkdir()
    from citizenry import identity as identity_module
    from citizenry import node_identity as node_module
    monkeypatch.setattr(identity_module, "IDENTITY_DIR", citizenry_dir)
    monkeypatch.setattr(node_module, "IDENTITY_DIR", citizenry_dir)


def test_handle_govern_pin_policy_sets_attribute(monkeypatch, tmp_path):
    """Receiving GOVERN(pin_policy, ...) records the pin on the citizen."""
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-pin-policy", citizen_type="test", capabilities=[])
    env = _make_envelope({
        "type": "pin_policy",
        "policy_id": "smolvla-pickplace-v3",
        "hf_revision_sha": "0123456789abcdef",
        "aibom_url": "https://example.org/aibom.cdx.json",
        "rekor_log_index": 42,
    })
    c._handle_govern(env, addr=("127.0.0.1", 0))
    assert hasattr(c, "policy_pinning")
    assert c.policy_pinning == {
        "smolvla-pickplace-v3": {
            "hf_revision_sha": "0123456789abcdef",
            "aibom_url": "https://example.org/aibom.cdx.json",
            "rekor_log_index": 42,
        }
    }


def test_pin_policy_replaces_existing_pin(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-pin-policy-replace", citizen_type="test", capabilities=[])
    c._handle_govern(_make_envelope({
        "type": "pin_policy",
        "policy_id": "x",
        "hf_revision_sha": "1234567",  # valid 7-char short SHA
        "aibom_url": "u1",
        "rekor_log_index": 1,
    }), addr=("127.0.0.1", 0))
    c._handle_govern(_make_envelope({
        "type": "pin_policy",
        "policy_id": "x",
        "hf_revision_sha": "abcdef0",
        "aibom_url": "u2",
        "rekor_log_index": 2,
    }), addr=("127.0.0.1", 0))
    assert c.policy_pinning["x"]["hf_revision_sha"] == "abcdef0"
    assert c.policy_pinning["x"]["rekor_log_index"] == 2


def test_pin_policy_missing_fields_logged_not_raised(monkeypatch, tmp_path):
    """Malformed pin_policy is logged but does not raise."""
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-pin-policy-malformed", citizen_type="test", capabilities=[])
    # Missing hf_revision_sha — must not crash
    c._handle_govern(_make_envelope({
        "type": "pin_policy",
        "policy_id": "x",
    }), addr=("127.0.0.1", 0))
    # nothing pinned
    assert c.policy_pinning.get("x", {}).get("hf_revision_sha", "") == ""


def test_pin_policy_rejects_short_hf_rev(monkeypatch, tmp_path):
    """hf_revision_sha shorter than 7 chars (less than git's abbreviated SHA) is rejected."""
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-pin-policy-short", citizen_type="test", capabilities=[])
    c._handle_govern(_make_envelope({
        "type": "pin_policy",
        "policy_id": "x",
        "hf_revision_sha": "abc",  # 3 chars, too short
    }), addr=("127.0.0.1", 0))
    assert "x" not in c.policy_pinning


def test_pin_policy_rejects_non_hex_hf_rev(monkeypatch, tmp_path):
    """hf_revision_sha must be hex even if length is acceptable."""
    _isolate(monkeypatch, tmp_path)
    c = Citizen(name="test-pin-policy-nonhex", citizen_type="test", capabilities=[])
    c._handle_govern(_make_envelope({
        "type": "pin_policy",
        "policy_id": "x",
        "hf_revision_sha": "g" * 12,  # valid length, invalid hex
    }), addr=("127.0.0.1", 0))
    assert "x" not in c.policy_pinning
