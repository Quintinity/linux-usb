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
  - synthesis-robot-citizenry.md
  - product-brief.md
  - citizenry/protocol.py
  - citizenry/citizen.py
  - citizenry/constitution.py
  - citizenry/telemetry.py
  - citizenry/surface_citizen.py
  - citizenry/pi_citizen.py
  - citizenry/transport.py
  - citizenry/identity.py
  - citizenry/mdns.py
  - citizenry/persistence.py
  - citizenry/dashboard.py
  - citizenry/choreo.py
  - citizenry/demo.py
workflowType: 'prd'
---

# Product Requirements Document — armOS Citizenry v2.0: "Citizens Collaborate"

**Author:** Bradley
**Date:** 2026-03-15
**Version:** 2.0
**Status:** Approved for implementation

---

## Executive Summary

armOS Citizenry v1.5 ("Citizens Discover Each Other") shipped a working 2-node distributed robot protocol: Surface Pro 7 as governor + Raspberry Pi 5 as follower arm, communicating over a 7-message UDP protocol with Ed25519 signing, mDNS discovery, constitutional governance, real-time teleop at 25+ FPS, and auto-reconnection. It works. Both nodes talk, trust is established, and arms move in sync.

**v2.0 ("Citizens Collaborate") extends the protocol so citizens can negotiate tasks, learn from experience, compose capabilities, and propagate safety warnings across the mesh.** The 7 message types remain unchanged. All new behavior is expressed through message body schemas on the existing PROPOSE/ACCEPT_REJECT/REPORT/GOVERN types.

The core deliverables:
1. **Task Marketplace** — Auction-based task bidding using PROPOSE/ACCEPT_REJECT
2. **Skill Trees + XP** — Citizens earn capabilities through successful task completions
3. **Capability Composition** — arm + camera = visual_pick_and_place (discovered automatically)
4. **Symbiosis Contracts** — Formal mutual-benefit agreements between citizens
5. **Telemetry Warning Propagation** — Fast + slow channels for safety events (mycelium network)
6. **Immune Memory** — Fault patterns shared across all citizens
7. **Citizen Genome** — Portable config DNA (calibration, skills, faults, XP)
8. **USB Camera as Citizen** — First non-arm citizen type with sense capability

---

## Vision

The citizenry moves from "devices that know about each other" to "devices that work together." v1.5 proved the communication layer. v2.0 proves the collaboration layer. When a goal arrives, citizens bid for it. When a citizen fails, others adapt. When a new citizen joins, it inherits the fleet's accumulated knowledge instantly. The system self-organizes through market dynamics, not central dispatch.

**Target demo:** Two SO-101 arms and a USB camera collaborate on a sorting task. The governor publishes "sort blocks by color." The camera citizen detects block positions. Arm citizens bid for pick-and-place tasks. If one arm overheats, the mycelium warning propagates and the other arm takes over. All of this happens over the same 7 messages, with no new transport or protocol changes.

---

## Problem Statement

v1.5 citizens can discover each other and run teleop, but they cannot:
- **Negotiate tasks** — The governor hardcodes which citizen does what
- **Learn from experience** — A citizen that has completed 1000 grasps is treated identically to one that has never grasped
- **Compose capabilities** — An arm and a camera on the same network don't know they can do visual manipulation together
- **Share safety knowledge** — When one arm experiences voltage collapse, other arms don't learn from it
- **Recover gracefully** — If the designated follower goes down, no other citizen can take over
- **Onboard quickly** — A replacement arm starts from zero, with no inherited calibration or fault history

These limitations mean the system scales linearly with human attention: every new task, every new citizen, every failure requires the governor (human) to intervene manually.

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Task auction latency | < 500ms from PROPOSE to ACCEPT | Timestamp delta in protocol logs |
| Multi-citizen task completion | 3+ citizens collaborating on 1 task | Demo: camera + 2 arms sorting |
| Capability discovery | Auto-detect composite capabilities within 5s of new citizen joining | Automated test |
| Warning propagation latency (fast channel) | < 100ms from detection to all neighbors warned | Telemetry timestamps |
| Immune memory inheritance | New citizen inherits all fault patterns within 10s of joining | Automated test |
| Genome portability | Export genome from one citizen, import to another, operational in < 30s | Manual test |
| XP tracking accuracy | XP increments on task success, no increment on failure | Unit test |
| Zero protocol breaking changes | All v1.5 messages still work unmodified | Integration test |
| Test coverage | > 80% for all new modules | pytest --cov |

---

## User Journeys

### Journey 1: Governor Publishes a Task

Bradley wants both arms to sort colored blocks. He types a command on the Surface Pro.

1. Governor creates a task descriptor: `{task: "pick_and_place", object: "red_block", destination: "bin_A"}`
2. Governor broadcasts PROPOSE to the neighborhood
3. Both arm citizens evaluate: Do I have the skill? Am I idle? Am I healthy?
4. Arm-1 bids: `{accepted: true, bid: {skill_level: 3, load: 0.1, distance: 0.3}}`
5. Arm-2 bids: `{accepted: true, bid: {skill_level: 1, load: 0.0, distance: 0.8}}`
6. Governor selects Arm-1 (higher skill, closer proximity)
7. Arm-1 executes, sends REPORT with result
8. Arm-1's XP for `pick_and_place` increments

### Journey 2: Arm Overheats Mid-Task

The elbow servo on Arm-1 hits 60C during a pick sequence.

1. Arm-1's telemetry loop detects temperature warning
2. Fast channel: Arm-1 broadcasts a WARNING REPORT to all neighbors (< 100ms)
3. Other citizens receive warning and reduce their own duty cycles preemptively
4. Arm-1 enters degraded mode, reduces speed 50%
5. Governor sees warning on dashboard, task re-enters marketplace
6. Arm-2 bids and takes over remaining tasks
7. Immune memory entry created: `{pattern: "elbow_thermal_under_sustained_load", mitigation: "reduce_speed_50pct"}`
8. This pattern is shared with all current and future citizens

### Journey 3: Camera Joins and Forms Symbiosis

A USB camera is plugged into the Surface Pro.

1. Camera citizen starts, generates keypair, broadcasts DISCOVER
2. Surface discovers it, sends constitution
3. Camera advertises capabilities: `["video_stream", "frame_capture", "color_detection"]`
4. Governor detects capability composition: camera(sense) + arm(actuate) = `visual_pick_and_place`
5. Camera PROPOSES symbiosis contract to nearest arm: "I provide visual feedback, you provide manipulation"
6. Arm ACCEPTS — contract registered in both citizens' state
7. Dashboard shows the composite capability as available
8. If camera goes offline, arm detects broken contract and enters safe mode (no blind manipulation)

### Journey 4: New Arm Inherits Fleet Knowledge

A second Pi with SO-101 joins the network.

1. New arm discovers neighborhood, receives constitution
2. Governor sends genome package: calibration priors (fleet average offsets), known fault patterns, skill tree definitions
3. New arm applies calibration priors — starts from fleet average instead of scratch
4. New arm's immune memory populated with all known fault patterns
5. New arm starts with XP=0 but inherits skill tree definitions so it knows what skills exist
6. Within 30 seconds of joining, the arm is operational and participating in the task marketplace

---

## Domain Model

### Core Entities

```
Citizen (extended)
├── identity: Ed25519 keypair (unchanged)
├── capabilities: list[str] (unchanged)
├── genome: CitizenGenome (NEW)
│   ├── calibration: dict
│   ├── protection_settings: dict
│   ├── xp: dict[str, int]
│   ├── skill_tree: SkillTree
│   ├── immune_memory: list[FaultPattern]
│   └── version: int
├── skill_tree: SkillTree (NEW)
│   ├── skills: dict[str, Skill]
│   └── xp: dict[str, int]
├── contracts: list[SymbiosisContract] (NEW)
├── immune_memory: ImmuneMemory (NEW)
└── task_state: TaskState (NEW)
    ├── current_task: Task | None
    ├── bid_history: list[Bid]
    └── completed_tasks: int

Task
├── id: str (UUID)
├── type: str (e.g., "pick_and_place")
├── params: dict
├── priority: float (0.0-1.0)
├── required_capabilities: list[str]
├── status: pending | bidding | assigned | executing | completed | failed
├── assigned_to: str | None (citizen pubkey)
└── result: dict | None

Bid
├── citizen_pubkey: str
├── task_id: str
├── score: float (composite)
├── skill_level: int
├── current_load: float
├── estimated_duration: float
└── timestamp: float

SkillTree
├── definitions: dict[str, SkillDef]
│   └── SkillDef: {name, prerequisites: list[str], xp_required: int}
└── xp: dict[str, int]

SymbiosisContract
├── id: str
├── provider: str (citizen pubkey)
├── consumer: str (citizen pubkey)
├── provider_capability: str
├── consumer_capability: str
├── composite_capability: str
├── health_check_interval: float
├── status: active | broken | expired
└── created_at: float

FaultPattern
├── id: str
├── pattern_type: str (e.g., "voltage_collapse", "thermal_overload")
├── conditions: dict (trigger thresholds)
├── mitigation: str (action to take)
├── severity: str (warning | critical | emergency)
├── source_citizen: str
├── learned_at: float
└── occurrences: int

CitizenGenome
├── citizen_name: str
├── citizen_type: str
├── hardware: dict (servo model, motor count, etc.)
├── calibration: dict (joint offsets, ranges)
├── protection: dict (torque limits, current limits)
├── xp: dict[str, int]
├── immune_memory: list[FaultPattern]
├── version: int
└── exported_at: float
```

### Message Body Schemas (v2.0 Extensions)

All new functionality uses the existing 7 message types. The `body` field of each envelope gains new schemas:

**PROPOSE bodies (type=4):**
```json
// Task proposal (auction)
{"task": "pick_and_place", "task_id": "uuid", "priority": 0.7,
 "required_capabilities": ["6dof_arm", "gripper"],
 "params": {"object": "red_block", "destination": [0.3, 0.5, 0.1]}}

// Symbiosis proposal
{"task": "symbiosis_propose", "provider_cap": "video_stream",
 "consumer_cap": "6dof_arm", "composite": "visual_pick_and_place",
 "health_check_hz": 1.0}

// Teleop frame (unchanged from v1.5)
{"task": "teleop_frame", "positions": {...}}
```

**ACCEPT_REJECT bodies (type=5):**
```json
// Task bid
{"accepted": true, "task_id": "uuid",
 "bid": {"skill_level": 3, "load": 0.12, "score": 0.87}}

// Symbiosis acceptance
{"accepted": true, "task": "symbiosis_propose",
 "contract_id": "uuid"}
```

**REPORT bodies (type=6):**
```json
// Task completion
{"type": "task_complete", "task_id": "uuid",
 "result": "success", "duration_ms": 3200, "xp_earned": 10}

// Warning (fast channel)
{"type": "warning", "severity": "critical",
 "detail": "voltage_collapse", "motor": "elbow_flex",
 "value": 5.2, "threshold": 6.0}

// Immune memory share
{"type": "immune_share", "patterns": [...]}

// Telemetry (unchanged from v1.5)
{"type": "telemetry", ...}
```

**GOVERN bodies (type=7):**
```json
// Genome distribution
{"type": "genome", "genome": {...}}

// Skill tree definitions
{"type": "skill_tree", "definitions": {...}}

// Task assignment (governor overrides auction)
{"type": "task_assign", "task_id": "uuid", "citizen": "pubkey"}
```

---

## Functional Requirements

### FR-1: Task Marketplace

**FR-1.1** The governor MUST be able to broadcast a task as a PROPOSE message with `task_id`, `priority`, `required_capabilities`, and task-specific `params`.

**FR-1.2** Citizens MUST evaluate incoming tasks against their capabilities, current load, health, and skill level before responding with ACCEPT (bid) or REJECT.

**FR-1.3** Bids MUST include a composite score calculated as: `score = capability_weight * skill_level + availability_weight * (1 - load) + health_weight * health`. Weights are configurable via laws.

**FR-1.4** The governor (or any designated coordinator) MUST select the winning bid within 2 seconds of the PROPOSE broadcast. Selection criteria: highest composite score, with deterministic tiebreak (lower pubkey hash wins).

**FR-1.5** If no bids arrive within the timeout, the task MUST be re-broadcast up to 3 times with exponential backoff (2s, 4s, 8s).

**FR-1.6** If a citizen fails mid-task (detected via missing heartbeats or fault REPORT), the task MUST automatically re-enter the marketplace.

**FR-1.7** The governor MUST be able to override the auction and directly assign a task to a specific citizen via GOVERN with `type: "task_assign"`.

### FR-2: Skill Trees and XP

**FR-2.1** Each citizen MUST maintain a local skill tree with XP counters per skill.

**FR-2.2** Skill definitions MUST be distributed by the governor via GOVERN messages. The default skill tree for manipulator citizens:
```
basic_movement (0 XP) → precise_movement (100 XP) → tool_use (500 XP)
basic_grasp (0 XP) → precise_grasp (200 XP) → delicate_grasp (1000 XP)
basic_gesture (0 XP) → complex_gesture (150 XP)
```

**FR-2.3** XP MUST be awarded on successful task completion: `xp = base_xp * task_difficulty * success_quality`. Base XP defaults to 10. Task difficulty and success quality are floats in [0.0, 1.0].

**FR-2.4** XP MUST NOT be awarded on task failure. Failed tasks MAY award a fraction (configurable, default 0) to encourage exploration.

**FR-2.5** A citizen MUST NOT bid on tasks requiring skills it has not unlocked.

**FR-2.6** XP MUST persist across restarts via the genome system.

### FR-3: Capability Composition

**FR-3.1** The governor MUST maintain a capability composition registry defining which capability combinations produce composite capabilities. Default compositions:
- `["6dof_arm", "video_stream"]` → `visual_pick_and_place`
- `["6dof_arm", "color_detection"]` → `color_sorting`
- `["6dof_arm", "6dof_arm"]` → `bimanual_manipulation`

**FR-3.2** When a new citizen joins or a symbiosis contract is formed, the governor MUST check for new composite capabilities and broadcast them via ADVERTISE.

**FR-3.3** Composite capabilities MUST appear in the dashboard alongside native capabilities.

### FR-4: Symbiosis Contracts

**FR-4.1** A citizen MUST be able to propose a symbiosis contract to another citizen via PROPOSE with `task: "symbiosis_propose"`.

**FR-4.2** Contracts MUST specify: provider capability, consumer capability, resulting composite capability, and health check interval.

**FR-4.3** Both parties MUST send periodic health checks (piggybacked on heartbeats). If 3 consecutive health checks are missed, the contract MUST be marked as `broken`.

**FR-4.4** When a contract breaks, both parties MUST: (a) remove the composite capability from their advertisements, (b) enter safe mode for any task that depended on the contract, (c) send a REPORT to the governor.

**FR-4.5** Contracts MUST persist across restarts via the persistence layer.

### FR-5: Telemetry Warning Propagation (Mycelium Network)

**FR-5.1** Citizens MUST broadcast safety warnings as REPORT messages with `type: "warning"` and a severity level (info, warning, critical, emergency).

**FR-5.2** Fast channel: Critical and emergency warnings MUST be sent via UDP multicast with TTL of 2 seconds. Delivery target: < 100ms to all neighbors.

**FR-5.3** Slow channel: Info and warning severity MUST be included in the next heartbeat's body as a `warnings` array. These propagate at heartbeat frequency (default 2s).

**FR-5.4** Citizens receiving warnings MUST apply proportional mitigation:
- `info`: Log only
- `warning`: Reduce duty cycle 25%
- `critical`: Reduce duty cycle 50%, avoid the specific motion pattern
- `emergency`: Stop all motion, disable torque

**FR-5.5** The governor MUST aggregate warnings and display them on the dashboard with time-decay (warnings fade after 60s of no recurrence).

### FR-6: Immune Memory

**FR-6.1** When a citizen detects and recovers from a fault (voltage collapse, thermal overload, servo error), it MUST create a FaultPattern entry with: trigger conditions, mitigation applied, severity, and outcome.

**FR-6.2** FaultPatterns MUST be shared with all neighbors via REPORT with `type: "immune_share"`.

**FR-6.3** The governor MUST maintain the authoritative immune memory database and distribute it to new citizens upon joining.

**FR-6.4** Citizens MUST check incoming telemetry against known fault patterns and apply preemptive mitigation when conditions match.

**FR-6.5** FaultPatterns MUST include an `occurrences` counter that increments each time the pattern is triggered across any citizen.

### FR-7: Citizen Genome

**FR-7.1** Each citizen MUST maintain a genome: a portable JSON blob containing calibration, protection settings, XP, skill tree state, immune memory, and hardware descriptor.

**FR-7.2** The genome MUST be exportable to a file (`<citizen_name>.genome.json`) and importable by any citizen of the same hardware type.

**FR-7.3** When a new citizen joins with no existing genome, the governor MUST send a "fleet average" genome derived from all citizens of the same type.

**FR-7.4** Genomes MUST be versioned. A citizen MUST NOT accept a genome with a version lower than its current genome.

**FR-7.5** The genome MUST be saved to disk on every shutdown and loaded on every startup.

### FR-8: USB Camera as Citizen

**FR-8.1** A `CameraCitizen` class MUST be implemented that wraps a USB camera (via OpenCV) and advertises capabilities: `["video_stream", "frame_capture", "color_detection"]`.

**FR-8.2** The camera citizen MUST respond to PROPOSE messages for `frame_capture` tasks by capturing a frame and returning it as a base64-encoded JPEG in a REPORT.

**FR-8.3** The camera citizen MUST support `color_detection` tasks: capture a frame, detect colored regions, return bounding boxes and color labels in a REPORT.

**FR-8.4** The camera citizen MUST stream heartbeats with health derived from: camera accessible (True/False), frame rate, and frame quality.

**FR-8.5** The camera citizen MUST be runnable on the Surface Pro 7 alongside the governor.

---

## Non-Functional Requirements

### NFR-1: Protocol Compatibility

All v1.5 messages MUST continue to work unmodified. v2.0 adds new body schemas to existing message types — it does NOT add new message types. A v1.5 citizen that receives a v2.0 body it doesn't understand MUST ignore the unknown fields gracefully.

### NFR-2: Performance

- Task auction round-trip (PROPOSE → winning ACCEPT): < 500ms on LAN
- Warning propagation (fast channel): < 100ms
- Heartbeat overhead: < 1% CPU on Pi 5
- Genome export/import: < 1 second for files up to 100KB
- Dashboard refresh: 2 Hz minimum with v2.0 data (no regression from v1.5)
- Memory usage: < 50MB RSS per citizen process

### NFR-3: Reliability

- Citizens MUST function correctly after any combination of restarts, network interruptions, and citizen departures
- All persistent state (genome, contracts, immune memory) MUST survive process restarts
- Atomic file writes (write-to-temp, rename) for all persistence operations — already established pattern in v1.5

### NFR-4: Security

- All new message bodies MUST be signed and verified using the existing Ed25519 envelope system
- Genome imports MUST be signed by the governor — a citizen MUST NOT accept an unsigned genome from a peer
- Immune memory entries MUST be traceable to the originating citizen's public key

### NFR-5: Testability

- All new modules MUST have unit tests with > 80% coverage
- Integration tests MUST verify multi-citizen scenarios using localhost multicast
- Tests MUST run without hardware (mock servo bus, mock camera)
- Tests MUST complete in < 60 seconds total

### NFR-6: Hardware Constraints

- No CUDA dependencies — all processing on CPU (Intel Iris Plus on Surface, ARM Cortex-A76 on Pi)
- OpenCV for camera — must work with `opencv-python-headless` (no GUI)
- Python 3.12+ on Surface, 3.13+ on Pi
- Maximum 50MB additional disk for new modules and dependencies
- Camera resolution capped at 640x480 for performance on Surface Pro 7

---

## Technical Constraints

1. **Transport unchanged** — UDP multicast + unicast, same ports, same envelope format
2. **No new dependencies beyond OpenCV** — pynacl, zeroconf already installed; add only opencv-python-headless
3. **Backward compatible** — v1.5 citizens on the network MUST NOT crash when v2.0 messages arrive
4. **Python only** — no Rust, no C extensions (keeps deployment simple via rsync)
5. **Same deploy mechanism** — `deploy.sh` rsync to Pi continues to work

---

## Scope Boundaries

### In Scope (v2.0)
- Task marketplace with auction bidding
- Skill trees + XP tracking
- Capability composition discovery
- Symbiosis contracts
- Telemetry warning propagation (fast + slow channels)
- Immune memory (create, share, apply)
- Citizen genome (export, import, fleet average)
- USB camera citizen
- Dashboard updates for all new features
- Comprehensive test suite

### Out of Scope (deferred to v3.0)
- Federated learning across locations
- Natural language governance ("make the robots gentle")
- Multi-location nation (WireGuard VPN, embassy model)
- Local LLM reasoning engine on citizens
- Rolling policy updates with canary testing
- Consciousness stream (natural language state narration)
- Emotional state signals (fatigue, confidence, curiosity)
- Dead citizen's will (final broadcast before shutdown)
- Web-based dashboard (remain terminal TUI)
- Apprenticeship learning (new arms watching experienced arms)

---

## Architecture Overview

```
citizenry/
├── __init__.py                 # Package version
├── protocol.py                 # 7-message protocol (unchanged)
├── identity.py                 # Ed25519 keypair management (unchanged)
├── transport.py                # UDP multicast + unicast (unchanged)
├── constitution.py             # Articles, laws, servo limits (unchanged)
├── citizen.py                  # Base citizen (extended: task state, genome, skills)
├── surface_citizen.py          # Governor (extended: marketplace, composition)
├── pi_citizen.py               # Follower arm (extended: bidding, skills)
├── camera_citizen.py           # NEW: USB camera citizen
├── marketplace.py              # NEW: Task lifecycle, auction, bidding
├── skills.py                   # NEW: Skill tree, XP tracking
├── symbiosis.py                # NEW: Contracts between citizens
├── mycelium.py                 # NEW: Warning propagation (fast + slow)
├── immune.py                   # NEW: Fault pattern learning and sharing
├── genome.py                   # NEW: Citizen genome export/import
├── composition.py              # NEW: Capability composition discovery
├── telemetry.py                # Servo telemetry (unchanged)
├── persistence.py              # JSON persistence (extended)
├── mdns.py                     # mDNS discovery (unchanged)
├── dashboard.py                # TUI dashboard (extended)
├── run_surface.py              # Surface entry point (updated)
├── run_pi.py                   # Pi entry point (updated)
├── run_camera.py               # NEW: Camera entry point
├── choreo.py                   # Demo choreography (unchanged)
├── demo.py                     # Demo script (extended)
├── deploy.sh                   # Pi deployment (unchanged)
└── tests/                      # NEW: Test suite
    ├── __init__.py
    ├── conftest.py              # Shared fixtures (mock bus, mock camera, test citizens)
    ├── test_marketplace.py
    ├── test_skills.py
    ├── test_symbiosis.py
    ├── test_mycelium.py
    ├── test_immune.py
    ├── test_genome.py
    ├── test_composition.py
    ├── test_camera_citizen.py
    ├── test_integration.py      # Multi-citizen scenarios
    └── test_protocol_compat.py  # v1.5 backward compatibility
```

---

## Dependencies

### New Python Packages
- `opencv-python-headless>=4.8.0` — Camera frame capture and color detection (headless = no GUI dependency)

### Existing (no changes)
- `pynacl>=1.5.0` — Ed25519 signing
- `zeroconf>=0.131.0` — mDNS discovery
- `lerobot==0.5.0` — Servo control (SO-101)

### Dev/Test
- `pytest>=8.0`
- `pytest-asyncio>=0.23`
- `pytest-cov>=5.0`

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Auction latency too high on WiFi | Tasks assigned slowly | Medium | Short timeout (2s), governor can override with direct assignment |
| Camera citizen CPU usage too high on Surface | Governor performance degrades | Medium | Cap resolution at 640x480, process frames on-demand not continuously |
| Immune memory grows unbounded | Disk/memory bloat | Low | Cap at 1000 patterns, LRU eviction by last-triggered time |
| Genome import from incompatible hardware | Servo damage from wrong calibration | Medium | Hardware descriptor check: genome MUST match citizen's hardware type |
| Multi-citizen localhost testing unreliable | CI flaky | Medium | Use explicit port assignment in tests, avoid random port collisions |

---

## Glossary

| Term | Definition |
|------|-----------|
| Citizen | A device with Ed25519 identity, capabilities, and protocol participation |
| Governor | The citizen that signs the constitution and has ultimate authority |
| Neighborhood | All citizens on the same LAN, discoverable via mDNS |
| Genome | Portable JSON blob containing a citizen's full configuration and learned state |
| Skill Tree | DAG of capabilities unlocked through XP accumulation |
| Symbiosis Contract | Formal agreement between two citizens to provide complementary capabilities |
| Immune Memory | Database of fault patterns learned from real failures |
| Mycelium Network | The warning propagation system (fast + slow channels) |
| Marketplace | The auction system for task allocation via PROPOSE/ACCEPT |
| Composite Capability | A capability that emerges from combining capabilities of multiple citizens |
