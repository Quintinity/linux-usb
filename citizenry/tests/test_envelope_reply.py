"""Envelope.reply(payload) constructs a unicast reply with the right destination."""
import time

import pytest
from nacl.signing import SigningKey

from citizenry.protocol import (
    Envelope,
    MessageType,
    PROTOCOL_VERSION,
    TTL_ACCEPT_REJECT,
    make_envelope,
)


def _signed_request_envelope() -> tuple[Envelope, SigningKey]:
    sk = SigningKey.generate()
    env = make_envelope(
        MessageType.PROPOSE,
        sender_pubkey=sk.verify_key.encode().hex(),
        body={"task": "demo"},
        signing_key=sk,
    )
    env.source_ip = "192.168.1.42"
    env.source_port = 50001
    return env, sk


def test_reply_addresses_envelope_to_original_sender():
    req, sk = _signed_request_envelope()
    rep = req.reply(
        msg_type=MessageType.ACCEPT_REJECT,
        sender_pubkey="ff" * 32,
        body={"accept": True, "task_id": "x"},
    )
    assert rep.recipient == req.sender
    assert rep.sender == "ff" * 32
    assert rep.type == int(MessageType.ACCEPT_REJECT)
    assert rep.body == {"accept": True, "task_id": "x"}
    assert rep.version == PROTOCOL_VERSION


def test_reply_default_ttl_matches_message_type():
    req, _ = _signed_request_envelope()
    rep = req.reply(
        msg_type=MessageType.ACCEPT_REJECT,
        sender_pubkey="ff" * 32,
        body={},
    )
    assert rep.ttl == TTL_ACCEPT_REJECT


def test_reply_explicit_ttl_overrides_default():
    req, _ = _signed_request_envelope()
    rep = req.reply(
        msg_type=MessageType.REPORT,
        sender_pubkey="ff" * 32,
        body={},
        ttl=99.0,
    )
    assert rep.ttl == 99.0


def test_destination_addr_returns_source_tuple():
    req, _ = _signed_request_envelope()
    assert req.destination_addr() == ("192.168.1.42", 50001)


def test_reply_unsigned_by_default():
    req, _ = _signed_request_envelope()
    rep = req.reply(
        msg_type=MessageType.ACCEPT_REJECT,
        sender_pubkey="ff" * 32,
        body={},
    )
    assert rep.signature == ""


def test_reply_carries_no_source_fields():
    """A freshly-minted reply has empty source_ip/source_port — those are
    populated by the receiver's transport layer if/when delivered."""
    req, _ = _signed_request_envelope()
    rep = req.reply(
        msg_type=MessageType.ACCEPT_REJECT,
        sender_pubkey="ff" * 32,
        body={},
    )
    assert rep.source_ip == ""
    assert rep.source_port == 0


def test_reply_raises_when_source_unknown():
    req = Envelope(
        version=1, type=int(MessageType.PROPOSE),
        sender="ab" * 32, recipient="*",
        timestamp=time.time(), ttl=10.0, body={},
    )
    with pytest.raises(ValueError, match="source"):
        req.reply(
            msg_type=MessageType.ACCEPT_REJECT,
            sender_pubkey="ff" * 32,
            body={},
        )


def test_destination_addr_raises_when_source_unknown():
    req = Envelope(
        version=1, type=int(MessageType.PROPOSE),
        sender="ab" * 32, recipient="*",
        timestamp=time.time(), ttl=10.0, body={},
    )
    with pytest.raises(ValueError, match="source"):
        req.destination_addr()
