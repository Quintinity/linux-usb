"""Mock backend for the 4-tier approval-gate tablet UI (T28).

The real orchestrator (T27) is BLOCKED on Anthropic Managed Agents enrolment.
Until it lands this server fakes the ``/pending``, ``/approve``, ``/reject``
shape so the iPad UI can be rehearsed end-to-end. Each approve/reject still
writes a real entry into T29's :class:`ActionLedger` so the chain accumulates
live during the demo.

Endpoints
---------

``GET  /``             — serves :file:`index.html`.
``GET  /pending``      — current head-of-queue proposal (or ``null`` if drained).
``POST /approve``      — record approval, append ledger entry, advance queue.
``POST /reject``       — same, but requires a one-line reason in the body.
``GET  /next-sample``  — manually advance (rehearsal: tap through scenarios).

T27 swap-in
-----------

When T27 lands, replace :class:`MockApprovalServer`'s in-memory queue and the
ledger-write side-effects with a real orchestrator handle. The HTTP contract
above is what the UI will keep talking. See ``test_server.py`` and the README
section in T28's commit message for the exact response shapes.

Usage::

    ~/lerobot-env/bin/python -m citizenry.mcp.approval_ui.server
    # then open Safari on the iPad to the printed LAN URL.
"""

from __future__ import annotations

import argparse
import logging
import socket
import time
import uuid
from pathlib import Path
from typing import Any

from aiohttp import web

from citizenry.mcp.ledger import ActionLedger


log = logging.getLogger("approval_ui")

HERE = Path(__file__).resolve().parent
HTML_PATH = HERE / "index.html"

REHEARSAL_SESSION_ID = "emex-rehearsal"


# ---------------------------------------------------------------------------
# Pre-canned proposals (rehearsal scenarios)
# ---------------------------------------------------------------------------


SAMPLE_PROPOSALS: list[dict[str, Any]] = [
    {
        "action_verb": "Stage backup tool",
        "nouns": ["WC-12345", "Mazak pot 3"],
        "proposed_by": "quin-agent (TDM session 14:22:08)",
        "confidence": 0.92,
        "evidence_chain": [
            {
                "kind": "tdm_read",
                "short_hash": "a14b9c02",
                "summary": "Mazak pot 3 spindle hours @ 412.7 — 18% over the change-out threshold.",
            },
            {
                "kind": "tdm_read",
                "short_hash": "f6cc1d34",
                "summary": "Scrap rate on op-3 climbing: 4 of last 50 parts out-of-tol on the 0.250 bore.",
            },
            {
                "kind": "propose",
                "short_hash": "9e7b3a41",
                "summary": "quin-agent proposes pre-emptive swap to backup end-mill WC-12345 before next batch.",
            },
            {
                "kind": "accept",
                "short_hash": "3fd80ab2",
                "summary": "Cell-3 supervisor agent accepts the proposal; awaits operator gate.",
            },
        ],
        "impact_statement": (
            "This will move the backup end-mill into Mazak's pot 3. Mazak's "
            "current pot 3 tool will be staged for change-out. Estimated "
            "downtime: 90 seconds."
        ),
    },
    {
        "action_verb": "Pause Mazak spindle",
        "nouns": ["Mazak-A", "op-3 batch"],
        "proposed_by": "quin-agent (mesh decision 14:24:51)",
        "confidence": 0.81,
        "evidence_chain": [
            {
                "kind": "tdm_read",
                "short_hash": "21d8e44a",
                "summary": "Vibration on Z-axis trended +27% over the last 6 parts.",
            },
            {
                "kind": "tdm_read",
                "short_hash": "ca6f29b7",
                "summary": "Coolant pressure dropped to 38 PSI (target 60); flush sensor reports clog likely.",
            },
            {
                "kind": "propose",
                "short_hash": "47b9a210",
                "summary": "Pause spindle for 90s, run coolant flush macro, then resume.",
            },
            {
                "kind": "accept",
                "short_hash": "bd02e7ff",
                "summary": "Cell-3 supervisor accepts; coolant macro pre-staged for the post-approval execute.",
            },
        ],
        "impact_statement": (
            "Mazak-A will pause for ~90 seconds after the current part finishes. "
            "Coolant flush macro will run automatically before the spindle resumes."
        ),
    },
    {
        "action_verb": "Increase coolant flow",
        "nouns": ["Mazak-A", "+15 PSI"],
        "proposed_by": "quin-agent (TDM session 14:31:12)",
        "confidence": 0.74,
        "evidence_chain": [
            {
                "kind": "tdm_read",
                "short_hash": "8c1a0fde",
                "summary": "Tool-tip temp on the active end-mill peaking at 612 C, vs 540 C nominal.",
            },
            {
                "kind": "tdm_read",
                "short_hash": "fb3d5601",
                "summary": "Chip evac camera shows long stringy chips (under-cooled cut signature).",
            },
            {
                "kind": "propose",
                "short_hash": "120ce98a",
                "summary": "Bump coolant set-point from 60 to 75 PSI for the rest of this batch.",
            },
            {
                "kind": "accept",
                "short_hash": "5ae72f9d",
                "summary": "Cell-3 supervisor accepts within visitor-safe envelope.",
            },
        ],
        "impact_statement": (
            "Coolant set-point will move from 60 PSI to 75 PSI for the remaining "
            "12 parts in this batch. No spindle pause required."
        ),
    },
    {
        "action_verb": "Re-zero work-coords",
        "nouns": ["Mazak-A", "op-3 fixture"],
        "proposed_by": "quin-agent (TDM session 14:38:44)",
        "confidence": 0.88,
        "evidence_chain": [
            {
                "kind": "tdm_read",
                "short_hash": "0042bb1c",
                "summary": "Probe touch-off on op-3 fixture drifted 0.0008\" since shift start.",
            },
            {
                "kind": "tdm_read",
                "short_hash": "77ee9134",
                "summary": "Last 3 first-articles required manual offset corrections of similar magnitude.",
            },
            {
                "kind": "propose",
                "short_hash": "cc4d20a6",
                "summary": "Run probing macro G54_PROBE; update active offset before next part.",
            },
            {
                "kind": "accept",
                "short_hash": "9b41a073",
                "summary": "Cell-3 supervisor accepts; probing macro is already qualified for live use.",
            },
        ],
        "impact_statement": (
            "Mazak-A will run its probing cycle (~30 seconds) and update G54 "
            "before the next part. No part scrap, no operator hand-off needed."
        ),
    },
    {
        "action_verb": "Halt SCRAP-prone job",
        "nouns": ["job 7821", "Mazak-A queue"],
        "proposed_by": "quin-agent (mesh decision 14:42:09)",
        "confidence": 0.96,
        "evidence_chain": [
            {
                "kind": "tdm_read",
                "short_hash": "ee31b4c8",
                "summary": "Op-2 vendor recall: stock heat-lot 4471-J flagged for inclusions.",
            },
            {
                "kind": "tdm_read",
                "short_hash": "1aa9c7db",
                "summary": "Job 7821 is the only queued job consuming heat-lot 4471-J in this cell.",
            },
            {
                "kind": "propose",
                "short_hash": "b6f81250",
                "summary": "Pull job 7821 from the queue; route to QA hold pending heat-lot disposition.",
            },
            {
                "kind": "accept",
                "short_hash": "dd09173c",
                "summary": "Cell-3 supervisor + planner agent both accept; awaiting operator gate.",
            },
        ],
        "impact_statement": (
            "Job 7821 will move from RUN-NEXT to QA-HOLD. Mazak-A will skip "
            "ahead to job 7822 (compatible heat-lot). Recoverable; no scrap risk."
        ),
    },
]


def _seed_proposals() -> list[dict[str, Any]]:
    """Stamp each sample proposal with a fresh uuid id."""
    out: list[dict[str, Any]] = []
    for s in SAMPLE_PROPOSALS:
        p = dict(s)
        p["id"] = str(uuid.uuid4())
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# Server state
# ---------------------------------------------------------------------------


class MockApprovalServer:
    """In-memory queue of pre-canned proposals + a real ActionLedger handle.

    Single-operator assumption: there's exactly one iPad in front of the cell.
    No locking or concurrency control. Decisions advance a queue cursor and
    write a signed entry into the action ledger so Bradley can show visitors
    a chain that grows live as he taps.
    """

    def __init__(
        self,
        proposals: list[dict[str, Any]] | None = None,
        ledger: ActionLedger | None = None,
        session_id: str = REHEARSAL_SESSION_ID,
    ):
        self.proposals: list[dict[str, Any]] = (
            proposals if proposals is not None else _seed_proposals()
        )
        self.cursor: int = 0
        self.session_id = session_id

        # Defensive: if ~/.citizenry/node.key is missing the ledger raises
        # under the hood. We catch and continue with ledger=None so the UI
        # is still usable for stand rehearsal even on a freshly-imaged box.
        if ledger is not None:
            self.ledger: ActionLedger | None = ledger
        else:
            try:
                self.ledger = ActionLedger()
            except Exception as e:  # pragma: no cover - defensive only
                log.warning(
                    "ActionLedger init failed (%s); approve/reject will not "
                    "write to the chain but the UI still works.", e,
                )
                self.ledger = None

        self.last_decision_at: float | None = None
        self.last_decision_kind: str | None = None
        self.last_ledger_hash: str | None = None

    # -- queue helpers ---------------------------------------------------

    def current(self) -> dict[str, Any] | None:
        if 0 <= self.cursor < len(self.proposals):
            return self.proposals[self.cursor]
        return None

    def advance(self) -> dict[str, Any] | None:
        """Move to the next proposal; loop at the end so rehearsal never runs dry."""
        if not self.proposals:
            return None
        self.cursor = (self.cursor + 1) % len(self.proposals)
        return self.current()

    def find(self, proposal_id: str) -> dict[str, Any] | None:
        for p in self.proposals:
            if p.get("id") == proposal_id:
                return p
        return None

    # -- decisions -------------------------------------------------------

    def _ledger_write(self, kind: str, payload: dict[str, Any]) -> str | None:
        """Append a signed entry to the rehearsal session chain. Returns hash or None."""
        if self.ledger is None:
            return None
        try:
            entry = self.ledger.write(
                kind=kind,
                session_id=self.session_id,
                payload=payload,
            )
            return entry.hash
        except Exception as e:  # pragma: no cover - defensive
            log.warning("ledger write failed (%s); continuing without chain entry", e)
            return None

    def approve(self, proposal_id: str) -> dict[str, Any]:
        p = self.find(proposal_id) or self.current()
        if p is None:
            return {"ok": False, "error": "no proposal to approve"}
        ledger_hash = self._ledger_write(
            "approve",
            {
                "action_id": p["id"],
                "verb": p["action_verb"],
                "nouns": p.get("nouns", []),
                "proposed_by": p.get("proposed_by"),
                "confidence": p.get("confidence"),
                "decision": "approve",
            },
        )
        self.last_decision_at = time.time()
        self.last_decision_kind = "approve"
        self.last_ledger_hash = ledger_hash
        # Advance only if the approved proposal was the head-of-queue.
        if p is self.current():
            self.advance()
        return {
            "ok": True,
            "decision": "approve",
            "approved_id": p["id"],
            "ledger_hash": ledger_hash,
            "next_proposal": self.current(),
        }

    def reject(self, proposal_id: str, reason: str) -> dict[str, Any]:
        p = self.find(proposal_id) or self.current()
        if p is None:
            return {"ok": False, "error": "no proposal to reject"}
        ledger_hash = self._ledger_write(
            "reject",
            {
                "action_id": p["id"],
                "verb": p["action_verb"],
                "nouns": p.get("nouns", []),
                "proposed_by": p.get("proposed_by"),
                "decision": "reject",
                "reason": reason,
            },
        )
        self.last_decision_at = time.time()
        self.last_decision_kind = "reject"
        self.last_ledger_hash = ledger_hash
        if p is self.current():
            self.advance()
        return {
            "ok": True,
            "decision": "reject",
            "rejected_id": p["id"],
            "reason": reason,
            "ledger_hash": ledger_hash,
            "next_proposal": self.current(),
        }


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------


async def _index(request: web.Request) -> web.Response:
    return web.Response(text=HTML_PATH.read_text(), content_type="text/html")


async def _pending(request: web.Request) -> web.Response:
    srv: MockApprovalServer = request.app["srv"]
    return web.json_response({
        "proposal": srv.current(),
        "queue_position": srv.cursor,
        "queue_length": len(srv.proposals),
    })


async def _approve(request: web.Request) -> web.Response:
    srv: MockApprovalServer = request.app["srv"]
    try:
        body = await request.json()
    except Exception:
        body = {}
    proposal_id = (body or {}).get("id") or ""
    result = srv.approve(proposal_id)
    if not result.get("ok"):
        return web.json_response(result, status=409)
    return web.json_response(result)


async def _reject(request: web.Request) -> web.Response:
    srv: MockApprovalServer = request.app["srv"]
    try:
        body = await request.json()
    except Exception:
        body = {}
    proposal_id = (body or {}).get("id") or ""
    reason = ((body or {}).get("reason") or "").strip()
    if not reason:
        return web.json_response(
            {"ok": False, "error": "reject requires a non-empty 'reason'"},
            status=400,
        )
    result = srv.reject(proposal_id, reason)
    if not result.get("ok"):
        return web.json_response(result, status=409)
    return web.json_response(result)


async def _next_sample(request: web.Request) -> web.Response:
    srv: MockApprovalServer = request.app["srv"]
    nxt = srv.advance()
    return web.json_response({"ok": True, "proposal": nxt})


def build_app(srv: MockApprovalServer | None = None) -> web.Application:
    app = web.Application()
    app["srv"] = srv or MockApprovalServer()
    app.router.add_get("/", _index)
    app.router.add_get("/pending", _pending)
    app.router.add_post("/approve", _approve)
    app.router.add_post("/reject", _reject)
    app.router.add_get("/next-sample", _next_sample)
    return app


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------


def detect_lan_ip() -> str:
    """Best-effort LAN IP for the URL the iPad will connect to."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _print_banner(host: str, port: int) -> None:
    url = f"http://{host}:{port}/"
    print()
    print("  QUINTINITY SHOPOS — APPROVAL GATE  (T28 mock backend)")
    print("  ====================================================")
    print(f"  Open this URL in Safari on the iPad:")
    print()
    print(f"      {url}")
    print()
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
        description="T28 mock approval-gate tablet UI server."
    )
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--host", default="0.0.0.0",
                        help="bind address (default: all interfaces)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    srv = MockApprovalServer()
    log.info(
        "loaded %d rehearsal proposals; ledger=%s; session=%s",
        len(srv.proposals),
        "ON" if srv.ledger is not None else "OFF (no node.key)",
        srv.session_id,
    )

    _print_banner(detect_lan_ip(), args.port)

    app = build_app(srv)
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
