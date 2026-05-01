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

    propose = make_envelope(
        MessageType.PROPOSE,
        sender_pubkey=alice_pub,
        body={"task": "demo", "task_id": "t1"},
        recipient=bob_pub,
        signing_key=alice_sk,
    )
    alice.send(propose, ("127.0.0.1", bob.bound_port))

    for _ in range(50):
        await asyncio.sleep(0.01)
        if bob_received:
            break
    assert bob_received, "Bob never received PROPOSE"
    got = bob_received[0]

    # Source fields populated by transport.
    assert got.source_port == alice.bound_port
    assert got.source_ip in ("127.0.0.1", "::ffff:127.0.0.1")
    assert got.verify(alice_sk.verify_key) is True

    # Build reply via the new helper, sign with Bob's role key, unicast.
    reply = got.reply(
        msg_type=MessageType.ACCEPT_REJECT,
        sender_pubkey=bob_pub,
        body={"accept": True, "task_id": "t1"},
    )
    reply.sign(bob_sk)
    bob.send(reply, got.destination_addr())

    for _ in range(50):
        await asyncio.sleep(0.01)
        if alice_received:
            break
    assert alice_received, "Alice never received ACCEPT_REJECT"
    rep = alice_received[0]

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
