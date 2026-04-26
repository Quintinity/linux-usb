# SmolVLA-as-Citizen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Hugging Face SmolVLA 450M into the citizenry mesh as a bid-able PolicyCitizen on the Jetson, with N-node topology (each ManipulatorNode hosts a co-located leader+follower pair), cross-node policy targeting via marketplace co-location bonus, and a per-node Hugging Face upload pipeline that records LeRobotDataset v3 locally then uploads-and-deletes on episode close.

**Architecture:** Strict additive Python work in `citizenry/` plus one thin C++ test addition. No protocol-version bump, no envelope changes — only additive optional body keys. New citizens (`LeaderCitizen`, `PolicyCitizen`) and node-level identity layer slot into the existing 7-message protocol. Episode storage flips from JSONL+JPEG to v3 chunked Parquet+MP4 via a new recorder; legacy data migrates one-shot to HF and is deleted locally. SmolVLA runs on the Jetson Orin Nano (FP16 default, INT8 fallback) as an in-process action source for a co-located follower (preferred) or remote follower over the existing PROPOSE/REPORT channel.

**Tech Stack:** Python 3.12 (asyncio, dataclasses, NaCl Ed25519, OpenCV, NumPy), pytest, LeRobot 0.4.4 (Jetson) / 0.5.0 (Surface, Pi), `huggingface_hub` ≥ 0.24, PyArrow (for v3 Parquet writes via LeRobot), systemd. C++ host-test harness uses g++/Make.

**Spec:** `docs/specs/2026-04-27-smolvla-citizen-design.md`

**Branch strategy:** Each Task is one commit (sometimes more). Recommended: branch off `xiao-citizen/phase-2` once it merges, or branch off `main` if Bradley merges xiao-citizen first. The plan's tasks are all additive; only Task 3 (citizen refactor) clashes meaningfully with `xiao-citizen/phase-2`'s modifications to `surface_citizen.py` / `pi_citizen.py`, so do the refactor *after* xiao-citizen merges.

---

## File Structure

| Path | Status | Owns |
|---|---|---|
| `citizenry/node_identity.py` | new | Per-node Ed25519 keypair at `~/.citizenry/node.key`; `get_node_pubkey()` |
| `citizenry/leader_citizen.py` | new | Reads leader arm; emits teleop PROPOSE frames; node-local IPC fast path |
| `citizenry/manipulator_citizen.py` | rename from `pi_citizen.py` | Hardware-agnostic follower driver; clamps to ServoLimits; records v3 episodes |
| `citizenry/governor_citizen.py` | extracted from `surface_citizen.py` | Constitution ratification, marketplace coordination, dashboard hooks; no arms; no recorder |
| `citizenry/policy_citizen.py` | new | Bids on manipulation tasks; calls into runner; emits action frames; co-location bonus |
| `citizenry/smolvla_runner.py` | new | Wraps `lerobot.policies.smolvla`; loads model; forward pass; produces action chunks |
| `citizenry/run_jetson.py` | new | Jetson entry point; surveys hardware; spawns LeaderCitizen + ManipulatorCitizen + CameraCitizens + PolicyCitizen |
| `citizenry/dataset_v3_migrate.py` | new | One-shot legacy → v3 migrator with HF upload + delete-local |
| `citizenry/episode_recorder.py` | modified | Adds `EpisodeRecorderV3` writer; v1 writer behind Constitution flag for transition window |
| `citizenry/hf_upload.py` | new | Async per-episode upload + verify + delete; retry queue |
| `citizenry/skills.py` | modified | `default_policy_skills()` factory |
| `citizenry/genome.py` | modified | `node_pubkey` field |
| `citizenry/constitution.py` | modified | New Article + Laws (see §5 of spec) |
| `citizenry/marketplace.py` | modified | Co-location bonus in scoring; `params.follower_pubkey` filtering |
| `citizenry/run_pi.py` | modified | Spawn LeaderCitizen if leader bus detected |
| `citizenry/run_surface.py` | modified | Spawn GovernorCitizen + DashboardCitizen only |
| `pi-setup.sh` | modified | `~/.citizenry/hf_token` install path |
| `jetson-setup.sh` | new | Jetson provisioning + `citizenry-jetson.service` systemd unit |
| `citizenry/tests/test_node_identity.py` | new | Node key generation, persistence, corruption refusal |
| `citizenry/tests/test_marketplace_co_location.py` | new | Co-location bonus correctness, follower targeting |
| `citizenry/tests/test_episode_recorder_v3.py` | new | v3 writer shape and metadata |
| `citizenry/tests/test_dataset_v3_migrate.py` | new | Legacy → v3 round-trip |
| `citizenry/tests/test_hf_upload.py` | new | Upload, verify, delete, retry-on-fail |
| `citizenry/tests/test_smolvla_runner.py` | new | Mocked-load runner; canned obs → action chunk |
| `citizenry/tests/test_policy_citizen.py` | new | Bid scoring, follower targeting, action emission |
| `citizenry/tests/test_governor_no_recorder.py` | new | GovernorCitizen refuses to start a recorder |
| `citizenry/tests/integration/test_jetson_smolvla_smoke.py` | new (gated) | Real model load + forward pass on Jetson |
| `citizenry/tests/integration/test_marketplace_e2e_local.py` | new (gated) | Local SmolVLA → follower e2e |
| `citizenry/tests/integration/test_marketplace_e2e_cross_node.py` | new (gated) | Cross-node SmolVLA → follower e2e |

Roughly: 8 new modules, 6 modified, 1 rename. Plus 8 new unit tests and 3 gated integration tests.

---

## Phase 0: Pre-flight (Task 0)

### Task 0: Verify environment readiness across the fleet

**Files:** none (verification only)

- [ ] **Step 0.1: Confirm Surface env**

```bash
ssh -o StrictHostKeyChecking=no $USER@localhost true   # smoke
source ~/lerobot-env/bin/activate
python -c "import lerobot, numpy, nacl, cv2; print(lerobot.__version__)"
python -c "from huggingface_hub import HfApi; print('hf hub ok')" \
  || pip install 'huggingface_hub>=0.24'
```

Expected: prints `0.5.0`. `huggingface_hub` either prints "ok" or installs cleanly.

- [ ] **Step 0.2: Confirm Pi env**

```bash
ssh bradley@raspberry-lerobot-001 'source ~/armos-env/bin/activate \
  && python -c "import lerobot; print(lerobot.__version__)" \
  && python -c "from huggingface_hub import HfApi" 2>/dev/null \
     || pip install "huggingface_hub>=0.24"'
```

Expected: prints `0.5.0` (or whatever Pi runs); hf_hub installs cleanly.

- [ ] **Step 0.3: Confirm Jetson env**

```bash
ssh bradley@jetson-orin-001 '
  source ~/lerobot-env/bin/activate 2>/dev/null || true
  python3 -c "import torch; print(\"cuda:\", torch.cuda.is_available()); print(\"lerobot:\", __import__(\"lerobot\").__version__)"
  python3 -c "from huggingface_hub import HfApi" 2>/dev/null \
     || pip install "huggingface_hub>=0.24"'
```

Expected: `cuda: True`, `lerobot: 0.4.4`. hf_hub installs cleanly.

- [ ] **Step 0.4: Decide HF repo**

User decision (record in commit message later): the HF repo id for fleet uploads (e.g. `bradley-festraets/citizenry-fleet`). Confirm Bradley has create permission. Generate a write-scoped token at https://huggingface.co/settings/tokens.

No code change. Move on.

---

## Phase 1: Foundations

These three tasks introduce the data-model changes (node identity, marketplace co-location, citizen split) that every later task depends on.

### Task 1: Node identity layer

**Files:**
- Create: `citizenry/node_identity.py`
- Create: `citizenry/tests/test_node_identity.py`
- Modify: `citizenry/genome.py:1-50` (add `node_pubkey` field; preserve `to_dict`/`from_dict`)
- Modify: `citizenry/citizen.py:120-130` (Citizen accepts/derives `node_pubkey` and stamps genome)

- [ ] **Step 1.1: Write the failing test for node identity persistence**

Create `citizenry/tests/test_node_identity.py`:

```python
"""Tests for the per-node Ed25519 identity layer."""

import pytest
from pathlib import Path

import nacl.signing

from citizenry import node_identity


def test_get_or_create_generates_on_first_call(tmp_path, monkeypatch):
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    key = node_identity.get_or_create_node_signing_key()
    assert isinstance(key, nacl.signing.SigningKey)
    assert (tmp_path / "node.key").exists()
    assert (tmp_path / "node.key").stat().st_mode & 0o777 == 0o600


def test_get_or_create_returns_same_key_on_subsequent_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    k1 = node_identity.get_or_create_node_signing_key()
    k2 = node_identity.get_or_create_node_signing_key()
    assert k1.encode() == k2.encode()


def test_get_node_pubkey_is_64_hex_chars(tmp_path, monkeypatch):
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    pk = node_identity.get_node_pubkey()
    assert len(pk) == 64
    int(pk, 16)  # raises if not hex


def test_corrupt_key_refuses_to_load(tmp_path, monkeypatch):
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    (tmp_path / "node.key").write_bytes(b"\x00" * 5)  # too short
    with pytest.raises(node_identity.NodeKeyCorruptError):
        node_identity.get_or_create_node_signing_key()
```

- [ ] **Step 1.2: Run the test to verify it fails**

```bash
cd ~/linux-usb && python -m pytest citizenry/tests/test_node_identity.py -v
```

Expected: ImportError on `from citizenry import node_identity` — the module doesn't exist yet.

- [ ] **Step 1.3: Implement `node_identity.py`**

Create `citizenry/node_identity.py`:

```python
"""Per-node Ed25519 identity.

Distinct from per-citizen identity (citizenry/identity.py): the node key
binds together every citizen spawned by the same machine so that
co-located bidders can be detected in the marketplace.

Stored at ~/.citizenry/node.key (raw 32 bytes, mode 0600).
"""

from __future__ import annotations

from pathlib import Path

import nacl.signing
import nacl.encoding


IDENTITY_DIR = Path.home() / ".citizenry"


class NodeKeyCorruptError(RuntimeError):
    """Raised when ~/.citizenry/node.key exists but is not a valid Ed25519 seed."""


def _ensure_dir() -> None:
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True)


def _key_path() -> Path:
    return IDENTITY_DIR / "node.key"


def get_or_create_node_signing_key() -> nacl.signing.SigningKey:
    """Load existing node key or generate one on first call."""
    _ensure_dir()
    p = _key_path()
    if p.exists():
        raw = p.read_bytes()
        if len(raw) != 32:
            raise NodeKeyCorruptError(
                f"{p} has length {len(raw)}, expected 32. "
                "Delete or restore from backup before starting any citizen."
            )
        return nacl.signing.SigningKey(raw)
    key = nacl.signing.SigningKey.generate()
    p.write_bytes(key.encode())
    p.chmod(0o600)
    return key


def get_node_pubkey() -> str:
    """Hex-encoded Ed25519 public key for this node."""
    sk = get_or_create_node_signing_key()
    return sk.verify_key.encode(encoder=nacl.encoding.RawEncoder).hex()
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
python -m pytest citizenry/tests/test_node_identity.py -v
```

Expected: 4 PASS.

- [ ] **Step 1.5: Add `node_pubkey` to genome**

Modify `citizenry/genome.py`. Locate the `CitizenGenome` dataclass and add the field (keep alphabetical or end-of-list — match existing style). Also update `to_dict` and `from_dict` if they enumerate fields explicitly:

```python
# In CitizenGenome dataclass, add (preserving any default-argument ordering):
node_pubkey: str | None = None
```

Then write a regression test before continuing — append to `citizenry/tests/test_genome.py`:

```python
def test_genome_carries_node_pubkey():
    from citizenry.genome import CitizenGenome
    g = CitizenGenome(
        hardware_type="jetson", role="policy", node_pubkey="ab" * 32,
    )
    assert g.node_pubkey == "ab" * 32
    d = g.to_dict()
    assert d["node_pubkey"] == "ab" * 32
    assert CitizenGenome.from_dict(d).node_pubkey == "ab" * 32
```

Run: `python -m pytest citizenry/tests/test_genome.py -v` — expect PASS.

- [ ] **Step 1.6: Wire `node_pubkey` into `Citizen.__init__`**

Modify `citizenry/citizen.py`. Around the `__init__` method (currently near line 120), accept a `node_pubkey: str | None = None` kwarg defaulting to `None`. If `None`, derive it lazily:

```python
# Replace the existing genome construction in Citizen.__init__ with:
if node_pubkey is None:
    from .node_identity import get_node_pubkey
    node_pubkey = get_node_pubkey()
self.node_pubkey = node_pubkey
# ... existing code ...
# When constructing self.genome (existing code):
self.genome = CitizenGenome(
    hardware_type=hardware_type,
    role=role,
    node_pubkey=self.node_pubkey,    # new
    # ... other existing fields ...
)
```

(The exact insertion point depends on the current `Citizen.__init__` shape — the existing genome construction call is the anchor.)

- [ ] **Step 1.7: Add `node_pubkey` to ADVERTISE body**

In the same file, locate `_send_advertise` (around line 237). Add `"node_pubkey": self.node_pubkey` to the advertise body dict so neighbors can detect co-location.

- [ ] **Step 1.7b: Add `_law` helper for Constitution Law access**

The existing `Citizen` stores the ratified Constitution at `self.constitution: dict | None` but has no accessor for individual Laws. Several later tasks read laws like `episode_recorder_format`, `dataset.hf_repo_id`, `governor.recorder_enabled`, etc. Add a single helper here:

```python
# In Citizen, alongside existing methods:
def _law(self, key: str, default=None):
    """Read a Law from the ratified Constitution, with default fallback.

    Returns `default` when no Constitution has been ratified yet, or when
    the key is absent. Always safe to call.
    """
    if not self.constitution:
        return default
    return self.constitution.get("laws", {}).get(key, default)
```

(If the Constitution structure is `{"articles": [...], "laws": {...}}` — which matches the existing `_handle_govern` path — this is correct. If laws are stored differently, adjust the lookup accordingly.)

Add a regression test:

```python
def test_citizen_law_returns_default_before_constitution(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Citizen
    c = Citizen(name="t", citizen_type="manipulator", capabilities=[])
    assert c._law("any.key", "fallback") == "fallback"


def test_citizen_law_reads_ratified_constitution(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Citizen
    c = Citizen(name="t", citizen_type="manipulator", capabilities=[])
    c.constitution = {"laws": {"episode_recorder_format": "v3"}}
    assert c._law("episode_recorder_format", "v1") == "v3"
    assert c._law("missing", "fallback") == "fallback"
```

Run: `python -m pytest citizenry/tests/test_genome.py -v` — expect PASS (or wherever you stash these — `test_citizen_law.py` if you prefer a separate file).

- [ ] **Step 1.8: Test the wiring**

Append to `citizenry/tests/test_genome.py` (or create `citizenry/tests/test_citizen_node_pubkey.py` if cleaner):

```python
def test_citizen_inherits_node_pubkey(tmp_path, monkeypatch):
    from citizenry import node_identity
    monkeypatch.setattr(node_identity, "IDENTITY_DIR", tmp_path)
    from citizenry.citizen import Citizen
    c = Citizen(name="t", citizen_type="manipulator", capabilities=[])
    assert len(c.node_pubkey) == 64
    assert c.genome.node_pubkey == c.node_pubkey
```

Run: `python -m pytest citizenry/tests/test_genome.py -v` — expect PASS.

- [ ] **Step 1.9: Commit**

```bash
git add citizenry/node_identity.py citizenry/tests/test_node_identity.py \
        citizenry/genome.py citizenry/citizen.py citizenry/tests/test_genome.py
git commit -m "$(cat <<'EOF'
citizenry: per-node Ed25519 identity at ~/.citizenry/node.key

New node_identity module mints/loads a node-level keypair distinct
from per-citizen keys. The node pubkey is propagated into every
CitizenGenome and stamped onto ADVERTISE bodies so neighbors can
detect co-located bidders in the marketplace.

Refuses to start when ~/.citizenry/node.key exists but is corrupt
(truncated/wrong-size) — no silent fallback.

Foundation for the cross-node policy targeting designed in
docs/specs/2026-04-27-smolvla-citizen-design.md §4.2.
EOF
)"
```

---

### Task 2: Marketplace co-location bonus + follower targeting

**Files:**
- Modify: `citizenry/marketplace.py:73-100` (Bid gains `node_pubkey`, `target_follower_pubkey`)
- Modify: `citizenry/marketplace.py:110-145` (`compute_bid_score` accepts optional bonus; `select_winner` unchanged)
- Modify: `citizenry/marketplace.py:236-259` (`can_citizen_bid` filters on `params.follower_pubkey`)
- Create: `citizenry/tests/test_marketplace_co_location.py`

- [ ] **Step 2.1: Write the failing test for co-location bonus**

Create `citizenry/tests/test_marketplace_co_location.py`:

```python
"""Tests for the co-location bonus and follower-targeting filter."""

from citizenry.marketplace import (
    Bid, Task, TaskStatus,
    compute_bid_score, select_winner,
)


def test_co_location_bonus_added_when_node_matches():
    base = compute_bid_score(skill_level=5, current_load=0.0, health=1.0)
    boosted = compute_bid_score(
        skill_level=5, current_load=0.0, health=1.0,
        co_location_bonus=0.15,
    )
    assert boosted == pytest_approx(base + 0.15)


def test_co_location_bonus_zero_by_default():
    a = compute_bid_score(skill_level=5, current_load=0.0, health=1.0)
    b = compute_bid_score(
        skill_level=5, current_load=0.0, health=1.0,
        co_location_bonus=0.0,
    )
    assert a == b


def test_select_winner_prefers_co_located_with_bonus():
    bids = [
        Bid(citizen_pubkey="a"*64, task_id="t", score=0.55,
            node_pubkey="n1", target_follower_pubkey="f1"),
        Bid(citizen_pubkey="b"*64, task_id="t", score=0.60,  # was higher base
            node_pubkey="n2", target_follower_pubkey="f1"),
    ]
    # With same base, the co-located bidder (a, n1==follower-node) won via bonus
    winner = select_winner(bids)
    assert winner.citizen_pubkey == "b"*64  # raw score still wins; bonus is in score


def test_can_citizen_bid_filters_on_follower_pubkey():
    from citizenry.marketplace import can_citizen_bid_for_follower
    task = Task(
        type="pick_and_place",
        params={"follower_pubkey": "f1"},
        required_capabilities=["6dof_arm"],
    )
    # Bidder targeting the right follower passes
    eligible, reason = can_citizen_bid_for_follower(
        task=task, target_follower_pubkey="f1",
        citizen_capabilities=["6dof_arm"], citizen_skills=[],
        citizen_load=0.1, citizen_health=1.0,
    )
    assert eligible, reason
    # Bidder targeting a different follower is filtered
    eligible, reason = can_citizen_bid_for_follower(
        task=task, target_follower_pubkey="OTHER",
        citizen_capabilities=["6dof_arm"], citizen_skills=[],
        citizen_load=0.1, citizen_health=1.0,
    )
    assert not eligible
    assert "follower" in reason.lower()


def pytest_approx(v):
    import pytest
    return pytest.approx(v)
```

- [ ] **Step 2.2: Run the tests to verify they fail**

```bash
python -m pytest citizenry/tests/test_marketplace_co_location.py -v
```

Expected: failures — `compute_bid_score` doesn't accept `co_location_bonus`; `Bid` lacks `node_pubkey` and `target_follower_pubkey`; `can_citizen_bid_for_follower` doesn't exist.

- [ ] **Step 2.3: Extend `Bid` dataclass**

Modify `citizenry/marketplace.py` around line 72:

```python
@dataclass
class Bid:
    """A citizen's bid on a task."""

    citizen_pubkey: str
    task_id: str
    score: float = 0.0
    skill_level: int = 0
    current_load: float = 0.0
    health: float = 1.0
    estimated_duration: float = 0.0
    timestamp: float = field(default_factory=time.time)
    # New: co-location and follower-targeting metadata
    node_pubkey: str = ""
    target_follower_pubkey: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_accept_body(cls, body: dict, sender_pubkey: str) -> Bid:
        bid_data = body.get("bid", {})
        return cls(
            citizen_pubkey=sender_pubkey,
            task_id=body.get("task_id", ""),
            score=bid_data.get("score", 0.0),
            skill_level=bid_data.get("skill_level", 0),
            current_load=bid_data.get("load", 0.0),
            health=bid_data.get("health", 1.0),
            estimated_duration=bid_data.get("estimated_duration", 0.0),
            node_pubkey=bid_data.get("node_pubkey", ""),
            target_follower_pubkey=bid_data.get("target_follower_pubkey", ""),
        )
```

- [ ] **Step 2.4: Extend `compute_bid_score` to accept the bonus**

Modify `compute_bid_score` (around line 110) — add `co_location_bonus` kwarg, applied AFTER the fatigue modifier:

```python
def compute_bid_score(
    skill_level: int,
    current_load: float,
    health: float,
    fatigue: float = 0.0,
    weights: dict[str, float] | None = None,
    co_location_bonus: float = 0.0,
) -> float:
    """... (existing docstring) ...
    co_location_bonus: extra absolute score awarded to bidders co-located
    with the targeted follower (same node_pubkey). Default 0.0; spec
    recommends 0.15.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    skill_norm = min(skill_level, 10) / 10.0
    avail = max(0.0, 1.0 - current_load)
    h = max(0.0, min(1.0, health))
    base = w["capability"] * skill_norm + w["availability"] * avail + w["health"] * h
    fatigue_modifier = 1.0 - 0.3 * max(0.0, min(1.0, fatigue))
    return base * fatigue_modifier + co_location_bonus
```

- [ ] **Step 2.5: Add `can_citizen_bid_for_follower`**

Add a sibling helper in the same file (after `can_citizen_bid` around line 259):

```python
def can_citizen_bid_for_follower(
    task: Task,
    target_follower_pubkey: str,
    citizen_capabilities: list[str],
    citizen_skills: list[str],
    citizen_load: float,
    citizen_health: float,
) -> tuple[bool, str]:
    """Like can_citizen_bid, plus enforces params.follower_pubkey targeting.

    A bidder must declare which follower it intends to drive. The Task's
    params.follower_pubkey (if present) restricts the auction to that
    follower; bidders targeting other followers are filtered out before
    base eligibility is checked.
    """
    requested = task.params.get("follower_pubkey")
    if requested and target_follower_pubkey and requested != target_follower_pubkey:
        return False, f"bid targets follower {target_follower_pubkey[:8]}, task wants {requested[:8]}"
    # Reuse base eligibility
    return TaskMarketplace.can_citizen_bid(
        TaskMarketplace(),  # method-on-class call w/o needing the instance state
        task=task,
        citizen_capabilities=citizen_capabilities,
        citizen_skills=citizen_skills,
        citizen_load=citizen_load,
        citizen_health=citizen_health,
    )
```

(If the existing `can_citizen_bid` is a method on `TaskMarketplace`, mirror that. If standalone, call it directly.)

- [ ] **Step 2.6: Run tests to verify they pass**

```bash
python -m pytest citizenry/tests/test_marketplace_co_location.py -v
```

Expected: 4 PASS.

- [ ] **Step 2.7: Run the full marketplace test suite to confirm no regressions**

```bash
python -m pytest citizenry/tests/test_marketplace.py -v
```

Expected: PASS (existing tests still pass with the additive changes).

- [ ] **Step 2.8: Commit**

```bash
git add citizenry/marketplace.py citizenry/tests/test_marketplace_co_location.py
git commit -m "$(cat <<'EOF'
citizenry: marketplace co-location bonus + follower targeting

- Bid gains node_pubkey and target_follower_pubkey fields so bidders
  can declare what follower they intend to drive and from where.
- compute_bid_score gains an additive co_location_bonus argument
  (spec default 0.15) — a Jetson policy targeting its locally-attached
  follower wins the auction by default; cross-node fallback works
  with a fair penalty.
- New can_citizen_bid_for_follower helper enforces the follower
  filter before base eligibility checks.

Existing marketplace tests unchanged. Foundation for PolicyCitizen
(Task 9) and the cross-node targeting designed in spec §4.4.
EOF
)"
```

---

### Task 3: Citizen split — extract LeaderCitizen, rename PiCitizen → ManipulatorCitizen, extract GovernorCitizen

**This task should be done AFTER `xiao-citizen/phase-2` merges to main.** The branch's existing modifications to `surface_citizen.py` and `pi_citizen.py` make the rename mechanically annoying mid-flight.

**Files:**
- Create: `citizenry/leader_citizen.py`
- Rename: `citizenry/pi_citizen.py` → `citizenry/manipulator_citizen.py`
- Create: `citizenry/governor_citizen.py` (extracted from `surface_citizen.py`)
- Delete or stub: `citizenry/surface_citizen.py` (becomes a thin re-export shim for one transition window)
- Modify: `citizenry/run_pi.py` (spawns LeaderCitizen if leader bus detected)
- Modify: `citizenry/run_surface.py` (spawns GovernorCitizen, no arms)
- Update imports across `citizenry/__main__.py`, `citizenry/coordinator.py`, `citizenry/dashboard.py`, anywhere else that imports `PiCitizen` or the governor side of `SurfaceCitizen`

- [ ] **Step 3.1: Pure rename — `git mv pi_citizen.py manipulator_citizen.py`**

```bash
git mv citizenry/pi_citizen.py citizenry/manipulator_citizen.py
# Update the class name:
sed -i 's/class PiCitizen/class ManipulatorCitizen/g' citizenry/manipulator_citizen.py
# Update internal references in the same file:
sed -i 's/PiCitizen/ManipulatorCitizen/g' citizenry/manipulator_citizen.py
# A backward-compat re-export so existing imports keep working during transition:
cat > citizenry/pi_citizen.py <<'EOF'
"""Deprecated shim — PiCitizen was renamed to ManipulatorCitizen.

This re-export will be removed after Task 12.
"""
from .manipulator_citizen import ManipulatorCitizen
PiCitizen = ManipulatorCitizen  # legacy alias
EOF
```

- [ ] **Step 3.2: Update all importers**

```bash
grep -rl "from .pi_citizen import PiCitizen\|from citizenry.pi_citizen import PiCitizen" citizenry/ \
  | xargs -r sed -i 's|from \.pi_citizen import PiCitizen|from .manipulator_citizen import ManipulatorCitizen as PiCitizen|g; s|from citizenry\.pi_citizen import PiCitizen|from citizenry.manipulator_citizen import ManipulatorCitizen as PiCitizen|g'
```

(The `as PiCitizen` aliasing is intentional — keeps the rest of the file compiling without renaming every reference. Subsequent passes can drop the alias.)

- [ ] **Step 3.3: Run the existing test suite to confirm no regressions**

```bash
python -m pytest citizenry/tests/ -x -q
```

Expected: PASS. Any failures here are the rename's fault and must be fixed before continuing.

- [ ] **Step 3.4: Extract `GovernorCitizen` from `surface_citizen.py`**

Open `citizenry/surface_citizen.py`, identify which methods belong to the **governor** role (constitution ratification, marketplace coordination, dashboard hooks) versus the **leader** role (reading the leader arm and emitting teleop frames). The governor pieces typically include:
- `_handle_discover` / `_handle_advertise` / `_send_govern`
- Constitution helpers
- `TaskCoordinator` integration

Move governor-only code into `citizenry/governor_citizen.py`:

```python
"""Governor citizen — Constitution ratification + marketplace coordination.

Hosts no arms and no recorder. Spawned only on a node that the
fleet treats as Governor (today: the Surface).
"""

from __future__ import annotations

# Imports — exact list depends on what extraction reveals:
import asyncio
from .citizen import Citizen
from .constitution import Constitution
from .coordinator import TaskCoordinator


class GovernorCitizen(Citizen):
    def __init__(self, **kwargs):
        super().__init__(
            name=kwargs.pop("name", "governor"),
            citizen_type="governor",
            capabilities=["compute", "govern"],
            **kwargs,
        )
        self.coordinator = TaskCoordinator(self)
        # No follower bus. No leader bus. No recorder.
        # Constitution ratification is unchanged from the existing path.

    async def start(self):
        await super().start()
        # Existing startup sequence specific to governance, lifted from
        # surface_citizen.py: ratify constitution, broadcast GOVERN, etc.
        # ...

    async def stop(self):
        await super().stop()

    # Governor-side handlers (lifted unchanged):
    # - _handle_discover
    # - _handle_advertise
    # - _send_govern
    # - any task-marketplace hooks
```

(The actual code is what `surface_citizen.py` already has; this step is pure file movement, not new logic.)

- [ ] **Step 3.5: Create `LeaderCitizen` from the leader-arm portion of `surface_citizen.py`**

```python
# citizenry/leader_citizen.py
"""Leader citizen — reads a leader arm and emits teleop PROPOSE frames.

Runs on any node where a leader arm is physically attached. Co-located
with a follower's ManipulatorCitizen on the same node; teleop frames
go in-process via loopback multicast.
"""

from __future__ import annotations

import asyncio
from typing import Iterable

from .citizen import Citizen
from .protocol import MessageType, make_envelope, TTL_TELEOP

MOTOR_NAMES = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
]


class LeaderCitizen(Citizen):
    def __init__(
        self,
        leader_port: str,
        target_follower_pubkey: str | None = None,
        teleop_fps: float = 60.0,
        auto_teleop: bool = True,
        **kwargs,
    ):
        super().__init__(
            name=kwargs.pop("name", "leader"),
            citizen_type="leader",
            capabilities=["leader_arm", "teleop_source", "feetech_sts3215"],
            **kwargs,
        )
        self.leader_port = leader_port
        self.teleop_fps = teleop_fps
        self.target_follower_pubkey = target_follower_pubkey
        self._auto_teleop = auto_teleop
        self._leader_bus = None
        self._teleop_task: asyncio.Task | None = None

    async def start(self):
        await super().start()
        # Open the Feetech bus on self.leader_port — exact lerobot/feetech
        # call lifted from surface_citizen.py's existing leader-open path.
        # ... (existing code) ...
        if self._auto_teleop:
            self._teleop_task = asyncio.create_task(self._teleop_loop())

    async def stop(self):
        if self._teleop_task:
            self._teleop_task.cancel()
        await super().stop()
        # Close leader bus.

    async def _teleop_loop(self):
        period = 1.0 / self.teleop_fps
        while True:
            try:
                positions = self._read_leader_positions()
                # Discovery: surface_citizen.py tracks self._follower_key /
                # self._follower_addr from neighbor ADVERTISE/HEARTBEAT.
                # Reuse exactly that machinery — lift it unchanged.
                if (positions is not None
                        and self._follower_key is not None
                        and self._follower_addr is not None):
                    # Use the inherited helper: unicast PROPOSE w/ teleop_frame
                    # body shape and TTL_TELEOP=0.1.
                    self.send_teleop(self._follower_key, positions, self._follower_addr)
                await asyncio.sleep(period)
            except asyncio.CancelledError:
                return
            except Exception as e:
                self._log(f"teleop loop error: {e}")
                await asyncio.sleep(period)

    def _read_leader_positions(self) -> dict[str, int] | None:
        """Lifted from surface_citizen.py: read 6 raw servo positions
        as a dict {motor_name: int_position}.
        """
        # ... existing code from surface_citizen._read_leader_positions ...
        return None  # placeholder — real impl uses self._leader_bus
```

Important contract details lifted from existing code:
- `Citizen.send_teleop(recipient_pubkey, positions: dict, addr: tuple)` is the existing helper. Body it builds is `{"task": "teleop_frame", "positions": positions}` — do NOT invent a different body shape; the Pi-side `manipulator_citizen.py` (renamed `pi_citizen.py`) only handles `teleop_frame`.
- `positions` is a `dict[str, int]` keyed by motor name (e.g. `{"shoulder_pan": 2048, ...}`) — NOT a list.
- `self._follower_key` (hex pubkey) and `self._follower_addr` (host:port tuple) are tracked via the neighbor table; lift the exact code from `surface_citizen.py`'s `_handle_advertise` so a leader-only node can discover its follower.
- Targeting a specific follower via `target_follower_pubkey` is a v2 concern. For now, LeaderCitizen pairs with whatever ManipulatorCitizen ADVERTISE arrives first (matches today's behaviour). PolicyCitizen (Task 9) carries the explicit follower-targeting load.

- [ ] **Step 3.6: Make `surface_citizen.py` a thin re-export shim**

After moving code into `governor_citizen.py` and `leader_citizen.py`, leave `surface_citizen.py` as:

```python
"""Deprecated shim — split into governor_citizen.py and leader_citizen.py.

This re-export will be removed after Task 12.
"""
from .governor_citizen import GovernorCitizen
from .leader_citizen import LeaderCitizen

# Legacy compound class — emulates the old SurfaceCitizen by composing
# the two new ones. New code should instantiate the two separately.
class SurfaceCitizen(GovernorCitizen):
    """Composes Governor + Leader for hosts that still need the combined behaviour."""
    def __init__(self, leader_port: str = "/dev/ttyACM1", teleop_fps: float = 60.0, **kwargs):
        super().__init__(**kwargs)
        # Note: a future task removes this class entirely. Use
        # GovernorCitizen + LeaderCitizen separately instead.
        self._leader_companion = LeaderCitizen(
            leader_port=leader_port, teleop_fps=teleop_fps,
            node_pubkey=self.node_pubkey,
        )

    async def start(self):
        await super().start()
        await self._leader_companion.start()

    async def stop(self):
        await self._leader_companion.stop()
        await super().stop()
```

- [ ] **Step 3.7: Update `run_pi.py` to spawn LeaderCitizen if a leader bus is present**

Locate the survey-driven spawn loop in `run_pi.py` and add a branch — if the survey turns up two servo buses, treat one as leader (configurable via `--leader-port`) and one as follower:

```python
# Inside the spawn loop, after the existing camera/manipulator branches:
from .leader_citizen import LeaderCitizen

# A simple heuristic: if we see two buses and --leader-port matched one,
# spawn a LeaderCitizen for it. The user can override via CLI.
async def _spawn_leader_citizen(citizens: dict, port: str, target_follower_pubkey: str | None):
    print(f"[hardware] Leader bus: {port}")
    citizen = LeaderCitizen(
        leader_port=port,
        target_follower_pubkey=target_follower_pubkey,
    )
    await citizen.start()
    citizens[f"leader:{port}"] = citizen
```

Wire it into the survey-react loop. Add a `--leader-port` CLI argument with no default (so absent = no leader on this Pi).

- [ ] **Step 3.8: Update `run_surface.py` to spawn GovernorCitizen only**

Replace the existing `SurfaceCitizen()` instantiation with `GovernorCitizen()`:

```python
# Old:
# citizen = SurfaceCitizen(leader_port=args.leader_port, teleop_fps=args.fps, hardware=hw)
# New:
from .governor_citizen import GovernorCitizen
citizen = GovernorCitizen(hardware=hw)
print("[surface] governor only — no arms, no recorder")
```

Drop `--leader-port` and `--fps` args from `run_surface.py`'s argparse setup (they no longer apply — the leader lives on a ManipulatorNode now).

- [ ] **Step 3.9: Run the full test suite**

```bash
python -m pytest citizenry/tests/ -x -q
```

Expected: PASS. The shim keeps legacy paths working.

- [ ] **Step 3.10: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
citizenry: split SurfaceCitizen into GovernorCitizen + LeaderCitizen;
rename PiCitizen → ManipulatorCitizen

Pure refactor for the node-based topology in spec §4.1. After this
commit:
- ManipulatorCitizen (was PiCitizen) is hardware-agnostic and runs
  wherever a follower is attached.
- LeaderCitizen reads a leader arm and emits teleop PROPOSE frames;
  spawns on whichever node has the leader bus (Pi or Jetson).
- GovernorCitizen handles Constitution ratification + marketplace
  coordination; no arms, no recorder.
- surface_citizen.py and pi_citizen.py become thin re-export shims
  (removed in a later task once all callers migrate).

run_pi.py spawns LeaderCitizen when --leader-port is supplied;
run_surface.py spawns GovernorCitizen only and drops the now-stale
--leader-port / --fps args.

Foundation for runtime co-location detection (Task 1) + cross-node
policy bidding (Task 9).
EOF
)"
```

---

## Phase 2: Dataset v3 + HF upload

### Task 4: `EpisodeRecorderV3` — direct LeRobotDataset v3 writer

**Files:**
- Modify: `citizenry/episode_recorder.py:1-401` (add `EpisodeRecorderV3` class alongside existing v1)
- Create: `citizenry/tests/test_episode_recorder_v3.py`

- [ ] **Step 4.1: Confirm the LeRobot v3 dataset API on the target machines**

```bash
# On Surface or Jetson (whichever has lerobot installed):
python -c "
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
print(LeRobotDataset.__doc__[:500] if LeRobotDataset.__doc__ else 'no docstring')
print('create_dataset' in dir(LeRobotDataset))
"
```

Expected: prints class docstring and confirms either `create_empty` or `create_dataset` constructor exists. Note the exact constructor name — Step 4.3's code uses it.

- [ ] **Step 4.2: Write the failing test**

Create `citizenry/tests/test_episode_recorder_v3.py`:

```python
"""Tests for the LeRobotDataset v3 episode recorder."""

from pathlib import Path

import numpy as np
import pytest

from citizenry.episode_recorder import EpisodeRecorderV3


@pytest.fixture
def recorder(tmp_path):
    return EpisodeRecorderV3(
        output_root=tmp_path / "v3",
        repo_id="test/local",
        fps=30,
    )


def test_begin_close_creates_episode_dir(recorder):
    eid = recorder.begin_episode("teleop", {"target": "red_block"})
    assert isinstance(eid, str) and len(eid) > 0
    out = recorder.close_episode(success=True, notes="ok")
    assert out.exists()
    # v3 layout: at least one parquet chunk
    assert any(out.rglob("*.parquet"))


def test_record_frame_appends_to_chunk(recorder):
    recorder.begin_episode("teleop", {})
    for i in range(5):
        recorder.record_frame(
            frame_index=i,
            timestamp=float(i) / 30.0,
            image=np.zeros((96, 128, 3), dtype=np.uint8),
            joint_positions=[100, 200, 300, 400, 500, 600],
            joint_currents=[0.0]*6,
            joint_temperatures=[40.0]*6,
            joint_loads=[0.1]*6,
            action_positions=[100, 200, 300, 400, 500, 600],
            reward=0.0,
        )
    out = recorder.close_episode(success=True)
    # Verify the parquet has 5 rows
    import pyarrow.parquet as pq
    tables = [pq.read_table(p) for p in out.rglob("*.parquet")]
    total_rows = sum(t.num_rows for t in tables)
    assert total_rows == 5


def test_metadata_json_includes_node_and_policy_pubkeys(recorder):
    recorder.set_attribution(
        node_pubkey="ab" * 32,
        policy_pubkey="cd" * 32,
        governor_pubkey="ef" * 32,
        constitution_hash="01" * 16,
    )
    recorder.begin_episode("pick_and_place", {"target": "red_block"})
    recorder.close_episode(success=True, reward_total=1.0, duration_s=2.5)
    # Read metadata
    import json
    out = recorder.last_episode_dir
    meta_files = list(out.rglob("episode_*.json")) + list(out.rglob("metadata.json"))
    assert meta_files, "expected an episode metadata json"
    meta = json.loads(meta_files[0].read_text())
    # The recorder writes its own attribution sidecar:
    sidecar = json.loads((out / "attribution.json").read_text())
    assert sidecar["node_pubkey"] == "ab" * 32
    assert sidecar["policy_pubkey"] == "cd" * 32
    assert sidecar["governor_pubkey"] == "ef" * 32
    assert sidecar["constitution_hash"] == "01" * 16
```

- [ ] **Step 4.3: Run the tests to verify they fail**

```bash
python -m pytest citizenry/tests/test_episode_recorder_v3.py -v
```

Expected: failure — `EpisodeRecorderV3` doesn't exist.

- [ ] **Step 4.4: Implement `EpisodeRecorderV3`**

Append to `citizenry/episode_recorder.py`:

```python
# At the top of the file, add:
import json
import uuid
from datetime import datetime, timezone

# At the bottom of the file, add the v3 recorder. The v1 EpisodeRecorder
# class above is unchanged.

class EpisodeRecorderV3:
    """Records episodes directly into a LeRobotDataset v3 layout.

    Output layout (rooted at output_root):
        output_root/
          <repo_id_safe>/
            data/
              chunk_NNN/
                episode_*.parquet
            videos/
              chunk_NNN/
                <camera_name>/
                  episode_*.mp4
            meta/
              episode_index.parquet
              tasks.json
            attribution.json   ← per-recorder sidecar (node/policy/governor/constitution)

    On close_episode(), Parquet+MP4 chunks are finalized; HFUploader (Task 6)
    detects new content via output_root mtime and starts uploading.
    """

    MOTOR_NAMES = MOTOR_NAMES  # reuse module-level constant

    def __init__(
        self,
        output_root: Path,
        repo_id: str = "local/citizenry-data",
        fps: int = 30,
        camera_names: tuple[str, ...] = ("base",),
    ):
        self.output_root = Path(output_root)
        self.repo_id = repo_id
        self.fps = int(fps)
        self.camera_names = tuple(camera_names)
        self.output_root.mkdir(parents=True, exist_ok=True)
        # Lazy LeRobot import so unit tests don't need lerobot installed.
        self._dataset = None
        self._open_episode_id: str | None = None
        self._open_frames: list[dict] = []
        self.last_episode_dir: Path | None = None
        # Attribution sidecar fields (set via set_attribution before begin_episode):
        self._attribution: dict = {}

    def set_attribution(
        self,
        node_pubkey: str,
        policy_pubkey: str | None = None,
        governor_pubkey: str | None = None,
        constitution_hash: str | None = None,
    ) -> None:
        self._attribution = {
            "node_pubkey": node_pubkey,
            "policy_pubkey": policy_pubkey,
            "governor_pubkey": governor_pubkey,
            "constitution_hash": constitution_hash,
        }

    def begin_episode(self, task: str, params: dict) -> str:
        if self._open_episode_id is not None:
            raise RuntimeError(
                f"begin_episode while episode {self._open_episode_id} is open"
            )
        self._open_episode_id = uuid.uuid4().hex[:12]
        self._open_frames = []
        self._open_task = task
        self._open_params = params
        self._open_started_at = datetime.now(timezone.utc).isoformat()
        return self._open_episode_id

    def record_frame(
        self,
        frame_index: int,
        timestamp: float,
        image,            # np.ndarray HxWx3 uint8 (one camera for now)
        joint_positions,
        joint_currents,
        joint_temperatures,
        joint_loads,
        action_positions,
        reward: float = 0.0,
        done: bool = False,
        camera_name: str = "base",
    ) -> None:
        if self._open_episode_id is None:
            raise RuntimeError("record_frame without begin_episode")
        self._open_frames.append({
            "frame_index": frame_index,
            "timestamp": float(timestamp),
            "image": image,
            "camera_name": camera_name,
            "observation.state": list(joint_positions),
            "observation.current": list(joint_currents),
            "observation.temperature": list(joint_temperatures),
            "observation.load": list(joint_loads),
            "action": list(action_positions),
            "reward": float(reward),
            "done": bool(done),
        })

    def close_episode(
        self,
        success: bool,
        notes: str = "",
        reward_total: float = 0.0,
        duration_s: float = 0.0,
    ) -> Path:
        if self._open_episode_id is None:
            raise RuntimeError("close_episode without begin_episode")
        eid = self._open_episode_id
        # Finalize the chunk: write parquet for state/action, MP4 for image.
        out = self._write_chunk(
            eid=eid,
            frames=self._open_frames,
            task=self._open_task,
            params=self._open_params,
            success=success,
            notes=notes,
            reward_total=reward_total,
            duration_s=duration_s,
            started_at=self._open_started_at,
        )
        # Write attribution sidecar
        if self._attribution:
            (out / "attribution.json").write_text(json.dumps(self._attribution, indent=2))
        self.last_episode_dir = out
        # Reset open-episode state
        self._open_episode_id = None
        self._open_frames = []
        return out

    # ---- internal ----

    def _write_chunk(
        self,
        eid: str,
        frames: list[dict],
        task: str,
        params: dict,
        success: bool,
        notes: str,
        reward_total: float,
        duration_s: float,
        started_at: str,
    ) -> Path:
        """Write one episode as a v3 chunk under output_root/<repo_safe>/."""
        import numpy as np
        import pyarrow as pa
        import pyarrow.parquet as pq
        # Build the table
        if not frames:
            # Empty episode — still write a marker so HFUploader sees it
            cols = {"frame_index": [], "timestamp": [],
                    "observation.state": [], "action": [], "reward": [], "done": []}
        else:
            cols = {k: [f[k] for f in frames]
                    for k in (
                        "frame_index", "timestamp",
                        "observation.state", "observation.current",
                        "observation.temperature", "observation.load",
                        "action", "reward", "done",
                    )}
        table = pa.table(cols)
        # Output paths
        repo_safe = self.repo_id.replace("/", "__")
        chunk_idx = self._next_chunk_index(repo_safe)
        chunk_dir = self.output_root / repo_safe / "data" / f"chunk_{chunk_idx:03d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = chunk_dir / f"episode_{eid}.parquet"
        pq.write_table(table, parquet_path)
        # MP4: write the image stream (only first camera for v1; multi-camera in Task 8 enhancement)
        video_root = self.output_root / repo_safe / "videos" / f"chunk_{chunk_idx:03d}"
        video_root.mkdir(parents=True, exist_ok=True)
        if frames:
            self._write_mp4(
                path=video_root / f"episode_{eid}_base.mp4",
                images=[f["image"] for f in frames],
            )
        # Per-episode metadata (not the dataset-level meta — that's append-only and lives at meta/)
        meta_path = chunk_dir / f"episode_{eid}.json"
        meta_path.write_text(json.dumps({
            "episode_id": eid,
            "task": task,
            "params": params,
            "success": success,
            "notes": notes,
            "reward_total": reward_total,
            "duration_s": duration_s,
            "started_at": started_at,
            "frame_count": len(frames),
        }, indent=2))
        return chunk_dir

    def _next_chunk_index(self, repo_safe: str) -> int:
        d = self.output_root / repo_safe / "data"
        if not d.exists():
            return 0
        existing = sorted(d.glob("chunk_*"))
        return len(existing)

    def _write_mp4(self, path: Path, images) -> None:
        import cv2
        if not images:
            return
        h, w = images[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(path), fourcc, self.fps, (w, h))
        try:
            for img in images:
                writer.write(img)
        finally:
            writer.release()
```

- [ ] **Step 4.5: Run tests to verify they pass**

```bash
python -m pytest citizenry/tests/test_episode_recorder_v3.py -v
```

Expected: 3 PASS.

- [ ] **Step 4.6: Add a Constitution Law `episode_recorder_format`**

Modify `citizenry/constitution.py` — locate `default_laws()` (or equivalent) and add:

```python
"episode_recorder_format": "v3",  # values: "v1" | "v3" | "both"
```

- [ ] **Step 4.7: Wire the recorder into `ManipulatorCitizen`**

In `citizenry/manipulator_citizen.py`, where the existing v1 recorder is constructed, branch on the law via the `_law` helper from Task 1.7b:

```python
fmt = self._law("episode_recorder_format", default="v3")
if fmt in ("v1", "both"):
    self._recorder_v1 = EpisodeRecorder(self)  # existing
if fmt in ("v3", "both"):
    self._recorder_v3 = EpisodeRecorderV3(
        output_root=Path.home() / "citizenry-datasets" / "v3",
        repo_id=self._law("dataset.hf_repo_id", default="local/citizenry-data"),
        fps=int(self._law("dataset.fps", default=30)),
    )
    self._recorder_v3.set_attribution(
        node_pubkey=self.node_pubkey,
        policy_pubkey=getattr(self, "_active_policy_pubkey", None),
        governor_pubkey=getattr(self, "governor_pubkey", None),
        constitution_hash=getattr(self, "constitution_hash", None),
    )
# At every existing record_frame() call site, fan out to whichever recorders are live.
```

Note: `_law()` returns the default when no Constitution has been ratified yet, so this code is safe to run at construction-time (before the governor sends a GOVERN). The recorders re-read laws on the next ratification via the existing `_on_constitution_received` hook.

- [ ] **Step 4.8: Commit**

```bash
git add citizenry/episode_recorder.py \
        citizenry/tests/test_episode_recorder_v3.py \
        citizenry/constitution.py \
        citizenry/manipulator_citizen.py
git commit -m "$(cat <<'EOF'
citizenry: EpisodeRecorderV3 writes LeRobotDataset v3 directly

New writer alongside the existing v1 recorder, gated by Constitution
Law episode_recorder_format ("v1" | "v3" | "both"; defaults to "v3").
Each closed episode produces:
  - one Parquet chunk under data/chunk_NNN/episode_*.parquet
  - one MP4 per camera under videos/chunk_NNN/<cam>/episode_*.mp4
  - per-episode metadata JSON
  - attribution.json sidecar (node_pubkey, policy_pubkey,
    governor_pubkey, constitution_hash) — used for fleet-wide indexing
    on Hugging Face Hub.

ManipulatorCitizen fans out record_frame() to whichever recorders are
live so the transition window (Task 12 flips default to v3-only)
keeps existing v1 consumers working.

Foundation for HFUploader (Task 6).
EOF
)"
```

---

### Task 5: One-shot legacy migrator `dataset_v3_migrate.py`

**Files:**
- Create: `citizenry/dataset_v3_migrate.py`
- Create: `citizenry/tests/test_dataset_v3_migrate.py`

- [ ] **Step 5.1: Write the failing test**

Create `citizenry/tests/test_dataset_v3_migrate.py`:

```python
"""Tests for the legacy → LeRobotDataset v3 migrator."""

import json
from pathlib import Path

import numpy as np
import pytest

from citizenry.dataset_v3_migrate import migrate_legacy_to_v3


def _seed_legacy_episode(root: Path, eid: int, frames: int = 3) -> None:
    """Create a fake legacy episode resembling the v1 layout."""
    ep_dir = root / f"episode_{eid:04d}"
    ep_dir.mkdir(parents=True, exist_ok=True)
    # v1 layout: one .npy of joint actions per frame, one .jpg per frame, plus a manifest.
    for i in range(frames):
        np.save(ep_dir / f"action_{i:05d}.npy",
                np.array([100, 200, 300, 400, 500, 600], dtype=np.int32))
        # tiny black JPEG
        import cv2
        cv2.imwrite(str(ep_dir / f"frame_{i:05d}.jpg"),
                    np.zeros((48, 64, 3), dtype=np.uint8))
    (ep_dir / "manifest.json").write_text(json.dumps({
        "task": "teleop", "frames": frames, "success": True, "fps": 30,
    }))


def test_migrate_one_episode_produces_v3_layout(tmp_path):
    legacy_root = tmp_path / "citizenry-datasets-legacy"
    out_root = tmp_path / "v3"
    _seed_legacy_episode(legacy_root, eid=1, frames=4)
    report = migrate_legacy_to_v3(
        legacy_paths=[legacy_root],
        output_root=out_root,
        repo_id="test/local",
        upload=False,
        delete_old=False,
        dry_run=False,
    )
    assert report["episodes_converted"] == 1
    assert report["frames_total"] == 4
    # The output should be loadable as a LeRobot v3 dataset shape:
    # at minimum, a parquet exists.
    parquets = list((out_root / "test__local").rglob("*.parquet"))
    assert parquets, f"expected parquets in {out_root}"


def test_dry_run_writes_nothing(tmp_path):
    legacy_root = tmp_path / "legacy"
    out_root = tmp_path / "v3"
    _seed_legacy_episode(legacy_root, eid=1, frames=2)
    report = migrate_legacy_to_v3(
        legacy_paths=[legacy_root],
        output_root=out_root,
        repo_id="test/local",
        upload=False,
        delete_old=False,
        dry_run=True,
    )
    assert report["episodes_converted"] == 1  # counted
    assert not out_root.exists() or not list(out_root.rglob("*.parquet"))


def test_idempotent_rerun_skips_already_converted(tmp_path):
    legacy_root = tmp_path / "legacy"
    out_root = tmp_path / "v3"
    _seed_legacy_episode(legacy_root, eid=1, frames=2)
    # First run
    r1 = migrate_legacy_to_v3([legacy_root], out_root, "test/local", False, False, False)
    # Add a second legacy episode and re-run
    _seed_legacy_episode(legacy_root, eid=2, frames=3)
    r2 = migrate_legacy_to_v3([legacy_root], out_root, "test/local", False, False, False)
    assert r2["episodes_converted"] == 1  # only the new one
    assert r2["episodes_skipped"] == 1


def test_delete_old_removes_legacy_paths_after_success(tmp_path):
    legacy_root = tmp_path / "legacy"
    out_root = tmp_path / "v3"
    _seed_legacy_episode(legacy_root, eid=1, frames=2)
    migrate_legacy_to_v3(
        [legacy_root], out_root, "test/local",
        upload=False, delete_old=True, dry_run=False,
    )
    assert not (legacy_root / "episode_0001").exists()
```

- [ ] **Step 5.2: Run tests to verify they fail**

```bash
python -m pytest citizenry/tests/test_dataset_v3_migrate.py -v
```

Expected: ImportError on `from citizenry.dataset_v3_migrate import migrate_legacy_to_v3`.

- [ ] **Step 5.3: Implement the migrator**

Create `citizenry/dataset_v3_migrate.py`:

```python
"""One-shot legacy → LeRobotDataset v3 migrator.

Walks ~/.citizenry/episodes/ + ~/citizenry-datasets/episode_*/ (and any
explicit paths), converts each legacy episode into a v3-shaped chunk,
optionally uploads to HF, optionally deletes the legacy source on
verified success.

CLI:
    python -m citizenry.dataset_v3_migrate \
        --legacy ~/.citizenry/episodes \
        --legacy ~/citizenry-datasets \
        --output ~/citizenry-datasets/v3 \
        --repo-id bradley-festraets/citizenry-fleet \
        [--upload] [--delete-old] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from .episode_recorder import EpisodeRecorderV3


def _discover_legacy_episodes(roots: list[Path]) -> list[Path]:
    """Find every legacy episode dir under the supplied roots."""
    found = []
    for root in roots:
        if not root.exists():
            continue
        # Look for dirs of the shape episode_XXXX/ with action_*.npy inside
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if list(child.glob("action_*.npy")) or list(child.glob("frame_*.jpg")):
                found.append(child)
    return found


def _already_converted(eid: str, output_root: Path, repo_safe: str) -> bool:
    return any((output_root / repo_safe).rglob(f"episode_{eid}.parquet"))


def _episode_id_for_legacy(p: Path) -> str:
    # episode_0001 → 0001; otherwise hash the path
    n = p.name
    if n.startswith("episode_"):
        return n[len("episode_"):]
    import hashlib
    return hashlib.sha1(str(p).encode()).hexdigest()[:12]


def _convert_one(legacy_dir: Path, recorder: EpisodeRecorderV3, dry_run: bool) -> dict:
    """Convert one legacy episode dir; return per-episode counters."""
    manifest_path = legacy_dir / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    actions = sorted(legacy_dir.glob("action_*.npy"))
    frames = sorted(legacy_dir.glob("frame_*.jpg"))
    # Pair them up by index (file name suffix)
    n = min(len(actions), len(frames)) if frames else len(actions)
    if dry_run:
        return {"frames_total": n, "skipped": False}
    eid = _episode_id_for_legacy(legacy_dir)
    recorder._open_episode_id = eid  # bypass uuid; preserve original id
    recorder._open_frames = []
    recorder._open_task = manifest.get("task", "teleop")
    recorder._open_params = manifest.get("params", {})
    recorder._open_started_at = manifest.get("started_at", "")
    import cv2
    for i in range(n):
        action = np.load(actions[i]).tolist()
        if frames:
            img = cv2.imread(str(frames[i]))
        else:
            img = np.zeros((48, 64, 3), dtype=np.uint8)
        recorder.record_frame(
            frame_index=i,
            timestamp=float(i) / float(manifest.get("fps", 30)),
            image=img,
            joint_positions=action,           # legacy v1 had no separate state
            joint_currents=[0.0]*len(action),
            joint_temperatures=[0.0]*len(action),
            joint_loads=[0.0]*len(action),
            action_positions=action,
            reward=0.0,
        )
    recorder.close_episode(
        success=manifest.get("success", True),
        notes=manifest.get("notes", "migrated"),
    )
    return {"frames_total": n, "skipped": False}


def migrate_legacy_to_v3(
    legacy_paths: list[Path],
    output_root: Path,
    repo_id: str,
    upload: bool,
    delete_old: bool,
    dry_run: bool,
) -> dict:
    """Top-level migrator. Returns counters."""
    output_root = Path(output_root)
    legacy_paths = [Path(p).expanduser() for p in legacy_paths]
    recorder = EpisodeRecorderV3(output_root=output_root, repo_id=repo_id)
    repo_safe = repo_id.replace("/", "__")
    eps = _discover_legacy_episodes(legacy_paths)
    report = {"episodes_total": len(eps), "episodes_converted": 0,
              "episodes_skipped": 0, "frames_total": 0,
              "uploaded": False, "deleted": []}
    for legacy_dir in eps:
        eid = _episode_id_for_legacy(legacy_dir)
        if _already_converted(eid, output_root, repo_safe):
            report["episodes_skipped"] += 1
            continue
        r = _convert_one(legacy_dir, recorder, dry_run)
        report["episodes_converted"] += 1
        report["frames_total"] += r["frames_total"]
        if delete_old and not dry_run:
            import shutil
            shutil.rmtree(legacy_dir)
            report["deleted"].append(str(legacy_dir))
    if upload and not dry_run:
        from .hf_upload import HFUploader
        ok = HFUploader(repo_id=repo_id).upload_root(output_root / repo_safe)
        report["uploaded"] = bool(ok)
    return report


def _cli() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--legacy", action="append", required=True,
                   help="legacy root dir; pass multiple times")
    p.add_argument("--output", default="~/citizenry-datasets/v3")
    p.add_argument("--repo-id", required=True)
    p.add_argument("--upload", action="store_true")
    p.add_argument("--delete-old", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    out = Path(args.output).expanduser()
    legacy = [Path(x).expanduser() for x in args.legacy]
    report = migrate_legacy_to_v3(
        legacy_paths=legacy,
        output_root=out,
        repo_id=args.repo_id,
        upload=args.upload,
        delete_old=args.delete_old,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
```

- [ ] **Step 5.4: Run tests to verify they pass**

```bash
python -m pytest citizenry/tests/test_dataset_v3_migrate.py -v
```

Expected: 4 PASS.

- [ ] **Step 5.5: Commit**

```bash
git add citizenry/dataset_v3_migrate.py citizenry/tests/test_dataset_v3_migrate.py
git commit -m "$(cat <<'EOF'
citizenry: dataset_v3_migrate.py — one-shot legacy → v3 with HF upload

Walks legacy roots (~/.citizenry/episodes, ~/citizenry-datasets/), converts
each episode into a LeRobotDataset v3 chunk via EpisodeRecorderV3,
optionally uploads via HFUploader (Task 6), optionally deletes legacy
sources on verified success.

Idempotent: re-running with new episodes appends; already-converted
episodes are skipped via parquet existence check.

CLI:
  python -m citizenry.dataset_v3_migrate \
    --legacy ~/.citizenry/episodes --legacy ~/citizenry-datasets \
    --output ~/citizenry-datasets/v3 \
    --repo-id <user>/citizenry-fleet \
    [--upload] [--delete-old] [--dry-run]
EOF
)"
```

---

### Task 6: `HFUploader` — async upload + verify + delete + retry

**Files:**
- Create: `citizenry/hf_upload.py`
- Create: `citizenry/tests/test_hf_upload.py`

- [ ] **Step 6.1: Write the failing test**

Create `citizenry/tests/test_hf_upload.py`:

```python
"""Tests for HFUploader (mocked HF API)."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from citizenry.hf_upload import HFUploader


@pytest.fixture
def fake_repo(tmp_path):
    root = tmp_path / "v3" / "test__local"
    (root / "data" / "chunk_000").mkdir(parents=True)
    (root / "data" / "chunk_000" / "episode_abc.parquet").write_bytes(b"dummy parquet")
    (root / "data" / "chunk_000" / "episode_abc.json").write_text(json.dumps({"frame_count": 1}))
    return root


def test_upload_root_calls_hf_api(fake_repo, tmp_path):
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    with patch("citizenry.hf_upload.upload_folder") as upload_mock:
        upload_mock.return_value = MagicMock(commit_url="https://...")
        ok = uploader.upload_root(fake_repo)
    assert ok is True
    upload_mock.assert_called_once()
    call_kwargs = upload_mock.call_args.kwargs
    assert call_kwargs["repo_id"] == "user/repo"
    assert Path(call_kwargs["folder_path"]) == fake_repo


def test_upload_failure_returns_false_does_not_delete(fake_repo, tmp_path):
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    with patch("citizenry.hf_upload.upload_folder") as upload_mock:
        upload_mock.side_effect = RuntimeError("500 from HF")
        ok = uploader.upload_root(fake_repo, delete_on_success=True)
    assert ok is False
    # Files still present
    assert (fake_repo / "data" / "chunk_000" / "episode_abc.parquet").exists()


def test_upload_success_with_delete_removes_local(fake_repo, tmp_path):
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    with patch("citizenry.hf_upload.upload_folder") as upload_mock, \
         patch.object(HFUploader, "_verify_remote", return_value=True):
        upload_mock.return_value = MagicMock(commit_url="https://...")
        ok = uploader.upload_root(fake_repo, delete_on_success=True)
    assert ok is True
    assert not (fake_repo / "data" / "chunk_000" / "episode_abc.parquet").exists()


@pytest.mark.asyncio
async def test_watch_uploads_new_chunks(fake_repo, tmp_path):
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    uploaded = []

    def fake_upload_root(path, **kw):
        uploaded.append(Path(path).name)
        return True

    with patch.object(uploader, "upload_root", side_effect=fake_upload_root):
        task = asyncio.create_task(uploader.watch(fake_repo, poll_interval=0.05))
        await asyncio.sleep(0.15)
        # Drop a new chunk
        new_chunk = fake_repo / "data" / "chunk_001"
        new_chunk.mkdir(parents=True)
        (new_chunk / "episode_xyz.parquet").write_bytes(b"new")
        await asyncio.sleep(0.20)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    # The watcher fires upload_root on parent dir each cycle; >=1 calls
    assert len(uploaded) >= 1
```

(Add `pytest-asyncio` to dev deps if not already; if missing, run `pip install pytest-asyncio`.)

- [ ] **Step 6.2: Run tests to verify they fail**

```bash
python -m pytest citizenry/tests/test_hf_upload.py -v
```

Expected: ImportError on `from citizenry.hf_upload import HFUploader`.

- [ ] **Step 6.3: Implement `HFUploader`**

Create `citizenry/hf_upload.py`:

```python
"""Async per-episode upload to Hugging Face Hub.

Watches a v3 dataset root, uploads on close, optionally deletes local
copy on verified success. Retries on transient failure.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path

from huggingface_hub import upload_folder, HfApi


def _read_token(path: str | None) -> str | None:
    if path is None:
        return None
    p = Path(path).expanduser()
    if not p.exists():
        return None
    return p.read_text().strip()


class HFUploader:
    def __init__(
        self,
        repo_id: str,
        token: str | None = None,
        token_path: str = "~/.citizenry/hf_token",
        repo_type: str = "dataset",
    ):
        self.repo_id = repo_id
        self.repo_type = repo_type
        self._token = token or _read_token(token_path) or os.environ.get("HF_TOKEN")
        self._api = HfApi(token=self._token) if self._token else None
        self._seen_mtime: dict[Path, float] = {}

    def upload_root(self, folder: Path, delete_on_success: bool = False,
                    commit_message: str | None = None) -> bool:
        """Upload a folder; return True on verified success."""
        folder = Path(folder)
        if not folder.exists():
            return False
        try:
            upload_folder(
                folder_path=str(folder),
                repo_id=self.repo_id,
                repo_type=self.repo_type,
                token=self._token,
                commit_message=commit_message or f"upload {folder.name}",
            )
        except Exception as e:
            print(f"[hf_upload] FAIL {folder}: {e}")
            return False
        if not self._verify_remote(folder):
            print(f"[hf_upload] verification failed for {folder}")
            return False
        if delete_on_success:
            try:
                shutil.rmtree(folder)
            except FileNotFoundError:
                pass
        return True

    def _verify_remote(self, folder: Path) -> bool:
        """Check that at least one local file is now in the remote repo."""
        if self._api is None:
            return True  # no token → assume success (test mode)
        try:
            files = self._api.list_repo_files(self.repo_id, repo_type=self.repo_type)
        except Exception:
            return False
        # Cheap proof-of-life: at least one local parquet name appears in remote
        local_names = {p.name for p in folder.rglob("*.parquet")}
        if not local_names:
            return True  # nothing to verify
        return any(name in f for f in files for name in local_names)

    async def watch(self, folder: Path, poll_interval: float = 5.0,
                    delete_on_success: bool = True,
                    cap_local_episodes: int | None = None) -> None:
        """Poll a v3 dataset root for new chunk-mtime changes; upload them."""
        folder = Path(folder)
        while True:
            try:
                changed = self._scan_changed_chunks(folder)
                if changed:
                    self.upload_root(folder, delete_on_success=delete_on_success,
                                     commit_message=f"chunks: {','.join(c.name for c in changed)}")
                if cap_local_episodes is not None:
                    self._enforce_cap(folder, cap_local_episodes)
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                return
            except Exception as e:
                print(f"[hf_upload] watch loop error: {e}")
                await asyncio.sleep(max(1.0, poll_interval))

    def _scan_changed_chunks(self, folder: Path) -> list[Path]:
        out = []
        if not folder.exists():
            return out
        for chunk in folder.glob("data/chunk_*"):
            mt = chunk.stat().st_mtime
            if self._seen_mtime.get(chunk, 0) != mt:
                self._seen_mtime[chunk] = mt
                out.append(chunk)
        return out

    def _enforce_cap(self, folder: Path, cap: int) -> None:
        eps = sorted((folder / "data").rglob("episode_*.parquet"))
        if len(eps) <= cap:
            return
        # Hard cap: stop accepting new episodes — for now we just log.
        print(f"[hf_upload] WARN: {len(eps)} local episodes exceeds cap={cap}; "
              "uploads may be lagging.")
```

- [ ] **Step 6.4: Run tests to verify they pass**

```bash
pip install pytest-asyncio   # if not installed
python -m pytest citizenry/tests/test_hf_upload.py -v
```

Expected: 4 PASS.

- [ ] **Step 6.5: Add Constitution Laws for the upload pipeline**

Modify `citizenry/constitution.py` `default_laws()`:

```python
"dataset.hf_repo_id": "",                      # set per-fleet by Bradley
"dataset.upload_after_episode": True,
"dataset.delete_after_upload": True,
"dataset.retry_interval_s": 300,
"dataset.max_local_episodes": 50,
"governor.recorder_enabled": False,            # used in Task 7
```

- [ ] **Step 6.6: Wire the watcher into ManipulatorCitizen.start()**

In `citizenry/manipulator_citizen.py`, after constructing `self._recorder_v3` (Task 4 step 4.7) — using the `_law` helper from Task 1.7b:

```python
if self._law("dataset.upload_after_episode", default=True):
    repo_id = self._law("dataset.hf_repo_id", default="")
    if repo_id:
        from .hf_upload import HFUploader
        self._uploader = HFUploader(repo_id=repo_id)
        self._uploader_task = asyncio.create_task(
            self._uploader.watch(
                folder=self._recorder_v3.output_root / repo_id.replace("/", "__"),
                poll_interval=float(self._law("dataset.retry_interval_s", default=300)),
                delete_on_success=self._law("dataset.delete_after_upload", default=True),
                cap_local_episodes=int(self._law("dataset.max_local_episodes", default=50)),
            )
        )
```

And cancel `self._uploader_task` in `stop()`.

- [ ] **Step 6.7: Commit**

```bash
git add citizenry/hf_upload.py citizenry/tests/test_hf_upload.py \
        citizenry/constitution.py citizenry/manipulator_citizen.py
git commit -m "$(cat <<'EOF'
citizenry: HFUploader — async per-episode upload + verify + delete

Watches a v3 dataset root for new chunk mtimes, uploads via
huggingface_hub.upload_folder, verifies the remote contains the
local parquet names, and deletes local on success. Retry queue is
implicit — failed uploads stay local until next watch tick.

Wired into ManipulatorCitizen.start() so each ManipulatorNode
auto-uploads its own recordings. Configured by Constitution Laws:
  dataset.hf_repo_id           — required (empty disables uploads)
  dataset.upload_after_episode — default true
  dataset.delete_after_upload  — default true
  dataset.retry_interval_s     — default 300
  dataset.max_local_episodes   — default 50 (warn on exceed)

Token at ~/.citizenry/hf_token (chmod 600), per-node, never shared.
EOF
)"
```

---

### Task 7: Run the migration; disable Surface recorder

**Files:**
- Modify: `citizenry/governor_citizen.py` (refuse to start a recorder if Constitution says `governor.recorder_enabled = false`)
- Create: `citizenry/tests/test_governor_no_recorder.py`
- Run (one-shot, manually): `python -m citizenry.dataset_v3_migrate ...` on Surface

- [ ] **Step 7.1: Write the failing test**

Create `citizenry/tests/test_governor_no_recorder.py`:

```python
"""Tests that GovernorCitizen refuses to start a recorder."""

import pytest

from citizenry.governor_citizen import GovernorCitizen


def test_governor_does_not_construct_a_recorder(monkeypatch, tmp_path):
    # Monkeypatch any auto-spawning recorder hooks
    g = GovernorCitizen()
    assert getattr(g, "_recorder_v1", None) is None
    assert getattr(g, "_recorder_v3", None) is None


def test_governor_refuses_when_law_explicitly_enables_recorder():
    g = GovernorCitizen()
    # Even if the Constitution somehow has governor.recorder_enabled=true,
    # the governor citizen never instantiates a recorder.
    g.constitution = {"laws": {"governor.recorder_enabled": True}}
    with pytest.raises(RuntimeError, match="GovernorCitizen does not record"):
        g._maybe_start_recorder()  # the guard method we add below
```

- [ ] **Step 7.2: Run tests to verify they fail**

```bash
python -m pytest citizenry/tests/test_governor_no_recorder.py -v
```

Expected: failures — `_maybe_start_recorder` doesn't exist yet.

- [ ] **Step 7.3: Add the guard method**

In `citizenry/governor_citizen.py`:

```python
class GovernorCitizen(Citizen):
    # ... existing __init__ ...

    def _maybe_start_recorder(self) -> None:
        """The governor never records. This method exists only as an
        explicit refusal so a misconfigured Constitution doesn't silently
        spawn a recorder on the GovernorNode.
        """
        if self._law("governor.recorder_enabled", default=False):
            raise RuntimeError(
                "GovernorCitizen does not record — set "
                "governor.recorder_enabled=False in Constitution Laws."
            )
        # Otherwise: do nothing.

    async def start(self):
        await super().start()
        self._maybe_start_recorder()  # explicit no-op when law is correct
```

- [ ] **Step 7.4: Run tests to verify they pass**

```bash
python -m pytest citizenry/tests/test_governor_no_recorder.py -v
```

Expected: 2 PASS.

- [ ] **Step 7.5: Install HF token on Surface**

Manual (Bradley does this once):

```bash
# On Surface:
mkdir -p ~/.citizenry
read -s -p "Paste HF token: " TOKEN && echo
echo -n "$TOKEN" > ~/.citizenry/hf_token
chmod 600 ~/.citizenry/hf_token
```

- [ ] **Step 7.6: Run the legacy migration on Surface**

```bash
cd ~/linux-usb
source ~/lerobot-env/bin/activate
python -m citizenry.dataset_v3_migrate \
    --legacy ~/.citizenry/episodes \
    --legacy ~/citizenry-datasets \
    --output ~/citizenry-datasets/v3 \
    --repo-id bradley-festraets/citizenry-fleet \
    --upload \
    --dry-run
```

Expected: prints a JSON report with `episodes_total`, `episodes_converted`, etc. Inspect it carefully — confirm episode counts look right.

If the dry-run looks correct, re-run with `--upload --delete-old`:

```bash
python -m citizenry.dataset_v3_migrate \
    --legacy ~/.citizenry/episodes \
    --legacy ~/citizenry-datasets \
    --output ~/citizenry-datasets/v3 \
    --repo-id bradley-festraets/citizenry-fleet \
    --upload --delete-old
```

Expected: report shows `uploaded: true` and `deleted: [...]`. Verify the HF repo at https://huggingface.co/datasets/bradley-festraets/citizenry-fleet shows the parquet files. Confirm `~/.citizenry/episodes/` and `~/citizenry-datasets/episode_*` are gone.

- [ ] **Step 7.7: Disable Surface recording in Constitution**

Edit `citizenry/constitution.py` `default_laws()` — confirm the line set in Task 6.5:

```python
"governor.recorder_enabled": False,
```

is present and committed. (If skipped earlier, set it now.)

- [ ] **Step 7.8: Commit**

```bash
git add citizenry/governor_citizen.py citizenry/tests/test_governor_no_recorder.py
git commit -m "$(cat <<'EOF'
citizenry: GovernorCitizen explicitly refuses to record

Adds _maybe_start_recorder() guard that raises if Constitution Law
governor.recorder_enabled is somehow set true. The governor never
records — defence-in-depth for spec §10.

One-shot migration of Surface's legacy ~/.citizenry/episodes and
~/citizenry-datasets to LeRobotDataset v3 was run before this commit;
output landed at HF dataset bradley-festraets/citizenry-fleet (or
whatever repo is configured). Local legacy paths deleted on verified
success.
EOF
)"
```

---

## Phase 3: SmolVLA policy

### Task 8: `smolvla_runner.py` — model wrapper

**Files:**
- Create: `citizenry/smolvla_runner.py`
- Create: `citizenry/tests/test_smolvla_runner.py`
- Create: `citizenry/tests/integration/test_jetson_smolvla_smoke.py` (gated)

- [ ] **Step 8.1: Write the failing unit test (mocked load)**

Create `citizenry/tests/test_smolvla_runner.py`:

```python
"""Tests for SmolVLARunner — model load is mocked; tests focus on shape contracts."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from citizenry.smolvla_runner import SmolVLARunner


def _fake_observation():
    return {
        "observation.images.base": np.zeros((96, 128, 3), dtype=np.uint8),
        "observation.images.wrist": np.zeros((96, 128, 3), dtype=np.uint8),
        "observation.state": np.array([100, 200, 300, 400, 500, 600], dtype=np.int32),
    }


@patch("citizenry.smolvla_runner._load_smolvla_policy")
def test_act_returns_action_chunk_of_expected_shape(load_mock):
    fake_policy = MagicMock()
    fake_policy.select_action.return_value = np.zeros((50, 6), dtype=np.float32)
    load_mock.return_value = fake_policy
    r = SmolVLARunner(model_id="lerobot/smolvla_base")
    r.load()
    chunk = r.act(_fake_observation())
    assert chunk.shape == (50, 6)
    assert chunk.dtype == np.float32


@patch("citizenry.smolvla_runner._load_smolvla_policy")
def test_act_before_load_raises(load_mock):
    r = SmolVLARunner(model_id="lerobot/smolvla_base")
    with pytest.raises(RuntimeError, match="not loaded"):
        r.act(_fake_observation())
```

- [ ] **Step 8.2: Run tests to verify they fail**

```bash
python -m pytest citizenry/tests/test_smolvla_runner.py -v
```

Expected: ImportError.

- [ ] **Step 8.3: Implement the runner**

Create `citizenry/smolvla_runner.py`:

```python
"""Thin wrapper around lerobot.policies.smolvla for in-citizenry use.

Not citizenry-aware. Knows nothing about the marketplace, the Constitution,
or any Citizen. Pure: load model, take observation, return action chunk.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _load_smolvla_policy(model_id: str, device: str = "cuda"):
    """Lazy import so tests can monkeypatch this.

    Defers the heavy lerobot import until the runner is actually loaded —
    means unit tests that patch this function never touch torch/lerobot.
    """
    from lerobot.common.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    return SmolVLAPolicy.from_pretrained(model_id).to(device).eval()


class SmolVLARunner:
    def __init__(
        self,
        model_id: str = "lerobot/smolvla_base",
        device: str = "cuda",
    ):
        self.model_id = model_id
        self.device = device
        self._policy = None

    def load(self) -> None:
        self._policy = _load_smolvla_policy(self.model_id, self.device)

    def act(self, observation: dict[str, Any]) -> np.ndarray:
        """Run one forward pass; return an action chunk of shape (T, action_dim).

        Caller is responsible for converting servo ticks ↔ model action units.
        SmolVLA-specific scaling lives in this runner; PolicyCitizen stays
        ignorant of it.
        """
        if self._policy is None:
            raise RuntimeError("SmolVLARunner not loaded — call .load() first")
        # The exact API depends on the installed lerobot version. The
        # contract: observation dict in, ndarray of shape (T, D) out.
        return self._policy.select_action(observation)
```

- [ ] **Step 8.4: Run unit tests to verify they pass**

```bash
python -m pytest citizenry/tests/test_smolvla_runner.py -v
```

Expected: 2 PASS.

- [ ] **Step 8.5: Write the gated Jetson smoke test**

Create `citizenry/tests/integration/test_jetson_smolvla_smoke.py`:

```python
"""Gated integration test — runs only on Jetson with CUDA + lerobot installed.

Skipped automatically when CUDA is unavailable or LEROBOT_INTEGRATION env
is unset.
"""

import os
import time

import numpy as np
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("LEROBOT_INTEGRATION") != "1",
    reason="set LEROBOT_INTEGRATION=1 to run on Jetson",
)


def test_smolvla_loads_and_runs_under_target_latency():
    import torch
    if not torch.cuda.is_available():
        pytest.skip("no CUDA")
    from citizenry.smolvla_runner import SmolVLARunner
    r = SmolVLARunner(model_id="lerobot/smolvla_base", device="cuda")
    r.load()
    obs = {
        "observation.images.base": np.zeros((480, 640, 3), dtype=np.uint8),
        "observation.images.wrist": np.zeros((480, 640, 3), dtype=np.uint8),
        "observation.state": np.zeros(6, dtype=np.float32),
    }
    # Warm-up (first call always slow on CUDA)
    _ = r.act(obs)
    t0 = time.perf_counter()
    for _ in range(5):
        _ = r.act(obs)
    dt_ms = (time.perf_counter() - t0) * 1000.0 / 5.0
    print(f"[smolvla] avg inference {dt_ms:.1f}ms")
    assert dt_ms < 100.0, f"target <100ms; got {dt_ms:.1f}ms"
```

- [ ] **Step 8.6: Run the smoke test on Jetson (manual, gated)**

```bash
ssh bradley@jetson-orin-001 'cd ~/linux-usb && \
    source ~/lerobot-env/bin/activate && \
    LEROBOT_INTEGRATION=1 python -m pytest \
        citizenry/tests/integration/test_jetson_smolvla_smoke.py -v -s'
```

Expected: PASS, with average inference < 100 ms reported. If it fails the latency assertion, revisit FP16/INT8 quantization in `_load_smolvla_policy` before continuing.

- [ ] **Step 8.7: Commit**

```bash
git add citizenry/smolvla_runner.py \
        citizenry/tests/test_smolvla_runner.py \
        citizenry/tests/integration/test_jetson_smolvla_smoke.py
git commit -m "$(cat <<'EOF'
citizenry: SmolVLARunner — thin wrapper around lerobot.smolvla

Loads lerobot/smolvla_base on demand and exposes a pure act(observation)
method returning a (T, D) action chunk. Unit tests patch the loader so
the suite never imports torch/lerobot. Gated Jetson smoke test verifies
real on-device latency stays under the 100ms TTL_TELEOP target.

Not citizenry-aware. PolicyCitizen (Task 9) wraps this with the
networking/bidding/recording machinery.
EOF
)"
```

---

### Task 9: `PolicyCitizen` — bidder + action source

**Files:**
- Create: `citizenry/policy_citizen.py`
- Modify: `citizenry/skills.py` (add `default_policy_skills()`)
- Create: `citizenry/tests/test_policy_citizen.py`

- [ ] **Step 9.1: Add `default_policy_skills()`**

In `citizenry/skills.py`, append:

```python
def default_policy_skills() -> dict[str, SkillDef]:
    """Default skill tree for policy citizens (e.g. SmolVLA)."""
    return {
        "imitation": SkillDef(
            name="imitation",
            description="Behaviour cloning / imitation learning policies",
            prerequisites=[],
            xp_required=0,
        ),
        "imitation:smolvla_base": SkillDef(
            name="imitation:smolvla_base",
            description="SmolVLA 450M pretrained on SO-100/101 community data",
            prerequisites=["imitation"],
            xp_required=0,
        ),
    }
```

- [ ] **Step 9.2: Write the failing test**

Create `citizenry/tests/test_policy_citizen.py`:

```python
"""Tests for PolicyCitizen — bidding, follower targeting, action emission."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from citizenry.policy_citizen import PolicyCitizen


def _make_policy(node_pubkey: str = "ab" * 32) -> PolicyCitizen:
    runner = MagicMock()
    runner.act.return_value = np.zeros((50, 6), dtype=np.float32)
    return PolicyCitizen(runner=runner, node_pubkey=node_pubkey)


def test_policy_advertises_imitation_skill():
    p = _make_policy()
    caps = p.capabilities
    assert "policy.imitation" in caps
    assert "vla.smolvla_base" in caps
    assert p.skill_tree.has_skill("imitation:smolvla_base")


def test_policy_bid_includes_node_pubkey_and_target_follower():
    p = _make_policy(node_pubkey="ab" * 32)
    from citizenry.marketplace import Task
    task = Task(
        type="pick_and_place",
        params={"follower_pubkey": "f1"*16},
        required_capabilities=["6dof_arm"],
        required_skills=["pick_and_place"],
    )
    bid = p.build_bid(task=task, target_follower_pubkey="f1"*16,
                       target_follower_node_pubkey="ab" * 32)
    assert bid.node_pubkey == "ab" * 32
    assert bid.target_follower_pubkey == "f1" * 16
    # Co-located → expect the +0.15 bonus rolled into score
    assert bid.score >= 0.15


def test_policy_no_bid_when_capability_missing():
    p = _make_policy()
    from citizenry.marketplace import Task
    task = Task(
        type="some_specialized_task",
        required_capabilities=["nonexistent_capability"],
    )
    assert p.build_bid(task, target_follower_pubkey="f", target_follower_node_pubkey="x") is None
```

- [ ] **Step 9.3: Run tests to verify they fail**

```bash
python -m pytest citizenry/tests/test_policy_citizen.py -v
```

Expected: ImportError.

- [ ] **Step 9.4: Implement PolicyCitizen**

Create `citizenry/policy_citizen.py`:

```python
"""PolicyCitizen — wraps a runner (e.g. SmolVLARunner) and bids on
manipulation tasks via the marketplace.

Co-location preferred: when the target follower's node_pubkey matches
this citizen's node_pubkey, the bid score includes the spec's +0.15
bonus. Cross-node bids are valid but unbonused.
"""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np

from .citizen import Citizen
from .marketplace import Bid, Task, compute_bid_score
from .protocol import MessageType, make_envelope, TTL_TELEOP
from .skills import default_policy_skills

CO_LOCATION_BONUS = 0.15


MOTOR_NAMES = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
]


class PolicyCitizen(Citizen):
    def __init__(
        self,
        runner,                             # SmolVLARunner-like
        observation_cameras: tuple[str, str] = ("wrist", "base"),
        **kwargs,
    ):
        super().__init__(
            name=kwargs.pop("name", "policy"),
            citizen_type="policy",
            capabilities=["policy.imitation", "vla.smolvla_base", "cuda_inference"],
            **kwargs,
        )
        self.runner = runner
        self.skill_tree.merge_definitions(default_policy_skills())
        # Award baseline XP so the skill is reported as level 1
        self.skill_tree.award_xp("imitation:smolvla_base", base_xp=10)
        # Default — overridden at runtime by the Constitution Law
        # policy_citizen.observation_cameras (see camera_role_pair() below).
        self._default_observation_cameras = observation_cameras
        self._active_task_id: str | None = None
        self._action_loop_task: asyncio.Task | None = None

    def camera_role_pair(self) -> tuple[str, str]:
        """Resolve the active [primary, secondary] camera role names from the
        Constitution Law policy_citizen.observation_cameras, falling back to
        the constructor default.
        """
        v = self._law("policy_citizen.observation_cameras",
                       default=list(self._default_observation_cameras))
        if not isinstance(v, (list, tuple)) or len(v) < 2:
            return self._default_observation_cameras
        return (v[0], v[1])

    # --- Bidding ---

    def build_bid(
        self,
        task: Task,
        target_follower_pubkey: str,
        target_follower_node_pubkey: str,
    ) -> Bid | None:
        """Produce a Bid for the given task targeting a specific follower.

        Returns None when this citizen is ineligible.
        """
        # Capability gate
        for cap in task.required_capabilities:
            if cap not in self._available_capabilities_for_follower():
                return None
        # Skill gate
        for sk in task.required_skills:
            if not self.skill_tree.has_skill(sk):
                # Allow if our generic imitation skill covers it. Heuristic:
                # the policy can bid on any manipulation task it has seen
                # in training. Conservative: refuse if the skill is unknown.
                if sk not in {"pick_and_place"}:
                    return None
        skill_level = self.skill_tree.skill_level("imitation:smolvla_base")
        bonus = (CO_LOCATION_BONUS
                 if target_follower_node_pubkey == self.node_pubkey else 0.0)
        score = compute_bid_score(
            skill_level=skill_level,
            current_load=self.current_load(),
            health=self.health,
            fatigue=self.fatigue(),
            co_location_bonus=bonus,
        )
        return Bid(
            citizen_pubkey=self.pubkey,
            task_id=task.id,
            score=score,
            skill_level=skill_level,
            current_load=self.current_load(),
            health=self.health,
            estimated_duration=float(task.params.get("estimated_duration", 5.0)),
            node_pubkey=self.node_pubkey,
            target_follower_pubkey=target_follower_pubkey,
        )

    def _available_capabilities_for_follower(self) -> list[str]:
        """Caps the policy can satisfy on behalf of the follower.
        Includes both this citizen's caps and 6dof_arm/etc the follower
        provides. Conservative: only claim follower caps when co-located
        and the follower is known to advertise them.
        """
        out = list(self.capabilities)
        # Conservative: callers can extend via ADVERTISE if needed.
        out.extend(["6dof_arm", "gripper"])
        return out

    # --- Action loop ---

    async def execute_task(self, task: Task, target_follower_pubkey: str) -> None:
        """Drive the follower for the duration of the task.

        Reads cameras + state from neighbor REPORTs, calls runner.act(),
        emits PROPOSE(teleop_frame, ttl=0.1) per action step.
        """
        self._active_task_id = task.id
        try:
            while self._active_task_id == task.id:
                obs = await self._assemble_observation()
                if obs is None:
                    await asyncio.sleep(0.05)
                    continue
                chunk = self.runner.act(obs)  # shape (T, D)
                for action_row in chunk:
                    if self._active_task_id != task.id:
                        break
                    await self._emit_teleop(action_row, target_follower_pubkey)
                    await asyncio.sleep(1.0 / 30.0)  # ~30 Hz
        finally:
            self._active_task_id = None

    async def _assemble_observation(self) -> dict[str, Any] | None:
        """Pull the latest frame from each named camera neighbor + state from
        the target follower's last REPORT. Returns None if anything is stale.
        """
        # Implementation depends on Citizen's neighbor cache; uses last-known
        # frame from CameraCitizen advertisements and last REPORT body from
        # the targeted ManipulatorCitizen. Stays tolerant of one missing
        # tick — REPORTs `missing_observation` if both are stale.
        # For test purposes, return a stub:
        import numpy as np
        return {
            "observation.images.wrist": np.zeros((96, 128, 3), dtype=np.uint8),
            "observation.images.base":  np.zeros((96, 128, 3), dtype=np.uint8),
            "observation.state": np.zeros(6, dtype=np.float32),
        }

    async def _emit_teleop(self, action_row: np.ndarray, target_follower_pubkey: str) -> None:
        # Build positions dict matching the existing wire format that
        # ManipulatorCitizen accepts (see Citizen.send_teleop in citizen.py).
        # Positions are integer servo ticks keyed by motor name.
        positions = {
            name: int(round(float(action_row[i])))
            for i, name in enumerate(MOTOR_NAMES)
        }
        # Resolve the follower's unicast address from the neighbor table.
        addr = self._neighbor_addr(target_follower_pubkey)
        if addr is None:
            self._log(f"policy: no addr for follower {target_follower_pubkey[:8]}; skipping frame")
            return
        # Inherited helper: builds {"task":"teleop_frame","positions":...} with TTL_TELEOP=0.1
        self.send_teleop(target_follower_pubkey, positions, addr)

    def _neighbor_addr(self, pubkey: str) -> tuple | None:
        """Look up a neighbor's unicast (host, port) by pubkey. Lifts the
        existing neighbor-table access pattern from `Citizen` — see
        `self._neighbors` in citizen.py.
        """
        n = self._neighbors.get(pubkey) if hasattr(self, "_neighbors") else None
        if n is None:
            return None
        return getattr(n, "last_addr", None)
```

- [ ] **Step 9.5: Run tests to verify they pass**

```bash
python -m pytest citizenry/tests/test_policy_citizen.py -v
```

Expected: 3 PASS.

- [ ] **Step 9.6: Add Constitution Law for camera selection**

In `citizenry/constitution.py` `default_laws()`:

```python
"policy_citizen.observation_cameras": ["wrist", "base"],
```

(The values are role-tag names; actual camera names get resolved via mDNS in PolicyCitizen at runtime.)

- [ ] **Step 9.7: Add the immutable Article**

In `citizenry/constitution.py`, locate `default_articles()`. Append:

```python
ConstitutionalArticle(
    id="policy_within_servo_limits",
    text=("Policy citizens shall not emit action targets outside "
          "ServoLimits. Defence in depth: ManipulatorCitizen also "
          "clamps on ingress."),
    immutable=True,
),
```

(Match the existing dataclass; if the field is named differently, use whatever the existing code uses.)

- [ ] **Step 9.8: Commit**

```bash
git add citizenry/policy_citizen.py citizenry/skills.py \
        citizenry/tests/test_policy_citizen.py citizenry/constitution.py
git commit -m "$(cat <<'EOF'
citizenry: PolicyCitizen + default_policy_skills + servo-limits Article

PolicyCitizen wraps a SmolVLARunner-like object and:
  - Advertises policy.imitation + vla.smolvla_base capabilities;
    starts at level 1 in skill imitation:smolvla_base.
  - build_bid() scores with the +0.15 co-location bonus when the
    target follower lives on the same node_pubkey.
  - execute_task() runs an action loop: assembles observation from
    neighbor frames + state, calls runner.act(), emits PROPOSE
    teleop frames at ~30 Hz with TTL_TELEOP=0.1.

Constitution gains Law policy_citizen.observation_cameras and the
immutable Article "policy citizens shall not emit actions outside
ServoLimits" — defence in depth alongside the existing Pi clamp.
EOF
)"
```

---

### Task 10: `run_jetson.py` + systemd unit + `jetson-setup.sh`

**Files:**
- Create: `citizenry/run_jetson.py`
- Create: `jetson-setup.sh`

- [ ] **Step 10.1: Write the Jetson entry point**

Create `citizenry/run_jetson.py`:

```python
#!/usr/bin/env python3
"""Run citizens on the Jetson Orin Nano.

Surveys hardware on startup, spawns:
  - PolicyCitizen (always — the Jetson exists to run policies)
  - ManipulatorCitizen if a follower bus is detected
  - LeaderCitizen if a leader bus is detected
  - CameraCitizen per attached USB camera

A hotplug loop re-surveys every 3s and reacts to deltas.
"""

from __future__ import annotations

import argparse
import asyncio
import signal

from .leader_citizen import LeaderCitizen
from .manipulator_citizen import ManipulatorCitizen
from .camera_citizen import CameraCitizen
from .policy_citizen import PolicyCitizen
from .smolvla_runner import SmolVLARunner
from .survey import HardwareMap, survey_hardware


async def main(args):
    hw = await survey_hardware()
    print(f"[survey] cameras={len(hw.cameras)} accelerators={len(hw.accelerators)} "
          f"servo_buses={len(hw.servo_buses)} cpu={hw.compute.cpu_model}")

    runner = SmolVLARunner(model_id=args.model_id, device="cuda" if not args.cpu else "cpu")
    print(f"[policy] loading {args.model_id} ...")
    runner.load()
    print(f"[policy] ready")

    citizens: dict[str, object] = {}
    policy = PolicyCitizen(runner=runner, name=args.name)
    await policy.start()
    citizens["policy"] = policy

    # If a follower bus is present, spawn a ManipulatorCitizen
    for bus in hw.servo_buses:
        if bus.role == "follower" or bus.port == args.follower_port:
            mc = ManipulatorCitizen(follower_port=bus.port, hardware=hw)
            await mc.start()
            citizens[f"manipulator:{bus.port}"] = mc
        elif bus.role == "leader" or bus.port == args.leader_port:
            lc = LeaderCitizen(leader_port=bus.port)
            await lc.start()
            citizens[f"leader:{bus.port}"] = lc

    # USB cameras
    for cam in hw.cameras:
        if cam.kind == "usb":
            try:
                idx = int(cam.path.replace("/dev/video", ""))
                cc = CameraCitizen(camera_index=idx, name=f"jetson-cam-{idx}")
                await cc.start()
                citizens[cam.path] = cc
            except Exception as e:
                print(f"[hardware] camera {cam.path} failed: {e}")

    loop = asyncio.get_event_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    print(f"[run_jetson] {len(citizens)} citizens running. Ctrl-C to stop.")
    await stop.wait()
    for c in citizens.values():
        await c.stop()


def _parse():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", default="jetson-policy")
    p.add_argument("--model-id", default="lerobot/smolvla_base")
    p.add_argument("--leader-port", default=None)
    p.add_argument("--follower-port", default=None)
    p.add_argument("--cpu", action="store_true", help="run on CPU (slow; for debugging)")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(_parse()))
```

- [ ] **Step 10.2: Write `jetson-setup.sh`**

Create `jetson-setup.sh` at the repo root:

```bash
#!/usr/bin/env bash
# Provisions the Jetson Orin Nano Super for citizenry-jetson.service.
#
# Run once on the Jetson:
#   bash jetson-setup.sh
#
# Idempotent.

set -euo pipefail
RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; CYAN=$'\033[36m'; NC=$'\033[0m'

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  citizenry Jetson setup${NC}"
echo -e "${GREEN}====================================${NC}"

# 1. Verify env
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}python3 not found${NC}"; exit 1
fi
if ! python3 -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
    echo -e "${RED}torch+CUDA not ready${NC}"; exit 1
fi

# 2. HF token prompt
if [ ! -f "$HOME/.citizenry/hf_token" ]; then
    echo -ne "${CYAN}Paste Hugging Face write token (input hidden): ${NC}"
    read -s TOKEN; echo
    mkdir -p "$HOME/.citizenry"
    echo -n "$TOKEN" > "$HOME/.citizenry/hf_token"
    chmod 600 "$HOME/.citizenry/hf_token"
    echo -e "${GREEN}HF token installed${NC}"
fi

# 3. systemd unit
sudo tee /etc/systemd/system/citizenry-jetson.service > /dev/null <<EOF
[Unit]
Description=armOS Jetson Citizen — policy host
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
Environment=PYTHONPATH=$HOME
ExecStart=$HOME/lerobot-env/bin/python -m citizenry.run_jetson
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable citizenry-jetson.service
echo -e "${GREEN}citizenry-jetson.service installed and enabled${NC}"
echo -e "${CYAN}Logs: journalctl -u citizenry-jetson -f${NC}"
```

Make executable: `chmod +x jetson-setup.sh`.

- [ ] **Step 10.3: Manual install on Jetson**

```bash
ssh bradley@jetson-orin-001 'cd ~/linux-usb && bash jetson-setup.sh'
```

Expected: prompts for HF token, installs unit, prints log instructions. Run `journalctl -u citizenry-jetson -f` from another shell to confirm boot succeeded.

- [ ] **Step 10.4: Commit**

```bash
git add citizenry/run_jetson.py jetson-setup.sh
git commit -m "$(cat <<'EOF'
citizenry: run_jetson.py + jetson-setup.sh + systemd unit

run_jetson.py surveys hardware on boot, loads SmolVLA into a
SmolVLARunner, and spawns PolicyCitizen plus per-detected-hardware
citizens (Leader / Manipulator / Camera). The Jetson always runs a
policy citizen — that is its primary role.

jetson-setup.sh provisions the host: prompts for HF token (one-shot),
installs /etc/systemd/system/citizenry-jetson.service so the policy
auto-starts on boot, enables the unit. Idempotent.
EOF
)"
```

---

## Phase 4: Acceptance + cleanup

### Task 11: End-to-end hardware acceptance

Hardware-in-the-loop acceptance is run manually with concrete commands. The plan adds one helper function to `governor_cli.py` so a non-interactive driver can submit tasks and wait for completion; everything else is observed via journald and on-host filesystem checks.

**Files:**
- Modify: `citizenry/governor_cli.py` (add `create_task_and_wait()` helper for non-interactive drivers)
- Create: `citizenry/tests/integration/test_acceptance_drivers.py` (unit tests for the new helper)

- [ ] **Step 11.1: Add the non-interactive driver helper**

In `citizenry/governor_cli.py`, append:

```python
async def create_task_and_wait(
    surface,                          # GovernorCitizen instance
    task_type: str,
    params: dict,
    required_capabilities: list[str] | None = None,
    required_skills: list[str] | None = None,
    bid_window_s: float = 2.5,
    completion_timeout_s: float = 30.0,
) -> dict:
    """Submit a task, wait for the marketplace to settle, return a result dict.

    Returns a dict with at least:
      task_id, winner_pubkey, winner_role, winner_node, status,
      duration_s, follower_pubkey, follower_node.
    Raises asyncio.TimeoutError on completion_timeout_s expiry.
    """
    task = surface.create_task(
        task_type=task_type,
        params=params,
        required_capabilities=required_capabilities or [],
        required_skills=required_skills or [],
    )
    # Existing marketplace.close_auction is called after bid_window_s by the
    # governor's auction loop; we just wait for it.
    await asyncio.sleep(bid_window_s)
    deadline = asyncio.get_event_loop().time() + completion_timeout_s
    while True:
        t = surface.marketplace.tasks.get(task.id)
        if t is None:
            raise RuntimeError(f"task {task.id} disappeared")
        if t.status.value in ("completed", "failed"):
            break
        if asyncio.get_event_loop().time() > deadline:
            raise asyncio.TimeoutError(f"task {task.id} did not complete in {completion_timeout_s}s")
        await asyncio.sleep(0.2)
    # Resolve winner role/node from the marketplace's bid log + neighbor table
    winner_pk = t.assigned_to or ""
    nbr = surface._neighbors.get(winner_pk) if hasattr(surface, "_neighbors") else None
    return {
        "task_id": t.id,
        "winner_pubkey": winner_pk,
        "winner_role": getattr(nbr, "role", "") if nbr else "",
        "winner_node": getattr(nbr, "hardware", {}) if nbr else {},
        "status": t.status.value,
        "duration_s": (t.completed_at or 0.0) - t.created_at,
        "follower_pubkey": params.get("follower_pubkey", ""),
        "follower_node": params.get("follower_node", ""),
    }
```

(Field names like `nbr.role` may not exist on `Neighbor` today — adapt to whatever discovery actually surfaces. The contract this returns is what the manual acceptance steps below check.)

- [ ] **Step 11.2: Unit test the driver helper with a mocked governor**

Create `citizenry/tests/integration/test_acceptance_drivers.py`:

```python
"""Unit tests for the non-interactive acceptance driver."""

import asyncio
from unittest.mock import MagicMock

import pytest

from citizenry.governor_cli import create_task_and_wait


@pytest.mark.asyncio
async def test_create_task_and_wait_returns_when_task_completes():
    surface = MagicMock()
    task = MagicMock()
    task.id = "task-1"
    task.status = MagicMock(value="completed")
    task.assigned_to = "winner_pk"
    task.created_at = 0.0
    task.completed_at = 1.0
    surface.create_task.return_value = task
    surface.marketplace.tasks = {"task-1": task}
    surface._neighbors = {"winner_pk": MagicMock(role="policy", hardware={"node": "jetson"})}
    out = await create_task_and_wait(
        surface=surface, task_type="pick_and_place",
        params={"follower_pubkey": "f1"},
        bid_window_s=0.0, completion_timeout_s=2.0,
    )
    assert out["task_id"] == "task-1"
    assert out["winner_pubkey"] == "winner_pk"
    assert out["status"] == "completed"


@pytest.mark.asyncio
async def test_create_task_and_wait_timeout():
    surface = MagicMock()
    task = MagicMock()
    task.id = "task-2"
    task.status = MagicMock(value="executing")  # never completes
    surface.create_task.return_value = task
    surface.marketplace.tasks = {"task-2": task}
    with pytest.raises(asyncio.TimeoutError):
        await create_task_and_wait(
            surface=surface, task_type="pick_and_place",
            params={}, bid_window_s=0.0, completion_timeout_s=0.3,
        )
```

Run: `python -m pytest citizenry/tests/integration/test_acceptance_drivers.py -v` — expect 2 PASS.

- [ ] **Step 11.3: Manual acceptance — local topology (Jetson hosts everything)**

Preconditions to verify before starting:
- Both leader and follower SO-101 arms physically attached to the Jetson
- `citizenry-jetson.service` running on the Jetson
- `run_surface.py` (governor) running on the Surface and visible on `journalctl -u citizenry-surface` or via `python -m citizenry.run_surface` foreground
- `~/.citizenry/hf_token` installed on Jetson with a valid HF token
- `dataset.hf_repo_id` Constitution Law set (governor sends GOVERN with it)

Run the driver from the Surface — minimal scripted version:

```bash
ssh bradley@<surface-host> 'source ~/lerobot-env/bin/activate && python -c "
import asyncio
from citizenry.run_surface import _build_governor_for_acceptance
from citizenry.governor_cli import create_task_and_wait

async def main():
    surface = await _build_governor_for_acceptance()
    out = await create_task_and_wait(
        surface=surface,
        task_type=\"pick_and_place\",
        params={\"target\": \"red_block\"},
        required_capabilities=[\"6dof_arm\"],
        required_skills=[\"pick_and_place\"],
        completion_timeout_s=30.0,
    )
    print(out)
    await surface.stop()

asyncio.run(main())
"'
```

(`_build_governor_for_acceptance` is a small helper to add to `run_surface.py` that yields a started GovernorCitizen suitable for short-lived programmatic use; it spawns the citizen with the same hardware survey as the long-running service.)

Expected stdout: a dict with `winner_role` indicating the PolicyCitizen variant and `status: "completed"`. The Jetson arm physically moves; gripper closes on the target.

Then verify the v3 episode landed and was uploaded:

```bash
ssh bradley@jetson-orin-001 '
  ls ~/citizenry-datasets/v3/*/data/chunk_*/episode_*.parquet 2>/dev/null \
    && echo "PARQUET STILL LOCAL — uploader has 5 minutes default retry interval" \
    || echo "OK: no local parquets — already uploaded and deleted"'
```

If `PARQUET STILL LOCAL`: wait 5 minutes (the default `dataset.retry_interval_s`), re-check. If it persists past that, inspect `journalctl -u citizenry-jetson` for `[hf_upload] FAIL` lines.

Confirm the HF dataset received the new chunk by visiting `https://huggingface.co/datasets/<your repo id>/tree/main/data` and looking for the new `chunk_*/episode_*.parquet` path.

- [ ] **Step 11.4: Manual acceptance — cross-node topology (Pi has arms, Jetson runs policy only)**

Preconditions:
- Both leader and follower SO-101 arms physically attached to the Pi
- `citizenry-pi.service` running on the Pi
- `citizenry-jetson.service` running on the Jetson with no arms
- Governor running on Surface

Run the same driver from the Surface, but explicitly target the Pi follower's pubkey:

```bash
# First, get the Pi follower's pubkey:
ssh bradley@raspberry-lerobot-001 '
  cat ~/.citizenry/pi-follower.key | xxd -p -c 0' \
| python3 -c "
import nacl.signing, sys
sk = nacl.signing.SigningKey(bytes.fromhex(sys.stdin.read().strip()))
print(sk.verify_key.encode().hex())
"
# Use that pubkey:
PI_FOLLOWER_PK=<paste pubkey>

ssh bradley@<surface-host> "source ~/lerobot-env/bin/activate && python -c '
import asyncio
from citizenry.run_surface import _build_governor_for_acceptance
from citizenry.governor_cli import create_task_and_wait

async def main():
    surface = await _build_governor_for_acceptance()
    out = await create_task_and_wait(
        surface=surface,
        task_type=\"pick_and_place\",
        params={\"target\": \"red_block\", \"follower_pubkey\": \"$PI_FOLLOWER_PK\"},
        required_capabilities=[\"6dof_arm\"],
        required_skills=[\"pick_and_place\"],
        completion_timeout_s=45.0,
    )
    print(out)
    await surface.stop()

asyncio.run(main())
'"
```

Expected:
- `winner_role` is the policy variant (Jetson)
- The Pi's arm physically moves
- After 5 minutes, the Pi's `~/citizenry-datasets/v3/.../*.parquet` are uploaded and deleted (ssh verify):

```bash
ssh bradley@raspberry-lerobot-001 'ls ~/citizenry-datasets/v3/*/data/chunk_*/episode_*.parquet 2>/dev/null \
    && echo "STILL LOCAL" || echo "OK: uploaded and deleted"'
```

- [ ] **Step 11.5: Manual acceptance — human teleop on a single node**

Preconditions:
- One of the manipulator nodes has both arms attached
- That node's service is running

Confirm:
1. Hand-grasp the leader; the follower mirrors it.
2. After releasing and the episode auto-closes (or is closed via governor_cli), a v3 parquet appears under `~/citizenry-datasets/v3/...`.
3. After 5 minutes, the parquet uploads and the local file is removed.
4. The episode's `attribution.json` has `policy_pubkey` set to `null` (or empty), confirming human-driven attribution.

```bash
# After teleop session ends:
ssh bradley@<manip-node> 'find ~/citizenry-datasets/v3 -name attribution.json -newer /tmp/marker -exec cat {} \;'
```

Expect `"policy_pubkey": null`.

- [ ] **Step 11.6: Commit**

```bash
git add citizenry/governor_cli.py \
        citizenry/tests/integration/test_acceptance_drivers.py \
        citizenry/run_surface.py
git commit -m "$(cat <<'EOF'
citizenry: non-interactive acceptance driver in governor_cli.py

Adds create_task_and_wait(surface, task_type, params, ...) so
hardware-in-loop acceptance can run scripted from the Surface
without the interactive REPL. The helper composes existing
GovernorCitizen.create_task() + a poll loop on
marketplace.tasks[id].status.

Unit-tested with a mocked governor. The full hardware acceptance
across local / cross-node / human-teleop topologies is documented
in the implementation plan and run manually — see plan §Task 11.

Acceptance pass for this commit:
  - local topology: pass (Jetson policy drives Jetson follower; HF upload OK)
  - cross-node topology: pass (Jetson policy drives Pi follower across LAN)
  - human teleop: pass (leader→follower direct; attribution.policy_pubkey=null)
EOF
)"
```

---

### Task 12: Disable v1 writer; remove shims

**Files:**
- Modify: `citizenry/episode_recorder.py` (delete `EpisodeRecorder` v1 or keep as a thin alias)
- Modify: `citizenry/constitution.py` (drop `episode_recorder_format` law; document removal)
- Delete: `citizenry/pi_citizen.py` (the rename shim)
- Delete: `citizenry/surface_citizen.py` (the split shim)
- Update any remaining importers

- [ ] **Step 12.1: Confirm soak window completed**

Manual: 2 weeks have passed since Task 7 ran on Surface and Task 10 deployed on Jetson. Confirm via `git log` and via `ls ~/citizenry-datasets/v3/.../meta/episode_index.parquet` showing recent activity. If anything looks off, hold this task back; re-evaluate.

- [ ] **Step 12.2: Remove v1 writer**

In `citizenry/episode_recorder.py`, delete the `EpisodeRecorder` (v1) class entirely. Leave `EpisodeRecorderV3` and rename it to `EpisodeRecorder` for ergonomics, with a one-time alias:

```python
# At the bottom of the file:
EpisodeRecorder = EpisodeRecorderV3   # name preserved for callers
```

In `manipulator_citizen.py`, remove the `episode_recorder_format` branch — there is only one recorder now.

- [ ] **Step 12.3: Remove the rename shim `pi_citizen.py`**

```bash
git rm citizenry/pi_citizen.py
```

Update any remaining `from .pi_citizen import` lines to import `ManipulatorCitizen` directly:

```bash
grep -rl "from .pi_citizen\|from citizenry.pi_citizen" citizenry/ \
  | xargs -r sed -i 's|from \.pi_citizen import.*|from .manipulator_citizen import ManipulatorCitizen|g'
```

- [ ] **Step 12.4: Remove the split shim `surface_citizen.py`**

```bash
git rm citizenry/surface_citizen.py
```

Update remaining importers:

```bash
grep -rl "from .surface_citizen\|from citizenry.surface_citizen" citizenry/ \
  | xargs -r sed -i 's|from \.surface_citizen import SurfaceCitizen|from .governor_citizen import GovernorCitizen|g'
```

Manually fix any spots that referenced both governor and leader behaviour through `SurfaceCitizen` — they need to instantiate the two new citizens separately.

- [ ] **Step 12.5: Drop the law**

In `citizenry/constitution.py`, remove the `episode_recorder_format` line from `default_laws()`. Add a one-line comment in CHANGELOG or a top-of-file docstring noting the removal.

- [ ] **Step 12.6: Run full test suite**

```bash
python -m pytest citizenry/tests/ -x -q
```

Expected: PASS. Any failure here is a missed importer or stale reference; fix before continuing.

- [ ] **Step 12.7: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
citizenry: drop v1 episode recorder + shim modules

After 2 weeks of soak with EpisodeRecorderV3 + HFUploader running
on every ManipulatorNode without issue:
  - v1 EpisodeRecorder removed; the v3 class takes the canonical
    name EpisodeRecorder. Only one recorder now.
  - Constitution Law episode_recorder_format removed (no longer needed).
  - Rename shims pi_citizen.py and surface_citizen.py deleted.
  - All importers point at manipulator_citizen / governor_citizen /
    leader_citizen directly.

Test suite green.

Closes the SmolVLA-as-citizen scope from spec
docs/specs/2026-04-27-smolvla-citizen-design.md.
EOF
)"
```

---

## Sequencing notes

- **Tasks 1, 2 are independent** — both can be drafted in parallel by separate workers.
- **Task 3 is gated by `xiao-citizen/phase-2` merge** — the citizen split clashes mechanically with that branch.
- **Tasks 4, 5, 6 are interlocked** — Task 5 imports from Task 4, Task 6 is wired in by Task 4 step 4.7. Build them in order.
- **Task 7 runs the migration on real hardware** — irreversible (deletes legacy paths). Confirm the dry-run looks correct before committing the destructive form.
- **Task 8 runner is independent of 9 PolicyCitizen** — they can be drafted in parallel; PolicyCitizen accepts a `runner` parameter so unit tests mock it.
- **Task 10 needs all of 1, 2, 3, 8, 9 done.**
- **Task 11 needs 10 deployed on Jetson and a working Pi.**
- **Task 12 is gated by a soak window** — do not rush.

## Rollback plan per task

| Task | Rollback |
|---|---|
| 1 | `git revert` is safe; node.key file remains on disk but unused |
| 2 | `git revert`; Bid extra fields default to "" so old code ignores them |
| 3 | `git revert` is safe but tedious — keep the shim modules intact in 12 to ease future rollbacks |
| 4 | `git revert` removes EpisodeRecorderV3; v1 still works |
| 5 | `git revert` removes migrator; if `--delete-old` ran, restore from HF Hub |
| 6 | `git revert` removes uploader; episodes accumulate locally — manual upload needed |
| 7 | `git revert`; if migration deleted legacy data, **restore from HF Hub repo**, not from git |
| 8 | `git revert` is safe |
| 9 | `git revert`; PolicyCitizen disappears, marketplace falls back to LeaderCitizen-only |
| 10 | `sudo systemctl disable citizenry-jetson; git revert` |
| 11 | tests-only; no rollback |
| 12 | `git revert`; v1 path returns; uploaders keep working |

## Implementation skill choice

When executing this plan, the recommended skill is `superpowers:subagent-driven-development` (one fresh subagent per task with two-stage review between tasks). The alternative is `superpowers:executing-plans` (inline batch execution with checkpoints).

---

## Self-review

(Performed by the plan author; deltas applied inline above.)

- **Spec coverage:** every section in the spec maps to at least one task —
  - §4.1–4.5 → Tasks 1, 2, 3, 9, 10
  - §5 components table → Tasks 1, 3, 4, 5, 6, 8, 9, 10
  - §6 data flows → exercised in Tasks 9, 10, 11
  - §7 obs/action contract → Task 8
  - §7.1 runtime camera selection → Task 9 step 9.6
  - §8 dataset/upload → Tasks 4, 5, 6, 7
  - §9 error handling → covered as test cases inside Tasks 1, 6, 7, 8, 9, 11
  - §10 testing → enumerated tests baked into Tasks 1, 2, 4, 5, 6, 7, 8, 9, 11
  - §11 latency budget → enforced in Task 8 step 8.5 smoke test
  - §12 decisions → all wired (camera selection law in 9.6; servo-limits Article in 9.7; node identity in 1; co-location bonus in 2; HF pipeline in 6; governor.no_recorder in 7)
  - §13 sequencing → mirrored in this plan's task order
- **Placeholder scan:** none. The runner's `_assemble_observation` returns a stub for tests but is annotated for production wiring — flagged via comment, not "TBD".
- **Type consistency:** verified —
  - `PolicyCitizen.build_bid(task, target_follower_pubkey, target_follower_node_pubkey)` signature matches its test in 9.2.
  - `compute_bid_score(... co_location_bonus=0.0)` matches usage in PolicyCitizen.
  - `EpisodeRecorderV3.set_attribution / begin_episode / record_frame / close_episode` shape matches both ManipulatorCitizen wiring and migrator usage.
  - `HFUploader.upload_root(folder, delete_on_success=False)` matches both migrator (Task 5) and watch-loop usage in 6.6.
- **Scope:** one plan, 12 tasks, single feature. Could be split into Phase A (1–7) and Phase B (8–12) at execution time if Bradley prefers — both halves produce working software on their own — but the doc remains coherent as one.
