---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
inputDocuments:
  - product-brief-v4.md
  - citizenry/SOUL.md
  - citizenry/RESEARCH-robot-memory.md
  - citizenry/RESEARCH-reflexes.md
  - citizenry/RESEARCH-pain-proprioception-sleep.md
  - citizenry/RESEARCH-spatial-awareness.md
  - citizenry/GROWTH.md
  - docs/research-robot-metabolism.md
workflowType: 'prd'
---

# Product Requirements Document — armOS v4.0 "The Living Machine"

**Author:** Bradley
**Date:** 2026-03-16
**Version:** 4.0
**Status:** Draft for review

---

## Executive Summary

armOS v3.0 gave the citizenry a brain (governance), nerves (protocol), DNA (genome), and an immune system (fault patterns). **v4.0 makes it alive.** Nine biological subsystems transform each citizen from a reactive automaton into a living entity that develops personality, remembers experiences, reacts reflexively to danger, feels pain and learns to avoid it, knows where its body is in space, manages its energy, sleeps for maintenance, and grows from a helpless newborn into a capable adult.

The biological metaphor is not decorative -- it is the architecture. Every subsystem solves a real engineering problem that v3.0 leaves unaddressed: robots that repeat the same mistakes, cannot protect themselves faster than the governor can respond, have no notion of physical self, waste power until brownout, never rest, and never mature.

**Scope:** 9 new modules (~3,000-4,000 lines of pure Python), zero new protocol message types, one new required dependency (numpy), one optional dependency (cma). All new behavior is opt-in: a v3.0 citizen joining a v4.0 fleet still works. A v4.0 citizen on a v3.0 fleet degrades gracefully to v3.0 behavior.

---

## Vision

**"Robots that live, learn, and grow."**

Two identical SO-101 arms come out of the same box. After a week of operation, they are recognizably different citizens. One has become the careful one -- it moves slowly, grips gently, and specializes in delicate tasks. The other is the fast one -- it prefers speed, handles heavy objects, and volunteers for rush jobs. Neither was configured this way. Their experiences shaped them.

When the careful arm encounters a joint configuration that caused pain last week, it routes around it automatically. When the fast arm's power supply sags, it reduces speed before brownout hits. When both arms are idle at 2 AM, they sleep -- consolidating the day's experiences into durable knowledge, pruning stale memories, and checking calibration.

A new arm joins the fleet and starts as a NEWBORN. It cannot bid on marketplace tasks. It can only follow teleop commands and learn its own body. After calibration and successful teleop sessions, it earns INFANT status. Over hundreds of tasks, it progresses through CHILD, JUVENILE, ADULT, and eventually ELDER -- each stage unlocking new capabilities and autonomy. Trust is earned, not configured.

The user sees all of this on the existing web dashboard: personality traits, memory counts, growth stage, sleep schedule, pain history, metabolic state. The system feels alive because it is -- not through simulation, but through genuine adaptation to experience.

---

## Problem Statement

armOS v3.0 citizens are capable but memoryless, unaware, and undifferentiated:

1. **No experiential memory.** A citizen that fails a grasp 10 times in a row has no record of those failures beyond immune fault patterns. It cannot recall "I tried to pick up the red block at 14:32 and the gripper slipped because my approach angle was wrong."

2. **No fast reflexes.** All safety responses route through the governor or scattered if-statements. A voltage collapse can destroy hardware before the async event loop processes the telemetry reading.

3. **No body awareness.** Citizens read raw servo ticks but have no geometric model. They cannot answer "where is my gripper in space?" or "am I about to collide with my own base?"

4. **No power management.** Citizens draw power until brownout. Two arms on the same PSU can simultaneously stall and collapse the voltage rail. There is no admission control, no duty cycle tracking, no predictive budgeting.

5. **No avoidance learning.** A joint configuration that caused overcurrent yesterday will cause overcurrent again today. There is no pain memory, no avoidance zones, no behavioral change from damage.

6. **No maintenance cycles.** Citizens run until fatigue accumulates, with no mechanism to consolidate memory, prune stale data, check calibration drift, or optimize the genome.

7. **No developmental progression.** A brand-new citizen has the same capabilities and trust level as one that has completed 1,000 tasks. There is no concept of maturity, earned autonomy, or specialization.

8. **No identity divergence.** Two citizens with the same genome behave identically. There is no personality, no preferences, no individuality emerging from experience.

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Reflex response time | < 10ms from trigger to servo command | Timestamp diff in reflex log |
| Self-collision prevention | 100% -- never self-collide | Zero self-collision events in test suite |
| Multi-arm collision prevention | 100% in shared zones | Zero collision events during multi-arm tasks |
| Pain avoidance learning | Avoid repeated fault within 3 occurrences | Same fault type does not recur at same joint configuration |
| Sleep consolidation | Memory reduced 50%+ while retaining key knowledge | Episode count before/after consolidation |
| Growth progression | Citizen reaches ADULT stage within 500 tasks | Task counter at stage promotion |
| Strategy improvement | 10%+ success rate gain via CMA-ES after 50 evaluations | Success rate delta in performance tracker |
| Personality stability | Big Five drift < 0.1 per 100 tasks | Max trait delta over 100-task windows |
| Brownout prevention | Zero unprotected voltage collapses | Brownout protocol fires before hardware protection |
| Backward compatibility | v3.0 citizens interoperate with v4.0 fleet | Integration test: mixed-version fleet completes tasks |
| Test coverage | 350+ tests (v3.0 has 297) | pytest count |

---

## User Journeys

### Journey 1: The Robot That Learns From Pain

Marcus has two SO-101 arms on the same table. Arm-alpha is picking blocks when its elbow servo stalls against a table edge. The reflex engine fires in 8ms -- reducing velocity before the governor even knows. The pain system records the event: joint positions, intensity, cause. Next time arm-alpha plans a trajectory through that region, the pain memory adds an avoidance cost that routes the arm around the danger zone. After three similar incidents in different configurations, arm-alpha has learned a "no-go zone" near the table edge that persists across reboots.

### Journey 2: The Robot That Sleeps

It is 2 AM. Both arms have been idle for 30 minutes. Sleep pressure has accumulated from 18 hours of uptime and 47 unconsolidated episodes. Arm-alpha enters DROWSY, then LIGHT_SLEEP. During light sleep, the consolidation engine processes 47 episodes: 12 high-importance failures become semantic knowledge ("red blocks on the left table are heavier than expected"), 8 successful grasps refine procedural memory (optimal approach angle updated from 25 to 28 degrees), and 27 routine episodes are compressed or pruned.

During DEEP_SLEEP, immune memory is optimized (3 stale patterns pruned), calibration drift is checked (all joints within tolerance), and the genome is compressed. During REM, the 5 most surprising episodes are replayed -- strengthening the procedural memory for the failure cases.

At 5 AM, a CRITICAL alert from the governor wakes arm-alpha from light sleep within 200ms. Arm-beta, in deep sleep, continues sleeping -- only EMERGENCY events wake from deep sleep.

### Journey 3: The Robot That Grows Up

A new SO-101 arm joins the fleet. It starts at NEWBORN stage: it can accept teleop commands but cannot bid on marketplace tasks, propose flight plans, or operate autonomously. After calibration and self-test (INFANT), then 5 successful teleop sessions (CHILD), it begins executing supervised tasks. After 50 successful tasks at 70%+ success rate (JUVENILE), it can bid on marketplace tasks. After 100 autonomous tasks at 85%+ success rate with governor certification (ADULT), it can coordinate multi-citizen tasks. The camera citizen, having observed 20 successful grasps, broadcasts a signed endorsement that accelerates the arm's growth.

### Journey 4: The Robot With Personality

After a month of operation, arm-alpha and arm-beta have diverged. Arm-alpha has higher conscientiousness (0.82) and lower movement_style (0.28) -- it developed a preference for slow, precise movements because those succeeded more often for the delicate tasks it was assigned. Arm-beta has higher extraversion (0.71) and higher movement_style (0.67) -- it volunteered for collaborative tasks and learned that speed was rewarded. Neither was configured this way. Their souls emerged from experience.

### Journey 5: The Robot That Manages Power

Two arms share a 5A PSU. Arm-alpha is executing a pick-and-place (sustained 2.5A). Arm-beta receives a task requiring 3.5A peak. The power ledger computes: 2.5 + 3.5 = 6.0A > 5.0A limit. Arm-beta's bid is rejected due to insufficient power headroom. It waits for arm-alpha to finish, then executes. During the task, voltage dips to 9.8V -- the brownout protocol enters WARNING stage, reducing arm-beta's speed by 25%. The voltage recovers. No brownout occurs.

---

## Domain Model

```
                 ┌──────────────────────────────────────┐
                 │           CITIZEN (v4.0)              │
                 │                                      │
                 │  ┌────────┐  ┌────────┐  ┌────────┐ │
                 │  │ Soul   │  │ Memory │  │ Growth │ │
                 │  │        │  │        │  │        │ │
                 │  │persona │  │episodic│  │stage   │ │
                 │  │goals   │  │semantic│  │autonomy│ │
                 │  │prefs   │  │proced. │  │special.│ │
                 │  │values  │  │consol. │  │gates   │ │
                 │  └────────┘  └────────┘  └────────┘ │
                 │                                      │
                 │  ┌────────┐  ┌────────┐  ┌────────┐ │
                 │  │ Reflex │  │ Pain   │  │ Proprio│ │
                 │  │        │  │        │  │ ception│ │
                 │  │rules   │  │events  │  │FK model│ │
                 │  │engine  │  │avoid.  │  │body    │ │
                 │  │deriv.  │  │referred│  │state   │ │
                 │  │sympathy│  │chronic │  │forces  │ │
                 │  └────────┘  └────────┘  └────────┘ │
                 │                                      │
                 │  ┌────────┐  ┌────────┐  ┌────────┐ │
                 │  │Metabol.│  │ Sleep  │  │Spatial │ │
                 │  │        │  │        │  │Aware.  │ │
                 │  │power   │  │4 phase │  │capsules│ │
                 │  │brownout│  │pressure│  │zones   │ │
                 │  │ledger  │  │consol. │  │flight  │ │
                 │  │duty cyc│  │dreams  │  │handoff │ │
                 │  └────────┘  └────────┘  └────────┘ │
                 │                                      │
                 │  ┌──────────────────────────────────┐│
                 │  │ Self-Improvement (improvement.py) ││
                 │  │ perf tracker | strategy selector  ││
                 │  │ param evolution | failure analysis ││
                 │  │ practice mode                     ││
                 │  └──────────────────────────────────┘│
                 │                                      │
                 │  ┌──────────────────────────────────┐│
                 │  │ v3.0 Foundation (unchanged)       ││
                 │  │ protocol | governance | genome    ││
                 │  │ marketplace | immune | emotional  ││
                 │  │ skills | HAL | mycelium           ││
                 │  └──────────────────────────────────┘│
                 └──────────────────────────────────────┘
```

### Module Dependency Map

```
soul.py ──────────► personality, goals, preferences, values, identity
memory.py ─────────► episodic, semantic, procedural, consolidation
improvement.py ────► performance tracker, strategy selector, CMA-ES, practice
reflex.py ─────────► 100Hz engine, declarative rules, derivative triggers
metabolism.py ─────► metabolic state, brownout protocol, power ledger, duty cycle
pain.py ───────────► pain events, avoidance zones, referred pain, chronic detection
proprioception.py ─► forward kinematics, body schema, joint limits, force estimation
sleep.py ──────────► 4-phase cycle, sleep pressure, consolidation dispatch, dreams
growth.py ─────────► developmental stages, autonomy levels, capability gates, specialization
spatial.py ────────► capsule collision, zone architecture, flight plans, object handoff
```

**Key dependency chain:** `reflex.py` depends on nothing (runs independently). `pain.py` depends on `reflex.py` (pain events originate from reflex triggers). `proprioception.py` depends on nothing (pure geometry). `spatial.py` depends on `proprioception.py` (capsule positions come from FK). `sleep.py` depends on `memory.py` (consolidation operates on memory). `improvement.py` depends on `memory.py` (performance tracking uses episodic data). `soul.py` depends on nothing (personality is a standalone dataclass). `growth.py` depends on `soul.py` and `memory.py` (maturation checks personality stability and task history). `metabolism.py` depends on nothing (reads raw telemetry).

---

## Functional Requirements

### FR-1: Soul (soul.py)

**FR-1.1 Personality Profile.** The system MUST implement a `PersonalityProfile` with Big Five (OCEAN) dimensions (openness, conscientiousness, extraversion, agreeableness, neuroticism), each a float in [0.0, 1.0], plus armOS-specific behavioral dimensions: movement_style, exploration_drive, social_drive, teaching_drive, independence.

**FR-1.2 Personality Seeding.** When a citizen boots for the first time, personality MUST be derived from its genome (hardware type, role) plus a small random perturbation (uniform +/- 0.1). A manipulator arm starts with high conscientiousness (0.7) and moderate movement_style (0.5). A camera citizen starts with high openness (0.7) and extraversion (0.6).

**FR-1.3 Personality Drift.** Personality traits MUST mutate slowly based on experience. Successful task completions nudge relevant traits by delta * drift_rate, where drift_rate defaults to 0.01 per 1,000 interactions. All trait values MUST remain clamped to [0.0, 1.0]. Drift per 100 tasks MUST be less than 0.1 on any single trait.

**FR-1.4 Personality Influence on Behavior.** Personality MUST bias marketplace bidding: high-conscientiousness citizens bid with longer estimated time but higher quality guarantee. High-extraversion citizens get a bonus for collaborative tasks. High-neuroticism citizens get a penalty for risky or novel tasks. Personality does not make decisions -- it modulates bid scores by +/- 15% maximum.

**FR-1.5 Goal Hierarchy.** The system MUST implement a `GoalHierarchy` with 5 priority tiers: SURVIVAL (0), OBLIGATION (1), COMMITMENT (2), ASPIRATION (3), CURIOSITY (4). Higher-priority goals always preempt lower-priority ones. The `select_next_goal()` method returns the highest-priority actionable goal.

**FR-1.6 Intrinsic Motivation.** When no external goals exist (citizen is idle), the goal hierarchy MUST generate intrinsic goals based on personality: high openness generates exploration goals, high conscientiousness generates calibration refinement goals, high neuroticism generates self-diagnostic goals. Idle citizens MUST NOT remain idle for more than 60 seconds without generating an intrinsic goal.

**FR-1.7 Behavioral Preferences.** The system MUST implement `BehavioralPreferences` tracking per-task success rates by movement style parameters (speed, smoothness, grip force, approach angle). After each task completion, preferences MUST update via exponential moving average (alpha=0.1). Successful high-quality outcomes (quality > 0.8) nudge global preferences toward the successful style at 5% drift rate.

**FR-1.8 Value System.** The system MUST implement a 3-tier `ValueSystem`: Constitutional values (immutable, from Articles 1-5), Normative values (governor-adjustable: risk_tolerance, autonomy_level, resource_sharing, privacy_respect), and Learned values (self-adjusting: trust scores per citizen, cooperation_value, caution_value, efficiency_value). A `check_action()` method MUST return (permitted, reason) for any proposed action. Constitutional checks are absolute and NEVER overridden.

**FR-1.9 Identity Continuity.** The Ed25519 private key MUST remain the sole determinant of identity. Hardware changes MUST be logged as LifeEvents in the autobiography but MUST NOT alter identity. The Soul MUST persist across reboots, hardware swaps, and software updates via the genome. A `continuity_score()` method MUST compute identity continuity from hardware changes, memory depth, and relationship count.

**FR-1.10 Autobiography.** The system MUST maintain a list of `LifeEvent` records for significant moments: birth, first task, hardware swap, achievement, failure, friendship. Each event includes timestamp, event_type, description, emotional_impact (-1.0 to 1.0), and participant pubkeys.

---

### FR-2: Memory (memory.py)

**FR-2.1 Episodic Memory.** The system MUST implement `EpisodicMemory` storing `Episode` records with: id (UUID), timestamp, citizen_id, location, event_type, description, context (structured dict), outcome (success/failure/partial), importance (0.0-1.0), and tags (searchable labels). Episodes MUST be created on task start, task complete, task fail, and significant sensor events.

**FR-2.2 Importance Scoring.** Episode importance MUST be computed at write time from four factors: recency (exponential decay), significance (failures score higher than routine successes), novelty (first-time events score higher), and emotional valence (high-stress states boost importance). The formula MUST be: `importance = 0.3 * recency + 0.3 * significance + 0.2 * novelty + 0.2 * emotional_valence`.

**FR-2.3 Episodic Retrieval.** The system MUST support retrieval by: tags/keywords, time range, event type, and outcome. Retrieval scoring MUST combine recency (exponential decay, hourly), importance, and tag overlap: `score = 0.3 * recency + 0.3 * importance + 0.4 * tag_overlap`. No embedding-based retrieval (no GPU).

**FR-2.4 Semantic Memory.** The system MUST implement `SemanticMemory` as a JSON property graph with `KnowledgeNode` (id, node_type, properties, confidence, last_updated, source_episodes) and `KnowledgeEdge` (source, target, relation, confidence, last_updated, source_episodes). Supported relation types: spatial (located_at, near, left_of, above, inside), causal (causes, prevents, requires), property (has_property, weighs, colored), temporal (usually_at), social (owned_by, used_by).

**FR-2.5 Confidence Decay.** Knowledge edge confidence MUST decay over time with a configurable half-life (default 30 days). Edges with confidence below 0.1 MUST be pruned during consolidation.

**FR-2.6 Procedural Memory.** The system MUST implement `ProceduralMemory` storing `Procedure` records with: skill_name, parameters (dict of learned values), success_rate, avg_duration, context_conditions (when to use), source (learned/demonstrated/shared), use_count, and learned_from_episodes. Multiple procedures per skill MUST be supported. The `get_best_procedure()` method MUST select the highest success_rate procedure matching the current context.

**FR-2.7 Consolidation Engine.** The system MUST implement memory consolidation that: (a) extracts semantic knowledge from episodes (same object at same location 3+ times creates/strengthens a `located_at` edge), (b) refines procedural memory from episodes (after N successful completions, extract average parameters), (c) prunes episodes older than retention_days (default 7) with importance below threshold (default 0.2), (d) prunes knowledge edges below confidence 0.1, (e) prunes unused procedures older than 30 days. Consolidation MUST run during sleep (FR-8) or idle periods.

**FR-2.8 Fleet Memory Sharing.** Citizens MUST share learned knowledge via the existing protocol (no new message types). KNOWLEDGE_GOSSIP MUST be carried in REPORT message bodies containing subject, relation, object, confidence, and timestamp. Receiving citizens MUST merge incoming knowledge weighted by sender trust score. Episode sharing MUST be request/response via existing unicast. Procedure sharing MUST be offered via REPORT when success_rate exceeds 0.85 and use_count exceeds 20.

**FR-2.9 Persistence.** All memory MUST persist as JSON files in `~/.citizenry/`: `<name>.episodes.json`, `<name>.knowledge.json`, `<name>.procedures.json`. Save MUST use atomic writes (write to temp, rename). Load MUST handle missing or corrupt files gracefully (start with empty memory).

---

### FR-3: Self-Improvement (improvement.py)

**FR-3.1 Performance Tracker.** The system MUST track per-skill success rate over a sliding window (default 100 tasks). The tracker MUST compute trend (improving/stable/degrading) using linear regression over the window. A regression alert MUST fire when success rate drops more than 10% over 50 tasks.

**FR-3.2 Strategy Selector.** The system MUST implement a UCB1 (Upper Confidence Bound) multi-armed bandit per task type. Each "arm" is a strategy (combination of movement style parameters). UCB1 balances exploration of new strategies with exploitation of known-good ones. The exploration weight MUST be configurable (default: sqrt(2)).

**FR-3.3 Parameter Evolution.** The system MUST support CMA-ES (Covariance Matrix Adaptation Evolution Strategy) for continuous skill parameters (approach speed, grip force, approach angle). CMA-ES MUST be imported from the optional `cma` package. If `cma` is not installed, parameter evolution MUST fall back to random perturbation with selection of the best. The objective function is task success quality (0.0-1.0). Population size MUST default to 8. A 10%+ success rate improvement MUST be achievable within 50 evaluations.

**FR-3.4 Failure Analysis.** When a task fails, the system MUST capture a telemetry snapshot (all servo readings at failure time) and compare it to the last successful execution of the same skill. The diff MUST be stored as a hypothesis: "failure occurred when elbow_flex was 200 ticks higher than successful baseline." Hypotheses MUST be validated by checking whether subsequent executions avoiding the hypothesized condition succeed.

**FR-3.5 Practice Mode.** Idle citizens MUST generate practice goals from the learning-progress heuristic: skills where recent improvement rate is highest get priority (the citizen practices what it is currently learning fastest). Practice MUST use the strategy selector (FR-3.2) to explore new approaches. Practice goals MUST have CURIOSITY priority (lowest tier) and yield immediately to any external goal.

---

### FR-4: Reflexes (reflex.py)

**FR-4.1 Reflex Engine.** The system MUST implement a 100Hz reflex loop that runs independently of the citizen's main async event loop. The loop MUST: (a) read telemetry from the servo bus, (b) evaluate declarative reflex rules in priority order, (c) execute the highest-priority triggered reflex, (d) notify the governor asynchronously (non-blocking). The entire evaluate-and-act cycle MUST complete within 10ms.

**FR-4.2 Declarative Reflex Rules.** Reflexes MUST be defined as `ReflexRule` dataclass instances with: id, priority (lower = higher priority), condition (`ReflexCondition`), action (`ReflexAction`), cooldown_ms, notify_governor (bool), and description. Conditions specify sensor, scope (per_servo/aggregate), operator, threshold, and sustain_ms (debounce). Actions specify action_type (reduce_velocity, disable_torque, reverse, hold), scope (triggering_servo, all_servos, arm), parameter, and duration_ms.

**FR-4.3 Hardcoded Reflex Table.** The system MUST ship with the following reflex rules, in priority order:

| Priority | Rule ID | Condition | Action |
|----------|---------|-----------|--------|
| 0 | voltage_collapse | Any servo voltage < 6.0V | Disable torque on all servos |
| 1 | emergency_stop | Governor command | Disable torque on all servos |
| 2 | overcurrent_critical | Any servo current > 1000mA for 20ms | Disable torque on triggering servo |
| 3 | temperature_critical | Any servo temp > 70C | Disable torque on triggering servo |
| 4 | collision_detect | Load derivative > 80% in 20ms | Reverse triggering servo 10 ticks |
| 5 | overcurrent_warning | Any servo current > 800mA for 50ms | Reduce triggering servo velocity 50% |
| 6 | temperature_warning | Any servo temp > 60C | Reduce triggering servo velocity 25% |
| 7 | position_error | Position error > 200 ticks for 100ms | Stop triggering servo |

**FR-4.4 Compound Conditions.** The system MUST support AND/OR composition of conditions via `CompoundCondition`. Example: jam detection = high current AND position error. Compound conditions MUST evaluate all sub-conditions in a single pass.

**FR-4.5 Derivative Triggers.** The reflex engine MUST maintain a rolling window of the last 10 telemetry readings (100ms at 100Hz). A `derivative>` operator MUST compute rate-of-change per second for any sensor field. This enables collision detection: load spike from 10% to 85% in 20ms is a collision; steady 60% load is normal heavy lifting.

**FR-4.6 Reflex Recovery.** After a reflex fires, the system MUST enter a recovery state: REFLEX_ACTIVE (mitigation in effect) -> RECOVERY (condition cleared, ramp back to normal over 500ms) -> NORMAL. If the condition persists beyond 5 seconds, the state MUST escalate to REFLEX_ESCALATED and notify the governor for intervention.

**FR-4.7 Distributed Sympathy.** When a citizen fires a reflex with severity >= CRITICAL, it MUST broadcast a warning via mycelium. Citizens in the same workspace zone MUST evaluate a local sympathetic reflex: slow down by 25% for 200ms (not 50% -- sympathetic reflexes are weaker than direct reflexes). Sympathetic warnings MUST carry hop_count. Warnings with hop_count > 1 MUST NOT be re-propagated (cascade damping).

**FR-4.8 Immune Integration.** If the same reflex rule fires 3+ times within 60 seconds, the reflex engine MUST create an immune memory entry with the triggering conditions and the effective mitigation. This converts transient reflexes into learned fault patterns.

**FR-4.9 GC Management.** The reflex loop MUST disable Python garbage collection during the evaluate-and-act cycle and manually trigger collection between cycles. This prevents GC pauses from delaying safety-critical responses.

---

### FR-5: Metabolism (metabolism.py)

**FR-5.1 Metabolic State Tracking.** The system MUST compute instantaneous power per servo as `voltage * current_ma / 1000.0` (watts) and classify total arm power into metabolic states: idle (< 25% of PSU capacity), resting (25-45%), active (45-70%), peak (70-85%), critical (> 85%). MetabolicState MUST include sliding-window averages at 1s, 10s, 60s, and 300s intervals, plus cumulative energy_consumed_wh and peak_power_w.

**FR-5.2 Brownout Protocol.** The system MUST implement a 4-stage voltage threshold protocol: NORMAL (>= 10V, full operation), WARNING (8-10V, log + reduce speed 50% + broadcast mycelium warning), BROWNOUT (6-8V, disable non-critical servos + reduce all torque 50% + reject new bids + alert governor), CRITICAL (< 6V, disable ALL torque immediately + broadcast EMERGENCY_STOP). Software thresholds MUST be lower than hardware protection thresholds to allow graceful degradation before hardware cutoff.

**FR-5.3 Voltage Sag Detection.** The system MUST detect PSU current limiting from voltage telemetry using a rolling baseline (max of last 10 readings) and sag threshold (default 1.0V). Sag events MUST be counted and persisted in the genome. Hysteresis MUST prevent repeated detection of the same sag (clear at 50% of threshold).

**FR-5.4 Power Ledger.** The system MUST implement a `PowerLedger` that tracks power allocations across all citizens sharing a PSU. The ledger MUST maintain: psu_max_a, per-citizen reserved amps, and a 0.5A safety margin. `can_allocate()` MUST return false if the requested current plus existing allocations plus safety margin exceeds PSU capacity.

**FR-5.5 Power-Aware Bidding.** Marketplace bid scoring MUST include power headroom as a dimension. Citizens MUST NOT bid on tasks whose estimated_peak_current_a exceeds available headroom. Citizens in "peak" or "critical" metabolic state MUST refuse all new task bids. The bid score formula MUST weight power_headroom at 25% alongside capability (30%), availability (25%), and health (20%).

**FR-5.6 Duty Cycle Tracking.** The system MUST track per-servo duty cycle (fraction of time under load > 30%) over 1-hour and 24-hour windows. If 1-hour duty cycle exceeds 70%, the citizen MUST report itself as fatigued and refuse high-load tasks for a configurable rest period (default 5 minutes).

**FR-5.7 Task Power Profiles.** The system MUST maintain learned power profiles per task type (peak_a, sustained_a, duration_s, energy_wh). Initial estimates MUST be hardcoded. After each task completion, actual telemetry MUST update the profile via exponential moving average. Profiles MUST persist in the genome.

**FR-5.8 Servo Fatigue Tracking.** The system MUST track per-servo lifetime counters in the genome: total_operating_hours, total_high_load_hours (>70% load, counted at 3x wear rate), total_overload_events, total_thermal_cycles, total_stall_events. An estimated_remaining_hours value MUST be computed from these counters against a 20,000-hour baseline.

**FR-5.9 Metabolic Heartbeat.** Citizens MUST include metabolic_state (idle/resting/active/peak/critical) and current_draw_a in heartbeat messages. The governor and neighbors MUST be able to see power stress before assigning tasks.

---

### FR-6: Pain (pain.py)

**FR-6.1 Pain Events.** The system MUST implement `PainEvent` with: id, timestamp, joint, pain_type (sharp/burning/aching), intensity (0.0-1.0 nonlinear scale), cause (overcurrent/overtemp/collision/position_error), context (what the robot was doing), position_at_onset (all joint positions), recovery_action, resolved flag, and duration. Pain intensity MUST be computed using a sigmoid function mapping sensor values to proximity-to-damage, not proportional to the raw sensor reading.

**FR-6.2 Pain Intensity Classification.** Pain events MUST be classified into 5 behavioral levels: DISCOMFORT (0.0-0.2, log only), MODERATE (0.2-0.4, slow affected joint + record memory), SIGNIFICANT (0.4-0.6, alter trajectory + warn neighbors), SEVERE (0.6-0.8, abort task + retreat + create immune entry), EMERGENCY (0.8-1.0, disable torque via reflex + broadcast emergency + create permanent avoidance zone).

**FR-6.3 Avoidance Zones.** Pain events with intensity > 0.3 MUST create or reinforce `PainMemory` records containing: joint_positions (the configuration that hurt), avoidance_radius (proportional to intensity, in servo ticks), occurrence_count, confidence (decays over time). A `check_trajectory()` method MUST return avoidance costs for any planned trajectory that passes through an avoidance zone. Avoidance cost MUST be: `proximity * intensity * confidence`, where proximity is 1.0 at the zone center and 0.0 at the radius boundary.

**FR-6.4 Avoidance Zone Decay.** Avoidance zone confidence MUST decay exponentially: `confidence *= 0.999 ** age_hours`. Zones with confidence below 0.05 MUST be pruned. Repeated pain at the same location MUST reinforce the zone (reset confidence to 1.0, increment occurrence_count, expand radius by 10%).

**FR-6.5 Referred Pain.** When a pain event occurs on a joint, the system MUST check adjacent joints (per the SO-101 adjacency map: shoulder_pan <-> shoulder_lift <-> elbow_flex <-> wrist_flex <-> wrist_roll <-> gripper) for elevated load/current/temperature. If found, a `ReferredPain` record MUST be created linking primary and affected joints with a correlation score.

**FR-6.6 Chronic Pain Detection.** Pain events lasting more than 30 seconds MUST be classified as chronic. Chronic pain MUST trigger: (a) a maintenance request to the governor, (b) a permanent avoidance zone, (c) reduction of the affected joint's maximum torque claim in the genome. Chronic pain indicates mechanical issues (stripped gear, worn bearing, calibration drift).

**FR-6.7 Sensitization and Habituation.** Repeated pain at the same joint MUST increase pain_sensitivity (hyperalgesia): `sensitivity = min(2.0, sensitivity * 1.2)`. Repeated benign stimuli (telemetry spikes that do not result in actual damage) MUST decrease sensitivity (habituation): `sensitivity = max(0.5, sensitivity * 0.95)`.

**FR-6.8 Pain-Emotional Integration.** Pain events MUST increase emotional fatigue proportionally to intensity. Current aggregate pain level MUST be available via `current_pain_level()` (max intensity of active events) for use by the emotional state system, the goal hierarchy (pain creates SURVIVAL-priority avoidance goals), and the sleep pressure calculator.

---

### FR-7: Proprioception (proprioception.py)

**FR-7.1 Forward Kinematics.** The system MUST implement forward kinematics for the SO-101 using the known link lengths: base_height (55mm), upper_arm (104mm), forearm (88mm), wrist (35mm), gripper (60mm). The FK function MUST accept joint angles in servo ticks, convert to radians via `(ticks - 2048) / (4096/360) * pi/180`, and return CartesianPose (x, y, z in mm) for the gripper tip. The computation MUST complete in < 0.1ms.

**FR-7.2 Body Schema.** The system MUST maintain a `BodyState` dataclass integrating: joint_positions (raw ticks), joint_angles_rad, joint_velocities, joint_loads (%), joint_currents (mA), joint_temperatures (C), computed elbow/wrist/gripper CartesianPose, joint_limit_proximity (0.0 at center, 1.0 at limit), and estimated_payload_grams. BodyState MUST update every telemetry cycle (100Hz in the reflex loop, 10Hz in the main loop).

**FR-7.3 Joint Limit Proximity.** The system MUST compute proximity to joint limits for all 6 joints using the SO-101 joint limit table. Proximity MUST be `abs(position - center) / half_range`. A warning MUST be generated when any joint exceeds 0.9 proximity. Joint limits: shoulder_pan (1024-3072), shoulder_lift (1200-2200), elbow_flex (2000-3200), wrist_flex (1024-3072), wrist_roll (1024-3072), gripper (1400-2600).

**FR-7.4 Force Estimation.** The system MUST estimate joint force from current draw: `force_N = (current_mA / 1000) * Kt / lever_arm`, where Kt = 0.015 Nm/A (STS3215 approximate) and lever_arm = 0.1m (average). This is approximate but sufficient for detecting unexpected loads, collisions, and estimating payload weight.

**FR-7.5 Payload Estimation.** The system MUST estimate held payload weight from gripper current draw by subtracting no-load current (80mA baseline) and applying a gravity-torque conversion factor. The estimate MUST be calibrated over time using known-weight objects recorded in semantic memory.

**FR-7.6 Calibration Drift Detection.** The system MUST implement a `DriftDetector` that compares current positions at known reference configurations against stored calibration baselines. RMS error across all joints MUST be computed. If error exceeds 30 ticks, the system MUST flag for recalibration and report to the governor.

**FR-7.7 Self-Collision Checking.** The system MUST check non-adjacent link pairs for collision risk using simplified bounding sphere checks. Checked pairs: base-forearm, base-wrist, base-gripper, upper_arm-wrist, upper_arm-gripper (5 pairs). A warning MUST be generated when any pair is within 80mm. This check MUST run at servo command time (before sending positions to the bus).

**FR-7.8 Capsule Model.** The system MUST implement capsule representations for each arm link (line segment + radius): base (30mm), upper_arm (20mm), forearm (18mm), wrist (15mm), gripper (25mm). Capsule endpoints MUST be computed from forward kinematics. The capsule model MUST be shared via heartbeat spatial data for use by the spatial awareness system (FR-9).

---

### FR-8: Sleep (sleep.py)

**FR-8.1 Four-Phase Sleep Cycle.** The system MUST implement a sleep cycle with 4 phases: DROWSY (2 minutes -- reduce activity, announce sleep to neighbors), LIGHT_SLEEP (20 minutes -- memory consolidation, still responsive to CRITICAL and EMERGENCY), DEEP_SLEEP (40 minutes -- heavy maintenance, only EMERGENCY wakes), REM (20 minutes -- dream replay of prioritized episodes). Total cycle: ~82 minutes.

**FR-8.2 Sleep Pressure.** The system MUST compute sleep pressure from 4 factors: uptime_hours (weight 0.3, normalized to 8 hours), fatigue (weight 0.25, from emotional state), unconsolidated_episodes (weight 0.25, normalized to 50 episodes), time_since_last_sleep_hours (weight 0.2, normalized to 24 hours). Sleep MUST be entered when pressure > 0.7 AND the citizen is idle AND no tasks are active. Sleep MUST NOT be entered during active tasks.

**FR-8.3 Wake Thresholds.** EMERGENCY events (severity >= 3) MUST always wake the citizen from any sleep phase within 200ms. CRITICAL events (severity >= 2) MUST wake from DROWSY and LIGHT_SLEEP only. No events below CRITICAL MUST wake from DEEP_SLEEP or REM. On wake, the citizen MUST transition directly to AWAKE (no gradual ramp).

**FR-8.4 Light Sleep Consolidation.** During LIGHT_SLEEP, the system MUST: (a) process all unconsolidated episodes, scoring by importance, (b) extract semantic knowledge from high-importance episodes (importance > 0.6), (c) refine procedural memory from successful episodes, (d) compress context of medium-importance episodes (0.3-0.6), (e) mark low-importance episodes (< 0.3) as prune candidates. Episode count and knowledge facts added MUST be logged.

**FR-8.5 Deep Sleep Maintenance.** During DEEP_SLEEP, the system MUST: (a) prune stale immune memory patterns (LRU, existing mechanism), (b) run calibration drift check (FR-7.6), (c) rotate and compress logs, (d) optimize genome storage (remove redundant entries), (e) decay pain memory confidence (FR-6.4). Bytes freed and patterns pruned MUST be logged.

**FR-8.6 REM Dream Replay.** During REM, the system MUST select the top 10 most important episodes from the last 24 hours using prioritized sampling: `priority = importance * 0.4 + surprise * 0.4 + recency * 0.2`, where surprise = 1.0 for failures, 0.3 for successes. Each replayed episode MUST: reinforce the procedure used (if success) or strengthen avoidance of failure conditions (if failure). Episodes replayed MUST be logged.

**FR-8.7 Sleep Schedule.** The system MUST support a configurable sleep schedule: preferred_sleep_time (default 2:00), preferred_wake_time (default 6:00), min_awake_hours (default 4). Time-based triggers MUST combine with pressure-based triggers (either can initiate sleep).

**FR-8.8 Sleep Announcement.** Before entering DROWSY, the citizen MUST broadcast a "going to sleep" message on the mycelium network so neighbors know not to assign tasks. On wake, the citizen MUST broadcast "awake" and re-announce capabilities.

---

### FR-9: Growth + Spatial Awareness (growth.py, spatial.py)

#### Growth (growth.py)

**FR-9.1 Developmental Stages.** The system MUST implement 6 developmental stages: NEWBORN (0), INFANT (1), CHILD (2), JUVENILE (3), ADULT (4), ELDER (5). Stages MUST gate protocol-level capabilities: NEWBORN cannot bid on marketplace tasks, CHILD cannot coordinate other citizens, only ADULT+ can delegate tasks. Stage MUST be included in heartbeat messages.

**FR-9.2 Promotion Criteria.** Stage promotion MUST require ALL of the following multi-factor gates (specific thresholds per stage):

| From | To | Criteria |
|------|-----|----------|
| NEWBORN | INFANT | Calibration complete + self-test passed |
| INFANT | CHILD | 5+ teleop sessions + 80% success rate over 10+ tasks |
| CHILD | JUVENILE | 50+ successful tasks + 70% overall success rate |
| JUVENILE | ADULT | 100+ autonomous tasks + 85% success rate + governor certification |
| ADULT | ELDER | 500+ autonomous tasks + 90% success rate + trained 1+ citizen + 3+ peer endorsements |

**FR-9.3 Earned Autonomy.** The system MUST implement per-skill autonomy levels: TELEOP_ONLY (0), SUPERVISED (1), GUIDED (2), AUTONOMOUS (3), DELEGATING (4), SELF_GOVERNING (5). Autonomy MUST be earned independently per skill. Promotion requires N consecutive successes: TELEOP_ONLY->SUPERVISED (5), SUPERVISED->GUIDED (10), GUIDED->AUTONOMOUS (25), AUTONOMOUS->DELEGATING (50), DELEGATING->SELF_GOVERNING (100).

**FR-9.4 Regression Detection.** The system MUST monitor performance using EWMA (Exponential Weighted Moving Average). Three consecutive failures at any autonomy level MUST trigger immediate demotion to the previous level. A 10% success rate drop over 50 tasks MUST trigger a regression alert and potential stage demotion. Demotion is fast (3 failures); promotion is slow (N consecutive successes). This asymmetry is intentional.

**FR-9.5 Peer Endorsement.** Citizens MUST support signed endorsement messages: endorser_pubkey, subject_pubkey, skill, observations (count), success_rate, timestamp, Ed25519 signature. A strong endorsement requires 10+ observations at 85%+ success rate. Camera citizens MUST automatically generate endorsements for arm citizens they have observed. Endorsements MUST be verified by signature before acceptance.

**FR-9.6 Emergent Specialization.** The system MUST track per-task-type performance via EMA and compute specialization scores as deviation from mean performance weighted by volume. A citizen with a specialization score > 0.1 (10% above average) in a task type MUST be considered a specialist. Specialization scores MUST feed into marketplace bid scoring (specialist bonus). An anti-specialization `breadth_check()` MUST flag skills that drop below 30% performance for remedial practice.

**FR-9.7 Growth Tracking.** The system MUST track learning curves via sliding windows at 20-task (short-term), 100-task (medium-term), and 500-task (long-term) scales. Plateau detection MUST fire when improvement rate < 2% over 50 tasks. Breakthrough detection MUST fire when recent performance exceeds medium-term average by 10%+.

#### Spatial Awareness (spatial.py)

**FR-9.8 Capsule Collision Checking.** The system MUST implement capsule-capsule distance computation using the minimum distance between line segments minus sum of radii. Two SO-101 arms (5 capsules each) require 25 inter-arm capsule checks. Self-collision requires 5 checks per arm (non-adjacent pairs only). All checks MUST complete in < 10 microseconds using NumPy.

**FR-9.9 Zone Architecture.** The system MUST support 3 zone types: exclusive (assigned to one robot, no entry by others), shared (multiple robots, mutex access via PROPOSE/ACCEPT), and forbidden (no robot may enter). Zones MUST be defined by the governor via constitution and distributed via GOVERN messages. Zone boundaries MUST be axis-aligned bounding boxes in Cartesian space (mm).

**FR-9.10 Zone Enforcement.** Before executing any servo command that would move the end-effector, the system MUST: (a) compute target gripper position via FK, (b) check target against forbidden zones (hard reject), (c) check target against other citizens' exclusive zones (hard reject), (d) check shared zone occupancy (PROPOSE access if occupied). Violations MUST be logged and reported.

**FR-9.11 Flight Plans.** Before moving into a shared workspace zone, a citizen MUST broadcast a flight plan via PROPOSE containing: start configuration (joint positions + Cartesian), end configuration, duration_ms, envelope (bounding box of swept volume), and priority (10=emergency, 8=active handoff, 6=ongoing task, 4=new task, 2=return home, 1=idle repositioning). Other arms MUST respond with ACCEPT_REJECT. If conflict exists, the lower-priority arm yields. Equal priority ties MUST be broken by lower pubkey yields.

**FR-9.12 Minimum Separation.** The system MUST enforce minimum separation distances between arms: green zone (> 50mm, normal operation), yellow zone (20-50mm, slow approaching arm + broadcast warning), red zone (< 20mm, stop approaching arm + broadcast emergency), contact (< 0mm, emergency stop both arms). Separation MUST be checked every telemetry cycle.

**FR-9.13 Object Handoff.** The system MUST implement a 4-phase handoff sequence: NEGOTIATE (holder PROPOSEs, receiver ACCEPTs, zone reserved), APPROACH (both arms move to handoff positions, both broadcast flight plans), TRANSFER (holder extends into shared zone, receiver grips, holder releases on grip confirmation), RETREAT (both retreat, zone unlocked, object registry updated). Handoff MUST use the existing PROPOSE/ACCEPT protocol.

**FR-9.14 Position Broadcasting.** Each arm citizen MUST include spatial data in its heartbeat: base_position (fixed), gripper_position (from FK), joint_positions (raw ticks), velocity estimate, and holding_object (object ID or null). This enables all citizens to maintain a local model of neighbor positions without dedicated spatial messages.

**FR-9.15 Camera Verification.** Camera citizens MUST broadcast spatial reports via REPORT messages containing detected objects (id, position, confidence) and observed arm positions (citizen_id, gripper_pixel, gripper_world). Discrepancies between FK-computed arm positions and camera-observed positions exceeding 20mm MUST trigger a warning on the mycelium network.

---

## Non-Functional Requirements

### NFR-1: Performance

- Reflex loop: 100Hz (10ms cycle), < 10ms from trigger to servo command
- FK computation: < 0.1ms per call
- Capsule collision check (2 arms): < 10 microseconds (25 pair checks)
- Memory retrieval: < 5ms for tag-based episodic search
- Consolidation: < 30 seconds for 100 episodes
- Sleep entry/exit: < 200ms state transition
- Pain event recording: < 1ms
- Metabolic state classification: < 0.1ms

### NFR-2: Memory Footprint

- Episodic memory: < 10MB per citizen (pre-consolidation)
- Semantic knowledge graph: < 2MB per citizen
- Procedural memory: < 1MB per citizen
- Pain avoidance zones: < 100 entries per citizen (pruned by confidence decay)
- Telemetry window (reflex engine): 10 readings x 6 servos = fixed, negligible
- Total v4.0 overhead: < 50MB RAM per citizen above v3.0 baseline

### NFR-3: Backward Compatibility

- v3.0 citizens MUST interoperate with v4.0 fleet without modification
- v4.0 citizens MUST function on a v3.0 fleet (biological subsystems disabled, v3.0 behavior)
- No new protocol message types -- all new data carried in existing message bodies
- Existing genome format MUST be extended (new optional fields), not replaced
- All v3.0 tests (297) MUST continue to pass

### NFR-4: Reliability

- Reflex engine MUST NOT block the asyncio event loop (runs in a separate thread or tight async loop with gc disabled during critical section)
- Sleep cycle MUST be interruptible at any phase for EMERGENCY events
- Memory persistence MUST use atomic writes -- no data loss on power failure
- Avoidance zones MUST survive reboots (persisted in genome)
- Growth stage MUST survive reboots (persisted in genome)

### NFR-5: Observability

- All 9 subsystems MUST expose their state via the existing web dashboard API
- Reflex firings MUST be logged with rule ID, condition values, action taken, and timestamp
- Sleep phases MUST be logged with entry/exit times and work performed
- Growth promotions/demotions MUST be logged as LifeEvents in the autobiography
- Pain events MUST be visible on the dashboard with joint, intensity, cause, and avoidance zone visualization

### NFR-6: Testability

- Every reflex rule MUST be testable with synthetic telemetry (no hardware required)
- Sleep consolidation MUST be testable with synthetic episode data
- Growth promotion MUST be testable with synthetic task histories
- Pain avoidance MUST be testable with synthetic pain events and trajectory checks
- FK computation MUST be testable against known joint configurations and expected Cartesian positions
- CMA-ES parameter evolution MUST be testable with a synthetic objective function

---

## Technical Constraints

1. **Pure Python.** No C extensions, no Cython, no compiled modules. All code MUST run on CPython 3.12.
2. **No GPU.** All computation runs on Intel Iris Plus (Surface Pro 7) and ARM Cortex-A76 (Pi 5). No CUDA, no OpenCL, no Metal.
3. **No new protocol messages.** The citizenry protocol remains exactly 7 message types: HEARTBEAT, GOVERN, PROPOSE, ACCEPT_REJECT, REPORT, WILL, POKE. All v4.0 data is carried in message bodies (JSON payloads).
4. **Minimal new dependencies.** numpy is the only required new dependency. cma (CMA-ES) is optional. No PyBullet, no FCL, no OMPL, no ROS -- custom capsule collision using NumPy only.
5. **Must not break v3.0.** All 297 existing tests pass. All existing CLI commands work. All existing genome files load without error. New genome fields are optional with defaults.
6. **100Hz reflex constraint.** The reflex loop MUST NOT use asyncio.sleep() with resolution worse than 10ms. It MUST account for serial bus read time (~5ms for 6 servos) in its cycle budget.
7. **JSON persistence.** All new persistent data uses JSON files in `~/.citizenry/`. No SQLite, no binary formats. Atomic writes via write-to-temp + rename.
8. **No external services.** All subsystems run locally. No cloud APIs, no model servers, no databases. Fully offline.

---

## Scope Boundaries

### In Scope (v4.0)

- Soul: personality, goals, preferences, values, identity continuity, autobiography
- Memory: episodic, semantic, procedural, consolidation engine, fleet sharing
- Self-Improvement: performance tracking, UCB1 strategy selection, CMA-ES parameter evolution, failure analysis, practice mode
- Reflexes: 100Hz engine, declarative rules, derivative triggers, compound conditions, distributed sympathy, immune integration
- Metabolism: metabolic states, brownout protocol, voltage sag detection, power ledger, power-aware bidding, duty cycle tracking, servo fatigue
- Pain: pain events, avoidance zones, referred pain, chronic detection, sensitization/habituation
- Proprioception: forward kinematics, body schema, joint limits, force estimation, payload estimation, calibration drift detection, self-collision checking, capsule model
- Sleep: 4-phase cycle, sleep pressure, consolidation dispatch, dream replay, wake thresholds, sleep schedule
- Growth: 6 developmental stages, earned per-skill autonomy, multi-factor capability gates, peer endorsement, emergent specialization, regression detection, growth tracking
- Spatial Awareness: capsule collision, zone architecture, flight plans, minimum separation, object handoff, position broadcasting, camera verification

### Out of Scope (v4.1+)

- Embedding-based memory retrieval (requires GPU or model server)
- Visual self-modeling (Chen et al. -- requires neural network training)
- Full motion planning / path optimization (OMPL-level planning around obstacles)
- Behavior trees (v4.0 uses priority arbitration; behavior trees are a v5.0 candidate)
- Reinforcement learning integration (v4.0 uses bandit algorithms and CMA-ES, not RL)
- Multi-floor / multi-room spatial models (v4.0 assumes a single flat workspace)
- Natural language personality expression (personality biases behavior, does not generate text)
- Depth camera integration for occupancy grids (v4.0 uses 2D camera + FK)
- Cross-fleet memory federation (v4.0 shares within a single fleet only)
- URDF model generation for SO-101

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Reflex engine GC pauses cause > 10ms delays | Safety-critical response delayed | Medium | Disable GC in reflex loop; manual collect between cycles; measure and alert if cycle exceeds budget |
| Pain avoidance zones become too conservative | Robot refuses to move to useful configurations | Medium | Confidence decay ensures zones shrink over time; governor can clear zones; sensitivity habituation for benign stimuli |
| Sleep consolidation corrupts memory | Knowledge lost or incorrect | Low | Consolidation operates on copies; atomic write on success; rollback on error; consolidation logged for audit |
| Growth promotion too slow (users impatient) | Users bypass growth system or disable it | Medium | Governor can fast-track promotions via certification; thresholds are configurable in constitution |
| CMA-ES parameter evolution diverges | Skill performance degrades instead of improving | Low | Fallback to best-known parameters if success rate drops below baseline; population reset on divergence |
| Metabolic state misclassification | Tasks rejected unnecessarily or brownout not prevented | Low | Voltage sag is primary signal (hardware-validated); metabolic state is secondary; brownout protocol has 4 stages with increasing severity |
| Capsule collision false positives | Arms stop unnecessarily in shared workspace | Medium | Conservative capsule radii can be tuned per-arm; yellow zone slows instead of stops; flight plan priority arbitration prevents deadlock |
| Memory files grow unbounded | Disk full on Pi 5 SD card | Medium | Consolidation prunes aggressively; max episode count enforced; max knowledge graph size enforced; monitor disk usage in deep sleep |
| Personality drift makes citizen unusable | Extreme trait values cause pathological bidding behavior | Low | Drift rate is 0.01 per 1000 interactions; traits clamped to [0, 1]; governor can reset personality to genome baseline |
| Backward compatibility regression | v3.0 citizens break on v4.0 fleet | Medium | All new genome fields have defaults; all new message body fields are optional; integration test with mixed-version fleet in CI |
