"""Tests for the action ledger (T29).

These verify that ``citizenry.mcp.ledger.ActionLedger`` produces a hash-chained,
Ed25519-signed sequence of decision entries — the citizenry counterpart to
TDM's T14 diagnostic ledger.

Six tests, mirroring the Step-1 spec:

  * ``chain_integrity``           — three writes in one session form a chain.
  * ``first_entry_empty_prev``    — the first entry has prev_hash == ''.
  * ``session_isolation``         — chains are per-session.
  * ``signature_verifies``        — every signature verifies under the
                                    governor's pubkey via ``VerifyKey``.
  * ``tampering_breaks_chain``    — mutating ``payload_json`` in the SQLite DB
                                    causes ``verify_chain`` to return False.
  * ``deterministic_ts_iso``      — equal ts arguments produce identical
                                    ts_iso strings (so equal hash inputs,
                                    modulo prev_hash).

We never mock nacl — every signature must verify under a real Ed25519
``VerifyKey``. We do, however, point HOME at a tmp_path so we don't trample
``~/.citizenry/node.key``.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import nacl.signing
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_identity(tmp_path, monkeypatch):
    """Throwaway HOME so identity / ledger paths are hermetic."""
    monkeypatch.setenv("HOME", str(tmp_path))
    from citizenry import identity
    importlib.reload(identity)
    from citizenry.mcp import ledger as ledger_mod
    importlib.reload(ledger_mod)
    return tmp_path


@pytest.fixture
def fresh_ledger(tmp_identity, tmp_path):
    """A fresh ActionLedger using a per-test SQLite file."""
    from citizenry.mcp.ledger import ActionLedger
    db_path = tmp_path / "action_ledger.sqlite"
    return ActionLedger(db_path=db_path)


# ---------------------------------------------------------------------------
# 1. chain_integrity
# ---------------------------------------------------------------------------


def test_chain_integrity(fresh_ledger):
    """Three entries in one session form a hash-chain."""
    e1 = fresh_ledger.write(kind="propose", session_id="s1", payload={"task": "a"})
    e2 = fresh_ledger.write(kind="accept", session_id="s1", payload={"task": "a"})
    e3 = fresh_ledger.write(kind="execute", session_id="s1", payload={"task": "a"})

    assert e1.prev_hash == ""
    assert e2.prev_hash == e1.hash
    assert e3.prev_hash == e2.hash

    # Hashes must all be distinct (different ts_iso even at minimum).
    assert len({e1.hash, e2.hash, e3.hash}) == 3

    assert fresh_ledger.verify_chain("s1") is True


# ---------------------------------------------------------------------------
# 2. first_entry_empty_prev_hash
# ---------------------------------------------------------------------------


def test_first_entry_empty_prev_hash(fresh_ledger):
    e = fresh_ledger.write(kind="tdm_read", session_id="brand-new", payload={"k": 1})
    assert e.prev_hash == ""
    assert e.id >= 1


# ---------------------------------------------------------------------------
# 3. session_isolation
# ---------------------------------------------------------------------------


def test_session_isolation(fresh_ledger):
    """Chains are per-session: a new session_id always starts with prev_hash == ''."""
    a1 = fresh_ledger.write(kind="propose", session_id="A", payload={"x": 1})
    a2 = fresh_ledger.write(kind="accept",  session_id="A", payload={"x": 1})
    b1 = fresh_ledger.write(kind="propose", session_id="B", payload={"y": 2})

    assert a1.prev_hash == ""
    assert a2.prev_hash == a1.hash
    assert b1.prev_hash == ""

    # Reading back per-session keeps them separate.
    sa = fresh_ledger.read_session("A")
    sb = fresh_ledger.read_session("B")
    assert [e.kind for e in sa] == ["propose", "accept"]
    assert [e.kind for e in sb] == ["propose"]

    assert fresh_ledger.verify_chain("A") is True
    assert fresh_ledger.verify_chain("B") is True


# ---------------------------------------------------------------------------
# 4. signature_verifies
# ---------------------------------------------------------------------------


def test_signature_verifies(fresh_ledger):
    """Every signature verifies under the governor's pubkey via VerifyKey."""
    entries = [
        fresh_ledger.write(kind="propose", session_id="sig", payload={"i": i})
        for i in range(4)
    ]
    pubkey_hex = entries[0].governor_pubkey
    verify_key = nacl.signing.VerifyKey(bytes.fromhex(pubkey_hex))

    for e in entries:
        # Signature is over the chain-hash (encoded as utf-8 of the hex string).
        verify_key.verify(e.hash.encode(), bytes.fromhex(e.signature))

    # And the bulk verifier agrees.
    assert fresh_ledger.verify_chain("sig") is True


# ---------------------------------------------------------------------------
# 5. tampering_breaks_chain
# ---------------------------------------------------------------------------


def test_tampering_breaks_chain(fresh_ledger, tmp_path):
    """Mutating payload_json directly in the DB is detected."""
    fresh_ledger.write(kind="propose", session_id="t", payload={"task": "good"})
    fresh_ledger.write(kind="accept",  session_id="t", payload={"task": "good"})
    fresh_ledger.write(kind="execute", session_id="t", payload={"task": "good"})

    assert fresh_ledger.verify_chain("t") is True

    # Forge: rewrite the middle entry's payload_json to claim a different task.
    db_path = fresh_ledger.db_path
    forged = json.dumps({"task": "EVIL"}, sort_keys=True, separators=(",", ":"))
    with sqlite3.connect(str(db_path)) as conn:
        # Pick the second entry of session 't'.
        rows = conn.execute(
            "SELECT id FROM action_ledger WHERE session_id=? ORDER BY id ASC", ("t",)
        ).fetchall()
        target_id = rows[1][0]
        conn.execute(
            "UPDATE action_ledger SET payload_json=? WHERE id=?",
            (forged, target_id),
        )
        conn.commit()

    assert fresh_ledger.verify_chain("t") is False


# ---------------------------------------------------------------------------
# 6. deterministic_ts_iso
# ---------------------------------------------------------------------------


def test_deterministic_ts_iso(fresh_ledger):
    """Equal ts arguments produce identical ts_iso (so identical hash inputs, modulo prev)."""
    from citizenry.mcp.ledger import _ts_iso

    ts = 1_700_000_000.123456
    assert _ts_iso(ts) == _ts_iso(ts)
    # Sanity-check it's the standard timezone-aware UTC isoformat.
    assert _ts_iso(ts) == datetime.fromtimestamp(ts, tz=UTC).isoformat()

    # And, end-to-end: two writes with the same ts but different sessions
    # produce the same ts_iso component (different hashes only because
    # session-A's payload and session-B's prev_hash differ).
    eA = fresh_ledger.write(kind="propose", session_id="A", payload={"k": 1}, ts=ts)
    eB = fresh_ledger.write(kind="propose", session_id="B", payload={"k": 1}, ts=ts)

    # Both are first entries in their respective sessions, with identical
    # payload_hash and identical ts_iso → identical chain-hashes.
    assert eA.prev_hash == "" and eB.prev_hash == ""
    assert eA.payload_hash == eB.payload_hash
    assert eA.hash == eB.hash
    # Signatures over the same hash by the same key are also identical (Ed25519
    # is deterministic), so this is a stronger statement than just hash equality.
    assert eA.signature == eB.signature
