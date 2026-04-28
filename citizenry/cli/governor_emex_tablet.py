"""EMEX 2026 tablet governor — live Constitution amendments from an iPad.

A tiny aiohttp server that serves a single-page touch UI (companion file
``governor_emex_web.html``). The page exposes three buttons that POST signed
Constitution amendments to ``/amend/relax``, ``/amend/restrict``, ``/amend/pause``.
Each handler:

  1. Loads the EMEX Constitution from ``citizenry/governance/emex_constitution.json``
     (or the in-memory mutated copy from a prior amendment).
  2. Mutates the relevant servo limit / law (max_torque_pct = 75 / 50, or pinned
     position envelope + paused law).
  3. Bumps ``version`` and re-signs the whole document with the GovernorNode's
     Ed25519 key from ``~/.citizenry/node.key``.
  4. Multicasts a GOVERN envelope ``{"type":"constitution","constitution": <dict>}``
     to ``239.67.84.90:7770`` — same wire format ``SurfaceCitizen`` uses on join
     (see ``citizenry/surface_citizen.py`` line ~142).

The ``relax`` handler also schedules an auto-revert task that fires after
``governor_torque_relax.auto_revert_seconds`` (300s by default) and re-broadcasts
the pre-relax Constitution so the visitor-safe 60% cap returns automatically.

This server does NOT depend on the long-running ``citizenry-surface.service``.
It owns its own UDP socket and signs with the node key directly, so the demo
operator can run it ad hoc on the tablet-attached laptop.

Usage::

    ~/lerobot-env/bin/python -m citizenry.cli.governor_emex_tablet
    # then point an iPad on the same WiFi at the printed URL.

For the EMEX hardware-rehearsal task (T24): the URL printed at startup is the
LAN IP of the GovernorNode (resolved by opening a UDP socket toward 8.8.8.8 and
reading the local sockname). The operator types it into Safari on the iPad —
or scans the QR code if the optional ``qrcode`` package is installed.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import logging
import socket
import struct
import time
from pathlib import Path
from typing import Any

from aiohttp import web

from citizenry.identity import load_or_create_identity, pubkey_hex
from citizenry.protocol import (
    MULTICAST_GROUP,
    MULTICAST_PORT,
    MessageType,
    make_envelope,
)


log = logging.getLogger("emex.tablet")

# Default deployment files. Resolved relative to this source tree so the
# tablet UI works without any environment configuration.
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
EMEX_CONSTITUTION_PATH = REPO_ROOT / "citizenry" / "governance" / "emex_constitution.json"
HTML_PATH = HERE / "governor_emex_web.html"

# EMEX safety caps — visitor-facing, non-negotiable upper bounds.
TORQUE_PCT_DEFAULT = 60   # baseline
TORQUE_PCT_RELAXED = 75   # gated by governor_torque_relax law
TORQUE_PCT_RESTRICTED = 50

# Pause-amendment law id — citizens look for this in laws[] to halt motion.
PAUSE_LAW_ID = "governor_paused"


# ---------------------------------------------------------------------------
# Server state
# ---------------------------------------------------------------------------


class GovernorTabletServer:
    """Holds the in-memory Constitution + node identity for the tablet UI.

    Single-process, single-tab assumption: there is exactly one operator at
    the EMEX stand. We don't bother with file locks or multi-writer races.
    """

    def __init__(
        self,
        constitution_path: Path = EMEX_CONSTITUTION_PATH,
        identity_name: str = "node",
    ):
        self.constitution_path = constitution_path
        self.signing_key = load_or_create_identity(identity_name)
        self.pubkey_hex = pubkey_hex(self.signing_key)

        # Load the EMEX Constitution as a plain dict so we can patch arbitrary
        # fields (the dataclass doesn't carry max_torque_pct / position_envelope).
        with open(self.constitution_path) as f:
            self._baseline_dict: dict[str, Any] = json.load(f)

        # Current state — starts as a fresh signed copy of the baseline.
        self.current_dict: dict[str, Any] = self._sign_dict(
            copy.deepcopy(self._baseline_dict)
        )
        self.last_amend_at: float = time.time()
        self.last_amend_label: str = "baseline"

        # Auto-revert bookkeeping for the relax button.
        self._revert_task: asyncio.Task | None = None
        self._revert_due_at: float | None = None

        # Multicast socket. We open one ad-hoc UDP socket and reuse it.
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL,
                              struct.pack("b", 1))
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

    # -- crypto -----------------------------------------------------------

    def _sign_dict(self, c: dict[str, Any]) -> dict[str, Any]:
        """Sign a Constitution dict in place using the node key.

        We can't use Constitution.sign() directly because the EMEX schema
        carries extra ServoLimits fields (max_torque_pct, max_voltage,
        position_envelope) and extension top-level keys (deployment,
        deployment_notes) that the wire-level dataclass doesn't model.

        Instead we mirror Constitution._signable_payload(): canonical JSON
        with sorted keys and tight separators, signature field excluded.
        """
        c["governor_pubkey"] = self.signing_key.verify_key.encode().hex()
        payload = dict(c)
        payload.pop("signature", None)
        signable = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signed = self.signing_key.sign(signable)
        c["signature"] = signed.signature.hex()
        return c

    # -- amendments -------------------------------------------------------

    def _next_version(self) -> int:
        return int(self.current_dict.get("version", 1)) + 1

    def _broadcast(self, c: dict[str, Any], label: str) -> dict[str, Any]:
        """Multicast a GOVERN envelope wrapping the signed Constitution."""
        env = make_envelope(
            MessageType.GOVERN,
            self.pubkey_hex,
            {"type": "constitution", "constitution": c},
            self.signing_key,
            recipient="*",
        )
        try:
            self._sock.sendto(env.to_bytes(), (MULTICAST_GROUP, MULTICAST_PORT))
        except OSError as e:
            # Network might be down at the stand; we still update local state
            # so the tablet UI reflects what was attempted.
            log.warning("multicast send failed (%s); state updated locally only", e)

        self.current_dict = c
        self.last_amend_at = time.time()
        self.last_amend_label = label
        log.info("amendment %r v%d applied, sig=%s",
                 label, c["version"], c["signature"][:8])
        return {
            "label": label,
            "version": c["version"],
            "signature": c["signature"],
            "envelope_signature": env.signature,
        }

    def _cancel_revert(self):
        if self._revert_task and not self._revert_task.done():
            self._revert_task.cancel()
        self._revert_task = None
        self._revert_due_at = None

    async def _scheduled_revert(self, snapshot: dict[str, Any], delay_s: float):
        """Restore the pre-relax Constitution after `delay_s`."""
        try:
            await asyncio.sleep(delay_s)
        except asyncio.CancelledError:
            return
        # Re-sign with a bumped version so receivers treat it as a new amendment.
        reverted = copy.deepcopy(snapshot)
        reverted["version"] = self._next_version()
        self._broadcast(self._sign_dict(reverted), "auto-revert")
        self._revert_due_at = None

    # -- public amendment API --------------------------------------------

    def apply_relax(self, loop: asyncio.AbstractEventLoop) -> dict[str, Any]:
        """Bump max_torque_pct to 75% and schedule a 300s auto-revert."""
        # Snapshot of the *baseline* (60%) to revert to, not whatever's current.
        revert_target = copy.deepcopy(self._baseline_dict)

        new = copy.deepcopy(self.current_dict)
        new["servo_limits"]["max_torque_pct"] = TORQUE_PCT_RELAXED
        new["version"] = self._next_version()
        # Strip any pause-law that might be in place; relax overrides pause.
        new["laws"] = [l for l in new.get("laws", []) if l.get("id") != PAUSE_LAW_ID]
        signed = self._sign_dict(new)

        result = self._broadcast(signed, "relax-75")

        # Auto-revert: read the law's auto_revert_seconds if present.
        revert_secs = 300.0
        for l in new.get("laws", []):
            if l.get("id") == "governor_torque_relax":
                revert_secs = float(l.get("params", {}).get("auto_revert_seconds", 300))
                break

        self._cancel_revert()
        self._revert_due_at = time.time() + revert_secs
        self._revert_task = loop.create_task(
            self._scheduled_revert(revert_target, revert_secs)
        )
        result["auto_revert_at"] = self._revert_due_at
        return result

    def apply_restrict(self) -> dict[str, Any]:
        """Drop max_torque_pct to 50%. Manual revert only."""
        self._cancel_revert()
        new = copy.deepcopy(self.current_dict)
        new["servo_limits"]["max_torque_pct"] = TORQUE_PCT_RESTRICTED
        new["version"] = self._next_version()
        new["laws"] = [l for l in new.get("laws", []) if l.get("id") != PAUSE_LAW_ID]
        return self._broadcast(self._sign_dict(new), "restrict-50")

    def apply_pause(self) -> dict[str, Any]:
        """Halt new motion: pin every axis to its envelope midpoint
        and add a ``governor_paused`` Law citizens can read.

        Citizens that respect the position envelope will reject every new
        commanded position not inside the (now zero-width) envelope, which
        effectively freezes the arm. The law itself is the human-readable
        signal so dashboards can render "PAUSED".
        """
        self._cancel_revert()
        new = copy.deepcopy(self.current_dict)

        env = new["servo_limits"].get("position_envelope", {}) or {}
        pinned = {}
        for axis, lim in env.items():
            mid = (float(lim["min_deg"]) + float(lim["max_deg"])) / 2.0
            pinned[axis] = {"min_deg": mid, "max_deg": mid}
        new["servo_limits"]["position_envelope"] = pinned

        # Add or replace the pause Law.
        laws = [l for l in new.get("laws", []) if l.get("id") != PAUSE_LAW_ID]
        laws.append({
            "id": PAUSE_LAW_ID,
            "description": "Operator-initiated pause from the EMEX tablet UI.",
            "params": {"paused": True, "reason": "tablet-pause-button"},
        })
        new["laws"] = laws
        new["version"] = self._next_version()
        return self._broadcast(self._sign_dict(new), "pause")

    # -- read-only state for the UI --------------------------------------

    def state_snapshot(self) -> dict[str, Any]:
        sl = self.current_dict.get("servo_limits", {})
        env = sl.get("position_envelope", {}) or {}
        env_summary = ", ".join(
            f"{axis}:[{lim['min_deg']:.0f}..{lim['max_deg']:.0f}]"
            for axis, lim in env.items()
        ) or "(unset)"
        is_paused = any(
            l.get("id") == PAUSE_LAW_ID for l in self.current_dict.get("laws", [])
        )
        return {
            "version": self.current_dict.get("version"),
            "deployment": self.current_dict.get("deployment", "?"),
            "max_torque_pct": sl.get("max_torque_pct"),
            "max_voltage": sl.get("max_voltage"),
            "position_envelope_summary": env_summary,
            "paused": is_paused,
            "last_amend_label": self.last_amend_label,
            "last_amend_at": self.last_amend_at,
            "last_amend_signature_short": self.current_dict.get("signature", "")[:8],
            "governor_pubkey_short": self.current_dict.get("governor_pubkey", "")[:8],
            "auto_revert_at": self._revert_due_at,
            "now": time.time(),
        }


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------


async def _index(request: web.Request) -> web.Response:
    return web.Response(text=HTML_PATH.read_text(), content_type="text/html")


async def _state(request: web.Request) -> web.Response:
    srv: GovernorTabletServer = request.app["srv"]
    return web.json_response(srv.state_snapshot())


async def _amend_relax(request: web.Request) -> web.Response:
    srv: GovernorTabletServer = request.app["srv"]
    result = srv.apply_relax(asyncio.get_running_loop())
    return web.json_response({"ok": True, "result": result, "state": srv.state_snapshot()})


async def _amend_restrict(request: web.Request) -> web.Response:
    srv: GovernorTabletServer = request.app["srv"]
    result = srv.apply_restrict()
    return web.json_response({"ok": True, "result": result, "state": srv.state_snapshot()})


async def _amend_pause(request: web.Request) -> web.Response:
    srv: GovernorTabletServer = request.app["srv"]
    result = srv.apply_pause()
    return web.json_response({"ok": True, "result": result, "state": srv.state_snapshot()})


def build_app(srv: GovernorTabletServer | None = None) -> web.Application:
    app = web.Application()
    app["srv"] = srv or GovernorTabletServer()
    app.router.add_get("/", _index)
    app.router.add_get("/state", _state)
    app.router.add_post("/amend/relax", _amend_relax)
    app.router.add_post("/amend/restrict", _amend_restrict)
    app.router.add_post("/amend/pause", _amend_pause)
    return app


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------


def detect_lan_ip() -> str:
    """Best-effort LAN IP for the URL the iPad will connect to."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No traffic actually sent — connect() on UDP just picks the route.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _print_banner(host: str, port: int) -> None:
    url = f"http://{host}:{port}/"
    print()
    print("  EMEX 2026 GOVERNOR TABLET")
    print("  =========================")
    print(f"  Open this URL in Safari on the iPad:")
    print()
    print(f"      {url}")
    print()
    # Best-effort QR via optional `qrcode` library; fall back silently.
    try:
        import qrcode  # type: ignore
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception:
        print("  (install `qrcode` for an inline QR; otherwise type the URL)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EMEX 2026 tablet governor — live Constitution edits over multicast."
    )
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0",
                        help="bind address (default: all interfaces)")
    parser.add_argument("--identity", default="node",
                        help="identity name in ~/.citizenry/<name>.key (default: node)")
    parser.add_argument(
        "--constitution",
        default=str(EMEX_CONSTITUTION_PATH),
        help="path to the EMEX Constitution JSON",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

    srv = GovernorTabletServer(
        constitution_path=Path(args.constitution),
        identity_name=args.identity,
    )
    log.info("loaded baseline Constitution v%d (deployment=%s) signed by %s",
             srv.current_dict["version"],
             srv.current_dict.get("deployment", "?"),
             srv.pubkey_hex[:8])

    _print_banner(detect_lan_ip(), args.port)

    app = build_app(srv)
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
