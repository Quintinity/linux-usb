# armOS USB -- QA and Execution Enhancements

**Authors:** Quinn (QA Engineer) + Bob (Scrum Master)
**Date:** 2026-03-15
**Scope:** Enhancements to test strategy and execution plan based on business plan, market research, and product validation findings
**Status:** Action required -- incorporate into sprint plan and epics before Sprint 2

---

## Part 1: Test Strategy Enhancements (Quinn)

The QA review (review-qa.md) covers the core MVP test strategy. This document extends it with tests required by the business plan, market positioning, and go-to-market strategy. These are the tests that separate "works on my desk" from "works at a trade show in front of 50 people."

---

### 1.1 Demo Mode Testing

The business plan identifies the live demo as the single most important marketing asset. The vision document calls for "every demo follows the same script: start with a powered-off laptop and a disconnected robot." A demo failure at Maker Faire or ROSCon would be catastrophic for credibility.

#### What Demo Mode Must Do

1. Boot from USB to TUI dashboard (cold start, no cached state)
2. Auto-detect SO-101 hardware on plug-in
3. Load pre-baked calibration (skip the interactive calibration step)
4. Launch leader-follower teleop immediately
5. Display live telemetry overlay
6. Gracefully handle audience-caused failures (cable bump, power glitch)

#### Demo Mode Test Protocol

| Test | Procedure | Pass Criteria | Frequency |
|------|-----------|---------------|-----------|
| DM-1: Cold boot demo | Power off laptop, insert USB, connect SO-101 (powered off), boot, power on SO-101 | TUI shows detected hardware within 30s of desktop appearing | Before every public event |
| DM-2: Pre-baked calibration | Boot with demo profile that includes calibration data | Teleop starts without calibration prompt | Sprint 6b |
| DM-3: Cable disconnect recovery | Unplug USB-serial cable during active teleop | Alert within 2s, teleop halts gracefully, re-plug resumes within 5s | Sprint 5 |
| DM-4: Power glitch recovery | Briefly interrupt 12V supply to servo bus (simulate audience bumping power cable) | Voltage sag alert fires, servos re-enable after power returns, no position jump | Sprint 5 |
| DM-5: 30-minute endurance | Run teleop continuously for 30 minutes with periodic audience interaction (cable touches, table bumps) | No crash, no memory leak (RSS growth < 20MB), no latency degradation | Pre-event |
| DM-6: Projector-friendly TUI | Launch TUI on a 1920x1080 external display at 150% scaling | All panels visible, text readable from 3 meters, no rendering artifacts | Sprint 6a |
| DM-7: Narration-compatible | Run full demo while speaking (simulate presenter talking) | All steps completable with one hand (other holding microphone) | Pre-event |

#### Demo Mode Implementation

Add an `armos demo` command or `armos tui --demo` flag that:
- Skips first-run wizard
- Uses a bundled demo calibration profile
- Auto-starts teleop on hardware detection
- Enables large-font TUI mode for projector visibility
- Suppresses non-critical warnings (keep the display clean for audiences)

**Recommendation:** Add Story 7.4 "Demo Mode" (M=3) to Sprint 6a or post-MVP backlog. This is not MVP-blocking but is launch-blocking.

---

### 1.2 Education Fleet Testing -- 30 Concurrent Arms

The business plan projects education licensing as a significant revenue stream ($50-200/seat/year). The vision document describes "web dashboard for fleet management (classroom with 30 arms)." Before selling to a university, we need evidence that 30 stations running simultaneously does not cause problems.

#### Fleet Test Scenarios

| Test | Scenario | Pass Criteria |
|------|----------|---------------|
| FL-1: 30 simultaneous USB boots | 30 USB sticks flashed from same ISO, booted on 30 machines simultaneously | All 30 reach TUI within 120s. No stick-specific failures (rules out corrupted flash). |
| FL-2: Shared WiFi contention | 30 armOS stations on same WiFi network, all uploading telemetry CSVs to a shared NFS mount | No station loses data. Network congestion does not affect teleop latency (teleop is local). |
| FL-3: Instructor broadcast | Instructor station sends "start calibration" command to all 30 stations | All stations enter calibration within 5s. (Growth feature -- fleet management.) |
| FL-4: Staggered startup | Students arrive over 10 minutes, booting at random intervals | No resource contention. Late starters do not affect running stations. |
| FL-5: Mixed hardware fleet | 30 stations across 3-4 laptop models (Dell, Lenovo, HP, Surface) | 90%+ boot success rate across the fleet. Document per-model issues. |
| FL-6: Student abuse testing | Rapid plug/unplug of USB-serial cable, closing TUI mid-teleop, force-killing armos process | System recovers gracefully in all cases. No corrupted calibration data. |
| FL-7: Simultaneous data upload | 30 stations each upload a 500MB dataset to cloud training endpoint | Uploads complete within 10 minutes. Server handles concurrent connections. No partial uploads silently accepted. |

#### Fleet Test Lab Requirements

- Minimum 5 physical machines for initial testing (Sprint 7)
- Scale to 10-15 for pre-education-pilot testing (Growth phase)
- Full 30-station test requires partnership with pilot university (use their lab)
- QEMU can simulate boot behavior for 30 VMs but not USB hardware

**Recommendation:** FL-1 through FL-6 are Growth phase. FL-5 (mixed hardware) partially overlaps with Story 8.4. Add a "Fleet Simulation" story to Epic 10 backlog.

---

### 1.3 USB Boot Testing -- Hardware Compatibility Matrix

The business plan targets 90%+ boot success on post-2016 x86 UEFI hardware. The market research shows the target audience uses a wide range of laptops. Story 8.4 says "tested on 5+ hardware models" but does not specify which models or what constitutes a test.

#### Tier 1: Must Boot (Block MVP if Fails)

| Vendor | Model | CPU | Why It Matters |
|--------|-------|-----|----------------|
| Microsoft | Surface Pro 7 | i5-1035G4 | Primary dev machine. Requires linux-surface kernel patches. |
| Dell | XPS 13 (9310 or newer) | i7-1165G7+ | Most popular developer ultrabook. USB-C only -- tests hub compatibility. |
| Lenovo | ThinkPad T480/T490 | i5-8250U+ | Standard university/enterprise laptop. Good USB-A port availability. |

#### Tier 2: Should Boot (Document Issues, Do Not Block)

| Vendor | Model | CPU | Why It Matters |
|--------|-------|-----|----------------|
| HP | EliteBook 840 G5+ | i5-8350U+ | Common in education procurement. BIOS can be restrictive. |
| Intel | NUC 11/12/13 | i5/i7 NUC | Popular as dedicated robot station. Small form factor. |
| ASUS | VivoBook | i5 various | Consumer-grade, tests budget hardware. |
| Acer | Aspire | i5 various | Education market standard. |

#### Tier 3: Nice to Have (Growth Phase)

| Vendor | Model | CPU | Why It Matters |
|--------|-------|-----|----------------|
| Any | AMD Ryzen desktop | Ryzen 5 3600+ | Tests AMD compatibility (different IOMMU, USB controller). |
| Any | Intel N100 mini PC | N100 | Tests minimum viable hardware. |
| Apple | MacBook (via USB boot) | Intel i5/i7 | Pre-M1 Macs can USB boot. Large potential audience. |

#### Per-Machine Test Protocol

For each machine in the matrix, run and record:

1. **BIOS access:** Can Secure Boot be disabled? Is USB boot available in boot menu?
2. **Boot time:** Seconds from power-on to TUI (target: <90s)
3. **Hardware detection:** Does `armos detect` find CH340? USB cameras?
4. **Display:** Does the TUI render correctly on the native display?
5. **Keyboard/touchpad:** Do input devices work (especially on Surface with Type Cover)?
6. **USB ports:** Which ports work for servo controller? Camera? Both simultaneously?
7. **Persistence:** Does calibration survive a reboot?
8. **Teleop latency:** p95 latency reported by `armos teleop --benchmark`
9. **Thermal:** Does the laptop throttle during 10-minute teleop session?
10. **QEMU pre-check:** Does the ISO boot in QEMU? (If QEMU fails, real hardware may too.)

Record results in a public compatibility matrix (Markdown table in the repo).

**Recommendation:** Tier 1 testing is Sprint 7. Tier 2 is post-MVP. Tier 3 is Growth. Start sourcing Tier 2 machines in Sprint 4.

---

### 1.4 Profile Sharing and Marketplace Security Testing

The business plan describes a marketplace for robot profiles and plugins (20-30% commission on paid listings). The vision document describes "community robot profile repository (like Docker Hub for robots)." This creates an attack surface: malicious profiles.

#### Threat Model

| Threat | Vector | Impact | Likelihood |
|--------|--------|--------|------------|
| T1: YAML bomb | Profile with deeply nested anchors/aliases (`&a [*a, *a, *a]`) | OOM crash, denial of service | Medium |
| T2: Servo damage | Profile with dangerously high torque limits (overload_torque: 1000) or wrong voltage | Physical hardware damage, burnt servos | Medium |
| T3: Path traversal | Profile references `calibration_path: ../../../etc/shadow` | Read arbitrary files | Low |
| T4: Code injection | Profile YAML contains `!!python/exec` tag | Remote code execution | Low (if using safe loader) |
| T5: ID collision | Community profile uses servo IDs that conflict with user's existing robot | Servo bus collision, unpredictable behavior | Medium |
| T6: Dependency confusion | Plugin claims to be "feetech-v2" but wraps a different protocol | Silent data corruption, wrong servo commands | Low |

#### Security Test Cases

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| SEC-1: YAML safe load | Load a profile containing `!!python/exec 'import os; os.system("rm -rf /")'` | Load fails with clear error. No code executed. |
| SEC-2: YAML bomb | Load a profile with 10-level nested aliases expanding to 1GB | Load fails within 1 second. Memory usage does not exceed 100MB. |
| SEC-3: Path traversal | Profile with `calibration_path: ../../../../etc/passwd` | Path is rejected. Error message says "path must be within config directory." |
| SEC-4: Dangerous servo values | Profile with `overload_torque: 2000` (max safe is ~500 for STS3215) | Pydantic validation rejects with warning: "overload_torque exceeds safe maximum for STS3215." |
| SEC-5: Profile signature verification | Tamper with a signed community profile (flip one byte) | Signature check fails. Profile not loaded. |
| SEC-6: Servo ID range | Profile with `servo_id: 255` (outside valid range for protocol) | Validation rejects with clear error. |

**Recommendation:** SEC-1 through SEC-4 are MVP (Sprint 3, profile validation). SEC-5 is Growth phase (marketplace launch). SEC-6 is Sprint 3. Add Pydantic validators for hardware safety bounds in Story 3.1.

---

### 1.5 Cloud Training Pipeline Testing -- Network Failure Scenarios

The business plan identifies cloud training as the primary monetization point ($5-20 per training run). The product validation report confirms users cannot train locally (no GPU). A failed upload after hours of data collection would be devastating to user trust.

#### Network Failure Test Cases

| Test | Scenario | Pass Criteria |
|------|----------|---------------|
| NET-1: Upload interruption | Disconnect WiFi at 50% of a 500MB dataset upload | Upload pauses. On reconnect, resumes from where it stopped (chunked upload). No re-upload of completed chunks. |
| NET-2: Complete network loss | Start upload with no internet connection | Clear error within 5s: "No internet connection. Dataset saved locally at /path. Upload when connected." |
| NET-3: Slow connection | Throttle to 100 Kbps during upload | Progress bar updates. Estimated time shown. User can cancel without data loss. |
| NET-4: Server error mid-upload | Server returns 500 at 75% upload | Client retries 3 times with exponential backoff. On final failure, saves upload state for retry. Displays "Upload failed. Your data is safe locally. Retry with `armos upload --resume`." |
| NET-5: Timeout during training | Connection drops while waiting for training results | Poll with exponential backoff. Training continues server-side. Client reconnects and retrieves results when available. |
| NET-6: Corrupt upload detection | Flip one bit in the uploaded dataset | Server-side checksum validation catches corruption. Client is asked to re-upload. |
| NET-7: Concurrent uploads | Two stations upload to the same user account simultaneously | Both uploads succeed. No data interleaving. Both datasets appear in the user's account. |
| NET-8: Large dataset | Upload a 10GB dataset (1000 episodes) | Chunked upload works. Progress survives client restart. Server accepts the full dataset. |

#### Implementation Notes

- All uploads must be resumable (use tus.io protocol or similar chunked upload)
- Local dataset is never deleted until server confirms receipt (checksum match)
- Upload state file persists across reboots (stored alongside dataset)
- Offline queue: datasets collected offline are queued for upload when internet is available

**Recommendation:** Cloud training is Growth phase. NET-1 through NET-4 should be tested before cloud beta launch (Month 12). NET-5 through NET-8 before general availability.

---

### 1.6 ISO Release Regression Test Suite

Every ISO release must pass a standard test suite before being published. This prevents shipping broken images that damage the project's reputation ("I tried armOS and it didn't boot" is an unrecoverable first impression for most users).

#### Pre-Release Gate Tests

| Stage | Test | Tool | Pass Criteria | Blocking? |
|-------|------|------|---------------|-----------|
| 1 | ISO builds without error | live-build CI | Exit code 0, ISO size < 16GB | Yes |
| 2 | ISO boots in QEMU (UEFI) | test-iso.sh | Login prompt within 90s | Yes |
| 3 | `armos --version` in QEMU | test-iso.sh | Prints correct version | Yes |
| 4 | `armos profile list` in QEMU | test-iso.sh | Shows SO-101 | Yes |
| 5 | `armos detect` in QEMU (no hardware) | test-iso.sh | Graceful "no hardware found" message | Yes |
| 6 | `armos diagnose --dry-run` in QEMU | test-iso.sh | Framework runs, reports no hardware | Yes |
| 7 | All unit tests pass inside ISO | pytest in QEMU | 100% pass, 80%+ coverage | Yes |
| 8 | Boot on Tier 1 hardware (Surface Pro 7) | Manual | TUI launches, hardware detected | Yes |
| 9 | Boot on Tier 1 hardware (non-Surface) | Manual | TUI launches | Yes |
| 10 | Full workflow on real hardware | Manual | detect -> calibrate -> teleop -> record | Yes |
| 11 | Persistence test | Manual | Calibrate, reboot, calibration recalled | Yes |
| 12 | No open network ports | `ss -tlnp` in QEMU | Zero LISTEN entries | Yes |
| 13 | No world-writable files | `find /opt/armos -perm -o+w` | Zero results | Yes |
| 14 | Flash script syntax check | PowerShell -WhatIf | No syntax errors | Yes |

#### Release Checklist

Before publishing any ISO:

- [ ] All 14 gate tests pass
- [ ] CHANGELOG.md updated with user-facing changes
- [ ] Version number bumped in pyproject.toml
- [ ] Git tag created
- [ ] ISO SHA256 checksum published alongside download
- [ ] Compatibility matrix updated with any new test results
- [ ] Demo mode tested on real hardware (if demo mode is included)

**Recommendation:** Automate stages 1-7 and 12-14 in CI. Stages 8-11 are manual. Block ISO publication on all 14 passing.

---

### 1.7 Test Lab Specification

What hardware does the test lab need to execute all the tests described above?

#### Minimum Test Lab (MVP, Sprint 0 through 7)

| Item | Quantity | Purpose | Estimated Cost |
|------|----------|---------|----------------|
| Surface Pro 7 (existing) | 1 | Primary dev and test | $0 (owned) |
| Second x86 laptop (Dell/Lenovo/HP, used) | 1 | Tier 1 compat testing, ISO boot testing | $150-300 |
| SO-101 arm kit (existing) | 1 | Primary test hardware | $0 (owned) |
| USB cameras (1080p, USB-A) | 2 | Camera detection and data collection testing | $30-50 |
| USB-A hub (powered, 4+ ports) | 1 | Multi-device testing | $20-30 |
| USB flash drives (32GB, USB 3.0) | 5 | ISO flashing, persistence testing | $25-40 |
| Yepkit YKUSH (USB switchable hub) | 1 | Automated disconnect testing (C3 in QA review) | $50 |
| Bench power supply (adjustable, 6-12V) | 1 | Voltage sag simulation (DM-4) | $40-60 |
| **Total** | | | **$315-530** |

#### Growth Test Lab (Post-MVP, Education Pilot)

| Item | Quantity | Purpose | Estimated Cost |
|------|----------|---------|----------------|
| Additional x86 laptops (mixed vendors) | 3-5 | Tier 2 compat testing | $450-1,500 |
| Intel NUC | 1 | Dedicated station testing | $200-400 |
| Second SO-101 arm kit | 1 | Dual-arm testing, fleet simulation | $240 |
| Additional USB cameras | 2 | Multi-camera data collection | $30-50 |
| Network switch + WiFi AP | 1 | Fleet network testing | $50-80 |
| **Total additional** | | | **$970-2,270** |

**Recommendation:** Source minimum test lab items by Sprint 0. Budget $500. Growth lab items by Month 9. Budget $1,500.

---

## Part 2: Execution Plan Enhancements (Bob)

The sprint plan (sprint-plan.md) covers the MVP build. This section extends it with the business features, launch preparation, and post-launch execution that the business plan and go-to-market strategy require.

---

### 2.1 Updated Sprint Plan -- Where Business Features Fit

The business plan introduces features not in the current sprint plan: demo mode, telemetry/analytics, cloud training hooks, and the profile marketplace. Here is where each fits.

#### Features Added to Existing Sprints

| Feature | Sprint | Story | Size | Rationale |
|---------|--------|-------|------|-----------|
| Demo calibration profile | 3 | 3.2 (extend) | +S | Ship a pre-calibrated demo profile alongside the default SO-101 profile. Zero incremental work -- just a second YAML file with calibration data baked in. |
| Telemetry opt-in prompt | 6a | 7.0 (extend) | +S | First-run wizard asks "Share anonymous usage data to help improve armOS?" Stores preference in config. No data sent in MVP -- just the preference. |
| Upload dataset command stub | 6a | 9.3 (extend) | +S | `armos upload` command that saves dataset path and prints "Cloud training coming soon. Your dataset is saved at /path." Placeholder for Growth phase. |

#### Features Deferred to Post-MVP Sprints

| Feature | Target | Story | Size | Dependencies |
|---------|--------|-------|------|--------------|
| Demo mode (`armos tui --demo`) | Sprint 8 (Launch prep) | 7.4 | M | 7.1, 7.3, 3.2 |
| Anonymous telemetry collection | Sprint 9 (Post-launch) | 11.1 | L | 7.0 (opt-in), backend service |
| Cloud training upload | Sprint 10+ (Growth) | 11.2 | XL | 9.3, backend infra |
| Profile marketplace | Sprint 12+ (Growth) | 11.3 | XL | 3.1, backend, web UI |
| Fleet management dashboard | Sprint 14+ (Growth) | 11.4 | XL | Web dashboard, auth |

#### Sprint Plan Extension (Post-MVP)

| Sprint | Weeks | Theme | Key Deliverables |
|--------|-------|-------|-----------------|
| 8 | 19-20 | Launch preparation | Demo mode, landing page, demo video recording, documentation polish |
| 9 | 21-22 | Community launch | Discord setup, HN/Reddit posts, blog posts, bug triage from first users |
| 10 | 23-24 | Stabilization | Bug fixes from user feedback, compatibility matrix expansion, Tier 2 hardware testing |
| 11 | 25-26 | Telemetry + analytics | Anonymous usage telemetry, crash reporting, feedback pipeline |
| 12 | 27-28 | Cloud training alpha | Upload pipeline, GPU backend, first 10 training runs |

---

### 2.2 Pre-Launch Checklist

What must be done before posting on LeRobot Discord, Hacker News, or r/robotics. A premature launch with missing pieces will get one shot at a first impression.

#### Must Have (Blocks Launch)

- [ ] **ISO boots and works on 2+ laptop models** (Tier 1 testing complete)
- [ ] **Full workflow works end-to-end:** boot -> detect -> calibrate -> teleop -> record
- [ ] **Demo video recorded:** 90-second, uncut, USB-to-teleop (the business plan's "single most important marketing asset")
- [ ] **GitHub repo public** with compelling README (embedded demo video, feature list, download link)
- [ ] **Download link works** (ISO hosted on GitHub Releases or similar CDN)
- [ ] **SHA256 checksum published** alongside ISO download
- [ ] **Quick-start guide:** 1-page PDF or README section: "1. Download. 2. Flash. 3. Boot. 4. Connect robot."
- [ ] **Known issues documented** (compatibility matrix, known limitations)
- [ ] **Discord server created** with channels: #general, #help, #show-your-setup, #bug-reports, #development
- [ ] **License file present** (Apache 2.0, per business plan)
- [ ] **No secrets in ISO** (API keys, passwords, personal paths -- scan before publishing)
- [ ] **flash.ps1 tested on Windows 10 and 11** (the primary audience's flash platform)

#### Should Have (Improves Launch Quality)

- [ ] **Blog post:** "I spent 40 hours debugging a robot arm, so I built an OS" (HN-optimized title)
- [ ] **3 tutorial blog posts** per GTM strategy: SO-101 from scratch, existing LeRobot user, educator setup
- [ ] **GitHub Issues templates:** bug report, feature request, hardware compatibility report
- [ ] **Contributing guide** (CONTRIBUTING.md) with profile contribution workflow
- [ ] **Demo mode working** for live demos at meetups
- [ ] **Tested by 3+ external users** (alpha testers recruited from LeRobot Discord)

#### Nice to Have (Can Follow Within 1 Week of Launch)

- [ ] YouTube channel with demo video
- [ ] X/Twitter account with launch thread
- [ ] Compatibility matrix with 5+ machines

---

### 2.3 Launch Sprint (Sprint 8, Weeks 19-20)

The two-week sprint that turns the shipped MVP into a public launch.

#### Sprint 8 Goal

Prepare and execute the public launch of armOS. By the end of this sprint, armOS is live on GitHub, announced on 3+ channels, and the demo video has been published.

| Day | Activity | Owner | Deliverable |
|-----|----------|-------|-------------|
| 1-2 | Demo mode implementation (Story 7.4) | Dev | `armos tui --demo` working |
| 3 | Record demo video (3-5 takes, edit to 90 seconds) | Dev | YouTube-ready video |
| 4-5 | Write launch blog post | Dev | Published on blog/Medium/Dev.to |
| 6 | Final ISO build with demo mode included | Dev | v0.1.0 ISO on GitHub Releases |
| 7 | Create Discord server, configure channels and roles | Dev/Community | Discord invite link |
| 8 | Write GitHub README with embedded video, download link | Dev | README.md finalized |
| 9 | Alpha tester feedback incorporated, final bug fixes | Dev | v0.1.1 if needed |
| 10 | **Launch day:** Post to LeRobot Discord, HN, r/robotics, X/Twitter | Dev | Posts live |

#### Launch Day Checklist

- [ ] ISO download link verified (download and flash on a clean machine)
- [ ] Demo video uploaded to YouTube (unlisted until launch, then public)
- [ ] HN post draft ready: "Show HN: armOS -- Boot any laptop into a robot control station in 5 minutes"
- [ ] LeRobot Discord message ready (clear, concise, includes video link)
- [ ] r/robotics post ready
- [ ] Monitor all channels for 4 hours after posting -- respond to every comment
- [ ] Have a bug-fix ISO build pipeline ready (you will need it)

#### Success Metrics (End of Sprint 8)

| Metric | Target | Stretch |
|--------|--------|---------|
| GitHub stars | 100 | 500 |
| ISO downloads | 50 | 200 |
| Discord members | 25 | 100 |
| Demo video views | 500 | 2,000 |
| Bug reports filed | 5+ (means people are actually using it) | -- |
| Alpha testers who complete full workflow | 5 | 15 |

---

### 2.4 Post-Launch Sprint (Sprint 9, Weeks 21-22)

The first two weeks after launch. Expect a flood of bug reports, compatibility issues, and feature requests. This sprint is 100% reactive.

#### Sprint 9 Goal

Respond to every user issue within 24 hours. Ship a patch release (v0.1.2) addressing the top 5 user-reported issues. Maintain community momentum.

#### Sprint 9 Structure

| Activity | Time Allocation | Notes |
|----------|----------------|-------|
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

#### What to Expect (Based on Product Validation Research)

The product validation report documents the most common LeRobot failure modes. Expect user reports about:

1. **Boot failures on specific hardware** -- BIOS settings, Secure Boot, USB controller quirks
2. **Servo communication intermittent failures** -- power supply issues on user's hardware
3. **Camera not detected** -- specific webcam models not supported by kernel
4. **Calibration confusion** -- users not understanding the homing procedure
5. **"It worked once but now it doesn't"** -- persistence/reboot issues

Prepare template responses for each of these categories before launch.

---

### 2.5 Partnership Development Timeline

The business plan identifies Seeed Studio, HuggingFace, and Intel as key partners. Partnerships require warm relationships and demonstrated traction. Here is the timeline.

#### Phase 0: Warm-Up (Sprints 6-8, Months 4-5)

| Action | When | Who to Contact | Purpose |
|--------|------|----------------|---------|
| Submit upstream patches to LeRobot | Sprint 5-6 | LeRobot maintainers (@cadene, @aliberts) | Build credibility. Show we contribute, not just consume. |
| Open a discussion in LeRobot GitHub | Sprint 7 | LeRobot community | "We're building a bootable USB for LeRobot. Here's a demo. Feedback?" |
| Email the HuggingFace robotics team | Sprint 8 | HuggingFace community team | Propose co-marketing. Offer to write a guest blog post. |

#### Phase 1: First Contact (Sprints 9-11, Months 5-7)

| Action | When | Target Partner | Pitch |
|--------|------|----------------|-------|
| Send armOS USB stick to Seeed Studio | Week after launch | Seeed Studio partnerships team | "Your SO-101 customers spend hours on setup. This USB eliminates that. Want to bundle it?" |
| Send USB sticks to 5 robotics YouTubers | Sprint 9 | James Bruton, Skyentific, The Construct, etc. | "Here's a USB stick. Boot any laptop, plug in an SO-101, teleop in 5 minutes. Film it?" |
| Contact university robotics instructors | Sprint 10 | Georgia Tech ECE 4560 (already uses SO-101), MIT, Stanford | "Run your next robotics lab on armOS. No student setup failures. Free pilot." |
| Reach out to Feetech | Sprint 11 | Feetech sales team | "We reduce your STS3215 support burden. Include our USB with your servo kits." |

#### Phase 2: Formalize (Months 8-12)

| Action | When | Target | Outcome |
|--------|------|--------|---------|
| Seeed Studio partnership agreement | Month 8-9 | Seeed Studio | "Powered by armOS" on SO-101 kit listing, USB stick included in Pro kit |
| HuggingFace blog post | Month 9 | HuggingFace blog | Joint post: "The fastest way to start with LeRobot" |
| University pilot | Month 10 | Pilot university | 20-student course, one semester, feedback report |
| Intel outreach | Month 11 | Intel Developer Relations | "Robotics on Intel" co-marketing. OpenVINO integration for local inference. |
| ROSCon/PyCon talk submission | Month 9-10 | Conference organizers | "armOS: A Bootable USB for Robot Arms" (15-minute talk) |

---

### 2.6 Content Calendar (Months 1-6)

The business plan calls for 2 blog posts/month, 2 YouTube videos/month, and weekly dev log posts. Here is the concrete calendar.

#### Month 1 (Sprints 1-2): Build in Public

| Week | Content | Channel | Purpose |
|------|---------|---------|---------|
| 1 | "Why I'm building an OS for robot arms" (dev log #1) | Blog, X | Establish narrative, attract early followers |
| 2 | "The brltty serial port bug that wastes everyone's time" | Blog, Dev.to, HN | SEO, demonstrate expertise, standalone value |
| 3 | "Building a servo protocol abstraction layer" (dev log #2) | Blog, X | Transparency, attract contributors |
| 4 | "Power supply problems you'll hit with STS3215 servos" | Blog, Dev.to | SEO, standalone value |

#### Month 2 (Sprints 3-4): Technical Deep Dives

| Week | Content | Channel | Purpose |
|------|---------|---------|---------|
| 5 | "How to tune overload protection on Feetech servos" | Blog, YouTube | Most-searched topic in LeRobot community |
| 6 | "YAML robot profiles: the configuration layer nobody built" (dev log #3) | Blog, X | Feature preview |
| 7 | "Diagnosing servo communication failures (sync_read explained)" | Blog, YouTube | Technical credibility |
| 8 | "Building the diagnostic suite" (dev log #4) | Blog, X | Feature preview |

#### Month 3 (Sprints 5-6a): Demo Content

| Week | Content | Channel | Purpose |
|------|---------|---------|---------|
| 9 | 30-second teaser: "armOS first teleop" | X, YouTube Shorts | Build anticipation |
| 10 | "Leader-follower teleoperation from scratch" (tutorial) | YouTube, Blog | Educational content |
| 11 | "Building a TUI for robot control with Textual" (dev log #5) | Blog, X | Attract Python developers |
| 12 | "The 90-second demo video" (pre-launch teaser) | YouTube, X | Pre-launch buzz |

#### Month 4 (Sprint 6b-7): Pre-Launch

| Week | Content | Channel | Purpose |
|------|---------|---------|---------|
| 13 | "How to build a bootable Linux USB with live-build" | Blog, Dev.to | SEO, technical audience |
| 14 | "Testing armOS on 5 different laptops" (compatibility results) | Blog, YouTube | Build confidence |
| 15 | "The complete armOS getting started guide" | Blog, YouTube | Launch-ready tutorial |
| 16 | Pre-launch announcement: "armOS launches next week" | X, Discord, all channels | Hype |

#### Month 5 (Sprint 8): Launch

| Week | Content | Channel | Purpose |
|------|---------|---------|---------|
| 17 | **Launch blog post** + demo video | Blog, HN, Reddit, Discord | **The big moment** |
| 18 | "From unboxing to AI data collection in 10 minutes" (full tutorial) | YouTube | Post-launch onboarding |
| 19 | "Building a robotics lab with armOS" (educator guide) | Blog | Education market |
| 20 | User spotlight: first community setup | Blog, X | Social proof |

#### Month 6 (Sprint 9-10): Post-Launch

| Week | Content | Channel | Purpose |
|------|---------|---------|---------|
| 21 | "What we learned from 100 users" (retrospective) | Blog | Transparency, iterate publicly |
| 22 | "Contributing a robot profile to armOS" (guide) | Blog, YouTube | Grow contributor base |
| 23 | "armOS v0.2: what's coming next" (roadmap post) | Blog, X | Maintain momentum |
| 24 | Conference talk submission materials | PyCon/ROSCon | Long-term credibility |

#### Content Production Notes

- Blog posts: target 1,000-2,000 words. Optimize titles for search ("How to [solve specific problem]").
- YouTube videos: target 5-10 minutes for tutorials, 60-90 seconds for demos. Thumbnails matter.
- Dev log posts: casual tone, 500-1,000 words. Show real terminal output and code.
- All content should work standalone -- do not require the reader to know what armOS is. The content markets itself.

---

## Combined Priority Matrix

| Enhancement | Category | Phase | Sprint | Blocks |
|-------------|----------|-------|--------|--------|
| ISO regression test suite (1.6) | QA | MVP | Sprint 6b | ISO release |
| Hardware compat matrix protocol (1.3) | QA | MVP | Sprint 7 | MVP ship |
| Profile security validation (1.4, SEC-1 to SEC-4) | QA | MVP | Sprint 3 | Profile system |
| Pre-launch checklist (2.2) | Execution | MVP | Sprint 7-8 | Public launch |
| Demo video recording | Execution | Launch | Sprint 8 | Public launch |
| Demo mode (1.1) | QA + Execution | Launch | Sprint 8 | Trade shows |
| Launch sprint plan (2.3) | Execution | Launch | Sprint 8 | Public launch |
| Post-launch triage process (2.4) | Execution | Launch | Sprint 9 | Community health |
| Content calendar start (2.6) | Execution | Ongoing | Sprint 1 | SEO, awareness |
| Partnership warm-up (2.5) | Execution | Growth | Sprint 5-6 | Revenue |
| Cloud training network tests (1.5) | QA | Growth | Sprint 12+ | Cloud beta |
| Fleet testing (1.2) | QA | Growth | Sprint 14+ | Education sales |
| Marketplace security (1.4, SEC-5) | QA | Growth | Marketplace launch | Marketplace |
| Test lab buildout (1.7) | QA | Ongoing | Sprint 0 start | All testing |

---

_QA and execution enhancements for armOS USB -- generated by Quinn (QA Engineer) and Bob (Scrum Master)._
