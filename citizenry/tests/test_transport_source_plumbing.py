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
    assert got.verify(sk.verify_key) is True


@pytest.mark.asyncio
async def test_signature_unaffected_by_source_population():
    """Regression: source_ip/source_port set by the transport must not break
    the signature."""
    sk = SigningKey.generate()
    env = make_envelope(
        MessageType.HEARTBEAT,
        sender_pubkey=sk.verify_key.encode().hex(),
        body={"state": "ok"},
        signing_key=sk,
    )
    env.source_ip = "192.168.1.99"
    env.source_port = 50111
    assert env.verify(sk.verify_key) is True
