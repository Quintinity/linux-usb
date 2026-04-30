# Constitution v2 + Identity Model — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace today's collapsed identity model (Constitution signed implicitly by governor citizen key, mixed with node key in MCP) with three explicit identity axes — node, role-citizen, Authority — and bump Constitution to v2 with the additional fields the §7.4 architecture spec requires (`authority_pubkey`, `node_key_version`, `tool_manifest_pinning`, `policy_pinning`, `embassy_topics`, `compliance_artefacts`). Add three new GOVERN body types (`rotate_node_key`, `pin_policy`, `pin_tool_manifest`) and a one-shot migration script for existing on-disk Constitution files.

**Architecture:** Backward-compatible additive change to `citizenry.constitution.Constitution` — old fields (`version=1`, `governor_pubkey`) preserved and round-trip cleanly so existing nodes do not crash on a v2 Constitution they don't yet understand. New `citizenry.authority` module owns the Authority signing key (single-key in v2.0, multi-sig hook stubbed for v2.1). `governor_citizen` and `mcp/citizen_mcp_server.py` updated to sign Constitution amendments with the Authority key, not their per-citizen key. Three new GOVERN handlers added in `citizen.py:_handle_govern`. Migration is a single CLI command `python -m citizenry.scripts.migrate_constitution` that reads `~/.citizenry/*.constitution.json`, mints a fresh `~/.citizenry/authority.key` if absent, re-signs the Constitution with it, and writes back atomically.

**Tech Stack:** Python 3.12, `pynacl` (Ed25519, already a citizenry dep), `dataclasses`, `pytest`. No new third-party dependencies.

**References:**
- Architecture spec: `docs/superpowers/specs/2026-04-30-citizenry-physical-ai-architecture-design.md` §5.2 (smell #1), §7.4 (identity & trust model), §10 sub-1.
- Existing code under modification: `citizenry/constitution.py`, `citizenry/identity.py`, `citizenry/node_identity.py`, `citizenry/citizen.py:636-699` (existing `_handle_govern`), `citizenry/governance/__init__.py`, `citizenry/governor_citizen.py`, `citizenry/mcp/citizen_mcp_server.py`.

**Out of scope:** Multi-sig Authority (v2.1, separate plan). Constitution federation across sites (v3). Approval-UI integration with new GOVERN types (separate sub-project).

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `citizenry/constitution.py` | modify | Add v2 fields to `Constitution`; refactor `sign()` to take any signing key (Authority); preserve v1 round-trip |
| `citizenry/authority.py` | **create** | Authority signing key — load/create at `~/.citizenry/authority.key`, `pubkey_hex()`, single-key for v2.0 |
| `citizenry/scripts/__init__.py` | **create** | Package marker for CLI scripts |
| `citizenry/scripts/migrate_constitution.py` | **create** | Migration CLI: v1 Constitution + governor.key → v2 Constitution + authority.key |
| `citizenry/citizen.py` | modify | `_handle_govern`: add `rotate_node_key`, `pin_policy`, `pin_tool_manifest` body types |
| `citizenry/governance/__init__.py` | modify | `ConstitutionView` exposes new v2 fields |
| `citizenry/governor_citizen.py` | modify | Sign Constitution amendments with Authority key (loaded via `citizenry.authority`), not the governor citizen identity |
| `citizenry/mcp/citizen_mcp_server.py` | modify | `govern_update` MCP tool: sign with Authority key |
| `citizenry/tests/test_constitution_v2.py` | **create** | v2 schema, round-trip, sign/verify with Authority |
| `citizenry/tests/test_authority.py` | **create** | Authority key load/create/persistence |
| `citizenry/tests/test_constitution_migration.py` | **create** | v1 → v2 migration correctness |
| `citizenry/tests/test_govern_pin_policy.py` | **create** | `pin_policy` GOVERN body type |
| `citizenry/tests/test_govern_pin_tool_manifest.py` | **create** | `pin_tool_manifest` GOVERN body type |
| `citizenry/tests/test_govern_rotate_node_key.py` | **create** | `rotate_node_key` GOVERN body type |
| `citizenry/tests/test_governor_citizen_signs_with_authority.py` | **create** | smell #1 fix verified end-to-end |

15 files (5 created code, 4 modified, 6 new test files). No file under modification is large enough to warrant restructuring.

---

## Conventions

- **Test paths**: all under `citizenry/tests/`. Use `pytest`.
- **Run tests**: `cd ~/linux-usb && source ~/lerobot-env/bin/activate && pytest citizenry/tests/<test>.py -v` (Surface; on Pi/Jetson the venv is the same path).
- **Commits**: small, one task per commit, message format `citizenry(constitution-v2): <task summary>`. Always `git add` explicit paths — never `git add -A` (the working tree has unrelated in-progress changes in `citizenry/manipulator_citizen.py` etc.).
- **Backward compatibility check**: every Constitution change must round-trip a known v1 JSON dict without raising. Test fixture committed under `citizenry/tests/fixtures/constitution_v1_sample.json`.

---

## Task 1: Constitution v2 schema fields (additive)

**Files:**
- Modify: `citizenry/constitution.py:53-127` (`Constitution` dataclass + `to_dict`/`from_dict`)
- Test: `citizenry/tests/test_constitution_v2.py` (create)
- Fixture: `citizenry/tests/fixtures/constitution_v1_sample.json` (create)

- [ ] **Step 1: Create the v1 fixture for round-trip testing**

Create `citizenry/tests/fixtures/constitution_v1_sample.json`:

```json
{
  "version": 1,
  "governor_pubkey": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "articles": [
    {"number": 1, "title": "Do No Harm", "text": "No command may cause physical harm."}
  ],
  "laws": [
    {"id": "heartbeat_interval", "description": "seconds", "params": {"seconds": 2.0}}
  ],
  "servo_limits": {
    "max_torque": 500,
    "protection_current": 250,
    "max_temperature": 65,
    "overload_torque": 90,
    "protective_torque": 50,
    "min_voltage": 6.0
  },
  "signature": "deadbeef"
}
```

- [ ] **Step 2: Write the failing tests for v2 fields and v1 round-trip**

Create `citizenry/tests/test_constitution_v2.py`:

```python
"""Constitution v2 schema and v1 backward-compat round-trip."""
import json
from pathlib import Path

import pytest
from nacl.signing import SigningKey

from citizenry.constitution import Constitution, Article, Law, ServoLimits


FIXTURES = Path(__file__).parent / "fixtures"


def test_v2_default_fields():
    c = Constitution()
    assert c.version == 2
    assert c.authority_pubkey == ""
    assert c.node_key_version == 1
    assert c.tool_manifest_pinning == {}
    assert c.policy_pinning == {}
    assert c.embassy_topics == {}
    assert c.compliance_artefacts == {}


def test_v2_to_dict_includes_new_fields():
    c = Constitution()
    d = c.to_dict()
    for k in (
        "version",
        "authority_pubkey",
        "node_key_version",
        "tool_manifest_pinning",
        "policy_pinning",
        "embassy_topics",
        "compliance_artefacts",
        "governor_pubkey",
        "articles",
        "laws",
        "servo_limits",
        "signature",
    ):
        assert k in d, f"missing key {k!r} in v2 to_dict()"


def test_v1_dict_round_trips_into_v2():
    raw = (FIXTURES / "constitution_v1_sample.json").read_text()
    v1_dict = json.loads(raw)
    c = Constitution.from_dict(v1_dict)
    assert c.version == 1
    assert c.governor_pubkey == v1_dict["governor_pubkey"]
    # New v2 fields default cleanly
    assert c.authority_pubkey == ""
    assert c.node_key_version == 1
    assert c.tool_manifest_pinning == {}
    # Round-trip back to dict and back to object preserves data
    again = Constitution.from_dict(c.to_dict())
    assert again.version == 1
    assert again.governor_pubkey == v1_dict["governor_pubkey"]


def test_v2_from_dict_accepts_full_payload():
    payload = {
        "version": 2,
        "governor_pubkey": "",
        "authority_pubkey": "ab" * 32,
        "node_key_version": 3,
        "articles": [],
        "laws": [],
        "servo_limits": {},
        "tool_manifest_pinning": {"bus-mcp": "sha256:abc"},
        "policy_pinning": {"smolvla-pickplace-v3": "hf:rev:def"},
        "embassy_topics": {"opcua_namespace": "ns/quintinity/cell1"},
        "compliance_artefacts": {"aibom_url": "https://example/aibom.cdx.json"},
        "signature": "",
    }
    c = Constitution.from_dict(payload)
    assert c.version == 2
    assert c.authority_pubkey == "ab" * 32
    assert c.node_key_version == 3
    assert c.tool_manifest_pinning == {"bus-mcp": "sha256:abc"}
    assert c.policy_pinning == {"smolvla-pickplace-v3": "hf:rev:def"}
    assert c.embassy_topics == {"opcua_namespace": "ns/quintinity/cell1"}
    assert c.compliance_artefacts == {"aibom_url": "https://example/aibom.cdx.json"}
```

- [ ] **Step 3: Run the tests and confirm they fail**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_constitution_v2.py -v
```

Expected: `test_v2_default_fields` FAILS with `assert 1 == 2` or AttributeError on `authority_pubkey`. The other v2 tests fail similarly. `test_v1_dict_round_trips_into_v2` may pass partially.

- [ ] **Step 4: Implement v2 fields on `Constitution`**

In `citizenry/constitution.py`, modify the `Constitution` dataclass and its `to_dict`/`from_dict` methods. Replace the existing class definition (lines 53-138 in the current file) with:

```python
@dataclass
class Constitution:
    """The root governance document for an armOS citizenry."""

    # v1 fields (preserved for backward compatibility)
    version: int = 2
    governor_pubkey: str = ""        # legacy alias of authority_pubkey
    articles: list[Article] = field(default_factory=list)
    laws: list[Law] = field(default_factory=list)
    servo_limits: ServoLimits = field(default_factory=ServoLimits)
    signature: str = ""              # hex-encoded Ed25519 signature

    # v2 additions
    authority_pubkey: str = ""       # hex-encoded Ed25519 public key of the Authority
    node_key_version: int = 1
    tool_manifest_pinning: dict[str, str] = field(default_factory=dict)
    policy_pinning: dict[str, str] = field(default_factory=dict)
    embassy_topics: dict[str, str] = field(default_factory=dict)
    compliance_artefacts: dict[str, str] = field(default_factory=dict)

    # -- crypto -------------------------------------------------------------

    def _signable_payload(self) -> bytes:
        """Return the canonical bytes that get signed/verified."""
        d = self.to_dict()
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def sign(self, signing_key: SigningKey) -> None:
        """Sign with the Authority's private key.

        For v2, the signing pubkey populates ``authority_pubkey`` and is
        mirrored into ``governor_pubkey`` for backward compatibility with
        v1 verifiers. For v1 Constitutions (version == 1) only
        ``governor_pubkey`` is populated.
        """
        pub_hex = signing_key.verify_key.encode(encoder=HexEncoder).decode()
        if self.version >= 2:
            self.authority_pubkey = pub_hex
            self.governor_pubkey = pub_hex  # mirror for v1 verifiers
        else:
            self.governor_pubkey = pub_hex
        signed = signing_key.sign(self._signable_payload(), encoder=HexEncoder)
        self.signature = signed.signature.decode()

    def verify(self, verify_key: VerifyKey | None = None) -> bool:
        """Verify the signature.

        For v2 Constitutions, prefers ``authority_pubkey``; falls back to
        ``governor_pubkey`` for v1 compatibility.
        """
        if verify_key is None:
            pub_hex = self.authority_pubkey or self.governor_pubkey
            if not pub_hex:
                return False
            verify_key = VerifyKey(pub_hex.encode(), encoder=HexEncoder)
        try:
            verify_key.verify(
                self._signable_payload(),
                bytes.fromhex(self.signature),
            )
            return True
        except Exception:
            return False

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "version": self.version,
            "governor_pubkey": self.governor_pubkey,
            "authority_pubkey": self.authority_pubkey,
            "node_key_version": self.node_key_version,
            "articles": [asdict(a) for a in self.articles],
            "laws": [asdict(l) for l in self.laws],
            "servo_limits": asdict(self.servo_limits),
            "tool_manifest_pinning": dict(self.tool_manifest_pinning),
            "policy_pinning": dict(self.policy_pinning),
            "embassy_topics": dict(self.embassy_topics),
            "compliance_artefacts": dict(self.compliance_artefacts),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Constitution:
        """Deserialize from a dictionary. Accepts both v1 and v2 payloads."""
        return cls(
            version=d.get("version", 1),
            governor_pubkey=d.get("governor_pubkey", ""),
            authority_pubkey=d.get("authority_pubkey", ""),
            node_key_version=d.get("node_key_version", 1),
            articles=[Article(**a) for a in d.get("articles", [])],
            laws=[Law(**l) for l in d.get("laws", [])],
            servo_limits=ServoLimits(**d.get("servo_limits", {})),
            tool_manifest_pinning=dict(d.get("tool_manifest_pinning", {})),
            policy_pinning=dict(d.get("policy_pinning", {})),
            embassy_topics=dict(d.get("embassy_topics", {})),
            compliance_artefacts=dict(d.get("compliance_artefacts", {})),
            signature=d.get("signature", ""),
        )

    def to_bytes(self) -> bytes:
        """Serialize to bytes for wire transport."""
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode()

    @classmethod
    def from_bytes(cls, raw: bytes) -> Constitution:
        return cls.from_dict(json.loads(raw))
```

Also update `default_constitution()` (still in `citizenry/constitution.py`) to set `version=2` on the returned object. Find this line:

```python
    return Constitution(
        version=1,
        articles=articles,
        laws=laws,
        servo_limits=ServoLimits(),
    )
```

Change to:

```python
    return Constitution(
        version=2,
        articles=articles,
        laws=laws,
        servo_limits=ServoLimits(),
    )
```

- [ ] **Step 5: Run tests, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_constitution_v2.py -v
```

Expected: 4 PASS.

- [ ] **Step 6: Run the existing constitution test suite to confirm no regression**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_citizen_law.py citizenry/governance/test_emex_constitution.py -v
```

Expected: all PASS (existing tests still green; v1 round-trip preserved).

- [ ] **Step 7: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/constitution.py \
             citizenry/tests/test_constitution_v2.py \
             citizenry/tests/fixtures/constitution_v1_sample.json \
  && git commit -m "$(cat <<'EOF'
citizenry(constitution-v2): add v2 schema fields with v1 backward-compat

- Constitution.version defaults to 2
- new fields: authority_pubkey, node_key_version, tool_manifest_pinning,
  policy_pinning, embassy_topics, compliance_artefacts
- sign() mirrors authority_pubkey into governor_pubkey for v1 verifiers
- verify() prefers authority_pubkey, falls back to governor_pubkey
- v1 dicts round-trip cleanly through from_dict/to_dict
- 4 new tests in test_constitution_v2.py

Spec: docs/superpowers/specs/2026-04-30-citizenry-physical-ai-architecture-design.md §7.4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Authority identity module

**Files:**
- Create: `citizenry/authority.py`
- Test: `citizenry/tests/test_authority.py`

- [ ] **Step 1: Write the failing test**

Create `citizenry/tests/test_authority.py`:

```python
"""Authority signing key — single-key for v2.0 (multi-sig is v2.1)."""
import os
import tempfile
from pathlib import Path

import pytest

from citizenry import authority


@pytest.fixture
def isolated_home(monkeypatch, tmp_path):
    """Redirect ~/.citizenry to a temp dir for the duration of the test."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    # Re-resolve module-level constants that captured Path.home()
    monkeypatch.setattr(authority, "AUTHORITY_DIR", fake_home / ".citizenry")
    monkeypatch.setattr(
        authority, "_KEY_PATH", fake_home / ".citizenry" / "authority.key"
    )
    return fake_home


def test_load_or_create_authority_key_is_idempotent(isolated_home):
    k1 = authority.load_or_create_authority_key()
    k2 = authority.load_or_create_authority_key()
    assert k1.encode() == k2.encode()


def test_authority_key_is_persisted_with_mode_0600(isolated_home):
    authority.load_or_create_authority_key()
    p = isolated_home / ".citizenry" / "authority.key"
    assert p.exists()
    assert (p.stat().st_mode & 0o777) == 0o600
    assert len(p.read_bytes()) == 32


def test_authority_pubkey_hex_is_64_chars(isolated_home):
    pub = authority.authority_pubkey_hex()
    assert isinstance(pub, str)
    assert len(pub) == 64
    int(pub, 16)  # must parse as hex


def test_corrupt_authority_key_raises(isolated_home):
    p = isolated_home / ".citizenry" / "authority.key"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"not32bytes")
    with pytest.raises(authority.AuthorityKeyCorruptError):
        authority.load_or_create_authority_key()
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_authority.py -v
```

Expected: ImportError — `citizenry.authority` does not exist yet.

- [ ] **Step 3: Implement `citizenry/authority.py`**

Create `citizenry/authority.py`:

```python
"""Authority signing key — the root identity that ratifies Constitution amendments.

In v2.0 this is a single Ed25519 key at ``~/.citizenry/authority.key``.
v2.1 will introduce multi-sig (2-of-3 with offline keys); the public surface
of this module is designed to remain stable across that transition.

Distinct from:
- ``citizenry.node_identity`` (per-machine identity for transport / co-location).
- ``citizenry.identity`` (per-citizen role identities).

Authority signs Constitution and Law amendments only. It must never sign
runtime mesh messages — those are signed by role identities.
"""
from __future__ import annotations

from pathlib import Path

import nacl.signing
import nacl.encoding


AUTHORITY_DIR = Path.home() / ".citizenry"
_KEY_PATH = AUTHORITY_DIR / "authority.key"


class AuthorityKeyCorruptError(RuntimeError):
    """Raised when ~/.citizenry/authority.key exists but is not a valid Ed25519 seed."""


def _ensure_dir() -> None:
    AUTHORITY_DIR.mkdir(parents=True, exist_ok=True)


def load_or_create_authority_key() -> nacl.signing.SigningKey:
    """Load or generate the Authority signing key.

    Idempotent. Persists at ``~/.citizenry/authority.key`` with mode 0600.
    """
    _ensure_dir()
    if _KEY_PATH.exists():
        raw = _KEY_PATH.read_bytes()
        if len(raw) != 32:
            raise AuthorityKeyCorruptError(
                f"{_KEY_PATH} has length {len(raw)}, expected 32. "
                "Restore from backup before issuing GOVERN."
            )
        return nacl.signing.SigningKey(raw)
    key = nacl.signing.SigningKey.generate()
    _KEY_PATH.write_bytes(key.encode())
    _KEY_PATH.chmod(0o600)
    return key


def authority_pubkey_hex() -> str:
    """Hex-encoded Ed25519 public key of the Authority."""
    sk = load_or_create_authority_key()
    return sk.verify_key.encode(encoder=nacl.encoding.RawEncoder).hex()
```

- [ ] **Step 4: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_authority.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/authority.py citizenry/tests/test_authority.py \
  && git commit -m "$(cat <<'EOF'
citizenry(constitution-v2): add Authority signing key module

- citizenry/authority.py: load_or_create_authority_key, authority_pubkey_hex
- single-key for v2.0; multi-sig hook reserved for v2.1
- distinct from node_identity (transport) and identity (role)
- 4 tests covering create/load idempotency, mode-0600, corrupt seed

Spec: §7.4 (three identity axes)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Constitution v1 → v2 migration script

**Files:**
- Create: `citizenry/scripts/__init__.py` (empty package marker)
- Create: `citizenry/scripts/migrate_constitution.py`
- Test: `citizenry/tests/test_constitution_migration.py`

- [ ] **Step 1: Create the empty package marker**

Create `citizenry/scripts/__init__.py` with one line:

```python
"""citizenry.scripts — one-shot CLI utilities (migrations, calibration helpers)."""
```

- [ ] **Step 2: Write the failing migration tests**

Create `citizenry/tests/test_constitution_migration.py`:

```python
"""v1 → v2 Constitution migration."""
import json
from pathlib import Path

import pytest
from nacl.signing import SigningKey

from citizenry.constitution import Constitution, default_constitution
from citizenry.scripts.migrate_constitution import migrate_v1_dict, migrate_file


def _v1_payload(governor_pubkey: str) -> dict:
    return {
        "version": 1,
        "governor_pubkey": governor_pubkey,
        "articles": [
            {"number": 1, "title": "Test", "text": "A test article."}
        ],
        "laws": [
            {"id": "x", "description": "y", "params": {"v": 1}}
        ],
        "servo_limits": {"max_torque": 500},
        "signature": "deadbeef",
    }


def test_migrate_v1_dict_sets_v2_fields():
    auth = SigningKey.generate()
    auth_pub = auth.verify_key.encode().hex()
    v1 = _v1_payload(governor_pubkey="cafebabe" * 8)
    v2 = migrate_v1_dict(v1, authority_signing_key=auth)
    assert v2["version"] == 2
    assert v2["authority_pubkey"] == auth_pub
    # legacy field mirrored (so old verifiers still pass)
    assert v2["governor_pubkey"] == auth_pub
    assert v2["node_key_version"] == 1
    assert v2["tool_manifest_pinning"] == {}
    assert v2["policy_pinning"] == {}


def test_migrated_constitution_verifies_with_authority():
    auth = SigningKey.generate()
    v1 = _v1_payload(governor_pubkey="cafebabe" * 8)
    v2 = migrate_v1_dict(v1, authority_signing_key=auth)
    c = Constitution.from_dict(v2)
    assert c.verify() is True


def test_migrate_file_atomic_with_backup(tmp_path):
    auth = SigningKey.generate()
    target = tmp_path / "governor.constitution.json"
    target.write_text(json.dumps(_v1_payload(governor_pubkey="d" * 64)))
    migrate_file(target, authority_signing_key=auth)
    backup = tmp_path / "governor.constitution.v1.bak.json"
    assert backup.exists(), "v1 backup must be created"
    assert json.loads(backup.read_text())["version"] == 1
    after = json.loads(target.read_text())
    assert after["version"] == 2
    c = Constitution.from_dict(after)
    assert c.verify() is True


def test_migrate_file_idempotent_on_v2(tmp_path):
    """Running migration twice does not break a v2 file."""
    auth = SigningKey.generate()
    target = tmp_path / "governor.constitution.json"
    target.write_text(json.dumps(_v1_payload(governor_pubkey="e" * 64)))
    migrate_file(target, authority_signing_key=auth)
    first = target.read_text()
    # Second call should detect v2 and noop (no re-sign).
    migrate_file(target, authority_signing_key=auth)
    second = target.read_text()
    assert first == second
```

- [ ] **Step 3: Run the tests, confirm they fail**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_constitution_migration.py -v
```

Expected: ImportError — `citizenry.scripts.migrate_constitution` does not exist.

- [ ] **Step 4: Implement the migration script**

Create `citizenry/scripts/migrate_constitution.py`:

```python
"""v1 → v2 Constitution migration.

Reads an on-disk v1 Constitution JSON, mints a fresh Authority key (or
loads the existing one), re-signs the Constitution with v2 fields, and
writes back atomically with a ``.v1.bak.json`` backup alongside.

Idempotent: running twice on a v2 file is a noop.

CLI:
    python -m citizenry.scripts.migrate_constitution [path1.json path2.json ...]

If no paths are given, migrates every file under ``~/.citizenry/``
matching ``*.constitution.json``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable

import nacl.signing

from citizenry.authority import load_or_create_authority_key
from citizenry.constitution import Constitution


def migrate_v1_dict(
    v1_dict: dict,
    authority_signing_key: nacl.signing.SigningKey,
) -> dict:
    """Convert a v1 Constitution dict to a v2 Constitution dict, signed."""
    if v1_dict.get("version", 1) >= 2:
        return v1_dict  # already v2
    c = Constitution.from_dict(v1_dict)
    c.version = 2
    # Reset signature; will be replaced by sign() below.
    c.signature = ""
    c.authority_pubkey = ""
    c.sign(authority_signing_key)  # populates authority_pubkey + governor_pubkey
    return c.to_dict()


def migrate_file(
    path: Path,
    authority_signing_key: nacl.signing.SigningKey | None = None,
) -> bool:
    """Migrate one Constitution JSON file. Returns True if the file was changed."""
    if authority_signing_key is None:
        authority_signing_key = load_or_create_authority_key()
    raw = path.read_text()
    data = json.loads(raw)
    if data.get("version", 1) >= 2:
        return False
    backup = path.with_suffix(".v1.bak.json")
    backup.write_text(raw)
    new_dict = migrate_v1_dict(data, authority_signing_key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(new_dict, sort_keys=True, separators=(",", ":")))
    os.replace(tmp, path)
    return True


def _discover_default_paths() -> list[Path]:
    home = Path.home() / ".citizenry"
    if not home.exists():
        return []
    return sorted(home.glob("*.constitution.json"))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m citizenry.scripts.migrate_constitution",
        description="Migrate v1 Constitution JSON files to v2.",
    )
    parser.add_argument("paths", nargs="*", type=Path,
                        help="Constitution JSON files (default: ~/.citizenry/*.constitution.json)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    paths = args.paths or _discover_default_paths()
    if not paths:
        print("No Constitution files found.", file=sys.stderr)
        return 1
    auth = load_or_create_authority_key()
    changed = 0
    for p in paths:
        if args.dry_run:
            data = json.loads(p.read_text())
            v = data.get("version", 1)
            print(f"{p}: version={v} {'(would migrate)' if v < 2 else '(noop)'}")
            continue
        if migrate_file(p, authority_signing_key=auth):
            print(f"migrated: {p}")
            changed += 1
        else:
            print(f"already v2: {p}")
    print(f"done. {changed} file(s) migrated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_constitution_migration.py -v
```

Expected: 4 PASS.

- [ ] **Step 6: Smoke-test the CLI in --dry-run mode**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && python -m citizenry.scripts.migrate_constitution --dry-run
```

Expected output: lists each `~/.citizenry/*.constitution.json` with version + intent. **Do not run without `--dry-run` yet**; that's Task 10.

- [ ] **Step 7: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/scripts/__init__.py \
             citizenry/scripts/migrate_constitution.py \
             citizenry/tests/test_constitution_migration.py \
  && git commit -m "$(cat <<'EOF'
citizenry(constitution-v2): v1→v2 migration script with .v1.bak.json backup

- citizenry/scripts/migrate_constitution.py: CLI + library
- migrate_v1_dict: pure function, returns v2 dict signed with Authority
- migrate_file: atomic rewrite, .v1.bak.json backup, idempotent on v2
- 4 tests covering field set, signature verify, backup creation, idempotency
- CLI: python -m citizenry.scripts.migrate_constitution [--dry-run]

Spec: §7.4 (Constitution v2 schema), §10 sub-1

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: GOVERN body type — `pin_policy`

**Files:**
- Modify: `citizenry/citizen.py:636-699` (extend `_handle_govern`)
- Test: `citizenry/tests/test_govern_pin_policy.py`

The existing `policy_commit` body type carries no provenance. v2 `pin_policy` adds `hf_revision_sha`, `aibom_url`, and `rekor_log_index`. We **add** the new type alongside `policy_commit` (don't remove); old citizens still understand `policy_commit`.

- [ ] **Step 1: Write the failing test**

Create `citizenry/tests/test_govern_pin_policy.py`:

```python
"""GOVERN body type: pin_policy — formal provenance-bearing policy pin."""
import time
from unittest.mock import MagicMock

import pytest

from citizenry.citizen import Citizen
from citizenry.protocol import Envelope, MessageType


def _make_envelope(body: dict) -> Envelope:
    return Envelope(
        version=1,
        type=int(MessageType.GOVERN),
        sender="ab" * 32,
        recipient="*",
        timestamp=time.time(),
        ttl=3600.0,
        body=body,
        signature="cd" * 64,
    )


def test_handle_govern_pin_policy_sets_attribute(monkeypatch, tmp_path):
    """Receiving GOVERN(pin_policy, ...) records the pin on the citizen."""
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-pin-policy", citizen_type="test")
    env = _make_envelope({
        "type": "pin_policy",
        "policy_id": "smolvla-pickplace-v3",
        "hf_revision_sha": "0123456789abcdef",
        "aibom_url": "https://example.org/aibom.cdx.json",
        "rekor_log_index": 42,
    })
    c._handle_govern(env, addr=("127.0.0.1", 0))
    assert hasattr(c, "policy_pinning")
    assert c.policy_pinning == {
        "smolvla-pickplace-v3": {
            "hf_revision_sha": "0123456789abcdef",
            "aibom_url": "https://example.org/aibom.cdx.json",
            "rekor_log_index": 42,
        }
    }


def test_pin_policy_replaces_existing_pin(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-pin-policy-replace", citizen_type="test")
    c._handle_govern(_make_envelope({
        "type": "pin_policy",
        "policy_id": "x",
        "hf_revision_sha": "old",
        "aibom_url": "u1",
        "rekor_log_index": 1,
    }), addr=("127.0.0.1", 0))
    c._handle_govern(_make_envelope({
        "type": "pin_policy",
        "policy_id": "x",
        "hf_revision_sha": "new",
        "aibom_url": "u2",
        "rekor_log_index": 2,
    }), addr=("127.0.0.1", 0))
    assert c.policy_pinning["x"]["hf_revision_sha"] == "new"
    assert c.policy_pinning["x"]["rekor_log_index"] == 2


def test_pin_policy_missing_fields_logged_not_raised(monkeypatch, tmp_path):
    """Malformed pin_policy is logged but does not raise."""
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-pin-policy-malformed", citizen_type="test")
    # Missing hf_revision_sha — must not crash
    c._handle_govern(_make_envelope({
        "type": "pin_policy",
        "policy_id": "x",
    }), addr=("127.0.0.1", 0))
    # nothing pinned
    assert c.policy_pinning.get("x", {}).get("hf_revision_sha", "") == ""
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_govern_pin_policy.py -v
```

Expected: AttributeError on `c.policy_pinning` — citizen doesn't yet track this.

- [ ] **Step 3: Add `policy_pinning` dict and the `pin_policy` handler**

In `citizenry/citizen.py`, find the `Citizen.__init__` method and add (near other dict-initialised attributes; one good locus is just before `self.constitution_received`):

```python
        self.policy_pinning: dict[str, dict] = {}
        self.tool_manifest_pinning: dict[str, str] = {}
```

In the `_handle_govern` method (around line 670, after the `policy_rollback` branch, before `genome`), add:

```python
        elif gov_type == "pin_policy":
            policy_id = body.get("policy_id", "")
            hf_rev = body.get("hf_revision_sha", "")
            aibom = body.get("aibom_url", "")
            rekor = body.get("rekor_log_index", -1)
            if policy_id and hf_rev:
                self.policy_pinning[policy_id] = {
                    "hf_revision_sha": hf_rev,
                    "aibom_url": aibom,
                    "rekor_log_index": rekor,
                }
                self._log(
                    f"POLICY PIN from [{short_id(env.sender)}]: "
                    f"{policy_id} → {hf_rev[:12]}"
                )
                self._add_log("GOVERN", short_id(env.sender), f"pin: {policy_id}")
            else:
                self._log(
                    f"pin_policy MALFORMED from [{short_id(env.sender)}]: "
                    f"missing policy_id or hf_revision_sha"
                )
```

- [ ] **Step 4: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_govern_pin_policy.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Run full citizen test suite to confirm no regression**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/ -k "govern or citizen" -v --no-header
```

Expected: existing tests stay green.

- [ ] **Step 6: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/citizen.py citizenry/tests/test_govern_pin_policy.py \
  && git commit -m "$(cat <<'EOF'
citizenry(constitution-v2): GOVERN(pin_policy, ...) handler

- new body type carries policy_id + hf_revision_sha + aibom_url + rekor_log_index
- citizen tracks self.policy_pinning dict; replaces on subsequent pins
- malformed payloads logged, never raised
- 3 tests in test_govern_pin_policy.py
- coexists with legacy policy_commit body type (unchanged)

Spec: §7.4 (Constitution v2), §7.7 (audit & provenance), §10 sub-1

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: GOVERN body type — `pin_tool_manifest`

**Files:**
- Modify: `citizenry/citizen.py` (extend `_handle_govern`)
- Test: `citizenry/tests/test_govern_pin_tool_manifest.py`

- [ ] **Step 1: Write the failing test**

Create `citizenry/tests/test_govern_pin_tool_manifest.py`:

```python
"""GOVERN body type: pin_tool_manifest — sha256 pin of an MCP server's tool surface."""
import time

from citizenry.citizen import Citizen
from citizenry.protocol import Envelope, MessageType


def _env(body: dict) -> Envelope:
    return Envelope(
        version=1,
        type=int(MessageType.GOVERN),
        sender="ab" * 32,
        recipient="*",
        timestamp=time.time(),
        ttl=3600.0,
        body=body,
        signature="cd" * 64,
    )


def test_pin_tool_manifest_records_sha(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-pin-tm", citizen_type="test")
    c._handle_govern(_env({
        "type": "pin_tool_manifest",
        "server": "bus-mcp",
        "sha256": "1" * 64,
    }), addr=("127.0.0.1", 0))
    assert c.tool_manifest_pinning == {"bus-mcp": "1" * 64}


def test_pin_tool_manifest_replaces_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-pin-tm-replace", citizen_type="test")
    c._handle_govern(_env({
        "type": "pin_tool_manifest", "server": "bus-mcp", "sha256": "1" * 64,
    }), addr=("127.0.0.1", 0))
    c._handle_govern(_env({
        "type": "pin_tool_manifest", "server": "bus-mcp", "sha256": "2" * 64,
    }), addr=("127.0.0.1", 0))
    assert c.tool_manifest_pinning["bus-mcp"] == "2" * 64


def test_pin_tool_manifest_rejects_short_sha(monkeypatch, tmp_path):
    """Sha256 hex must be exactly 64 chars."""
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-pin-tm-bad", citizen_type="test")
    c._handle_govern(_env({
        "type": "pin_tool_manifest", "server": "bus-mcp", "sha256": "abc",
    }), addr=("127.0.0.1", 0))
    assert "bus-mcp" not in c.tool_manifest_pinning
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_govern_pin_tool_manifest.py -v
```

Expected: FAIL — handler not yet present.

- [ ] **Step 3: Add the handler**

In `citizenry/citizen.py`, in `_handle_govern`, after the `pin_policy` branch from Task 4, add:

```python
        elif gov_type == "pin_tool_manifest":
            server = body.get("server", "")
            sha = body.get("sha256", "")
            if server and len(sha) == 64:
                try:
                    int(sha, 16)
                    self.tool_manifest_pinning[server] = sha
                    self._log(
                        f"TOOL MANIFEST PIN from [{short_id(env.sender)}]: "
                        f"{server} → {sha[:12]}"
                    )
                    self._add_log("GOVERN", short_id(env.sender), f"tm-pin: {server}")
                except ValueError:
                    self._log(f"pin_tool_manifest non-hex sha for {server}")
            else:
                self._log(
                    f"pin_tool_manifest MALFORMED from [{short_id(env.sender)}]: "
                    f"server={server!r} sha_len={len(sha)}"
                )
```

- [ ] **Step 4: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_govern_pin_tool_manifest.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/citizen.py citizenry/tests/test_govern_pin_tool_manifest.py \
  && git commit -m "$(cat <<'EOF'
citizenry(constitution-v2): GOVERN(pin_tool_manifest, ...) handler

- pins sha256 of an MCP server's tool manifest (server, sha256)
- citizen tracks self.tool_manifest_pinning dict
- rejects non-64-char or non-hex sha256 silently with a log line
- 3 tests in test_govern_pin_tool_manifest.py

Spec: §7.3 (gateway tool-manifest signing), §7.4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: GOVERN body type — `rotate_node_key`

**Files:**
- Modify: `citizenry/citizen.py` (extend `_handle_govern`)
- Test: `citizenry/tests/test_govern_rotate_node_key.py`

`rotate_node_key` triggers a genome-refresh sweep: bumps `node_key_version` and emits a one-shot signal that downstream marketplace bidders use to mark their cached neighbor genomes as stale.

- [ ] **Step 1: Write the failing test**

Create `citizenry/tests/test_govern_rotate_node_key.py`:

```python
"""GOVERN body type: rotate_node_key — bumps node_key_version on receivers."""
import time

from citizenry.citizen import Citizen
from citizenry.protocol import Envelope, MessageType


def _env(body: dict) -> Envelope:
    return Envelope(
        version=1,
        type=int(MessageType.GOVERN),
        sender="ab" * 32,
        recipient="*",
        timestamp=time.time(),
        ttl=3600.0,
        body=body,
        signature="cd" * 64,
    )


def test_rotate_node_key_bumps_version(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-rotate", citizen_type="test")
    assert c.node_key_version == 1
    c._handle_govern(_env({
        "type": "rotate_node_key",
        "old_node_pubkey": "a" * 64,
        "new_node_pubkey": "b" * 64,
        "version": 2,
    }), addr=("127.0.0.1", 0))
    assert c.node_key_version == 2


def test_rotate_node_key_records_pubkey_for_marketplace(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-rotate-pk", citizen_type="test")
    c._handle_govern(_env({
        "type": "rotate_node_key",
        "old_node_pubkey": "a" * 64,
        "new_node_pubkey": "b" * 64,
        "version": 2,
    }), addr=("127.0.0.1", 0))
    assert c._stale_node_pubkeys == {"a" * 64}


def test_rotate_node_key_rejects_old_version(monkeypatch, tmp_path):
    """Receiving an older rotate (version < current) is ignored."""
    monkeypatch.setenv("HOME", str(tmp_path))
    c = Citizen(name="test-rotate-old", citizen_type="test")
    c.node_key_version = 5
    c._handle_govern(_env({
        "type": "rotate_node_key",
        "old_node_pubkey": "a" * 64,
        "new_node_pubkey": "b" * 64,
        "version": 3,
    }), addr=("127.0.0.1", 0))
    assert c.node_key_version == 5
    assert c._stale_node_pubkeys == set()
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_govern_rotate_node_key.py -v
```

Expected: AttributeError on `c.node_key_version` / `_stale_node_pubkeys`.

- [ ] **Step 3: Add tracking attributes and handler**

In `citizenry/citizen.py`, in `Citizen.__init__` (near where Task 4 added `policy_pinning`):

```python
        self.node_key_version: int = 1
        self._stale_node_pubkeys: set[str] = set()
```

In `_handle_govern`, after the `pin_tool_manifest` branch from Task 5, add:

```python
        elif gov_type == "rotate_node_key":
            old_pk = body.get("old_node_pubkey", "")
            new_pk = body.get("new_node_pubkey", "")
            new_version = int(body.get("version", 0))
            if new_version > self.node_key_version and len(old_pk) == 64 and len(new_pk) == 64:
                self.node_key_version = new_version
                self._stale_node_pubkeys.add(old_pk)
                self._log(
                    f"NODE KEY ROTATE from [{short_id(env.sender)}]: "
                    f"{short_id(old_pk)} → {short_id(new_pk)} (v{new_version})"
                )
                self._add_log("GOVERN", short_id(env.sender), f"rotate: v{new_version}")
            else:
                self._log(
                    f"rotate_node_key IGNORED from [{short_id(env.sender)}]: "
                    f"version={new_version} current={self.node_key_version}"
                )
```

- [ ] **Step 4: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_govern_rotate_node_key.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/citizen.py citizenry/tests/test_govern_rotate_node_key.py \
  && git commit -m "$(cat <<'EOF'
citizenry(constitution-v2): GOVERN(rotate_node_key, ...) handler

- bumps citizen.node_key_version when a higher version arrives
- records old node_pubkey in self._stale_node_pubkeys for marketplace consumers
- rejects out-of-order rotates (older version)
- 3 tests in test_govern_rotate_node_key.py

Fixes architectural smell #5 (co-location bonus fragile under node-key rotation).
Spec: §5.2 smell #5, §7.4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: ConstitutionView exposes new v2 fields

**Files:**
- Modify: `citizenry/governance/__init__.py:56-89` (`ConstitutionView` class)
- Test: extend `citizenry/governance/test_emex_constitution.py` OR create `citizenry/tests/test_constitution_view_v2.py` (we add a new file to keep the EMEX test focused)
- Test: `citizenry/tests/test_constitution_view_v2.py`

- [ ] **Step 1: Write the failing test**

Create `citizenry/tests/test_constitution_view_v2.py`:

```python
"""ConstitutionView exposes the v2 fields added in Constitution."""
import json
from pathlib import Path

import pytest

from citizenry.governance import load_constitution


def test_view_exposes_v2_fields(tmp_path):
    payload = {
        "version": 2,
        "governor_pubkey": "",
        "authority_pubkey": "ab" * 32,
        "node_key_version": 7,
        "articles": [],
        "laws": [],
        "servo_limits": {},
        "tool_manifest_pinning": {"bus-mcp": "sha256:abc"},
        "policy_pinning": {"smolvla-pickplace-v3": "hf:rev:def"},
        "embassy_topics": {"opcua_namespace": "ns/q/cell1"},
        "compliance_artefacts": {"aibom_url": "https://x/aibom.cdx.json"},
        "signature": "",
    }
    p = tmp_path / "c.json"
    p.write_text(json.dumps(payload))
    view = load_constitution(p)
    assert view.authority_pubkey == "ab" * 32
    assert view.node_key_version == 7
    assert view.tool_manifest_pinning == {"bus-mcp": "sha256:abc"}
    assert view.policy_pinning == {"smolvla-pickplace-v3": "hf:rev:def"}
    assert view.embassy_topics == {"opcua_namespace": "ns/q/cell1"}
    assert view.compliance_artefacts == {"aibom_url": "https://x/aibom.cdx.json"}


def test_view_v1_constitution_returns_empty_v2_fields(tmp_path):
    """A v1 Constitution loaded through the view yields empty v2 dicts."""
    payload = {
        "version": 1,
        "governor_pubkey": "ef" * 32,
        "articles": [],
        "laws": [],
        "servo_limits": {},
        "signature": "",
    }
    p = tmp_path / "v1.json"
    p.write_text(json.dumps(payload))
    view = load_constitution(p)
    assert view.authority_pubkey == ""
    assert view.node_key_version == 1
    assert view.tool_manifest_pinning == {}
    assert view.policy_pinning == {}
    assert view.embassy_topics == {}
    assert view.compliance_artefacts == {}
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_constitution_view_v2.py -v
```

Expected: AttributeError on `view.authority_pubkey`.

- [ ] **Step 3: Extend `ConstitutionView`**

In `citizenry/governance/__init__.py`, find the `ConstitutionView` dataclass and add property accessors for the v2 fields. After the existing `signature` property, add:

```python
    @property
    def authority_pubkey(self) -> str:
        return self.base.authority_pubkey

    @property
    def node_key_version(self) -> int:
        return self.base.node_key_version

    @property
    def tool_manifest_pinning(self) -> dict[str, str]:
        return dict(self.base.tool_manifest_pinning)

    @property
    def policy_pinning(self) -> dict[str, str]:
        return dict(self.base.policy_pinning)

    @property
    def embassy_topics(self) -> dict[str, str]:
        return dict(self.base.embassy_topics)

    @property
    def compliance_artefacts(self) -> dict[str, str]:
        return dict(self.base.compliance_artefacts)
```

- [ ] **Step 4: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_constitution_view_v2.py \
            citizenry/governance/test_emex_constitution.py -v
```

Expected: new + EMEX tests all pass.

- [ ] **Step 5: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/governance/__init__.py \
             citizenry/tests/test_constitution_view_v2.py \
  && git commit -m "$(cat <<'EOF'
citizenry(constitution-v2): ConstitutionView exposes v2 fields

- ConstitutionView gains authority_pubkey, node_key_version,
  tool_manifest_pinning, policy_pinning, embassy_topics,
  compliance_artefacts properties (read-only views over base)
- 2 tests covering v2 payload + v1-fallback empty dicts

Spec: §7.4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: GovernorCitizen signs Constitution amendments with Authority key

**Files:**
- Modify: `citizenry/governor_citizen.py` (Constitution-issuing path)
- Test: `citizenry/tests/test_governor_citizen_signs_with_authority.py`

This is the architectural smell #1 fix. Today the GovernorCitizen signs Constitution via its own per-citizen `governor.key`. After this task, it signs via the Authority key. The `governor.key` continues to sign per-citizen mesh messages (heartbeats, ADVERTISEs, etc.); only Constitution and Law amendments switch to the Authority key.

- [ ] **Step 1: Read the relevant section of governor_citizen.py to find the Constitution-issuing site**

```bash
cd ~/linux-usb && grep -n "constitution\|sign\|Constitution" citizenry/governor_citizen.py | head -30
```

Note the line numbers where Constitution is signed/transmitted. The GOVERN-broadcast site uses the citizen's signing key today.

- [ ] **Step 2: Write the failing test**

Create `citizenry/tests/test_governor_citizen_signs_with_authority.py`:

```python
"""Smell #1 fix: GovernorCitizen signs Constitution amendments with Authority key.

The per-citizen governor.key remains the identity for heartbeat/advertise
mesh traffic; only Constitution and Law amendments switch to authority.key.
"""
import os
from pathlib import Path

import pytest
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder

from citizenry.constitution import default_constitution


def test_governor_signs_with_authority_key(monkeypatch, tmp_path):
    """Loading the GovernorCitizen and asking it to ratify a fresh Constitution
    must produce a signature verifiable with the Authority pubkey, not the
    governor citizen's pubkey."""
    monkeypatch.setenv("HOME", str(tmp_path))
    citizenry_dir = tmp_path / ".citizenry"
    citizenry_dir.mkdir()

    # Pre-create distinct authority and governor identities so we can verify
    # the signature provenance.
    auth_key = SigningKey.generate()
    (citizenry_dir / "authority.key").write_bytes(auth_key.encode())
    (citizenry_dir / "authority.key").chmod(0o600)
    gov_key = SigningKey.generate()
    (citizenry_dir / "governor.key").write_bytes(gov_key.encode())
    (citizenry_dir / "governor.key").chmod(0o600)

    from citizenry.governor_citizen import GovernorCitizen

    g = GovernorCitizen(name="governor")
    c = default_constitution()
    g.ratify_constitution(c)

    auth_pub = VerifyKey(auth_key.verify_key.encode())
    gov_pub = VerifyKey(gov_key.verify_key.encode())

    # The Constitution must verify against the Authority key.
    assert c.verify(auth_pub) is True
    # And NOT against the governor citizen key.
    assert c.verify(gov_pub) is False
    # authority_pubkey on the Constitution must match the authority key, not the governor key.
    assert c.authority_pubkey == auth_key.verify_key.encode(encoder=HexEncoder).decode()


def test_governor_heartbeat_still_signed_with_governor_key(monkeypatch, tmp_path):
    """Confirm the per-citizen governor key remains the heartbeat/advertise
    identity (no regression on existing mesh signatures)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    citizenry_dir = tmp_path / ".citizenry"
    citizenry_dir.mkdir()
    auth_key = SigningKey.generate()
    (citizenry_dir / "authority.key").write_bytes(auth_key.encode())
    (citizenry_dir / "authority.key").chmod(0o600)
    gov_key = SigningKey.generate()
    (citizenry_dir / "governor.key").write_bytes(gov_key.encode())
    (citizenry_dir / "governor.key").chmod(0o600)

    from citizenry.governor_citizen import GovernorCitizen

    g = GovernorCitizen(name="governor")
    # Heartbeat envelope sender must be the governor citizen pubkey, not Authority.
    gov_pub_hex = gov_key.verify_key.encode(encoder=HexEncoder).decode()
    assert g.pubkey == gov_pub_hex
```

- [ ] **Step 3: Run the test, confirm it fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_governor_citizen_signs_with_authority.py -v
```

Expected: `test_governor_signs_with_authority_key` FAILS — Constitution currently signed by `governor.key` not `authority.key`. `test_governor_heartbeat_still_signed_with_governor_key` should already pass (no change to heartbeat path).

- [ ] **Step 4: Add `ratify_constitution` (and reroute existing Constitution-signing path) to use Authority key**

In `citizenry/governor_citizen.py`:

a. At the top of the file, near other imports, add:

```python
from citizenry.authority import load_or_create_authority_key
```

b. Add a new method on `GovernorCitizen`:

```python
    def ratify_constitution(self, constitution) -> None:
        """Sign and persist a Constitution with the Authority key (not the
        per-citizen governor key)."""
        auth_key = load_or_create_authority_key()
        constitution.sign(auth_key)
```

c. Audit any existing `constitution.sign(self.signing_key)` call sites in `governor_citizen.py` and replace them with `self.ratify_constitution(constitution)`. (At minimum the place where the Governor first signs the on-disk Constitution at boot.)

If there is no existing `constitution.sign(self.signing_key)` call site (the Constitution may currently be loaded pre-signed from disk), the new `ratify_constitution` method is the canonical entry point for amendments going forward; existing on-disk Constitutions are migrated separately by Task 3's CLI.

- [ ] **Step 5: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_governor_citizen_signs_with_authority.py -v
```

Expected: 2 PASS.

- [ ] **Step 6: Run the broader governor test suite to confirm no regression**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/ -k "governor" -v
```

Expected: pre-existing tests stay green.

- [ ] **Step 7: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/governor_citizen.py \
             citizenry/tests/test_governor_citizen_signs_with_authority.py \
  && git commit -m "$(cat <<'EOF'
citizenry(constitution-v2): GovernorCitizen ratifies with Authority key

- new method GovernorCitizen.ratify_constitution(c) signs with authority.key
- per-citizen governor.key continues to sign heartbeat / advertise / etc.
- only Constitution and Law amendments switch to the Authority key
- 2 tests: signature provenance (authority verifies, governor does not)
  and heartbeat-pubkey-unchanged regression check

Fixes architectural smell #1 (governor citizen key vs node key collapse).
Spec: §5.2 smell #1, §7.4

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `citizen_mcp_server.govern_update` signs with Authority key

**Files:**
- Modify: `citizenry/mcp/citizen_mcp_server.py` (find the `govern_update` MCP tool around line 178)

The MCP server today reads `~/.citizenry/node.key` for signing GOVERN messages. It must use the Authority key for Constitution/Law/pin amendments. Other GOVERN body types (e.g. `genome`, `skill_tree`) are not Authority-class — they remain signed with the governor citizen key. For Sub-1's scope we only switch the Constitution-amendment path; pins (`pin_policy`, `pin_tool_manifest`, `rotate_node_key`) likewise become Authority-signed.

- [ ] **Step 1: Read the current implementation site**

```bash
cd ~/linux-usb && sed -n '170,210p' citizenry/mcp/citizen_mcp_server.py
```

Note: at line ~98 the server reads `~/.citizenry/node.key`. At line ~178 it loads the constitution dict, applies a mutator, re-signs, and multicasts a GOVERN. This path becomes Authority-signed for Constitution-class amendments.

- [ ] **Step 2: Write a small failing test**

Create `citizenry/tests/test_mcp_govern_update_uses_authority.py`:

```python
"""MCP server's govern_update path signs Constitution amendments with Authority."""
import json
from pathlib import Path

import pytest
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder

from citizenry.constitution import default_constitution


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    citizenry_dir = tmp_path / ".citizenry"
    citizenry_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    auth = SigningKey.generate()
    (citizenry_dir / "authority.key").write_bytes(auth.encode())
    (citizenry_dir / "authority.key").chmod(0o600)
    node = SigningKey.generate()
    (citizenry_dir / "node.key").write_bytes(node.encode())
    (citizenry_dir / "node.key").chmod(0o600)
    # Pre-place a v2 Constitution that the server will mutate.
    c = default_constitution()
    c.sign(auth)
    (citizenry_dir / "governor.constitution.json").write_text(json.dumps(c.to_dict()))
    return tmp_path, auth, node


def test_govern_update_resigns_with_authority_key(isolated):
    """After a govern_update mutation, the on-disk Constitution must verify
    against the Authority key, not the node key."""
    tmp_path, auth, node = isolated
    from citizenry.mcp.citizen_mcp_server import _resign_constitution_with_authority

    cfg_path = tmp_path / ".citizenry" / "governor.constitution.json"
    data = json.loads(cfg_path.read_text())
    data["laws"] = [
        {"id": "test_new_law", "description": "added by mcp", "params": {"v": 1}}
    ]
    new_dict = _resign_constitution_with_authority(data)
    auth_pub = VerifyKey(auth.verify_key.encode())
    node_pub = VerifyKey(node.verify_key.encode())
    from citizenry.constitution import Constitution
    c = Constitution.from_dict(new_dict)
    assert c.verify(auth_pub) is True
    assert c.verify(node_pub) is False
    assert c.authority_pubkey == auth.verify_key.encode(encoder=HexEncoder).decode()
```

- [ ] **Step 3: Run the test, confirm it fails**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_mcp_govern_update_uses_authority.py -v
```

Expected: ImportError — `_resign_constitution_with_authority` doesn't exist yet.

- [ ] **Step 4: Implement the helper and reroute the govern path**

In `citizenry/mcp/citizen_mcp_server.py`:

a. Near the existing imports, add:

```python
from citizenry.authority import load_or_create_authority_key
```

b. Add a small module-level helper (this is what the test calls directly so we can verify in isolation):

```python
def _resign_constitution_with_authority(constitution_dict: dict) -> dict:
    """Strip any existing signature and re-sign the Constitution with the
    Authority key. Returns the new dict."""
    from citizenry.constitution import Constitution
    c = Constitution.from_dict(constitution_dict)
    c.signature = ""
    c.authority_pubkey = ""
    auth_key = load_or_create_authority_key()
    c.sign(auth_key)
    return c.to_dict()
```

c. In the existing `govern_update` MCP tool (at the point where the server loads the Constitution dict, applies a mutator, and re-signs before multicasting), replace the existing re-sign/serialise step with a call to `_resign_constitution_with_authority(...)`. Keep the multicast step using the node key — the wire-level multicast envelope is signed by the node, but the **payload it carries** (the Constitution itself) is signed by the Authority. Two layers, two distinct keys.

- [ ] **Step 5: Run the test, confirm pass**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/tests/test_mcp_govern_update_uses_authority.py -v
```

Expected: 1 PASS.

- [ ] **Step 6: Smoke-test the existing MCP test suite**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && pytest citizenry/mcp/test_citizen_mcp_server.py -v
```

Expected: pre-existing tests stay green. If any pre-existing test was hard-coding `node.key` as the Constitution signer (rather than as the multicast envelope signer), that test legitimately needs an update to assert the new two-layer model — fix it inline.

- [ ] **Step 7: Commit**

```bash
cd ~/linux-usb \
  && git add citizenry/mcp/citizen_mcp_server.py \
             citizenry/tests/test_mcp_govern_update_uses_authority.py \
  && git commit -m "$(cat <<'EOF'
citizenry(constitution-v2): MCP govern_update re-signs Constitution with Authority

- new helper _resign_constitution_with_authority(dict) -> dict
- govern_update mutates Constitution and re-signs payload with authority.key
- multicast envelope still signed with node.key (transport layer unchanged)
- two-layer model: envelope = node, payload = Authority
- 1 test asserting payload signature provenance

Spec: §7.4 (identity & trust model — three independent axes)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Run the migration on this machine and update persona docs

**Files:**
- Modify (runtime, NOT git-tracked): `~/.citizenry/governor.constitution.json` etc. — migrated in place via the Task 3 CLI.
- Create runtime artefact: `~/.citizenry/authority.key` (mode 0600).
- Modify: `~/CLAUDE.md` and `~/.claude/projects/-home-bradley/memory/device_persona.md` — only via the persona refresh script. Not part of this commit.
- Modify: `docs/superpowers/specs/2026-04-30-citizenry-physical-ai-architecture-design.md` — strike the "smell #1 fix pending" annotation in §5.2 if any (none currently; no edit needed unless ambiguity surfaces during execution).

- [ ] **Step 1: Dry-run the migration on the live runtime files**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && python -m citizenry.scripts.migrate_constitution --dry-run
```

Expected: lists each `~/.citizenry/*.constitution.json` file and its current version. Read carefully — confirm only files you expect (governor, pi-follower) are listed.

- [ ] **Step 2: Run the migration for real**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate \
  && python -m citizenry.scripts.migrate_constitution
```

Expected output: "migrated: <path>" lines, "<N> file(s) migrated."

- [ ] **Step 3: Verify the on-disk artefacts**

```bash
ls -la ~/.citizenry/authority.key ~/.citizenry/*.constitution.json ~/.citizenry/*.v1.bak.json
```

Expected: `authority.key` present (mode 0600, 32 bytes), each `*.constitution.json` has a `*.v1.bak.json` alongside it.

- [ ] **Step 4: Verify the new Constitution loads and verifies**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate && python -c "
import json
from pathlib import Path
from citizenry.constitution import Constitution
from citizenry.authority import authority_pubkey_hex

for p in sorted(Path.home().joinpath('.citizenry').glob('*.constitution.json')):
    d = json.loads(p.read_text())
    c = Constitution.from_dict(d)
    ok = c.verify()
    print(f'{p.name}: version={c.version} verify={ok} authority={c.authority_pubkey[:12]}…')
print(f'(authority.key pubkey: {authority_pubkey_hex()[:12]}…)')
"
```

Expected: every file shows `version=2 verify=True` and the `authority` short-id matches the runtime authority key.

- [ ] **Step 5: Run persona-refresh so device_persona.md picks up the new identity model**

```bash
bash ~/linux-usb/scripts/claude-persona-refresh.sh
```

Expected: `~/CLAUDE.md` and `~/.claude/projects/-home-bradley/memory/device_persona.md` updated (managed files; not committed from here).

- [ ] **Step 6: Commit (no on-disk runtime artefacts; only the test/code changes from Tasks 1-9 are in git)**

There is nothing new to commit at this step. The runtime migration is local. Move to the closing summary commit:

```bash
cd ~/linux-usb && git log --oneline -10
```

Expected: 9 new commits from Tasks 1-9, plus the umbrella spec commit `3d41b09`.

---

## Self-Review

Run through the spec sections that Sub-1 must implement:

- **§5.2 smell #1** (Constitution signed by governor.key vs node.key collapse) → Tasks 8, 9.
- **§5.2 smell #5** (co-location bonus fragile to node-key rotation) → Task 6 (`rotate_node_key` GOVERN).
- **§7.4 Constitution v2 wire format additions** (`authority_pubkey`, `node_key_version`, `tool_manifest_pinning`, `policy_pinning`, `embassy_topics`, `compliance_artefacts`) → Task 1.
- **§7.4 GOVERN message types** (`amend_law` already exists as `law_update`; `rotate_node_key`, `pin_policy`, `pin_tool_manifest`, `emergency_stop` already exists) → Tasks 4, 5, 6.
- **§7.4 three identity axes** (node, role, Authority) → Task 2 (Authority module), preserved node + role identities (already exist).
- **§10 sub-1 acceptance** ("New schema, migration of existing constitution.json files, role-key separation, GOVERN message extensions, fix smell #1") → Tasks 1-9 cover this; Task 10 runs the migration on this machine.

No `TBD` / `TODO` / `implement later` strings in any task. Every step has either a code block or an exact command.

Type / signature consistency:

- `Constitution.sign(signing_key: SigningKey)` — single signature throughout.
- `migrate_v1_dict(v1_dict, authority_signing_key)` — same name in helper and test.
- `migrate_file(path, authority_signing_key=None)` — keyword arg consistent.
- `load_or_create_authority_key()` and `authority_pubkey_hex()` — names align across module and tests.
- `_resign_constitution_with_authority(dict) -> dict` — module-level helper, same name in test.
- `policy_pinning`, `tool_manifest_pinning`, `node_key_version`, `_stale_node_pubkeys` — used consistently across Tasks 4, 5, 6, 7.

No gaps detected.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-30-constitution-v2-identity.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
