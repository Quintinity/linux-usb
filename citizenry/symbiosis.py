"""Symbiosis Contracts — formal mutual-benefit agreements between citizens.

Two citizens agree: "I provide X capability, you provide Y, together we
offer Z." Contracts have health monitoring and auto-break on failure.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class ContractStatus(Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    BROKEN = "broken"
    EXPIRED = "expired"


@dataclass
class SymbiosisContract:
    """A mutual-benefit agreement between two citizens."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    provider: str = ""              # citizen pubkey providing a capability
    consumer: str = ""              # citizen pubkey consuming it
    provider_capability: str = ""
    consumer_capability: str = ""
    composite_capability: str = ""
    health_check_interval: float = 2.0
    status: ContractStatus = ContractStatus.PROPOSED
    created_at: float = field(default_factory=time.time)
    last_health_check: float = field(default_factory=time.time)
    missed_checks: int = 0
    max_missed_checks: int = 3

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> SymbiosisContract:
        d = dict(d)
        if "status" in d and isinstance(d["status"], str):
            d["status"] = ContractStatus(d["status"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def to_propose_body(self) -> dict:
        """Convert to a PROPOSE message body."""
        return {
            "task": "symbiosis_propose",
            "contract_id": self.id,
            "provider_cap": self.provider_capability,
            "consumer_cap": self.consumer_capability,
            "composite": self.composite_capability,
            "health_check_hz": 1.0 / self.health_check_interval,
        }

    @classmethod
    def from_propose_body(cls, body: dict, sender: str, recipient: str) -> SymbiosisContract:
        interval = 1.0 / body.get("health_check_hz", 0.5) if body.get("health_check_hz", 0) > 0 else 2.0
        return cls(
            id=body.get("contract_id", uuid.uuid4().hex[:12]),
            provider=sender,
            consumer=recipient,
            provider_capability=body.get("provider_cap", ""),
            consumer_capability=body.get("consumer_cap", ""),
            composite_capability=body.get("composite", ""),
            health_check_interval=interval,
        )

    def is_healthy(self) -> bool:
        return self.missed_checks < self.max_missed_checks

    def record_health_check(self) -> None:
        self.last_health_check = time.time()
        self.missed_checks = 0

    def check_timeout(self) -> bool:
        """Check if a health check has timed out. Returns True if contract should break."""
        elapsed = time.time() - self.last_health_check
        expected_checks = int(elapsed / self.health_check_interval)
        self.missed_checks = max(self.missed_checks, expected_checks)
        if self.missed_checks >= self.max_missed_checks:
            self.status = ContractStatus.BROKEN
            return True
        return False


class ContractManager:
    """Manages all symbiosis contracts for a citizen."""

    def __init__(self):
        self.contracts: dict[str, SymbiosisContract] = {}

    def propose(
        self,
        provider: str,
        consumer: str,
        provider_cap: str,
        consumer_cap: str,
        composite: str,
    ) -> SymbiosisContract:
        """Create a new contract proposal."""
        contract = SymbiosisContract(
            provider=provider,
            consumer=consumer,
            provider_capability=provider_cap,
            consumer_capability=consumer_cap,
            composite_capability=composite,
        )
        self.contracts[contract.id] = contract
        return contract

    def accept(self, contract_id: str) -> SymbiosisContract | None:
        """Accept a proposed contract."""
        contract = self.contracts.get(contract_id)
        if contract and contract.status == ContractStatus.PROPOSED:
            contract.status = ContractStatus.ACTIVE
            contract.last_health_check = time.time()
            return contract
        return None

    def register(self, contract: SymbiosisContract) -> None:
        """Register a contract received from another citizen."""
        self.contracts[contract.id] = contract

    def record_health(self, partner_pubkey: str) -> None:
        """Record a health check from a contract partner."""
        for contract in self.contracts.values():
            if contract.status != ContractStatus.ACTIVE:
                continue
            if contract.provider == partner_pubkey or contract.consumer == partner_pubkey:
                contract.record_health_check()

    def check_contracts(self) -> list[SymbiosisContract]:
        """Check all active contracts for timeouts. Returns list of newly broken contracts."""
        broken = []
        for contract in self.contracts.values():
            if contract.status == ContractStatus.ACTIVE:
                if contract.check_timeout():
                    broken.append(contract)
        return broken

    def get_active(self) -> list[SymbiosisContract]:
        return [c for c in self.contracts.values() if c.status == ContractStatus.ACTIVE]

    def get_composite_capabilities(self) -> list[str]:
        """Return composite capabilities from all active contracts."""
        return [c.composite_capability for c in self.contracts.values()
                if c.status == ContractStatus.ACTIVE and c.composite_capability]

    def remove_citizen(self, pubkey: str) -> list[SymbiosisContract]:
        """Break all contracts involving a citizen. Returns broken contracts."""
        broken = []
        for contract in self.contracts.values():
            if contract.status == ContractStatus.ACTIVE:
                if contract.provider == pubkey or contract.consumer == pubkey:
                    contract.status = ContractStatus.BROKEN
                    broken.append(contract)
        return broken

    def to_list(self) -> list[dict]:
        return [c.to_dict() for c in self.contracts.values()]

    @classmethod
    def from_list(cls, data: list[dict]) -> ContractManager:
        mgr = cls()
        for d in data:
            mgr.contracts[d["id"]] = SymbiosisContract.from_dict(d)
        return mgr
