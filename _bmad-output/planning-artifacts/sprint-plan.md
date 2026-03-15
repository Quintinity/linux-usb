# armOS USB -- Sprint Plan

**Author:** Bob (Scrum Master Agent)
**Date:** 2026-03-15
**Status:** Consolidated v2.0
**Scope:** MVP (v0.1) Sprints 0-7, Launch Sprint 8, Post-Launch Sprint 9
**Sprint Duration:** 2 weeks each (Sprint 0 is 1 week)

---

## Sprint Goal

Build the `armos` Python package with a hardware abstraction layer, robot profiles, diagnostics, telemetry, calibration, teleoperation, a TUI launcher with demo mode, a pre-built USB image with CI/CD pipeline, and AI-assisted data collection -- delivering a complete MVP for the SO-101 robot on x86 hardware. Then execute a public launch and stabilize based on community feedback.

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

**Content (build in public):**
- Week 1: "Why I'm building an OS for robot arms" (dev log #1) -- Blog, X
- Week 2: "The brltty serial port bug that wastes everyone's time" -- Blog, Dev.to, HN

---

### Sprint 2: HAL + Feetech Driver (Weeks 3-4)

**Goal:** Implement the servo protocol abstraction and the Feetech STS3215 driver, including bus scanning, protection settings, retry logic, and the conformance test suite.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 2.1 ServoProtocol ABC and FeetechPlugin | L | 1.1, 1.3 |
| 2 | 2.2 Servo Bus Scan | M | 2.1 |
| 3 | 2.3 Protection Settings Read/Write | M | 2.1 |
| 4 | 2.4 Resilient Communication with Retry and Port Flush | M | 2.1 |
| 5 | 2.5 ServoProtocol Conformance Test Suite | M | 2.1, 0.1 |

**Capacity:** 5 stories (1L + 4M). Total weight: 17. Heavy foundational sprint -- 2.1 is the largest single story and the critical path item.

**Demo:** `armos detect` finds CH340 adapters and servos on real hardware. Conformance tests pass against MockServoProtocol.

**Notes:**
- Stories 2.2, 2.3, 2.4, and 2.5 can run in parallel after 2.1 completes.
- 2.1 wraps LeRobot's `FeetechMotorsBus` so it must be validated against real hardware.
- Risk: If the ABC design needs iteration after downstream consumers (Epic 3, 4) start, refactoring cost is high. Mitigate by reviewing the ABC interface with Epic 3/4 acceptance criteria before declaring 2.1 done.

**Content:**
- Week 3: "Building a servo protocol abstraction layer" (dev log #2) -- Blog, X
- Week 4: "Power supply problems you'll hit with STS3215 servos" -- Blog, Dev.to

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
- **Spike S1** (HuggingFace Hub API for Profiles, 2 days) runs during this sprint to inform Growth-phase profile sharing design.

**Content:**
- Week 5: "How to tune overload protection on Feetech servos" -- Blog, YouTube
- Week 6: "YAML robot profiles: the configuration layer nobody built" (dev log #3) -- Blog, X

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
- 8.1a is the live-build spike -- time-boxed to 2-3 days. De-risks the full ISO build in Sprint 6b.
- 4.3 and 5.2 run after their parents complete.
- **Spike S2** (Foxglove MCAP Telemetry Format, 1 day) runs during this sprint.

**Content:**
- Week 7: "Diagnosing servo communication failures (sync_read explained)" -- Blog, YouTube
- Week 8: "Building the diagnostic suite" (dev log #4) -- Blog, X

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
- **Spike S3** (Cloud Training Pipeline Prototype, 3 days) can begin during this sprint.

**Partnership warm-up begins:**
- Submit upstream patches to LeRobot (Sprint 5-6)

**Content:**
- Week 9: 30-second teaser: "armOS first teleop" -- X, YouTube Shorts
- Week 10: "Leader-follower teleoperation from scratch" (tutorial) -- YouTube, Blog

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
- The telemetry opt-in prompt is built into 7.0 (first-run wizard).
- The upload dataset command stub is built into 9.3.

**Partnership:**
- Open a discussion in LeRobot GitHub: "We're building a bootable USB for LeRobot."

**Content:**
- Week 11: "Building a TUI for robot control with Textual" (dev log #5) -- Blog, X
- Week 12: "The 90-second demo video" (pre-launch teaser) -- YouTube, X

---

### Sprint 6b: USB Image + Polish (Weeks 15-16)

**Goal:** Build the full bootable USB image with CI/CD pipeline, add boot splash, distribution pipeline, and validate on hardware.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 8.1b Full Live-Build with All Packages | L | 8.1a, all previous epics |
| 2 | 8.2 System Configuration Baked Into Image | L | 8.1b |
| 3 | 8.3 Windows Flash Script Update | M | 8.1b |
| 4 | 8.5 Plymouth Boot Splash | S | 8.1b |
| 5 | 9.1 Claude Code Context Pre-seeding | S | 1.5, 8.1b |
| 6 | 8.9 ISO Version Metadata | S | 8.1b |

**Capacity:** 6 stories (3S + 1M + 2L). Total weight: 17.

**Demo:** Bootable ISO with branded splash, all armos commands work from USB, flash script tested on Windows.

**Notes:**
- 8.1b is the critical path item -- builds on the spike from Sprint 4a (8.1a).
- 8.2, 8.3, 8.5, 9.1, and 8.9 all depend on 8.1b and can run in parallel after it completes.
- **Spike S4** (ISO Distribution Strategy, 1 day) and **Spike S5** (OTA Update Mechanism, 2 days) run during this sprint.

**Content:**
- Week 13: "How to build a bootable Linux USB with live-build" -- Blog, Dev.to
- Week 14: "Testing armOS on 5 different laptops" (compatibility results) -- Blog, YouTube

---

### Sprint 7: Hardware Testing + CI/CD + Release (Weeks 17-18)

**Goal:** Validate the ISO on multiple hardware platforms, build the CI/CD pipeline for ISO builds, fix remaining issues, and ship the MVP.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 8.6 Dockerfile.build for Reproducible ISO Builds | M | 8.1b |
| 2 | 8.7 QEMU ISO Smoke Test | M | 8.1b |
| 3 | 8.8 ISO Distribution Pipeline | M | 8.6, 8.7 |
| 4 | 8.4 Hardware Compatibility Testing | L | 8.1b, 8.2 |
| 5 | Bug fixes and polish | -- | All |
| 6 | MVP release preparation | -- | All |

**Capacity:** 4 stories + buffer. Total weight: 14+.

**Demo:** ISO boots and works on 5+ x86 machines. CI pipeline builds and smoke-tests ISOs. MVP shipped.

**Notes:**
- 8.6 and 8.7 can run in parallel with 8.4.
- 8.8 depends on 8.6 and 8.7.
- Hardware compatibility testing runs throughout the sprint.
- The pre-launch checklist (see below) must be completed before Sprint 8.

**Content:**
- Week 15: "The complete armOS getting started guide" -- Blog, YouTube
- Week 16: Pre-launch announcement: "armOS launches next week" -- X, Discord, all channels

**Partnership:**
- Email the HuggingFace robotics team to propose co-marketing

---

### Sprint 8: Launch Preparation (Weeks 19-20)

**Goal:** Prepare and execute the public launch of armOS. By the end of this sprint, armOS is live on GitHub, announced on 3+ channels, and the demo video has been published.

| Order | Story | Size | Dependencies |
|-------|-------|------|--------------|
| 1 | 7.4 Demo Mode (Kiosk) | M | 6.2, 7.1, 3.2 |
| 2 | Demo video recording (3-5 takes, edit to 90 seconds) | -- | 7.4 |
| 3 | Launch blog post | -- | All |
| 4 | Final ISO build with demo mode included | -- | 7.4 |
| 5 | GitHub README finalized with embedded video | -- | Demo video |
| 6 | Discord server created and configured | -- | None |
| 7 | Alpha tester feedback incorporated | -- | All |

**Capacity:** 1 story (M) + launch execution tasks. Total weight: 3+.

#### Launch Sprint Day-by-Day

| Day | Activity | Deliverable |
|-----|----------|-------------|
| 1-2 | Demo mode implementation (Story 7.4) | `armos demo` working |
| 3 | Record demo video (3-5 takes, edit to 90 seconds) | YouTube-ready video |
| 4-5 | Write launch blog post | Published on blog/Medium/Dev.to |
| 6 | Final ISO build with demo mode included | v0.1.0 ISO on HuggingFace Hub |
| 7 | Create Discord server, configure channels and roles | Discord invite link |
| 8 | Write GitHub README with embedded video, download link | README.md finalized |
| 9 | Alpha tester feedback incorporated, final bug fixes | v0.1.1 if needed |
| 10 | **Launch day:** Post to LeRobot Discord, HN, r/robotics, X | Posts live |

#### Launch Day Checklist

- [ ] ISO download link verified (download and flash on a clean machine)
- [ ] Demo video uploaded to YouTube (unlisted until launch, then public)
- [ ] HN post draft ready: "Show HN: armOS -- Boot any laptop into a robot control station in 5 minutes"
- [ ] LeRobot Discord message ready (clear, concise, includes video link)
- [ ] r/robotics post ready
- [ ] Monitor all channels for 4 hours after posting -- respond to every comment
- [ ] Have a bug-fix ISO build pipeline ready (you will need it)

#### Launch Success Metrics

| Metric | Target | Stretch |
|--------|--------|---------|
| GitHub stars | 100 | 500 |
| ISO downloads | 50 | 200 |
| Discord members | 25 | 100 |
| Demo video views | 500 | 2,000 |
| Bug reports filed | 5+ (means people are using it) | -- |
| Alpha testers who complete full workflow | 5 | 15 |

**Content:**
- Week 17: **Launch blog post** + demo video -- Blog, HN, Reddit, Discord
- Week 18: "From unboxing to AI data collection in 10 minutes" (full tutorial) -- YouTube

**Partnership:**
- Send armOS USB stick to Seeed Studio partnerships team
- Send USB sticks to 5 robotics YouTubers

---

### Sprint 9: Post-Launch Stabilization (Weeks 21-22)

**Goal:** Respond to every user issue within 24 hours. Ship a patch release (v0.1.2) addressing the top 5 user-reported issues. Maintain community momentum.

#### Time Allocation

| Activity | Time | Notes |
|----------|------|-------|
| Bug triage and response | 40% | Every GitHub issue gets a response within 24 hours. Label, prioritize, assign. |
| Bug fixes and patch release | 30% | Fix the top 5 user-reported issues. Ship v0.1.2 by end of sprint. |
| Compatibility matrix expansion | 15% | Users will report boot results. Add to the matrix. Follow up on failures. |
| Community engagement | 15% | Respond on Discord. Retweet user posts. Feature "Show Your Setup" submissions. |

#### Triage Priority Rules

| Priority | Criteria | Response Time | Fix Time |
|----------|----------|---------------|----------|
| P0 | ISO does not boot on a Tier 1 machine | 4 hours | 48 hours |
| P0 | Data loss (calibration, recorded episodes) | 4 hours | 48 hours |
| P1 | Teleop does not work on detected hardware | 12 hours | 1 week |
| P1 | TUI crash or hang | 12 hours | 1 week |
| P2 | Cosmetic TUI issues, non-blocking errors | 24 hours | Next release |
| P3 | Feature requests | 48 hours | Backlog |

#### Expected User Reports (from Product Validation Research)

1. **Boot failures on specific hardware** -- BIOS settings, Secure Boot, USB controller quirks
2. **Servo communication intermittent failures** -- power supply issues on user's hardware
3. **Camera not detected** -- specific webcam models not supported by kernel
4. **Calibration confusion** -- users not understanding the homing procedure
5. **"It worked once but now it doesn't"** -- persistence/reboot issues

Prepare template responses for each of these categories before launch.

**Content:**
- Week 19: "Building a robotics lab with armOS" (educator guide) -- Blog
- Week 20: User spotlight: first community setup -- Blog, X

**Partnership:**
- Contact university robotics instructors for pilot program

---

## Pre-Launch Checklist

### Must Have (Blocks Launch)

- [ ] **ISO boots and works on 2+ laptop models** (Tier 1 testing complete)
- [ ] **Full workflow works end-to-end:** boot -> detect -> calibrate -> teleop -> record
- [ ] **Demo video recorded:** 90-second, uncut, USB-to-teleop (the business plan's "single most important marketing asset")
- [ ] **GitHub repo public** with compelling README (embedded demo video, feature list, download link)
- [ ] **Download link works** (ISO hosted on HuggingFace Hub with SHA256 checksum)
- [ ] **Quick-start guide:** 1-page PDF or README section: "1. Download. 2. Flash. 3. Boot. 4. Connect robot."
- [ ] **Known issues documented** (compatibility matrix, known limitations)
- [ ] **Discord server created** with channels: #general, #help, #show-your-setup, #bug-reports, #development
- [ ] **License file present** (Apache 2.0, per business plan)
- [ ] **No secrets in ISO** (API keys, passwords, personal paths -- scan before publishing)
- [ ] **flash.ps1 tested on Windows 10 and 11** (the primary audience's flash platform)

### Should Have (Improves Launch Quality)

- [ ] **Blog post:** "I spent 40 hours debugging a robot arm, so I built an OS" (HN-optimized title)
- [ ] **3 tutorial blog posts** per GTM strategy: SO-101 from scratch, existing LeRobot user, educator setup
- [ ] **GitHub Issues templates:** bug report, feature request, hardware compatibility report
- [ ] **Contributing guide** (CONTRIBUTING.md) with profile contribution workflow
- [ ] **Demo mode working** for live demos at meetups
- [ ] **Tested by 3+ external users** (alpha testers recruited from LeRobot Discord)

### Nice to Have (Can Follow Within 1 Week of Launch)

- [ ] YouTube channel with demo video
- [ ] X/Twitter account with launch thread
- [ ] Compatibility matrix with 5+ machines

---

## Backlog (Post-MVP)

### Growth Phase Sprints (Planned)

| Sprint | Weeks | Theme | Key Deliverables |
|--------|-------|-------|-----------------|
| 10 | 23-24 | Stabilization | Bug fixes from user feedback, compatibility matrix expansion, Tier 2 hardware testing |
| 11 | 25-26 | Telemetry + analytics | Anonymous usage telemetry (11.1), crash reporting, feedback pipeline |
| 12 | 27-28 | Cloud training alpha | Upload pipeline (11.2), GPU backend, first 10 training runs |
| 13 | 29-30 | Profile marketplace | Profile sharing via Hub (11.3), community profiles |
| 14 | 31-32 | Fleet + education | Fleet deployment (11.4), education pilot prep |

### Growth Phase Backlog (Unscheduled)

| Story | Size | Key Dependencies |
|-------|------|-----------------|
| 10.1 DeviceManager -- pyudev Hotplug and Profile Matching | L | 2.1, 3.1, 6.4 |
| 10.2 Plugin Architecture for Servo Protocols | L | 2.1 |
| 10.3 Profile Creation Wizard and Export/Import | L | 3.1, 3.2 |
| 10.4 Configurable Teleop, Episode Review, Camera Feeds | L | 6.2, 9.3, 6.4 |
| 10.5 USB Image Cloning for Fleet Deployment | M | 8.1b, 8.2 |
| 10.6 AI Troubleshooting with Live System State | M | 9.1, 4.3, 5.3 |
| 11.5 armos update Command | M | 8.2 |
| SDK1 Plugin Scaffolding Command | S | 10.2 |
| SDK3 Plugin Developer Guide | M | 10.2 |
| CI4 Self-Hosted Runner with Hardware | M | 8.6, 8.7 |

---

## Partnership Development Timeline

### Phase 0: Warm-Up (Sprints 5-8, Months 3-5)

| Action | When | Who to Contact | Purpose |
|--------|------|----------------|---------|
| Submit upstream patches to LeRobot | Sprint 5-6 | LeRobot maintainers (@cadene, @aliberts) | Build credibility. Show we contribute, not just consume. |
| Open a discussion in LeRobot GitHub | Sprint 6a | LeRobot community | "We're building a bootable USB for LeRobot. Here's a demo. Feedback?" |
| Email the HuggingFace robotics team | Sprint 7 | HuggingFace community team | Propose co-marketing. Offer to write a guest blog post. |

### Phase 1: First Contact (Sprints 8-11, Months 5-7)

| Action | When | Target Partner | Pitch |
|--------|------|----------------|-------|
| Send armOS USB stick to Seeed Studio | Week after launch | Seeed Studio partnerships team | "Your SO-101 customers spend hours on setup. This USB eliminates that. Want to bundle it?" |
| Send USB sticks to 5 robotics YouTubers | Sprint 9 | James Bruton, Skyentific, The Construct, etc. | "Here's a USB stick. Boot any laptop, plug in an SO-101, teleop in 5 minutes. Film it?" |
| Contact university robotics instructors | Sprint 10 | Georgia Tech ECE 4560, MIT, Stanford | "Run your next robotics lab on armOS. No student setup failures. Free pilot." |
| Reach out to Feetech | Sprint 11 | Feetech sales team | "We reduce your STS3215 support burden. Include our USB with your servo kits." |

### Phase 2: Formalize (Months 8-12)

| Action | When | Target | Outcome |
|--------|------|--------|---------|
| Seeed Studio partnership agreement | Month 8-9 | Seeed Studio | "Powered by armOS" on SO-101 kit listing |
| HuggingFace blog post | Month 9 | HuggingFace blog | Joint post: "The fastest way to start with LeRobot" |
| University pilot | Month 10 | Pilot university | 20-student course, one semester, feedback report |
| Intel outreach | Month 11 | Intel Developer Relations | "Robotics on Intel" co-marketing. OpenVINO integration. |
| ROSCon/PyCon talk submission | Month 9-10 | Conference organizers | "armOS: A Bootable USB for Robot Arms" (15-minute talk) |

---

## Content Calendar Summary

| Month | Sprint | Theme | Key Content |
|-------|--------|-------|-------------|
| 1 | 1-2 | Build in public | Dev logs, SEO blog posts on servo debugging |
| 2 | 3-4 | Technical deep dives | Overload protection tutorial (YouTube), diagnostic suite dev log |
| 3 | 5-6a | Demo content | First teleop teaser (YouTube Shorts), TUI dev log |
| 4 | 6b-7 | Pre-launch | live-build tutorial, compatibility results, getting started guide |
| 5 | 8 | **Launch** | Launch blog post + demo video (HN, Reddit, Discord) |
| 6 | 9-10 | Post-launch | Retrospective, contributor guide, roadmap post |

**Cadence:** 2 blog posts/month, 2 YouTube videos/month, weekly dev log posts. All content works standalone -- does not require the reader to know what armOS is.

---

## Technical Spikes

| ID | Title | Duration | Sprint | Status |
|----|-------|----------|--------|--------|
| S1 | HuggingFace Hub API for Profile Sharing | 2 days | Sprint 3 | Planned |
| S2 | Foxglove MCAP Telemetry Format | 1 day | Sprint 4a | Planned |
| S3 | Cloud Training Pipeline Prototype | 3 days | Sprint 5-6 | Planned |
| S4 | ISO Distribution Strategy | 1 day | Sprint 6b | Planned |
| S5 | OTA Update Mechanism for Live USB | 2 days | Sprint 6b | Planned |

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
| **Story 8.1b (live-build ISO) is blocked by unforeseen OS packaging issues** | Medium | High | De-risked by 8.1a spike in Sprint 4a. Do not wait until Sprint 6b to discover packaging problems. Fallback: ship installer script alongside base Ubuntu ISO. |
| **Hardware availability for testing** | Low | Medium | SO-101 hardware is already available on the Surface Pro 7. Ensure USB cameras are sourced by Sprint 5. Source 2-3 additional test machines by Sprint 6. |
| **Sprint 6a overload (24 weight points)** | Medium | Medium | Split into 6a (TUI + data) and 6b (USB image). 8.1a spike in Sprint 4a de-risks the build. |
| **LeRobot v0.5.0 API changes** | Low | High | Pin to v0.5.0. The bridge layer (9.2) isolates LeRobot from the rest of the system. |
| **Sprint 4a/4b balance** | Low | Low | Split into 4a (15 points) and 4b (16 points) keeps both under capacity. 4.2b can overflow if needed. |
| **Demo mode not ready for launch** | Low | Medium | 7.4 is a focused M-sized story with clear dependencies. Schedule early in Sprint 8. |

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
12. **Compatibility validated:** ISO tested on Surface Pro 7 and at least one non-Surface machine (MVP ship blocker). 5+ models is stretch goal.
13. **Docstrings:** All public classes and methods have Google-style docstrings. All CLI commands have help strings.
14. **Tests:** Every story ships with automated tests covering its core acceptance criteria. CI pipeline is green.
15. **Conformance tests:** ServoProtocol conformance test suite passes against MockServoProtocol and FeetechPlugin.

---

## Summary

| Sprint | Weeks | Epics | Stories | Weight | Theme | Demo |
|--------|-------|-------|---------|--------|-------|------|
| 0 | 0-1 | 0 | 2 | 4 | Tooling + environment | Green CI, hardware matrix |
| 1 | 1-2 | 1 | 5 | 5 | Package foundation | `armos --help` works |
| 2 | 3-4 | 2 | 5 | 17 | Hardware abstraction + conformance | `armos detect` finds servos |
| 3 | 5-6 | 3 | 5 | 11 | Robot profiles + cameras | `armos calibrate` works |
| 4a | 7-8 | 4, 5, 8 | 5 | 15 | Diag framework + live-build spike | Diagnostics framework + ISO boots in QEMU |
| 4b | 9-10 | 4, 5 | 4 | 16 | Active diagnostics + faults | `armos diagnose` runs all checks |
| 5 | 11-12 | 6 | 4 | 14 | Calibration + teleop | `armos teleop` -- first full demo |
| 6a | 13-14 | 7, 9 | 6 | 24 | TUI + data collection | TUI with first-run wizard |
| 6b | 15-16 | 8, 9 | 6 | 17 | USB image + polish | Bootable ISO with splash |
| 7 | 17-18 | 8 | 4+ | 14+ | CI/CD + hardware testing + release | MVP shipped |
| 8 | 19-20 | 7 | 1+ | 3+ | Launch preparation | Demo mode, launch day |
| 9 | 21-22 | -- | -- | -- | Post-launch stabilization | v0.1.2 patch release |
| **MVP Total** | **18 weeks** | **10** | **47** | **131** | | |
| **Through Launch** | **22 weeks** | **10** | **48+** | **134+** | | |
| Backlog | -- | 10, 11 | 16 | 45 | Growth phase | -- |
| **Grand Total** | **22+ weeks** | **12** | **64+** | **179+** | | |

**Estimated MVP delivery:** 18 weeks (Sprint 0 + 7 two-week sprints + buffer). Launch at week 20. Post-launch stabilization through week 22. This accounts for Sprint 4 split, Sprint 6 split, a dedicated hardware testing sprint, and a launch sprint.

---

_Sprint plan for armOS USB -- consolidated v2.0 from sprint plan, QA/execution enhancements, implementation enhancements, and review findings._
