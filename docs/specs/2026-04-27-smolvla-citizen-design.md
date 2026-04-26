# SmolVLA-as-Citizen — Design Spec

**Date:** 2026-04-27
**Author:** Brainstormed with Claude (Opus 4.7) at Bradley's request
**Status:** Draft for review — not yet approved
**Scope chosen:** B from brainstorm (Inference + LeRobotDataset v3 migration as precursor)

---

## 1. Goal

Make Hugging Face's SmolVLA 450M a first-class citizen in the citizenry mesh, running on the Jetson Orin Nano Super (`jetson-orin-001` @ 192.168.1.189), bid-able through the existing task marketplace as an action source for the SO-101 follower arm. Migrate `~/citizenry-datasets/` to LeRobotDataset v3 format as a precursor so the next spec (fine-tuning) is unblocked.

This is the first spec where a *learned* policy participates in the marketplace alongside hand-coded routines and human teleop.

## 2. Non-goals (explicitly out of scope)

The following are intentionally deferred to follow-up specs so this one stays small enough to ship:

- **Fine-tuning** SmolVLA on local SO-101 data (next spec — depends on v3 migration here)
- **Latent safety filter / OOD veto** (option F from brainstorm)
- **ASkDAgger active teleop** loop (option E)
- **Hailo-8L perception citizen** (option B from question 1; separate spec)
- **Multi-fleet federation / policy-merging**
- **Qwen2.5-VL nightly auto-captioning**
- **Surface CPU fallback policy** (option C)

## 3. Why this scope (B = inference + v3 migration)

`A` (inference only) leaves a "demo policy" that can't be improved. `B` adds the dataset migration that *every* downstream spec (fine-tuning, ASkDAgger, federation) requires anyway, at ~10% extra cost. Doing v3 now also forces us to harden `episode_recorder.py` before the dataset volume grows, which it will once SmolVLA is running episodes unattended.

## 4. Architecture

### 4.1 New citizen type

```
PolicyCitizen(Citizen)
  Lives on:        jetson-orin-001 (Jetson Orin Nano Super, 8GB)
  Genome:          hardware_type="jetson_orin_nano_super"
                   role="policy"
                   personality_seed → high Conscientiousness, low Neuroticism,
                                       mid Openness, mid Extraversion ("teacher")
  Capabilities:    ["policy.imitation", "vla.smolvla_base", "cuda_inference"]
  Skills:          imitation:smolvla_base (level 1 — factory-pretrained)
                   pick_and_place_smolvla (level 0 until first success)
  Stage:           starts at JUVENILE (skips NEWBORN/INFANT — pretrained model
                   ≠ blank slate; ratified in Constitution)
```

### 4.2 Slot in the existing protocol

`PolicyCitizen` participates in the existing 7-message protocol unchanged. No new message types, no protocol version bump, no canonical-JSON changes (which matters because `xiao-citizen` C++ firmware is mid-flight and any wire-format drift would block that).

When the Governor (Surface) creates a manipulation `Task` (`type="pick_and_place"`, `required_capabilities=["arm.so101"]`, `required_skills=["pick_and_place"]`), PolicyCitizen evaluates it via the existing `can_citizen_bid()` (`citizenry/marketplace.py:236-259`) and emits a `Bid` via PROPOSE. If it wins (`select_winner`, `marketplace.py:135-143`), it becomes the action source for the duration of the task.

### 4.3 Action source flip

Today: Surface's `surface_citizen` reads the leader arm and emits teleop frames at 60 FPS to `pi_citizen`. With this spec: when PolicyCitizen wins a marketplace task, it becomes the source of teleop-shaped frames. The Pi's frame-application path (servo writes + ServoLimits clamp) is unchanged. The Surface's leader-arm reader stays running but its frames are ignored unless it bids and wins.

This keeps the change additive — no Pi-side modifications required for the inference path.

## 5. Components

| File | Status | Purpose |
|---|---|---|
| `citizenry/policy_citizen.py` | **new** | Jetson-side `Citizen` subclass; bids on manipulation tasks; calls into runner; emits action frames |
| `citizenry/smolvla_runner.py` | **new** | Wraps `lerobot.policies.smolvla` load/forward; produces action chunks; not citizenry-aware |
| `citizenry/run_jetson.py` | **new** | Entry point for jetson-orin-001, mirrors `run_pi.py` / `run_surface.py` |
| `citizenry/dataset_v3_migrate.py` | **new** | One-shot migrator: legacy `~/.citizenry/episodes/` + `~/citizenry-datasets/` → LeRobotDataset v3 |
| `citizenry/episode_recorder.py` | **modified** | Adds `EpisodeRecorderV3` writer; existing v1 writer kept behind a Constitution flag for one transition window |
| `citizenry/skills.py` | **modified** | Adds `default_policy_skills()` factory |
| `citizenry/genome.py` | **no change** | Already supports custom `role` and `hardware_type` strings |
| `citizenry/constitution.py` | **modified** | Adds Article: "Policy citizens shall not emit action targets outside ServoLimits"; adds Laws `episode_recorder_format = "v3"` and `policy_citizen.observation_cameras = [...]` |
| `citizenry/marketplace.py` | **no change** | Already protocol-agnostic re: who bids |
| `pi-setup.sh` / new `jetson-setup.sh` | **new** | Provisioning + systemd unit `citizenry-jetson.service` |

Total new code: roughly 4 modules + tests. Total modified: 3 files, all additive.

## 6. Data flow (steady state during a SmolVLA-driven task)

```
[camera-citizens]                          [pi_citizen]
   ── ADVERTISE(camera) ──┐              ┌── REPORT(joint state, currents) ──┐
                          ▼              ▼                                     │
                       [policy_citizen on jetson-orin-001]                     │
                       1. assemble {wrist_frame, base_frame, state} into       │
                          SmolVLA observation tensor                           │
                       2. smolvla_runner.act(obs) → 50-step action chunk       │
                       3. emit PROPOSE(teleop_frame, ttl=0.1) per step at      │
                          ~30 Hz ─────────────────────────────────────────────┘
                                                            │
                                                            ▼
                                                   [pi_citizen]
                                                   - verify Ed25519
                                                   - clamp to ServoLimits
                                                   - write to servos
                                                   - record EpisodeFrame v3
                                                   - REPORT telemetry
```

The `surface_citizen` Governor is still active throughout — it ratifies the Constitution, brokers the marketplace, and can interject GOVERN messages to halt or re-auction. It just isn't the action source.

## 7. SmolVLA action / observation contract

SmolVLA `lerobot/smolvla_base` is pretrained on Hugging Face's SO-100/101 community dataset, so its action space is *expected* to align with the SO-101 follower's 6-joint absolute-position frame already used in `episode_recorder.py:31` (`MOTOR_NAMES`). Two items to verify against the model card before merging:

- **Observation shape:** wrist + base camera, normalized resolution, color channels (RGB vs BGR — OpenCV is BGR by default in citizenry).
- **Action units:** SmolVLA's checkpoint outputs (likely normalized [-1, 1] or radians); citizenry's `action_positions` are raw Feetech servo ticks (0–4095). The runner is responsible for the inverse mapping.

Mapping lives in `smolvla_runner.py` so policy_citizen stays unaware of it. If the contract turns out not to match, the runner is the only file that has to change.

### 7.1 Runtime camera selection (decided 2026-04-27)

All three on-fleet cameras (Pi CSI NoIR Wide, two XIAO wifi cams) remain available as observation sources at all times. PolicyCitizen picks **which two** to consume at runtime based on a Constitution Law:

```python
# in constitution.py default_laws()
"policy_citizen.observation_cameras": ["xiao-cam-wrist", "pi-csi-base"]  # ordered: [primary, secondary]
```

Camera identity is resolved by mDNS-advertised name (e.g. `xiao-cam-a1b2`) or by a `role` tag in the camera-citizen's genome (e.g. `wrist`, `base`, `ceiling`). PolicyCitizen subscribes to the two named camera-citizens via the existing ADVERTISE/PROPOSE pattern and assembles the SmolVLA observation in `smolvla_runner.py`.

**Switching cameras at runtime:** Governor issues a `GOVERN` message with an updated Law. PolicyCitizen detects the change on its next constitution refresh, drops its current camera subscriptions, subscribes to the new pair, and continues without restart. No code change to swap; no re-deployment.

**Implication for components:** `policy_citizen.py` keeps a small `ObservationAssembler` that holds the active subscription list; `smolvla_runner.py` is told which slot is `[primary, secondary]` and packages them into the model's expected channel order. If the Law names a camera that isn't on the network, PolicyCitizen REPORTs `camera_unresolved`, refuses to bid, and waits for either the camera to come online or a new GOVERN.

## 8. Dataset v3 migration

### 8.1 Sources

- `~/.citizenry/episodes/<episode_id>/` — JSONL frames + JPEGs (the live recorder output)
- `~/citizenry-datasets/episode_000X/action_*.npy` — partial v2 layout (currently 2 frames)

These are inconsistent with each other and with v3.

### 8.2 Target

A single LeRobotDataset v3 dataset at `~/citizenry-datasets/v3/`:

- Chunked Parquet for episode/state/action/reward/metadata
- MP4 per camera stream (one MP4 per chunk, not per episode — v3 default)
- Hub-streamable: a future spec can `huggingface-cli upload` directly
- Per-episode metadata preserved: `citizen_pubkey`, `task_type`, `success`, `reward_total`, `governor_pubkey`, `constitution_hash`

### 8.3 Migration script behaviour

`citizenry/dataset_v3_migrate.py`:

- Walks both legacy paths
- Builds a v3 dataset using `lerobot.common.datasets.lerobot_dataset.LeRobotDataset` (v0.4.4 API; the Jetson already has 0.4.4)
- `--dry-run` flag: report counts + planned chunk sizes without writing
- Idempotent: re-running with new episodes appends, doesn't reconvert
- `--keep-old` (default) / `--delete-old` (gated, requires `--yes`)
- Logs per-episode conversion result to a JSONL audit file

### 8.4 Forward path

`EpisodeRecorderV3` writes v3 directly going forward. For one transition window (target: 2 weeks of soak), both v1 and v3 are written; the Constitution Law `episode_recorder_format` switches default to `"v3"`. After soak, v1 writer is removed in a follow-up commit.

## 9. Error handling

| Failure mode | Behaviour |
|---|---|
| Jetson offline | Multicast presence drops in 6s (3× heartbeat). Marketplace re-broadcasts task. Surface leader-arm teleop or another bidder wins. Pi never accepts a stale-TTL frame, so no zombie commands reach servos. |
| SmolVLA inference latency spike (>100ms) | Emitted teleop frame TTL expires before Pi applies it; Pi's existing expiry rule causes arm to go limp; PolicyCitizen REPORTs `inference_latency_violation`; marketplace re-auctions; PolicyCitizen's fatigue increases (existing system, `marketplace.py:131`) so its next bid score drops. |
| Camera frame missing | PolicyCitizen pauses action emission, REPORTs `missing_observation`, governor decides to abort or wait. |
| Model load failure at boot | PolicyCitizen advertises `policy.imitation:disabled`; cannot bid; visible in dashboard. |
| Action target out of range | Pi's existing ServoLimits clamp catches it; counter increments; PolicyCitizen's `position_error_mean` rises; future bids penalised. |
| Constitution version mismatch | Existing citizenry behaviour: PolicyCitizen refuses to act until it has a current ratified Constitution from the Governor. |

No new failure surfaces are introduced; all existing recovery paths cover the new citizen.

## 10. Testing

### 10.1 Unit tests (run on any host)

- `tests/test_smolvla_runner.py` — given canned (frame, state) tuple, runner returns action chunk of expected shape and dtype. Mock the model load to keep CI fast; have a slow-marker test that does a real load.
- `tests/test_policy_citizen_bids.py` — given a manipulation Task, PolicyCitizen produces a Bid with score > 0.7 when warm and capability matches; produces no bid when capability missing.
- `tests/test_dataset_v3_migrate.py` — fixture legacy episode → migration produces a v3 dataset that `LeRobotDataset.load_from_disk()` can read; verify episode count, frame count, action shape, MP4 frame count.
- `tests/test_episode_recorder_v3.py` — recorder writes v3-shaped output; both writers run in parallel during transition window.

### 10.2 Integration tests (run on Jetson; gated by env)

- `integration/test_jetson_smolvla_smoke.py` — load SmolVLA, run forward pass on a synthetic frame; assert latency < 100ms target.
- `integration/test_marketplace_e2e.py` — Surface emits a Task; PolicyCitizen wins; Pi receives action stream; success REPORTed; episode lands in v3 dataset.

### 10.3 Hardware acceptance (manual, one pass)

Bradley triggers a marketplace task via `governor_cli` (e.g. "pick the red block"). PolicyCitizen wins the auction. Arm executes. Episode logs in v3 format. Visual confirmation that the arm moves smoothly and the gripper closes on the target.

## 11. Hardware constraints + latency budget

- Jetson Orin Nano 8GB Super, JetPack 6.2.7, CUDA torch installed (per `project_jetson_setup.md`).
- SmolVLA 450M expected to run comfortably at FP16; INT8 fallback available if needed.
- LearnOpenCV's published Jetson Orin Nano benchmark for SmolVLA confirms the chip can host it; we still measure on-device before committing to specific Hz targets.
- End-to-end action latency budget: < 100ms (`TTL_TELEOP` in `protocol.py:40`). Components: camera frame age (<33ms at 30 FPS) + LAN transit (<10ms) + Jetson inference (target <50ms) + Pi servo write (<5ms).
- If sustained 30 Hz isn't reachable, fall back to lower-Hz action-chunk emission with chunk size K covering the gap. This is already SmolVLA's native pattern.

## 12. Decisions (all closed 2026-04-27)

1. ✅ **Camera selection** — all three on-fleet cameras remain available; PolicyCitizen picks 2 at runtime via Constitution Law `policy_citizen.observation_cameras`. See §7.1 for the full mechanism.
2. ✅ **Skill granularity** — single `imitation:smolvla_base` skill in v1; refine into per-task skills (`pick_and_place_smolvla`, `pour_smolvla`, …) post-fine-tune, once we have evidence that performance differs meaningfully across task types.
3. ✅ **Constitution amendment** — add a new immutable Article: "Policy citizens shall not emit action targets outside ServoLimits." Defence-in-depth: Pi already enforces this on ingress, but codifying it in the Constitution gives the immune-memory subsystem a clean event class to learn from and makes governance auditable.
4. ✅ **Personality seed** — "teacher" archetype: high Conscientiousness, low Neuroticism, mid Openness, mid Extraversion. Stored in `genome.json` at first boot; mutates per the existing personality drift mechanism.
5. ✅ **Surface fallback policy** — Surface stays teleop-only for v1. No second policy citizen on the Surface. Marketplace re-auction is the failure hook; if PolicyCitizen drops, Bradley's leader-arm teleop wins by default.
6. ✅ **Class naming** — `PolicyCitizen`, with `imitation:smolvla_base` as a skill. Future variants (Octo, π0.5-distilled, local fine-tunes) drop into the same class as additional skills.

## 13. Suggested implementation order

These are tickets, not commits. Each can be a separate PR.

1. **Dataset v3 migration script** — independent of everything else; can run before any new code.
2. **`EpisodeRecorderV3`** + Constitution Law flag; both writers run in parallel.
3. **`smolvla_runner.py`** standalone — loads model, runs inference, no networking. Unit tests + Jetson smoke test.
4. **`policy_citizen.py`** — `Citizen` subclass; bids and accepts; no SmolVLA wired in (uses a stub action emitter for tests).
5. **Wire SmolVLA into `policy_citizen`** via runner.
6. **`run_jetson.py`** entry point + `citizenry-jetson.service` systemd unit + `jetson-setup.sh`.
7. **End-to-end hardware acceptance.**
8. **Switch `episode_recorder.py` default to v3-only**, remove v1 writer (separate PR after soak).

## 14. Research grounding

- SmolVLA blog post (Hugging Face): https://huggingface.co/blog/smolvla
- SmolVLA model card: https://huggingface.co/lerobot/smolvla_base
- LeRobotDataset v3 announcement: https://huggingface.co/blog/lerobot-datasets-v3
- v3 porting guide: https://huggingface.co/docs/lerobot/porting_datasets_v3
- SmolVLA on Jetson Orin Nano (LearnOpenCV walkthrough): https://learnopencv.com/smolvla-lerobot-vision-language-action-model/
- Jetson AI Lab models index: https://www.jetson-ai-lab.com/models/

## 15. What this spec deliberately leaves on the table

The brainstorming session surfaced several frontier-research items (ASkDAgger active teleop, latent safety filters, Qwen2.5-VL auto-captioning, federated policy merging, π0.5, GR00T). All are deferred. The reasoning: get a single learned policy actually running in the marketplace first; every other research item plugs in cleanly *around* that core, but starts to entangle if combined up front. The natural next spec after this one is **#7 from §13** (acceptance) → **fine-tune loop** → **safety filter** → **ASkDAgger**.
