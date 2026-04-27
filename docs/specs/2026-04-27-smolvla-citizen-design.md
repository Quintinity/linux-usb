# SmolVLA-as-Citizen — Design Spec

**Date:** 2026-04-27
**Author:** Brainstormed with Claude (Opus 4.7) at Bradley's request
**Status:** Draft for review — not yet approved
**Scope chosen:** B from brainstorm (Inference + LeRobotDataset v3 migration as precursor) + **C from question 2** (generalize for N follower arms across N nodes from day one)

---

## 1. Goal

Make Hugging Face's SmolVLA 450M a first-class citizen in the citizenry mesh, bid-able through the existing task marketplace, **deployable across a multi-node fleet** in which each ManipulatorNode hosts a co-located leader+follower arm pair. Migrate `~/citizenry-datasets/` to LeRobotDataset v3 format and add a per-node Hugging Face upload pipeline so episodes auto-upload on close and the local copy is freed.

This is the first spec where (a) a *learned* policy participates in the marketplace alongside human teleop and hand-coded routines, and (b) the fleet topology is generalized to N nodes with co-located leader+follower pairs rather than the original Surface-leader / Pi-follower split.

## 2. Non-goals (explicitly out of scope)

The following are intentionally deferred to follow-up specs so this one stays small enough to ship:

- **Fine-tuning** SmolVLA on local SO-101 data (next spec — depends on v3 migration here)
- **Latent safety filter / OOD veto** (option F from brainstorm)
- **ASkDAgger active teleop** loop (option E)
- **Hailo-8L perception citizen** (option B from question 1; separate spec)
- **Multi-fleet federation / policy-merging across remote owners**
- **Qwen2.5-VL nightly auto-captioning**
- **Bimanual VLA models** (need physical 2-arm follower; SmolVLA is single-arm)

## 3. Why this scope

`A` (inference only) leaves a "demo policy" that can't be improved. `B` adds the dataset migration that *every* downstream spec (fine-tuning, ASkDAgger, federation) requires anyway. Adopting `C` (generalized N-node topology) early avoids a painful retrofit later — node identity, co-location bidding, and the HF upload pipeline all touch the same data model, so doing them once now is cheaper than refactoring after the first single-arm version ships. The HF upload-and-delete pipeline keeps each ManipulatorNode's storage bounded; without it, episode growth would saturate Pi/Jetson SD cards within weeks.

## 4. Architecture

### 4.1 Node-based topology (decided 2026-04-27)

The fleet is composed of **nodes**, each playing one of two roles:

- **ManipulatorNode** — a machine with **both** a leader arm and a follower arm physically attached. Self-contained for human teleop: leader-position reads and follower-position writes happen entirely on-host with no network in the critical path. Examples: Jetson Orin Nano with leader+follower attached, Pi 5 with leader+follower attached.
- **GovernorNode** — the Surface Pro 7. No arms, no recorder. Hosts Governor (constitutional ratification, marketplace coordination), dashboard, CLI.

The fleet may have N ManipulatorNodes (today: 1; near-future: 2 with the Pi). One GovernorNode is sufficient.

### 4.2 Node identity

To support cross-node co-location detection, each node carries a **node-level Ed25519 keypair** at `~/.citizenry/node.key`. Every citizen spawned by a node entry point (`run_jetson.py`, `run_pi.py`, `run_surface.py`) inherits a `node_pubkey` field in its genome and includes it in ADVERTISE bodies. Two citizens with the same `node_pubkey` are guaranteed co-located.

This is additive — per-citizen pubkeys remain the protocol-level identity; `node_pubkey` is a co-location hint, not an authorization channel.

### 4.3 Citizen roster per node

| Node type | Spawned citizens | Notes |
|---|---|---|
| ManipulatorNode (Jetson) | LeaderCitizen, ManipulatorCitizen, CameraCitizens, **PolicyCitizen** | PolicyCitizen only spawns where accelerator can host SmolVLA |
| ManipulatorNode (Pi) | LeaderCitizen, ManipulatorCitizen, CameraCitizens | No PolicyCitizen on Pi — Hailo-8L can't host VLAs (separate spec for Hailo perception role) |
| GovernorNode (Surface) | GovernorCitizen, DashboardCitizen | No arms, no recorder |

`LeaderCitizen` is new. The existing `surface_citizen.py` mixed leader-reading and governor logic; we split them so any node can host either independently. `ManipulatorCitizen` generalizes today's `pi_citizen.py` (renamed; same code, just hardware-agnostic).

### 4.4 SmolVLA cross-node targeting (decided 2026-04-27)

When the Governor proposes a manipulation Task, every PolicyCitizen evaluates eligibility for each known ManipulatorCitizen on the network. Bids include the target follower's pubkey via a new `params.follower_pubkey` Task field. The Governor selects the winner using existing bid scoring plus a **co-location bonus**:

```
score = compute_bid_score(...) + co_location_bonus
co_location_bonus = +0.15 if bidder.node_pubkey == follower.node_pubkey else 0
```

Effects:
- A Jetson PolicyCitizen targeting its locally-attached follower wins by default — tightest loop.
- If the local follower is unhealthy, busy, or absent, the same PolicyCitizen still bids on remote followers; teleop frames cross the network with the existing `TTL_TELEOP=0.1` envelope.
- A node with arms but no compute (Pi+arms) can be SmolVLA-driven from the Jetson when needed, at the cost of LAN latency.

This is one additive change to `marketplace.Task`: a `params.follower_pubkey` field. Bidders that don't match the targeted follower (or that target nobody) are filtered out by `can_citizen_bid` before scoring.

### 4.5 Action source flip

When a PolicyCitizen wins a task targeting a specific follower:
- That follower's ManipulatorCitizen accepts teleop frames from the policy's pubkey for task duration.
- The local LeaderCitizen continues reading positions but its frames are not applied while the policy is in command (the human can still grab the leader; positions are still recorded as observation context).
- On task completion or failure, the action source defaults back to LeaderCitizen.

## 5. Components

| File | Status | Purpose |
|---|---|---|
| `citizenry/node_identity.py` | **new** | Generate/load node-level Ed25519 keypair at `~/.citizenry/node.key`; expose `get_node_pubkey()` for genome inheritance |
| `citizenry/leader_citizen.py` | **new** | Reads leader arm positions; emits teleop PROPOSE frames; can run on any node with leader hardware (extracted from `surface_citizen.py`) |
| `citizenry/manipulator_citizen.py` | **rename + refactor** | Was `pi_citizen.py`; now hardware-agnostic; runs on Jetson or Pi |
| `citizenry/governor_citizen.py` | **rename + refactor** | Was the governor portion of `surface_citizen.py`; now arms-free |
| `citizenry/policy_citizen.py` | **new** | Bids on manipulation tasks; calls into runner; emits action frames; co-located with target follower preferred |
| `citizenry/smolvla_runner.py` | **new** | Wraps `lerobot.policies.smolvla` load/forward; produces action chunks; not citizenry-aware |
| `citizenry/run_jetson.py` | **new** | Jetson entry point; surveys hardware; spawns LeaderCitizen + ManipulatorCitizen + CameraCitizens + PolicyCitizen |
| `citizenry/dataset_v3_migrate.py` | **new** | One-shot migrator: legacy Surface `~/.citizenry/episodes/` + `~/citizenry-datasets/` → LeRobotDataset v3 + HF upload + delete-local |
| `citizenry/episode_recorder.py` | **modified** | Adds `EpisodeRecorderV3` writer; old v1 writer kept behind a Constitution flag for one transition window; **disabled entirely on GovernorNode** |
| `citizenry/hf_upload.py` | **new** | Async per-episode upload to Hugging Face Hub; verify; delete local on success; retry queue on failure |
| `citizenry/skills.py` | **modified** | Adds `default_policy_skills()` factory |
| `citizenry/genome.py` | **modified** | Adds `node_pubkey` field |
| `citizenry/constitution.py` | **modified** | Adds Article forbidding policy actions outside ServoLimits; adds Laws for `episode_recorder_format`, `policy_citizen.observation_cameras`, `dataset.hf_repo_id`, `dataset.upload_after_episode`, `dataset.delete_after_upload`, `dataset.retry_interval_s`, `governor.recorder_enabled = false` |
| `citizenry/marketplace.py` | **modified** | Adds `co_location_bonus` to `compute_bid_score`; adds `params.follower_pubkey` filtering in `can_citizen_bid` |
| `citizenry/run_pi.py` | **modified** | Spawns LeaderCitizen if leader bus detected |
| `citizenry/run_surface.py` | **modified** | Spawns GovernorCitizen + DashboardCitizen only; episode recorder disabled by Constitution Law |
| `pi-setup.sh` / new `jetson-setup.sh` | **new/modified** | Provisioning + systemd unit `citizenry-jetson.service`; HF token install path |

Total new code: roughly 6 modules + tests; 6 modified; 2 renamed. Most are small (<300 lines).

## 6. Data flow

### 6.1 Local SmolVLA-driven task (Jetson hosts everything)

```
[Jetson — ManipulatorNode]
  ┌──────────────────────────────────────────────────────────────────┐
  │  CameraCitizen × 2 (active selection from N attached cams)       │
  │       │                                                          │
  │       ▼                                                          │
  │  PolicyCitizen ──→ smolvla_runner.act() ──→ action chunk         │
  │       │                                                          │
  │       ▼ (in-process / loopback multicast)                        │
  │       │                                                          │
  │  ManipulatorCitizen ── ServoLimits clamp ── follower servos      │
  │       │                                                          │
  │       ▼                                                          │
  │  EpisodeRecorderV3 writes to ~/citizenry-datasets/v3/            │
  │       │                                                          │
  │       ▼ on episode close                                         │
  │  HFUploader → Hugging Face Hub → verify → delete local           │
  └──────────────────────────────────────────────────────────────────┘

[Surface — GovernorNode]      (network)
  GovernorCitizen ratifies Constitution; runs marketplace; renders dashboard.
  No data flows through Surface in steady state.
```

End-to-end action latency: target <10ms (loopback only).

### 6.2 Cross-node SmolVLA-driven task (Jetson policy → Pi follower)

```
[Pi — ManipulatorNode]                       [Jetson — ManipulatorNode]
  CameraCitizen ─── ADVERTISE ──→            ◄── subscribe to Pi cams
                                              PolicyCitizen
  ManipulatorCitizen ─── REPORT ──→          ◄── subscribe to Pi REPORT
       ▲                                      │
       │                                      ▼
       └─── PROPOSE(teleop_frame) ◄─────────── action chunk ─→ emit
       │
       ▼
  ServoLimits clamp; servo write
  EpisodeRecorderV3 writes locally on Pi (the *follower's* node records)
       │
       ▼ on close
  HFUploader → HF Hub → verify → delete local on Pi
```

End-to-end action latency: 10–30ms LAN + Jetson inference; budget tight against `TTL_TELEOP=0.1`.

### 6.3 Human teleop on a single ManipulatorNode

```
[Jetson or Pi — ManipulatorNode]
  LeaderCitizen reads positions @ 60 FPS
       │
       ▼ (in-process)
  ManipulatorCitizen writes to follower
  EpisodeRecorderV3 captures frame → ~/citizenry-datasets/v3/
       │
       ▼ on episode close
  HFUploader → HF Hub → verify → delete local
```

The Surface is not in the action loop.

### 6.4 Where episodes are recorded

The follower's node records. PolicyCitizen on the Jetson driving a Pi follower causes the **Pi** to record the episode (the Pi is where the action lands and where telemetry originates). Per-episode metadata captures `policy_pubkey` (the source) and `node_pubkey` (the recorder), so attribution is unambiguous.

GovernorNode (Surface) **never** records — `governor.recorder_enabled = false` enforced by Constitution Law and verified at boot.

## 7. SmolVLA action / observation contract

SmolVLA `lerobot/smolvla_base` is pretrained on Hugging Face's SO-100/101 community dataset, so its action space is *expected* to align with the SO-101 follower's 6-joint absolute-position frame already used in `episode_recorder.py:31` (`MOTOR_NAMES`). Two items to verify against the model card before merging:

- **Observation shape:** wrist + base camera, normalized resolution, color channels (RGB vs BGR — OpenCV is BGR by default in citizenry).
- **Action units:** SmolVLA's checkpoint outputs (likely normalized [-1, 1] or radians); citizenry's `action_positions` are raw Feetech servo ticks (0–4095). The runner is responsible for the inverse mapping.

Mapping lives in `smolvla_runner.py` so policy_citizen stays unaware of it. If the contract turns out not to match, the runner is the only file that has to change.

### 7.1 Runtime camera selection

All on-fleet cameras (Pi CSI NoIR Wide, two XIAO wifi cams, plus any USB cams attached to the Jetson) remain available as observation sources at all times. PolicyCitizen picks **which two** to consume at runtime based on a Constitution Law:

```python
"policy_citizen.observation_cameras": ["xiao-cam-wrist", "pi-csi-base"]  # ordered: [primary, secondary]
```

Camera identity is resolved by mDNS-advertised name or by a `role` tag in the camera-citizen's genome. PolicyCitizen subscribes to the two named camera-citizens via the existing ADVERTISE/PROPOSE pattern and assembles the SmolVLA observation in `smolvla_runner.py`.

**Switching cameras at runtime:** Governor issues a `GOVERN` message with an updated Law. PolicyCitizen detects the change on its next constitution refresh, drops its current camera subscriptions, subscribes to the new pair, and continues without restart.

If the Law names a camera that isn't on the network, PolicyCitizen REPORTs `camera_unresolved`, refuses to bid, and waits for either the camera to come online or a new GOVERN.

## 8. Dataset v3 + per-node upload pipeline

### 8.1 Legacy migration (one-shot, on Surface)

Surface today holds `~/.citizenry/episodes/` (JSONL+JPEGs) and `~/citizenry-datasets/episode_000X/` (partial v2). One-shot migration:

1. Run `dataset_v3_migrate.py --upload --delete-old` on Surface.
2. Builds a v3 dataset from both legacy paths into a temporary v3 staging dir.
3. Uploads to a Hugging Face Hub repo (e.g. `bradley-festraets/citizenry-fleet`).
4. On verified upload (hash check), deletes the legacy local dirs.
5. Surface's recorder is then disabled in Constitution Law (`governor.recorder_enabled = false`); GovernorNode entry point will refuse to start a recorder going forward.

`--keep-old` flag preserves legacy paths if anything goes wrong; `--dry-run` reports counts and planned upload size without writing.

### 8.2 Forward path (per-node, automatic)

Each ManipulatorNode runs `EpisodeRecorderV3` writing directly to `~/citizenry-datasets/v3/` during episode capture. On episode close:

1. ManipulatorCitizen calls `EpisodeRecorderV3.close_episode()` — finalizes Parquet and MP4.
2. `HFUploader` (async) detects the closed episode and starts an upload to the configured repo.
3. Upload is verified by hash check against local files.
4. On verified success, local episode files are deleted.
5. On failure, episode stays local; retry queue picks it up after `dataset.retry_interval_s`.

Configuration via Constitution Laws (Governor-controlled, runtime-mutable):

- `dataset.hf_repo_id` — e.g. `bradley-festraets/citizenry-fleet`
- `dataset.upload_after_episode = true`
- `dataset.delete_after_upload = true`
- `dataset.retry_interval_s = 300`
- `dataset.max_local_episodes = 50` — hard cap; if hit, oldest unmirrored episode is preserved and recorder pauses

HF auth: a token at `~/.citizenry/hf_token` (chmod 600), referenced by `HFUploader`. Per-node tokens permitted — fleet doesn't share auth.

### 8.3 What gets uploaded

Per episode:
- v3-shaped Parquet (state, action, reward, frame metadata)
- One MP4 per camera stream
- Per-episode metadata: `node_pubkey` (recorder), `policy_pubkey` (source — `null` if human-driven), `governor_pubkey`, `constitution_hash`, `task_type`, `success`, `reward_total`, `started_at`, `duration_s`

The HF repo accumulates episodes across the fleet, indexed by these metadata fields, so future fine-tuning can filter (e.g. "all SmolVLA-driven episodes" or "all jetson-orin-001 episodes" or "all successful pick-and-place").

## 9. Error handling

| Failure mode | Behaviour |
|---|---|
| Jetson offline | Multicast presence drops in 6s. Marketplace re-broadcasts task. Co-located fallback (LeaderCitizen on the same follower's node) takes over. |
| SmolVLA inference latency >100ms | Emitted teleop frame TTL expires; ManipulatorCitizen's expiry rule causes arm to go limp; PolicyCitizen REPORTs `inference_latency_violation`; fatigue increases, future bids penalized. |
| Camera frame missing | PolicyCitizen pauses action emission, REPORTs `missing_observation`; governor decides to abort or wait. |
| Cross-node action-stream packet loss | TTL handles staleness. Sustained loss → ManipulatorCitizen's REPORT shows degraded fps; governor can revoke task. |
| HF upload failure | Episode stays local; retry queue. If `dataset.max_local_episodes` hit, recorder pauses on that node and emits a mycelium warning. |
| HF auth missing/invalid | Recording continues locally; HFUploader logs warning per attempt; governor dashboard shows alert. |
| Model load failure at boot | PolicyCitizen advertises `policy.imitation:disabled`; cannot bid. |
| Action target out of range | ServoLimits clamp at follower; counter increments; PolicyCitizen's `position_error_mean` rises; future bids penalized. |
| Constitution version mismatch | Existing behaviour: citizens refuse to act until current ratified Constitution is received. |
| Node-key file missing/corrupt | Node refuses to start; logs path and instructs to regenerate; no silent fallback. |

## 10. Testing

### 10.1 Unit tests (host-agnostic)

- `tests/test_smolvla_runner.py` — canned (frame, state) tuple → action chunk of expected shape and dtype. Mock model load; slow-marker test does real load.
- `tests/test_policy_citizen_bids.py` — manipulation Task with `params.follower_pubkey` → PolicyCitizen produces a Bid with co-location bonus when local; with no bonus when remote; no bid when capability missing.
- `tests/test_marketplace_co_location.py` — given two bidders (one co-located, one remote) with equal base scores, co-located bidder wins.
- `tests/test_dataset_v3_migrate.py` — fixture legacy episode → v3 dataset readable by `LeRobotDataset.load_from_disk()`; verify episode/frame/action counts and MP4 frame counts.
- `tests/test_episode_recorder_v3.py` — recorder writes v3-shaped output; both writers run during transition window.
- `tests/test_hf_upload.py` — close episode → uploader sees it → mocked HF API returns success → local files deleted. Failure path: mocked 500 → episode retained, retry counter increments.
- `tests/test_node_identity.py` — node key generated on first run; re-loaded on subsequent runs; refuses to start if file is corrupted.
- `tests/test_governor_no_recorder.py` — GovernorCitizen entry point refuses to start a recorder if `governor.recorder_enabled = false`.

### 10.2 Integration tests (gated by env)

- `integration/test_jetson_smolvla_smoke.py` (Jetson) — load SmolVLA, run forward pass on synthetic frame; assert latency < 100ms.
- `integration/test_marketplace_e2e_local.py` (Jetson) — Surface emits Task; co-located PolicyCitizen wins; local follower receives action stream; success REPORTed; episode lands in v3 dataset.
- `integration/test_marketplace_e2e_cross_node.py` (Jetson + Pi) — Surface emits Task targeting Pi follower; Jetson PolicyCitizen wins (Pi has no PolicyCitizen); cross-LAN action stream; episode recorded on Pi.
- `integration/test_hf_upload_real.py` (any node, network required) — record short episode → upload to throwaway HF repo → verify → delete local.

### 10.3 Hardware acceptance (manual, one pass per topology)

1. Single-node case: leader+follower on Jetson; trigger marketplace task; PolicyCitizen wins; arm executes; episode logs in v3; auto-uploads; local cleared.
2. Cross-node case: leader+follower on Pi; PolicyCitizen on Jetson bids and wins; Pi arm executes; episode recorded on Pi; uploads.
3. Human teleop: any ManipulatorNode; LeaderCitizen drives ManipulatorCitizen; episode records and uploads.

## 11. Hardware constraints + latency budget

- Jetson Orin Nano 8GB Super, JetPack 6.2.7, CUDA torch installed (per `project_jetson_setup.md`).
- SmolVLA 450M expected to run comfortably at FP16; INT8 fallback available if needed.
- LearnOpenCV's published Jetson Orin Nano benchmark for SmolVLA confirms the chip can host it; we still measure on-device before committing to specific Hz targets.

End-to-end action latency budgets:

| Path | Budget | Components |
|---|---|---|
| Local SmolVLA (§6.1) | <60ms | camera capture (<33ms) + IPC (<2ms) + Jetson inference (<25ms) — well inside 100ms TTL |
| Cross-node SmolVLA (§6.2) | <100ms (TTL bound) | camera capture (<33ms) + LAN transit ×2 (<20ms) + Jetson inference (<25ms) + servo write (<5ms) |
| Human teleop on a node (§6.3) | <10ms | leader read (<2ms) + IPC (<2ms) + servo write (<5ms) |

If sustained target Hz isn't reachable, fall back to lower-Hz action-chunk emission with chunk size K covering the gap. SmolVLA's native pattern.

WiFi-cam streams (XIAO) carry higher and more variable latency than the Pi CSI cam; if both are required for SmolVLA observation, Constitution Law `policy_citizen.observation_cameras` should pair them in the order [stable_cam, wifi_cam] and the runner allows the wifi frame to be one tick stale before pausing.

## 12. Decisions (all closed 2026-04-27)

1. ✅ **Camera selection** — all attached cameras remain available; PolicyCitizen picks 2 at runtime via Constitution Law `policy_citizen.observation_cameras`. See §7.1.
2. ✅ **Skill granularity** — single `imitation:smolvla_base` skill in v1; refine into per-task skills post-fine-tune.
3. ✅ **Constitution amendment** — new immutable Article: "Policy citizens shall not emit action targets outside ServoLimits."
4. ✅ **Personality seed** — "teacher" archetype: high Conscientiousness, low Neuroticism, mid Openness, mid Extraversion. Stored in `genome.json`; mutates per the existing personality drift mechanism.
5. ✅ **Surface fallback** — Surface stays governor-only (no second policy citizen on it). Marketplace re-auction is the failure hook; if PolicyCitizen drops, the LeaderCitizen on the target follower's node wins by default (human-driven teleop).
6. ✅ **Class naming** — `PolicyCitizen`, with `imitation:smolvla_base` as a skill. Future variants (Octo, π0.5-distilled, fine-tunes) drop into the same class.
7. ✅ **Topology generalization** — N nodes, each ManipulatorNode hosts a co-located leader+follower pair. GovernorNode (Surface) hosts no arms.
8. ✅ **Cross-node policy targeting** — PolicyCitizen on any compute-capable node may bid on any follower; co-located bidders receive a +0.15 score bonus. Tightest loop wins by default; cross-node fallback works when needed.
9. ✅ **Node identity** — separate Ed25519 keypair at `~/.citizenry/node.key` per node; `node_pubkey` propagated through citizen genomes for co-location detection.
10. ✅ **Surface role** — Governor + dashboard + CLI only. **No recorder.** Enforced by Constitution Law `governor.recorder_enabled = false` and verified at GovernorCitizen boot.
11. ✅ **Per-node HF upload pipeline** — each ManipulatorNode records v3 locally, uploads to HF on episode close, deletes local on verified success. Per-node HF token at `~/.citizenry/hf_token`. Configurable Constitution Laws control repo, retry, and local-cap behaviour.
12. ✅ **Recording attribution** — the follower's node records (always); per-episode metadata captures `node_pubkey` (recorder) and `policy_pubkey` (source).

## 13. Suggested implementation order

Each ticket is potentially a separate PR. Dependencies in parentheses.

1. **Node identity layer** — `node_identity.py`, key generation, genome `node_pubkey` field. Tests.
2. **Marketplace co-location bonus** — `compute_bid_score` extension, `params.follower_pubkey` filtering, tests. (depends on 1)
3. **Citizen split** — extract `LeaderCitizen` from `surface_citizen.py`; rename `pi_citizen.py` → `manipulator_citizen.py`; rename governor portion → `governor_citizen.py`. Pure refactor, no behaviour change.
4. **EpisodeRecorderV3** — new writer class behind Constitution flag; both v1 and v3 written in parallel during transition window.
5. **Dataset v3 migration script** — `dataset_v3_migrate.py`, idempotent, dry-run. (independent of 1–4)
6. **HFUploader** — async upload + verify + delete, retry queue, Constitution Laws. (depends on 4)
7. **Run migration on Surface** + **disable Surface recorder** by setting `governor.recorder_enabled = false` in Constitution. (depends on 5, 6)
8. **smolvla_runner.py** — standalone load + forward pass on Jetson, no networking. Unit tests + Jetson smoke test.
9. **PolicyCitizen** — `Citizen` subclass; bids and accepts; uses runner from 8; co-location bonus from 2.
10. **run_jetson.py** entry point + `citizenry-jetson.service` + `jetson-setup.sh`. (depends on 1, 3, 9)
11. **End-to-end hardware acceptance** — single-node, cross-node, human-teleop scenarios.
12. **Switch `episode_recorder.py` default to v3-only**, remove v1 writer (after soak window).

## 14. Research grounding

- SmolVLA blog post (Hugging Face): https://huggingface.co/blog/smolvla
- SmolVLA model card: https://huggingface.co/lerobot/smolvla_base
- LeRobotDataset v3 announcement: https://huggingface.co/blog/lerobot-datasets-v3
- v3 porting guide: https://huggingface.co/docs/lerobot/porting_datasets_v3
- SmolVLA on Jetson Orin Nano (LearnOpenCV walkthrough): https://learnopencv.com/smolvla-lerobot-vision-language-action-model/
- Jetson AI Lab models index: https://www.jetson-ai-lab.com/models/
- Federated Cloud Robotic Manipulation survey (relevant once multi-fleet ships): https://arxiv.org/html/2507.17903

## 15. What this spec deliberately leaves on the table

The brainstorming session surfaced several frontier-research items (ASkDAgger active teleop, latent safety filters, Qwen2.5-VL auto-captioning, federated policy merging, π0.5, GR00T). All are deferred. The reasoning: get a single learned policy actually running in the multi-node marketplace first; every other research item plugs in cleanly *around* that core. The natural next specs after this one are: **(a)** safety filter as a `safety-citizen` (option F), **(b)** SmolVLA fine-tune loop on Jetson using v3 datasets pulled from HF, **(c)** ASkDAgger active teleop where the governor only requests human assistance when the policy is uncertain.
