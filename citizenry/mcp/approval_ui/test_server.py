"""Tests for the T28 mock approval-gate server.

We use ``aiohttp.test_utils.TestClient`` directly (no pytest-aiohttp dep) and
``pytest-asyncio`` for the async test runner. ``HOME`` is monkeypatched so the
real ``~/.citizenry/node.key`` and action ledger DB are never touched.

Three required tests:

  1. ``/pending`` returns the first proposal.
  2. ``/approve`` writes an ``approve`` ledger entry and advances the queue.
  3. ``/reject`` requires a non-empty reason; otherwise 400.

Plus a couple of bonus checks (index page renders, /next-sample advances
without writing). We never mock nacl — every signature must verify under a
real Ed25519 ``VerifyKey`` because that's the contract T29 commits to.
"""

from __future__ import annotations

import importlib

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer


@pytest.fixture
def tmp_identity(tmp_path, monkeypatch):
    """Throwaway HOME so identity / ledger paths never touch the real ones."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv(
        "CITIZENRY_ACTION_LEDGER_PATH",
        str(tmp_path / "action_ledger.sqlite"),
    )
    from citizenry import identity
    importlib.reload(identity)
    from citizenry.mcp import ledger as ledger_mod
    importlib.reload(ledger_mod)
    return tmp_path


@pytest.fixture
def fresh_server_module(tmp_identity):
    """Reload the server module so it picks up the freshly-reloaded ledger module."""
    from citizenry.mcp.approval_ui import server as server_mod
    importlib.reload(server_mod)
    return server_mod


@pytest_asyncio.fixture
async def cli(fresh_server_module):
    """aiohttp TestClient driving the real route handlers + an in-memory mock server."""
    srv = fresh_server_module.MockApprovalServer()
    app = fresh_server_module.build_app(srv)
    test_server = TestServer(app)
    client = TestClient(test_server)
    await client.start_server()
    client._mock_server = srv  # type: ignore[attr-defined]
    try:
        yield client
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# 1. /pending returns the first proposal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_returns_first_proposal(cli):
    r = await cli.get("/pending")
    assert r.status == 200
    body = await r.json()
    assert body["queue_position"] == 0
    p = body["proposal"]
    assert p is not None
    # Match the pre-canned head-of-queue (Stage backup tool: WC-12345 to Mazak pot 3).
    assert p["action_verb"] == "Stage backup tool"
    assert "WC-12345" in p["nouns"]
    # Evidence chain has exactly 4 entries with kind/short_hash/summary keys.
    assert len(p["evidence_chain"]) == 4
    for step in p["evidence_chain"]:
        assert {"kind", "short_hash", "summary"} <= step.keys()
        assert len(step["short_hash"]) == 8
    # Confidence chip in range.
    assert 0.0 <= p["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# 2. /approve writes a real ledger entry and advances the queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_writes_ledger_entry_and_advances(cli):
    srv = cli._mock_server  # type: ignore[attr-defined]
    head = srv.current()
    assert head is not None
    head_id = head["id"]
    head_verb = head["action_verb"]

    r = await cli.post("/approve", json={"id": head_id})
    assert r.status == 200
    body = await r.json()
    assert body["ok"] is True
    assert body["decision"] == "approve"
    assert body["approved_id"] == head_id
    assert body["ledger_hash"], "approve must return a non-empty ledger hash"

    # Queue advanced.
    nxt = body["next_proposal"]
    assert nxt is not None
    assert nxt["id"] != head_id

    # Ledger has a real signed entry for the rehearsal session.
    entries = srv.ledger.read_session(srv.session_id)
    assert len(entries) == 1
    e = entries[0]
    assert e.kind == "approve"
    assert e.session_id == "emex-rehearsal"
    assert e.payload["action_id"] == head_id
    assert e.payload["verb"] == head_verb
    assert e.payload["decision"] == "approve"
    # The signature chain verifies under the governor pubkey.
    assert srv.ledger.verify_chain(srv.session_id) is True


# ---------------------------------------------------------------------------
# 3. /reject requires a reason
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_requires_reason(cli):
    srv = cli._mock_server  # type: ignore[attr-defined]
    head_id = srv.current()["id"]

    # No reason → 400.
    r = await cli.post("/reject", json={"id": head_id})
    assert r.status == 400
    body = await r.json()
    assert body["ok"] is False
    assert "reason" in body["error"].lower()

    # Empty/whitespace-only reason → 400.
    r = await cli.post("/reject", json={"id": head_id, "reason": "   "})
    assert r.status == 400

    # Queue did not advance: we're still on the same head.
    r = await cli.get("/pending")
    body = await r.json()
    assert body["proposal"]["id"] == head_id

    # With a reason → 200, ledger entry recorded.
    r = await cli.post("/reject", json={"id": head_id, "reason": "coolant pump pressure low"})
    assert r.status == 200
    body = await r.json()
    assert body["ok"] is True
    assert body["decision"] == "reject"
    assert body["reason"] == "coolant pump pressure low"

    entries = srv.ledger.read_session(srv.session_id)
    assert len(entries) == 1
    assert entries[0].kind == "reject"
    assert entries[0].payload["reason"] == "coolant pump pressure low"


# ---------------------------------------------------------------------------
# Bonus: index page loads (the iPad will hit /, which serves index.html)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_serves_html(cli):
    r = await cli.get("/")
    assert r.status == 200
    text = await r.text()
    assert "Quintinity ShopOS" in text
    assert "APPROVE" in text


# ---------------------------------------------------------------------------
# Bonus: /next-sample advances without recording a decision
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_next_sample_advances_without_ledger_write(cli):
    srv = cli._mock_server  # type: ignore[attr-defined]
    head_id_before = srv.current()["id"]

    r = await cli.get("/next-sample")
    assert r.status == 200
    body = await r.json()
    assert body["proposal"]["id"] != head_id_before

    # No ledger entries written by /next-sample.
    assert srv.ledger.read_session(srv.session_id) == []
