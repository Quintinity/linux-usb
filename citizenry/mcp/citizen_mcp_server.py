"""Citizen-MCP server — three citizenry-mesh actions exposed over MCP.

This is the bridge between an MCP client (e.g. a Claude session) and the
local citizenry mesh. Three tools, no more:

  * ``get_status``       — listen on multicast for ~3s and snapshot the
                           heartbeats we hear: pubkey, last_seen, ONLINE/
                           DEGRADED/DEAD, emotional state, name.
  * ``propose_task``     — multicast a signed PROPOSE envelope wrapping a
                           Task body matching ``Task.from_propose_body``.
  * ``govern_update``    — load the EMEX Constitution as a raw dict, apply
                           a structured mutator, bump version, re-sign with
                           the canonical-JSON pattern from T21, and
                           multicast a GOVERN envelope.

Architectural choices (matching T21):

  * Standalone — owns its own UDP socket, signs with ``~/.citizenry/node.key``
    directly. No dependency on a long-running ``citizenry-surface.service``.
  * stdio transport for the MCP client. T27 (the Cell 3 orchestrator) will
    launch this as a subprocess.
  * Constitution signing copies the ``_sign_dict`` pattern from
    ``citizenry/cli/governor_emex_tablet.py`` verbatim. The
    ``Constitution.from_dict()`` round-trip would strip EMEX extension
    fields (``max_torque_pct``, ``max_voltage``, ``position_envelope``).

Mutator shapes accepted by ``govern_update``:

    {"set_servo_limits": {"max_torque_pct": 70, "max_voltage": 7.4}}
    {"law_id": "governor_torque_relax",
     "patch": {"params": {"currently_relaxed": true}}}
    {"add_law": {"id": "...", "description": "...", "params": {...}}}
    {"remove_law_id": "governor_paused"}

Run as a stdio MCP server::

    python -m citizenry.mcp.citizen_mcp_server
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import socket
import struct
import time
import uuid
from pathlib import Path
from typing import Any

import nacl.signing

from citizenry.identity import load_or_create_identity, pubkey_hex
from citizenry.protocol import (
    MULTICAST_GROUP,
    MULTICAST_PORT,
    Envelope,
    MessageType,
    make_envelope,
)


log = logging.getLogger("citizen.mcp")

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
DEFAULT_CONSTITUTION_PATH = (
    REPO_ROOT / "citizenry" / "governance" / "emex_constitution.json"
)

# Citizen heartbeat cadence the protocol layer enforces. We use this to
# decide whether a citizen we last heard from is ONLINE (≤ 2× interval),
# DEGRADED (≤ 3×), or DEAD (older than 3× — caller will rarely see DEAD
# since we're snapshotting a fresh listen window, but it can show up if
# the listener captures an out-of-date forwarded heartbeat).
HEARTBEAT_INTERVAL_S = 2.0

GET_STATUS_DEFAULT_S = 3.0
GET_STATUS_MAX_S = 10.0
GET_STATUS_MIN_S = 0.1


# ---------------------------------------------------------------------------
# Mesh adapter — owns the node key + the multicast socket
# ---------------------------------------------------------------------------


class MeshAdapter:
    """All mesh I/O for the three MCP tools.

    Held by ``CitizenMCPServer`` and reused across tool invocations so we
    don't pay a key-load + socket-open cost on every call.
    """

    def __init__(self, identity_name: str = "node") -> None:
        self.signing_key: nacl.signing.SigningKey = load_or_create_identity(identity_name)
        self.pubkey_hex: str = pubkey_hex(self.signing_key)

        # Reusable multicast send socket — same options as the T21 tablet.
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("b", 1)
        )
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

    # -- shared crypto ----------------------------------------------------

    def _sign_dict(self, c: dict[str, Any]) -> dict[str, Any]:
        """Sign a Constitution dict in place using the canonical-JSON pattern.

        Mirrors ``Constitution._signable_payload``: sorted keys, tight
        separators, signature field excluded. Keeps the EMEX extension
        fields intact (``max_torque_pct``, ``max_voltage``,
        ``position_envelope``) — see T21's ``governor_emex_tablet.py``.
        """
        c["governor_pubkey"] = self.signing_key.verify_key.encode().hex()
        payload = dict(c)
        payload.pop("signature", None)
        signable = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signed = self.signing_key.sign(signable)
        c["signature"] = signed.signature.hex()
        return c

    # -- send -------------------------------------------------------------

    def _multicast(self, env: Envelope) -> None:
        # Re-resolve module-level constants on every send so tests can
        # monkeypatch MULTICAST_GROUP / MULTICAST_PORT for hermeticism.
        try:
            self._sock.sendto(env.to_bytes(), (MULTICAST_GROUP, MULTICAST_PORT))
        except OSError as e:
            log.warning("multicast send failed (%s); not retrying", e)

    # -- propose_task -----------------------------------------------------

    def propose_task(
        self,
        task_type: str,
        params: dict[str, Any] | None = None,
        target_pubkey: str | None = None,
        priority: float = 0.5,
        required_capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build, sign, and multicast a PROPOSE envelope.

        The body matches ``citizenry.marketplace.Task.from_propose_body`` so
        any existing citizen running the marketplace handler can pick it up.
        """
        task_id = uuid.uuid4().hex[:12]
        body = {
            "task": task_type,
            "task_id": task_id,
            "priority": float(priority),
            "required_capabilities": required_capabilities or [],
            "required_skills": [],
            "params": params or {},
        }
        env = make_envelope(
            MessageType.PROPOSE,
            self.pubkey_hex,
            body,
            self.signing_key,
            recipient=target_pubkey or "*",
        )
        self._multicast(env)
        return {
            "task_id": task_id,
            "envelope_signature_short": env.signature[:8],
        }

    # -- govern_update ----------------------------------------------------

    def govern_update(
        self, path: str | Path, mutator: dict[str, Any]
    ) -> dict[str, Any]:
        """Load Constitution dict, apply mutator, re-sign, multicast GOVERN.

        Persists the amended document back to ``path`` so subsequent calls
        see the bumped version. The mutator schema is documented in the
        module docstring.
        """
        cpath = Path(path)
        with open(cpath) as f:
            c: dict[str, Any] = json.load(f)

        new = copy.deepcopy(c)
        new = _apply_mutator(new, mutator)
        new["version"] = int(c.get("version", 0)) + 1
        signed = self._sign_dict(new)

        env = make_envelope(
            MessageType.GOVERN,
            self.pubkey_hex,
            {"type": "constitution", "constitution": signed},
            self.signing_key,
            recipient="*",
        )
        self._multicast(env)

        # Persist so the next call sees the bumped version. Do this AFTER
        # the multicast — if writing fails we still emitted the amendment.
        try:
            cpath.write_text(json.dumps(signed, indent=2))
        except OSError as e:
            log.warning("could not persist amended constitution to %s: %s", cpath, e)

        return {
            "version": signed["version"],
            "envelope_signature_short": env.signature[:8],
        }

    # -- get_status -------------------------------------------------------

    def get_status(self, wait_seconds: float = GET_STATUS_DEFAULT_S) -> dict[str, Any]:
        """Listen for ``wait_seconds`` and snapshot the heartbeats heard.

        Opens its own listener socket — does NOT poke at any running
        citizen daemon. Returns a presence-tagged citizen list.
        """
        wait = max(GET_STATUS_MIN_S, min(GET_STATUS_MAX_S, float(wait_seconds)))

        listener = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("", MULTICAST_PORT))
        mreq = struct.pack(
            "4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY
        )
        listener.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Per-pubkey snapshot of the last heartbeat we saw.
        latest: dict[str, dict[str, Any]] = {}

        deadline = time.time() + wait
        try:
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                listener.settimeout(remaining)
                try:
                    data, _addr = listener.recvfrom(65535)
                except (socket.timeout, TimeoutError):
                    break
                try:
                    env = Envelope.from_bytes(data)
                except Exception:
                    continue
                if env.type != int(MessageType.HEARTBEAT):
                    continue
                # Drop our own heartbeats if we somehow appear on the wire.
                if env.sender == self.pubkey_hex:
                    continue
                latest[env.sender] = {
                    "pubkey": env.sender,
                    "last_seen": env.timestamp,
                    "name": env.body.get("name"),
                    "internal_state": env.body.get("state"),
                    "health": env.body.get("health"),
                    "emotional_state": env.body.get("emotional_state"),
                    "soul_mood": env.body.get("soul_mood"),
                    "growth_stage": env.body.get("growth_stage"),
                    "sleeping": env.body.get("sleeping"),
                }
        finally:
            try:
                listener.setsockopt(
                    socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq
                )
            except OSError:
                pass
            listener.close()

        now = time.time()
        citizens = []
        for pk, snap in latest.items():
            age = now - float(snap["last_seen"])
            if age <= 2 * HEARTBEAT_INTERVAL_S:
                state = "ONLINE"
            elif age <= 3 * HEARTBEAT_INTERVAL_S:
                state = "DEGRADED"
            else:
                state = "DEAD"
            citizens.append({**snap, "state": state, "age_seconds": age})

        # Sort by name for stable output (None names go last).
        citizens.sort(key=lambda c: (c.get("name") is None, c.get("name") or "", c["pubkey"]))

        return {
            "citizens": citizens,
            "snapshot_window_s": wait,
            "observer_pubkey": self.pubkey_hex,
            "captured_at": now,
        }


# ---------------------------------------------------------------------------
# Constitution mutator
# ---------------------------------------------------------------------------


def _apply_mutator(c: dict[str, Any], mutator: dict[str, Any]) -> dict[str, Any]:
    """Apply one of the supported mutator shapes to a Constitution dict."""
    if "set_servo_limits" in mutator:
        sl = c.setdefault("servo_limits", {})
        for k, v in mutator["set_servo_limits"].items():
            sl[k] = v

    if "law_id" in mutator and "patch" in mutator:
        law_id = mutator["law_id"]
        patch = mutator["patch"]
        laws = c.setdefault("laws", [])
        for i, law in enumerate(laws):
            if law.get("id") == law_id:
                laws[i] = _deep_merge(copy.deepcopy(law), patch)
                break
        else:
            # Law not found — append it with id baked in.
            laws.append(_deep_merge({"id": law_id}, patch))

    if "add_law" in mutator:
        c.setdefault("laws", []).append(copy.deepcopy(mutator["add_law"]))

    if "remove_law_id" in mutator:
        target = mutator["remove_law_id"]
        c["laws"] = [l for l in c.get("laws", []) if l.get("id") != target]

    return c


def _deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge src into dst (src wins). Returns dst."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------


class _ToolDescriptor:
    """Synchronous tool record for ``CitizenMCPServer.list_tools``.

    Mirrors the shape of the MCP SDK's own ``Tool`` (``.name`` + a JSON
    schema). The FastMCP-registered version is what serves stdio clients.
    """

    __slots__ = ("name", "description", "input_schema")

    def __init__(self, name: str, description: str, input_schema: dict[str, Any]) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema


class CitizenMCPServer:
    """FastMCP-backed server exposing the three citizenry mesh tools.

    Each tool is registered twice — once with FastMCP (so stdio JSON-RPC
    just works) and once as a sync handler (so tests and embedding callers
    can use ``s.list_tools()`` / ``s.call_tool_sync()`` without spinning up
    an MCP client).
    """

    def __init__(self, mesh: MeshAdapter | None = None) -> None:
        self.mesh = mesh or MeshAdapter()
        # Lazy import so ``mcp`` only loads when the server is actually built.
        from mcp.server.fastmcp import FastMCP

        self._mcp = FastMCP("citizen-mcp")
        self._tools: list[_ToolDescriptor] = []
        self._sync_handlers: dict[str, Any] = {}

        # Tool table: (name, description, json_schema, sync_handler, fastmcp_fn).
        # The two callables share a body for each tool (no behaviour drift).
        m = self.mesh
        default_path = str(DEFAULT_CONSTITUTION_PATH)

        def fmcp_get_status(wait_seconds: float = GET_STATUS_DEFAULT_S) -> dict[str, Any]:
            return m.get_status(wait_seconds=wait_seconds)

        def fmcp_propose_task(
            task_type: str,
            params: dict[str, Any] | None = None,
            target_pubkey: str | None = None,
            priority: float = 0.5,
            required_capabilities: list[str] | None = None,
        ) -> dict[str, Any]:
            return m.propose_task(
                task_type=task_type,
                params=params,
                target_pubkey=target_pubkey,
                priority=priority,
                required_capabilities=required_capabilities,
            )

        def fmcp_govern_update(
            mutator: dict[str, Any], path: str = default_path
        ) -> dict[str, Any]:
            return m.govern_update(path=path, mutator=mutator)

        for name, description, schema, sync, fmcp_fn in [
            (
                "get_status",
                "Listen for citizenry mesh heartbeats and return a presence snapshot.",
                {
                    "type": "object",
                    "properties": {
                        "wait_seconds": {
                            "type": "number",
                            "minimum": GET_STATUS_MIN_S,
                            "maximum": GET_STATUS_MAX_S,
                            "default": GET_STATUS_DEFAULT_S,
                        },
                    },
                    "additionalProperties": False,
                },
                lambda args: m.get_status(
                    wait_seconds=float(args.get("wait_seconds", GET_STATUS_DEFAULT_S))
                ),
                fmcp_get_status,
            ),
            (
                "propose_task",
                "Multicast a signed PROPOSE envelope onto the citizenry mesh.",
                {
                    "type": "object",
                    "properties": {
                        "task_type": {"type": "string"},
                        "params": {"type": "object"},
                        "target_pubkey": {"type": "string"},
                        "priority": {"type": "number", "default": 0.5},
                        "required_capabilities": {
                            "type": "array", "items": {"type": "string"},
                        },
                    },
                    "required": ["task_type"],
                    "additionalProperties": False,
                },
                lambda args: m.propose_task(
                    task_type=args["task_type"],
                    params=args.get("params"),
                    target_pubkey=args.get("target_pubkey"),
                    priority=float(args.get("priority", 0.5)),
                    required_capabilities=args.get("required_capabilities"),
                ),
                fmcp_propose_task,
            ),
            (
                "govern_update",
                (
                    "Apply a mutator to the EMEX Constitution, re-sign with the "
                    "canonical-JSON pattern, bump version, multicast a GOVERN "
                    "envelope. Mutator shapes: {set_servo_limits:{...}}, "
                    "{law_id, patch:{...}}, {add_law:{...}}, {remove_law_id}."
                ),
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": default_path},
                        "mutator": {"type": "object"},
                    },
                    "required": ["mutator"],
                    "additionalProperties": False,
                },
                lambda args: m.govern_update(
                    path=args.get("path", default_path),
                    mutator=args["mutator"],
                ),
                fmcp_govern_update,
            ),
        ]:
            self._tools.append(_ToolDescriptor(name, description, schema))
            self._sync_handlers[name] = sync
            self._mcp.tool(name=name, description=description)(fmcp_fn)

    # -- public sync API --------------------------------------------------

    def list_tools(self) -> list[_ToolDescriptor]:
        return list(self._tools)

    def call_tool_sync(self, name: str, args: dict[str, Any]) -> Any:
        """Invoke a tool by name with a JSON args dict (no MCP client needed)."""
        try:
            handler = self._sync_handlers[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc
        return handler(args)

    # -- MCP transport ----------------------------------------------------

    @property
    def fastmcp(self) -> Any:
        """Underlying FastMCP instance — for embedding into a parent server."""
        return self._mcp

    async def run_stdio(self) -> None:
        await self._mcp.run_stdio_async()


# ---------------------------------------------------------------------------
# Public factory + entry point
# ---------------------------------------------------------------------------


def build_server(identity_name: str = "node") -> CitizenMCPServer:
    """Build a citizen-mcp server. The default identity is the node key."""
    return CitizenMCPServer(mesh=MeshAdapter(identity_name=identity_name))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    srv = build_server()
    log.info("citizen-mcp ready; identity=%s", srv.mesh.pubkey_hex[:8])
    asyncio.run(srv.run_stdio())


if __name__ == "__main__":
    main()
