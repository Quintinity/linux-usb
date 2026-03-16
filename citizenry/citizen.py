"""Base Citizen Agent.

Every citizen has: identity, capabilities, heartbeat, discovery, message dispatch.
Subclass this to build specific citizen types (governor, manipulator, sensor).

v2.0 additions: skill tree, immune memory, mycelium warnings, genome,
symbiosis contracts — all integrated at the base level.
"""

import asyncio
import collections
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import nacl.signing
import nacl.encoding

from .identity import load_or_create_identity, pubkey_hex, short_id
from .protocol import (
    MessageType, Envelope, make_envelope,
    TTL_HEARTBEAT, TTL_TELEOP, TTL_GOVERN,
)
from .transport import MulticastTransport, UnicastTransport
from .skills import SkillTree
from .immune import ImmuneMemory, bootstrap_immune_memory, FaultPattern
from .mycelium import MyceliumNetwork, Warning, Severity
from .genome import CitizenGenome, save_genome, load_genome
from .symbiosis import ContractManager, SymbiosisContract, ContractStatus
from .emotional import EmotionalState, compute_emotional_state
from .will import CitizenWill, create_will


class Presence(Enum):
    """Neighbor presence state machine."""
    ONLINE = "online"           # Heartbeats arriving normally
    DEGRADED = "degraded"       # 3 missed heartbeats — warning
    PRESUMED_DEAD = "dead"      # 10 missed heartbeats — offline


@dataclass
class Neighbor:
    """A known citizen in the neighborhood."""
    pubkey: str
    name: str
    citizen_type: str
    capabilities: list[str]
    addr: tuple[str, int]       # (ip, unicast_port)
    health: float = 1.0
    last_seen: float = 0.0
    state: str = "unknown"
    presence: Presence = Presence.ONLINE
    missed_heartbeats: int = 0
    has_constitution: bool = False
    emotional_state: Any = None  # EmotionalState from heartbeat


@dataclass
class MessageLog:
    """Recent message log for dashboard display."""
    timestamp: str
    msg_type: str
    sender: str
    detail: str


class Citizen:
    """Base class for all citizens in the citizenry."""

    def __init__(
        self,
        name: str,
        citizen_type: str,
        capabilities: list[str],
        heartbeat_interval: float = 2.0,
    ):
        self.name = name
        self.citizen_type = citizen_type
        self.capabilities = capabilities
        self.heartbeat_interval = heartbeat_interval

        # Identity
        self._signing_key = load_or_create_identity(name)
        self.pubkey = pubkey_hex(self._signing_key)
        self.short_id = short_id(self.pubkey)

        # Neighbor table
        self.neighbors: dict[str, Neighbor] = {}

        # Transport
        self._multicast = MulticastTransport(self._on_message)
        self._unicast = UnicastTransport(self._on_message)

        # State
        self.health = 1.0
        self.state = "idle"
        self._running = False
        self._tasks: list[asyncio.Task] = []

        # Constitution
        self.constitution: dict | None = None
        self.constitution_received: bool = False

        # Message log (for dashboard)
        self.message_log: collections.deque[MessageLog] = collections.deque(maxlen=50)

        # Stats
        self.messages_sent = 0
        self.messages_received = 0
        self.start_time: float = 0

        # v2.0: Skill tree, immune memory, mycelium, genome, contracts
        self.skill_tree = SkillTree()
        self.immune_memory = bootstrap_immune_memory()
        self.mycelium = MyceliumNetwork()
        self.contracts = ContractManager()
        self.genome = CitizenGenome(
            citizen_name=name,
            citizen_type=citizen_type,
        )
        self.emotional_state = EmotionalState()
        self._tasks_completed_count = 0
        self._tasks_failed_count = 0

        # Message handlers — subclasses register additional handlers
        self._handlers: dict[int, list] = {
            MessageType.HEARTBEAT: [self._handle_heartbeat],
            MessageType.DISCOVER: [self._handle_discover],
            MessageType.ADVERTISE: [self._handle_advertise],
            MessageType.PROPOSE: [self._handle_propose],
            MessageType.ACCEPT_REJECT: [self._handle_accept_reject],
            MessageType.REPORT: [self._handle_report],
            MessageType.GOVERN: [self._handle_govern],
        }

    def on(self, msg_type: MessageType, handler):
        """Register an additional handler for a message type."""
        self._handlers.setdefault(int(msg_type), []).append(handler)

    async def start(self):
        """Start the citizen agent."""
        loop = asyncio.get_event_loop()
        await self._multicast.start(loop)
        await self._unicast.start(loop)

        self._running = True
        self.start_time = time.time()
        self._log(f"citizen born — {self.citizen_type} [{self.short_id}]")
        self._log(f"unicast port: {self._unicast.bound_port}")

        # Load persisted state
        self._load_persisted_state()

        # Start mDNS advertisement
        await self._start_mdns()

        # Start background tasks
        self._tasks.append(asyncio.create_task(self._heartbeat_loop()))
        self._tasks.append(asyncio.create_task(self._presence_loop()))

        # Initial discovery broadcast
        await self._send_discover()

    async def stop(self):
        """Stop the citizen agent."""
        self._running = False
        # v3.0: Broadcast will before going offline
        try:
            will = create_will(self)
            body = will.to_report_body()
            env = make_envelope(
                MessageType.REPORT, self.pubkey, body, self._signing_key,
            )
            self._multicast.send(env)
            self._log(f"will broadcast — {will.reason}")
        except Exception:
            pass
        # Broadcast a final "going offline" heartbeat
        try:
            self.state = "offline"
            self._send_heartbeat()
        except Exception:
            pass
        # Persist state for next restart
        self._save_persisted_state()
        # Stop mDNS
        await self._stop_mdns()
        for t in self._tasks:
            t.cancel()
        self._multicast.close()
        self._unicast.close()
        self._log("citizen stopped")

    # ── Outbound messages ──

    async def _send_discover(self):
        """Broadcast: who is out there?"""
        env = make_envelope(
            MessageType.DISCOVER,
            self.pubkey,
            {"name": self.name, "type": self.citizen_type, "unicast_port": self._unicast.bound_port},
            self._signing_key,
        )
        self._multicast.send(env)
        self.messages_sent += 1
        self._log("DISCOVER broadcast")

    def _send_advertise(self, recipient: str = "*", addr: tuple | None = None):
        """Advertise capabilities — broadcast or directed."""
        env = make_envelope(
            MessageType.ADVERTISE,
            self.pubkey,
            {
                "name": self.name,
                "type": self.citizen_type,
                "capabilities": self.capabilities,
                "health": self.health,
                "state": self.state,
                "unicast_port": self._unicast.bound_port,
                "has_constitution": self.constitution_received,
            },
            self._signing_key,
            recipient=recipient,
        )
        if addr:
            self._unicast.send(env, addr)
        else:
            self._multicast.send(env)
        self.messages_sent += 1

    def _send_heartbeat(self):
        """Broadcast heartbeat with current state + v2.0 data."""
        body = {
            "name": self.name,
            "state": self.state,
            "health": self.health,
            "unicast_port": self._unicast.bound_port,
            "uptime": time.time() - self.start_time,
        }
        # v2.0: piggyback warnings on slow channel
        slow_warnings = self.mycelium.get_slow_channel_payload()
        if slow_warnings:
            body["warnings"] = slow_warnings
        # v2.0: include active contract IDs for health monitoring
        active_contracts = [c.id for c in self.contracts.get_active()]
        if active_contracts:
            body["contracts"] = active_contracts
        # v2.0: decay old warnings
        self.mycelium.decay_warnings()
        # v3.0: emotional state
        uptime_hrs = (time.time() - self.start_time) / 3600 if self.start_time else 0
        self.emotional_state = compute_emotional_state(
            uptime_hours=uptime_hrs,
            warning_count=self.mycelium.active_count(),
            tasks_completed=self._tasks_completed_count,
            tasks_failed=self._tasks_failed_count,
            novel_neighbors=len([n for n in self.neighbors.values() if time.time() - n.last_seen < 60]),
        )
        body["emotional_state"] = self.emotional_state.to_dict()

        env = make_envelope(
            MessageType.HEARTBEAT,
            self.pubkey,
            body,
            self._signing_key,
        )
        self._multicast.send(env)
        self.messages_sent += 1

    def send_propose(self, recipient: str, task: dict, addr: tuple):
        """Send a task proposal to a specific citizen."""
        env = make_envelope(
            MessageType.PROPOSE,
            self.pubkey,
            task,
            self._signing_key,
            recipient=recipient,
        )
        self._unicast.send(env, addr)
        self.messages_sent += 1
        self._add_log("PROPOSE", self.name, f"task={task.get('task', '?')} → {short_id(recipient)}")

    def send_accept(self, recipient: str, proposal_body: dict, addr: tuple):
        """Accept a proposal."""
        env = make_envelope(
            MessageType.ACCEPT_REJECT,
            self.pubkey,
            {"accepted": True, "task": proposal_body.get("task", ""), "reason": "capable and available"},
            self._signing_key,
            recipient=recipient,
        )
        self._unicast.send(env, addr)
        self.messages_sent += 1
        self._add_log("ACCEPT", self.name, f"task={proposal_body.get('task', '?')}")

    def send_reject(self, recipient: str, reason: str, addr: tuple):
        """Reject a proposal."""
        env = make_envelope(
            MessageType.ACCEPT_REJECT,
            self.pubkey,
            {"accepted": False, "reason": reason},
            self._signing_key,
            recipient=recipient,
        )
        self._unicast.send(env, addr)
        self.messages_sent += 1
        self._add_log("REJECT", self.name, f"reason={reason}")

    def send_report(self, recipient: str, report: dict, addr: tuple):
        """Send a task report."""
        env = make_envelope(
            MessageType.REPORT,
            self.pubkey,
            report,
            self._signing_key,
            recipient=recipient,
        )
        self._unicast.send(env, addr)
        self.messages_sent += 1

    def send_govern(self, recipient: str, governance: dict, addr: tuple):
        """Send a governance message (constitution, laws, commands)."""
        env = make_envelope(
            MessageType.GOVERN,
            self.pubkey,
            governance,
            self._signing_key,
            recipient=recipient,
            ttl=TTL_GOVERN,
        )
        self._unicast.send(env, addr)
        self.messages_sent += 1
        self._add_log("GOVERN", self.name, f"type={governance.get('type', '?')} → {short_id(recipient)}")

    def send_teleop(self, recipient: str, positions: dict, addr: tuple):
        """Send teleop positions — short TTL, high frequency."""
        env = make_envelope(
            MessageType.PROPOSE,
            self.pubkey,
            {"task": "teleop_frame", "positions": positions},
            self._signing_key,
            recipient=recipient,
            ttl=TTL_TELEOP,
        )
        self._unicast.send(env, addr)
        self.messages_sent += 1

    # ── Inbound message dispatch ──

    def _on_message(self, env: Envelope, addr: tuple):
        """Called by transport layer for every received message."""
        # Drop our own messages
        if env.sender == self.pubkey:
            return
        # Drop expired
        if env.is_expired():
            return
        # Drop messages not addressed to us or broadcast
        if env.recipient != "*" and env.recipient != self.pubkey:
            return
        # Verify signature
        try:
            vk = nacl.signing.VerifyKey(bytes.fromhex(env.sender))
            if not env.verify(vk):
                self._log(f"BAD SIGNATURE from {short_id(env.sender)}")
                return
        except Exception:
            return

        self.messages_received += 1

        # Dispatch to handlers
        handlers = self._handlers.get(env.type, [])
        for handler in handlers:
            try:
                handler(env, addr)
            except Exception as e:
                self._log(f"handler error: {e}")

    # ── Default handlers ──

    def _handle_heartbeat(self, env: Envelope, addr: tuple):
        sender = env.sender
        if sender in self.neighbors:
            n = self.neighbors[sender]
            n.last_seen = time.time()
            n.health = env.body.get("health", 1.0)
            n.state = env.body.get("state", "unknown")
            n.addr = (addr[0], env.body.get("unicast_port", addr[1]))
            # v3.0: parse emotional state from heartbeat
            emo_data = env.body.get("emotional_state")
            if emo_data:
                n.emotional_state = EmotionalState.from_dict(emo_data)
            # Reset presence on heartbeat
            if n.presence != Presence.ONLINE:
                self._log(f"NEIGHBOR BACK: {n.name} [{short_id(sender)}] — was {n.presence.value}")
                self._add_log("PRESENCE", n.name, "back online")
            n.presence = Presence.ONLINE
            n.missed_heartbeats = 0
            # v2.0: process slow-channel warnings from heartbeat
            for w_data in env.body.get("warnings", []):
                try:
                    w = Warning.from_report_body(w_data)
                    w.source_citizen = sender
                    self.mycelium.add_warning(w)
                except Exception:
                    pass
            # v2.0: record contract health check
            self.contracts.record_health(sender)

    def _handle_discover(self, env: Envelope, addr: tuple):
        self._log(f"DISCOVER from {env.body.get('name', '?')} [{short_id(env.sender)}]")
        self._add_log("DISCOVER", env.body.get("name", "?"), f"[{short_id(env.sender)}]")
        # Reply via unicast AND broadcast so both sides always learn about each other
        reply_port = env.body.get("unicast_port", addr[1])
        reply_addr = (addr[0], reply_port)
        self._send_advertise(recipient=env.sender, addr=reply_addr)
        self._send_advertise()  # Also broadcast for anyone else listening

    def _handle_advertise(self, env: Envelope, addr: tuple):
        sender = env.sender
        body = env.body
        unicast_port = body.get("unicast_port", addr[1])
        n = Neighbor(
            pubkey=sender,
            name=body.get("name", "unknown"),
            citizen_type=body.get("type", "unknown"),
            capabilities=body.get("capabilities", []),
            addr=(addr[0], unicast_port),
            health=body.get("health", 1.0),
            last_seen=time.time(),
            state=body.get("state", "idle"),
            has_constitution=body.get("has_constitution", False),
        )
        is_new = sender not in self.neighbors
        self.neighbors[sender] = n
        if is_new:
            self._log(f"NEW NEIGHBOR: {n.name} [{short_id(sender)}] @ {n.addr} — {n.capabilities}")
            self._add_log("ADVERTISE", n.name, f"joined — {', '.join(n.capabilities)}")
            # Handshake: reply with our own ADVERTISE so they learn about us too
            self._send_advertise(recipient=sender, addr=n.addr)
            self._on_neighbor_joined(n)

    def _handle_propose(self, env: Envelope, addr: tuple):
        """Override in subclass for task handling."""
        pass

    def _handle_accept_reject(self, env: Envelope, addr: tuple):
        """Override in subclass."""
        pass

    def _handle_report(self, env: Envelope, addr: tuple):
        """Base report handling — v2.0 warning and immune share processing."""
        body = env.body
        report_type = body.get("type", "")

        if report_type == "warning":
            try:
                w = Warning.from_report_body(body)
                w.source_citizen = env.sender
                self.mycelium.add_warning(w)
                self._add_log("WARNING", short_id(env.sender),
                              f"{body.get('severity', '?')}: {body.get('detail', '?')}")
            except Exception:
                pass

        elif report_type == "immune_share":
            patterns = body.get("patterns", [])
            fault_patterns = [FaultPattern.from_dict(p) for p in patterns]
            added = self.immune_memory.merge(fault_patterns)
            if added > 0:
                self._log(f"immune memory: merged {added} new patterns from [{short_id(env.sender)}]")
                self._add_log("IMMUNE", short_id(env.sender), f"+{added} patterns")

    def _handle_govern(self, env: Envelope, addr: tuple):
        """Base governance handling — constitution and law updates."""
        body = env.body
        gov_type = body.get("type", "")

        if gov_type == "constitution":
            self.constitution = body.get("constitution")
            self.constitution_received = True
            self._log(f"CONSTITUTION received from [{short_id(env.sender)}] — v{self.constitution.get('version', '?')}")
            self._add_log("GOVERN", short_id(env.sender), "constitution received")
            self._on_constitution_received(env.sender, self.constitution)

        elif gov_type == "law_update":
            law_id = body.get("law_id", "")
            params = body.get("params", {})
            self._log(f"LAW UPDATE from [{short_id(env.sender)}]: {law_id} = {params}")
            self._add_log("GOVERN", short_id(env.sender), f"law: {law_id}")
            self._on_law_updated(env.sender, law_id, params)

        elif gov_type == "emergency_stop":
            self._log(f"EMERGENCY STOP from [{short_id(env.sender)}]")
            self._add_log("SAFETY", short_id(env.sender), "EMERGENCY STOP")
            self._on_emergency_stop(env.sender)

        elif gov_type == "policy_canary":
            self._log(f"CANARY policy from [{short_id(env.sender)}]")
            self._handle_policy_canary(env, body)

        elif gov_type == "policy_commit":
            self._log(f"POLICY COMMITTED from [{short_id(env.sender)}]")
            self._add_log("GOVERN", short_id(env.sender), "policy committed")

        elif gov_type == "policy_rollback":
            self._log(f"POLICY ROLLBACK from [{short_id(env.sender)}]")
            self._add_log("GOVERN", short_id(env.sender), "policy rolled back")

        elif gov_type == "genome":
            genome_data = body.get("genome", {})
            try:
                genome = CitizenGenome.from_dict(genome_data)
                if genome.version >= self.genome.version:
                    # Merge: keep our XP, take their calibration/immune/skills
                    self.genome.calibration = genome.calibration
                    self.genome.protection = genome.protection
                    self.genome.skill_definitions = genome.skill_definitions
                    self.immune_memory.merge(
                        [FaultPattern.from_dict(p) for p in genome.immune_memory]
                    )
                    self._log(f"genome received from [{short_id(env.sender)}] — v{genome.version}")
                    self._add_log("GOVERN", short_id(env.sender), f"genome v{genome.version}")
            except Exception as e:
                self._log(f"genome processing failed: {e}")

        elif gov_type == "skill_tree":
            definitions = body.get("definitions", {})
            try:
                from .skills import SkillDef
                skill_defs = {k: SkillDef.from_dict(v) for k, v in definitions.items()}
                self.skill_tree.merge_definitions(skill_defs)
                self._log(f"skill tree updated: {len(skill_defs)} skills from [{short_id(env.sender)}]")
                self._add_log("GOVERN", short_id(env.sender), f"skills: {len(skill_defs)} defs")
            except Exception as e:
                self._log(f"skill tree processing failed: {e}")

    def _on_neighbor_joined(self, neighbor: Neighbor):
        """Override in subclass to react to new neighbors."""
        pass

    def _on_neighbor_presence_changed(self, neighbor: Neighbor, old_presence: Presence):
        """Override in subclass to react to presence changes."""
        pass

    def _on_constitution_received(self, sender: str, constitution: dict):
        """Override in subclass to apply constitution (e.g., write servo limits)."""
        pass

    def _on_law_updated(self, sender: str, law_id: str, params: dict):
        """Override in subclass to apply law changes."""
        pass

    def _on_emergency_stop(self, sender: str):
        """Override in subclass to handle emergency stop."""
        pass

    def _run_self_test(self) -> tuple[bool, str]:
        """Run a self-test to verify citizen is functioning.

        Override in subclass for hardware-specific tests.
        Returns (passed, detail_message).
        """
        return True, "base self-test passed"

    def _handle_policy_canary(self, env, body):
        """Handle a canary policy update — apply, self-test, report."""
        # Save rollback snapshot
        rollback_laws = dict(getattr(self, 'laws', {})) if hasattr(self, 'laws') else {}
        rollback_constitution = dict(self.constitution) if self.constitution else {}

        # Apply the policy
        policy_data = body.get("policy_data", {})
        law_id = policy_data.get("law_id", "")
        params = policy_data.get("params", {})
        if law_id:
            self._on_law_updated(env.sender, law_id, params)

        # Run self-test
        passed, detail = self._run_self_test()

        if not passed:
            # Revert
            if hasattr(self, 'laws') and law_id in rollback_laws:
                self._on_law_updated(env.sender, law_id, rollback_laws[law_id])
            self._log(f"canary FAILED — reverted: {detail}")

        # Report result
        report = {
            "type": "canary_result",
            "citizen": self.name,
            "passed": passed,
            "detail": detail,
            "rollout_id": body.get("rollout_id", ""),
        }
        sender_addr = None
        if env.sender in self.neighbors:
            sender_addr = self.neighbors[env.sender].addr
        if sender_addr:
            self.send_report(env.sender, report, sender_addr)

    # ── Background loops ──

    async def _heartbeat_loop(self):
        while self._running:
            self._send_heartbeat()
            await asyncio.sleep(self.heartbeat_interval)

    async def _presence_loop(self):
        """Track neighbor presence — escalate from online → degraded → dead."""
        while self._running:
            await asyncio.sleep(self.heartbeat_interval)
            now = time.time()
            for k, n in list(self.neighbors.items()):
                if n.last_seen == 0:
                    continue
                silence = now - n.last_seen
                missed = int(silence / self.heartbeat_interval)
                old_presence = n.presence

                if missed >= 10 and n.presence != Presence.PRESUMED_DEAD:
                    n.presence = Presence.PRESUMED_DEAD
                    n.missed_heartbeats = missed
                    self._log(f"NEIGHBOR DEAD: {n.name} [{short_id(k)}] — {missed} missed heartbeats")
                    self._add_log("PRESENCE", n.name, f"presumed dead ({missed} missed)")
                    self._on_neighbor_presence_changed(n, old_presence)
                elif 3 <= missed < 10 and n.presence == Presence.ONLINE:
                    n.presence = Presence.DEGRADED
                    n.missed_heartbeats = missed
                    self._log(f"NEIGHBOR DEGRADED: {n.name} [{short_id(k)}] — {missed} missed heartbeats")
                    self._add_log("PRESENCE", n.name, f"degraded ({missed} missed)")
                    self._on_neighbor_presence_changed(n, old_presence)

            # Remove truly dead neighbors after 30 missed heartbeats
            dead = [
                k for k, v in self.neighbors.items()
                if v.presence == Presence.PRESUMED_DEAD
                and now - v.last_seen > self.heartbeat_interval * 30
            ]
            for k in dead:
                n = self.neighbors.pop(k)
                self._log(f"NEIGHBOR REMOVED: {n.name} [{short_id(k)}] — timed out")
                self._add_log("PRESENCE", n.name, "removed (timeout)")

    # ── mDNS ──

    async def _start_mdns(self):
        """Start mDNS service advertisement."""
        try:
            from .mdns import CitizenMDNS
            self._mdns = CitizenMDNS(
                self.name, self.citizen_type, self.pubkey,
                self._unicast.bound_port, self.capabilities,
            )
            self._mdns.on_neighbor_found = self._on_mdns_neighbor_found
            await self._mdns.start()
            self._log("mDNS advertising")
        except Exception as e:
            self._log(f"mDNS failed: {e} — UDP discovery only")
            self._mdns = None

    async def _stop_mdns(self):
        if hasattr(self, '_mdns') and self._mdns:
            try:
                await self._mdns.stop()
            except Exception:
                pass

    def _on_mdns_neighbor_found(self, name, citizen_type, pubkey_short, addr, port, capabilities):
        """mDNS found a neighbor — trigger UDP discovery to exchange full details."""
        self._log(f"mDNS found: {name} ({citizen_type}) @ {addr}:{port}")
        # Send a directed ADVERTISE to bootstrap the full protocol handshake
        self._send_advertise(addr=(addr, port))

    # ── Persistence ──

    def _load_persisted_state(self):
        """Load persisted neighbor table, constitution, and v2.0 state from disk."""
        try:
            from .persistence import load_neighbors, load_constitution
            saved = load_neighbors(self.name)
            if saved:
                self._log(f"loaded {len(saved)} persisted neighbors")
                for pubkey, record in saved.items():
                    addr = tuple(record.last_addr) if record.last_addr else None
                    if addr:
                        self._send_advertise(addr=addr)

            saved_const = load_constitution(self.name)
            if saved_const and not self.constitution_received:
                self.constitution = saved_const
                self.constitution_received = True
                self._log(f"loaded persisted constitution v{saved_const.get('version', '?')}")
        except Exception:
            pass

        # v2.0: load genome (includes XP, immune memory, skills)
        try:
            saved_genome = load_genome(self.name)
            if saved_genome:
                self.genome = saved_genome
                self.skill_tree.xp = dict(saved_genome.xp)
                if saved_genome.immune_memory:
                    self.immune_memory.merge(
                        [FaultPattern.from_dict(p) for p in saved_genome.immune_memory]
                    )
                if saved_genome.skill_definitions:
                    from .skills import SkillDef
                    defs = {k: SkillDef.from_dict(v) for k, v in saved_genome.skill_definitions.items()}
                    self.skill_tree.merge_definitions(defs)
                self._log(f"genome loaded — v{saved_genome.version}, {len(saved_genome.xp)} XP entries")
        except Exception:
            pass

        # v2.0: load contracts
        try:
            from .persistence import load_contracts
            from .symbiosis import ContractManager
            saved_contracts = load_contracts(self.name)
            if saved_contracts:
                self.contracts = ContractManager.from_list(saved_contracts)
                self._log(f"loaded {len(saved_contracts)} persisted contracts")
        except Exception:
            pass

    def _save_persisted_state(self):
        """Save neighbor table, constitution, and v2.0 state to disk."""
        try:
            from .persistence import save_neighbors, save_constitution, NeighborRecord
            records = {}
            for pubkey, n in self.neighbors.items():
                records[pubkey] = NeighborRecord(
                    pubkey=n.pubkey,
                    name=n.name,
                    citizen_type=n.citizen_type,
                    capabilities=n.capabilities,
                    last_addr=list(n.addr),
                    last_seen=n.last_seen,
                    has_constitution=n.has_constitution,
                )
            save_neighbors(self.name, records)

            if self.constitution:
                save_constitution(self.name, self.constitution)
        except Exception:
            pass

        # v2.0: save genome with current XP, immune memory, skill definitions
        try:
            self.genome.xp = dict(self.skill_tree.xp)
            self.genome.immune_memory = self.immune_memory.to_list()
            self.genome.skill_definitions = {
                k: v.to_dict() for k, v in self.skill_tree.definitions.items()
            }
            self.genome.version += 1
            save_genome(self.genome)
        except Exception:
            pass

        # v2.0: save contracts
        try:
            from .persistence import save_contracts
            contracts_data = self.contracts.to_list()
            if contracts_data:
                save_contracts(self.name, contracts_data)
        except Exception:
            pass

    # ── Logging ──

    def _add_log(self, msg_type: str, sender: str, detail: str):
        """Add to the message log (for dashboard)."""
        self.message_log.append(MessageLog(
            timestamp=time.strftime("%H:%M:%S"),
            msg_type=msg_type,
            sender=sender,
            detail=detail,
        ))

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [{self.name}] {msg}")
