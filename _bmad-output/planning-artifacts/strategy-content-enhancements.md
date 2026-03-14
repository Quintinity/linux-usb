# armOS Strategy and Content Enhancements

**Authors:** Mary (Analyst) and Paige (Tech Writer)
**Date:** 2026-03-15
**Based on:** vision.md, business-plan.md, market-research.md, product-validation.md, review-analyst.md, review-tech-writer.md

---

# PART I: STRATEGIC ENHANCEMENTS (Mary)

---

## 1. Competitive Positioning Matrix

### Detailed Feature Comparison

| Capability | armOS | Foxglove | ROS2 + MoveIt2 | LeRobot (bare) | phosphobot | NVIDIA Isaac |
|---|---|---|---|---|---|---|
| **Setup time** | <5 min (USB boot) | 15-30 min (install) | 4-8 hours | 1-3 hours | 30-60 min (their kit) | 2-4 hours (GPU required) |
| **Target hardware cost** | $0 (any x86 laptop) | $0 (any machine) | $0 (any machine) | $0 (any machine) | $995+ (their kits) | $500+ (needs NVIDIA GPU) |
| **Robot arm support** | SO-101 (MVP), Dynamixel (Growth) | N/A (viz only) | 50+ (URDF-based) | SO-101, Koch, Aloha | SO-100, SO-101, Unitree Go2 | Industrial arms |
| **Servo diagnostics** | Real-time voltage, temp, load, comms | Log replay only | No built-in for hobby servos | None | Basic status | Industrial-grade |
| **Data collection** | Built-in (LeRobot format) | No | Rosbag (different format) | Built-in (native) | Built-in | SIM-focused |
| **Cloud training** | Planned (Year 2) | No | No | HuggingFace Hub | PRO subscription | Omniverse |
| **Offline operation** | Full (after first boot) | Partial | Full | Full | Requires internet for cloud | Partial |
| **License** | Apache 2.0 (planned) | Freemium ($18-90/user/mo) | Apache 2.0 | Apache 2.0 | Proprietary + open agent | Proprietary |
| **Funding / Backing** | Bootstrap | $58M raised | OSRA (Alphabet/Intrinsic) | HuggingFace ($4.5B) | Y Combinator | NVIDIA |
| **GitHub stars** | N/A (pre-launch) | N/A (closed) | ~1.7K (MoveIt2) | ~22K | ~76 | N/A |
| **Primary user** | Hobbyist, educator, new researcher | Robotics engineer | Robotics engineer, researcher | ML researcher | Hobbyist, educator | Enterprise, researcher |
| **Key weakness** | Pre-launch, single maintainer | No robot control | Extreme complexity | No plug-and-play setup | Locked to their hardware, paid | GPU required, enterprise pricing |

### Positioning Summary

```
                        High Hardware Breadth
                               |
                   ROS2 + MoveIt2          NVIDIA Isaac
                               |
                               |
     High Complexity ----------+---------- Low Complexity
                               |
              LeRobot (bare)   |   armOS  <-- "it just works"
              phosphobot       |
                               |
               Foxglove (viz)  |
                        Low Hardware Breadth
```

**armOS owns the "low complexity, affordable hardware" quadrant.** No other product occupies it. Foxglove is visualization-only. phosphobot requires their kits. ROS2 requires a PhD-level tolerance for configuration. LeRobot requires a working Linux environment. armOS is the only product where you insert a USB stick and have a working robot in 5 minutes.

### Head-to-Head: armOS vs. phosphobot (the closest competitor)

| Dimension | armOS | phosphobot | Verdict |
|---|---|---|---|
| Price to start | Free (download ISO) | $995+ (buy their kit) | armOS wins |
| Hardware lock-in | None (BYOH) | Their kits preferred | armOS wins |
| VR teleoperation | No | Meta Quest support | phosphobot wins |
| Servo diagnostics | Deep (voltage, temp, load, comms) | Basic | armOS wins |
| Cloud training | Planned | Available now (PRO tier) | phosphobot wins (for now) |
| Community size | 0 (pre-launch) | 1,000+ claimed robots | phosphobot wins (for now) |
| Offline capability | Full | Internet required for cloud | armOS wins |
| Open source depth | Full OS + drivers + diagnostics | Open agent, closed platform | armOS wins |

**Strategic implication:** armOS competes on freedom (free, open, any hardware, offline) vs. phosphobot's convenience (integrated kit, VR, cloud). These are different value propositions for overlapping audiences. The risk is phosphobot going free/open -- monitor closely.

---

## 2. Partnership Pitch Deck Outline -- Seeed Studio First Email

### Subject Line

"Reduce SO-101 support tickets by 80% -- free software partnership proposal"

### Email Structure

**Paragraph 1 -- The Hook (their pain):**
"Every SO-101 kit you sell generates support tickets about brltty serial hijacking, servo calibration crashes, and LeRobot dependency hell. We know because we hit every one of those problems ourselves. We built armOS to fix them -- a bootable USB image that eliminates the entire setup process."

**Paragraph 2 -- The Offer (zero cost to them):**
"We would like to propose a partnership: Seeed Studio recommends armOS in SO-101 product documentation and retail listings. We handle all software support. This costs you nothing and directly reduces your customer support burden."

**Paragraph 3 -- The Demo (proof it works):**
"Here is a 90-second video showing a complete stranger going from powered-off laptop to robot teleoperation using armOS: [link]. No Linux knowledge. No terminal commands. Five minutes."

**Paragraph 4 -- The Ask (specific and small):**
"Could we schedule a 15-minute call to discuss? We are also happy to send you a pre-flashed USB stick for your team to evaluate."

**Paragraph 5 -- Growth Path (hint at bigger deal):**
"Longer term, we see an opportunity for co-branded 'armOS Edition' kits that include a pre-flashed USB stick -- similar to how Universal Robots and KUKA ship software with their industrial arms. But step one is just a documentation link."

### Pitch Deck Slides (for follow-up call)

| Slide | Content |
|---|---|
| 1. Title | armOS: The Missing Software for Robot Arms |
| 2. Problem | 3 stats: avg setup time (hours), top 5 LeRobot GitHub issues (all setup), support ticket categories |
| 3. Demo | Embedded 90-second video or live demo |
| 4. Solution | What armOS does in 5 bullet points |
| 5. Market | 22K LeRobot stars, 15K Discord members, 3-5K SO-101 arms in field |
| 6. Partnership model | Three tiers: (a) doc link (free), (b) co-branded page ($0), (c) bundled USB ($3-5/unit) |
| 7. Traction | GitHub stars, beta tester count, community feedback quotes |
| 8. Team | Bradley's background, the Surface Pro debugging story as credibility |
| 9. Ask | Documentation link now, bundled USB evaluation in 90 days |

### Key Talking Points for Seeed Studio

1. **Their incentive is support cost reduction.** Frame everything around fewer returns, fewer tickets, happier customers.
2. **Reference Universal Robots and KUKA** -- they already ship USB sticks with industrial robots. Seeed is bringing that model to the $220 price point.
3. **The SO-101 is their product, but the software experience is LeRobot's responsibility** -- and LeRobot does not ship a plug-and-play solution. armOS fills that gap.
4. **Quantify the pain:** "The top 5 LeRobot GitHub issues by comment count are all setup failures. Issue #923 alone has X comments."
5. **No exclusivity.** armOS works with Waveshare and other vendors too. Seeed gets first-mover advantage if they partner early.

---

## 3. Pricing Strategy

### Philosophy

**Free forever for the core. Pay for convenience and compute.**

armOS follows the "open core" model proven by GitLab, Grafana, and Arduino: the core product is free and open source, monetization comes from services and partnerships that provide value beyond what free users need.

### Tier Structure

| Tier | Price | What You Get | When It Launches |
|---|---|---|---|
| **Free (Community)** | $0 forever | Full armOS ISO, all robot profiles, all diagnostics, TUI dashboard, LeRobot integration, offline operation, community Discord support | MVP launch (Q3 2026) |
| **USB Stick (Convenience)** | $15-25 one-time | Pre-flashed USB drive shipped to your door. Identical software to free tier. You pay for the hardware and the convenience of not flashing it yourself. | MVP launch |
| **Cloud Training** | $5-20 per run | Upload your collected dataset, receive a trained policy. No GPU required. Pricing based on dataset size and model complexity. | Q1 2027 |
| **Education** | $50-200/seat/year | Fleet management, locked-down classroom mode, centralized profiles, student progress tracking, curriculum materials, priority support | Q2 2027 |
| **Enterprise** | $500-1,000/seat/year | Everything in Education plus: custom profiles, SLA support, usage analytics, dedicated Discord channel, on-site setup assistance | Q3 2027 |
| **Hardware Partnership** | $3-5/unit revenue share | Kit manufacturers include armOS USB or download link. Per-unit fee for bundled USBs. Free for documentation-only partnerships. | Q1 2027 |

### Pricing Principles

1. **Never charge for something the community can build.** The ISO image will always be free to download and flash yourself.
2. **Cloud training is the natural paywall.** Users collect data on $0 hardware (any laptop). Training requires GPUs they do not have. Paying $10 to avoid setting up a GPU cluster is a no-brainer.
3. **Education pricing must undercut alternatives.** A full classroom setup (20 SO-101 kits + 20 armOS seats) should cost under $6,000 total -- 10x cheaper than any comparable robotics lab.
4. **No feature gates on safety.** Diagnostics, voltage monitoring, overload protection -- these are always free. Gating safety features behind a paywall is unethical and would destroy community trust.
5. **Price increases come with advance notice.** Early adopters lock in pricing for 12 months.

### When to Start Charging

| Milestone | Action |
|---|---|
| MVP launch | Everything free. Sell USB sticks at cost + margin ($15-25). |
| 500 GitHub stars | Open GitHub Sponsors. Accept donations. |
| 1,000 users | Launch Cloud Training beta at $5/run (below cost, to validate demand). |
| First hardware partnership | Begin revenue share on bundled USBs. |
| 2,000 users | Launch Education tier. Raise Cloud Training to market rate ($10-20/run). |
| 5,000 users | Launch Enterprise tier. |

---

## 4. Community Growth Playbook -- First 90 Days

### Pre-Launch (Weeks -2 to 0)

| Day | Action | Goal |
|---|---|---|
| -14 | Record 90-second demo video (USB to teleop, no cuts, timer in corner) | Core marketing asset |
| -10 | Create GitHub repo with README + embedded demo video | Public presence |
| -7 | Set up Discord server with channels: #general, #setup-help, #show-your-setup, #bug-reports, #feature-requests, #contributors | Community hub |
| -5 | Create landing page with beta signup form | Email list |
| -3 | Recruit 5-10 alpha testers from LeRobot Discord (DM active members who post setup questions) | Pre-launch validation |
| -1 | Write "Show HN" post draft and tweets | Launch day content |

### Week 1: Launch

| Day | Action | Target Metric |
|---|---|---|
| Day 1 (Mon) | Post to Hacker News: "Show HN: I spent 40 hours debugging a robot arm, so I built an OS that does it in 5 minutes" | 50+ HN upvotes |
| Day 1 | Post to r/robotics, r/raspberry_pi, r/homelab | 20+ upvotes each |
| Day 1 | Post to LeRobot Discord #general with demo video | 50+ reactions |
| Day 1 | Tweet launch thread with demo video clip (15 seconds) | 100+ likes |
| Day 2 | Post to LeRobot GitHub Discussions | 10+ replies |
| Day 3 | Publish blog post 1: "How brltty steals your robot's serial ports (and how to fix it)" | SEO, 500+ views |
| Day 5 | Respond to every GitHub issue, Discord message, and Reddit comment personally | 100% response rate |
| Day 7 | Week 1 retrospective: count stars, signups, Discord members | Target: 100 stars, 50 Discord members |

### Weeks 2-4: Content Drumbeat

| Week | Content | Distribution |
|---|---|---|
| Week 2 | Blog post 2: "Why your SO-101 servos stutter (voltage sag explained)" | Blog, Dev.to, LeRobot Discord |
| Week 2 | Tutorial video 1: "SO-101 from unboxing to teleop with armOS" (5 min) | YouTube, Twitter/X |
| Week 3 | Blog post 3: "Building armOS: dev log #1" (transparent building-in-public post) | Blog, Hacker News |
| Week 3 | "Show Your Setup" gallery launch -- post first 3-5 community setups | Discord, Twitter/X |
| Week 4 | Tutorial video 2: "armOS diagnostics -- find out what is wrong with your servos" (3 min) | YouTube |
| Week 4 | Blog post 4: "The overload protection settings nobody tells you about" | Blog, Dev.to |

### Weeks 5-8: Community Activation

| Week | Action | Goal |
|---|---|---|
| Week 5 | First community call (Discord voice, 30 min) -- demo new features, take questions | 10+ attendees |
| Week 5 | Open "good first issue" labels on GitHub for robot profiles | First community PR |
| Week 6 | Contact 10 robotics YouTubers -- send USB sticks with a one-page "what this is" card | 2-3 unboxing/review videos |
| Week 6 | Write "How to contribute a robot profile" guide | Enable community contributions |
| Week 7 | Submit talk proposal to local robotics/maker meetup | In-person demo |
| Week 7 | Reach out to HuggingFace LeRobot team -- propose joint blog post | Distribution via HuggingFace channels |
| Week 8 | Second community call -- highlight community contributions | Reinforce contributor culture |

### Weeks 9-12: Growth Acceleration

| Week | Action | Goal |
|---|---|---|
| Week 9 | Email 5 university robotics professors with a "free classroom pilot" offer | 1 pilot commitment |
| Week 9 | Blog post 5: "armOS vs. manual LeRobot setup: a side-by-side comparison" | Conversion content |
| Week 10 | Contact Seeed Studio with partnership pitch (see Section 2) | Meeting scheduled |
| Week 10 | Launch "Robot of the Month" -- spotlight a community member's setup | Community engagement |
| Week 11 | Tutorial video 3: "Collect your first AI training dataset with armOS" | YouTube |
| Week 11 | Apply for first grant (NSF Cyberlearning or equivalent) | Funding pipeline |
| Week 12 | 90-day retrospective blog post: "armOS by the numbers -- our first 90 days" | Transparency, social proof |

### 90-Day Targets

| Metric | Conservative | Moderate | Stretch |
|---|---|---|---|
| GitHub stars | 200 | 500 | 1,000 |
| Discord members | 100 | 250 | 500 |
| Active users (booted + completed teleop) | 25 | 75 | 200 |
| Community-contributed robot profiles | 1 | 3 | 5 |
| YouTube tutorial views (total) | 1,000 | 5,000 | 15,000 |
| Email subscribers | 100 | 300 | 750 |
| University pilot commitments | 0 | 1 | 2 |

---

## 5. Risk Matrix

### Scoring Key

- **Probability:** 1 (Very unlikely) to 5 (Near certain)
- **Impact:** 1 (Minimal) to 5 (Fatal/project-ending)
- **Risk Score:** Probability x Impact. Red >= 15, Yellow 8-14, Green <= 7.

### Risk Register

| ID | Risk | Category | Probability (1-5) | Impact (1-5) | Score | Mitigation | Owner |
|---|---|---|---|---|---|---|---|
| R1 | **Maintainer burnout** (solo project, no funding) | Operational | 5 | 5 | **25** | Recruit contributors via low-barrier profile PRs. Pursue grant funding. Strict scope limits. Do not over-commit. | Founder |
| R2 | **USB boot fails on common hardware** (UEFI variations, Secure Boot, driver gaps) | Technical | 3 | 5 | **15** | Start HW compat testing in Sprint 4. Maintain public compat matrix. Target 90%+ on post-2016 x86 UEFI. | Founder |
| R3 | **phosphobot captures the market** before armOS launches | Market | 3 | 4 | **12** | Differentiate on free + BYOH + offline. Move fast. Monitor their releases weekly. | Founder |
| R4 | **LeRobot ships their own setup tool** (devcontainer, snap, or similar) | Market | 2 | 5 | **10** | Engage LeRobot team as collaborators. Upstream patches. If they ship a tool, pivot to "advanced diagnostics and fleet management" layer. | Founder |
| R5 | **Hardware partnerships take longer than expected** | Business | 4 | 3 | **12** | Do not depend on partnership revenue in Year 1. Sell USB sticks directly. Build community first. | Founder |
| R6 | **Persistent storage on live USB is unreliable** (casper-rw corruption on unclean shutdown) | Technical | 3 | 4 | **12** | Spike in Sprint 2: test 10 unclean shutdowns. If casper-rw fails, use BTRFS or separate data partition. | Founder |
| R7 | **LeRobot API breaks in a future version** | Technical | 3 | 3 | **9** | Pin to v0.5.0. Wrap all calls through bridge layer. Submit upstream patches. | Founder |
| R8 | **Support burden exceeds capacity** | Operational | 4 | 3 | **12** | Invest in self-service diagnostics (the product IS the support deflection tool). Empower community moderators. | Founder |
| R9 | **Education market is slow to adopt** | Market | 3 | 2 | **6** | Do not depend on education revenue in Year 1. Focus on hobbyists and researchers first. | Founder |
| R10 | **Name conflict or trademark issue with "armOS"** | Legal | 2 | 3 | **6** | Conduct trademark search before public launch. Register domain and GitHub org early. Have a backup name ready. | Founder |
| R11 | **Cloud training service has low margins** (GPU costs) | Business | 3 | 2 | **6** | Use spot instances and auto-scaling. Partner with Lambda Labs or Modal rather than building infra. Start with simple pricing. | Founder |
| R12 | **Servo protocol abstraction does not generalize to Dynamixel** | Technical | 2 | 3 | **6** | Before finalizing API, sketch a Dynamixel driver to validate the abstraction. 2 hours of research saves 2 weeks of refactoring. | Founder |
| R13 | **A well-funded competitor builds the same thing** | Market | 2 | 3 | **6** | Move fast, build community, accumulate profiles. Network effects from profiles are the best defense. | Founder |
| R14 | **Robot arm kits stall in popularity** | Market | 1 | 4 | **4** | Diversify beyond arms (mobile robots, grippers). Monitor Feetech and Dynamixel sales data. | Founder |

### Risk Heat Map

```
Impact  5 |  R4      R2,R1
        4 |  R14     R6,R3
        3 |  R10,R12,R13  R7  R8,R5
        2 |  R9      R11
        1 |
           +----+----+----+----+----
             1    2    3    4    5   Probability
```

### Top 3 Risks Requiring Immediate Action

1. **R1 (Burnout, score 25):** This is the existential risk. Mitigation: strict MVP scope, no feature creep, recruit one contributor within 30 days, pursue grant funding within 90 days.
2. **R2 (USB boot compatibility, score 15):** If the USB does not boot, nothing else matters. Mitigation: test on 5+ different laptops by Sprint 4. Publish results honestly.
3. **R3 (phosphobot, score 12) + R5 (slow partnerships, score 12):** These are linked -- if phosphobot moves fast and partnerships are slow, armOS loses its window. Mitigation: launch the demo video and GitHub repo before the MVP is done. Build community traction that de-risks the partnership conversation.

---

## 6. KPIs Dashboard -- Metrics from Day 1

### Primary KPIs (Track Weekly)

| Metric | Data Source | Day 1 Baseline | 30-Day Target | 90-Day Target | Why It Matters |
|---|---|---|---|---|---|
| **GitHub stars** | GitHub API | 0 | 100 | 500 | Top-line awareness metric. Partners and contributors look at this first. |
| **ISO downloads** | GitHub Releases download count | 0 | 50 | 300 | Actual interest (stars are vanity, downloads are intent). |
| **Boot success rate** | Opt-in telemetry or community reports | Unknown | 85%+ | 90%+ | If the USB does not boot, nothing else matters. |
| **Time to first teleop** | Opt-in telemetry or user surveys | Unknown | <10 min | <5 min | The core promise. SC1 from the PRD. |
| **Discord members** | Discord server stats | 0 | 50 | 250 | Community health and support capacity. |
| **Active users** (booted + completed teleop at least once) | Opt-in telemetry | 0 | 10 | 75 | True adoption, not just curiosity. |

### Secondary KPIs (Track Monthly)

| Metric | Data Source | 90-Day Target | Why It Matters |
|---|---|---|---|
| **Community PRs merged** | GitHub | 3+ | Community engagement and contributor pipeline |
| **Robot profiles contributed** | GitHub | 2+ | Ecosystem growth / network effect |
| **GitHub issues opened** | GitHub | 30+ | Users care enough to report problems (a GOOD signal early on) |
| **GitHub issues closed** | GitHub | 80%+ close rate | Responsiveness and quality signal |
| **Blog post views** | Blog analytics | 2,000+ total | Content marketing effectiveness |
| **YouTube views** | YouTube Studio | 3,000+ total | Visual content reach |
| **Beta signup emails** | Email list | 200+ | Future launch audience |
| **Unique visitors to docs site** | Analytics | 500+ | Documentation quality and discoverability |

### Leading Indicators (Track Monthly -- Predict Future Growth)

| Indicator | Source | What It Tells You |
|---|---|---|
| LeRobot GitHub stars growth rate | GitHub API | Is the overall market growing? (Currently ~500/month) |
| LeRobot Discord new members/month | Discord stats | Inflow of potential armOS users |
| SO-101 kit availability on Amazon/AliExpress | Manual check | Hardware supply = demand signal |
| Number of new LeRobot GitHub issues tagged "setup" or "installation" | GitHub search | Ongoing pain = ongoing demand for armOS |
| phosphobot GitHub stars and releases | GitHub API | Competitor momentum |
| University course syllabi mentioning SO-101 or LeRobot | Google Scholar / web search | Education market readiness |

### Dashboard Implementation

**Phase 1 (Week 1):** Manual spreadsheet updated weekly. Track GitHub stars, downloads, Discord members, and issues.

**Phase 2 (Month 2):** Simple script that pulls GitHub API data and Discord stats into a markdown file committed to the repo (public transparency).

**Phase 3 (Month 4+):** If opt-in telemetry is implemented, add boot success rate and time-to-teleop to the dashboard. Consider a simple Grafana instance if the data warrants it.

### Decision Triggers

| Metric State | Decision |
|---|---|
| <20 stars after 2 weeks | Reconsider positioning and messaging. Is the demo compelling enough? |
| <50 downloads after 30 days | The product is not reaching the audience. Increase distribution effort. |
| Boot success rate <70% | Pause feature work. Fix compatibility. This is a P0 blocker. |
| 0 community PRs after 60 days | The contribution workflow is too hard. Simplify the profile submission process. |
| 500+ stars by day 60 | Accelerate partnership outreach. The community traction de-risks the pitch. |
| phosphobot releases a free tier | Immediately differentiate on offline-first + diagnostics depth. Consider accelerating cloud training. |

---

# PART II: CONTENT AND DOCUMENTATION ENHANCEMENTS (Paige)

---

## 7. Launch Content Plan

### Content That Ships With MVP

| Content Piece | Format | Purpose | Owner | Status |
|---|---|---|---|---|
| **Demo video** (90 seconds) | Video (YouTube + embedded in README) | Primary marketing asset. Shows the core value prop in real time. | Founder | Must record pre-launch |
| **README.md** (rewritten) | Markdown | First impression for every GitHub visitor. 30-second understanding. | Tech Writer | Sprint 5-6 |
| **Getting Started: Your First Teleop** | Docs page | Golden-path tutorial. Boot to teleop. | Tech Writer | Sprint 5-6 |
| **Getting Started: Flashing the USB** | Docs page | Prerequisite for all users. | Tech Writer | Sprint 6 |
| **Getting Started: First Boot** | Docs page | What to expect on first boot. | Tech Writer | Sprint 6 |
| **Blog post 1:** "How brltty steals your robot's serial ports" | Blog | SEO, credibility, standalone value. Not a product pitch -- a genuinely useful debugging guide. | Founder | Launch week |
| **Blog post 2:** "Why your SO-101 servos stutter" | Blog | SEO, credibility. Voltage sag explained with oscilloscope screenshots if available. | Founder | Week 2 |
| **Profile schema reference** | Docs page | For users inspecting or customizing the SO-101 profile. | Tech Writer | Sprint 3 |
| **CLI reference** | Docs page (auto-generated) | Complete command reference from Click help strings. | Auto-gen | Sprint 6 |
| **Glossary** | Docs page | Standardized terminology for all audiences. | Tech Writer | Sprint 1, ongoing |
| **CHANGELOG** | Markdown | v0.1.0 release notes. | Founder | Sprint 6 |

### Content for First 30 Days Post-Launch

| Content Piece | Format | Purpose |
|---|---|---|
| **Blog post 3:** "Building armOS: dev log #1" | Blog | Transparency, building in public, attract contributors |
| **Tutorial video 1:** "SO-101 unboxing to teleop with armOS" | YouTube (5 min) | Visual learners, YouTube search traffic |
| **"Show Your Setup" gallery launch** | Discord channel + docs page | Social proof, community engagement |
| **Blog post 4:** "Overload protection settings nobody tells you about" | Blog | Deep technical content that builds authority |

### Content for Days 31-90

| Content Piece | Format | Purpose |
|---|---|---|
| **Tutorial video 2:** "armOS diagnostics explained" | YouTube (3 min) | Showcase the diagnostic moat |
| **Tutorial video 3:** "Collect your first AI training dataset" | YouTube (5 min) | Data collection workflow |
| **Blog post 5:** "armOS vs. manual LeRobot setup: side-by-side" | Blog | Conversion content, direct comparison |
| **Case study 1:** Alpha tester experience (interview + writeup) | Blog | Social proof |
| **"armOS for Educators" page** | Docs / landing page | Education market material (min specs, IT one-pager, cost estimate, sample syllabus) |
| **Blog post 6:** "90-day retrospective: armOS by the numbers" | Blog | Transparency, milestone marketing |

---

## 8. 90-Second Demo Video Script

### Concept

One continuous take. No narration. No music. Just ambient room sound, a timer in the corner, and clear text overlays. The silence is the point -- it lets the viewer focus on how fast and easy this is.

### Shot List

| Timestamp | Shot | Visual | Text Overlay |
|---|---|---|---|
| 0:00-0:05 | **Wide shot:** A table with a powered-off laptop, a disconnected SO-101 arm, and a USB stick. | Clean, well-lit workspace. Laptop closed. Arm motionless. USB stick next to laptop. | "armOS: USB boot to robot teleop" |
| 0:05-0:10 | **Close-up:** Hands pick up the USB stick and insert it into the laptop's USB port. | Clear view of USB going into port. | Timer starts: 0:00 |
| 0:10-0:15 | **Medium shot:** Hands open the laptop and press the power button. | Screen is black, then BIOS splash. | Timer: 0:05 |
| 0:15-0:25 | **Screen capture:** GRUB boot menu appears. armOS is auto-selected. Boot messages scroll. | Fast boot sequence. armOS logo appears. | Timer: 0:10 ... 0:20 |
| 0:25-0:35 | **Screen capture:** armOS TUI dashboard appears. "No hardware detected" message shown. | Clean TUI with status panel. | Timer: 0:20 ... 0:30 |
| 0:35-0:45 | **Close-up:** Hands plug the USB-serial cable from the SO-101 into the laptop's USB hub. | Physical connection being made. | Timer: 0:30 |
| 0:45-0:55 | **Screen capture:** TUI auto-detects the SO-101. "Feetech STS3215 controller detected. SO-101 profile loaded." Green status indicators appear. | Auto-detection in action. | Timer: 0:35 ... 0:50. Overlay: "Auto-detected. Zero configuration." |
| 0:55-1:05 | **Screen capture:** User selects "Calibrate" from TUI menu. Calibration runs (progress bar). Completes. | Calibration is fast and automatic. | Timer: 0:50 ... 1:00 |
| 1:05-1:15 | **Screen capture:** User selects "Teleop" from TUI menu. Telemetry panel shows live servo data (voltage, position, load). | Real-time data flowing. | Timer: 1:00 ... 1:10 |
| 1:15-1:25 | **Wide shot:** The SO-101 follower arm is moving, mirroring the leader arm being manipulated by hand. Both arms visible, laptop screen in background showing telemetry. | The money shot. Robot is alive and responsive. | Timer: 1:10 ... 1:20. Overlay: "From USB stick to this." |
| 1:25-1:30 | **Fade to black.** | | "armOS. Boot from USB. Detect hardware. Start building." |
| 1:30 | **End card:** GitHub URL, website URL. | | "github.com/[org]/armOS -- Free and open source." |

### Production Notes

- **Record on a non-Surface laptop** (something generic-looking -- a ThinkPad or Dell Latitude). The demo must not look hardware-specific.
- **The timer is the hero.** Keep it large (top-right corner), counting seconds. The entire video is an argument about time.
- **No jump cuts.** The credibility comes from the continuous take. If something fails, restart. The audience must believe this is real.
- **Record multiple takes.** Pick the one where the total time is under 3 minutes (actual) and cut the waiting (boot, calibration) to fit 90 seconds. Use 2x speed during boot with a "2x" indicator.
- **Resolution:** 1080p minimum. 4K preferred. Screen text must be legible.
- **Thumbnail:** Split image -- left side: tangled cables and terminal errors (the old way), right side: clean USB stick and working robot (armOS). Text: "5 minutes."

---

## 9. README Rewrite for armOS

```markdown
# armOS

> Boot from USB. Detect hardware. Start building.

armOS is a free, open-source operating system that turns any x86 laptop into a robot arm
control station. Insert a USB stick, power on, and go from zero to robot teleoperation
in under 5 minutes -- no Linux expertise required.

[Watch the demo (90 seconds)](link-to-video) | [Download](link-to-releases) | [Documentation](link-to-docs) | [Discord](link-to-discord)

## The Problem

Setting up a computer to control a robot arm takes hours. You need the right Linux
distribution, the right Python version, the right kernel drivers, the right udev rules,
the right servo firmware, and the right calibration. One wrong step and you are debugging
serial port conflicts instead of building robots.

## The Solution

armOS is a complete, pre-configured Linux environment on a bootable USB drive. It includes
everything you need:

- **Hardware auto-detection** -- Plug in your servo controller and armOS identifies it,
  loads the right profile, and configures communication automatically.
- **Built-in diagnostics** -- Real-time servo voltage, temperature, load, and communication
  monitoring. When something goes wrong, armOS tells you what and why.
- **Teleoperation** -- Leader-follower control out of the box. Move the leader arm and
  the follower mirrors it.
- **Data collection** -- Record demonstration episodes in LeRobot format for AI training.
- **TUI dashboard** -- A terminal interface for calibration, teleoperation, diagnostics,
  and data collection. No terminal commands needed.
- **Offline operation** -- Everything works without an internet connection after first boot.

## Quick Start

1. **Download** the latest ISO from [Releases](link-to-releases).
2. **Flash** to a USB drive (8GB+) using [balenaEtcher](https://etcher.balena.io)
   or [Rufus](https://rufus.ie).
3. **Boot** from USB (press F12/F2/Del at startup to access boot menu).
4. **Connect** your robot arm via USB.
5. **Follow** the TUI prompts to calibrate and start teleoperating.

Full setup guide: [Getting Started](link-to-docs/getting-started)

## Supported Hardware

| Robot Arm | Servo Protocol | Status |
|-----------|---------------|--------|
| SO-101 (Seeed Studio, Waveshare) | Feetech STS3215 | Supported (v0.1) |
| Koch v1.1 | Dynamixel XL330 | Planned (v0.5) |
| Custom builds | Feetech STS series | Supported via profiles |

Tested on: ThinkPad T480, Dell Latitude 5520, HP ProBook 450, Surface Pro 7.
[Full compatibility matrix](link-to-docs/compatibility)

## Screenshots

[TUI dashboard screenshot placeholder]

[Diagnostic output screenshot placeholder]

## How It Works

armOS is a pre-built Ubuntu 24.04 image with the entire robotics stack pre-installed:
Linux kernel with USB-serial drivers, Python 3.12, LeRobot 0.5.0, and all dependencies.
Robot profiles (YAML files) describe the hardware configuration for each supported arm.
On boot, armOS detects connected hardware, matches it to a profile, and presents the
TUI dashboard.

## Contributing

We welcome contributions, especially new robot profiles. If you have a robot arm working
with armOS, submitting a profile helps everyone who owns that hardware.

- [How to contribute a robot profile](link-to-docs/contributing/adding-a-robot-profile)
- [How to add a servo protocol plugin](link-to-docs/contributing/adding-a-servo-protocol)
- [Development setup](link-to-docs/contributing/development-setup)

## Community

- [Discord](link-to-discord) -- Setup help, show your builds, feature requests
- [GitHub Discussions](link-to-discussions) -- Long-form Q&A and proposals
- [Blog](link-to-blog) -- Tutorials, dev logs, and debugging guides

## License

Apache 2.0. See [LICENSE](LICENSE).

---

*armOS: the Android of robot arms.*
```

---

## 10. Getting Started Guide Outline

### Page: getting-started/flashing.md

```
# Flashing the armOS USB Drive

## What You Need
- USB drive (8GB minimum, USB 3.0 recommended)
- A computer with internet access (to download the ISO)
- Flashing software: balenaEtcher (recommended) or Rufus (Windows)

## Step 1: Download the ISO
[Screenshot: GitHub Releases page with download button highlighted]
- Link to latest release
- Note file size (~4GB)
- Verify checksum (SHA256 provided)

## Step 2: Flash the USB Drive
### Using balenaEtcher (all platforms)
[Screenshot: Etcher with "Select Image" highlighted]
[Screenshot: Etcher with "Select Target" highlighted]
[Screenshot: Etcher flashing in progress]
[Screenshot: Etcher "Flash Complete" message]

### Using Rufus (Windows)
[Screenshot: Rufus settings for ISO mode]

## Step 3: Verify the Flash
- Safely eject the USB drive
- Re-insert it
- You should see a drive labeled "ARMOS"

## Troubleshooting
- "The drive is not bootable" -- ensure you selected ISO mode, not DD mode
- Etcher reports write errors -- try a different USB drive
- Flash takes more than 10 minutes -- use a USB 3.0 port and drive
```

### Page: getting-started/first-boot.md

```
# First Boot

## Entering the Boot Menu
[Screenshot: typical BIOS boot menu key prompt]
- Common keys by manufacturer:
  - Dell: F12
  - Lenovo/ThinkPad: F12
  - HP: F9
  - ASUS: F8 / Esc
  - Surface: Volume Down + Power
- Select the USB drive from the boot menu

## What You Will See
### GRUB Menu
[Screenshot: GRUB with armOS option highlighted]
- armOS is auto-selected after 5 seconds
- Press Enter to boot immediately

### Boot Sequence
[Screenshot: boot messages scrolling]
- Takes 30-90 seconds depending on hardware
- You may see driver loading messages -- this is normal

### armOS TUI Dashboard
[Screenshot: TUI dashboard on first boot, no hardware connected]
- The main menu appears
- Status panel shows "No hardware detected"
- You are ready to connect your robot

## Troubleshooting
- Screen stays black after selecting USB -- try disabling Secure Boot in BIOS
- Boot hangs at a specific message -- note the message and report on Discord
- TUI does not appear -- press Ctrl+Alt+F1 to switch to the console
```

### Page: getting-started/connecting-hardware.md

```
# Connecting Your Robot Arm

## Hardware Connection Diagram
[Diagram: laptop -> USB hub -> USB-serial adapter -> leader arm]
[Diagram: laptop -> USB hub -> USB-serial adapter -> follower arm]
[Diagram: laptop -> USB hub -> USB camera(s)]

## Step 1: Connect the USB-Serial Adapters
[Photo: USB-serial adapter with servo bus cable]
- Plug leader arm's adapter into any USB port
- Plug follower arm's adapter into another USB port
- armOS auto-detects both -- no need to specify which is which

## Step 2: Power the Servo Bus
[Photo: power supply connected to servo bus]
- Connect 7.4V power supply to each arm's servo bus
- LED on the USB-serial adapter should light up
- Servos should hold position (slight resistance when you push them)

## Step 3: Verify Detection
[Screenshot: TUI showing "2 Feetech controllers detected"]
- armOS displays detected hardware in the status panel
- Green = detected and healthy
- Yellow = detected but needs attention (see diagnostics)
- Red = communication error

## Step 4 (Optional): Connect Cameras
- Plug USB cameras into available ports
- armOS detects V4L2 cameras automatically
- Camera feeds appear in the data collection view

## Troubleshooting
- "No hardware detected" after plugging in -- try a different USB port
- Only one arm detected -- check the USB-serial adapter LED
- Servos are limp (no holding torque) -- check the 7.4V power supply connection
```

### Page: getting-started/your-first-teleop.md

```
# Your First Teleoperation Session

Estimated time: 5 minutes from boot.

## Prerequisites
- armOS booted (see First Boot)
- Robot arm connected and detected (see Connecting Hardware)

## Step 1: Calibrate
[Screenshot: TUI calibration menu]
- Select "Calibrate" from the main menu
- Follow the on-screen prompts to move each joint to its limits
- Calibration takes ~60 seconds
[Screenshot: calibration complete with green checkmarks]

## Step 2: Start Teleoperation
[Screenshot: TUI teleop menu]
- Select "Teleop" from the main menu
- The follower arm will mirror the leader arm's movements
[Screenshot: telemetry panel showing live data]

## Step 3: Explore the Telemetry Panel
- Servo positions (real-time)
- Voltage per servo
- Load per servo
- Communication health (packets/sec, error rate)

## Step 4: Stop and Save
- Press Esc to stop teleoperation
- Servos will hold their last position briefly, then relax

## Next Steps
- [Run diagnostics](link) to check servo health
- [Collect training data](link) for AI policy learning
- [Customize your robot profile](link) to tune settings

## Troubleshooting
- Follower arm moves jerkily -- check the voltage panel (should be >7.0V under load)
- One servo does not respond -- run diagnostics to identify the faulty servo
- "Communication timeout" error -- unplug and replug the USB-serial adapter
```

---

## 11. Contributing Guide Outlines

### contributing/adding-a-robot-profile.md

```
# How to Contribute a Robot Profile

A robot profile is a YAML file that describes your robot's hardware configuration.
When you contribute a profile, every armOS user with the same hardware benefits.

## What Is a Robot Profile?

A robot profile contains:
- Robot name and description
- Servo protocol and bus configuration
- Joint definitions (name, ID, limits, direction)
- Default calibration hints
- Recommended protection thresholds (temperature, voltage, load)
- Camera configuration (if applicable)

## Prerequisites
- A working armOS setup with your robot arm
- Completed calibration
- Basic familiarity with YAML syntax

## Step 1: Export Your Current Configuration
    $ robotos profile export my-robot.yaml
[Example output: annotated YAML file]

## Step 2: Edit the Profile
- Review each field
- Add descriptive names for joints
- Verify servo IDs match your wiring
- Set conservative protection thresholds
[Annotated YAML example with comments explaining each field]

## Step 3: Test the Profile
    $ robotos profile validate my-robot.yaml
    $ robotos profile load my-robot.yaml
    $ robotos teleop    # Verify everything works

## Step 4: Submit a Pull Request
- Fork the armOS repository
- Add your profile to profiles/community/
- Add an entry to the hardware compatibility table in the README
- Submit a PR with:
  - Profile YAML file
  - Photo of your setup (optional but encouraged)
  - Brief description of the hardware

## Profile Review Criteria
- All servos have correct IDs and direction
- Protection thresholds are set (not left at defaults)
- Profile validates without errors
- Calibration hints are reasonable
- Description is clear and helpful

## CI Validation
When you open a PR, CI automatically:
- Validates YAML syntax
- Checks schema compliance
- Verifies no duplicate servo IDs
- Runs a simulated load of the profile
```

### contributing/adding-a-servo-protocol.md

```
# How to Add a Servo Protocol Plugin

armOS uses a plugin architecture for servo communication protocols.
This guide walks through implementing support for a new servo protocol.

## Architecture Overview
[Diagram: Plugin Manager -> Protocol Registry -> Your Plugin -> Hardware]
- All plugins implement the ServoProtocol abstract base class
- Plugins are auto-discovered via Python entry points
- Each plugin handles one protocol family (e.g., Feetech STS, Dynamixel Protocol 2.0)

## Prerequisites
- Python 3.12
- Development setup (see development-setup.md)
- Servo protocol datasheet or documentation
- Physical hardware for testing

## Step 1: Create the Plugin File
    src/robotos/plugins/my_protocol.py

## Step 2: Implement the ServoProtocol ABC
Required methods:
- discover() -- Scan the bus and return detected servo IDs
- ping(servo_id) -- Check if a specific servo responds
- read_position(servo_id) -- Read current position
- write_position(servo_id, position) -- Command a position
- sync_read(servo_ids, register) -- Batch read from multiple servos
- sync_write(servo_ids, register, values) -- Batch write to multiple servos
- read_register(servo_id, register, length) -- Raw register read
- write_register(servo_id, register, data) -- Raw register write

Optional methods:
- read_voltage(servo_id) -- Read supply voltage
- read_temperature(servo_id) -- Read internal temperature
- read_load(servo_id) -- Read current load
- set_torque(servo_id, enable) -- Enable/disable torque

[Code skeleton with docstrings for each method]

## Step 3: Register the Plugin
Add entry point in pyproject.toml:
    [project.entry-points."robotos.servo_protocols"]
    my_protocol = "robotos.plugins.my_protocol:MyProtocolPlugin"

## Step 4: Write Tests
- Unit tests with mocked serial communication
- Integration tests (require physical hardware, marked with @pytest.mark.hardware)

## Step 5: Submit a PR
- Plugin code with full docstrings
- Unit tests (required)
- Integration test (optional, will be run by maintainers with hardware)
- Updated servo-protocols.md reference page
- Example robot profile using the new protocol
```

---

## 12. Glossary of Terms

Standardized definitions for use across all armOS documents, documentation, and marketing materials.

| Term | Definition | Context |
|---|---|---|
| **armOS** | A bootable USB operating system for controlling robot arms. Pronounced "arm-oh-ess." | Product name. Always lowercase "arm," uppercase "OS." |
| **Robot profile** | A YAML configuration file that describes a complete robot setup: servo IDs, joint limits, calibration data, protection thresholds, and camera configuration. armOS loads the appropriate profile when hardware is detected. | Core concept. Never abbreviate to just "profile" in user-facing docs (too ambiguous). |
| **Servo** | A smart actuator with built-in position feedback, used as a joint in a robot arm. Not the same as an RC hobby servo -- armOS servos communicate digitally over a serial bus and report position, load, voltage, and temperature. | Distinguish from RC servos in introductory material. |
| **Servo bus** | A half-duplex serial communication line connecting multiple servos in a daisy chain. Each servo has a unique ID. Commands and responses share a single wire. | Technical term that appears in error messages and diagnostics. |
| **USB-serial adapter** | A small circuit board (typically CH340, FTDI, or CP2102 chipset) that converts USB to the TTL serial signal used by the servo bus. The green PCB that came with your robot kit. | Users see the physical hardware but may not know its name. |
| **Leader arm** | The robot arm manipulated by a human operator during teleoperation. Its joint positions are read and sent to the follower arm. | Core interaction concept. |
| **Follower arm** | The robot arm that mirrors the leader arm's movements during teleoperation. It receives position commands and moves to match the leader. | Core interaction concept. |
| **Teleoperation (teleop)** | Controlling a robot arm remotely by physically moving a leader arm. The follower arm mirrors the leader's movements in real time. | The primary use case. Often abbreviated to "teleop" in the TUI and CLI. |
| **Calibration** | The process of recording each servo's minimum and maximum positions to establish the valid range of motion. Required once per robot (or after hardware changes). | Users must calibrate before teleop or data collection. |
| **Episode** | A single recorded demonstration: a time series of servo positions and (optionally) camera frames. Multiple episodes make up a dataset. | LeRobot terminology. Used in data collection. |
| **Dataset** | A collection of episodes used to train an AI policy. Stored in LeRobot/HuggingFace format. | LeRobot terminology. |
| **Policy** | A trained AI model that maps sensor observations (joint positions, camera images) to robot actions (joint commands). Trained from datasets of human demonstrations. | Used when discussing AI training and inference. |
| **HAL (Hardware Abstraction Layer)** | The software layer that translates armOS commands into servo-protocol-specific communication. Allows armOS to support multiple servo protocols through a common interface. | Technical/contributor term. Not used in user-facing docs. |
| **Servo protocol plugin** | A software module that implements communication with a specific servo protocol family (e.g., Feetech STS, Dynamixel Protocol 2.0). Plugged into the HAL via a standard interface. | Technical/contributor term. |
| **Overload** | A servo safety mode that disables torque when the motor is under excessive mechanical load. Prevents motor damage but causes the joint to go limp. Triggered when load exceeds the protection threshold. | Users will encounter this. Diagnostics explain it. |
| **Protection threshold** | Configurable safety limits for servo temperature, voltage, and load. When a threshold is exceeded, the servo enters a protective mode (e.g., overload). Set in the robot profile. | Critical for hardware safety. |
| **Sync read / sync write** | Batch communication operations that read from or write to multiple servos in a single bus transaction. More efficient than individual reads/writes. Appears in error messages as "sync_read." | Technical term that appears in error messages. |
| **V4L2 (Video for Linux 2)** | The Linux kernel API for camera access. armOS uses V4L2 to detect and capture from USB cameras. | Users may see this in camera-related logs or errors. |
| **UEFI (Unified Extensible Firmware Interface)** | The modern replacement for BIOS. Controls how a computer boots. Users interact with UEFI to select the USB drive as the boot device. | Users need to access UEFI/BIOS to boot from USB. |
| **udev** | The Linux device manager that handles hardware detection. armOS uses udev rules to configure permissions and identify servo controllers when plugged in. | Technical term visible in logs. Users never need to edit udev rules directly. |
| **TUI (Terminal User Interface)** | The text-based dashboard that armOS presents after boot. Provides menus for calibration, teleoperation, diagnostics, and data collection without requiring command-line knowledge. | The primary user interface in v0.1. |
| **ISO image** | The build artifact -- a disk image file (.iso) that contains the complete armOS operating system. Flashed to a USB drive to create a bootable armOS installation. | Used in download and flashing instructions. |
| **Live USB** | A USB drive containing a bootable operating system (like armOS) that runs entirely from the USB without modifying the host computer's hard drive. | Explains why armOS is safe to try -- it does not touch your existing OS. |
| **brltty** | A Linux daemon for braille displays that conflicts with CH340 USB-serial adapters. armOS removes brltty to prevent it from hijacking servo controller connections. | The single most common setup failure in manual LeRobot installation. armOS eliminates it. |
| **casper-rw** | The persistence layer used by Ubuntu live USBs to save changes across reboots. armOS uses this (or an alternative) to persist calibration data and user settings. | Technical implementation detail. Users see "your settings are saved." |

---

## 13. API Documentation Structure

### Approach

Auto-generated from Google-style docstrings using `mkdocstrings` with manual narrative pages for key concepts. The API docs serve contributors and advanced users, not beginners.

### Structure

```
docs/reference/api/
  index.md                      # API overview, how to import, versioning policy
  core/
    robot_profile.md            # RobotProfile Pydantic model -- the schema everything revolves around
    hardware_manager.md         # HardwareManager -- detection, connection lifecycle
    calibration.md              # CalibrationRunner, CalibrationData
  servo/
    protocol.md                 # ServoProtocol ABC -- THE extension point, documented exhaustively
    feetech.md                  # FeetechPlugin -- reference implementation
    registry.md                 # ProtocolRegistry -- discovery and loading
  diagnostics/
    runner.md                   # DiagnosticRunner -- how to run checks
    checks.md                   # Built-in HealthCheck implementations
    telemetry.md                # TelemetryStream -- real-time monitoring interface
  teleop/
    controller.md               # TeleopController -- the read-write loop
    safety.md                   # SafetyWatchdog -- limits enforcement
  data/
    recorder.md                 # EpisodeRecorder -- data collection interface
    dataset.md                  # DatasetManager -- episode storage and export
  cli/
    commands.md                 # Auto-generated from Click decorators via mkdocs-click
```

### Documentation Standards for API Pages

Each auto-generated API page should include:

1. **Module docstring** -- One paragraph explaining what this module does and when a developer would use it.
2. **Class docstring** -- Purpose, usage example, and relationship to other classes.
3. **Method docstrings** -- Google-style with Args, Returns, Raises, and Example sections.
4. **Type annotations** -- All public methods fully type-annotated (enforced by mypy in CI).

### Key Interfaces to Document Thoroughly

These are the extension points -- contributors will read these most:

1. **ServoProtocol ABC** -- The most important interface. Every method needs a full docstring with argument descriptions, return types, exception behavior, timing constraints, and a usage example. Include a "How to implement" tutorial link.

2. **RobotProfile Pydantic model** -- The schema that defines a robot. Every field needs a description, valid range, default value explanation, and example. Include a "How to create a profile" tutorial link.

3. **HealthCheck interface** -- How to write a custom diagnostic check. Include examples of voltage check, communication check, and temperature check.

4. **TelemetryStream** -- How to subscribe to real-time servo data. Include a minimal consumer example.

### Versioning and Stability

| API Surface | Stability | Policy |
|---|---|---|
| CLI commands and flags | Stable from v0.1 | Breaking changes only in minor versions with deprecation warnings |
| Robot profile YAML schema | Stable from v0.1 | Additive changes only. Old profiles must always load. |
| ServoProtocol ABC | Stable from v0.5 | May change during 0.1-0.4 as the abstraction is validated |
| Internal classes | Unstable | May change without notice. Not documented in public API docs. |

---

# APPENDIX: Cross-Reference to Existing Recommendations

This document builds on the 32 recommendations (R1-R32) from the analyst review and the action items from the tech writer review. The table below maps sections of this document to those original recommendations.

| This Document Section | Addresses |
|---|---|
| 1. Competitive Matrix | R3 (2x2 matrix), R4 (Foxglove/rerun decision) |
| 2. Seeed Studio Pitch | R8 (hardware partnerships), R24 (HuggingFace outreach), R25 (YouTuber outreach) |
| 3. Pricing Strategy | R9 (cloud training monetization), R10 (grants) |
| 4. Community Playbook | R11 (Discord), R12 (Show Your Setup), R13 (tutorials), R14 (profile contributions), R15 (star targets) |
| 5. Risk Matrix | Business plan Section 10 risks, product validation Section 9 risks, consolidated and scored |
| 6. KPIs Dashboard | R2 (leading indicators), R31/R32 (telemetry) |
| 7. Launch Content Plan | Tech writer Sprint 6 deliverables, expanded with post-launch content |
| 8. Demo Video Script | Business plan Section 6.1 flagship content, product validation Section 8 minimum viable demo |
| 9. README Rewrite | Tech writer Part 5 specification, implemented in full |
| 10. Getting Started Guide | Tech writer Part 2.1 docs structure, fleshed out with screenshot placeholders |
| 11. Contributing Guides | Tech writer Part 3 deferred deliverables, outlined for Growth phase |
| 12. Glossary | Tech writer Part 6 term list, expanded with definitions |
| 13. API Docs Structure | Tech writer Part 2.3 API strategy, expanded with stability policy |

---

*Strategy and content enhancements for armOS -- prepared by Mary (Analyst) and Paige (Tech Writer), 2026-03-15.*
