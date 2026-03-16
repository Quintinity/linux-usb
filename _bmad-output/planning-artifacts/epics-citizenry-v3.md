---
project: armOS Citizenry v3.0
date: 2026-03-16
status: approved
---

# Epics & Stories — armOS Citizenry v3.0: "The Nation Governs Itself"

## Epic 1: Natural Language Governance [DONE]

**Goal:** The governor interprets natural language policy intents and translates them to formal law changes.

### Stories

**E1-S1: GovernanceAction data model and pattern parser** (nl_governance.py) -- DONE
- GovernanceAction dataclass with action_type, params, confidence, explanation
- Pattern-based parser for common intents: gentle/careful, speed, stop, status
- Keyword fallback engine handles top 10 intents without LLM
- AC: Unit tests pass, parse_command handles all core intent categories

**E1-S2: GovernorAide integration** (nl_governance.py) -- DONE
- GovernorAide class wraps pattern parser for use by governor CLI
- Confidence scoring on each parsed action
- Stateless between calls — full context provided each time
- AC: GovernorAide returns correct actions for test phrases

**E1-S3: Governor CLI NL input loop** (governor_cli.py) -- DONE
- Interactive REPL accepts natural language commands
- Routes parsed actions to governor citizen for execution
- Displays proposed changes before applying
- AC: CLI starts, accepts input, executes governance actions

---

## Epic 2: Rolling Policy Updates [DONE]

**Goal:** Policy changes roll out one citizen at a time with canary testing and automatic rollback.

### Stories

**E2-S1: Rollout data models** (rolling_update.py) -- DONE
- RolloutStatus enum: pending, in_progress, completed, failed, rolled_back
- CitizenRolloutState dataclass tracking per-citizen status
- RolloutPlan dataclass with id, changes, citizen ordering, failure threshold
- AC: Unit tests pass, models serialize correctly

**E2-S2: Rollout engine** (rolling_update.py) -- DONE
- RolloutEngine orchestrates sequential canary deployment
- Orders citizens by risk (XP, health stability, uptime)
- Sends policy to one citizen, waits for result, proceeds or halts
- Abort on failure rate > 20% (configurable threshold)
- AC: Unit tests with mock citizens verify rollout/rollback logic

---

## Epic 3: Dead Citizen's Will [DONE]

**Goal:** Citizens broadcast a final testament before shutdown, preserving knowledge and task state.

### Stories

**E3-S1: CitizenWill data model** (will.py) -- DONE
- CitizenWill dataclass: name, pubkey, type, reason, current_task, partial_results, xp, contracts, warnings, uptime
- Serializes to REPORT message body with type="will"
- AC: Unit tests for serialization round-trip

**E3-S2: Will broadcast on shutdown** (will.py) -- DONE
- Signal handlers for SIGTERM/SIGINT registered at citizen startup
- Citizen enters "dying" state and broadcasts will via multicast within 2s
- Will is single UDP packet, truncated if oversized (telemetry dropped first)
- AC: Unit test — SIGTERM triggers will broadcast

---

## Epic 4: Emotional State Signals [DONE]

**Goal:** Composite telemetry metrics (fatigue, confidence, curiosity) make citizen state intuitive.

### Stories

**E4-S1: EmotionalState data model** (emotional.py) -- DONE
- EmotionalState dataclass: fatigue (0-1), confidence (0-1), curiosity (0-1), timestamp
- Serializes to/from dict for heartbeat piggybacking
- Mood label computation from composite metrics
- AC: Unit tests for computation and serialization

**E4-S2: Emotional state computation** (emotional.py) -- DONE
- Fatigue from normalized temp, error rate, uptime, power drift
- Confidence from success rate on current task type
- Curiosity from sensor state novelty vs historical mean
- AC: Unit tests with synthetic telemetry data

---

## Epic 5: Camera Calibration [DONE]

**Goal:** Guided camera-to-arm calibration using frame differencing, no markers needed.

### Stories

**E5-S1: Calibration procedure** (calibration.py) -- DONE
- CalibrationProcedure class: guides camera placement, collects points, fits homography with RANSAC
- PlacementScore and CalibrationPoint data models
- Works overhead, angled, or side-mounted
- Persists calibration to disk
- AC: Unit tests with mock arm bus and mock camera

---

## Epic 6: Web Dashboard [DONE]

**Goal:** Real-time fleet monitoring via HTTP served from the governor.

### Stories

**E6-S1: Web dashboard server** (web_dashboard.py) -- DONE
- WebDashboard class serves single-page app at localhost:8080
- aiohttp-based with SSE for live updates
- Displays neighborhood, tasks, health, marketplace status
- AC: Dashboard starts and serves data without errors

---

## Epic 7: Data Collection [DONE]

**Goal:** Record camera + arm episodes as LeRobot-compatible training datasets.

### Stories

**E7-S1: DataCollector and RecordingSession** (data_collection.py) -- DONE
- RecordingSession dataclass: task_label, episode_count, frame_count, fps, dataset_path
- DataCollector class: start_recording, stop_recording, finalize
- Outputs LeRobot-compatible dataset format
- AC: Unit tests with mock camera frames and arm positions

---

## Epic 8: Governor CLI [DONE]

**Goal:** Interactive REPL for natural language control of the entire fleet.

### Stories

**E8-S1: Governor CLI** (governor_cli.py) -- DONE
- Interactive command loop with NL parsing
- Commands: wave, sort, be gentle, slow down, what do you see, take photo, stop, status, tasks, skills, contracts, quit
- Color-coded output
- AC: CLI starts and routes all listed commands correctly

---

## Epic 9: Will Enhancement — Governor Absorption

**Goal:** Governor absorbs will data on citizen death: re-auctions tasks with partial progress, preserves XP in fleet genome, breaks symbiosis contracts cleanly.

### Stories

**E9-S1: Governor will reception and task re-listing**
- Governor receives will REPORT and extracts current_task_id, current_task_type, partial_results
- Re-lists the dead citizen's task in the marketplace with partial_progress attached to the task params
- New bidders see partial progress and can resume instead of restart
- AC: Integration test — citizen dies with active task, governor re-lists task, new citizen receives partial_results in PROPOSE

**E9-S2: XP preservation in fleet genome**
- Governor extracts XP dict from received will
- Merges dead citizen's XP into fleet average genome (weighted by citizen count)
- New citizens joining receive the enriched fleet genome
- AC: Unit test — will with XP={pick_and_place: 50} merges into fleet genome, new citizen inherits

**E9-S3: Contract cleanup on will receipt**
- Governor identifies active_contracts from will
- Sends contract-break notifications to all contract partners
- Partners exit symbiosis gracefully (remove composite capabilities, log event)
- Dashboard shows contract dissolution event
- AC: Integration test — citizen with active contract dies, partner receives break notification, composite capability removed

**E9-S4: Will archive and dashboard display**
- Governor persists all received wills to will_archive on disk (JSON)
- Dashboard shows will receipt events: "pi-follower: final will received — task re-listed"
- Will archive viewable via governor CLI `wills` command
- AC: Will persisted to ~/.citizenry/will_archive.json, dashboard event rendered, CLI shows archive

---

## Epic 10: Emotional State in Dashboard

**Goal:** Web dashboard and TUI display mood labels derived from emotional state metrics.

### Stories

**E10-S1: Mood label rendering in web dashboard**
- WebDashboard reads emotional_state from each citizen's heartbeat data
- Renders human-readable mood label per citizen: "focused", "tired", "uncertain", "curious"
- Label logic: high confidence + low fatigue = "focused", high fatigue = "tired", low confidence = "uncertain", high curiosity = "curious"
- Color-coded: green for focused, yellow for tired, orange for uncertain, blue for curious
- AC: Web dashboard displays mood label for each citizen; label changes when emotional state changes

**E10-S2: Mood label rendering in TUI dashboard**
- TUI dashboard (dashboard.py) adds mood column to citizen status table
- Same label logic as web dashboard
- AC: TUI renders mood labels correctly with mock emotional state data

**E10-S3: Emotional state history sparkline**
- Web dashboard shows fatigue trend over last 30 heartbeats as a sparkline per citizen
- Allows user to spot fatigue buildup before it becomes critical
- AC: Sparkline renders and updates live via SSE

---

## Epic 11: Federated Learning Foundations

**Goal:** Define model weight sharing format and exchange protocol for future federated learning. No actual FL training yet — this is the data contract.

### Stories

**E11-S1: Model weight envelope data model** (federated.py)
- ModelWeightEnvelope dataclass: citizen_pubkey, model_id, version, task_type, weight_format (numpy/safetensors), weight_hash (SHA256), weight_size_bytes, training_episodes, timestamp
- Serializes to JSON metadata (weights shipped separately as binary blob)
- AC: Unit tests for serialization, hash verification, version comparison

**E11-S2: Weight sharing protocol via REPORT**
- New REPORT body schema: type="model_weights_available" with ModelWeightEnvelope metadata
- Citizens announce available weights; governor aggregates announcements
- No actual weight transfer yet — just the announcement protocol
- AC: Unit test — citizen sends weight announcement, governor receives and catalogs it

**E11-S3: Weight registry in governor**
- Governor maintains a registry of available model weights per task type
- Registry tracks: which citizen trained it, how many episodes, version lineage
- Queryable via governor CLI: `models` command lists available weights
- AC: Unit test — registry stores and queries weight metadata; CLI lists models

---

## Epic 12: Multi-Location Architecture Design

**Goal:** Design the embassy model for multi-location nations connected via WireGuard VPN. Implementation is deferred — this epic produces the design artifacts and data models only.

### Stories

**E12-S1: Embassy and location data models** (embassy.py)
- Location dataclass: location_id, name, wireguard_endpoint, subnet, governor_pubkey, citizen_count, last_seen
- Embassy dataclass: local_location, remote_location, tunnel_status, latency_ms, bandwidth_kbps, established_at
- EmbassyRegistry: manages known locations and tunnel states
- AC: Unit tests for data models, serialization, registry CRUD

**E12-S2: Cross-location message routing design**
- Define how GOVERN/REPORT/HEARTBEAT messages route across WireGuard tunnels
- Design message relay: local governor relays to remote governor (no direct citizen-to-citizen cross-location)
- Document latency budget: cross-location heartbeats at 10s interval (vs 2s local)
- AC: Design documented in architecture doc; EmbassyRelay stub class with interface defined

**E12-S3: Location-aware constitution**
- Constitution gains location_policies: per-location law overrides (e.g., different servo limits at different sites)
- Governor merges global + local policies, local takes precedence
- AC: Unit test — constitution with location override returns correct effective law value

**E12-S4: Governor CLI location commands**
- `locations` command shows known locations and tunnel status
- `ping <location>` sends diagnostic probe across tunnel
- `sync <location>` exchanges fleet genome and immune memory
- AC: CLI commands defined with stub implementations; help text accurate

---

## Epic 13: Rolling Update End-to-End Integration

**Goal:** Wire rolling update engine into governor CLI and test with real law changes across live citizens.

### Stories

**E13-S1: Governor CLI rollout commands**
- `rollout <policy>` command initiates a rolling update through the RolloutEngine
- Displays live rollout progress: "gentle_mode: 2/3 passed, 0 failed, 1 pending"
- `rollout status` shows current rollout state
- `rollout abort` cancels in-progress rollout and triggers rollback
- AC: CLI commands correctly invoke RolloutEngine; progress displays in real time

**E13-S2: NL governance to rollout pipeline**
- When GovernorAide produces a policy change action, it routes through RolloutEngine instead of direct apply
- Confidence < 0.7 requires user confirmation before rollout begins
- `force_apply` bypass for emergency_stop (skips canary)
- AC: Integration test — NL command "be gentle" triggers rollout, not direct law update

**E13-S3: Citizen self-test on policy receipt**
- Citizen receives policy_canary GOVERN message
- Saves rollback snapshot of current law params
- Applies new params and runs self-test suite (joint range check, load test, fault check)
- Sends canary_result REPORT within 10 seconds
- On failure: reverts to snapshot immediately
- AC: Unit test with mock servo bus — self-test passes for valid policy, fails and reverts for invalid policy

**E13-S4: Rollout state persistence and crash recovery**
- RolloutEngine persists rollout state to disk (JSON) on each status change
- On governor restart, loads persisted state and triggers automatic rollback for any in-progress rollout
- AC: Unit test — simulate governor crash mid-rollout, verify rollback on restart

**E13-S5: Rollout audit log**
- Every rollout creates an audit entry: rollout_id, changes, citizen results, timestamps, final status
- Persisted to ~/.citizenry/rollout_audit.json
- Viewable via governor CLI: `rollout history`
- AC: Audit log written on rollout completion; CLI displays history

---

## Epic 14: NL Governance LLM Enhancement

**Goal:** Add Claude API as optional backend for NL governance, supplementing the pattern-based parser for complex or ambiguous intents.

### Stories

**E14-S1: Anthropic SDK integration** (nl_governance.py)
- Add optional Claude API call path using anthropic Python SDK
- API key loaded from ~/.citizenry/api_key (0600 permissions)
- Sends current constitution, laws, and citizen states as context
- Returns structured LawChange objects with reasoning
- AC: Unit test with mocked API response — correctly parses Claude output into GovernanceAction

**E14-S2: Confidence-based routing**
- Pattern parser runs first; if confidence < 0.7, escalate to Claude API
- If API unreachable (no internet, key missing, budget exhausted), fall back to pattern result with degradation warning
- Log which path handled each command (pattern vs API)
- AC: Unit test — low-confidence pattern result triggers API call; API failure falls back gracefully

**E14-S3: Monthly API budget enforcement**
- Track API call costs in ~/.citizenry/api_usage.json (monthly totals)
- monthly_api_budget law (default $5.00) caps total spend
- When budget exhausted, NL governance operates in pattern-only mode with user notification
- AC: Unit test — budget tracking increments correctly; budget exceeded triggers fallback mode

**E14-S4: Complex intent support**
- Claude handles multi-part intents: "be gentle but keep the camera running at full resolution"
- Claude handles relative intents: "a bit faster than before" (requires current state context)
- Claude handles role assignment: "the Pi arm should focus on sorting"
- AC: Integration test with mocked API — multi-part intent produces multiple LawChange objects

---

## Epic 15: Camera Calibration Interactive Flow

**Goal:** Wire the calibration procedure into the governor CLI as a guided, interactive experience.

### Stories

**E15-S1: Governor CLI calibration command**
- `calibrate` command launches interactive calibration flow
- Prompts user through camera placement, displays placement score
- Shows real-time progress: "Point 3/8 collected, reprojection error: 2.1px"
- AC: CLI command starts calibration procedure; user sees step-by-step guidance

**E15-S2: Calibration status and re-calibration**
- `calibrate status` shows current calibration: valid/expired, reprojection error, when last calibrated
- `calibrate reset` clears calibration and starts fresh
- Auto-suggest re-calibration when reprojection error drifts above threshold (detected during task execution)
- AC: Status command displays calibration data; reset clears persisted calibration

**E15-S3: Calibration result integration with visual tasks**
- CalibrationResult automatically loaded by visual task pipeline (color detection, pick-and-place)
- If no calibration exists, visual tasks warn and use approximate defaults
- If calibration is stale (>24h), visual tasks log warning but proceed
- AC: Visual task reads calibration from persistence; missing calibration produces warning, not crash

---

## Epic 16: Data Collection Teleop Integration

**Goal:** Automatically record camera + arm data during teleop sessions for LeRobot training.

### Stories

**E16-S1: Auto-record during teleop**
- When teleop starts, DataCollector automatically begins a recording session
- Each teleop episode (start → stop → reset) becomes one training episode
- Recording captures: camera frames at configured FPS, arm servo positions at each frame, task label
- AC: Integration test — teleop session produces LeRobot-compatible episode data

**E16-S2: Governor CLI recording controls**
- `record start [task_label]` begins recording with optional label (default: "teleoperation")
- `record stop` ends current episode and saves
- `record status` shows: recording yes/no, episode count, frame count, disk usage
- `record finalize` closes dataset, computes statistics, prints summary
- AC: CLI commands control DataCollector; status displays accurate metrics

**E16-S3: Episode annotation and filtering**
- After each episode, prompt user: "Keep this episode? [Y/n/label]"
- User can relabel ("pick_and_place"), keep (Y), or discard (n) the episode
- Discarded episodes are deleted from disk immediately
- AC: Prompt appears after episode; discard removes files; relabel updates metadata

**E16-S4: Dataset upload stub**
- `record upload` command defined with stub implementation
- Prints: "Upload to HuggingFace Hub — not yet implemented. Dataset at: <path>"
- Prepares for future HF Hub integration without adding the dependency now
- AC: Command exists, prints path, does not crash

---

## Sprint Plan

### Sprint 1: Governor Intelligence (Epics 9, 13, 14)
- E9-S1, E9-S2, E9-S3, E9-S4: Will absorption and cleanup
- E13-S1, E13-S2: CLI rollout commands + NL-to-rollout pipeline
- E14-S1, E14-S2: Claude API integration + confidence routing
- All unit tests for these stories

### Sprint 2: Citizen Robustness (Epics 10, 13, 14)
- E13-S3, E13-S4, E13-S5: Self-test, crash recovery, audit log
- E14-S3, E14-S4: Budget enforcement + complex intents
- E10-S1, E10-S2, E10-S3: Mood labels in web + TUI dashboards

### Sprint 3: Interactive Flows (Epics 15, 16)
- E15-S1, E15-S2, E15-S3: Calibration CLI flow + visual task integration
- E16-S1, E16-S2, E16-S3, E16-S4: Teleop recording + annotation + upload stub

### Sprint 4: Architecture & Foundations (Epics 11, 12)
- E11-S1, E11-S2, E11-S3: Federated learning data models + weight protocol + registry
- E12-S1, E12-S2, E12-S3, E12-S4: Embassy model + routing design + location-aware constitution + CLI
