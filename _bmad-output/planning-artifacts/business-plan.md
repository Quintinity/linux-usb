# armOS Business Plan

**Date:** 2026-03-15
**Author:** Bradley
**Version:** 1.0

---

## 1. Executive Summary

armOS is a bootable USB operating system purpose-built for controlling robot arms. Users plug the USB into any x86 laptop, boot it, connect their robot hardware, and have a working robot control station in minutes -- no Linux expertise, no manual configuration, no internet required.

The robotics hobbyist and education markets are growing rapidly. The global educational robotics market is projected to reach $5.8B by 2030. Sub-$500 robot arm kits (SO-101, Koch, Aloha-style) are proliferating, driven by the embodied AI wave from Google DeepMind, Tesla Optimus, and Figure AI. But every one of these kits ships with a multi-hour, failure-prone setup process that requires deep Linux and servo protocol knowledge.

armOS eliminates that setup entirely. It is the "Arduino IDE of robot arms" -- the missing software layer that makes affordable robot hardware accessible to everyone.

**The ask:** $150K in seed funding to deliver the MVP (SO-101 support), launch the open-source community, and secure the first hardware partnership within 12 months.

---

## 2. Problem and Solution

### The Problem

Setting up a computer to control a robot arm today requires:

- **Hours of manual Linux configuration.** Kernel drivers, udev rules, serial port permissions, Python virtual environments, dependency resolution -- each step is a potential failure point.
- **Deep domain knowledge.** Servo communication protocols (Feetech, Dynamixel), USB-serial adapters, voltage requirements, overload protection tuning -- none of this is documented in one place.
- **No visibility when things break.** Servo stuttering? Could be a power supply issue, a communication timeout, an overload protection trip, or a firmware bug. Users have no diagnostic tools and no way to distinguish between these failure modes.
- **No portability.** A setup that works on one machine does not transfer to another. Educators cannot distribute reproducible environments. Researchers waste days re-creating setups on new hardware.

Our own experience setting up an SO-101 on a Surface Pro 7 validated every one of these pain points. It took multiple days and uncovered dozens of failure modes: brltty hijacking serial ports, power supply sag causing servo stuttering, sync_read communication failures requiring custom retry patches, EEPROM protection settings needing per-servo tuning.

### The Solution

armOS is a pre-built, bootable USB image that contains:

1. **A fully configured Linux environment** with all robotics dependencies pre-installed.
2. **Hardware auto-detection** that identifies connected servo controllers, cameras, and sensors on plug-in.
3. **Robot profiles** -- YAML files describing complete robot configurations -- that auto-apply calibration, protection settings, and teleoperation configs.
4. **A built-in diagnostic suite** that monitors servo voltage, temperature, load, and communication health in real time, with actionable error messages.
5. **A terminal UI dashboard** for calibration, teleoperation, data collection, and diagnostics -- no terminal commands required.
6. **LeRobot integration** for AI training data collection, compatible with HuggingFace datasets.

The result: boot to working robot teleoperation in under 5 minutes, on any x86 laptop, with zero prior Linux experience.

---

## 3. Business Model Options

armOS follows an open-core strategy: the core OS and robot control software are open source (Apache 2.0), while revenue comes from services, partnerships, and enterprise features built on top.

### 3.1 Open Source Core + Paid Support and Consulting

The base armOS image, robot profiles, servo drivers, diagnostic suite, and TUI dashboard are fully open source. Revenue comes from:

- **Paid support contracts** for institutions deploying armOS at scale (universities, corporate R&D labs).
- **Custom integration consulting** for hardware manufacturers who want armOS profiles for their products.
- **Priority bug fixes and feature requests** for paying customers.

**Target:** $500-2,000/year per institutional customer. Realistic at 10+ institutions by Year 2.

### 3.2 Hardware Partnerships

Pre-loaded USB sticks sold bundled with robot arm kits. The partnership model:

- **Kit manufacturers** (Seeed Studio, Waveshare, Feetech resellers) include an armOS USB stick with their kits, or recommend armOS in their documentation and retail listings.
- **Revenue share:** $3-5 per USB stick included in a kit, or a flat licensing fee for "Powered by armOS" branding.
- **Pre-flashed USB sticks** sold directly through the armOS website or Amazon for $15-25 (cost of USB drive + margin).

**Target partners:** Seeed Studio (1M+ customer base, already sells robotics kits), Waveshare (growing robot arm line), Feetech (servo manufacturer, direct interest in reducing their support burden).

### 3.3 Cloud Training Service

Users collect demonstration data locally on armOS (free, offline), then upload datasets to the armOS cloud for GPU-accelerated policy training.

- **Pricing:** $5-20 per training run depending on dataset size and model complexity.
- **Value proposition:** Users cannot train models locally (armOS runs on Intel integrated graphics with no GPU). The cloud service closes the loop: collect data on armOS, train in the cloud, download the trained policy, run inference on armOS.
- **Technical implementation:** Managed GPU cluster (initially rented from Lambda Labs or vast.ai) running LeRobot training pipelines. Users upload via the armOS dashboard; results are returned as downloadable policy files.

**Target:** 500+ training runs/month by Year 2 at an average of $10/run = $5,000/month.

### 3.4 Enterprise and Education Licensing

Fleet management features for institutions running multiple armOS stations:

- **Classroom mode:** Locked-down configuration, centralized profile management, student progress tracking.
- **Fleet deployment:** Clone configured USB images across dozens of stations with centralized settings.
- **Usage analytics dashboard:** Track which stations are active, which hardware is connected, aggregate diagnostic data.
- **Curriculum materials:** Lesson plans, lab exercises, and assessment tools for robotics courses.

**Pricing:** $50-200/seat/year for education, $500-1,000/seat/year for enterprise.

### 3.5 Marketplace for Robot Profiles and Plugins

A curated marketplace where:

- **Hardware manufacturers** publish official robot profiles (free or paid).
- **Community members** sell advanced profiles with tuned calibrations, custom diagnostic routines, or specialized teleoperation configurations.
- **Plugin developers** sell servo protocol drivers, sensor integrations, or application-specific extensions.

**Revenue model:** 20-30% commission on paid listings. Free listings drive ecosystem growth.

**Target:** Launch marketplace in Year 2 once the community has sufficient scale.

---

## 4. Revenue Projections

All figures in USD. Assumes MVP launches in Q3 2026.

### Year 1 (2026-2027) -- Foundation

| Revenue Stream | Conservative | Moderate | Aggressive |
|----------------|-------------|----------|------------|
| Pre-flashed USB sales (direct) | $2,000 | $8,000 | $20,000 |
| Hardware partnership revenue share | $0 | $5,000 | $15,000 |
| Consulting and custom integration | $5,000 | $15,000 | $30,000 |
| Cloud training service | $0 | $0 | $5,000 |
| Grants (NSF, educational) | $0 | $25,000 | $50,000 |
| GitHub Sponsors / donations | $1,000 | $3,000 | $5,000 |
| **Total Year 1** | **$8,000** | **$56,000** | **$125,000** |

Year 1 is about community building and validation, not revenue. The conservative scenario assumes the project is self-funded; the aggressive scenario assumes one grant and one hardware partnership close.

### Year 2 (2027-2028) -- Growth

| Revenue Stream | Conservative | Moderate | Aggressive |
|----------------|-------------|----------|------------|
| Pre-flashed USB sales (direct) | $10,000 | $30,000 | $75,000 |
| Hardware partnership revenue share | $10,000 | $40,000 | $100,000 |
| Cloud training service | $15,000 | $60,000 | $150,000 |
| Education licensing | $10,000 | $50,000 | $120,000 |
| Consulting | $15,000 | $30,000 | $50,000 |
| Grants | $25,000 | $50,000 | $100,000 |
| Marketplace (late Year 2) | $0 | $5,000 | $20,000 |
| **Total Year 2** | **$85,000** | **$265,000** | **$615,000** |

### Year 3 (2028-2029) -- Scale

| Revenue Stream | Conservative | Moderate | Aggressive |
|----------------|-------------|----------|------------|
| Hardware partnerships | $30,000 | $100,000 | $300,000 |
| Cloud training service | $50,000 | $200,000 | $500,000 |
| Education and enterprise licensing | $40,000 | $150,000 | $400,000 |
| Marketplace | $10,000 | $40,000 | $100,000 |
| USB sales + consulting | $30,000 | $60,000 | $100,000 |
| Grants | $25,000 | $50,000 | $100,000 |
| **Total Year 3** | **$185,000** | **$600,000** | **$1,500,000** |

**Key assumptions for the aggressive scenario:** 50,000+ people worldwide own LeRobot-compatible arm kits by 2028; armOS captures 10-20% of that market; cloud training becomes the default workflow; 2-3 major hardware partnerships are active.

---

## 5. Go-to-Market Strategy

### Phase 1: Open Source Launch and Community Building (Months 1-6)

**Goal:** Establish armOS as the recommended way to get started with robot arms. Reach 500+ GitHub stars and 50+ active users.

**Actions:**

- Release armOS v0.1 (SO-101 support) as an open-source project on GitHub under Apache 2.0.
- Launch a Discord server as the community hub on day one.
- Publish 3 "Getting Started" tutorials: (a) SO-101 from scratch, (b) existing LeRobot user migration, (c) educator classroom setup.
- Write 2-3 blog posts about hard-won debugging knowledge (brltty serial hijacking, servo power supply diagnosis, overload protection tuning). These are standalone valuable content that builds SEO and credibility before the product is even mentioned.
- Post launch announcements on Hacker News, r/robotics, r/raspberry_pi, LeRobot GitHub Discussions, and HuggingFace community forums.
- Produce a 90-second demo video: "USB boot to robot teleop in 3 minutes." This single asset will drive more adoption than any feature list.
- Establish the robot profile contribution workflow (GitHub PR template, CI validation, "Tested Hardware" badges).

**Key metric:** 500 GitHub stars, 50 active users (defined as: booted armOS and completed teleoperation at least once).

### Phase 2: Hardware Partnerships (Months 6-12)

**Goal:** Bundle armOS with robot arm kits from at least one major distributor.

**Actions:**

- Approach Seeed Studio, Waveshare, and Feetech with a partnership proposal: include armOS USB sticks or a download link with their robot arm kits. The pitch -- armOS reduces their customer support burden by eliminating setup failures.
- Send free armOS USB sticks to 10-20 robotics YouTubers and educators (James Bruton, Skyentific, The Construct, university lab leads). The "plug in and it works" demo is extremely compelling on video.
- Partner with one university robotics course as a pilot. A single course with 20 students produces invaluable feedback and a case study for marketing.
- Engage the HuggingFace/LeRobot team for a joint blog post or README mention.
- Add Dynamixel support (v0.5) to unlock Koch and other arms, expanding the addressable market.

**Key metric:** 1 signed hardware partnership, 5+ community-contributed robot profiles, 1 university pilot.

### Phase 3: Cloud Services and Enterprise (Months 12-24)

**Goal:** Launch monetized services. Reach revenue sustainability.

**Actions:**

- Launch armOS Cloud Training service. Users collect data locally, upload datasets, receive trained policies.
- Release enterprise/education licensing for fleet management features.
- Launch the profile and plugin marketplace.
- Apply for educational technology grants (NSF Cyberlearning, EU Horizon, DARPA).
- Pursue Intel partnership for "robotics on Intel" co-marketing and OpenVINO integration for local inference.
- Present at ROSCon, PyCon, and Maker Faire.

**Key metric:** $20K+ monthly recurring revenue, 5+ enterprise/education customers, 2,000+ GitHub stars.

---

## 6. Marketing Strategy

### 6.1 Content Marketing

| Content Type | Frequency | Channel | Purpose |
|-------------|-----------|---------|---------|
| Tutorial blog posts | 2/month | Blog, Dev.to, Medium | SEO, demonstrate expertise, drive organic traffic |
| YouTube tutorials | 2/month | YouTube | Visual learners, most compelling for hardware products |
| "Building armOS" dev log | Weekly | Blog, X/Twitter | Transparency, community engagement, attract contributors |
| Conference talks | 2-3/year | PyCon, ROSCon, Maker Faire | Credibility, networking, partnership development |
| Case studies | Quarterly | Blog, PDF | Convince educators and enterprises |

**Flagship content piece:** A 90-second video showing a complete stranger unboxing an SO-101 kit, plugging in an armOS USB, booting a random laptop, and doing teleoperation. No cuts, no narration, just a timer in the corner. This video is the entire marketing strategy in compressed form.

### 6.2 Community Channels

| Channel | Purpose | Launch Timing |
|---------|---------|---------------|
| Discord server | Real-time support, "Show Your Setup" gallery, contributor coordination | Day 1 |
| GitHub Discussions | Long-form Q&A, feature requests, profile submissions | Day 1 |
| r/robotics | Announce releases, share tutorials, answer questions | Launch day |
| HuggingFace community | Cross-pollinate with LeRobot users | Launch day |
| X/Twitter | Short updates, demo clips, retweet community projects | Ongoing |
| Hacker News | Major releases and milestone posts | Launch, then quarterly |

### 6.3 Partnership Marketing

- **LeRobot/HuggingFace:** Joint blog post, mention in LeRobot documentation, shared Discord presence. HuggingFace has massive reach in the ML community; a single tweet from them can drive 1,000+ stars in a day.
- **Kit manufacturers:** "Works with armOS" badge on product listings. Co-branded setup guides. YouTube reviews by their affiliate creators.
- **Intel:** "Robotics on Intel" co-marketing. armOS proves you do not need an NVIDIA GPU for physical robot control, which is a story Intel wants to tell.

### 6.4 The Demo

The most important marketing asset is a live demo. Target opportunities:

- Maker Faire show floor (hands-on demo booth).
- University open houses (partner with pilot university).
- Robotics meetups (local, low-cost, high-engagement).
- Online: livestream a "zero to teleop" session on YouTube or Twitch.

Every demo follows the same script: start with a powered-off laptop and a disconnected robot. Insert USB. Boot. Connect robot. Teleop. Under 5 minutes. Every time.

---

## 7. Competitive Advantages

### 7.1 Defensible Moats

**1. The diagnostic suite.**
No other tool provides real-time servo health monitoring with actionable error messages for hobbyist-grade hardware. This was built from hard-won debugging experience -- voltage sag detection, overload protection tuning, communication reliability testing. It cannot be replicated without the same painful hands-on experience with these specific servos. This is the feature that turns first-time frustration into "it just told me what was wrong."

**2. The robot profile ecosystem.**
As community members contribute profiles for their robots, the profile library becomes a network effect. Each new profile makes armOS more valuable to all users and more attractive to new contributors. This is the Arduino library manager playbook.

**3. Zero-config USB boot.**
Competitors require installation. ROS2 takes hours to set up. LeRobot requires a working Linux environment with correct Python versions, dependencies, and udev rules. armOS requires inserting a USB stick and pressing the power button. This is not a feature; it is a fundamentally different product category.

**4. Domain expertise encoded as software.**
The lessons learned from the Surface Pro 7 + SO-101 setup -- brltty conflicts, sync_read retry logic, EEPROM protection settings, power supply requirements -- are encoded directly into armOS as auto-detection rules, default configurations, and diagnostic checks. This institutional knowledge is the product.

**5. Cloud training as the natural monetization point.**
Users collect data for free on commodity hardware (no GPU needed). Training requires GPUs they do not have. The cloud training service is the obvious, non-exploitative place to monetize -- users are happy to pay $10 to avoid setting up a GPU training environment.

### 7.2 What Competitors Would Need to Match Us

- **ROS2** would need to become simple. It will not. Simplicity is antithetical to its design as an enterprise-grade distributed robotics framework.
- **LeRobot** would need to ship an OS layer with hardware auto-detection and diagnostics. Possible, but HuggingFace's focus is AI frameworks, not operating systems. armOS is complementary to LeRobot, not competitive.
- **A new entrant** would need to replicate the servo protocol knowledge, debugging experience, and hardware compatibility testing. This takes months of hands-on work with physical hardware -- it cannot be shortcut.

---

## 8. Team and Resources Needed

### Founding Team (Months 1-6)

| Role | Responsibility | Status |
|------|---------------|--------|
| **Founder / Lead Engineer** | Architecture, servo drivers, diagnostic suite, OS image build | Current (Bradley) |
| **Community Manager (part-time)** | Discord, GitHub, social media, tutorial writing | Hire or volunteer |

The MVP can be built by one engineer. The founding team's constraint is time, not headcount.

### First Hires (Months 6-12)

| Role | Why | Estimated Cost |
|------|-----|---------------|
| **DevOps / Build Engineer** | OS image build pipeline, CI/CD, hardware compatibility testing matrix | $80-120K/year |
| **Developer Advocate** | Tutorials, YouTube content, conference talks, community engagement | $70-100K/year |
| **Part-time Designer** | TUI/dashboard UX, website, marketing materials | $30-50K/year (contractor) |

### Growth Hires (Year 2)

| Role | Why |
|------|-----|
| **Backend Engineer** | Cloud training service infrastructure |
| **Servo Protocol Engineer** | Dynamixel, CAN, WiFi servo support |
| **Education Partnerships Lead** | University pilots, curriculum development, grant writing |

### Advisory Board (Unpaid, Equity)

Target advisors from:
- LeRobot/HuggingFace team (technical credibility, distribution).
- Robotics education (university professor teaching with affordable arms).
- Hardware manufacturing (someone at Seeed Studio, Waveshare, or similar).
- Open-source business models (someone who has commercialized an open-source project).

---

## 9. Funding Strategy

### Phase 0: Bootstrap (Months 1-6)

- **Source:** Personal savings, side project time.
- **Budget:** $5-10K for hardware (test laptops, servo kits, USB drives), hosting, and domain registration.
- **Goal:** Ship MVP, validate product-market fit with 50+ users.

Bootstrapping is the right choice for Phase 0. The MVP is a single-engineer project that can be built in 12-14 weeks. Taking funding before validating demand creates misaligned incentives.

### Phase 1: Grants and Angels (Months 6-12)

- **NSF Cyberlearning and Future Learning Technologies:** Funds accessible STEM education tools. armOS for classroom robotics is a strong fit. Awards range from $50K-300K.
- **DARPA Young Faculty Award / Small Business Innovation Research (SBIR):** If the project demonstrates defense-adjacent applications (e.g., rapid field deployment of robotic systems). Awards range from $100K-1M.
- **EU Horizon Europe:** Funds open-source educational technology. Requires an EU partner institution.
- **Angel investors:** Target angels with robotics or education backgrounds. Raise $100-250K on a SAFE note at a $2-3M cap.
- **GitHub Sponsors / Open Collective:** Cover infrastructure costs ($500-2,000/month).

**Priority order:** Grants first (non-dilutive), then angels only if needed for the cloud training service buildout.

### Phase 2: Seed Round (Months 12-18, if warranted)

- **Target raise:** $500K-1.5M.
- **Use of funds:** Cloud training infrastructure, team expansion (3-4 hires), hardware partnerships, marketing.
- **Trigger:** Only pursue VC funding if (a) hardware partnerships are signed and generating revenue, (b) cloud training has demonstrated demand, and (c) the growth trajectory justifies venture-scale ambition.
- **Target investors:** Robotics-focused funds (The Engine, Lux Capital), open-source-focused funds (OSS Capital, Heavybit), education-focused funds.

**Important:** VC funding is optional, not assumed. The business model (cloud training + hardware partnerships + education licensing) can reach profitability at $50-100K MRR without venture capital. Pursue VC only if the market opportunity justifies hypergrowth.

---

## 10. Risks and Mitigations

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **USB boot fails on common hardware** | Medium | Critical | Start hardware compatibility testing in Sprint 4 (not Sprint 6). Maintain a public compatibility matrix. Target 90%+ success rate on post-2016 x86 UEFI hardware. |
| **Persistent storage on live USB is unreliable** | Medium | High | Spike in Sprint 2: validate that calibrations and profiles survive 10 unclean shutdowns. If casper-rw is unreliable, evaluate BTRFS or a separate data partition. |
| **LeRobot API breaks in a future version** | Medium | High | Pin to LeRobot v0.5.0 for MVP. Wrap all LeRobot calls through a bridge layer that can be updated independently. Submit upstream patches to reduce delta. |
| **Servo protocol abstraction does not generalize** | Medium | Medium | Before finalizing the API, sketch (do not implement) a Dynamixel driver to validate the abstraction. Spend 2 hours on this research to save 2 weeks of refactoring. |

### Market Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **LeRobot ships their own setup tool** | Low | High | Engage the LeRobot team early as collaborators. Upstream improvements. Make armOS the recommended LeRobot setup method, not a parallel effort. If HuggingFace builds their own tool, pivot to being the best "advanced diagnostics and fleet management" layer. |
| **Robot arm kits stall in popularity** | Low | High | Diversify hardware support beyond arms (mobile robots, grippers, sensors). Monitor sales data from Feetech and Dynamixel. |
| **A well-funded competitor builds the same thing** | Low | Medium | Move fast, build community, accumulate hardware profiles. Network effects from the profile ecosystem are the best defense. First-mover advantage matters in open source. |
| **Education market is slow to adopt** | Medium | Medium | Do not depend on education revenue in Year 1. Focus on hobbyists and researchers first; education is a Year 2 growth market. |

### Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Maintainer burnout (single-person project)** | High | Critical | Recruit contributors early through the profile system (low-barrier contributions). Pursue grant funding to enable full-time work. Do not over-commit on scope. |
| **Cloud training service has low margins** | Medium | Medium | Use spot GPU instances and auto-scaling. Start with a simple pricing model and adjust. Consider partnering with an existing training platform (Lambda Labs, Modal) rather than building infrastructure from scratch. |
| **Hardware partnerships take longer than expected** | High | Medium | Do not depend on partnership revenue in Year 1. Build the product and community first; partnerships follow traction. Sell USB sticks directly as a bridge. |
| **Name conflicts or trademark issues** | Low | Medium | Conduct a trademark search before public launch. The name "armOS" is less generic than "RobotOS" but still needs validation. Register the domain and GitHub org early. |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Support burden exceeds capacity** | High | Medium | Invest in documentation and self-service diagnostics. The diagnostic suite is both a product feature and a support deflection tool. Empower community members as support moderators on Discord. |
| **Hardware for testing is expensive** | Medium | Low | Request hardware donations from manufacturers (part of the partnership pitch). Buy used laptops for compatibility testing. Community members can run compatibility tests and report results. |

---

## Appendix A: Market Sizing

### Total Addressable Market (TAM)

- Global educational robotics: $5.8B by 2030.
- Hobbyist/maker segment: $1.5B+.
- AI robotics research tooling: emerging, $500M+ by 2028.

### Serviceable Addressable Market (SAM)

People who own or will buy a LeRobot-compatible arm kit and have an x86 laptop:
- 2026: 5,000-20,000 people worldwide.
- 2028: 50,000+ as kits get cheaper and AI robotics curricula expand.

### Serviceable Obtainable Market (SOM)

Realistic armOS capture rate of 10-20% of SAM:
- 2026: 500-4,000 users.
- 2028: 5,000-10,000 users.

### Revenue per User (blended)

- Free tier (open source core): $0.
- Active users who pay for cloud training: ~$50-100/year.
- Education/enterprise seats: $50-1,000/year.
- USB stick purchases: $15-25 one-time.

### Leading Indicators to Track

- LeRobot GitHub stars growth rate (currently ~10K, growing ~300/month).
- Feetech STS3215 monthly sales volume on AliExpress.
- Number of university robotics courses adopting low-cost arms.
- SO-101 kit availability and pricing trends.

---

## Appendix B: Competitive Positioning Matrix

```
                        High Hardware Breadth
                               |
                   ROS2 + MoveIt2
                               |
                               |
     High Complexity ----------+---------- Low Complexity
                               |
              LeRobot (bare)   |   armOS  <-- target position
                               |
                               |
                        Low Hardware Breadth
```

**armOS positioning:** Low complexity, moderate hardware breadth. The only product in the "it just works" quadrant for affordable robot arms.

**Key competitors by segment:**

| Segment | Competitor | armOS Advantage |
|---------|-----------|-----------------|
| Setup simplicity | YouTube tutorials + manual install | 10x faster, reproducible, no expertise needed |
| Diagnostics | Nothing comparable for hobbyist hardware | Only tool that monitors servo health with actionable recommendations |
| Data collection | LeRobot (requires manual setup) | Pre-configured pipeline, zero setup |
| Visualization | Foxglove, rerun.io | Integrate rather than compete; armOS owns "getting started," they own "power user analysis" |
| Enterprise robots | ROS2, NVIDIA Isaac | Different market; armOS targets sub-$500 arms, not industrial robots |

---

## Appendix C: Key Milestones

| Milestone | Target Date | Success Criteria |
|-----------|------------|-----------------|
| MVP (v0.1) ships | Q3 2026 | SO-101 boot-to-teleop in under 5 minutes |
| 500 GitHub stars | Q4 2026 | Community traction validated |
| First hardware partnership signed | Q1 2027 | Distribution channel established |
| Cloud training beta | Q1 2027 | 10+ users completing training runs |
| v0.5 (multi-hardware) ships | Q2 2027 | Dynamixel support, 3+ robot profiles |
| First education pilot | Q2 2027 | 1 university course, 20+ students |
| $10K MRR | Q4 2027 | Revenue sustainability in sight |
| v1.0 (universal robot OS) ships | Q4 2027 | 3+ servo protocols, web dashboard, marketplace |
| $50K MRR | Q2 2028 | Path to profitability |

---

_Business plan for armOS -- a universal robot operating system on a bootable USB stick._
