"""Signed hash-chain action ledger for the citizenry side (T29).

Sibling to TDM's T14 diagnostic ledger. T14 is hash-only; T29 is hash +
Ed25519-signed by the GovernorCitizen's node key, using the canonical-JSON
pattern from ``governor_emex_tablet._sign_dict`` and
``citizen_mcp_server.MeshAdapter._sign_dict``.

Pure local persistence: SQLite stdlib, no network, no async. Per-session
hash chains; the signature covers the chain-hash so tampering with any
prior entry in the chain breaks every later signature even if the attacker
re-signs the tampered entry (Bitcoin / signed-Git-commit construction).

T27 (orchestrator wiring) is deferred — when it lands it will hold an
``ActionLedger`` and call ``write(...)`` on every TDM read, every PROPOSE,
and every approval-gate decision.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import nacl.signing

from citizenry.identity import IDENTITY_DIR, load_or_create_identity


DEFAULT_DB_PATH: Path = IDENTITY_DIR / "action_ledger.sqlite"
DEFAULT_IDENTITY_NAME: str = "node"
ENV_DB_PATH: str = "CITIZENRY_ACTION_LEDGER_PATH"

_DDL = """
CREATE TABLE IF NOT EXISTS action_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    kind            TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    governor_pubkey TEXT NOT NULL,
    payload_json    TEXT NOT NULL,
    payload_hash    TEXT NOT NULL,
    prev_hash       TEXT NOT NULL DEFAULT '',
    hash            TEXT NOT NULL,
    signature       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_action_ledger_session ON action_ledger(session_id, ts);
CREATE INDEX IF NOT EXISTS idx_action_ledger_chain   ON action_ledger(prev_hash);
"""


def _canonical_json(payload: dict) -> str:
    """Sorted-keys, tight-separators canonical JSON — same shape T21/T26 use."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ts_iso(ts: float) -> str:
    """Deterministic timezone-aware UTC isoformat (module-level for test import)."""
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def _resolve_db_path(db_path: str | Path | None) -> Path:
    """Caller arg > env var > default."""
    if db_path is not None:
        return Path(db_path).expanduser()
    env = os.environ.get(ENV_DB_PATH)
    if env:
        return Path(env).expanduser()
    return DEFAULT_DB_PATH


@dataclass(frozen=True)
class LedgerEntry:
    """One row of ``action_ledger`` with the payload re-parsed for callers."""
    id: int
    ts: float
    kind: str
    session_id: str
    governor_pubkey: str
    payload: dict[str, Any]
    payload_hash: str
    prev_hash: str
    hash: str
    signature: str


class ActionLedger:
    """Append-only signed hash-chain over local SQLite.

    Each ``session_id`` is an independent chain. The first entry has
    ``prev_hash == ''``; subsequent entries' ``prev_hash`` is the prior
    entry's ``hash``. ``signature`` is Ed25519 over the chain ``hash``
    (utf-8 of the hex string).
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        signing_key: nacl.signing.SigningKey | None = None,
        identity_name: str = DEFAULT_IDENTITY_NAME,
    ) -> None:
        self.db_path: Path = _resolve_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.signing_key: nacl.signing.SigningKey = (
            signing_key
            if signing_key is not None
            else load_or_create_identity(identity_name)
        )
        self.governor_pubkey: str = self.signing_key.verify_key.encode().hex()

        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        # Default isolation: each `write` is its own transaction.
        return sqlite3.connect(str(self.db_path))

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)

    def _latest_hash(self, conn: sqlite3.Connection, session_id: str) -> str:
        row = conn.execute(
            "SELECT hash FROM action_ledger WHERE session_id=? "
            "ORDER BY id DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        return row[0] if row else ""

    def write(
        self,
        *,
        kind: str,
        session_id: str,
        payload: dict[str, Any],
        ts: float | None = None,
    ) -> LedgerEntry:
        """Append a signed entry to ``session_id``'s chain. Returns the entry."""
        if ts is None:
            ts = time.time()

        payload_json = _canonical_json(payload)
        payload_hash = _sha256_hex(payload_json.encode())
        ts_iso = _ts_iso(ts)

        with self._connect() as conn:
            prev_hash = self._latest_hash(conn, session_id)
            entry_hash = _sha256_hex((prev_hash + payload_hash + ts_iso).encode())
            signature = self.signing_key.sign(entry_hash.encode()).signature.hex()

            cur = conn.execute(
                "INSERT INTO action_ledger "
                "(ts, kind, session_id, governor_pubkey, payload_json, "
                " payload_hash, prev_hash, hash, signature) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ts, kind, session_id, self.governor_pubkey, payload_json,
                 payload_hash, prev_hash, entry_hash, signature),
            )
            row_id = cur.lastrowid
            conn.commit()

        return LedgerEntry(
            id=int(row_id), ts=ts, kind=kind, session_id=session_id,
            governor_pubkey=self.governor_pubkey,
            payload=json.loads(payload_json),
            payload_hash=payload_hash, prev_hash=prev_hash,
            hash=entry_hash, signature=signature,
        )

    def read_session(self, session_id: str) -> list[LedgerEntry]:
        """Return all entries for ``session_id``, ordered by id ascending."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, kind, session_id, governor_pubkey, payload_json, "
                "payload_hash, prev_hash, hash, signature "
                "FROM action_ledger WHERE session_id=? ORDER BY id ASC",
                (session_id,),
            ).fetchall()

        return [
            LedgerEntry(
                id=r[0], ts=r[1], kind=r[2], session_id=r[3],
                governor_pubkey=r[4], payload=json.loads(r[5]),
                payload_hash=r[6], prev_hash=r[7], hash=r[8], signature=r[9],
            )
            for r in rows
        ]

    def verify_chain(self, session_id: str) -> bool:
        """Recompute every hash + verify every signature for ``session_id``.

        True iff every ``prev_hash`` links to the prior entry's ``hash``,
        every ``payload_hash`` matches sha256(payload_json), every ``hash``
        matches sha256(prev_hash || payload_hash || ts_iso), and every
        ``signature`` verifies under ``governor_pubkey``.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts, governor_pubkey, payload_json, payload_hash, "
                "prev_hash, hash, signature "
                "FROM action_ledger WHERE session_id=? ORDER BY id ASC",
                (session_id,),
            ).fetchall()

        expected_prev = ""
        for ts, gov_pub, payload_json, payload_hash, prev_hash, entry_hash, sig in rows:
            if prev_hash != expected_prev:
                return False
            if _sha256_hex(payload_json.encode()) != payload_hash:
                return False
            recomputed = _sha256_hex(
                (prev_hash + payload_hash + _ts_iso(ts)).encode()
            )
            if recomputed != entry_hash:
                return False
            try:
                vk = nacl.signing.VerifyKey(bytes.fromhex(gov_pub))
                vk.verify(entry_hash.encode(), bytes.fromhex(sig))
            except Exception:
                return False
            expected_prev = entry_hash

        return True


if __name__ == "__main__":  # pragma: no cover - smoke only
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        led = ActionLedger(db_path=Path(td) / "smoke.sqlite")
        led.write(kind="propose", session_id="s", payload={"hi": 1})
        led.write(kind="accept",  session_id="s", payload={"hi": 1})
        print(f"smoke verify_chain={led.verify_chain('s')}")
