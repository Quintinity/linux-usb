---
project: armOS Citizenry v2.0
date: 2026-03-15
status: approved
---

# Epics & Stories — armOS Citizenry v2.0: "Citizens Collaborate"

## Epic 1: Task Marketplace

**Goal:** Citizens bid on tasks via auction using existing PROPOSE/ACCEPT_REJECT messages.

### Stories

**E1-S1: Task and Bid data models** (marketplace.py)
- Create Task dataclass with id, type, params, priority, required_capabilities, status, assigned_to, result
- Create Bid dataclass with citizen_pubkey, task_id, score, skill_level, current_load, estimated_duration
- Create TaskMarketplace class to manage task lifecycle (pending → bidding → assigned → executing → completed/failed)
- AC: Unit tests pass, models serialize to/from JSON

**E1-S2: Bid scoring engine**
- Implement composite score: `capability_weight * skill_level + availability_weight * (1 - load) + health_weight * health`
- Configurable weights via law params
- Deterministic tiebreak: lower pubkey hash wins
- AC: Unit tests with various bid scenarios

**E1-S3: Governor marketplace integration** (surface_citizen.py)
- Governor can create and broadcast tasks as PROPOSE messages
- Governor collects bids within timeout (2s default)
- Governor selects winner and sends assignment notification
- Re-broadcast on no bids (up to 3x with exponential backoff)
- AC: Integration test with mock citizens

**E1-S4: Citizen bidding integration** (citizen.py)
- Citizens evaluate incoming PROPOSE tasks against capabilities, load, health, skills
- Generate bid with composite score
- Send ACCEPT with bid or REJECT with reason
- Execute assigned task and send REPORT on completion
- AC: Integration test, citizen correctly bids/rejects

**E1-S5: Task failure recovery**
- If assigned citizen goes dead (missed heartbeats), task re-enters marketplace
- Failed task REPORT triggers re-auction
- AC: Integration test with simulated citizen death

---

## Epic 2: Skill Trees & XP

**Goal:** Citizens earn capabilities through experience, tracked via persistent skill trees.

### Stories

**E2-S1: Skill tree data model** (skills.py)
- SkillDef dataclass: name, prerequisites, xp_required, description
- SkillTree class: definitions dict, xp dict, methods to check/unlock/award
- Default skill tree for manipulator citizens
- AC: Unit tests for skill unlock logic

**E2-S2: XP award on task completion**
- Hook into task completion flow
- `xp = base_xp * task_difficulty * success_quality`
- No XP on failure (configurable)
- Persist XP via genome
- AC: Unit tests verify XP math and persistence

**E2-S3: Skill-gated bidding**
- Citizens check skill requirements before bidding on tasks
- Tasks can specify `required_skills` in params
- Citizen rejects tasks requiring unlocked skills
- AC: Unit test — unskilled citizen rejects, skilled citizen bids

**E2-S4: Skill tree distribution via GOVERN**
- Governor sends skill tree definitions to new citizens
- Citizens accept and store skill definitions
- AC: Integration test

---

## Epic 3: Capability Composition

**Goal:** Auto-discover composite capabilities when citizens with complementary capabilities are in the same neighborhood.

### Stories

**E3-S1: Composition registry** (composition.py)
- CompositionRule dataclass: required_capabilities, composite_capability
- Default rules: arm+camera → visual_pick_and_place, arm+arm → bimanual_manipulation
- CompositionEngine: given a set of citizen capabilities, return discovered compositions
- AC: Unit tests for composition discovery

**E3-S2: Auto-discovery on neighbor join**
- When a new citizen joins, governor checks all capability pairs/triples
- New composite capabilities broadcast via ADVERTISE
- Capabilities removed when citizen leaves
- AC: Integration test

---

## Epic 4: Symbiosis Contracts

**Goal:** Citizens form explicit mutual-benefit agreements with health monitoring.

### Stories

**E4-S1: Contract data model** (symbiosis.py)
- SymbiosisContract dataclass with all fields from PRD
- ContractManager: create, accept, monitor, break contracts
- Persistence via JSON files
- AC: Unit tests for contract lifecycle

**E4-S2: Contract negotiation via protocol**
- PROPOSE with task="symbiosis_propose"
- ACCEPT with contract_id
- Both parties register contract
- AC: Integration test

**E4-S3: Health monitoring and contract breaking**
- Heartbeat includes contract health data
- 3 missed health checks → contract broken
- Broken contract → remove composite capability, safe mode, REPORT to governor
- AC: Integration test with simulated timeout

---

## Epic 5: Mycelium Warning Network

**Goal:** Safety warnings propagate across the mesh via fast and slow channels.

### Stories

**E5-S1: Warning data model and channels** (mycelium.py)
- Warning dataclass: severity, detail, motor, value, threshold, timestamp
- MyceliumNetwork: manages warning propagation, deduplication, decay
- Fast channel: multicast REPORT for critical/emergency
- Slow channel: warnings array in heartbeat body
- AC: Unit tests

**E5-S2: Proportional mitigation**
- Citizens receiving warnings apply severity-based response
- info → log, warning → -25% duty, critical → -50%, emergency → stop
- Mitigation decays after 60s of no recurrence
- AC: Unit tests for mitigation logic

**E5-S3: Dashboard warning display**
- Dashboard shows active warnings with severity colors
- Warning decay visualization
- AC: Manual verification + unit test for data aggregation

---

## Epic 6: Immune Memory

**Goal:** Fault patterns are learned and shared so new citizens inherit fleet knowledge.

### Stories

**E6-S1: Fault pattern model** (immune.py)
- FaultPattern dataclass from PRD
- ImmuneMemory class: add, match, share, prune (LRU at 1000 entries)
- AC: Unit tests

**E6-S2: Pattern detection from telemetry**
- Check telemetry against known patterns
- Create new pattern on novel fault + recovery
- AC: Unit test with simulated fault data

**E6-S3: Pattern sharing via protocol**
- REPORT with type="immune_share" broadcasts patterns
- Governor maintains authoritative database
- New citizens receive full immune memory on join
- AC: Integration test

---

## Epic 7: Citizen Genome

**Goal:** Portable configuration DNA that captures everything a citizen has learned.

### Stories

**E7-S1: Genome data model** (genome.py)
- CitizenGenome dataclass from PRD
- Export to JSON file, import from JSON file
- Version checking (reject older versions)
- AC: Unit tests for export/import round-trip

**E7-S2: Fleet average genome**
- Governor computes average genome from all citizens of same type
- Sent to new citizens on join
- AC: Unit test with mock genome data

**E7-S3: Genome persistence lifecycle**
- Save on shutdown, load on startup
- Integrate with existing persistence.py pattern
- AC: Unit test

---

## Epic 8: USB Camera Citizen

**Goal:** First non-arm citizen type — a USB camera that provides sense capabilities.

### Stories

**E8-S1: CameraCitizen base** (camera_citizen.py)
- Extends Citizen base class
- OpenCV VideoCapture for USB camera
- Capabilities: video_stream, frame_capture, color_detection
- Health from: camera accessible, frame rate
- AC: Unit test with mock camera

**E8-S2: Frame capture task**
- Respond to PROPOSE for frame_capture
- Capture frame, base64 encode, return in REPORT
- AC: Unit test with mock frame

**E8-S3: Color detection task**
- Respond to PROPOSE for color_detection
- HSV color space detection, return bounding boxes
- AC: Unit test with synthetic image

**E8-S4: Camera entry point** (run_camera.py)
- CLI entry point for running camera citizen
- Camera index selection, resolution config
- AC: Starts without error when no camera (graceful degradation)

---

## Epic 9: Dashboard & Integration

**Goal:** Update dashboard for v2.0 data, comprehensive integration tests.

### Stories

**E9-S1: Dashboard v2.0 sections**
- Add: Active tasks section, skill levels, contracts, warnings, immune memory count
- Update: Capability display shows composites
- AC: Dashboard renders without errors with v2.0 data

**E9-S2: Integration test suite**
- Multi-citizen test: governor + 2 arm citizens + camera citizen (all localhost)
- Task auction end-to-end
- Capability composition discovery
- Warning propagation
- Immune memory sharing
- AC: All integration tests pass in < 60s

**E9-S3: Protocol backward compatibility tests**
- v1.5 citizen receives v2.0 messages → no crash
- v2.0 citizen receives v1.5 messages → works normally
- AC: Tests pass

---

## Sprint Plan

### Sprint 1: Foundation (Epics 1, 2, 7)
- E1-S1, E1-S2: Task and bid models + scoring
- E2-S1: Skill tree model
- E7-S1, E7-S3: Genome model + persistence
- All unit tests for these models

### Sprint 2: Protocol Integration (Epics 1, 2, 4, 5, 6)
- E1-S3, E1-S4, E1-S5: Marketplace governor + citizen integration
- E2-S2, E2-S3, E2-S4: XP, skill-gating, distribution
- E5-S1, E5-S2: Mycelium warning network
- E6-S1, E6-S2, E6-S3: Immune memory
- E4-S1, E4-S2, E4-S3: Symbiosis contracts

### Sprint 3: Camera + Composition + Polish (Epics 3, 8, 9)
- E3-S1, E3-S2: Capability composition
- E8-S1, E8-S2, E8-S3, E8-S4: Camera citizen
- E7-S2: Fleet average genome
- E9-S1: Dashboard updates
- E9-S2, E9-S3: Integration + compatibility tests
