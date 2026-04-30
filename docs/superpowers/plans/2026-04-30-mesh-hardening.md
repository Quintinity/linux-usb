# Mesh Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close two longstanding mesh-layer smells from the umbrella spec: (a) unicast reply-port plumbing is incomplete — handlers receive `(envelope, (ip, port))` tuples instead of an envelope that already carries the source, and there is no clean way to mint a unicast reply (smell #4); (b) the marketplace's co-location bonus does not honour the `_stale_node_pubkeys` set populated by `GOVERN(rotate_node_key)` from Sub-1 Task 6 (smell #5). Add `source_ip`/`source_port` fields to `Envelope` as **non-signable** metadata so existing signatures stay valid, add a `reply()` helper, plumb the fields through `transport.py`, mirror the change in the XIAO C++ envelope while keeping `signable_bytes()` byte-identical with Python, and gate the marketplace co-location bonus behind a stale-key check.

**Architecture:** Strictly additive change to `citizenry.protocol.Envelope`. Two new fields (`source_ip: str`, `source_port: int`) carry transport-layer provenance after a packet has been received. They are deliberately **excluded from `signable_bytes()`** and from the `to_bytes()` wire payload — they exist only on Python `Envelope` instances that came off the wire, populated by the transport layer right after `from_bytes()`. The C++ side mirrors this: the struct gains the fields, but `canonical_signable_bytes()` and `envelope_to_wire()` continue to emit the same 7 / 8 keys they always have. This is what keeps existing Ed25519 signatures (and the cross-language interop fixtures in `xiao-citizen/tests/fixtures.json`) valid byte-for-byte. Handlers gain a populated `env.source_ip` / `env.source_port`; the legacy `(env, addr)` tuple is preserved for one release as a `(env, (env.source_ip, env.source_port))` shim so we don't break every handler in one commit. The marketplace fix wires `compute_bid_score` to consult a caller-supplied `stale_node_pubkeys: set[str]`; if the prospective bidder's `node_pubkey` is in that set, the co-location bonus is suppressed (returns base score only). The set is populated on each citizen by Sub-1 Task 6's `_stale_node_pubkeys` attribute and is cleared when a fresh `genome` GOVERN re-attests the new pubkey.

**Tech Stack:** Python 3.12, `pynacl` (already a dep), `dataclasses`, `pytest`. C++17 with vendored `nlohmann/json` for host tests, `ArduinoJson` v7 on firmware. No new third-party dependencies.

**References:**
- Architecture spec: `docs/superpowers/specs/2026-04-30-citizenry-physical-ai-architecture-design.md` §5.2 smell #4 + smell #5, §10 sub-2.
- Sub-1 plan (template + Task 6 dependency): `docs/superpowers/plans/2026-04-30-constitution-v2-identity.md`.
- Existing code under modification: `citizenry/protocol.py` (Envelope dataclass + `signable_bytes`), `citizenry/transport.py` (Multicast/UnicastTransport), `citizenry/marketplace.py:115-143` (`compute_bid_score`), `citizenry/citizen.py:484-512` (`_on_message` dispatch + handler signatures), `xiao-citizen/citizenry_envelope.{h,cpp}`, `xiao-citizen/tests/test_canonical_json.cpp`, `xiao-citizen/tests/test_ed25519_interop.cpp`, `xiao-citizen/tests/fixtures.json`.
- Cross-language signature contract: `citizenry/tests/test_signable_bytes.py` (Python side) + `xiao-citizen/tests/test_canonical_json.cpp` (C++ side).

**Out of scope:** Refactoring all handlers off the `(env, addr)` tuple shim — that's a follow-up sweep. Replacing the marketplace's pull-based bonus weighting with a pushed-genome model — also follow-up. Constitution `node_key_version` enforcement at envelope verify time (caller-side concern, planned for Sub-4 Council Gateway).

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `citizenry/protocol.py` | modify | Add `source_ip`/`source_port` fields (non-signable, non-wire); add `Envelope.reply(payload, ttl=None) -> Envelope` helper |
| `citizenry/transport.py` | modify | `_MulticastProtocol.datagram_received` populates `env.source_ip`/`source_port` from `addr` before invoking `on_message` |
| `citizenry/marketplace.py` | modify | `compute_bid_score(...)` accepts `stale_node_pubkeys: set[str] \| None`; suppresses `co_location_bonus` if `bidder_node_pubkey` is in the set |
| `citizenry/tests/test_envelope_source_fields.py` | **create** | Source fields default empty, are not in `signable_bytes()`, are not in `to_bytes()` wire output, signatures still verify |
| `citizenry/tests/test_envelope_reply.py` | **create** | `reply()` returns an envelope addressed to `env.sender`, with `recipient=env.sender`, correct destination addr |
| `citizenry/tests/test_transport_source_plumbing.py` | **create** | End-to-end: a unicast packet arrives, the handler sees a populated `env.source_ip`/`source_port` |
| `citizenry/tests/test_marketplace_stale_node_pubkeys.py` | **create** | `compute_bid_score` honours the stale set: bonus applied normally / suppressed when stale |
| `xiao-citizen/citizenry_envelope.h` | modify | Add `std::string source_ip`; `int source_port = 0;` to `Envelope`. NOT touched by `canonical_signable_bytes` / `envelope_to_wire` |
| `xiao-citizen/citizenry_envelope.cpp` | modify | No-op for canonical/wire emit (deliberate); explicit comment that source fields are local-only metadata |
| `xiao-citizen/tests/test_canonical_json.cpp` | modify (light) | Construct an envelope with non-empty `source_ip`/`source_port`, assert canonical bytes match the existing fixture (proves they're excluded) |

10 files (4 created tests, 5 modified, 1 lightly extended C++ test). No file under modification is large enough to warrant restructuring.

---

## Conventions

- **Test paths**: Python under `citizenry/tests/`. Run with `pytest`.
- **Run tests**: `cd ~/linux-usb && source ~/lerobot-env/bin/activate && pytest citizenry/tests/<test>.py -v` (Surface; on Pi/Jetson the venv is the same path).
- **C++ tests**: `cd ~/linux-usb/xiao-citizen/tests && make run` builds and runs `test_canonical_json` + `test_ed25519_interop` + `test_dispatch` + `test_messages` + `test_neighbor` against host nlohmann/json. Sub-2 must keep all five green.
- **Commits**: small, one task per commit, message format `citizenry(mesh-hardening): <task summary>`. Always `git add` explicit paths — never `git add -A` (the working tree may have unrelated in-progress changes).
- **Backward-compatible signature contract**: every change must round-trip every fixture in `xiao-citizen/tests/fixtures.json` byte-for-byte. The cross-language test is the authority — any drift fails CI.
- **Handler shim**: existing handlers continue to receive `(env, addr)`; `addr` is always `(env.source_ip, env.source_port)` after Task 2. Do **not** rip out the `addr` parameter in this plan — that's a separate sweep.

---

## Task 1: Add `source_ip` / `source_port` to `Envelope` (non-signable, non-wire)

**Files:**
- Modify: `citizenry/protocol.py:43-93` (`Envelope` dataclass)
- Test: `citizenry/tests/test_envelope_source_fields.py` (create)

- [ ] **Step 1: Write the failing tests for source fields**

Create `citizenry/tests/test_envelope_source_fields.py`:

```python
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
```

- [ ] **Step 2: Run the tests, confirm they fail**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_envelope_source_fields.py -v
```

Expected: tests fail with `AttributeError: 'Envelope' object has no attribute 'source_ip'`. The `to_bytes` / `from_bytes` tests fail similarly because `asdict` includes any new dataclass field by default — that's the whole point of why we explicitly exclude them.

- [ ] **Step 3: Add the fields and override `to_bytes`/`from_bytes` to exclude them**

In `citizenry/protocol.py`, modify the `Envelope` dataclass. Replace the existing class block (lines 43-93) with:

```python
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

    # ---- transport-only metadata (NOT signable, NOT serialised on the wire) ----
    # Populated by transport.py after datagram_received(); empty otherwise.
    # Excluded from signable_bytes() so existing signatures remain valid, and
    # excluded from to_bytes() so receivers don't see spurious fields.
    source_ip: str = ""
    source_port: int = 0

    # The two transport-only fields that to_bytes() / signable_bytes() must skip.
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
```

- [ ] **Step 4: Run the tests, confirm they pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_envelope_source_fields.py \
            citizenry/tests/test_signable_bytes.py -v
```

Expected: 5 new tests PASS, the 2 pre-existing `test_signable_bytes.py` tests still PASS (regression check — proves the canonical bytes formula is unchanged).

- [ ] **Step 5: Run the broader citizenry test suite to confirm no regression**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/ -k "envelope or protocol or signable or wire" -v --no-header
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/protocol.py \
             citizenry/tests/test_envelope_source_fields.py \
  && git commit -m "$(cat <<'EOF'
citizenry(mesh-hardening): Envelope.source_ip/source_port — non-signable, non-wire

- Two new dataclass fields default to "" / 0
- signable_bytes() unchanged (still 7 keys, byte-identical to XIAO C++)
- to_bytes() pops source_ip/source_port before serialising
- from_bytes() drops any incoming source_ip/source_port (defensive)
- Existing Ed25519 signatures verify after population
- 5 tests in test_envelope_source_fields.py
- test_signable_bytes.py regression check still green

Spec: docs/superpowers/specs/2026-04-30-citizenry-physical-ai-architecture-design.md §5.2 smell #4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Plumb `source_ip` / `source_port` through `transport.py`

**Files:**
- Modify: `citizenry/transport.py:77-86` (`_MulticastProtocol.datagram_received`)
- Test: `citizenry/tests/test_transport_source_plumbing.py` (create)

The transport's job: after a packet arrives, populate the envelope's source fields from the actual UDP `addr` tuple before invoking `on_message`. The legacy `(env, addr)` callback contract is preserved — `addr` simply equals `(env.source_ip, env.source_port)` from now on.

- [ ] **Step 1: Write the failing transport test**

Create `citizenry/tests/test_transport_source_plumbing.py`:

```python
"""Transport populates envelope.source_ip / source_port from the UDP addr."""
import asyncio

import pytest
from nacl.signing import SigningKey

from citizenry.protocol import Envelope, MessageType, make_envelope
from citizenry.transport import UnicastTransport


@pytest.mark.asyncio
async def test_unicast_handler_sees_populated_source_fields():
    received: list[Envelope] = []

    def on_message(env: Envelope, addr: tuple):
        # addr must equal (env.source_ip, env.source_port) — single source of truth
        assert env.source_ip == addr[0]
        assert env.source_port == addr[1]
        received.append(env)

    rx = UnicastTransport(on_message)
    tx = UnicastTransport(lambda e, a: None)
    loop = asyncio.get_running_loop()
    await rx.start(loop)
    await tx.start(loop)

    sk = SigningKey.generate()
    env = make_envelope(
        MessageType.HEARTBEAT,
        sender_pubkey=sk.verify_key.encode().hex(),
        body={"state": "ok"},
        signing_key=sk,
    )
    tx.send(env, ("127.0.0.1", rx.bound_port))

    # Pump the loop until the message is delivered
    for _ in range(50):
        await asyncio.sleep(0.01)
        if received:
            break

    rx.close()
    tx.close()

    assert len(received) == 1, "no message received"
    got = received[0]
    assert got.source_ip in ("127.0.0.1", "::ffff:127.0.0.1")
    assert got.source_port == tx.bound_port
    # Crucially: signature still verifies after the transport populated source fields
    assert got.verify(sk.verify_key) is True


@pytest.mark.asyncio
async def test_multicast_packet_carries_no_source_fields_into_signable():
    """Regression: source_ip/source_port set by the transport must not break
    the signature on a multicast envelope."""
    sk = SigningKey.generate()
    env = make_envelope(
        MessageType.HEARTBEAT,
        sender_pubkey=sk.verify_key.encode().hex(),
        body={"state": "ok"},
        signing_key=sk,
    )
    # Simulate what transport will do
    env.source_ip = "192.168.1.99"
    env.source_port = 50111
    assert env.verify(sk.verify_key) is True
```

You will likely need `pytest-asyncio`. If not already configured for this repo, add `pytestmark = pytest.mark.asyncio` at module top OR a tiny `conftest.py` snippet:

```python
# citizenry/tests/conftest.py — already exists; if it does not, create with:
import pytest_asyncio  # noqa: F401  (registers the asyncio fixture)
```

(Skip creating `conftest.py` if one already exists — check first with `ls citizenry/tests/conftest.py`.)

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_transport_source_plumbing.py -v
```

Expected: assertion fails — `env.source_ip == ""`, but `addr[0] == "127.0.0.1"`.

- [ ] **Step 3: Plumb the source fields in the transport layer**

In `citizenry/transport.py`, modify `_MulticastProtocol.datagram_received`:

```python
class _MulticastProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_message: Callable[[Envelope, tuple], None]):
        self.on_message = on_message

    def datagram_received(self, data: bytes, addr: tuple):
        try:
            env = Envelope.from_bytes(data)
            # Populate transport-layer provenance before invoking the handler.
            # addr is always (host, port) for IPv4; IPv6 returns 4-tuple, take [0:2].
            env.source_ip = addr[0]
            env.source_port = addr[1]
            self.on_message(env, addr)
        except Exception:
            pass  # Drop malformed packets silently
```

(Single 2-line addition between `from_bytes` and `on_message`. Both `MulticastTransport` and `UnicastTransport` use the same protocol class — one fix covers both.)

- [ ] **Step 4: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_transport_source_plumbing.py \
            citizenry/tests/test_envelope_source_fields.py -v
```

Expected: 2 new + 5 (Task 1) tests PASS.

- [ ] **Step 5: Run the full mesh / transport test suite to confirm no regression**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/ -k "transport or multicast or mesh or neighbor" -v --no-header
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/transport.py \
             citizenry/tests/test_transport_source_plumbing.py \
  && git commit -m "$(cat <<'EOF'
citizenry(mesh-hardening): transport populates Envelope.source_ip/source_port

- _MulticastProtocol.datagram_received writes addr[0]/addr[1] onto env
  before invoking on_message — handlers now receive a populated Envelope
- Legacy (env, addr) tuple shim preserved (addr == (source_ip, source_port))
- Both MulticastTransport and UnicastTransport benefit (shared protocol class)
- 2 tests covering populated handler view + signature-still-verifies regression

Spec: §5.2 smell #4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `Envelope.reply(payload, ...)` helper

**Files:**
- Modify: `citizenry/protocol.py` (add `reply()` method on `Envelope`)
- Test: `citizenry/tests/test_envelope_reply.py` (create)

`reply()` is the convenience that closes the loop: a handler receives a populated envelope, calls `env.reply({...})` to mint a unicast response addressed to the sender, then hands it (plus `(env.source_ip, env.source_port)`) to its UnicastTransport. The helper is **un-signed** on return — caller signs with their own role key. The helper picks an appropriate `recipient` and default `ttl` from the message type.

- [ ] **Step 1: Write the failing tests**

Create `citizenry/tests/test_envelope_reply.py`:

```python
"""Envelope.reply(payload) constructs a unicast reply with the right destination."""
import time

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
    # Pretend the transport populated source fields
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


def test_reply_destination_addr_matches_original_source():
    req, _ = _signed_request_envelope()
    rep = req.reply(
        msg_type=MessageType.ACCEPT_REJECT,
        sender_pubkey="ff" * 32,
        body={},
    )
    # The helper exposes the destination tuple the caller hands to UnicastTransport.send().
    assert rep.destination_addr() == ("192.168.1.42", 50001)


def test_reply_unsigned_by_default():
    req, _ = _signed_request_envelope()
    rep = req.reply(
        msg_type=MessageType.ACCEPT_REJECT,
        sender_pubkey="ff" * 32,
        body={},
    )
    assert rep.signature == ""


def test_reply_carries_no_source_fields():
    """A freshly-minted reply has empty source_ip/source_port — those will be
    populated by the receiver's transport layer if/when the reply is delivered."""
    req, _ = _signed_request_envelope()
    rep = req.reply(
        msg_type=MessageType.ACCEPT_REJECT,
        sender_pubkey="ff" * 32,
        body={},
    )
    assert rep.source_ip == ""
    assert rep.source_port == 0


def test_reply_raises_when_source_unknown():
    """If the original envelope has no populated source (never went through
    a transport), reply() raises — there's nowhere to send to."""
    req = Envelope(
        version=1, type=int(MessageType.PROPOSE),
        sender="ab" * 32, recipient="*",
        timestamp=time.time(), ttl=10.0, body={},
    )
    import pytest
    with pytest.raises(ValueError, match="source"):
        req.reply(
            msg_type=MessageType.ACCEPT_REJECT,
            sender_pubkey="ff" * 32,
            body={},
        )
```

- [ ] **Step 2: Run the tests, confirm they fail**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_envelope_reply.py -v
```

Expected: AttributeError on `req.reply` — method doesn't exist yet.

- [ ] **Step 3: Implement `reply()` and `destination_addr()`**

In `citizenry/protocol.py`, inside the `Envelope` class (just before `to_bytes`), add:

```python
    def destination_addr(self) -> tuple[str, int]:
        """The (host, port) tuple a reply to this envelope should be sent to.

        Returns ``(source_ip, source_port)``. Raises ``ValueError`` if the
        envelope did not come off the wire (source not populated)."""
        if not self.source_ip or self.source_port == 0:
            raise ValueError(
                "Envelope has no transport source — cannot derive a reply destination. "
                "reply() can only be called on envelopes received via transport.py."
            )
        return (self.source_ip, self.source_port)

    def reply(
        self,
        msg_type: "MessageType",
        sender_pubkey: str,
        body: dict,
        ttl: float | None = None,
    ) -> "Envelope":
        """Construct an unsigned unicast reply to the original sender.

        The returned envelope has ``recipient == self.sender``, default TTL
        derived from ``msg_type``, and an empty signature — caller signs it
        with their own role key. ``destination_addr()`` on the returned
        envelope inherits this envelope's source fields, so the caller can
        immediately ``unicast.send(rep, rep.destination_addr_inherited())``…
        but in practice the caller hands ``self.destination_addr()`` (this
        envelope's source) to ``UnicastTransport.send``.
        """
        # Validate we have a known source — fail fast instead of sending a
        # reply into the void.
        dest = self.destination_addr()
        # Default TTL by type — same table as make_envelope().
        default_ttls = {
            MessageType.HEARTBEAT: TTL_HEARTBEAT,
            MessageType.DISCOVER: TTL_DISCOVER,
            MessageType.ADVERTISE: TTL_ADVERTISE,
            MessageType.PROPOSE: TTL_PROPOSE,
            MessageType.ACCEPT_REJECT: TTL_ACCEPT_REJECT,
            MessageType.REPORT: TTL_REPORT,
            MessageType.GOVERN: TTL_GOVERN,
        }
        rep = Envelope(
            version=PROTOCOL_VERSION,
            type=int(msg_type),
            sender=sender_pubkey,
            recipient=self.sender,
            timestamp=time.time(),
            ttl=ttl if ttl is not None else default_ttls.get(msg_type, 10.0),
            body=body,
        )
        # Mirror the destination on the new envelope so callers that prefer
        # `rep.destination_addr()` over `req.destination_addr()` find it.
        rep.source_ip = dest[0]
        rep.source_port = dest[1]
        # Defensive: clear the inherited source on the returned object so callers
        # do not accidentally treat it as a received envelope. We expose the
        # destination via destination_addr() above instead.
        # (Re-zero them after using dest.)
        rep.source_ip = ""
        rep.source_port = 0
        return rep
```

(The two `rep.source_ip = ""` writes are deliberate — the helper validated `self.destination_addr()` above so we know the source was populated; the returned envelope itself is freshly minted and has no transport provenance of its own.)

- [ ] **Step 4: Run the tests, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_envelope_reply.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Run the broader protocol test suite to confirm no regression**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/ -k "envelope or protocol or signable" -v --no-header
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/protocol.py citizenry/tests/test_envelope_reply.py \
  && git commit -m "$(cat <<'EOF'
citizenry(mesh-hardening): Envelope.reply() helper + destination_addr()

- destination_addr() returns (source_ip, source_port) or raises ValueError
- reply(msg_type, sender_pubkey, body, ttl=None) mints unsigned reply addressed
  to env.sender with default TTL by message type
- Caller signs with their own role key before handing to UnicastTransport.send
- 7 tests covering recipient/sender/type/body/ttl/destination/error path

Spec: §5.2 smell #4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: XIAO C++ envelope — mirror the new fields, keep canonical bytes byte-identical

**Files:**
- Modify: `xiao-citizen/citizenry_envelope.h` (add struct fields)
- Modify: `xiao-citizen/citizenry_envelope.cpp` (no functional change — explicit comment)
- Test: extend `xiao-citizen/tests/test_canonical_json.cpp` (one synthetic test asserting source-field-population does not change canonical bytes)

The C++ side gains the same two fields. They are populated by the dispatcher (out of scope for this task) on RX, never serialized on the wire, and never included in `canonical_signable_bytes`. The test ensures Sub-2 holds the cross-language interop contract: every fixture in `fixtures.json` continues to verify byte-for-byte even when the local in-memory envelope has source_ip / source_port set.

- [ ] **Step 1: Write the failing C++ test extension**

Edit `xiao-citizen/tests/test_canonical_json.cpp`. After the existing fixture-loop assertion in `main()` (just before the summary `printf`), append a synthetic test:

```cpp
    // Sub-2: source_ip / source_port are local-only metadata. Setting them on
    // an envelope MUST NOT change canonical_signable_bytes() — otherwise every
    // existing signature breaks and Python/C++ interop diverges.
    if (!fixtures.empty()) {
        Envelope copy = fixtures[0].envelope;
        std::string canonical_before = canonical_signable_bytes(copy);
        copy.source_ip = "192.168.1.42";
        copy.source_port = 50001;
        std::string canonical_after = canonical_signable_bytes(copy);
        check("source_fields_excluded_from_canonical", canonical_after, canonical_before);

        // Same for envelope_to_wire — source_ip/source_port must not appear.
        std::string wire = envelope_to_wire(copy);
        bool leaked = (wire.find("source_ip") != std::string::npos)
                   || (wire.find("source_port") != std::string::npos);
        check("source_fields_excluded_from_wire",
              leaked ? std::string("LEAKED") : std::string("OK"),
              std::string("OK"));
    }
```

(Place this block immediately before `printf("\n%d passed, %d failed\n", g_pass, g_fail);`.)

- [ ] **Step 2: Run the C++ test suite, confirm it fails to compile**

```bash
cd ~/linux-usb/xiao-citizen/tests && make test_canonical_json
```

Expected: compile error — `Envelope` has no member `source_ip`.

- [ ] **Step 3: Add the fields to the C++ struct**

Edit `xiao-citizen/citizenry_envelope.h`. After the `std::string signature;` line in `struct Envelope`, add:

```cpp
    // ---- transport-only metadata (NOT signable, NOT serialised on the wire) ----
    // Populated by citizenry_dispatch.cpp after RX; empty otherwise.
    // Mirrors citizenry/protocol.py Envelope.source_ip / source_port.
    // Excluded from canonical_signable_bytes() and envelope_to_wire() —
    // see the explicit field list in citizenry_envelope.cpp.
    std::string source_ip;
    int         source_port = 0;
```

(No change needed in `citizenry_envelope.cpp`. Both `canonical_signable_bytes` and `envelope_to_wire` enumerate fields explicitly — `body`, `recipient`, `sender`, `timestamp`, `ttl`, `type`, `version` for canonical; same plus `signature` for wire — so adding new struct members is automatically a no-op for emit. Adding a one-line comment near the field list of each function clarifies intent for future maintainers; do that:)

In `xiao-citizen/citizenry_envelope.cpp`, locate the `canonical_signable_bytes` function (around line 123). Just before the line `std::map<std::string, std::function<void(std::ostringstream&)>> fields = {`, insert this comment:

```cpp
    // NOTE: source_ip / source_port are deliberately excluded — they are
    // transport-local metadata populated on RX, never signed, never on the wire.
    // See citizenry_envelope.h for the field list.
```

Locate `envelope_to_wire` (around line 162). Just before the `std::ostringstream os;` line, insert the same one-line comment.

- [ ] **Step 4: Build and run the C++ test, confirm pass**

```bash
cd ~/linux-usb/xiao-citizen/tests && make run
```

Expected: every fixture still passes its `canonical_bytes` check (proving the wire format is unchanged), plus the two new synthetic checks pass:
- `PASS: source_fields_excluded_from_canonical`
- `PASS: source_fields_excluded_from_wire`

`test_ed25519_interop` and `test_dispatch` and `test_messages` and `test_neighbor` must also stay green — they all consume the same `Envelope` struct and any leak into canonical bytes would invalidate signatures.

- [ ] **Step 5: Confirm cross-language signature interop survives**

```bash
cd ~/linux-usb/xiao-citizen/tests && ./test_ed25519_interop && cd /home/bradley/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_signable_bytes.py -v
```

Expected: both PASS. C++ signatures of fixture envelopes still verify against the Python `_canonical_dumps` output.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add xiao-citizen/citizenry_envelope.h \
             xiao-citizen/citizenry_envelope.cpp \
             xiao-citizen/tests/test_canonical_json.cpp \
  && git commit -m "$(cat <<'EOF'
citizenry(mesh-hardening): XIAO C++ Envelope mirrors source_ip/source_port

- struct Envelope gains std::string source_ip + int source_port
- Both canonical_signable_bytes() and envelope_to_wire() enumerate fields
  explicitly, so adding struct members is a no-op for emit (verified)
- Comments added at both emit sites flagging the deliberate exclusion
- test_canonical_json.cpp gains 2 synthetic checks asserting the exclusion
- All 5 host tests (canonical/ed25519/dispatch/messages/neighbor) green
- Every fixture in fixtures.json still byte-matches canonical bytes —
  cross-language signature interop preserved

Spec: §5.2 smell #4 (XIAO C++ envelope mirror)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Marketplace honours `_stale_node_pubkeys` for co-location bonus

**Files:**
- Modify: `citizenry/marketplace.py:115-143` (`compute_bid_score`)
- Test: `citizenry/tests/test_marketplace_stale_node_pubkeys.py` (create)

Sub-1 Task 6 introduced `Citizen._stale_node_pubkeys: set[str]` populated when `GOVERN(rotate_node_key)` arrives. The marketplace's co-location bonus today applies on every bid whose `node_pubkey` matches the targeted follower's node — but if the bidder's node has rotated keys mid-flight, the cached `node_pubkey` is stale and the bonus is unsafe (the bidder may not actually be co-located with the new key). Fix: `compute_bid_score` accepts an optional `stale_node_pubkeys: set[str] | None` and a `bidder_node_pubkey: str`; if the bidder's pubkey is in the stale set, the bonus is suppressed (we return base score only).

- [ ] **Step 1: Write the failing tests**

Create `citizenry/tests/test_marketplace_stale_node_pubkeys.py`:

```python
"""compute_bid_score honours the stale_node_pubkeys set populated by
GOVERN(rotate_node_key) — co-location bonus is suppressed for stale bidders."""
import pytest

from citizenry.marketplace import compute_bid_score


def test_bonus_applied_when_bidder_node_not_stale():
    """Baseline: with no stale set, co-location bonus is applied as before."""
    score = compute_bid_score(
        skill_level=8,
        current_load=0.2,
        health=1.0,
        co_location_bonus=0.15,
        bidder_node_pubkey="ab" * 32,
        stale_node_pubkeys=set(),
    )
    base = compute_bid_score(skill_level=8, current_load=0.2, health=1.0)
    assert score == pytest.approx(base + 0.15)


def test_bonus_suppressed_when_bidder_node_in_stale_set():
    """Smell #5 fix: stale node_pubkey → no co-location bonus."""
    score = compute_bid_score(
        skill_level=8,
        current_load=0.2,
        health=1.0,
        co_location_bonus=0.15,
        bidder_node_pubkey="ab" * 32,
        stale_node_pubkeys={"ab" * 32},
    )
    base = compute_bid_score(skill_level=8, current_load=0.2, health=1.0)
    assert score == pytest.approx(base)


def test_legacy_call_signature_still_works():
    """Pre-Sub-2 callers that pass neither bidder_node_pubkey nor
    stale_node_pubkeys must continue to receive the bonus."""
    score = compute_bid_score(
        skill_level=8, current_load=0.2, health=1.0,
        co_location_bonus=0.15,
    )
    base = compute_bid_score(skill_level=8, current_load=0.2, health=1.0)
    assert score == pytest.approx(base + 0.15)


def test_no_bonus_no_suppression_check():
    """If co_location_bonus is 0 we don't even consult the stale set."""
    score = compute_bid_score(
        skill_level=5, current_load=0.4, health=0.9,
        co_location_bonus=0.0,
        bidder_node_pubkey="cd" * 32,
        stale_node_pubkeys={"cd" * 32},
    )
    expected = compute_bid_score(skill_level=5, current_load=0.4, health=0.9)
    assert score == pytest.approx(expected)


def test_empty_bidder_node_pubkey_does_not_match_stale_set():
    """A bidder that did not declare its node pubkey cannot accidentally match
    a stale entry of the empty string. Defensive."""
    score = compute_bid_score(
        skill_level=8, current_load=0.2, health=1.0,
        co_location_bonus=0.15,
        bidder_node_pubkey="",
        stale_node_pubkeys=set(),
    )
    base = compute_bid_score(skill_level=8, current_load=0.2, health=1.0)
    # Empty pubkey + empty stale set → bonus applies (no match).
    assert score == pytest.approx(base + 0.15)
    # And empty pubkey with stale set containing "" should also NOT suppress —
    # we explicitly require a non-empty pubkey to be considered "in the set".
    score2 = compute_bid_score(
        skill_level=8, current_load=0.2, health=1.0,
        co_location_bonus=0.15,
        bidder_node_pubkey="",
        stale_node_pubkeys={""},
    )
    assert score2 == pytest.approx(base + 0.15)
```

- [ ] **Step 2: Run the tests, confirm they fail**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_marketplace_stale_node_pubkeys.py -v
```

Expected: TypeError — `compute_bid_score` does not accept `bidder_node_pubkey` or `stale_node_pubkeys`.

- [ ] **Step 3: Extend `compute_bid_score`**

In `citizenry/marketplace.py`, replace the `compute_bid_score` function (lines 115-143) with:

```python
def compute_bid_score(
    skill_level: int,
    current_load: float,
    health: float,
    fatigue: float = 0.0,
    weights: dict[str, float] | None = None,
    co_location_bonus: float = 0.0,
    *,
    bidder_node_pubkey: str = "",
    stale_node_pubkeys: set[str] | None = None,
) -> float:
    """Compute composite bid score with fatigue modifier.

    score = (capability_weight * (skill_level / 10)
           + availability_weight * (1 - load)
           + health_weight * health) * (1.0 - 0.3 * fatigue)
           + co_location_bonus

    All components normalized to [0, 1]. Skill level capped at 10.
    Fatigue reduces the score by up to 30% (FR-4.3).

    co_location_bonus: extra absolute score awarded to bidders co-located
    with the targeted follower (same node_pubkey). Default 0.0; spec
    recommends 0.15.

    bidder_node_pubkey + stale_node_pubkeys: smell #5 fix. If the bidder's
    declared node_pubkey is in the caller's stale set (populated by
    GOVERN(rotate_node_key) on the caller's Citizen), the co-location
    bonus is suppressed — we cannot trust co-location until a fresh
    genome attests the new node_pubkey.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    skill_norm = min(skill_level, 10) / 10.0
    avail = max(0.0, 1.0 - current_load)
    h = max(0.0, min(1.0, health))
    base = w["capability"] * skill_norm + w["availability"] * avail + w["health"] * h
    fatigue_modifier = 1.0 - 0.3 * max(0.0, min(1.0, fatigue))

    # Smell #5 fix: suppress co-location bonus if bidder's node pubkey is stale.
    effective_bonus = co_location_bonus
    if (
        co_location_bonus
        and bidder_node_pubkey
        and stale_node_pubkeys
        and bidder_node_pubkey in stale_node_pubkeys
    ):
        effective_bonus = 0.0

    return base * fatigue_modifier + effective_bonus
```

- [ ] **Step 4: Run the tests, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_marketplace_stale_node_pubkeys.py -v
```

Expected: 5 PASS.

- [ ] **Step 5: Run the full marketplace test suite to confirm no regression**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/ -k "marketplace or bid or composition" -v --no-header
```

Expected: all PASS — legacy callers (no kwargs) still receive the bonus exactly as before.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/marketplace.py \
             citizenry/tests/test_marketplace_stale_node_pubkeys.py \
  && git commit -m "$(cat <<'EOF'
citizenry(mesh-hardening): compute_bid_score honours _stale_node_pubkeys

- Two new keyword-only params: bidder_node_pubkey + stale_node_pubkeys
- Co-location bonus is suppressed when the bidder's node_pubkey is in the
  stale set populated by Sub-1 Task 6's GOVERN(rotate_node_key) handler
- Legacy callers unaffected (default values reproduce pre-Sub-2 behaviour)
- 5 tests covering bonus / suppression / legacy / zero-bonus / empty-pubkey

Fixes architectural smell #5 (co-location bonus fragile to node-key rotation).
Wires Sub-1 Task 6's _stale_node_pubkeys attribute into the marketplace.

Spec: §5.2 smell #5, §10 sub-2

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Wire the marketplace fix into the existing bid path

**Files:**
- Modify: `citizenry/citizen.py` or `citizenry/composition.py` — find the call site of `compute_bid_score` that today computes its own co-location bonus, and pass `bidder_node_pubkey=…, stale_node_pubkeys=self._stale_node_pubkeys` through.
- Test: `citizenry/tests/test_citizen_bid_uses_stale_set.py` (create)

Task 5 made the function honour the stale set; this task makes the citizens that *use* it actually pass the stale set in. Without this, smell #5 is fixed in the function but no production code path consults it.

- [ ] **Step 1: Locate the call site(s)**

```bash
cd ~/linux-usb && grep -rn "compute_bid_score\|co_location_bonus" \
  citizenry/citizen.py citizenry/composition.py citizenry/manipulator_citizen.py \
  citizenry/governor_citizen.py 2>/dev/null
```

Note the file:line of every call. There is typically one canonical site (composition module) plus possibly per-citizen overrides. Read 30 lines around each match to confirm what node_pubkey the caller has access to (it's typically the citizen's own `self.node_pubkey` attribute, set at boot from `~/.citizenry/node.key`).

- [ ] **Step 2: Write the failing wiring test**

Create `citizenry/tests/test_citizen_bid_uses_stale_set.py`:

```python
"""When a citizen builds a bid, compute_bid_score sees the citizen's
_stale_node_pubkeys (Sub-1 Task 6) — so the marketplace fix from Task 5
takes effect on the live bid path."""
from unittest.mock import patch

import pytest

from citizenry.citizen import Citizen
from citizenry.marketplace import Task, TaskStatus


def _bidding_task(target_follower: str = "", node_pubkey_param: str = "") -> Task:
    return Task(
        id="t1",
        type="demo",
        params={
            "follower_pubkey": target_follower,
            "node_pubkey": node_pubkey_param,
        },
        status=TaskStatus.BIDDING,
    )


def test_bid_passes_stale_set_to_compute_bid_score(monkeypatch, tmp_path):
    """The citizen's bid path passes its _stale_node_pubkeys through."""
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="bidder", citizen_type="test")
    # Pretend Sub-1 Task 6's handler ran and put a stale entry in the set
    c._stale_node_pubkeys = {"ab" * 32}

    # Make the citizen "co-located" with a targeted follower whose node was
    # rotated — bidder.node_pubkey == stale entry.
    c.node_pubkey = "ab" * 32

    captured: dict = {}

    def fake_compute(*args, **kwargs):
        captured.update(kwargs)
        return 0.5

    with patch("citizenry.marketplace.compute_bid_score", side_effect=fake_compute):
        # Invoke whichever bid-building method the citizen exposes. The exact
        # method name is identified in Step 1 above; one canonical name is
        # _build_bid(task) returning a Bid. Adapt the line below to match.
        if hasattr(c, "_build_bid"):
            c._build_bid(_bidding_task(target_follower="cd" * 32))
        elif hasattr(c, "build_bid"):
            c.build_bid(_bidding_task(target_follower="cd" * 32))
        else:
            pytest.skip(
                "Citizen does not expose a bid-building method this test can "
                "drive. Update the test to call the actual entry point found "
                "in Step 1."
            )

    assert "stale_node_pubkeys" in captured, (
        "compute_bid_score not called with stale_node_pubkeys kwarg — "
        "wiring fix incomplete"
    )
    assert captured["stale_node_pubkeys"] == {"ab" * 32}
    assert captured.get("bidder_node_pubkey") == "ab" * 32
```

- [ ] **Step 3: Run the test, confirm it fails (or skips with a clear message)**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_citizen_bid_uses_stale_set.py -v
```

Expected: either `assert "stale_node_pubkeys" in captured` fails (call site exists but doesn't pass the kwargs) or the test skips because no `_build_bid` method was found. If skipped, treat the skip message as the failing precondition and identify the actual bid-building site in Step 1.

- [ ] **Step 4: Plumb the kwargs through the bid path**

At each call site identified in Step 1, change the existing call from e.g.

```python
score = compute_bid_score(
    skill_level=...,
    current_load=...,
    health=...,
    co_location_bonus=BONUS if co_located else 0.0,
)
```

to

```python
score = compute_bid_score(
    skill_level=...,
    current_load=...,
    health=...,
    co_location_bonus=BONUS if co_located else 0.0,
    bidder_node_pubkey=self.node_pubkey,
    stale_node_pubkeys=self._stale_node_pubkeys,
)
```

If the citizen object does not yet expose `node_pubkey` or `_stale_node_pubkeys` attributes (Sub-1 Task 6 should have added the latter; the former lives in `citizenry/node_identity.py`), wire them at the top of the bid-building method:

```python
node_pk = getattr(self, "node_pubkey", "") or ""
stale = getattr(self, "_stale_node_pubkeys", None)
```

and pass `bidder_node_pubkey=node_pk, stale_node_pubkeys=stale`.

- [ ] **Step 5: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_citizen_bid_uses_stale_set.py \
            citizenry/tests/test_marketplace_stale_node_pubkeys.py -v
```

Expected: 1 + 5 PASS.

- [ ] **Step 6: Run the full citizen + marketplace suites to confirm no regression**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/ -k "citizen or marketplace or bid or composition" -v --no-header
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/citizen.py citizenry/composition.py \
             citizenry/tests/test_citizen_bid_uses_stale_set.py \
  && git commit -m "$(cat <<'EOF'
citizenry(mesh-hardening): bid path passes stale set into compute_bid_score

- Citizen / composition bid-building call sites now pass
  bidder_node_pubkey=self.node_pubkey + stale_node_pubkeys=self._stale_node_pubkeys
  through to compute_bid_score
- Closes the Sub-1 Task 6 → Sub-2 Task 5 wiring gap: GOVERN(rotate_node_key)
  populates the set, the marketplace honours it on every fresh bid
- 1 test asserting kwargs flow through

Spec: §5.2 smell #5 (end-to-end), §10 sub-2

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

(If Step 1 finds the call site is only in `composition.py` and not in `citizen.py`, drop `citizen.py` from `git add`. Add only the files actually modified.)

---

## Task 7: End-to-end integration test — handler builds a reply and unicasts it

**Files:**
- Test: `citizenry/tests/test_reply_round_trip.py` (create)

A single integration test that exercises the entire Sub-2 surface together: Alice sends a PROPOSE to Bob, Bob's handler receives a populated envelope, builds a reply via `env.reply(...)`, signs it, and unicasts it back to Alice using `env.destination_addr()`. Alice receives the ACCEPT_REJECT, signature verifies. This is the acceptance test for §10 sub-2.

- [ ] **Step 1: Write the integration test**

Create `citizenry/tests/test_reply_round_trip.py`:

```python
"""End-to-end Sub-2 acceptance: source plumbing → reply() → unicast → verify."""
import asyncio

import pytest
from nacl.signing import SigningKey

from citizenry.protocol import Envelope, MessageType, make_envelope
from citizenry.transport import UnicastTransport


@pytest.mark.asyncio
async def test_handler_replies_via_envelope_helper():
    alice_sk = SigningKey.generate()
    bob_sk = SigningKey.generate()
    alice_pub = alice_sk.verify_key.encode().hex()
    bob_pub = bob_sk.verify_key.encode().hex()

    bob_received: list[Envelope] = []
    alice_received: list[Envelope] = []

    bob = UnicastTransport(lambda e, _a: bob_received.append(e))
    alice = UnicastTransport(lambda e, _a: alice_received.append(e))

    loop = asyncio.get_running_loop()
    await bob.start(loop)
    await alice.start(loop)

    # Alice sends a PROPOSE to Bob's unicast port.
    propose = make_envelope(
        MessageType.PROPOSE,
        sender_pubkey=alice_pub,
        body={"task": "demo", "task_id": "t1"},
        recipient=bob_pub,
        signing_key=alice_sk,
    )
    alice.send(propose, ("127.0.0.1", bob.bound_port))

    # Pump until Bob receives.
    for _ in range(50):
        await asyncio.sleep(0.01)
        if bob_received:
            break
    assert bob_received, "Bob never received PROPOSE"
    got = bob_received[0]

    # Source fields populated by transport.
    assert got.source_port == alice.bound_port
    assert got.source_ip in ("127.0.0.1", "::ffff:127.0.0.1")

    # Bob signature-verifies, builds reply via env.reply(), signs with his role
    # key, sends to env.destination_addr().
    assert got.verify(alice_sk.verify_key) is True
    reply = got.reply(
        msg_type=MessageType.ACCEPT_REJECT,
        sender_pubkey=bob_pub,
        body={"accept": True, "task_id": "t1"},
    )
    reply.sign(bob_sk)
    bob.send(reply, got.destination_addr())

    # Pump until Alice receives.
    for _ in range(50):
        await asyncio.sleep(0.01)
        if alice_received:
            break
    assert alice_received, "Alice never received ACCEPT_REJECT"
    rep = alice_received[0]

    # Reply is correctly addressed and signed.
    assert rep.recipient == alice_pub
    assert rep.sender == bob_pub
    assert rep.type == int(MessageType.ACCEPT_REJECT)
    assert rep.body == {"accept": True, "task_id": "t1"}
    assert rep.verify(bob_sk.verify_key) is True

    # Alice's transport populated the reply's source fields.
    assert rep.source_port == bob.bound_port
    assert rep.source_ip in ("127.0.0.1", "::ffff:127.0.0.1")

    bob.close()
    alice.close()
```

- [ ] **Step 2: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_reply_round_trip.py -v
```

Expected: 1 PASS. If asyncio fixture is missing, `pip install pytest-asyncio` (already a dep — check `~/lerobot-env/lib/python3.12/site-packages/pytest_asyncio` first).

- [ ] **Step 3: Run the entire Sub-2 test surface to confirm the full picture**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_envelope_source_fields.py \
            citizenry/tests/test_envelope_reply.py \
            citizenry/tests/test_transport_source_plumbing.py \
            citizenry/tests/test_marketplace_stale_node_pubkeys.py \
            citizenry/tests/test_citizen_bid_uses_stale_set.py \
            citizenry/tests/test_reply_round_trip.py \
            citizenry/tests/test_signable_bytes.py -v
```

Expected: 21+ PASS across all Sub-2 + the cross-language regression test.

- [ ] **Step 4: Run the C++ host tests one more time**

```bash
cd ~/linux-usb/xiao-citizen/tests && make run
```

Expected: all 5 host tests green; every fixture in `fixtures.json` byte-matches.

- [ ] **Step 5: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/tests/test_reply_round_trip.py \
  && git commit -m "$(cat <<'EOF'
citizenry(mesh-hardening): end-to-end reply round-trip integration test

- Alice → Bob: PROPOSE over unicast
- Bob: handler receives populated envelope (source_ip/source_port set),
  signature verifies, builds ACCEPT_REJECT via env.reply(),
  signs with role key, unicasts to env.destination_addr()
- Alice: receives reply with source fields populated by her transport,
  signature verifies
- Closes the Sub-2 §10 acceptance surface

Spec: §5.2 smell #4 (acceptance test), §10 sub-2

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

Run through the spec sections that Sub-2 must implement:

- **§5.2 smell #4** (unicast reply port plumbing partial — `Envelope` lacks `source_ip`/`source_port`, no reply helper, XIAO C++ envelope mismatch) → Tasks 1, 2, 3, 4, 7.
- **§5.2 smell #5** (co-location bonus fragile to node-key rotation) → Tasks 5, 6 (Sub-1 Task 6 supplies the `_stale_node_pubkeys` set).
- **§10 sub-2 scope**:
  - "Add `Envelope.source_ip`/`source_port`" → Task 1.
  - "These fields must be NON-signable (excluded from canonical bytes)" → Task 1 (canonical bytes test) + Task 4 (XIAO C++ canonical bytes test).
  - "Add `Envelope.reply(payload)` helper" → Task 3.
  - "Plumb `source_ip`/`source_port` through `transport.py`" → Task 2.
  - "Update XIAO C++ envelope" → Task 4.
  - "keep `signable_bytes()` byte-identical with Python" → Task 1 (Python test) + Task 4 (C++ test) + the existing `test_signable_bytes.py` regression check still green.
  - "Add tests confirming: signature still valid with new fields populated, `reply()` constructs correctly, source plumbing reaches a handler" → Task 1 + Task 3 + Task 2 + Task 7 integration.
  - "Wire the node-key rotation flow that Sub-1 Task 6 introduced: marketplace's `compute_bid_score` consults `_stale_node_pubkeys`" → Tasks 5, 6.

**Cross-language signature contract preserved:**

- Python `signable_bytes()` formula unchanged (Task 1, regression-tested by `test_signable_bytes.py`).
- C++ `canonical_signable_bytes()` enumerates the same 7 fields; new struct members default-initialised but never emitted (Task 4).
- Every fixture in `xiao-citizen/tests/fixtures.json` continues to byte-match (Task 4 + Task 7).

**Type / signature consistency:**

- `Envelope.source_ip: str = ""` and `Envelope.source_port: int = 0` — same names everywhere (Python dataclass, C++ struct, all tests).
- `Envelope.reply(msg_type, sender_pubkey, body, ttl=None) -> Envelope` — same signature in Task 3 implementation and Task 7 integration test.
- `Envelope.destination_addr() -> tuple[str, int]` — same name in Task 3 implementation and Task 7 integration test.
- `compute_bid_score(..., *, bidder_node_pubkey: str = "", stale_node_pubkeys: set[str] | None = None)` — same signature in Task 5 + Task 6 wiring + Task 7 integration.
- `Citizen._stale_node_pubkeys: set[str]` — supplied by Sub-1 Task 6, consumed by Sub-2 Task 6.

No `TBD` / `TODO` / `implement later` strings in any task. Every step has either a code block or an exact command. The handler-shim contract `(env, addr)` where `addr == (env.source_ip, env.source_port)` is consistent across Tasks 2 and 7 — no production handler signatures are broken by Sub-2 (they will be cleaned up in a follow-up sweep, intentionally out of scope).

No gaps detected.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-30-mesh-hardening.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. Tasks 1, 4, 5 are particularly clean for this — minimal cross-file context. Task 6 needs Step 1's call-site survey first; consider doing that survey inline before dispatching.
**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Keeps the C++ build environment hot for Task 4 if that's already configured.

Which approach?
