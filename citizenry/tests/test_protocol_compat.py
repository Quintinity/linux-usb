"""Tests for v1.5 backward compatibility.

v2.0 adds new body schemas to existing message types. v1.5 citizens
must not crash when receiving v2.0 messages.
"""

import pytest
import nacl.signing

from citizenry.protocol import (
    Envelope, make_envelope, MessageType, PROTOCOL_VERSION,
)
from citizenry.identity import generate_keypair, pubkey_hex


class TestProtocolCompat:
    """Verify v2.0 messages are valid v1.5 envelopes."""

    def setup_method(self):
        self.key = generate_keypair()
        self.pubkey = pubkey_hex(self.key)

    def test_task_propose_is_valid_envelope(self):
        """A v2.0 task PROPOSE is a valid PROPOSE envelope."""
        env = make_envelope(
            MessageType.PROPOSE,
            self.pubkey,
            {
                "task": "pick_and_place",
                "task_id": "abc123",
                "priority": 0.7,
                "required_capabilities": ["6dof_arm"],
                "required_skills": ["basic_grasp"],
                "params": {"object": "red_block"},
            },
            self.key,
        )
        assert env.type == int(MessageType.PROPOSE)
        assert not env.is_expired()
        # Roundtrip through bytes
        data = env.to_bytes()
        env2 = Envelope.from_bytes(data)
        assert env2.body["task"] == "pick_and_place"
        assert env2.body["task_id"] == "abc123"

    def test_bid_accept_is_valid_envelope(self):
        env = make_envelope(
            MessageType.ACCEPT_REJECT,
            self.pubkey,
            {
                "accepted": True,
                "task_id": "abc123",
                "bid": {"skill_level": 3, "load": 0.12, "score": 0.87},
            },
            self.key,
        )
        data = env.to_bytes()
        env2 = Envelope.from_bytes(data)
        assert env2.body["accepted"] is True

    def test_warning_report_is_valid_envelope(self):
        env = make_envelope(
            MessageType.REPORT,
            self.pubkey,
            {
                "type": "warning",
                "severity": "critical",
                "detail": "voltage_collapse",
                "motor": "elbow_flex",
                "value": 5.2,
                "threshold": 6.0,
            },
            self.key,
        )
        data = env.to_bytes()
        env2 = Envelope.from_bytes(data)
        assert env2.body["type"] == "warning"

    def test_immune_share_is_valid_envelope(self):
        env = make_envelope(
            MessageType.REPORT,
            self.pubkey,
            {
                "type": "immune_share",
                "patterns": [
                    {"pattern_type": "voltage_collapse", "severity": "critical"},
                ],
            },
            self.key,
        )
        data = env.to_bytes()
        env2 = Envelope.from_bytes(data)
        assert env2.body["type"] == "immune_share"

    def test_genome_govern_is_valid_envelope(self):
        env = make_envelope(
            MessageType.GOVERN,
            self.pubkey,
            {
                "type": "genome",
                "genome": {"citizen_name": "test", "version": 1},
            },
            self.key,
        )
        data = env.to_bytes()
        env2 = Envelope.from_bytes(data)
        assert env2.body["type"] == "genome"

    def test_symbiosis_propose_is_valid_envelope(self):
        env = make_envelope(
            MessageType.PROPOSE,
            self.pubkey,
            {
                "task": "symbiosis_propose",
                "contract_id": "contract123",
                "provider_cap": "video_stream",
                "consumer_cap": "6dof_arm",
                "composite": "visual_pick_and_place",
                "health_check_hz": 1.0,
            },
            self.key,
        )
        data = env.to_bytes()
        env2 = Envelope.from_bytes(data)
        assert env2.body["task"] == "symbiosis_propose"

    def test_v15_teleop_still_works(self):
        """v1.5 teleop PROPOSE still roundtrips correctly."""
        env = make_envelope(
            MessageType.PROPOSE,
            self.pubkey,
            {"task": "teleop_frame", "positions": {"shoulder_pan": 2048}},
            self.key,
            ttl=0.1,
        )
        data = env.to_bytes()
        env2 = Envelope.from_bytes(data)
        assert env2.body["task"] == "teleop_frame"
        assert env2.body["positions"]["shoulder_pan"] == 2048

    def test_v15_heartbeat_still_works(self):
        env = make_envelope(
            MessageType.HEARTBEAT,
            self.pubkey,
            {"name": "test", "state": "idle", "health": 1.0, "unicast_port": 9000},
            self.key,
        )
        data = env.to_bytes()
        env2 = Envelope.from_bytes(data)
        assert env2.body["name"] == "test"

    def test_signature_verification(self):
        """All v2.0 messages must be properly signed."""
        env = make_envelope(
            MessageType.REPORT,
            self.pubkey,
            {"type": "immune_share", "patterns": []},
            self.key,
        )
        vk = nacl.signing.VerifyKey(bytes.fromhex(self.pubkey))
        assert env.verify(vk)

    def test_unknown_body_fields_ignored(self):
        """A v1.5 citizen can safely ignore unknown body fields."""
        env = make_envelope(
            MessageType.HEARTBEAT,
            self.pubkey,
            {
                "name": "test",
                "state": "idle",
                "health": 1.0,
                "unicast_port": 9000,
                # v2.0 addition — v1.5 should ignore these
                "warnings": [{"severity": "info", "detail": "test"}],
                "contracts": ["contract123"],
                "xp": {"basic_grasp": 50},
            },
            self.key,
        )
        data = env.to_bytes()
        env2 = Envelope.from_bytes(data)
        # v1.5 would just read name/state/health/unicast_port
        assert env2.body["name"] == "test"
        assert env2.body["state"] == "idle"
