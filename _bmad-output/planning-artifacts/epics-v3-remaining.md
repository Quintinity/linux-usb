---
project: armOS Citizenry v3.0 — Remaining Implementation
date: 2026-03-16
status: approved
---

# Remaining v3.0 Epics — PRD Gap Closure

All modules exist. These epics wire up the end-to-end flows that the PRD requires but aren't fully connected yet.

---

## Epic A: NL Governance Enhancement (FR-1.3, FR-1.4, FR-1.6)

**E-A1: Rich Claude API context**
- Send full constitution, current laws, citizen states, and recent policy history as context
- Use structured prompt that returns LawChange objects with confidence
- AC: Claude call includes constitution + citizen list in prompt

**E-A2: Confidence-based auto-apply**
- If confidence >= 0.7 and auto_apply_policy law is true → apply without confirmation
- If confidence < 0.7 → show proposed changes, ask user to confirm
- AC: Low-confidence change prompts user; high-confidence auto-applies

**E-A3: Policy history logging**
- Log every NL policy change: original text, interpreted changes, confidence, confirmed/auto
- Persist to ~/.citizenry/policy_history.json
- `policy history` CLI command shows last 20 entries
- AC: Policy changes appear in history file

---

## Epic B: Canary Self-Test Protocol (FR-2.3 through FR-2.8)

**E-B1: Citizen self-test framework**
- Each citizen implements `_run_self_test()` returning pass/fail
- Arm: move each joint through 50% range at current limits, check for faults
- Camera: capture frame, verify resolution
- AC: Self-test runs without errors on real hardware

**E-B2: Canary protocol messages**
- Governor sends GOVERN `type: "policy_canary"` with rollback snapshot
- Citizen applies, runs self-test, sends REPORT `type: "canary_result"`
- On failure: citizen reverts automatically
- AC: Integration test with mock citizen

**E-B3: Rollout crash recovery**
- Persist rollout state to disk before starting
- On governor restart, detect incomplete rollout → auto-rollback
- AC: Simulated crash during rollout → recovery on restart

---

## Epic C: Fatigue Bid Modifier + Consciousness Stream (FR-4.3, FR-5)

**E-C1: Fatigue-adjusted marketplace bids**
- `adjusted_score = base_score * (1.0 - 0.3 * fatigue)`
- Fatigued citizens bid lower, get fewer tasks, rest more
- AC: Unit test — fatigued citizen's bid is 30% lower

**E-C2: Consciousness stream (template-based)**
- Template narration: "Executing {task}. {joint} load at {load}%. Confidence: {confidence}."
- REPORT with `type: "consciousness"` at most once per 5 seconds
- Dashboard displays latest narration per citizen
- AC: Consciousness report visible in web dashboard

---

## Epic D: Federated Learning End-to-End (Epic 11 wiring)

**E-D1: Weight announcement flow**
- After task completion with high XP, citizen announces model weights via REPORT
- Governor registers in WeightRegistry
- AC: Weight announcement appears in governor registry

**E-D2: Weight request and transfer**
- New citizen sends PROPOSE `task: "weight_transfer"` to governor
- Governor responds with weight envelope location
- AC: New citizen can request and receive weight metadata

---

## Epic E: Multi-Location Embassy Prototype (Epic 12 wiring)

**E-E1: Location registration in governor**
- Governor maintains LocationRegistry from config
- `locations` CLI command shows registered locations
- AC: Location list displayed in CLI

**E-E2: Cross-location message relay design doc**
- Document the embassy relay protocol (not implemented — design only)
- How heartbeats, tasks, and genome are relayed across VPN
- AC: Design doc in planning-artifacts

---

## Sprint Plan

**Sprint V3-A** (build now): Epics A + C (NL enhancement + fatigue + consciousness)
**Sprint V3-B** (build now): Epic B (canary self-test)
**Sprint V3-C** (build now): Epics D + E (federated + multi-location wiring)
