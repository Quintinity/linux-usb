---
inputDocuments:
  - synthesis-robot-citizenry.md
  - prd-citizenry-v2.md
  - architecture-citizenry-v2.md
  - citizenry/protocol.py
  - citizenry/citizen.py
  - citizenry/surface_citizen.py
  - citizenry/constitution.py
workflowType: 'prd'
---

# Product Requirements Document — armOS Citizenry v3.0: "The Nation Governs Itself"

**Author:** Bradley
**Date:** 2026-03-16
**Version:** 3.0
**Status:** Draft

---

## Executive Summary

armOS Citizenry v2.0 ("Citizens Collaborate") shipped a working multi-citizen system: task marketplace with auction bidding, skill trees with XP, capability composition, symbiosis contracts, mycelium warning propagation, immune memory, citizen genomes, and a USB camera citizen. All running on real hardware: Surface Pro 7 as governor, Raspberry Pi 5 as follower arm, DJI Osmo Action 4 as camera citizen. The 7-message protocol remains unchanged. Citizens can negotiate tasks, learn from experience, compose capabilities, and share safety knowledge.

**v3.0 ("The Nation Governs Itself") adds the governance intelligence layer: natural language policy control, safe rolling policy updates, and graceful citizen shutdown.** The user speaks intent ("make the robots gentle") and the system translates it to formal policy, rolls it out safely one citizen at a time with automatic rollback, and ensures no knowledge is lost when a citizen shuts down.

The core deliverables:

1. **Natural Language Governance** -- User says "make the robots gentle" and the governor translates it to a formal policy (reduce torque 30%) via Claude on the Surface, then distributes it as GOVERN messages
2. **Rolling Policy Updates with Canary Testing** -- New policies roll out one citizen at a time with self-test gates and automatic rollback on >20% failure rate
3. **Dead Citizen's Will** -- Final broadcast before shutdown containing current tasks, partial results, and state to preserve

Stretch goals (deferred if infeasible within the sprint):

4. **Emotional State Signals** -- Fatigue/confidence/curiosity as composite telemetry metrics derived from real servo data
5. **Consciousness Stream** -- Natural language state narration via local LLM

---

## Vision

The citizenry moves from "devices that work together" to "devices that govern themselves." v2.0 proved the collaboration layer: citizens negotiate tasks, learn skills, form contracts, and share warnings. v3.0 proves the governance intelligence layer. The governor stops being a protocol relay and becomes a policy interpreter. The user stops writing JSON and starts speaking English.

When the user says "be more careful around the edges of the workspace," the system understands this means: reduce velocity near joint limits, increase collision sensitivity, and tighten the workspace boundary by 10%. The governor's Claude instance translates the intent into formal law parameters. The new policy rolls out to citizens one at a time. Each citizen runs a self-test: can I still reach the task workspace? Can I still complete my current skill set? If the self-test passes, the citizen adopts the policy. If 2 out of 5 citizens fail the self-test, the rollout halts and reverts automatically.

When a citizen detects imminent shutdown (thermal, power loss, user unplugging), it broadcasts a will: "I was 60% through a pick-and-place task, the red block is at position (0.3, 0.5), my gripper was closed, and here are my last 10 immune memory entries." Neighbors absorb the knowledge. The task re-enters the marketplace with partial progress attached. No knowledge is lost.

**Target demo:** Bradley says "make the robots gentle" into the Surface Pro terminal. Claude translates this to `{reduce_torque: 30%, reduce_velocity: 20%}`. The governor rolls the new law to the Pi arm first (canary). The arm runs a self-test (move each joint through 50% range at the new limits, verify no faults). Self-test passes. The policy propagates to all citizens. Then Bradley unplugs the Pi. The Pi broadcasts its will before dying. When a new Pi is plugged in, it inherits the will's knowledge through the fleet genome. The "gentle" policy is already in the constitution -- the new citizen adopts it immediately.

---

## Problem Statement

v2.0 citizens can collaborate, but the governance layer is still mechanical:

- **Policy changes require JSON** -- To change a law, the user must construct a precise `update_law()` call with correct parameter names and values. Users have goals ("be gentle"), not parameter tuples.
- **Policy updates are atomic and global** -- When a law changes, it hits all citizens simultaneously. A bad law (e.g., torque so low the arm cannot lift itself) bricks the entire fleet. There is no canary mechanism, no self-test, no rollback.
- **Citizen death is information loss** -- When a citizen goes offline (unplugged, thermal shutdown, power failure), its current task state, partial results, and recent observations vanish. The task simply times out and re-enters the marketplace from scratch.
- **No intent interpretation** -- The gap between what the user wants ("sort gently") and what the system needs (`max_torque: 350, max_velocity: 0.6`) requires manual translation every time.

These limitations mean the governance layer scales linearly with the user's technical knowledge. A user who cannot write JSON cannot govern. A policy mistake affects all citizens at once. Knowledge dies with the citizen.

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| NL to policy translation | >80% of common intents correctly translated | Manual evaluation: 20 test phrases |
| NL policy round-trip | < 5s from user input to first citizen receiving GOVERN | Timestamp delta in protocol logs |
| Canary rollout coverage | 100% of policy updates go through canary | Rollout audit log |
| Self-test pass rate | >95% for valid policies | Self-test result logs |
| Auto-rollback trigger | <10s from failure detection to full rollback | Integration test |
| Will broadcast success | >90% of graceful shutdowns include will | Signal handler test |
| Will absorption | Partial task progress preserved in 100% of wills received | Integration test |
| Zero protocol breaking changes | All v2.0 messages still work unmodified | Protocol compat test |
| No new message types | Still exactly 7 message types | Code audit |
| Test coverage | >80% for all new modules | pytest --cov |

---

## User Journeys

### Journey 1: Natural Language Policy Change

Bradley is watching teleop and the arms are moving too aggressively near a cup on the table.

1. Bradley types in the Surface terminal: "make the robots more gentle"
2. The governor's NL interpreter (Claude via Anthropic API on Surface) receives the text
3. Claude analyzes the current constitution and laws, then generates a policy diff:
   - `max_torque`: 500 -> 350 (30% reduction)
   - `max_velocity`: 1.0 -> 0.7 (30% reduction)
   - `collision_sensitivity`: 0.5 -> 0.8 (60% increase)
4. The governor displays the proposed changes to Bradley: "I'll reduce torque by 30%, slow movements by 30%, and increase collision sensitivity. Apply? [Y/n]"
5. Bradley confirms (or the system auto-applies if `auto_apply_policy` law is set)
6. The rollout engine begins canary deployment (see Journey 2)
7. Dashboard shows: "Policy: gentle_mode -- rolling out (1/3 citizens)"

### Journey 2: Canary Policy Rollout

The governor has a new policy to distribute (from Journey 1 or from any `update_law()` call).

1. Rollout engine selects the first citizen (lowest-risk: the one with the most XP, most stable health history)
2. Governor sends GOVERN with `type: "policy_canary"` containing the new law params and a `rollout_id`
3. Citizen receives the canary policy and enters "canary mode":
   a. Saves current law params as rollback snapshot
   b. Applies new law params
   c. Runs self-test suite (move joints through safe range, verify telemetry within bounds, verify no faults triggered)
   d. Sends REPORT with `type: "canary_result"` containing pass/fail and diagnostics
4. If pass: governor marks citizen as "updated," moves to next citizen in the rollout order
5. If fail: governor halts rollout, sends GOVERN `type: "policy_rollback"` with `rollout_id` to all citizens that already received the canary -- they revert to their snapshot
6. After all citizens pass: governor sends GOVERN `type: "policy_commit"` -- citizens discard their rollback snapshots
7. If >20% of citizens fail during rollout, the entire rollout is aborted and all changes reverted
8. Dashboard shows rollout progress: "gentle_mode: 2/3 passed, 0 failed, 1 pending"

### Journey 3: Dead Citizen's Will

The Pi 5's USB power cable is accidentally pulled during a task.

1. The Pi's citizen process receives SIGTERM (or detects low voltage via servo telemetry)
2. The citizen enters "dying" state and has a 2-second window to broadcast its will
3. Will contains:
   - Current task ID and progress (e.g., "pick_and_place, 60% complete, gripper closed")
   - Last known positions of all joints
   - Last 10 telemetry readings
   - Any in-flight immune memory patterns not yet shared
   - Active symbiosis contracts (so partners know to break them)
   - Last policy version applied (so the fleet knows this citizen was up-to-date)
4. Will is broadcast as REPORT with `type: "will"` via UDP multicast (best-effort, citizen may die before transmission completes)
5. All neighbors receive the will:
   - Governor absorbs the task state and re-lists the task in the marketplace with `partial_progress` attached
   - Neighbors merge any new immune memory patterns
   - Contract partners mark contracts as broken and enter safe mode
   - Dashboard shows: "pi-follower: final will received -- task re-listed"
6. When a replacement citizen joins, it receives the fleet genome which now includes the dead citizen's last immune patterns

### Journey 4: Emotional State Signals (Stretch)

Bradley glances at the dashboard during a long data collection session.

1. Each citizen computes emotional state metrics from real telemetry every heartbeat:
   - **Fatigue**: f(avg_motor_temp, error_rate_trend, uptime, power_drift) -- 0.0 (fresh) to 1.0 (exhausted)
   - **Confidence**: success_rate on current task type over last N attempts -- 0.0 (failing) to 1.0 (reliable)
   - **Curiosity**: novelty score of current sensor readings vs. experience history -- 0.0 (routine) to 1.0 (novel)
2. These signals piggyback on the HEARTBEAT body as `emotional_state: {fatigue: 0.3, confidence: 0.9, curiosity: 0.1}`
3. Dashboard renders them as intuitive indicators: "pi-follower: focused (high confidence, low fatigue)"
4. The marketplace uses fatigue to weight bids: fatigued citizens bid lower, allowing fresh citizens to win auctions
5. The governor uses confidence to adjust supervision: low-confidence citizens get more frequent health checks

### Journey 5: Consciousness Stream (Stretch)

A visitor asks "what is the robot doing right now?"

1. Every decision cycle (~2s), the citizen generates a natural language summary from structured state
2. On the Surface (has internet): Claude API generates the summary from a structured prompt containing joint positions, current task, health, recent events
3. On the Pi (no internet): a small local model (or template-based generation) produces a simpler summary
4. The stream is published as REPORT with `type: "consciousness"` and displayed on the dashboard:
   - "I'm executing pick_and_place for the red block. Approaching from the left. Elbow load at 42%, within limits. Confidence: 0.87."
5. The consciousness stream is archived with timestamps for post-session review

---

## Domain Model

### New Entities (v3.0)

```
PolicyIntent
├── raw_text: str                     # "make the robots gentle"
├── timestamp: float
├── interpreted_changes: list[LawChange]
├── confidence: float                 # How confident the NL interpreter is
├── requires_confirmation: bool       # True if confidence < threshold
└── applied: bool

LawChange
├── law_id: str                       # "servo_limits", "teleop_max_fps", etc.
├── param: str                        # "max_torque"
├── old_value: Any
├── new_value: Any
└── reasoning: str                    # "User said 'gentle' -- reducing torque 30%"

Rollout
├── id: str (UUID)
├── policy_changes: list[LawChange]
├── status: pending | rolling | committed | rolled_back | aborted
├── citizens_order: list[str]         # Pubkeys in rollout order
├── results: dict[str, CanaryResult]  # pubkey -> result
├── started_at: float
├── completed_at: float | None
├── failure_threshold: float          # Default 0.2 (20%)
└── rollback_snapshot: dict           # Pre-change law state

CanaryResult
├── citizen_pubkey: str
├── rollout_id: str
├── passed: bool
├── self_test_results: list[SelfTestResult]
├── diagnostics: dict                 # Joint ranges, fault counts, etc.
└── timestamp: float

SelfTestResult
├── test_name: str                    # "joint_range_check", "load_test", "fault_check"
├── passed: bool
├── detail: str                       # "All joints reached 50% range" or "elbow_flex: range reduced 40%"
└── duration_ms: float

CitizenWill
├── citizen_pubkey: str
├── citizen_name: str
├── timestamp: float
├── cause: str                        # "sigterm", "thermal_shutdown", "low_voltage", "user_shutdown"
├── current_task: dict | None         # Task ID, progress, partial results
├── joint_positions: dict             # Last known positions
├── recent_telemetry: list[dict]      # Last 10 readings
├── unsent_immune_patterns: list[FaultPattern]
├── active_contracts: list[str]       # Contract IDs
├── policy_version: int               # Last applied policy version
└── genome_snapshot: dict             # Compact genome for preservation

EmotionalState (stretch)
├── fatigue: float                    # 0.0-1.0
├── confidence: float                 # 0.0-1.0
├── curiosity: float                  # 0.0-1.0
├── computed_at: float
└── inputs: dict                      # Raw values used in computation
```

### Extended Entities

```
Citizen (extended from v2.0)
├── ... (all v2.0 fields)
├── policy_version: int (NEW)         # Monotonic, incremented on each law change
├── rollback_snapshot: dict | None (NEW)  # Saved state during canary
├── will_registered: bool (NEW)       # Whether SIGTERM handler is installed
├── emotional_state: EmotionalState | None (NEW, stretch)
└── consciousness_buffer: str (NEW, stretch)

SurfaceCitizen (governor, extended)
├── ... (all v2.0 fields)
├── nl_interpreter: NLPolicyInterpreter (NEW)
├── rollout_engine: RolloutEngine (NEW)
├── policy_history: list[PolicyIntent] (NEW)
├── will_archive: list[CitizenWill] (NEW)
└── consciousness_enabled: bool (NEW, stretch)
```

### Message Body Schemas (v3.0 Extensions)

All new functionality uses the existing 7 message types. The `body` field gains new schemas:

**GOVERN bodies (type=7) -- new schemas:**
```json
// Natural language policy (governor -> citizens)
{"type": "policy_update", "rollout_id": "uuid",
 "changes": [{"law_id": "servo_limits", "param": "max_torque",
              "old_value": 500, "new_value": 350,
              "reasoning": "User requested gentle mode"}],
 "policy_version": 12,
 "source": "nl_governance",
 "original_intent": "make the robots gentle"}

// Canary policy test (governor -> single citizen)
{"type": "policy_canary", "rollout_id": "uuid",
 "changes": [...], "policy_version": 12,
 "self_test_required": true}

// Policy commit (governor -> all, after successful rollout)
{"type": "policy_commit", "rollout_id": "uuid",
 "policy_version": 12}

// Policy rollback (governor -> affected citizens)
{"type": "policy_rollback", "rollout_id": "uuid",
 "reason": "canary failed on pi-follower: elbow range reduced 40%"}
```

**REPORT bodies (type=6) -- new schemas:**
```json
// Canary self-test result (citizen -> governor)
{"type": "canary_result", "rollout_id": "uuid",
 "passed": true,
 "tests": [
   {"name": "joint_range_check", "passed": true,
    "detail": "All joints reached 50% range"},
   {"name": "load_test", "passed": true,
    "detail": "No faults under test load"},
   {"name": "fault_check", "passed": true,
    "detail": "0 faults during self-test"}
 ],
 "diagnostics": {"joint_ranges": {...}, "peak_current": 180}}

// Dead citizen's will (dying citizen -> all, multicast)
{"type": "will", "cause": "sigterm",
 "current_task": {"task_id": "uuid", "progress": 0.6,
                  "partial_result": {"block_position": [0.3, 0.5]}},
 "joint_positions": {"shoulder_pan": 2048, "shoulder_lift": 1800, ...},
 "recent_telemetry": [...],
 "unsent_immune_patterns": [...],
 "active_contracts": ["contract-uuid-1"],
 "policy_version": 12}

// Emotional state (stretch, piggybacked on heartbeat)
// (Not a separate REPORT -- included in HEARTBEAT body)

// Consciousness stream (stretch, citizen -> governor)
{"type": "consciousness",
 "narration": "Executing pick_and_place for red block. Approaching from left. Elbow load 42%, within limits. Confidence 0.87.",
 "structured_state": {"task": "pick_and_place", "phase": "approach", ...}}
```

**HEARTBEAT body extension (stretch):**
```json
// Emotional state piggybacked on heartbeat
{"name": "pi-follower", "state": "executing", "health": 0.92,
 "unicast_port": 7771, "uptime": 3600,
 "emotional_state": {"fatigue": 0.3, "confidence": 0.9, "curiosity": 0.1}}
```

---

## Functional Requirements

### FR-1: Natural Language Governance

**FR-1.1** The governor MUST accept natural language policy intents as text strings (e.g., "make the robots gentle", "speed up the teleop", "be careful around the workspace edges").

**FR-1.2** The NL interpreter MUST translate intents into one or more concrete `LawChange` objects, each specifying a `law_id`, `param`, `old_value`, `new_value`, and `reasoning` string.

**FR-1.3** The NL interpreter MUST use Claude (via the Anthropic Python SDK) running on the Surface Pro 7. The interpreter MUST send the current constitution, current laws, and current citizen states as context with each translation request.

**FR-1.4** The interpreter MUST assign a confidence score (0.0-1.0) to each translation. If confidence < 0.7, the change MUST require explicit user confirmation before applying. If confidence >= 0.7, the change MAY be auto-applied (configurable via the `auto_apply_policy` law, default: require confirmation).

**FR-1.5** The interpreter MUST support at minimum these intent categories:
- **Force/gentleness**: "gentle", "careful", "aggressive", "strong" -> torque and velocity adjustments
- **Speed**: "faster", "slower", "half speed", "full speed" -> velocity and FPS adjustments
- **Safety**: "more careful", "cautious", "risky" -> collision sensitivity, workspace boundaries
- **Operational**: "rest", "stop", "resume", "home position" -> state transitions
- **Role assignment**: "the arm on the Pi should sort", "camera should watch" -> task assignment

**FR-1.6** Every NL policy change MUST be logged in a `policy_history` with the original text, interpreted changes, confidence, and whether it was confirmed or auto-applied.

**FR-1.7** The NL interpreter MUST be stateless between calls -- it receives full context each time, so it can recover from crashes without losing governance capability.

**FR-1.8** If the Anthropic API is unreachable (no internet), the interpreter MUST fall back to a keyword-matching engine that handles the top 10 most common intents with hardcoded translations. The fallback MUST log a warning that NL interpretation is degraded.

### FR-2: Rolling Policy Updates with Canary Testing

**FR-2.1** Every policy change (whether from NL governance or `update_law()`) MUST go through the rollout engine. Direct atomic updates to all citizens are no longer allowed.

**FR-2.2** The rollout engine MUST order citizens for canary testing by risk (lowest risk first). Risk score = inverse of (XP total * health history stability * uptime). The citizen with the highest XP, most stable health, and longest uptime is tested first.

**FR-2.3** The rollout engine MUST send GOVERN `type: "policy_canary"` to one citizen at a time, wait for a REPORT `type: "canary_result"`, then proceed or halt.

**FR-2.4** Each citizen receiving a canary policy MUST:
a. Save a rollback snapshot of current law parameters
b. Apply the new parameters
c. Run the self-test suite
d. Send the canary result REPORT within 10 seconds

**FR-2.5** The self-test suite MUST include at minimum:
- **Joint range check**: Move each joint to 50% of its range at the new torque/velocity limits. Pass if all joints reach target within 5 seconds.
- **Load test**: Apply a test load pattern (predefined safe sequence). Pass if no overload, thermal, or voltage faults trigger.
- **Fault check**: Verify zero new fault patterns during the self-test window.

**FR-2.6** If a citizen's self-test fails, it MUST immediately revert to its rollback snapshot and report failure.

**FR-2.7** The rollout engine MUST abort the entire rollout if the failure rate exceeds 20% (configurable via `rollout_failure_threshold` law). Abort means: send GOVERN `type: "policy_rollback"` to all citizens that received the canary, causing them to revert.

**FR-2.8** If all citizens pass, the rollout engine MUST send GOVERN `type: "policy_commit"` to all citizens, causing them to discard their rollback snapshots and finalize the new policy.

**FR-2.9** Only one rollout MAY be active at a time. Attempts to start a second rollout while one is in progress MUST be queued.

**FR-2.10** The rollout engine MUST support a `force_apply` override where the governor can skip canary testing (for emergency policy changes like emergency_stop). This MUST log a warning.

**FR-2.11** Rollout state MUST be persisted to disk so that a governor crash during rollout triggers automatic rollback on restart.

**FR-2.12** Non-manipulator citizens (e.g., camera) MUST have simplified self-tests appropriate to their type (e.g., camera tests that it can still capture frames at the required resolution).

### FR-3: Dead Citizen's Will

**FR-3.1** Every citizen MUST register signal handlers for SIGTERM, SIGINT, and SIGHUP at startup.

**FR-3.2** When a shutdown signal is received, the citizen MUST enter "dying" state and broadcast a will REPORT via UDP multicast within 2 seconds.

**FR-3.3** The will MUST contain:
- Cause of death (signal type, or "thermal_shutdown", "low_voltage" if detectable from telemetry)
- Current task state (task_id, progress percentage, partial results) if a task is active
- Last known joint positions (raw servo register values)
- Last 10 telemetry readings
- Any immune memory patterns not yet shared with the fleet
- Active symbiosis contract IDs
- Current policy version

**FR-3.4** Citizens receiving a will MUST:
a. Merge any unsent immune patterns into their own immune memory
b. If they are the governor: re-list the dead citizen's task in the marketplace with `partial_progress` data attached
c. Mark any symbiosis contracts with the dead citizen as broken
d. Log the will receipt on the dashboard

**FR-3.5** The governor MUST maintain a `will_archive` of all received wills, persisted to disk, for diagnostic and knowledge preservation purposes.

**FR-3.6** For non-graceful shutdowns (power cut, kernel panic) where no signal is received, the existing heartbeat-based death detection (10 missed heartbeats = presumed dead) remains the fallback. The will mechanism is best-effort, not guaranteed.

**FR-3.7** The will MUST be a single UDP multicast packet. If the will exceeds the UDP payload limit (65507 bytes), it MUST be truncated: telemetry readings are dropped first, then immune patterns, keeping task state and joint positions as the highest priority.

**FR-3.8** A citizen MUST NOT send a will if it is shutting down cleanly via the `stop()` method (normal shutdown). The will is only for unexpected/forced shutdowns. Normal shutdown already persists state via the genome system.

### FR-4: Emotional State Signals (Stretch)

**FR-4.1** Each citizen MAY compute emotional state metrics every heartbeat cycle:
- **Fatigue**: `clamp(0.3 * norm_temp + 0.3 * error_rate_trend + 0.2 * norm_uptime + 0.2 * power_drift, 0, 1)`
  where norm_temp = avg_motor_temp / max_temp, norm_uptime = min(uptime_hours / 8, 1.0), error_rate_trend = errors_last_5min / total_commands_last_5min, power_drift = abs(current_voltage - nominal_voltage) / nominal_voltage
- **Confidence**: `successful_tasks / total_tasks` for the current task type over the last 20 attempts (or lifetime if < 20)
- **Curiosity**: `1.0 - similarity(current_sensor_state, historical_mean)` using cosine similarity on a feature vector of joint positions + telemetry

**FR-4.2** Emotional state MUST piggyback on the HEARTBEAT body -- no separate message.

**FR-4.3** The marketplace MUST use fatigue as a bid modifier: `adjusted_score = base_score * (1.0 - 0.3 * fatigue)`. Fatigued citizens bid lower.

**FR-4.4** The dashboard MUST display emotional state as a human-readable label: "focused" (high confidence, low fatigue), "tired" (high fatigue), "uncertain" (low confidence), "curious" (high curiosity).

### FR-5: Consciousness Stream (Stretch)

**FR-5.1** The Surface governor MAY generate natural language narrations of citizen state by calling the Anthropic API with structured state as input.

**FR-5.2** On the Pi (no internet), consciousness narration MUST use a template-based system: `"Executing {task}. {joint} load at {load}%. Confidence: {confidence}."` -- no LLM required.

**FR-5.3** Consciousness narrations MUST be sent as REPORT with `type: "consciousness"` at most once per 5 seconds (to avoid API rate limits and bandwidth).

**FR-5.4** The dashboard MUST display the latest narration for each citizen in a dedicated panel.

---

## Non-Functional Requirements

### NFR-1: Protocol Compatibility

All v2.0 messages MUST continue to work unmodified. v3.0 adds new body schemas to existing message types -- it does NOT add new message types. A v2.0 citizen that receives a v3.0 body it doesn't understand MUST ignore the unknown fields gracefully (this is already the v2.0 behavior, inherited from v1.5).

### NFR-2: Performance

- NL policy translation: < 5s including Anthropic API call (network permitting)
- NL fallback (keyword matching): < 50ms
- Canary self-test execution: < 10s per citizen
- Full rollout for 5 citizens: < 60s
- Will broadcast: < 100ms from signal to packet sent
- Emotional state computation: < 1ms per heartbeat (stretch)
- Consciousness narration (API): < 3s per call (stretch)
- Consciousness narration (template): < 1ms (stretch)
- No regression in existing performance (heartbeat, teleop, marketplace)

### NFR-3: Reliability

- NL interpreter failure MUST NOT block manual policy updates -- `update_law()` still works
- Rollout engine crash during rollout MUST trigger automatic rollback on restart (persisted state)
- Will broadcast is best-effort -- system MUST function correctly even if will is never received
- API unavailability MUST be handled gracefully: fallback to keyword matching, log degradation

### NFR-4: Security

- All new message bodies MUST be signed and verified using the existing Ed25519 envelope system
- NL-interpreted policy changes MUST be signed by the governor before distribution
- Policy rollback commands MUST be verifiable as originating from the governor (prevents spoofed rollbacks)
- The Anthropic API key MUST be stored in `~/.citizenry/api_key` with 0600 permissions, not in code
- Will broadcasts are signed by the dying citizen -- receivers verify authenticity before merging data

### NFR-5: Testability

- NL interpreter MUST be testable with mocked API responses (no real API calls in tests)
- Rollout engine MUST be testable with mock citizens on localhost
- Will mechanism MUST be testable by sending SIGTERM to a test citizen process
- Self-test suite MUST be testable with mock servo bus
- All new modules MUST have unit tests with >80% coverage
- Tests MUST run without hardware and without internet
- Tests MUST complete in < 60 seconds total

### NFR-6: Hardware Constraints

- No CUDA dependencies -- NL interpretation uses Anthropic API (cloud), not local GPU inference
- Anthropic SDK is the only new dependency for core features (FR-1 through FR-3)
- Python 3.12+ on Surface, 3.13+ on Pi
- Consciousness stream on Pi uses templates, not LLM (no new dependencies on Pi)
- Maximum 10MB additional disk for new modules
- API calls are metered -- consciousness stream is rate-limited to prevent cost overrun

### NFR-7: Cost

- Anthropic API usage for NL governance: estimated < $0.01 per policy change (single Claude Haiku call with ~2KB context)
- Consciousness stream (stretch): estimated < $0.10/hour at 12 calls/minute (one per 5s)
- A configurable `monthly_api_budget` law with default $5.00 MUST cap total API spend; system falls back to keyword/template mode when budget is exhausted

---

## Technical Constraints

1. **Transport unchanged** -- UDP multicast + unicast, same ports, same envelope format
2. **7 message types unchanged** -- No new MessageType enum values
3. **New dependency: anthropic SDK** -- For NL governance on Surface only. Pi does not need it.
4. **Backward compatible** -- v2.0 citizens on the network MUST NOT crash when v3.0 messages arrive
5. **Python only** -- No Rust, no C extensions
6. **Same deploy mechanism** -- `deploy.sh` rsync to Pi continues to work
7. **Internet optional** -- NL governance degrades gracefully without internet. Rollout and will work fully offline.

---

## Scope Boundaries

### In Scope (v3.0)

- Natural language policy interpretation (Claude API + keyword fallback)
- Rolling policy updates with canary testing and auto-rollback
- Citizen self-test suite (joint range, load test, fault check)
- Dead citizen's will (signal handler, broadcast, absorption)
- Will archive and task re-listing with partial progress
- Policy history and audit logging
- Dashboard updates for rollout progress, will events, policy history

### In Scope (v3.0 Stretch)

- Emotional state signals (fatigue, confidence, curiosity)
- Consciousness stream (API on Surface, templates on Pi)

### Out of Scope (deferred to v4.0+)

- Federated learning across locations
- Multi-location nation (WireGuard VPN, embassy model)
- Apprenticeship learning (arms watching experienced arms)
- Web-based dashboard (remain terminal TUI)
- Constitutional amendments with safety quorum
- Graceful sovereignty transfer (interim governor election)
- Local LLM on Pi (waiting for better small models)
- Voice input (microphone -> speech-to-text -> NL governance)

---

## Architecture Overview

```
citizenry/
├── __init__.py                 # Package version
├── protocol.py                 # 7-message protocol (unchanged)
├── identity.py                 # Ed25519 keypair management (unchanged)
├── transport.py                # UDP multicast + unicast (unchanged)
├── constitution.py             # Articles, laws, servo limits (unchanged)
├── citizen.py                  # Base citizen (extended: will, policy_version, emotional_state)
├── surface_citizen.py          # Governor (extended: NL interpreter, rollout engine)
├── pi_citizen.py               # Follower arm (extended: self-test, will handler)
├── camera_citizen.py           # USB camera citizen (extended: camera-specific self-test)
├── marketplace.py              # Task lifecycle, auction, bidding (extended: partial progress)
├── skills.py                   # Skill tree, XP tracking (unchanged)
├── symbiosis.py                # Contracts between citizens (unchanged)
├── mycelium.py                 # Warning propagation (unchanged)
├── immune.py                   # Fault pattern learning and sharing (unchanged)
├── genome.py                   # Citizen genome export/import (unchanged)
├── composition.py              # Capability composition discovery (unchanged)
├── nl_governance.py            # NEW: NL intent interpretation (Claude API + fallback)
├── rollout.py                  # NEW: Canary rollout engine
├── self_test.py                # NEW: Citizen self-test suite
├── will.py                     # NEW: Dead citizen's will
├── emotional.py                # NEW (stretch): Emotional state computation
├── consciousness.py            # NEW (stretch): NL state narration
├── telemetry.py                # Servo telemetry (unchanged)
├── persistence.py              # JSON persistence (extended: rollout state, will archive)
├── mdns.py                     # mDNS discovery (unchanged)
├── dashboard.py                # TUI dashboard (extended: rollout, will, emotions)
├── run_surface.py              # Surface entry point (updated: NL input loop)
├── run_pi.py                   # Pi entry point (updated: signal handlers)
├── run_camera.py               # Camera entry point (updated: signal handlers)
├── choreo.py                   # Demo choreography (unchanged)
├── demo.py                     # Demo script (extended)
├── demo_v2.py                  # v2.0 demo (unchanged)
├── deploy.sh                   # Pi deployment (updated: exclude api_key)
└── tests/
    ├── __init__.py
    ├── conftest.py              # Shared fixtures (mock bus, mock camera, mock API)
    ├── test_nl_governance.py    # NL interpretation tests with mocked API
    ├── test_rollout.py          # Canary rollout engine tests
    ├── test_self_test.py        # Self-test suite tests
    ├── test_will.py             # Will broadcast and absorption tests
    ├── test_emotional.py        # Emotional state computation tests (stretch)
    ├── test_consciousness.py    # Consciousness stream tests (stretch)
    ├── test_marketplace.py      # (extended: partial progress)
    ├── test_skills.py           # (unchanged)
    ├── test_symbiosis.py        # (unchanged)
    ├── test_mycelium.py         # (unchanged)
    ├── test_immune.py           # (unchanged)
    ├── test_genome.py           # (unchanged)
    ├── test_composition.py      # (unchanged)
    ├── test_camera_citizen.py   # (unchanged)
    ├── test_integration.py      # Multi-citizen scenarios (extended)
    └── test_protocol_compat.py  # v2.0 backward compatibility
```

---

## Dependencies

### New Python Packages

- `anthropic>=0.40.0` -- Anthropic Python SDK for Claude API (NL governance). Surface only. Not installed on Pi.

### Existing (no changes)

- `pynacl>=1.5.0` -- Ed25519 signing
- `zeroconf>=0.131.0` -- mDNS discovery
- `lerobot==0.5.0` -- Servo control (SO-101)
- `opencv-python-headless>=4.8.0` -- Camera (v2.0)

### Dev/Test

- `pytest>=8.0`
- `pytest-asyncio>=0.23`
- `pytest-cov>=5.0`

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Claude API misinterprets intent | Wrong policy applied (e.g., increase torque instead of decrease) | Medium | Confidence threshold + mandatory confirmation for ambiguous intents; self-test catches dangerous changes |
| API unavailable (no internet, outage) | NL governance non-functional | Medium | Keyword fallback engine handles top 10 intents; manual update_law() always works |
| Will broadcast doesn't complete before process death | Knowledge lost on hard shutdown | High for power cuts | Will is best-effort. Heartbeat death detection + genome system are the reliable fallbacks. |
| Self-test too strict | Valid policies rejected, rollouts fail unnecessarily | Medium | Configurable thresholds per test; governor can force_apply |
| Self-test too lenient | Dangerous policies pass canary | Low | Conservative defaults (50% joint range, zero fault tolerance); immune memory catches issues post-deployment |
| Rollout too slow for time-sensitive changes | Emergency policy takes 60s to propagate | Low | force_apply bypass for emergency_stop and critical safety changes |
| API cost overrun from consciousness stream | Unexpected charges | Medium | monthly_api_budget law with hard cap; template fallback |
| Signal handler race condition | Will corrupted or partial | Low | Will is a single atomic JSON blob; receivers validate structure |

---

## Glossary

| Term | Definition |
|------|-----------|
| NL Governance | Natural language policy interpretation -- translating English intent to formal law changes |
| Policy Intent | A natural language string expressing a desired system behavior change |
| Rollout | The process of distributing a policy change to citizens one at a time with testing |
| Canary | The first citizen to receive a policy change during a rollout, acting as a test subject |
| Self-Test | An automated check a citizen runs after receiving a policy change to verify it can still function |
| Rollback | Reverting a policy change to the previous state after a canary failure |
| Will | A dying citizen's final broadcast containing its current state and knowledge |
| Emotional State | Composite metrics (fatigue, confidence, curiosity) derived from real telemetry (stretch) |
| Consciousness Stream | Natural language narration of a citizen's current state and reasoning (stretch) |
| Keyword Fallback | A hardcoded NL interpreter that handles common intents without an API call |
| Policy Version | A monotonic integer incremented on each law change, used to track policy currency |
