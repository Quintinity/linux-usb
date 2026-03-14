# armOS USB -- Sprint Plan

**Author:** Bob (Scrum Master Agent)
**Date:** 2026-03-15
**Scope:** MVP (v0.1) -- Epics 1-9
**Sprint Duration:** 2 weeks each

---

## Sprint Goal

Build the `armos` Python package with a hardware abstraction layer, robot profiles, diagnostics, telemetry, calibration, teleoperation, a TUI launcher, a pre-built USB image, and AI-assisted data collection -- delivering a complete MVP for the SO-101 robot on x86 hardware.

---

## Sprint Breakdown

### Sprint 0: Tooling and Environment Setup (Week 0-1)

**Goal:** Establish CI/CD, test infrastructure, MockServoProtocol, code quality tooling, and hardware inventory before any feature work begins.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 0.1 CI/CD, Test Fixtures, MockServoProtocol, Code Quality Tooling | M | None |
| 2 | 0.2 Hardware Inventory and Test Environment Setup | S | None |

**Capacity:** 2 stories (1M + 1S). Total weight: 4. One-week sprint.

**Demo:** Green CI pipeline, `pytest` runs with MockServoProtocol, hardware inventory documented.

---

### Sprint 1: Package Skeleton + CLI Foundation (Weeks 1-2)

**Goal:** Establish the `armos` Python package, CLI entry point, utility modules, and AI context -- the foundation everything else builds on.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 1.1 Initialize Python Package with pyproject.toml | S | None |
| 2 | 1.2 CLI Command Group Structure | S | 1.1 |
| 3 | 1.3 Utility Module -- Serial Helpers | S | 1.1 |
| 4 | 1.4 Utility Module -- XDG Config Paths | S | 1.1 |
| 5 | 1.5 Migrate CLAUDE.md and AI Context Files | S | 1.2 |

**Capacity:** 5 stories, all size S. Total weight: 5. Light sprint by design -- establishes conventions and project structure that every subsequent sprint depends on.

**Demo:** `armos --help` shows all command stubs, `pip install -e .` works.

**Notes:**
- Stories 1.2, 1.3, and 1.4 can run in parallel after 1.1 completes.
- Story 1.5 requires 1.2 (needs the CLI command names to document).
- Exit criteria: `pip install -e .` works, `armos --help` shows all command stubs.

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

**Demo:** `armos detect` finds CH340 adapters and servos on real hardware.

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
| 5 | 3.5 Camera Auto-Detection and CameraManager | M | 1.3 |

**Capacity:** 5 stories (2S + 3M). Total weight: 11. Moderate sprint.

**Demo:** `armos calibrate` walks through joint homing, calibration data persists across restarts.

**Notes:**
- 3.1 depends on 1.4 (XDG paths for profile storage locations).
- 3.3 depends on 2.1 (needs ServoProtocol for reading current positions during calibration recall).
- 3.5 (Camera auto-detection) runs in parallel, depends only on 1.3.
- Sprint 2 and Sprint 3 could overlap if capacity allows: 3.1 only needs 1.1 + 1.4, not Epic 2.

---

### Sprint 4a: Diagnostic Framework + Telemetry Core (Weeks 7-8)

**Goal:** Build the diagnostic and telemetry frameworks, migrate read-only diagnostic checks, and spike the live-build ISO.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 4.1 DiagnosticRunner and HealthCheck Interface | M | 2.1, 3.1 |
| 2 | 5.1 TelemetryStream with Pluggable Backends | L | 2.1, 3.1 |
| 3 | 4.3 Diagnostic Output Reporters | M | 4.1 |
| 4 | 5.2 CSV Logging Backend | S | 5.1 |
| 5 | 8.1a Live-Build Spike -- Minimal Bootable ISO | M | 1.1 |

**Capacity:** 5 stories (1S + 3M + 1L). Total weight: 15.

**Demo:** `armos diagnose` framework runs with reporters, telemetry stream produces data, minimal ISO boots in QEMU.

**Notes:**
- 4.1 and 5.1 can start in parallel (both depend on 2.1 + 3.1, neither depends on the other).
- 8.1a is the live-build spike -- time-boxed to 2-3 days. De-risks the full ISO build in Sprint 6.
- 4.3 and 5.2 run after their parents complete.

---

### Sprint 4b: Active Diagnostics + Fault Detection (Weeks 9-10)

**Goal:** Complete diagnostic migration, add fault detection, and exercise command.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 5.3 Fault Detection and Alert System | M | 5.1, 3.1 |
| 2 | 4.4 Exercise Command Migration | M | 2.1, 3.1, 3.3 |
| 3 | 4.2a Migrate Read-Only Diagnostic Checks | L | 4.1, 2.1, 2.2, 2.3, 3.1, 3.3 |
| 4 | 4.2b Migrate Active Diagnostic Checks | L | 4.2a |

**Capacity:** 4 stories (2M + 2L). Total weight: 16.

**Demo:** `armos diagnose` runs all 11 checks on real hardware, fault alerts fire on simulated issues.

**Notes:**
- 5.3 and 4.4 can start in parallel at sprint start.
- 4.2a (read-only checks) can start immediately; 4.2b (active checks) starts after 4.2a completes.
- If 4.2b overflows, it can slip without blocking the teleop critical path.

---

### Sprint 5: Calibration + Teleop CLI (Weeks 11-12)

**Goal:** Deliver the two primary user-facing commands: interactive calibration and leader-follower teleoperation.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 6.4 Hardware Detection Command | M | 2.1, 1.3 |
| 2 | 6.1 Interactive Calibration Command | M | 2.1, 3.1, 3.3 |
| 3 | 6.2 Leader-Follower Teleoperation Command | L | 2.1, 2.4, 3.1, 3.3, 5.1, 5.3 |
| 4 | 6.3 Teleop Monitor Overlay | M | 6.2, 5.1 |

**Capacity:** 4 stories (3M + 1L). Total weight: 14.

**Demo:** `armos teleop` -- move leader arm, follower mirrors. First full end-to-end demo.

**Notes:**
- 6.4 and 6.1 can start in parallel.
- 6.2 is the critical path item -- it depends on the telemetry stream (5.1) and fault detection (5.3) from Sprint 4b.
- 6.2 includes the teleop watchdog (FR42) -- disables torque if control loop stalls >500ms.
- 6.3 depends on 6.2 being at least partially complete (needs the teleop loop to exist).
- This sprint delivers the first end-to-end user workflow: detect -> calibrate -> teleop.

---

### Sprint 6a: TUI + Data Collection (Weeks 13-14)

**Goal:** Build the TUI dashboard, first-run wizard, and LeRobot data collection pipeline.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 7.1 TUI Application Shell | M | 6.4, 3.1 |
| 2 | 9.2 LeRobot Bridge -- Profile to Config Translation | M | 3.1, 3.3, 2.1 |
| 3 | 7.2 Live Telemetry Panel | M | 7.1, 5.1 |
| 4 | 7.3 Workflow Launcher Panel | L | 7.1, 7.2, 6.1, 6.2, 4.2a |
| 5 | 9.3 Data Collection Command | L | 9.2, 6.2, 5.1 |
| 6 | 7.0 First-Run Setup Wizard | L | 7.1, 6.1, 6.4 |

**Capacity:** 6 stories (3M + 3L). Total weight: 24. Heavy sprint but 7.3/9.3 and 7.0 can overlap.

**Demo:** TUI dashboard with live telemetry, first-run wizard guides through setup, `armos record` captures data.

**Notes:**
- 7.1 and 9.2 can start in parallel at sprint start.
- 7.0 (first-run wizard) depends on 7.1 and 6.1 -- can start mid-sprint.
- 9.3 depends on 9.2 and the teleop command (6.2) from Sprint 5.

---

### Sprint 6b: USB Image + Polish (Weeks 15-16)

**Goal:** Build the full bootable USB image, add boot splash, and validate on hardware.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 8.1b Full Live-Build with All Packages | L | 8.1a, all previous epics |
| 2 | 8.2 System Configuration Baked Into Image | L | 8.1b |
| 3 | 8.3 Windows Flash Script Update | M | 8.1b |
| 4 | 8.5 Plymouth Boot Splash | S | 8.1b |
| 5 | 9.1 Claude Code Context Pre-seeding | S | 1.5, 8.1b |

**Capacity:** 5 stories (2S + 1M + 2L). Total weight: 16.

**Demo:** Bootable ISO with branded splash, all armos commands work from USB, flash script tested on Windows.

**Notes:**
- 8.1b is the critical path item -- builds on the spike from Sprint 4a (8.1a).
- 8.2, 8.3, 8.5, and 9.1 all depend on 8.1b and can run in parallel after it completes.

---

### Sprint 7: Hardware Testing + Release (Weeks 17-18)

**Goal:** Validate the ISO on multiple hardware platforms, fix remaining issues, and ship the MVP.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 8.4 Hardware Compatibility Testing | L | 8.1b, 8.2 |
| 2 | Bug fixes and polish | -- | All |
| 3 | MVP release preparation | -- | All |

**Capacity:** 1 story + buffer. Total weight: 5+.

**Demo:** ISO boots and works on 5+ x86 machines. MVP shipped.

---

## Backlog (Post-MVP)

Epic 10 stories are in the backlog and will be planned after MVP ships:

| Story | Size | Key Dependencies |
|-------|------|-----------------|
| 10.1 DeviceManager -- pyudev Hotplug and Profile Matching | L | 2.1, 3.1, 6.4 |
| 10.2 Plugin Architecture for Servo Protocols | L | 2.1 |
| 10.3 Profile Creation Wizard and Export/Import | L | 3.1, 3.2 |
| 10.4 Configurable Teleop, Episode Review, Camera Feeds | L | 6.2, 9.3, 6.4 |
| 10.5 USB Image Cloning for Fleet Deployment | M | 8.1b, 8.2 |
| 10.6 AI Troubleshooting with Live System State | M | 9.1, 4.3, 5.3 |

---

## Critical Path

The longest dependency chain through the MVP:

```
0.1 -> 1.1 -> 1.3 -> 2.1 -> 5.1 -> 6.2 -> 7.3 -> 8.1b -> 8.4
 M      S      S      L      L      L      L       L       L
```

Total weight on critical path: 30. Any delay on this chain delays the MVP.

**Secondary critical path:**
```
1.1 -> 1.4 -> 3.1 -> 3.3 -> 4.2a -> 4.2b
```

The 4.2a/4.2b split (migrate diagnostic checks) reduces risk -- 4.2a can ship while 4.2b is still in progress.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **ServoProtocol ABC needs redesign after downstream integration** | Medium | High | Review ABC interface against Epic 3-6 acceptance criteria before declaring 2.1 done. Write integration tests early. |
| **Stories 4.2a/4.2b (migrate diagnostics) take longer than estimated** | Medium | Medium | Split into read-only (4.2a) and active (4.2b) checks reduces risk. 4.2b can overflow without blocking teleop critical path. |
| **Story 8.1b (live-build ISO) is blocked by unforeseen OS packaging issues** | Medium | High | De-risked by 8.1a spike in Sprint 4a. Do not wait until Sprint 6b to discover packaging problems. |
| **Hardware availability for testing** | Low | Medium | SO-101 hardware is already available on the Surface Pro 7. Ensure USB cameras are sourced by Sprint 5. |
| **Sprint 6a overload (24 weight points)** | Medium | Medium | Split into 6a (TUI + data) and 6b (USB image). 8.1a spike in Sprint 4a de-risks the build. |
| **LeRobot v0.5.0 API changes** | Low | High | Pin to v0.5.0. The bridge layer (9.2) isolates LeRobot from the rest of the system. |
| **Sprint 4a/4b balance** | Low | Low | Split into 4a (15 points) and 4b (16 points) keeps both under capacity. 4.2b can overflow if needed. |

---

## Definition of Done -- MVP (v0.1)

The MVP is complete when ALL of the following are true:

1. **Package installable:** `pip install armos` installs cleanly and `armos --version` prints `0.1.0`.
2. **Hardware detection works:** `armos detect` identifies CH340 adapters and USB cameras on a Surface Pro 7.
3. **SO-101 profile ships:** `armos profile list` shows the SO-101 profile with correct joint/servo configuration.
4. **Calibration persists:** Calibrate both arms, reboot, and calibration is automatically recalled.
5. **Teleoperation runs:** `armos teleop` achieves leader-follower mirroring at 60Hz with safety stops on threshold breach.
6. **Diagnostics pass:** `armos diagnose` runs all 11 checks and produces colored terminal output, JSON, and CSV.
7. **Telemetry streams:** `armos monitor` displays live per-servo data at 10Hz with fault alerts.
8. **TUI launches:** `armos tui` shows hardware status, telemetry, and launches workflows via keyboard shortcuts.
9. **Data collection works:** `armos record` captures LeRobot-compatible datasets with servo + camera data.
10. **USB image boots:** The ISO boots on the Surface Pro 7 within 90 seconds, all armos commands work without internet.
11. **Flash script works:** `flash.ps1` writes the ISO to a USB drive from Windows.
12. **Compatibility validated:** ISO tested on 5+ x86 models with 80%+ success rate documented.
13. **Docstrings:** All public classes and methods have Google-style docstrings. All CLI commands have help strings.
14. **Tests:** Every story ships with automated tests covering its core acceptance criteria. CI pipeline is green.

---

## Summary

| Sprint | Weeks | Epics | Stories | Weight | Theme | Demo |
|--------|-------|-------|---------|--------|-------|------|
| 0 | 0-1 | 0 | 2 | 4 | Tooling + environment | Green CI, hardware matrix |
| 1 | 1-2 | 1 | 5 | 5 | Package foundation | `armos --help` works |
| 2 | 3-4 | 2 | 4 | 14 | Hardware abstraction | `armos detect` finds servos |
| 3 | 5-6 | 3 | 5 | 11 | Robot profiles + cameras | `armos calibrate` works |
| 4a | 7-8 | 4, 5, 8 | 5 | 15 | Diag framework + live-build spike | Diagnostics framework + ISO boots in QEMU |
| 4b | 9-10 | 4, 5 | 4 | 16 | Active diagnostics + faults | `armos diagnose` runs all checks |
| 5 | 11-12 | 6 | 4 | 14 | Calibration + teleop | `armos teleop` -- first full demo |
| 6a | 13-14 | 7, 9 | 6 | 24 | TUI + data collection | TUI with first-run wizard |
| 6b | 15-16 | 8, 9 | 5 | 16 | USB image + polish | Bootable ISO with splash |
| 7 | 17-18 | 8 | 1+ | 5+ | Hardware testing + release | MVP shipped |
| Backlog | -- | 10 | 6 | 18 | Growth phase | -- |
| **Total** | **15-18 weeks** | **10** | **47+** | **122+** | | |

**Estimated MVP delivery:** 15-18 weeks (Sprint 0 + 7 two-week sprints + buffer). This is more honest than the original 12-week estimate and accounts for Sprint 4 split, Sprint 6 split, and a dedicated hardware testing sprint.

---

_Sprint plan for armOS USB MVP -- generated by Bob (Scrum Master Agent)._
