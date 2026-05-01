"""The 7-Message Citizenry Protocol.

Every interaction between citizens reduces to one of seven message types.
All JSON, all signed, all with TTL.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Any

import nacl.signing
import nacl.encoding


PROTOCOL_VERSION = 1
MULTICAST_GROUP = "239.67.84.90"  # "CTZO" in ASCII — citizenry
MULTICAST_PORT = 7770


class MessageType(IntEnum):
    HEARTBEAT = 1       # "I exist, here is my state"
    DISCOVER = 2        # "Who is out there?"
    ADVERTISE = 3       # "Here is what I can do"
    PROPOSE = 4         # "I think we should do X"
    ACCEPT_REJECT = 5   # "I will/won't do X"
    REPORT = 6          # "Here is what happened"
    GOVERN = 7          # "New policy from the governor"


# Default TTLs in seconds
TTL_HEARTBEAT = 6.0       # 3x heartbeat interval
TTL_DISCOVER = 5.0
TTL_ADVERTISE = 30.0
TTL_PROPOSE = 10.0
TTL_ACCEPT_REJECT = 10.0
TTL_REPORT = 60.0
TTL_GOVERN = 3600.0
TTL_TELEOP = 0.1         # Teleop commands expire fast — 100ms


@dataclass
class Envelope:
    """Wire format for every citizenry message."""
    version: int
    type: int
    sender: str           # Hex-encoded public key
    recipient: str        # Hex-encoded public key, or "*" for broadcast
    timestamp: float
    ttl: float
    body: dict
    signature: str = ""   # Hex-encoded Ed25519 signature

    # ---- transport-only metadata (NOT signable, NOT serialised on wire) ----
    # Populated by transport.py after datagram_received(); empty otherwise.
    # Excluded from signable_bytes() so existing signatures remain valid, and
    # excluded from to_bytes() so receivers don't see spurious fields.
    source_ip: str = ""
    source_port: int = 0

    _NON_WIRE_FIELDS = ("source_ip", "source_port")

    def signable_bytes(self) -> bytes:
        """Canonical bytes for signing — sorted keys, %.3f floats, tight separators.

        Format is locked down so the XIAO C++ firmware can produce byte-identical
        signables. Do not change without updating tests/test_signable_bytes.py and
        the C++ implementation in xiao-citizen/citizenry_envelope.cpp.

        source_ip / source_port are deliberately excluded.
        """
        d = {
            "version": self.version,
            "type": self.type,
            "sender": self.sender,
            "recipient": self.recipient,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "body": self.body,
        }
        return _canonical_dumps(d).encode()

    def sign(self, signing_key: nacl.signing.SigningKey) -> None:
        signed = signing_key.sign(self.signable_bytes())
        self.signature = signed.signature.hex()

    def verify(self, verify_key: nacl.signing.VerifyKey) -> bool:
        try:
            verify_key.verify(self.signable_bytes(), bytes.fromhex(self.signature))
            return True
        except nacl.exceptions.BadSignatureError:
            return False

    def is_expired(self) -> bool:
        return time.time() > (self.timestamp + self.ttl)

    def destination_addr(self) -> tuple[str, int]:
        """Return ``(source_ip, source_port)`` — where a reply should be sent.

        Raises ``ValueError`` if the envelope did not come off the wire (source
        not populated). Used by ``reply()`` and by handlers that mint their own
        unicast responses.
        """
        if not self.source_ip or self.source_port == 0:
            raise ValueError(
                "Envelope has no transport source — cannot derive a reply destination. "
                "destination_addr()/reply() can only be called on envelopes received via transport.py."
            )
        return (self.source_ip, self.source_port)

    def reply(
        self,
        msg_type: "MessageType",
        sender_pubkey: str,
        body: dict,
        ttl: float | None = None,
    ) -> "Envelope":
        """Construct an unsigned unicast reply addressed to the original sender.

        The returned envelope has ``recipient == self.sender``, default TTL
        derived from ``msg_type``, and an empty signature — caller signs it
        with their own role key. The caller is responsible for delivering it
        via ``UnicastTransport.send(rep, self.destination_addr())``.
        """
        # Validate source is known — fail fast instead of sending into the void.
        self.destination_addr()
        default_ttls = {
            MessageType.HEARTBEAT: TTL_HEARTBEAT,
            MessageType.DISCOVER: TTL_DISCOVER,
            MessageType.ADVERTISE: TTL_ADVERTISE,
            MessageType.PROPOSE: TTL_PROPOSE,
            MessageType.ACCEPT_REJECT: TTL_ACCEPT_REJECT,
            MessageType.REPORT: TTL_REPORT,
            MessageType.GOVERN: TTL_GOVERN,
        }
        return Envelope(
            version=PROTOCOL_VERSION,
            type=int(msg_type),
            sender=sender_pubkey,
            recipient=self.sender,
            timestamp=time.time(),
            ttl=ttl if ttl is not None else default_ttls.get(msg_type, 10.0),
            body=body,
        )

    def to_bytes(self) -> bytes:
        d = asdict(self)
        for k in self._NON_WIRE_FIELDS:
            d.pop(k, None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> "Envelope":
        d = json.loads(data)
        # Ignore any incoming source_ip/source_port — they're transport-local;
        # the receiving transport will populate them from the actual UDP addr.
        for k in cls._NON_WIRE_FIELDS:
            d.pop(k, None)
        return cls(**d)


def _canonical_dumps(obj) -> str:
    """Sorted-keys, %.3f floats, no whitespace. Recursive."""
    if isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: kv[0])
        return "{" + ",".join(f"{_canonical_dumps(k)}:{_canonical_dumps(v)}" for k, v in items) + "}"
    if isinstance(obj, list):
        return "[" + ",".join(_canonical_dumps(v) for v in obj) + "]"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if obj is None:
        return "null"
    if isinstance(obj, float):
        return f"{obj:.3f}"
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    raise TypeError(f"Unsupported type for canonical JSON: {type(obj)}")


def make_envelope(
    msg_type: MessageType,
    sender_pubkey: str,
    body: dict,
    signing_key: nacl.signing.SigningKey,
    recipient: str = "*",
    ttl: float | None = None,
) -> Envelope:
    """Create a signed envelope."""
    default_ttls = {
        MessageType.HEARTBEAT: TTL_HEARTBEAT,
        MessageType.DISCOVER: TTL_DISCOVER,
        MessageType.ADVERTISE: TTL_ADVERTISE,
        MessageType.PROPOSE: TTL_PROPOSE,
        MessageType.ACCEPT_REJECT: TTL_ACCEPT_REJECT,
        MessageType.REPORT: TTL_REPORT,
        MessageType.GOVERN: TTL_GOVERN,
    }
    if ttl is None:
        ttl = default_ttls.get(msg_type, 10.0)

    env = Envelope(
        version=PROTOCOL_VERSION,
        type=int(msg_type),
        sender=sender_pubkey,
        recipient=recipient,
        timestamp=time.time(),
        ttl=ttl,
        body=body,
    )
    env.sign(signing_key)
    return env
