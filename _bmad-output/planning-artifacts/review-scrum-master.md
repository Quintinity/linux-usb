# Scrum Master Execution Review -- RobotOS USB MVP

**Reviewer:** Bob (Scrum Master)
**Date:** 2026-03-15
**Scope:** All planning artifacts, sprint plan, and sprint status
**Verdict:** Conditionally approved with mandatory mitigations below

---

## 1. Overall Assessment

The planning is thorough. The PRD, architecture, epics, and sprint plan are well-aligned and the dependency chains are correctly identified. The FR coverage map is complete. The critical path analysis is accurate.

However, the plan has three structural problems that will cause delivery to slip if not addressed:

1. **Sprint 4 and Sprint 6 are overloaded** -- not slightly, but dangerously.
2. **No Sprint 0** -- CI/CD, test infrastructure, and hardware validation are assumed to happen alongside feature work.
3. **The two XL stories (4.2 and 8.1) are each large enough to be their own sprint.**

The 12-14 week estimate is optimistic. Realistic delivery with the mitigations below is **14-18 weeks**.

---

## 2. Velocity Analysis

### Assumptions

The sprint plan assigns story points (weights) using S=1, M=3, L=5, XL=8. For a solo developer + AI pair programming:

| Sprint | Planned Weight | Realistic Capacity (2 weeks) |
|--------|---------------|------------------------------|
| 1 | 5 | 8-10 (underloaded) |
| 2 | 14 | 12-15 (at limit) |
| 3 | 8 | 12-15 (underloaded) |
| 4 | 24 | 12-15 (**overloaded by 60-100%**) |
| 5 | 14 | 12-15 (at limit) |
| 6 | 33 | 12-15 (**overloaded by 120-175%**) |

**Key observation:** Sprints 1 and 3 are underloaded while Sprints 4 and 6 are dangerously overloaded. This is a leveling problem, not a capacity problem. Total MVP weight is 98 (excluding backlog). At 12-15 points per sprint, that is 7-8 sprints of work being crammed into 6.

### Recommendation: Rebalance to 7 Sprints

Redistribute work across 7 two-week sprints targeting 14 points each (98 / 7 = 14). See Section 7 for the revised plan.

---

## 3. Sprint 4 Mitigation (Weight 24)

Sprint 4 packs Epics 4 and 5 into a single sprint. The problem is Story 4.2 (Migrate Existing Diagnostic Checks, XL=8), which depends on 4.1 finishing first -- meaning it cannot start until mid-sprint at the earliest.

### Concrete Mitigation

1. **Pull 3.1 (Profile Schema) into Sprint 2.** It only depends on 1.1 and 1.4, not on Epic 2. This frees Sprint 3 capacity.
2. **Pull 4.1 (DiagnosticRunner) and 5.1 (TelemetryStream) into Sprint 3.** Both depend on 2.1 + 3.1. If Sprint 2 completes on time, these can start in Sprint 3 alongside 3.2, 3.3, 3.4.
3. **Keep 4.2 (XL) as the centerpiece of Sprint 4.** With 4.1 done in Sprint 3, 4.2 gets the full two weeks.
4. **Split 4.2 into two halves if needed:**
   - 4.2a: First 6 checks (PortDetection, ServoPing, FirmwareVersion, PowerHealth, StatusRegister, EEPROMConfig) -- L=5
   - 4.2b: Remaining 5 checks (CommsReliability, TorqueStress, CrossBusTeleop, MotorIsolation, CalibrationValid) -- L=5

---

## 4. Sprint 6 Mitigation (Weight 33)

Sprint 6 is the real problem. It combines the TUI (Epic 7), the USB image build (Epic 8), the LeRobot bridge (Epic 9), and the AI context work -- three different epics with very different skill sets (Python TUI, Debian live-build packaging, LeRobot integration).

### Concrete Mitigation

**Split into Sprint 6a and 6b** (the plan already suggests this, but I am making it mandatory):

**Sprint 6a (Weeks 11-12): TUI + Data Collection**
- 7.1 TUI Application Shell (M=3)
- 7.2 Live Telemetry Panel (M=3)
- 7.3 Workflow Launcher Panel (L=5)
- 9.2 LeRobot Bridge (M=3)
- 9.3 Data Collection Command (L=5)
- **Total: 19** -- still heavy, but 7.3 and 9.3 can overlap

**Sprint 6b (Weeks 13-14): USB Image + Polish**
- 8.1 live-build Configuration (XL=8)
- 8.2 System Configuration Baked Into Image (L=5)
- 8.3 Windows Flash Script Update (M=3)
- 9.1 Claude Code Context Pre-seeding (S=1)
- **Total: 17** -- manageable

**Sprint 7 (Weeks 15-16): Hardware Testing + Buffer**
- 8.4 Hardware Compatibility Testing (L=5)
- Bug fixes, polish, overflow from earlier sprints
- MVP release preparation
- **Total: 5 + buffer**

### Why 8.1 Needs a Spike in Sprint 4 or 5

Story 8.1 (live-build ISO) depends on nearly everything else being done, but the *learning curve* for Debian live-build is steep. If you wait until Sprint 6b to touch live-build for the first time, you will lose 3-5 days just getting the build working.

**Action: Run a time-boxed spike (2-3 days) in Sprint 4 or 5.**
- Goal: Get a minimal live-build producing a bootable ISO with Python 3.12 + a "hello world" robotos package.
- This de-risks the packaging step and exposes any live-build limitations early.

---

## 5. XL Story Decomposition

### Story 4.2: Migrate Existing Diagnostic Checks (XL=8)

This story migrates 11 diagnostic phases. Each phase is essentially an independent health check class. It should be split:

| Sub-task | Checks | Est. Size |
|----------|--------|-----------|
| 4.2a | PortDetection, ServoPing, FirmwareVersion, PowerHealth, StatusRegister, EEPROMConfig | L (5) |
| 4.2b | CommsReliability, TorqueStress, CrossBusTeleop, MotorIsolation, CalibrationValid | L (5) |

4.2a covers the "read-only" checks (no servo movement). 4.2b covers the "active" checks (require torque, cross-bus coordination). This split is natural and reduces risk -- 4.2a can ship while 4.2b is still in progress.

### Story 8.1: live-build Configuration and ISO Build Script (XL=8)

This story conflates three different activities:
1. Writing the live-build configuration files
2. Getting the build to produce a bootable ISO
3. Baking in all robotos dependencies

Recommended split:

| Sub-task | Scope | Est. Size |
|----------|-------|-----------|
| 8.1a | Minimal live-build config that boots to Ubuntu desktop | M (3) |
| 8.1b | Add robotos package, LeRobot, Python venv, SO-101 profile | L (5) |

8.1a is the spike candidate for Sprint 4/5. 8.1b is the Sprint 6b work.

---

## 6. Story Reordering for Faster Value Delivery

The current plan delivers the first user-visible value (detect -> calibrate -> teleop) in Sprint 5, week 10. That is too late. If the HAL design is wrong, you do not find out until week 10.

### Recommended Reorder

**Pull Story 6.4 (Hardware Detection Command) into Sprint 2.** It depends on 2.1 and 1.3 -- both Sprint 2 stories. Having `robotos detect` working at the end of Sprint 2 gives immediate user-facing validation that the HAL works.

**Pull Story 6.1 (Interactive Calibration) into Sprint 3.** It depends on 2.1, 3.1, and 3.3 -- all available by Sprint 3. This gives calibrate-and-verify capability by week 6 instead of week 10.

This means the first end-to-end workflow (detect -> calibrate -> teleop) is possible by Sprint 4 instead of Sprint 5, saving two weeks of feedback latency.

---

## 7. Revised Sprint Plan

| Sprint | Weeks | Stories | Weight | Theme | Demo |
|--------|-------|---------|--------|-------|------|
| 0 | 0-1 | CI/CD setup, test harness, hardware inventory | 0 | Tooling | Green CI, hardware matrix |
| 1 | 1-2 | 1.1, 1.2, 1.3, 1.4, 1.5 | 5 | Package skeleton | `robotos --help` works |
| 2 | 3-4 | 2.1, 2.2, 2.3, 2.4, 3.1, 6.4 | 17 | HAL + profiles + detect | `robotos detect` finds servos |
| 3 | 5-6 | 3.2, 3.3, 3.4, 4.1, 5.1, 6.1 | 14 | Calibration + framework foundations | `robotos calibrate` works end-to-end |
| 4 | 7-8 | 4.2a, 4.3, 4.4, 5.2, 5.3, 6.2, 6.3 | 21 | Diagnostics + teleop | `robotos teleop` -- **first full demo** |
| 5 | 9-10 | 4.2b, 7.1, 7.2, 7.3, 9.2 | 19 | TUI + remaining diagnostics | TUI dashboard with live telemetry |
| 6 | 11-12 | 8.1, 8.2, 8.3, 9.1, 9.3 | 17 | USB image + data collection | Bootable ISO, `robotos record` |
| 7 | 13-14 | 8.4, buffer, release prep | 5+ | Testing + release | MVP shipped |

**Total: 14 weeks (7 sprints x 2 weeks)**

Sprint 2 is heavy at 17, but 3.1 has no dependency on Epic 2 and can run in parallel with 2.1. Sprint 4 is heavy at 21 but contains many parallelizable items (4.3, 5.2, 5.3 can all run simultaneously once their parents are done).

---

## 8. Minimum Viable Demo at Each Sprint Boundary

| Sprint | Demo | Stakeholder Value |
|--------|------|-------------------|
| 0 | CI runs, tests pass on empty package | "We can ship code safely" |
| 1 | `robotos --help` shows all commands, `pip install -e .` works | "The package exists" |
| 2 | `robotos detect` finds CH340 + servos on real hardware | "It talks to the robot" |
| 3 | `robotos calibrate` walks through joint homing, data persists | "The robot remembers its setup" |
| 4 | `robotos teleop` -- move leader arm, follower mirrors | **"The robot works"** -- this is the money demo |
| 5 | TUI dashboard with live telemetry, diagnostics, workflow launcher | "No terminal commands needed" |
| 6 | Boot from USB, everything works without install | "Plug and play" |
| 7 | Tested on 5+ machines, documented compatibility | "Ready for users" |

---

## 9. Top 5 Risks to Delivery

### Risk 1: live-build packaging is harder than expected (CRITICAL)

**Likelihood:** High
**Impact:** High (blocks MVP ship)
**Why:** Debian live-build is finicky. Baking a Python venv with compiled packages (numpy, etc.) into a live ISO has known failure modes: path issues, library versioning, UEFI secure boot. Nobody on the team has done this before.

**Mitigation:**
- Run the live-build spike in Sprint 4 (mandatory, not optional)
- Have a fallback plan: ship a traditional installer script (like the current CLAUDE.md phases) alongside a base Ubuntu ISO. Less elegant, but shippable.
- Budget 3 days of troubleshooting time in Sprint 6

### Risk 2: ServoProtocol ABC needs redesign after downstream integration (HIGH)

**Likelihood:** Medium
**Impact:** High (refactoring ripples through Epics 3-9)
**Why:** The ABC is designed before its consumers exist. The interface for `sync_read` retry behavior, telemetry polling, and calibration reads may not match what the teleop loop and diagnostic framework actually need.

**Mitigation:**
- Before declaring 2.1 "done," write a mini integration test that exercises the ABC through the calibrate and teleop workflows (even with hardcoded data)
- Review the ABC interface against 6.1 and 6.2 acceptance criteria explicitly
- Accept that one ABC revision in Sprint 3 is likely and budget for it

### Risk 3: Sprint 4/6 overload causes cascading delays (HIGH)

**Likelihood:** High (it is a mathematical certainty if not rebalanced)
**Impact:** High (every subsequent sprint slips)

**Mitigation:**
- Adopt the revised 7-sprint plan above
- Enforce a "no overflow" rule: if a story is not done by sprint end, it moves to the next sprint and something else gets cut
- The overflow candidate order is: 4.2b > 7.3 > 9.3 > 8.4

### Risk 4: Hardware availability and test environment (MEDIUM)

**Likelihood:** Medium
**Impact:** Medium
**Why:** Story 8.4 requires 5+ distinct x86 machines. The current setup has one Surface Pro 7. USB cameras are needed by Sprint 4 for teleop monitor validation. Testing live-build ISOs requires a second machine (cannot test a USB boot on the machine building the ISO).

**Mitigation:**
- Inventory all available hardware by Sprint 0
- Source 2-3 additional test machines (borrow, thrift store, etc.) by Sprint 5
- Use QEMU/KVM for initial ISO boot testing (imperfect but catches 80% of issues)
- USB cameras: order by end of Sprint 1 if not already available

### Risk 5: LeRobot v0.5.0 compatibility and upstream changes (LOW but catastrophic)

**Likelihood:** Low
**Impact:** Very High
**Why:** The entire data collection pipeline (Epic 9) and the FeetechPlugin (Story 2.1) wrap LeRobot internals. If LeRobot releases a breaking change to `FeetechMotorsBus` or the data format, the bridge layer (9.2) and the HAL (2.1) break.

**Mitigation:**
- Pin to `lerobot==0.5.0` in pyproject.toml (already planned)
- The bridge layer (9.2) isolates LeRobot from the rest of the system -- this is good
- Do not upgrade LeRobot during the MVP cycle under any circumstances
- Add a CI test that installs lerobot 0.5.0 and imports it successfully

---

## 10. Definition of Done Analysis

The sprint plan's Definition of Done (12 criteria) is comprehensive but has two problems:

### Problem 1: "Compatibility validated on 5+ x86 models with 80%+ success"

This requires hardware the team may not have. The DoD should distinguish between:
- **MVP ship blocker:** Boots on Surface Pro 7 + one other machine
- **Nice to have:** 5+ models validated
- **Post-MVP:** 80%+ compatibility across 20+ models

### Problem 2: No automated test coverage requirement

The DoD says nothing about test coverage. Each story has acceptance criteria, but there is no requirement that these be automated tests rather than manual verification.

**Recommendation:** Add to the DoD:
- Every story has at least one automated test (unit or integration) that validates its core acceptance criterion
- The CI pipeline is green before any story is marked "done"
- Manual hardware testing is documented in a test log (date, hardware, result, notes)

### Revised MVP Ship Criteria

The MVP is shippable when:
1. All 34 MVP stories are "done" with automated tests passing
2. `robotos teleop` works end-to-end on real SO-101 hardware
3. The ISO boots on the Surface Pro 7 and at least one non-Surface machine
4. `robotos record` produces a valid LeRobot dataset
5. The TUI launches and all keyboard shortcuts work
6. No FAIL-severity diagnostic check is unresolved

---

## 11. Sprint 0 Recommendation

**Verdict: Yes, Sprint 0 is mandatory.** Allocate 1 week (not 2).

### Sprint 0 Deliverables

| Item | Why |
|------|-----|
| GitHub Actions CI pipeline | Every PR gets tested. Catch regressions early. Without this, "works on my machine" becomes the test strategy. |
| pytest + fixtures for hardware mocking | Stories 2.1-2.4 need mock servos. Writing the mock framework alongside the first tests is cheaper than retrofitting. |
| Pre-commit hooks (ruff, mypy) | Code quality from day 1. Cheaper than fixing style in Sprint 5. |
| Hardware inventory document | What machines, cameras, USB hubs are available? What needs to be sourced? |
| Development environment setup script | `make dev` installs everything. Reproducible dev setup. |
| Decision: live-build feasibility check | 2 hours of research. Is live-build the right tool? Are there show-stoppers? |

---

## 12. Communication Cadence

| Event | Frequency | Format |
|-------|-----------|--------|
| Daily standup | Daily (async) | 3 bullets in a log file: did, doing, blocked |
| Sprint review | Every 2 weeks | Live demo of working software on real hardware |
| Sprint retrospective | Every 2 weeks | What worked, what did not, one thing to change |
| Mid-sprint check-in | Weekly | Quick status: on track, at risk, or blocked? |
| Risk review | Every 2 sprints | Review and update the risk register |
| Stakeholder update | Monthly | Summary email/post: what shipped, what is next, any asks |

### Retrospective Triggers (Stop and Reassess)

Stop the current sprint and hold an emergency retro if any of these occur:

1. **A story takes more than 2x its estimated time.** The estimate was wrong -- reassess the remaining plan.
2. **The ServoProtocol ABC needs a second major revision.** The abstraction is not stabilizing -- consider a different design approach.
3. **The live-build spike fails completely.** The OS packaging strategy needs to change -- evaluate alternatives (Cubic, casper-rw, nix, etc.).
4. **Hardware dies.** The Surface Pro 7 or the SO-101 servos fail. The entire project depends on this hardware.
5. **Two consecutive sprints miss their goals by more than 30%.** Velocity is not what was assumed -- re-scope the MVP.

---

## 13. Blocker Inventory

| Blocker | Stories Affected | Lead Time | Status |
|---------|-----------------|-----------|--------|
| USB cameras not available | 6.3, 6.4, 9.3 | 1-2 weeks to ship | Unknown -- verify in Sprint 0 |
| Second x86 test machine | 8.1, 8.4 | Need by Sprint 6 | Unknown |
| LeRobot v0.5.0 has undocumented breaking changes | 2.1, 9.2, 9.3 | N/A | Pin version, test early |
| live-build requires root access / VM | 8.1 | Build machine setup | Needs investigation in Sprint 0 |
| Feetech servo firmware issues | 2.1, 2.4 | Requires Windows machine | Already documented |
| `textual` library limitations for TUI | 7.1, 7.2, 7.3 | N/A | Evaluate in Sprint 0 research |

---

## 14. What "Done" Looks Like for the MVP

### The Acceptance Test

A person who has never seen RobotOS before receives:
1. A USB stick with the ISO flashed
2. A laptop (not a Surface Pro 7)
3. An SO-101 robot kit (assembled, servos connected)

They must be able to:
1. Boot from the USB stick
2. See the TUI dashboard
3. Connect the robot (plug in USB cables)
4. See the robot detected in the dashboard
5. Calibrate both arms through the guided procedure
6. Run leader-follower teleoperation
7. Record 3 episodes of data collection
8. Run diagnostics and see all checks pass
9. Reboot and have calibration still present

**Without opening a terminal. Without reading documentation. Without internet.**

Time budget: under 10 minutes for steps 1-6 (5-minute target for boot-to-teleop, with margin for first-time confusion).

This is the acceptance test. If a first-time user cannot do this, the MVP is not done.

---

## 15. Summary of Mandatory Actions

| # | Action | When | Owner |
|---|--------|------|-------|
| 1 | Add Sprint 0 (1 week) for CI/CD, test infrastructure, hardware inventory | Before Sprint 1 | SM/Dev |
| 2 | Rebalance to 7 sprints per revised plan (Section 7) | Now | SM |
| 3 | Split Story 4.2 into 4.2a and 4.2b | Before Sprint 4 | PM/Dev |
| 4 | Split Story 8.1 into 8.1a (spike) and 8.1b (full build) | Before Sprint 4 | PM/Dev |
| 5 | Run live-build spike (8.1a) in Sprint 4 or 5 | Sprint 4-5 | Dev |
| 6 | Pull 6.4 (detect) into Sprint 2 for early value | Sprint 2 | SM |
| 7 | Pull 6.1 (calibrate) into Sprint 3 for early value | Sprint 3 | SM |
| 8 | Add automated test requirement to Definition of Done | Sprint 0 | SM |
| 9 | Inventory hardware and source test machines + USB cameras | Sprint 0 | Dev |
| 10 | Establish fallback plan for OS image delivery (installer script) | Sprint 5 | Dev/SM |

---

_Execution review for RobotOS USB MVP -- generated by Bob (Scrum Master Agent)._
