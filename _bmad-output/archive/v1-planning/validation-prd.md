# PRD Validation Report

**Document:** `prd.md` (RobotOS USB)
**Validator:** QA Validator (BMAD Framework)
**Date:** 2026-03-15
**Cross-referenced against:** `product-brief.md`, `architecture.md`

---

## Summary

| Check | Result | Issues |
|-------|--------|--------|
| 1. FR unique IDs, clear descriptions, testability | PASS | 0 |
| 2. NFR measurable criteria | PASS | 1 Minor |
| 3. Success metrics specific and measurable | PASS | 1 Minor |
| 4. User journeys complete | PASS | 0 |
| 5. MVP scope clearly defined | PASS | 2 Major |
| 6. No contradictions between sections | FAIL | 2 Major |
| 7. No vague language | PASS | 1 Minor |
| 8. Technical constraints realistic | PASS | 0 |
| 9. Dependencies between FRs noted | FAIL | 1 Major |
| 10. No orphaned requirements | PASS | 1 Minor |
| Cross-ref: PRD fulfills product brief | PASS | 1 Minor |
| Cross-ref: FRs architecturally feasible | PASS | 0 |

**Overall: CONDITIONAL PASS -- 5 Major issues must be resolved before implementation.**

---

## Check 1: FR Unique IDs, Clear Descriptions, Testability

**Result: PASS**

All 41 functional requirements (FR1-FR41) have unique IDs and clear descriptions. Each is phrased as a capability ("The system can..." / "Users can...") which is directly testable.

No issues found.

---

## Check 2: NFR Measurable Criteria

**Result: PASS (1 Minor)**

All 22 NFRs (NFR1-NFR22) include quantitative thresholds or specific criteria.

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 2.1 | Minor | NFR18 specifies "fewer than 10 required methods" and "under 500 lines of code." The architecture's `ServoProtocol` ABC (architecture.md lines 254-303) already defines 12 abstract methods. Either the interface count needs to increase to match architecture, or the architecture needs consolidation. | Line 304 (NFR18) |

**Recommended fix for 2.1:** Update NFR18 to say "fewer than 15 required methods" to match the architecture's actual `ServoProtocol` interface which has 12 methods, or consolidate the architecture ABC.

---

## Check 3: Success Metrics Specific and Measurable

**Result: PASS (1 Minor)**

All 8 success criteria (SC1-SC8) have targets, measurement methods, and traceability.

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 3.1 | Minor | SC6 ("100+ GitHub stars within 6 months") is not within the team's control and is not a product quality metric. It is a vanity metric that cannot guide engineering decisions. | Line 47 (SC6) |

**Recommended fix for 3.1:** Demote SC6 to a "tracking metric" or replace with something actionable, e.g., "Community-contributed robot profiles: 3+ within 6 months."

---

## Check 4: User Journeys Complete

**Result: PASS**

All 5 user journeys (UJ1-UJ5) have:
- Named actor with role
- Clear trigger
- Numbered sequential steps
- Defined success condition
- Traceability to success criteria

No issues found.

---

## Check 5: MVP Scope Clearly Defined

**Result: PASS (2 Major)**

The MVP includes/excludes list is explicit and traces FRs to phases. However:

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 5.1 | Major | FR3 (profile matching against library) is not listed in the MVP includes list (line 340), yet MVP includes FR7 (load profiles) and FR10 (SO-101 profile). If FR3 is excluded, how does the MVP match detected hardware to the SO-101 profile? The MVP scope says "USB-serial auto-detection for CH340 adapters" but does not explicitly include the profile-matching step. FR3 appears to be implicitly required but is not listed. | Line 340 |
| 5.2 | Major | FR4 (camera detection via V4L2) and FR5 (assign cameras to roles) are not in the MVP includes list, but the MVP scope description (line 61) says "USB camera detection and V4L2 configuration" is included. FR4 should be added to the MVP FR list. FR5 may be deferred (user confirmation of assignment is not needed with a single camera). | Lines 58-62 vs line 340 |

**Recommended fix for 5.1:** Add FR3 (limited to single-profile matching for SO-101) to the MVP includes list, or add a note that MVP uses hard-coded SO-101 detection without profile matching.

**Recommended fix for 5.2:** Add FR4 to the MVP FR list on line 340. Explicitly note that FR5 is deferred (MVP auto-assigns the first camera).

---

## Check 6: No Contradictions Between Sections

**Result: FAIL (2 Major)**

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 6.1 | Major | NFR21 (line 311) says "Servo bus access shall be restricted to the RobotOS user and root via udev rules. No world-writable serial device nodes." But FR6 (line 207) says the system configures "udev rules and serial port permissions automatically, without requiring manual terminal commands or root access." The architecture's udev rules (architecture.md line 373) use `MODE="0666"` which IS world-writable, directly contradicting NFR21. The existing project udev rule in CLAUDE.md also uses `MODE="0666"`. Either NFR21 must relax to allow group-writable (MODE="0660", GROUP="dialout") and FR6 must ensure the user is in the dialout group, or NFR21 must be rewritten. | Lines 207, 311; architecture.md line 373 |
| 6.2 | Major | The Product Scope section (line 71) says Growth phase will support "TUI dashboard for robot status, calibration, and teleoperation launch." But the MVP scope (line 334) already includes "TUI-based launcher menu (calibrate, teleop, diagnose, monitor)" and line 340 says FR33 and FR34 are in MVP as "TUI version." The Growth scope should say "full-featured TUI dashboard" not introduce TUI as new. This is a labeling/clarity issue but could mislead implementation planning. | Lines 71 vs 334 |

**Recommended fix for 6.1:** Change NFR21 to: "Servo bus access shall be restricted to the `dialout` group via udev rules using `MODE=0660`. The default RobotOS user shall be a member of `dialout`." Update the architecture udev rules from `MODE="0666"` to `MODE="0660"`.

**Recommended fix for 6.2:** Rephrase line 71 to "Full-featured TUI dashboard with real-time telemetry, multi-robot support" to distinguish from the MVP's basic TUI launcher menu.

---

## Check 7: No Vague Language

**Result: PASS (1 Minor)**

The document generally uses strong, testable language ("can", "shall", "must"). One instance of soft language:

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 7.1 | Minor | FR14 (line 221): "warn if calibration appears stale or invalid." The word "appears" is vague. What makes calibration stale? There is no defined threshold (e.g., time since calibration, position drift tolerance). | Line 221 |

**Recommended fix for 7.1:** Rephrase FR14 to: "The system can validate stored calibration against current servo positions and warn if any joint position at the home pose deviates by more than N encoder ticks from the stored calibration value, or if calibration is older than N days."

---

## Check 8: Technical Constraints Realistic

**Result: PASS**

All 8 technical constraints (TC1-TC8) are realistic and align with the existing project state:
- TC1 (no GPU) matches the Surface Pro 7 hardware and Intel iGPU reality.
- TC2 (USB boot) is proven possible with existing flash.ps1 pipeline.
- TC3 (offline) is achievable since all dependencies are pre-installed.
- TC4 (Python) matches existing codebase and LeRobot ecosystem.
- TC5 (LeRobot compat) is validated by existing working integration.
- TC6 (open source) is feasible; no proprietary dependencies identified.
- TC7 (x86 only) is a reasonable scope limit for v1.0.
- TC8 (single user) matches the USB-booted desktop model.

No issues found.

---

## Check 9: FR Dependencies Noted

**Result: FAIL (1 Major)**

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 9.1 | Major | No FR dependency chain is documented anywhere in the PRD. Several FRs have implicit hard dependencies that, if not tracked, will cause blocked implementation: FR15 (teleop) depends on FR12 (calibration) and FR7 (profiles). FR24 (data collection) depends on FR15 (teleop) and FR4 (cameras). FR3 (profile matching) depends on FR1 (USB detection) and FR2 (bus scan). FR19 (diagnostics) depends on FR1 and FR2. FR36 (actionable errors) depends on FR23 (fault detection). None of these are stated. | Entire FR section (lines 198-269) |

**Recommended fix for 9.1:** Add a "Dependency Map" subsection after the FR list, or annotate each FR with a `Depends on:` field. At minimum, document the critical path: FR1 -> FR2 -> FR3 -> FR7 -> FR12 -> FR15 -> FR24.

---

## Check 10: No Orphaned Requirements

**Result: PASS (1 Minor)**

All FRs trace to at least one user journey or success criterion. One borderline case:

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 10.1 | Minor | FR41 (load third-party plugins from a designated directory) is deferred to Vision phase and traces to UJ4 (maker with custom hardware). However, UJ4 focuses on profile creation, not driver plugins. There is no user journey that specifically covers "developer implements and installs a third-party servo protocol driver." This is fine for Vision phase but should get its own UJ before implementation. | Line 269 |

**Recommended fix for 10.1:** Add a UJ for "Developer adds a new servo protocol driver" before implementing FR39/FR41. Not blocking for MVP.

---

## Cross-Reference: PRD vs Product Brief

**Result: PASS (1 Minor)**

The PRD covers all items from the product brief:

| Brief Item | PRD Coverage |
|------------|-------------|
| Boot-from-USB | FR28, FR29, FR30, FR31, FR32 |
| Hardware Auto-Detection | FR1, FR2, FR3, FR4, FR5 |
| Universal Robot API | FR39, FR40, FR41 + architecture HAL |
| AI-Assisted Setup | FR37, FR38 |
| Built-in Diagnostics | FR19-FR23 |
| Plug-and-Play Profiles | FR7-FR11 |
| Target users (4 types) | UJ1-UJ5 cover all 4 |
| Success metrics (5) | SC1-SC8 cover all 5 from brief and expand |
| Constraints (5) | TC1-TC8 cover all 5 and expand |

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| CB.1 | Minor | The product brief mentions "ROS2" compatibility in the architecture diagram (line 37 of brief: "LeRobot, ROS2, Custom Policies, Teleop"). The PRD makes no mention of ROS2 anywhere. If ROS2 is intentionally out of scope, this should be stated explicitly in the PRD constraints. | Product brief line 37; PRD has no mention |

**Recommended fix for CB.1:** Add a note under Technical Constraints: "TC9: ROS2 integration is out of scope for v1.0. The architecture allows future ROS2 bridging but v1.0 targets LeRobot only."

---

## Cross-Reference: PRD vs Architecture

**Result: PASS**

All FRs are architecturally feasible based on the architecture document:

| FR Group | Architecture Component | Feasibility |
|----------|----------------------|-------------|
| FR1-FR6 (detection) | HAL DeviceManager + pyudev + udev rules | Feasible, detailed design exists |
| FR7-FR11 (profiles) | Robot Profile System + YAML + Pydantic | Feasible, schema defined |
| FR12-FR14 (calibration) | Profile system + JSON storage | Feasible, storage paths defined |
| FR15-FR18 (teleop) | CLI `robotos teleop` + HAL sync_read/write | Feasible, latency budget addressed |
| FR19-FR23 (diagnostics) | Diagnostic Framework + 11 health checks | Feasible, directly maps to existing code |
| FR24-FR27 (data collection) | AI Integration Layer + LeRobot bridge | Feasible, pipeline designed |
| FR28-FR32 (OS/boot) | OS Layer + live-build + GRUB | Feasible, build toolchain specified |
| FR33-FR36 (dashboard) | UI Layer (TUI via textual, Web via FastAPI) | Feasible, technology choices appropriate |
| FR37-FR38 (AI assist) | AI Integration Layer + Claude Code context | Feasible, no API needed (file-based) |
| FR39-FR41 (extensibility) | HAL plugin interface + ServoProtocol ABC | Feasible, ABC defined with 12 methods |

The only architecture concern (NFR18 method count vs actual interface) is captured under Check 2 above.

---

## Issue Summary

| ID | Severity | Check | Summary |
|----|----------|-------|---------|
| 5.1 | **Major** | MVP Scope | FR3 (profile matching) missing from MVP includes but implicitly required |
| 5.2 | **Major** | MVP Scope | FR4 (camera detection) in MVP description but missing from FR list |
| 6.1 | **Major** | Contradiction | NFR21 (no world-writable ports) contradicts FR6 and architecture udev rules (MODE=0666) |
| 6.2 | **Major** | Contradiction | Growth phase claims to introduce TUI but MVP already includes TUI launcher |
| 9.1 | **Major** | Dependencies | No FR dependency chain documented; critical path is implicit |
| 2.1 | Minor | NFR Measurability | NFR18 method count (10) is less than architecture's actual count (12) |
| 3.1 | Minor | Success Metrics | SC6 (GitHub stars) is a vanity metric outside engineering control |
| 7.1 | Minor | Vague Language | FR14 uses "appears stale" without defined threshold |
| 10.1 | Minor | Orphaned FR | FR41 (plugin loading) lacks a dedicated user journey |
| CB.1 | Minor | Brief Alignment | ROS2 mentioned in brief but not addressed in PRD scope |

**5 Major issues, 5 Minor issues.**

All Major issues are fixable without restructuring the document. Recommended to resolve all Major issues before starting story decomposition.
