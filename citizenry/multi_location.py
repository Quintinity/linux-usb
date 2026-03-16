"""Multi-Location Architecture — WireGuard VPN + Embassy model.

Design foundations for connecting citizenry neighborhoods across locations.
Each location is a "province" with its own LAN. Provinces connect through
"embassies" — always-on relay nodes over WireGuard VPN.

This module defines the data structures and routing logic. Actual VPN
setup and cross-location transport are deferred to v4.0.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Location:
    """A physical location where citizens operate."""

    id: str = ""
    name: str = ""              # "Home Office", "School Lab"
    subnet: str = ""            # "192.168.1.0/24"
    embassy_ip: str = ""        # WireGuard endpoint for this location
    embassy_port: int = 51820   # WireGuard port
    citizen_count: int = 0
    last_seen: float = 0.0
    latency_ms: float = 0.0     # RTT to this location

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "subnet": self.subnet,
            "embassy_ip": self.embassy_ip,
            "citizen_count": self.citizen_count,
            "latency_ms": self.latency_ms,
        }


@dataclass
class Embassy:
    """A relay node that connects two locations over WireGuard VPN.

    Each location runs an embassy process on a Pi or similar always-on device.
    The embassy translates between local UDP multicast and cross-VPN unicast.
    """

    location: Location
    wireguard_interface: str = "wg0"
    is_local: bool = False      # True if this is our location's embassy
    connected: bool = False
    peers: list[str] = field(default_factory=list)  # Peer embassy IPs

    def to_dict(self) -> dict:
        return {
            "location": self.location.to_dict(),
            "interface": self.wireguard_interface,
            "is_local": self.is_local,
            "connected": self.connected,
            "peers": self.peers,
        }


@dataclass
class CrossLocationMessage:
    """A message routed between locations via embassies.

    The embassy wraps local citizenry protocol messages for cross-VPN
    transport, adding source/destination location metadata.
    """

    source_location: str = ""
    dest_location: str = ""     # "*" for broadcast to all locations
    original_sender: str = ""   # Citizen pubkey
    original_recipient: str = ""
    message_type: int = 0
    payload: bytes = b""
    timestamp: float = field(default_factory=time.time)
    ttl_hops: int = 3           # Max location hops


class LocationRegistry:
    """Registry of known locations in the nation."""

    def __init__(self):
        self.locations: dict[str, Location] = {}
        self.local_location_id: str = ""

    def register(self, location: Location) -> None:
        self.locations[location.id] = location

    def set_local(self, location_id: str) -> None:
        self.local_location_id = location_id

    def get_remote(self) -> list[Location]:
        """Get all non-local locations."""
        return [l for l in self.locations.values() if l.id != self.local_location_id]

    def get_by_subnet(self, ip: str) -> Location | None:
        """Find which location an IP belongs to."""
        import ipaddress
        for loc in self.locations.values():
            if loc.subnet:
                try:
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(loc.subnet, strict=False):
                        return loc
                except ValueError:
                    continue
        return None

    def to_list(self) -> list[dict]:
        return [l.to_dict() for l in self.locations.values()]


# ── Constitution extensions for multi-location ───────────────────────────────

LOCATION_LAWS = {
    "cross_location_heartbeat_interval": {
        "description": "Seconds between cross-location heartbeat relay",
        "params": {"seconds": 10.0},
    },
    "cross_location_task_routing": {
        "description": "Allow tasks to be routed to remote locations",
        "params": {"enabled": False, "max_latency_ms": 100},
    },
    "embassy_failover_timeout": {
        "description": "Seconds before declaring an embassy unreachable",
        "params": {"seconds": 30.0},
    },
}
