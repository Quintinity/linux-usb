# Citizenry Usability Plan — Make It Demo-able + Onboarding-able

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Take the citizenry from "operationally live but invisible to anyone outside Bradley's head" to "demonstrable end-to-end, self-explanatory to a fresh user, and easy to extend with new devices."

**Architecture:** Three tracks of work that share one branch. Track A is documentation + CLI (no protocol changes). Track B closes the only-PolicyCitizen-stub-observation gap so SmolVLA actually drives an arm with real input — required for Track A to demo anything real. Track C wires the attribution audit trail (the Quintinity-strategic "auditable AI" piece that's currently null). Track D opens the system to non-Pi/non-Jetson devices via a single interactive wizard.

**Tech stack:** Same as smolvla-citizen plan — Python 3.10+/3.12, asyncio, NaCl Ed25519, lerobot, huggingface_hub, pytest. Plus bash for the device wizard.

**Branch strategy:** Single feature branch `citizenry-usability` off `main`. Tasks land as separate commits. Merge to main when all four tracks are green or when Bradley calls it.

**Spec:** This document is the spec. The 7 items here are concrete enough that a separate spec would be redundant — each task has a clear acceptance test.

---

## Why this plan exists

After the SmolVLA-as-citizen integration shipped (commits `df8672d`..`3a66561`), three honest gaps remain:

1. **The robot doesn't actually move yet.** PolicyCitizen.execute_task assembles a stub observation of zero-pixel images and feeds that to SmolVLA. The model runs; it predicts actions on black frames; nothing meaningful happens. The whole SmolVLA loop is an unverified mechanism.
2. **A new user can't tell what this is.** No top-level README, no quickstart, no demo command, no curated task vocabulary. The repo's surface area presents as scattered specs/plans/research.
3. **Auditability is broken at the data layer.** Attribution sidecars in v3 episodes always write `null` for `policy_pubkey`, `governor_pubkey`, `constitution_hash`. The data tells you what was recorded, but not under whose governance or which policy — directly counter to Quintinity's "auditable AI for manufacturing" positioning.

This plan closes those.

A fourth gap — adding new device types to the mesh — is included as Track D because the persona auto-detection's role list is hardcoded to four categories and there's no template for "what if someone brings a Mac mini or laptop to the lab?"

---

## Track A — User Onboarding

### Task A1: Top-level `README.md`

**Files:**
- Create: `README.md` (repo root — currently absent at `/home/bradley/linux-usb/`)

**Goal:** A new user clones the repo, opens `README.md`, and within 5 minutes knows: (a) what this is, (b) what it can do, (c) how to run the demo, (d) where to read more.

- [ ] **Step A1.1: Outline**

The README contains, in order:
1. **One-line elevator pitch.** ~20 words. "Distributed robotics OS where every piece of hardware is an autonomous Ed25519-signed citizen sharing a constitution and a marketplace."
2. **Mesh diagram.** ASCII art showing Surface (governor) ↔ Pi (manipulator+perception) ↔ Jetson (policy host) connected over `239.67.84.90:7770` multicast.
3. **What it does today.** 5-line bullet list of capabilities (matches the "What the system does today" table from `docs/plans/2026-04-29-citizenry-usability.md`).
4. **Quickstart.** Three commands a new user can paste:
   ```bash
   git clone <repo> ~/linux-usb && cd ~/linux-usb
   bash setup.sh     # Surface bootstrap
   # Say "continue setup" to Claude when prompted.
   ```
   Plus a single command to run the demo (filled in once Task A3 lands).
5. **Architecture.** 5 sentences pointing at `docs/specs/2026-04-27-smolvla-citizen-design.md` and `citizenry/SOUL.md` / `GROWTH.md` for depth.
6. **Adding a device.** Pointer to `bash scripts/add-device.sh` (filled in once Task C1 lands).
7. **For Quintinity context.** One paragraph + link to the strategy doc (private; just a name).

- [ ] **Step A1.2: Write it**

Plain markdown, no fancy formatting. Aim for ~150 lines, not 500. Easier to keep accurate.

- [ ] **Step A1.3: Verify by handing to a fresh observer**

If you have anyone you can show this to — Philippe, future-you-with-coffee — open the README on a screen and ask: "in 5 minutes, can you tell me what this does and how to run it?" If no, the README is wrong; fix it.

- [ ] **Step A1.4: Commit**

```bash
git add README.md
git commit -m "docs: top-level README — purpose, mesh diagram, quickstart, pointers"
```

### Task A3: `governor_cli demo` command

**Files:**
- Modify: `citizenry/governor_cli.py` (add a `demo` subcommand to the existing CLI)
- Create: `citizenry/tests/test_governor_cli_demo.py`

(A2 — separate `inventory` CLI — folded into A3 since `demo` opens with an inventory printout.)

**Goal:** `python -m citizenry.governor_cli demo` walks through one full marketplace round end-to-end, narrates what's happening, and ends with "the arm waved" or "no arm attached, but here's what would have happened."

- [ ] **Step A3.1: Test (write first)**

```python
# citizenry/tests/test_governor_cli_demo.py
"""Tests for the governor_cli demo command."""

from unittest.mock import MagicMock, patch
import pytest

from citizenry.governor_cli import run_demo  # the new function we're building


@pytest.mark.asyncio
async def test_run_demo_prints_inventory_and_emits_task(capsys):
    surface = MagicMock()
    surface.neighbors = {
        "pi_pk": MagicMock(name="pi-inference", citizen_type="manipulator", capabilities=["6dof_arm"]),
        "jetson_pk": MagicMock(name="jetson-policy", citizen_type="policy", capabilities=["policy.imitation"]),
    }
    fake_task = MagicMock(id="t1", status=MagicMock(value="completed"), assigned_to="jetson_pk", created_at=0.0, completed_at=2.0)
    surface.create_task.return_value = fake_task
    surface.marketplace.tasks = {"t1": fake_task}
    with patch("citizenry.governor_cli.create_task_and_wait") as wait_mock:
        wait_mock.return_value = {"task_id": "t1", "winner_pubkey": "jetson_pk", "winner_role": "policy", "status": "completed", "duration_s": 2.0}
        await run_demo(surface, task_type="basic_gesture/wave")
    out = capsys.readouterr().out
    assert "inventory" in out.lower() or "neighbors" in out.lower()
    assert "jetson-policy" in out
    assert "completed" in out
```

- [ ] **Step A3.2: Implement**

```python
async def run_demo(surface, task_type: str = "basic_gesture/wave") -> None:
    """End-to-end demo: print inventory, emit a task, narrate outcome."""
    print("=" * 60)
    print("citizenry demo — basic marketplace round")
    print("=" * 60)
    print(f"\nGovernor: {surface.name} [{surface.pubkey[:8]}]")
    print(f"\nNeighbors ({len(surface.neighbors)}):")
    for pk, n in surface.neighbors.items():
        caps = getattr(n, "capabilities", [])
        print(f"  {n.name} [{pk[:8]}] type={getattr(n, 'citizen_type', '?')} caps={caps}")
    print(f"\nProposing task: {task_type!r}")
    result = await create_task_and_wait(
        surface=surface,
        task_type=task_type,
        params={},
        bid_window_s=2.5,
        completion_timeout_s=30.0,
    )
    print("\n--- result ---")
    for k, v in result.items():
        print(f"  {k}: {v}")
    if result["status"] == "completed":
        print(f"\n✓ task completed by {result['winner_role']} in {result['duration_s']:.2f}s")
    else:
        print(f"\n✗ task did not complete: status={result['status']}")
```

Wire as a subcommand in the existing `_cli()` argparse. Add `demo` mode that constructs a Surface (or attaches to a running governor — start with the simpler "constructs a fresh governor for the demo" path).

- [ ] **Step A3.3: Acceptance**

Run on Surface against the live mesh:
```bash
source ~/lerobot-env/bin/activate
python -m citizenry.governor_cli demo --task-type "basic_gesture/wave"
```
Expected: prints inventory (sees pi-inference, jetson-policy), emits task, gets a winner back, prints completion. If no arm is physically connected, the task may fail at execute_task — that's OK; the demo's job is to surface that fact, not to fake success.

- [ ] **Step A3.4: Commit**

```bash
git add citizenry/governor_cli.py citizenry/tests/test_governor_cli_demo.py
git commit -m "governor_cli: add 'demo' subcommand — inventory + one marketplace round"
```

---

## Track B — Make Robot Stuff Actually Work

### Task B1: Real `_assemble_observation` in PolicyCitizen

**Files:**
- Modify: `citizenry/policy_citizen.py` (replace stub with real camera-frame caching + state lookup)
- Create: `citizenry/observation_cache.py` (small dedicated module for caching ADVERTISE'd / REPORT'd frames)
- Modify: `citizenry/citizen.py` (add hook so subclasses can intercept ADVERTISE bodies that contain image data)
- Create: `citizenry/tests/test_observation_cache.py`

**Goal:** When PolicyCitizen.execute_task fires, it pulls the latest frame from each named camera neighbor and the latest joint state from the targeted follower's REPORT body, assembles them into the SmolVLA input dict, and only THEN calls `runner.act()`. Currently it returns zeros.

- [ ] **Step B1.1: Test the cache (TDD)**

```python
# citizenry/tests/test_observation_cache.py
import numpy as np
from citizenry.observation_cache import ObservationCache


def test_cache_stores_and_retrieves_frame_by_camera_role():
    cache = ObservationCache()
    frame = np.zeros((96, 128, 3), dtype=np.uint8)
    cache.update_frame(camera_role="wrist", frame=frame, timestamp=1.0)
    out = cache.latest_frame("wrist", max_age_s=5.0)
    assert out is not None
    assert out.shape == frame.shape


def test_stale_frame_returns_none():
    cache = ObservationCache()
    cache.update_frame(camera_role="wrist", frame=np.zeros((48, 64, 3), dtype=np.uint8), timestamp=0.0)
    out = cache.latest_frame("wrist", max_age_s=0.1, now=10.0)
    assert out is None


def test_cache_stores_state_per_follower_pubkey():
    cache = ObservationCache()
    cache.update_state(follower_pubkey="abc", state=np.array([1, 2, 3, 4, 5, 6]), timestamp=1.0)
    out = cache.latest_state("abc", max_age_s=5.0)
    assert out is not None
    assert list(out) == [1, 2, 3, 4, 5, 6]
```

- [ ] **Step B1.2: Implement ObservationCache**

```python
# citizenry/observation_cache.py
"""Per-citizen cache of the latest camera frames + follower states.

PolicyCitizen feeds this to SmolVLA. Updates come from neighbor ADVERTISE
bodies (frame: bytes) and REPORT bodies (state: list[int]).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np


@dataclass
class _FrameEntry:
    frame: np.ndarray
    timestamp: float


@dataclass
class _StateEntry:
    state: np.ndarray
    timestamp: float


class ObservationCache:
    def __init__(self):
        self._frames: dict[str, _FrameEntry] = {}   # keyed by camera role
        self._states: dict[str, _StateEntry] = {}   # keyed by follower pubkey

    def update_frame(self, camera_role: str, frame: np.ndarray, timestamp: float | None = None) -> None:
        self._frames[camera_role] = _FrameEntry(frame=frame, timestamp=timestamp or time.time())

    def update_state(self, follower_pubkey: str, state, timestamp: float | None = None) -> None:
        s = state if isinstance(state, np.ndarray) else np.array(state)
        self._states[follower_pubkey] = _StateEntry(state=s, timestamp=timestamp or time.time())

    def latest_frame(self, camera_role: str, max_age_s: float = 1.0, now: float | None = None) -> np.ndarray | None:
        e = self._frames.get(camera_role)
        if e is None:
            return None
        if (now or time.time()) - e.timestamp > max_age_s:
            return None
        return e.frame

    def latest_state(self, follower_pubkey: str, max_age_s: float = 1.0, now: float | None = None) -> np.ndarray | None:
        e = self._states.get(follower_pubkey)
        if e is None:
            return None
        if (now or time.time()) - e.timestamp > max_age_s:
            return None
        return e.state
```

- [ ] **Step B1.3: Wire ObservationCache into Citizen base class**

Add a default `self.observations = ObservationCache()` in `Citizen.__init__`. Add `_handle_advertise` and `_handle_report` overrides that sniff body for `frame` (base64-encoded JPEG) or `joint_positions` and update the cache accordingly. Decode JPEG → numpy via cv2.

- [ ] **Step B1.4: Replace PolicyCitizen._assemble_observation**

```python
async def _assemble_observation(self, target_follower_pubkey: str) -> dict | None:
    primary_role, secondary_role = self.camera_role_pair()
    primary = self.observations.latest_frame(primary_role, max_age_s=0.5)
    secondary = self.observations.latest_frame(secondary_role, max_age_s=0.5)
    state = self.observations.latest_state(target_follower_pubkey, max_age_s=0.5)
    # All three required for a meaningful observation. None means stale/missing.
    if primary is None or secondary is None or state is None:
        return None
    return {
        f"observation.images.{primary_role}": primary,
        f"observation.images.{secondary_role}": secondary,
        "observation.state": state.astype(np.float32),
    }
```

- [ ] **Step B1.5: Update execute_task call site**

The existing call was `obs = await self._assemble_observation()` — now passes `target_follower_pubkey`. Tests already assert behaviour when `obs is None` (stale → skip).

- [ ] **Step B1.6: Update PolicyCitizen tests**

Existing tests stub the runner. Add a new test:
```python
@pytest.mark.asyncio
async def test_execute_task_skips_when_observation_stale(tmp_path, monkeypatch):
    # Construct a PolicyCitizen with no neighbor ADVERTISE'd frames yet.
    # _assemble_observation returns None.
    # execute_task's loop sleeps and retries; cancel and assert no teleop frames sent.
    ...
```

- [ ] **Step B1.7: Acceptance**

```bash
python -m pytest citizenry/tests/test_observation_cache.py citizenry/tests/test_policy_citizen.py -v
```
Target: 11+ passes.

- [ ] **Step B1.8: Commit**

```bash
git add citizenry/observation_cache.py citizenry/policy_citizen.py citizenry/citizen.py citizenry/tests/test_observation_cache.py citizenry/tests/test_policy_citizen.py
git commit -m "policy_citizen: real observation assembly via ObservationCache (closes Task 9 stub TODO)"
```

### Task B2: Demo task vocabulary

**Files:**
- Create: `citizenry/tasks_catalog.py` (curated task definitions)
- Modify: `citizenry/governor_cli.py` (the `demo` subcommand picks from the catalog)

**Goal:** Curate a small set of demo tasks that the fleet can actually execute. Each task has: name, description, required_capabilities, required_skills, suggested_winner_role. Used by the demo command + future tutorials.

- [ ] **Step B2.1: Catalog**

```python
# citizenry/tasks_catalog.py
"""Curated demo tasks. Single source of truth for what the fleet knows how to do."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TaskTemplate:
    name: str                 # e.g. "basic_gesture/wave"
    description: str          # human-readable
    required_capabilities: list[str]
    required_skills: list[str]
    suggested_winner_role: str    # "manipulator", "policy", "leader" etc.
    estimated_duration_s: float


CATALOG: list[TaskTemplate] = [
    TaskTemplate(
        name="basic_gesture/wave",
        description="Manipulator arm waves once. No camera input required; deterministic motion.",
        required_capabilities=["6dof_arm"],
        required_skills=["basic_gesture"],
        suggested_winner_role="manipulator",
        estimated_duration_s=4.0,
    ),
    TaskTemplate(
        name="pick_and_place",
        description="Drive a pick-and-place behavior. SmolVLA-driven if available; teleop fallback otherwise.",
        required_capabilities=["6dof_arm"],
        required_skills=["pick_and_place"],
        suggested_winner_role="policy",
        estimated_duration_s=20.0,
    ),
    TaskTemplate(
        name="capture_frame",
        description="A camera citizen captures a single frame and reports it. Useful smoke test.",
        required_capabilities=["camera"],
        required_skills=["frame_capture"],
        suggested_winner_role="camera",
        estimated_duration_s=1.0,
    ),
]


def get(name: str) -> TaskTemplate | None:
    return next((t for t in CATALOG if t.name == name), None)
```

- [ ] **Step B2.2: Demo wires to catalog**

`governor_cli demo --task-type` defaults to `basic_gesture/wave` (lowest barrier to actual movement). `demo --list-tasks` prints the catalog.

- [ ] **Step B2.3: Test**

```python
def test_catalog_has_at_least_three_tasks():
    from citizenry.tasks_catalog import CATALOG
    assert len(CATALOG) >= 3

def test_get_returns_task_by_name():
    from citizenry.tasks_catalog import get
    t = get("basic_gesture/wave")
    assert t is not None
    assert "wave" in t.description.lower()
```

- [ ] **Step B2.4: Commit**

```bash
git add citizenry/tasks_catalog.py citizenry/governor_cli.py citizenry/tests/test_tasks_catalog.py
git commit -m "citizenry: tasks_catalog as single source of demo-task definitions"
```

### Task B3: Two missing E2E integration tests

**Files:**
- Create: `citizenry/tests/integration/test_marketplace_e2e_local.py`
- Create: `citizenry/tests/integration/test_marketplace_e2e_cross_node.py`

**Goal:** Close the gated-test gap from the SmolVLA plan. Verify the full chain (governor → marketplace → bid → SmolVLA → send_teleop → ManipulatorCitizen → episode recorded → HF upload) end to end.

- [ ] **Step B3.1: local test (Jetson hosts everything)**

Per spec Task 11. Gated by `LEROBOT_INTEGRATION=1` env. Submits a `pick_and_place` task via `create_task_and_wait`, asserts `winner_role == "policy"` and `winner_node == follower_node`, verifies a v3 parquet lands then disappears (uploaded + deleted within 60s).

- [ ] **Step B3.2: cross-node test**

Pi has arms, Jetson policy bids and wins. Asserts `winner_node != follower_node`. Episode lands on Pi (the follower's node), not Jetson.

Both tests follow the layout in the SmolVLA plan §10. Use `governor_cli.create_task_and_wait` (already exists from Task 11 of that plan).

- [ ] **Step B3.3: Hardware run, manual**

These run on real hardware with `LEROBOT_INTEGRATION=1 pytest`. Document the run results in this commit's message. If they fail because the arms aren't physically attached, the failure mode is honest and recorded.

- [ ] **Step B3.4: Commit**

```bash
git add citizenry/tests/integration/
git commit -m "tests: gated e2e marketplace tests (local + cross-node) — closes SmolVLA plan gap"
```

---

## Track C — Device Onboarding

### Task C1: `add-device.sh` interactive wizard

**Files:**
- Create: `scripts/add-device.sh`
- Modify: `scripts/claude-persona-refresh.sh` (extend role detection list)

**Goal:** A new device (any kind) runs `bash <(curl ...)` or `bash add-device.sh` from a cloned repo, picks a role from a menu, and ends up provisioned + joined to the mesh + persona auto-set.

- [ ] **Step C1.1: Define role catalog**

```bash
ROLES=(
  "GovernorNode      — Constitution + marketplace coordination, no arms, no recorder"
  "ManipulatorNode   — leader+follower arms attached, hosts ManipulatorCitizen + LeaderCitizen"
  "PolicyNode        — CUDA host running SmolVLA or other VLAs, bids on manipulation"
  "PerceptionNode    — non-CUDA accelerator (Hailo, Coral, etc.) running detector models"
  "ObserverNode      — ephemeral; joins mesh read-only for monitoring/dashboard"
  "GenericCompute    — bare compute, no specific role yet (placeholder)"
)
```

- [ ] **Step C1.2: Wizard flow**

```bash
# 1. Detect basics: hostname, OS, python, hardware (cameras/accelerators/buses)
# 2. Print detected hardware. Suggest a role based on detection (e.g. /dev/hailo0 → PerceptionNode).
# 3. Prompt: "Use suggested role <X>? [Y/n] or pick number 1-6:"
# 4. Install steps based on chosen role:
#    - venv (lerobot-env) if not present
#    - HF token via `hf auth login` (if uploads needed)
#    - systemd unit pointing at the right run_*.py entry
#    - persona watcher
# 5. Start the service, watch journal for "citizen born".
```

The wizard delegates to existing setup scripts where possible (`pi-setup.sh`, `jetson-setup.sh`) for known hardware combos. For new combos, it generates a generic systemd unit on the fly.

- [ ] **Step C1.3: Persona script extends to handle new roles**

Add `PerceptionNode`, `ObserverNode`, `GenericCompute` cases to `claude-persona-refresh.sh`'s narrative-block switch.

- [ ] **Step C1.4: Acceptance**

Run `bash scripts/add-device.sh` on a test machine (Bradley's laptop or a fresh Pi). Pick a role. Verify it ends with a citizen on the mesh and `~/CLAUDE.md` written.

- [ ] **Step C1.5: Commit**

```bash
git add scripts/add-device.sh scripts/claude-persona-refresh.sh
git commit -m "scripts: add-device.sh interactive wizard + extended role catalog"
```

---

## Track D — Audit Trail

### Task D1: Attribution sidecar wiring

**Files:**
- Modify: `citizenry/manipulator_citizen.py` (set actual values when constructing the recorder)
- Modify: `citizenry/citizen.py` (expose `constitution_hash` property)

**Goal:** Episodes' attribution sidecar carries non-null `policy_pubkey`, `governor_pubkey`, `constitution_hash`. Directly serves Quintinity's "auditable AI" pitch.

- [ ] **Step D1.1: Track active policy on ManipulatorCitizen**

When ManipulatorCitizen accepts a teleop frame with `target_follower_pubkey` matching its own pubkey, record `env.sender` as `self._active_policy_pubkey`. When teleop expires (TTL_TELEOP), clear it.

- [ ] **Step D1.2: Constitution hash**

Add to `Citizen`:
```python
@property
def constitution_hash(self) -> str | None:
    if not self.constitution:
        return None
    import hashlib, json
    return hashlib.sha256(json.dumps(self.constitution, sort_keys=True).encode()).hexdigest()[:16]
```

- [ ] **Step D1.3: Stamp attribution at every record_frame fan-out site**

The recorder's `set_attribution()` is called at construction time, but `_active_policy_pubkey` changes mid-episode. Update set_attribution to be cheap-callable per episode (or call it at `begin_episode` time inside ManipulatorCitizen's call wrapper).

- [ ] **Step D1.4: Test**

```python
def test_attribution_sidecar_carries_real_pubkeys(tmp_path):
    # Construct a ManipulatorCitizen with a known governor and active policy.
    # Begin + close an episode.
    # Read attribution.json — assert all four fields are non-null and match.
    ...
```

- [ ] **Step D1.5: Commit**

```bash
git add citizenry/manipulator_citizen.py citizenry/citizen.py citizenry/tests/test_attribution.py
git commit -m "citizenry: attribution sidecar carries policy/governor/constitution provenance"
```

---

## Sequencing

```
Day 1 (mostly parallel):
  A1 (README) — independent, do first or last
  D1 (attribution) — independent, small
  B2 (catalog) — independent, small

Day 2 (B1 unblocks the rest):
  B1 (real observation) — required for B3 and meaningful A3

Day 3:
  A3 (demo CLI) — depends on B1 + B2
  B3 (e2e tests) — depends on B1 + hardware available

Day 4 (independent):
  C1 (add-device wizard)

Total: ~4 days of work, ~7 subagent dispatches.
```

## Out of scope (intentionally)

- Bimanual / multi-arm policies (different model, different spec)
- Inference Endpoints / cloud SmolVLA (this work is local-first)
- Web dashboard / visualization (covered separately by `dashboard.py`; not a citizen problem)
- Federated training across remote operators (research, not product)
- Replacing the `governor_cli` REPL (it works; just adding a `demo` subcommand)

## Acceptance for this plan as a whole

The plan is "done" when:
1. A new collaborator can clone the repo, read README.md, run `bash setup.sh`, then `python -m citizenry.governor_cli demo`, and watch a citizen do something visible.
2. SmolVLA on Jetson actually drives a real arm (not zero-image stubs) given camera feeds from the mesh.
3. The two e2e integration tests exist and pass on hardware (or fail honestly with a clear "no arm attached" reason).
4. `bash scripts/add-device.sh` works for at least one new device type Bradley brings to the workshop (e.g. another Pi, a Mac mini, a desktop).
5. Every v3 episode's attribution.json carries real (non-null) `policy_pubkey`, `governor_pubkey`, `constitution_hash`.
6. Memory entry `project_smolvla_citizen_status.md` is updated with: "all SmolVLA plan follow-ups closed."

## Connection to Quintinity strategy

Three of these tasks directly serve the EMEX 2026 trade-show forcing function:

- **A1 + A3** — "show me what this does" is the question every booth visitor asks. Without these, the citizenry is invisible. With them, you can demo end-to-end in 60 seconds.
- **D1** — "auditable AI" is Quintinity's core pitch. An episode dataset where every recording carries crypto-signed provenance (which model, which governor, which constitution version) is the artifact that makes the pitch concrete.

Tasks B1, B3, C1 are infrastructure work that supports those — they don't pitch directly but they make the pitches *true*.

Bradley to decide which tracks ship pre-EMEX vs post-EMEX. My read: A1 + A3 + D1 are the EMEX critical path; B1 is required for A3 to actually demo; B3 + C1 can slip to post-show.
