"""mDNS service advertisement and discovery for armOS citizens.

Uses zeroconf to advertise each citizen as a LAN service and discover
neighbors.  Runs alongside the existing UDP multicast discovery as a
secondary mechanism.

    pip install zeroconf
"""

from __future__ import annotations

import asyncio
import socket
from typing import Callable

from zeroconf import IPVersion, ServiceStateChange
from zeroconf.asyncio import (
    AsyncServiceBrowser,
    AsyncServiceInfo,
    AsyncZeroconf,
)

SERVICE_TYPE = "_armos-citizen._udp.local."
PROTOCOL_VERSION = "1"


def get_local_ip() -> str:
    """Return this machine's LAN IP (not 127.0.0.1)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


class CitizenMDNS:
    """Advertise and discover armOS citizens over mDNS."""

    def __init__(
        self,
        name: str,
        citizen_type: str,
        pubkey: str,
        unicast_port: int,
        capabilities: list[str],
    ) -> None:
        self.name = name
        self.citizen_type = citizen_type
        self.pubkey = pubkey
        self.unicast_port = unicast_port
        self.capabilities = capabilities

        self.on_neighbor_found: Callable | None = None
        self.on_neighbor_lost: Callable | None = None

        self._azc: AsyncZeroconf | None = None
        self._browser: AsyncServiceBrowser | None = None
        self._info: AsyncServiceInfo | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Register the mDNS service and begin browsing for neighbors."""
        local_ip = get_local_ip()
        self._azc = AsyncZeroconf(ip_version=IPVersion.V4Only)

        self._info = AsyncServiceInfo(
            SERVICE_TYPE,
            f"{self.name}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(local_ip)],
            port=self.unicast_port,
            properties={
                "type": self.citizen_type,
                "pubkey": self.pubkey[:16],
                "caps": ",".join(self.capabilities),
                "version": PROTOCOL_VERSION,
            },
        )
        await self._azc.async_register_service(self._info)

        self._browser = AsyncServiceBrowser(
            self._azc.zeroconf,
            SERVICE_TYPE,
            handlers=[self._on_state_change],
        )

    async def stop(self) -> None:
        """Unregister the service and shut down."""
        if self._browser is not None:
            await self._browser.async_cancel()
            self._browser = None
        if self._info is not None and self._azc is not None:
            await self._azc.async_unregister_service(self._info)
            self._info = None
        if self._azc is not None:
            await self._azc.async_close()
            self._azc = None

    # ------------------------------------------------------------------
    # Browser callback
    # ------------------------------------------------------------------

    def _on_state_change(
        self,
        zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        if state_change in (
            ServiceStateChange.Added,
            ServiceStateChange.Updated,
        ):
            asyncio.ensure_future(self._handle_found(zeroconf, service_type, name))
        elif state_change is ServiceStateChange.Removed:
            short_name = name.replace(f".{SERVICE_TYPE}", "")
            if short_name == self.name:
                return
            if self.on_neighbor_lost is not None:
                self.on_neighbor_lost(short_name)

    async def _handle_found(self, zeroconf, service_type: str, name: str) -> None:
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 3000)

        short_name = name.replace(f".{SERVICE_TYPE}", "")
        if short_name == self.name:
            return

        if info.addresses and self.on_neighbor_found is not None:
            props = {
                k.decode() if isinstance(k, bytes) else k:
                v.decode() if isinstance(v, bytes) else v
                for k, v in (info.properties or {}).items()
            }
            addr = socket.inet_ntoa(info.addresses[0])
            caps = [c for c in props.get("caps", "").split(",") if c]
            self.on_neighbor_found(
                short_name,
                props.get("type", ""),
                props.get("pubkey", ""),
                addr,
                info.port,
                caps,
            )
