"""UDP Transport Layer — multicast for broadcast, unicast for directed messages."""

import asyncio
import socket
import struct
from typing import Callable

from .protocol import MULTICAST_GROUP, MULTICAST_PORT, Envelope


class MulticastTransport:
    """Sends and receives UDP multicast messages for discovery and heartbeats."""

    def __init__(self, on_message: Callable[[Envelope, tuple], None], port: int = MULTICAST_PORT):
        self.on_message = on_message
        self.port = port
        self._sock: socket.socket | None = None
        self._transport: asyncio.DatagramTransport | None = None

    async def start(self, loop: asyncio.AbstractEventLoop):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind(("", self.port))

        # Join multicast group
        group = socket.inet_aton(MULTICAST_GROUP)
        mreq = struct.pack("4sL", group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Enable multicast loopback for same-host testing
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

        self._sock = sock
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: _MulticastProtocol(self.on_message),
            sock=sock,
        )

    def send(self, envelope: Envelope):
        if self._transport:
            self._transport.sendto(envelope.to_bytes(), (MULTICAST_GROUP, self.port))

    def close(self):
        if self._transport:
            self._transport.close()


class UnicastTransport:
    """Sends and receives UDP unicast messages for directed citizen-to-citizen comms."""

    def __init__(self, on_message: Callable[[Envelope, tuple], None], port: int = 0):
        self.on_message = on_message
        self.port = port
        self._transport: asyncio.DatagramTransport | None = None
        self.bound_port: int = 0

    async def start(self, loop: asyncio.AbstractEventLoop):
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: _MulticastProtocol(self.on_message),
            local_addr=("0.0.0.0", self.port),
        )
        # Record the actual bound port
        sock = self._transport.get_extra_info("socket")
        if sock:
            self.bound_port = sock.getsockname()[1]

    def send(self, envelope: Envelope, addr: tuple[str, int]):
        if self._transport:
            self._transport.sendto(envelope.to_bytes(), addr)

    def close(self):
        if self._transport:
            self._transport.close()


class _MulticastProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_message: Callable[[Envelope, tuple], None]):
        self.on_message = on_message

    def datagram_received(self, data: bytes, addr: tuple):
        try:
            env = Envelope.from_bytes(data)
            self.on_message(env, addr)
        except Exception:
            pass  # Drop malformed packets silently
