# RobotOS USB -- Sprint Plan

**Author:** Bob (Scrum Master Agent)
**Date:** 2026-03-15
**Scope:** MVP (v0.1) -- Epics 1-9
**Sprint Duration:** 2 weeks each

---

## Sprint Goal

Build the `robotos` Python package with a hardware abstraction layer, robot profiles, diagnostics, telemetry, calibration, teleoperation, a TUI launcher, a pre-built USB image, and AI-assisted data collection -- delivering a complete MVP for the SO-101 robot on x86 hardware.

---

## Sprint Breakdown

### Sprint 1: Package Skeleton + CLI Foundation (Weeks 1-2)

**Goal:** Establish the `robotos` Python package, CLI entry point, utility modules, and AI context -- the foundation everything else builds on.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 1.1 Initialize Python Package with pyproject.toml | S | None |
| 2 | 1.2 CLI Command Group Structure | S | 1.1 |
| 3 | 1.3 Utility Module -- Serial Helpers | S | 1.1 |
| 4 | 1.4 Utility Module -- XDG Config Paths | S | 1.1 |
| 5 | 1.5 Migrate CLAUDE.md and AI Context Files | S | 1.2 |

**Capacity:** 5 stories, all size S. Total weight: 5. Light sprint by design -- establishes conventions and project structure that every subsequent sprint depends on.

**Notes:**
- Stories 1.2, 1.3, and 1.4 can run in parallel after 1.1 completes.
- Story 1.5 requires 1.2 (needs the CLI command names to document).
- Exit criteria: `pip install -e .` works, `robotos --help` shows all command stubs.

---

### Sprint 2: HAL + Feetech Driver (Weeks 3-4)

**Goal:** Implement the servo protocol abstraction and the Feetech STS3215 driver, including bus scanning, protection settings, and retry logic.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 2.1 ServoProtocol ABC and FeetechPlugin | L | 1.1, 1.3 |
| 2 | 2.2 Servo Bus Scan | M | 2.1 |
| 3 | 2.3 Protection Settings Read/Write | M | 2.1 |
| 4 | 2.4 Resilient Communication with Retry and Port Flush | M | 2.1 |

**Capacity:** 4 stories (1L + 3M). Total weight: 14. Heaviest foundational sprint -- 2.1 is the largest single story and the critical path item.

**Notes:**
- Stories 2.2, 2.3, and 2.4 can run in parallel after 2.1 completes.
- 2.1 wraps LeRobot's `FeetechMotorsBus` so it must be validated against real hardware.
- Risk: If the ABC design needs iteration after downstream consumers (Epic 3, 4) start, refactoring cost is high. Mitigate by reviewing the ABC interface with Epic 3/4 acceptance criteria before declaring 2.1 done.

---

### Sprint 3: Robot Profiles + SO-101 (Weeks 5-6)

**Goal:** Build the YAML profile system with Pydantic validation, ship the SO-101 profile, and implement calibration persistence.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 3.1 Profile Schema and Loader | M | 1.1, 1.4 |
| 2 | 3.2 Built-in SO-101 Profile | S | 3.1 |
| 3 | 3.3 Calibration Storage and Recall | M | 3.1, 2.1 |
| 4 | 3.4 Calibration Validation | S | 3.3 |

**Capacity:** 4 stories (2S + 2M). Total weight: 8. Moderate sprint.

**Notes:**
- 3.1 depends on 1.4 (XDG paths for profile storage locations).
- 3.3 depends on 2.1 (needs ServoProtocol for reading current positions during calibration recall).
- Sprint 2 and Sprint 3 could overlap if capacity allows: 3.1 only needs 1.1 + 1.4, not Epic 2.

---

### Sprint 4: Diagnostic Framework + Telemetry (Weeks 7-8)

**Goal:** Decompose the monolithic diagnostic script into a modular framework and build the reusable telemetry streaming library.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 4.1 DiagnosticRunner and HealthCheck Interface | M | 2.1, 3.1 |
| 2 | 5.1 TelemetryStream with Pluggable Backends | L | 2.1, 3.1 |
| 3 | 4.3 Diagnostic Output Reporters | M | 4.1 |
| 4 | 5.2 CSV Logging Backend | S | 5.1 |
| 5 | 5.3 Fault Detection and Alert System | M | 5.1, 3.1 |
| 6 | 4.4 Exercise Command Migration | M | 2.1, 3.1, 3.3 |
| 7 | 4.2 Migrate Existing Diagnostic Checks | XL | 4.1, 2.1, 2.2, 2.3, 3.1, 3.3 |

**Capacity:** 7 stories (1S + 4M + 1L + 1XL). Total weight: 24. Heaviest sprint -- consider splitting if velocity is lower than expected.

**Notes:**
- 4.1 and 5.1 can start in parallel (both depend on 2.1 + 3.1, neither depends on the other).
- 4.2 (XL) is the largest single story in the MVP. It migrates 11 diagnostic phases. Consider splitting into sub-tasks if needed.
- 4.3, 5.2, and 5.3 can run in parallel once their respective parent stories complete.
- If this sprint overflows, 4.2 can slip to Sprint 5 without blocking the critical path (Sprint 5 needs 5.1 and 5.3, not 4.2 directly).

**Overflow plan:** Move 4.2 (Migrate Existing Diagnostic Checks) to Sprint 5 if needed. It is not on the critical path for Sprint 5's teleop work.

---

### Sprint 5: Calibration + Teleop CLI (Weeks 9-10)

**Goal:** Deliver the two primary user-facing commands: interactive calibration and leader-follower teleoperation.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 6.4 Hardware Detection Command | M | 2.1, 1.3 |
| 2 | 6.1 Interactive Calibration Command | M | 2.1, 3.1, 3.3 |
| 3 | 6.2 Leader-Follower Teleoperation Command | L | 2.1, 2.4, 3.1, 3.3, 5.1, 5.3 |
| 4 | 6.3 Teleop Monitor Overlay | M | 6.2, 5.1 |

**Capacity:** 4 stories (3M + 1L). Total weight: 14.

**Notes:**
- 6.4 and 6.1 can start in parallel.
- 6.2 is the critical path item -- it depends on the telemetry stream (5.1) and fault detection (5.3) from Sprint 4.
- 6.3 depends on 6.2 being at least partially complete (needs the teleop loop to exist).
- This sprint delivers the first end-to-end user workflow: detect -> calibrate -> teleop.

---

### Sprint 6: TUI + USB Image + AI Integration (Weeks 11-12)

**Goal:** Build the TUI dashboard, create the bootable USB image, and integrate LeRobot data collection. Ship the MVP.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 7.1 TUI Application Shell | M | 6.4, 3.1 |
| 2 | 9.1 Claude Code Context Pre-seeding | S | 1.5, 8.1 |
| 3 | 9.2 LeRobot Bridge -- Profile to Config Translation | M | 3.1, 3.3, 2.1 |
| 4 | 7.2 Live Telemetry Panel | M | 7.1, 5.1 |
| 5 | 8.1 live-build Configuration and ISO Build Script | XL | 1.1, 2.1, 3.2, 4.2, 5.1, 6.1, 6.2, 7.1 |
| 6 | 7.3 Workflow Launcher Panel | L | 7.1, 7.2, 6.1, 6.2, 4.2 |
| 7 | 9.3 Data Collection Command | L | 9.2, 6.2, 5.1 |
| 8 | 8.2 System Configuration Baked Into Image | L | 8.1 |
| 9 | 8.3 Windows Flash Script Update | M | 8.1 |
| 10 | 8.4 Hardware Compatibility Testing | L | 8.1, 8.2 |

**Capacity:** 10 stories (1S + 4M + 3L + 1XL). Total weight: 33. This is the largest sprint and may need to extend to 3 weeks or split into 6a/6b.

**Notes:**
- 7.1, 9.1, and 9.2 can start in parallel at sprint start.
- 8.1 (XL) is the second-largest story in the MVP and depends on nearly everything. It should start as soon as Sprints 1-5 artifacts are stable.
- 9.1 depends on 8.1 because the context files need to describe the final USB image environment. However, the content can be drafted early and finalized after 8.1.
- 8.4 (hardware testing) is the final gate before MVP release.

**Recommended split if needed:**
- **Sprint 6a (Weeks 11-12):** 7.1, 7.2, 7.3, 9.2, 9.3 (TUI + data collection)
- **Sprint 6b (Weeks 13-14):** 8.1, 8.2, 8.3, 8.4, 9.1 (USB image + AI context)

---

## Backlog (Post-MVP)

Epic 10 stories are in the backlog and will be planned after MVP ships:

| Story | Size | Key Dependencies |
|-------|------|-----------------|
| 10.1 DeviceManager -- pyudev Hotplug and Profile Matching | L | 2.1, 3.1, 6.4 |
| 10.2 Plugin Architecture for Servo Protocols | L | 2.1 |
| 10.3 Profile Creation Wizard and Export/Import | L | 3.1, 3.2 |
| 10.4 Configurable Teleop, Episode Review, Camera Feeds | L | 6.2, 9.3, 6.4 |
| 10.5 USB Image Cloning for Fleet Deployment | M | 8.1, 8.2 |
| 10.6 AI Troubleshooting with Live System State | M | 9.1, 4.3, 5.3 |

---

## Critical Path

The longest dependency chain through the MVP:

```
1.1 -> 1.3 -> 2.1 -> 5.1 -> 6.2 -> 7.3 -> 8.1 -> 8.4
 S      S      L      L      L      L     XL      L
```

Total weight on critical path: 30 (out of 110 total). Any delay on this chain delays the MVP.

**Secondary critical path:**
```
1.1 -> 1.4 -> 3.1 -> 3.3 -> 4.2 (XL)
```

The 4.2 story (migrate 11 diagnostic checks) is the single largest story and the biggest schedule risk within the MVP.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **ServoProtocol ABC needs redesign after downstream integration** | Medium | High | Review ABC interface against Epic 3-6 acceptance criteria before declaring 2.1 done. Write integration tests early. |
| **Story 4.2 (migrate diagnostics) takes longer than estimated** | High | Medium | It is XL and touches 11 distinct diagnostic phases. Allow overflow into Sprint 5. Not on teleop critical path. |
| **Story 8.1 (live-build ISO) is blocked by unforeseen OS packaging issues** | Medium | High | Prototype the live-build config in Sprint 4 as a spike. Do not wait until Sprint 6 to discover packaging problems. |
| **Hardware availability for testing** | Low | Medium | SO-101 hardware is already available on the Surface Pro 7. Ensure USB cameras are sourced by Sprint 5. |
| **Sprint 6 overload (33 weight points)** | High | Medium | Pre-plan the 6a/6b split. Start 8.1 spike work during Sprint 5. |
| **LeRobot v0.5.0 API changes** | Low | High | Pin to v0.5.0. The bridge layer (9.2) isolates LeRobot from the rest of the system. |
| **Sprint 4 overload (24 weight points)** | Medium | Medium | 4.2 can overflow to Sprint 5 without blocking critical path. |

---

## Definition of Done -- MVP (v0.1)

The MVP is complete when ALL of the following are true:

1. **Package installable:** `pip install robotos` installs cleanly and `robotos --version` prints `0.1.0`.
2. **Hardware detection works:** `robotos detect` identifies CH340 adapters and USB cameras on a Surface Pro 7.
3. **SO-101 profile ships:** `robotos profile list` shows the SO-101 profile with correct joint/servo configuration.
4. **Calibration persists:** Calibrate both arms, reboot, and calibration is automatically recalled.
5. **Teleoperation runs:** `robotos teleop` achieves leader-follower mirroring at 60Hz with safety stops on threshold breach.
6. **Diagnostics pass:** `robotos diagnose` runs all 11 checks and produces colored terminal output, JSON, and CSV.
7. **Telemetry streams:** `robotos monitor` displays live per-servo data at 10Hz with fault alerts.
8. **TUI launches:** `robotos tui` shows hardware status, telemetry, and launches workflows via keyboard shortcuts.
9. **Data collection works:** `robotos record` captures LeRobot-compatible datasets with servo + camera data.
10. **USB image boots:** The ISO boots on the Surface Pro 7 within 90 seconds, all robotos commands work without internet.
11. **Flash script works:** `flash.ps1` writes the ISO to a USB drive from Windows.
12. **Compatibility validated:** ISO tested on 5+ x86 models with 80%+ success rate documented.

---

## Summary

| Sprint | Weeks | Epics | Stories | Weight | Theme |
|--------|-------|-------|---------|--------|-------|
| 1 | 1-2 | 1 | 5 | 5 | Package foundation |
| 2 | 3-4 | 2 | 4 | 14 | Hardware abstraction |
| 3 | 5-6 | 3 | 4 | 8 | Robot profiles |
| 4 | 7-8 | 4, 5 | 7 | 24 | Diagnostics + telemetry |
| 5 | 9-10 | 6 | 4 | 14 | Calibration + teleop |
| 6 | 11-12+ | 7, 8, 9 | 10 | 33 | TUI + USB image + AI |
| Backlog | -- | 10 | 6 | 18 | Growth phase |
| **Total** | **12+ weeks** | **10** | **40** | **116** | |

**Estimated MVP delivery:** 12-14 weeks from sprint 1 start, assuming Sprint 6 extends to 3 weeks.

---

_Sprint plan for RobotOS USB MVP -- generated by Bob (Scrum Master Agent)._
