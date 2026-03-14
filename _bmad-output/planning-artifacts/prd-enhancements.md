# PRD Enhancements -- Business-Informed Update

**Author:** John (Product Manager)
**Date:** 2026-03-15
**Based on:** Vision, Business Plan, Market Research, Product Validation, PM Review, Current PRD
**Status:** Proposed enhancements -- pending founder review

---

## 1. New and Refined User Journeys

### UJ6: Educator Deploying 30 Arms (Classroom Fleet)

**Actor:** University instructor setting up a robotics lab for ECE 4560 (like Georgia Tech).
**Context:** The education market is $1.8B and growing at 18.1% CAGR. Georgia Tech already assigns SO-101 builds. This journey must be frictionless enough for a TA to execute, not just the professor.

1. Instructor downloads the armOS image and flashes one USB stick.
2. Instructor boots one station, connects an SO-101, runs calibration, and verifies teleop works.
3. Instructor opens "Fleet Mode" from the TUI: exports the current profile + calibration + a locked-down configuration (no terminal access, restricted menus) as a clonable image.
4. TA uses a batch cloning tool (Etcher-style, multi-target) to flash 29 additional USB sticks from the master image.
5. On lab day, 30 students insert USB sticks into 30 different laptops (Dell, HP, Lenovo mix). Each boots to a branded splash screen showing the course name and lab number.
6. Each station auto-detects its SO-101. Because the profile is pre-loaded, students skip profile matching and go straight to "Calibrate" (each physical arm needs its own calibration, but the workflow is guided and takes under 3 minutes).
7. Instructor's station shows a "Fleet Dashboard" -- a simple grid of station status: booted, calibrating, teleoping, error. Requires local network (DHCP on a lab switch). No internet required.
8. When a student's station shows an error, the fleet dashboard surfaces the diagnostic message (e.g., "Station 14: Servo 3 voltage sag -- check power supply").
9. At end of semester, instructor collects all USB sticks. Student data (datasets, calibrations) is on the sticks. No data leaves the lab network.

**New FRs needed:** FR45 (Fleet Mode image export), FR46 (Fleet Dashboard -- local network station monitoring), FR47 (Locked-down classroom configuration).

**Phase:** Fleet Dashboard is Growth (v0.5). Image cloning and locked-down config should be pulled into late MVP or v0.1.1 -- educators are early adopters and the $50-200/seat/year licensing depends on this journey working.

**Success:** 30 stations operational in under 60 minutes (2 minutes per station average). Instructor can monitor all stations from one screen.

---

### UJ7: Hackathon Participant (Zero to Demo in 2 Hours)

**Actor:** One of the 3,000+ LeRobot hackathon participants who just received an SO-101 kit at a hackathon venue.
**Context:** The LeRobot hackathon across 100+ cities is the single largest concentration of our target users. If armOS is not the tool they reach for at these events, we have failed at distribution.

1. Participant receives an SO-101 kit and an armOS USB stick (distributed by event organizers or downloaded from armOS.dev QR code on a poster).
2. Participant plugs USB into their personal laptop (unknown hardware -- could be anything).
3. System boots. If boot fails (BIOS not set to USB), the boot splash shows a 5-second "If you see this, press [key] for boot menu" message tailored to the top 5 laptop brands detected from SMBIOS data.
4. Hardware is detected. System enters "Hackathon Mode" -- a streamlined flow that skips advanced options and goes straight to: Calibrate > Teleop > Collect Data.
5. After 30 minutes of data collection, participant wants to train a policy. System shows: "Training requires a GPU. Upload your dataset to armOS Cloud or HuggingFace Hub." One-click upload (requires WiFi, which hackathon venues provide).
6. While waiting for training (20-40 minutes on armOS Cloud), participant explores "Demo Mode" -- pre-loaded example policies that show what a trained arm can do (replay of a pick-and-place, wave, or sorting task using pre-recorded trajectories).
7. Training completes. Participant downloads the policy, loads it via the dashboard, and runs inference. Their arm now does the task autonomously.
8. Participant shares their profile + trained policy to the armOS community hub with one click.

**New FRs needed:** FR48 (Hackathon Mode -- streamlined first-run flow), FR49 (Demo Mode -- pre-loaded replay trajectories), FR50 (One-click dataset upload to armOS Cloud or HuggingFace Hub), FR51 (One-click policy download and deployment).

**Phase:** Hackathon Mode and Demo Mode are MVP. Cloud upload/download is Growth (v0.5), but the UX for it should be designed now so the button exists in MVP with a "Coming Soon" state.

**Success:** Participant goes from unboxing to autonomous policy execution in under 2 hours. Zero terminal commands. armOS USB sticks become standard issue at LeRobot hackathons.

---

### UJ8: Seeed Studio Customer Unboxing

**Actor:** Customer who just received an SO-101 Pro kit ($240) from Seeed Studio, with an armOS USB stick included in the box.
**Context:** This is the hardware partnership revenue model ($3-5 per USB stick). The unboxing experience must justify Seeed including the USB stick instead of just pointing to their wiki.

1. Customer opens the SO-101 Pro box. Inside: servo kit, cables, screws, 3D printed parts, and a small armOS USB stick in a branded sleeve with a QR code.
2. QR code links to armOS.dev/seeed-quickstart -- a single page with a 90-second video and three steps: (a) assemble the arm, (b) plug in the USB, (c) boot and connect.
3. Customer assembles the arm following Seeed's existing assembly guide.
4. Customer plugs the armOS USB into their laptop and boots.
5. System boots to a Seeed-cobranded splash screen ("Powered by armOS -- Seeed Studio SO-101 Edition").
6. System detects the SO-101 hardware. Because this is a Seeed-distributed USB, the SO-101 profile is pre-loaded and pre-selected. No profile matching needed.
7. Guided calibration walks the customer through homing each joint with visual diagrams showing which joint to move (drawn from the Seeed wiki's existing images, licensed for use).
8. Customer completes calibration, starts teleop, and moves the arm within 5 minutes of first boot.
9. Dashboard shows a "What's Next?" panel: links to the HuggingFace robotics course, the armOS community Discord, and the armOS Cloud training service.

**New FRs needed:** FR52 (Co-branded boot splash -- configurable per hardware partner), FR53 (Partner quickstart URL embedded in boot splash), FR54 ("What's Next?" onboarding panel with partner-specific links).

**Phase:** Co-branding and partner quickstart are Growth (v0.5) -- needed before Seeed partnership closes. But the "What's Next?" panel should be in MVP for all users (just without partner branding).

**Success:** Seeed customer reaches teleop in under 5 minutes. Seeed support tickets for SO-101 setup drop by 50%+. Seeed renews the partnership.

---

## 2. New Functional Requirements for Business Model

### Telemetry (Opt-In)

These requirements enable the data flywheel described in the vision document and provide the usage metrics the business plan depends on.

- **FR55: Opt-in telemetry consent on first boot.** The first-run wizard includes a clear, plain-language telemetry opt-in screen. Default is OFF. The screen explains exactly what is collected (hardware model, boot success, profile used, diagnostic results) and what is never collected (camera feeds, datasets, personal information). Users can change their preference at any time from the dashboard settings.

- **FR56: Anonymous hardware compatibility reporting.** When opted in, the system sends a single anonymous HTTP POST on each successful boot: hardware model (SMBIOS), boot time, kernel version, detected USB devices. No user identifier. This feeds the hardware compatibility matrix automatically instead of relying on manual community reports.

- **FR57: Diagnostic result sharing.** When opted in, the system can upload anonymized diagnostic results (servo health summary, fault types, communication reliability scores) to a central aggregation service. This powers "common issues" knowledge and improves default protection settings across the fleet.

- **FR58: Telemetry dashboard for maintainers.** A simple admin dashboard (internal tool, not user-facing) that aggregates telemetry data: boot success rates by hardware model, most common faults, profile usage distribution, geographic distribution of users. This is how we know if the product is working without relying on GitHub issues.

**Phase:** FR55-FR57 are Growth (v0.5). FR58 is Growth/Vision. But the telemetry architecture (what data, what format, where it goes) should be designed during MVP so we do not have to retrofit it later.

### Cloud Training Hooks

The business plan projects cloud training as the primary revenue stream ($5-20 per training run, $60K/year moderate scenario by Year 2).

- **FR59: Dataset export to HuggingFace Hub.** Users can push a locally collected dataset to their HuggingFace account with one command or dashboard button. This is the existing LeRobot workflow, but armOS should make it zero-config (pre-configure the HF CLI, provide a guided login flow).

- **FR60: armOS Cloud training integration.** Users can submit a dataset to the armOS Cloud training service directly from the dashboard. The flow: select dataset > choose model architecture (ACT, Diffusion Policy) > confirm > upload > receive notification when training completes > download trained policy. Pricing is displayed before upload ("This training run will cost approximately $X based on dataset size").

- **FR61: Policy deployment from cloud.** Users can download a trained policy from armOS Cloud and load it for inference, all from the dashboard. The system verifies the policy is compatible with the connected hardware before attempting to run it.

**Phase:** FR59 is late MVP or v0.1.1 (it is mostly existing LeRobot functionality with UX polish). FR60-FR61 are Growth (v0.5) and depend on backend infrastructure.

### Profile Sharing

The profile ecosystem is the network-effect moat. These requirements make sharing frictionless.

- **FR62: Profile export as shareable file.** Users can export their robot profile (YAML + calibration data + any custom protection settings) as a single .armos file (zip archive) that can be shared via email, Discord, or USB.

- **FR63: Profile import from file or URL.** Users can import a .armos profile file from local storage or a URL. The system validates the profile against the schema before importing.

- **FR64: Community profile browser.** The dashboard includes a "Community Profiles" section that lists profiles from a central repository (GitHub-backed). Users can browse, search by robot type or servo protocol, and install profiles with one click. Requires internet.

- **FR65: Profile contribution workflow.** Users can submit their profile to the community repository directly from the dashboard. The submission creates a GitHub PR with the profile YAML, a hardware photo (optional), and test results from the diagnostic suite.

**Phase:** FR62-FR63 are Growth (v0.5). FR64-FR65 are Vision (v1.0). But the .armos file format should be defined during MVP so early adopters can share profiles manually.

---

## 3. Go-to-Market Requirements

### Demo Mode (MVP)

The business plan and product validation both identify the 90-second demo video as the single highest-leverage marketing asset. Demo Mode makes every armOS installation a potential demo.

- **FR49 (from UJ7): Pre-loaded demo trajectories.** The MVP ships with 2-3 pre-recorded SO-101 trajectories (wave, pick-and-place, point-to-point) that can be replayed without a trained policy or leader arm. These are recorded servo position sequences, not ML policies -- dead simple, always work.

- **FR66: Demo Mode launcher.** A prominent "Demo" button on the TUI dashboard. When pressed with hardware connected, it replays the pre-loaded trajectories. When pressed without hardware, it plays a video of the trajectories. This means armOS can demo itself even at a booth where the robot is not yet assembled.

- **FR67: Screen recording integration.** Users can record a screen capture of their armOS session (TUI + camera feeds) with one keypress. Output is an MP4 file on the USB. This makes it trivial for users to share their experience on social media -- every user becomes a potential marketing channel.

**Phase:** FR49 and FR66 are MVP. FR67 is Growth.

### Landing Page Requirements

The landing page is the top of the adoption funnel. These are product requirements because the landing page content depends on product capabilities.

- **GTM-1: Landing page at armOS.dev.** Single page with: hero video (90-second boot-to-teleop), three value props (zero setup / built-in diagnostics / works on any laptop), download button, hardware compatibility list, "Star us on GitHub" CTA.

- **GTM-2: SEO content strategy.** Three blog posts to publish before or at launch, each targeting a specific search query:
  1. "brltty stealing serial ports on Ubuntu" -- targets the #1 pain point, links to armOS as the fix.
  2. "SO-101 servo stuttering fix" -- targets power supply and overload protection issues.
  3. "LeRobot setup guide 2026" -- targets the broadest query, positions armOS as the recommended path.

- **GTM-3: 90-second video script outline.**
  - 0:00-0:05 -- "What if setting up a robot arm took 5 minutes instead of 5 hours?"
  - 0:05-0:15 -- Show the pain: terminal scrolling with error messages, GitHub issues, frustrated user.
  - 0:15-0:25 -- "armOS is a USB stick that turns any laptop into a robot control station."
  - 0:25-0:45 -- The demo: USB inserted, laptop boots, SO-101 detected, calibration, teleop working. Timer in corner. Real hardware, no cuts.
  - 0:45-0:55 -- "Built-in diagnostics tell you exactly what's wrong." Show diagnostic panel catching a voltage sag.
  - 0:55-1:15 -- "Collect training data. Upload to the cloud. Download a trained policy." Show the full loop.
  - 1:15-1:25 -- "Open source. Works offline. No GPU required."
  - 1:25-1:30 -- "armOS. Plug in. Boot up. Your robot works." URL + GitHub star CTA.

- **GTM-4: Hackathon distribution kit.** A downloadable package for hackathon organizers: USB image, one-page printed quickstart (PDF), table tent with QR code, and a slide deck for the opening presentation. Targets the 3,000+ LeRobot hackathon participants across 100+ cities.

**Phase:** GTM-1 and GTM-3 are pre-launch (must exist before MVP ships). GTM-2 starts during development (write posts about real debugging experiences as they happen). GTM-4 is Growth, but the quickstart PDF should be drafted during MVP.

---

## 4. Competitive Positioning Refinements

### phosphobot Differentiation Matrix

phosphobot is YC-backed and claims 1,000+ robots. We need a clear, honest differentiation story.

| Dimension | phosphobot | armOS | Why It Matters |
|-----------|-----------|-------|----------------|
| **Price** | Kits from $995 + subscription | Free + BYOH ($0 + your $220 SO-101) | 4x cost difference. Hobbyists and students cannot afford $995. |
| **Hardware lock-in** | Their kits, their platform | Any x86 laptop + any supported arm | Educators buy the cheapest option. Seeed sells at $220-240. |
| **Offline operation** | Cloud-dependent for training features | Fully offline for all core functions | Schools and hackathons have unreliable WiFi. |
| **Diagnostics** | Not a focus | Core differentiator -- real-time servo health monitoring | No one else does this. It is the feature that makes beginners successful. |
| **Boot experience** | Install their software on your machine | Boot from USB, touch nothing on the host | Zero commitment. Zero risk to the host OS. Try before you buy. |
| **VR teleoperation** | Meta Quest support | Not planned (MVP) | phosphobot advantage. Not relevant for most educational use cases. |
| **Community** | ~76 GitHub stars | N/A (pre-launch) | They are ahead on launch but behind on community size vs. LeRobot ecosystem. |

**Positioning statement (for internal use and pitch decks):**

> phosphobot sells a vertically integrated platform -- their hardware, their software, their cloud. armOS is the horizontal layer -- it works with any hardware, on any laptop, for free. We are the Android to their iPhone. They will capture the high end; we will capture the long tail.

### HuggingFace/Pollen Robotics Acquisition

HuggingFace acquired Pollen Robotics and released Reachy Mini and HopeJr. This is both an opportunity and a risk.

**Risk:** HuggingFace could build their own "LeRobot OS" -- a setup tool or bootable image that does what armOS does, backed by their 22k-star community and $4.5B valuation. If they do, we cannot compete on distribution.

**Mitigation:** Position armOS as the *community* deployment tool for LeRobot, not a competitor to HuggingFace's own hardware. Engage the LeRobot team immediately. Offer to upstream patches. The ideal outcome is a mention in LeRobot's README: "For the fastest setup experience, use armOS." If HuggingFace builds their own tool, pivot to diagnostics + fleet management as the value-add layer on top.

**Opportunity:** HuggingFace's hardware play (Reachy Mini, HopeJr) means they need deployment tooling for *their own* robots. armOS profiles for Reachy Mini and HopeJr could make us a natural partner rather than a competitor.

**New FR:** FR68 -- Reachy Mini and HopeJr robot profiles (Growth phase, contingent on partnership discussion).

### Arduino/Qualcomm Acquisition as Exit Precedent

Arduino was acquired by Qualcomm in October 2025 after $54M in funding. The Arduino path -- hardware partnerships + education ecosystem + open source community -- is the closest analogy to armOS's trajectory.

**Implications for PRD:**
- The education licensing model ($50-200/seat/year) and hardware partnership model ($3-5/unit) are the same revenue streams Arduino used.
- Qualcomm acquired Arduino for the developer ecosystem and education distribution, not for the technology.
- **For armOS, this means community size and education penetration are the metrics that matter for an exit.** The PRD success metrics should weight these heavily.

### Foxglove Pricing Signal

Foxglove charges $18-90/user/month for robotics devtools and raised $58M. This validates that robotics developers will pay for tooling.

**Implications for PRD:**
- The business plan's $50-200/seat/year education pricing is conservative relative to Foxglove's $216-1,080/user/year.
- Consider a "Pro" tier for individual power users at $10-15/month that unlocks: advanced diagnostics (stress tests, long-duration monitoring), priority cloud training queue, and profile analytics (how your robot compares to fleet averages).
- **New FR:** FR69 -- Pro tier feature gating (Vision phase). The free tier includes everything in MVP. The Pro tier adds power-user features that do not affect the core "boot and teleop" experience.

---

## 5. Updated Success Metrics

The current PRD targets 100+ GitHub stars in 6 months. The PM review suggested 500. Given the market research (3,000+ hackathon participants, 15k Discord members, 22k LeRobot stars), and the business plan's need for traction to close partnerships, the metrics need to be more ambitious and more closely tied to revenue prerequisites.

### Revised Metrics Table

| Metric | Current PRD Target | Revised Target | Rationale | Traces To |
|--------|-------------------|----------------|-----------|-----------|
| GitHub stars (6 months) | 100+ | 500+ | 15k LeRobot Discord members. If 3% try armOS and 10% star, that is 45 stars from Discord alone. Add HN, Reddit, YouTube. 500 is ambitious but achievable. | SC6 (revised) |
| Active users (6 months) | Not defined | 50+ | Defined as: booted armOS and completed teleop at least once. Tracked via opt-in telemetry or self-reported survey. This is the metric that matters for partnership pitches. | New SC9 |
| USB image downloads (6 months) | Not defined | 1,000+ | Top of funnel. GitHub release download count. Expect 5-10% conversion to active user. | New SC10 |
| Time to first teleop | Under 5 min | Under 5 min (unchanged) | Core value prop. Non-negotiable. | SC1 |
| Hardware compatibility | 90% of tested | 90% of tested (unchanged), but test matrix expanded to 20+ models starting Sprint 4 | PM review recommendation: start testing early. | SC5 |
| Community-contributed profiles | Not defined | 5+ by 12 months | This is the network effect indicator. If no one contributes profiles, the platform thesis fails. | New SC11 |
| Education pilots | Not defined | 1 university pilot by 12 months | Required for education licensing revenue. Georgia Tech ECE 4560 is the obvious first target. | New SC12 |
| Hardware partnership LOI | Not defined | 1 signed LOI by 12 months | Required for the $3-5/unit revenue stream. Seeed Studio is the primary target. | New SC13 |
| Hackathon presence | Not defined | armOS USB distributed at 3+ hackathon events by 12 months | 3,000+ hackathon participants is the launch audience. Being present at events is the distribution strategy. | New SC14 |
| Cloud training beta users | Not defined | 10+ users completing training runs by 15 months | Business plan projects this as the primary revenue stream. Must validate demand before investing in infrastructure. | New SC15 |
| Monthly recurring revenue | Not defined | $1K MRR by 18 months | Modest but proves the model works. Sources: cloud training + education pilot + USB sales. | New SC16 |

### Leading Indicators (Track from Day 1)

These are not success criteria but early warning signals:

| Indicator | Signal | Action If Weak |
|-----------|--------|---------------|
| Demo video views (first 2 weeks) | <500 views | Rethink distribution channels. Try paid promotion on r/robotics. |
| LeRobot Discord reaction to launch post | <10 replies | The messaging is wrong. Reposition around a specific pain point, not the platform vision. |
| Boot failure reports (first 50 users) | >20% failure rate | Halt feature work. Focus entirely on hardware compatibility. |
| Seeed Studio response to partnership email | No response in 2 weeks | Try Waveshare and Feetech in parallel. Approach via warm intro, not cold email. |
| Profile contributions (first 6 months) | Zero external contributions | Simplify the contribution workflow. Write 2-3 example profiles yourself to show the pattern. |

---

## 6. Summary of All New FRs

| FR | Description | Phase | Business Driver |
|----|-------------|-------|-----------------|
| FR45 | Fleet Mode image export (locked-down classroom config) | Growth | Education licensing ($50-200/seat/yr) |
| FR46 | Fleet Dashboard (local network station monitoring) | Growth | Education licensing |
| FR47 | Locked-down classroom configuration | Growth | Education licensing |
| FR48 | Hackathon Mode (streamlined first-run flow) | MVP | Hackathon distribution (3,000+ participants) |
| FR49 | Demo Mode (pre-loaded replay trajectories) | MVP | Marketing -- every install is a demo |
| FR50 | One-click dataset upload (armOS Cloud / HuggingFace) | Growth | Cloud training revenue ($5-20/run) |
| FR51 | One-click policy download and deployment | Growth | Cloud training revenue |
| FR52 | Co-branded boot splash (configurable per partner) | Growth | Hardware partnerships ($3-5/unit) |
| FR53 | Partner quickstart URL in boot splash | Growth | Hardware partnerships |
| FR54 | "What's Next?" onboarding panel | MVP | Retention and upsell |
| FR55 | Opt-in telemetry consent on first boot | Growth | Data flywheel, usage metrics |
| FR56 | Anonymous hardware compatibility reporting | Growth | Hardware compatibility matrix |
| FR57 | Diagnostic result sharing (anonymized) | Growth | Improve default settings fleet-wide |
| FR58 | Telemetry dashboard (internal maintainer tool) | Growth/Vision | Operational visibility |
| FR59 | Dataset export to HuggingFace Hub (one-click) | Late MVP | Cloud training funnel |
| FR60 | armOS Cloud training submission from dashboard | Growth | Primary revenue stream |
| FR61 | Policy deployment from cloud | Growth | Primary revenue stream |
| FR62 | Profile export as .armos file | Growth | Profile ecosystem / network effect |
| FR63 | Profile import from file or URL | Growth | Profile ecosystem |
| FR64 | Community profile browser | Vision | Profile ecosystem |
| FR65 | Profile contribution from dashboard (GitHub PR) | Vision | Profile ecosystem |
| FR66 | Demo Mode launcher (with/without hardware) | MVP | Marketing |
| FR67 | Screen recording integration | Growth | User-generated content |
| FR68 | Reachy Mini / HopeJr profiles | Growth | HuggingFace partnership |
| FR69 | Pro tier feature gating | Vision | $10-15/mo individual revenue |

### MVP Additions (4 new FRs)

The following FRs should be added to the MVP scope:

1. **FR48 (Hackathon Mode)** -- Low implementation cost (it is a simplified first-run flow that skips advanced options). High distribution impact.
2. **FR49 (Demo Mode trajectories)** -- Record 2-3 SO-101 trajectories during development. Ship them as data files. Trivial to implement; powerful for marketing.
3. **FR54 ("What's Next?" panel)** -- A static screen with links. One hour of work. Prevents the "I teleoped, now what?" dropoff.
4. **FR66 (Demo Mode launcher)** -- A TUI button that triggers trajectory replay. Depends on FR49.

These four additions do not materially increase MVP scope (estimated 3-5 story points total) but directly enable the go-to-market strategy.

---

## 7. Open Questions for Founder

1. **Naming confirmed?** The PM review flagged "RobotOS" as problematic. The current PRD uses "armOS." Is this final? Domain registered? Trademark searched?

2. **Hackathon timeline.** When is the next LeRobot hackathon? If it is within 6 months, MVP must ship before it to capture the distribution opportunity. If it has already passed, we need an alternative launch event.

3. **Seeed Studio contact.** Do we have a warm intro to anyone at Seeed Studio? A cold partnership pitch is unlikely to succeed. The market research notes their $47M revenue and 252 employees -- we need to reach a product manager or developer relations lead, not a sales inbox.

4. **HuggingFace relationship.** Have we engaged the LeRobot maintainers? The PM review and business plan both depend on HuggingFace cooperation. Upstream PRs for sync_read retry and port flush patches would be the best opening move.

5. **Cloud training build vs. buy.** The business plan suggests Lambda Labs or vast.ai for GPU infrastructure. An alternative: partner with Modal or Replicate, who already have per-run pricing APIs. This could reduce time-to-market for cloud training from months to weeks.

---

*PRD enhancements proposed by John (Product Manager), informed by business plan, market research, and product validation findings. 2026-03-15.*
