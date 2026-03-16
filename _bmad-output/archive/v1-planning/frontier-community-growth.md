# armOS Frontier Community Growth Strategy

**Authors:** John (PM) and Bob (Scrum Master)
**Date:** 2026-03-15
**Mode:** Frontier -- unconventional growth strategies grounded in what is actually buildable

---

## Thesis

armOS has a rare advantage: it is an operating system that ships with an AI agent (Claude Code) as a first-class citizen. Most developer tools bolt AI on after the fact. armOS can make AI the *interface itself*. This changes everything about onboarding, community building, and viral distribution.

The strategies below are organized by time horizon and ordered by expected impact per engineering hour invested. Each one includes a concrete "week 1 action" so this document drives execution, not just ideation.

---

## 1. AI-Powered Onboarding: Claude Code IS the Setup Wizard

### The Idea

When someone boots armOS for the first time, they do not see a menu. They see a conversation. Claude Code greets them, asks what hardware they have, and walks them through setup like a patient lab partner. Not a wizard with radio buttons -- an AI tutor that adapts to what it sees on the USB bus.

### What This Looks Like

```
$ armOS first-boot

  Welcome to armOS. I'm checking your hardware...

  I see:
    - 1x CH340 USB-serial adapter (ttyUSB0)
    - 6 Feetech STS3215 servos responding on the bus
    - 1x USB camera (Logitech C920)

  This looks like an SO-101 follower arm. Is that right? (y/n)

  > y

  Great. I'll set up the SO-101 profile and run calibration.
  Place the arm in the rest position shown in this diagram:
  [ASCII art of rest position]

  Ready? (y/n)
```

### Offline Fallback: Local LLM

Claude Code requires internet. For offline-first scenarios (classrooms without WiFi, field deployments), ship a local LLM as a fallback:

| Model | Size | Hardware Requirement | Capability |
|---|---|---|---|
| **Phi-3-mini (3.8B)** | 2.3 GB | 8 GB RAM, any CPU | Good enough for guided setup, FAQ, basic troubleshooting |
| **TinyLlama (1.1B)** | 700 MB | 4 GB RAM | Minimal -- scripted responses with light NLU |
| **Qwen2-1.5B** | 1.1 GB | 4 GB RAM | Better multilingual support for international users |

**Recommendation:** Ship Phi-3-mini as the offline default. It fits on the USB image, runs on any machine that can run armOS, and handles the structured onboarding flow well enough. When internet is available, upgrade to Claude Code seamlessly.

**Implementation approach:** The offline LLM does not need to be general-purpose. Fine-tune it (or use structured prompting) on a narrow corpus: armOS setup flows, common error messages, servo troubleshooting decision trees. A 3.8B model with a tight system prompt can match a 70B model on this narrow domain.

### Auto-Detection as Conversation

The key insight: hardware auto-detection is not a silent background process. It is a *conversation topic*. When armOS detects hardware, the AI narrates what it found and asks the user to confirm. This turns a technical process into an educational moment:

```
  I found a second USB-serial adapter on ttyUSB1.
  Let me scan for servos...

  ttyUSB0: 6 servos (IDs 1-6) -- this is probably your follower arm
  ttyUSB1: 6 servos (IDs 1-6) -- this is probably your leader arm

  I'm assigning ttyUSB0 as the follower and ttyUSB1 as the leader.
  If that's backwards, just say "swap arms" and I'll fix it.
```

Compare this to the current LeRobot experience: "Enter the port for your leader arm (e.g., /dev/ttyUSB0)." The user has no idea which is which and must unplug cables to figure it out.

### Week 1 Action

Write a `first-boot.sh` script that performs hardware detection and outputs the conversational text above (no LLM needed -- just templated strings with detected values). This proves the UX concept without any AI dependency. The AI layer comes later.

### Priority: P0 (Sprint 3-4)

This is not a nice-to-have. This IS the product differentiation. phosphobot has a web UI. ROS2 has launch files. armOS has a conversation.

---

## 2. Viral Mechanics: Make Every Teleop Session Shareable

### The Problem with Robotics Content

Robot videos go viral. But creating them requires: screen recording software, video editing, knowing where to post, writing a caption. Every friction point between "cool moment" and "shared post" kills 90% of potential content.

### Auto-Clip Generation

Build clip capture directly into the teleop TUI:

```
[Teleop running]

  Press [C] to clip the last 15 seconds
  Press [S] to start/stop recording

  > C

  Clip saved: ~/armOS/clips/teleop-2026-03-15-14-32.mp4

  Share to:
    [1] Copy to USB (for transfer)
    [2] Upload to HuggingFace Hub
    [3] Generate shareable link

  > 3

  Link: https://armos.dev/clip/a3f9k2
  (Auto-expires in 7 days. QR code displayed below.)
```

### Implementation Details

- **Continuous ring buffer:** Record the camera feed and teleop overlay to a rolling 60-second buffer using ffmpeg. When the user presses [C], save the last 15 seconds. Zero-cost until clip is requested.
- **Watermark:** Subtle "Built with armOS | armos.dev" text in the bottom-right corner. Not obnoxious -- think "Shot on iPhone" energy. Users who want to remove it can (it is open source), but most will not bother.
- **Format:** 720p MP4, vertical crop option for TikTok/Reels/Shorts. Horizontal for YouTube/X. The TUI asks which format on export.
- **Metadata:** Embed robot type, servo count, and armOS version in the MP4 metadata. This enables a future gallery page that auto-categorizes uploads.

### Gamification: The armOS Dashboard

Add an achievements system to the TUI -- not as a gimmick, but as a structured onboarding progression:

| Achievement | Trigger | Why It Matters |
|---|---|---|
| First Boot | Boot armOS for the first time | Confirms the USB works |
| Hardware Detected | Auto-detect completes successfully | Confirms the robot is connected |
| Calibrated | Complete calibration | The first real milestone |
| First Teleop | Run teleop for 30+ seconds | The "it works!" moment |
| Smooth Operator | 60 seconds of teleop with zero communication errors | Validates hardware reliability |
| Data Collector | Record 10+ demonstration episodes | Enters the ML pipeline |
| Diagnostician | Run the full diagnostic suite | Learns the diagnostic tools |
| Contributor | Submit a robot profile or bug report | Community participation |
| Fleet Commander | Connect 2+ arms simultaneously | Advanced use case |

**Display:** Show achievements as a sidebar in the TUI dashboard. Unlocked achievements show in green. This gives new users a clear "what should I do next?" progression without a tutorial.

**Leaderboard:** Optional, opt-in. Track anonymized metrics: total teleop hours, episodes collected, unique robot profiles tested. Display on armos.dev/community. This creates friendly competition and makes the community feel alive.

### Week 1 Action

Add a `--clip` flag to the teleop script that saves the last 15 seconds of camera feed using ffmpeg's segment muxer. No watermark, no upload -- just the core ring-buffer-to-file mechanic. Get the plumbing right first.

### Priority: P1 (Sprint 5-6 for clips, Sprint 7+ for gamification)

---

## 3. Education as Distribution: The Trojan USB

### Why Education Is the Highest-Leverage Channel

One professor adopting armOS means 20-50 students per semester, every semester, for years. Those students graduate, join companies, and bring armOS with them. This is the playbook that made MATLAB, Git, and Docker ubiquitous.

The numbers: there are roughly 2,000 universities worldwide with robotics programs. If armOS captures 50 courses in 3 years (2.5%), that is 1,000-2,500 students per semester who learn robotics on armOS.

### Free Curriculum Kit: "Robotics in 10 Lessons"

Build a complete, free, open curriculum that uses armOS as the lab platform:

| Lesson | Topic | armOS Feature Used |
|---|---|---|
| 1 | What is a robot? Boot armOS, explore the hardware | First boot, auto-detection |
| 2 | Servo fundamentals: position, speed, torque | Diagnostic suite (read servo registers) |
| 3 | Forward kinematics: where is the end effector? | Teleop with position readout |
| 4 | Calibration: teaching the robot where "zero" is | Calibration workflow |
| 5 | Teleoperation: controlling a robot in real-time | Teleop TUI |
| 6 | Sensing: cameras and the robot's view of the world | Camera integration, data visualization |
| 7 | Data collection: recording demonstrations | LeRobot data collection |
| 8 | Imitation learning: teaching by showing | Cloud training (or local if GPU available) |
| 9 | Policy deployment: the robot acts autonomously | Inference pipeline |
| 10 | Diagnostics and debugging: when things go wrong | Full diagnostic suite |

**Format:** Each lesson is a Markdown file in the armOS repo, plus a Jupyter notebook for the hands-on portion. Lessons 1-6 require zero internet. Lessons 7-9 require internet for cloud training (or a local GPU).

**Distribution:** Host on the armOS website, cross-list on HuggingFace Learn (where the LeRobot course already lives), and submit to Class Central for discoverability.

### Partnership Targets

| Partner | What They Get | What armOS Gets | Likelihood |
|---|---|---|---|
| **HuggingFace Learn** | Hardware lab component for their robotics course (currently software-only) | Distribution to their course enrollees, HuggingFace brand association | High -- their course needs a hardware lab and armOS is the easiest path |
| **fast.ai** | A "practical robotics" module that fits their "make it work first" philosophy | Jeremy Howard's endorsement is worth 10,000 GitHub stars | Medium -- requires a compelling demo and personal outreach |
| **CS50 (Harvard)** | A robotics problem set that runs on any student laptop via USB | Massive brand credibility, 100K+ students per year see it | Low-Medium -- CS50 is selective but always looking for novel problem sets |
| **Georgia Tech ECE 4560** | They already use SO-101. armOS eliminates their setup TA burden | Proof-of-concept university deployment, case study | High -- they are already in our target market |

### University Site License Model

One email from a professor gets 50 USB image downloads (or a bulk shipping option for pre-flashed drives). No purchase order, no procurement process, no IT approval. The professor downloads, flashes 20 USB drives, hands them out in class. Done.

**Why this matters:** University procurement kills adoption. If a professor needs IT approval to install software, they will not use it. A bootable USB sidesteps IT entirely -- it does not touch the university's machines.

### Student Competition Platform

Launch "armOS Challenges" -- monthly manipulation challenges with a public leaderboard:

- **Month 1:** Pick up a block and place it in a cup (baseline task)
- **Month 2:** Stack 3 blocks (precision challenge)
- **Month 3:** Sort colored objects (perception challenge)
- **Format:** Students upload their trained policy and a video. Community votes on best execution. Winners get featured on the armOS website and a "Challenge Winner" badge in their TUI.

This is Kaggle for robot manipulation. The key difference: every entry requires real hardware, not just code. This means entries are inherently visual and shareable -- every submission is a potential viral video.

### Week 1 Action

Write Lesson 1 of the curriculum ("What is a robot?") as a Markdown file in the repo. Keep it short (500 words + 5 hands-on steps). This proves the format and creates a template for the remaining 9 lessons. Contact the Georgia Tech ECE 4560 instructor with a cold email offering armOS for their next semester.

### Priority: P1 (curriculum in Sprint 5-8, partnerships are ongoing)

---

## 4. Hardware Partnerships as Growth: armOS Inside the Box

### The Dream

You buy an SO-101 kit from Seeed Studio. Inside the box, alongside the servos and 3D printed parts, is a microSD card (or USB stick) labeled "armOS -- Plug in and start building." The quick-start guide says "Step 1: Insert the armOS drive. Step 2: Boot your laptop from USB. Step 3: Follow the on-screen instructions."

No mention of Linux. No mention of Python. No mention of LeRobot. The user never knows those things exist until they are ready to learn about them.

### Why Seeed Studio Should Say Yes

Build the pitch around *their* economics, not ours:

1. **Support cost reduction:** Every SO-101 buyer who hits a setup problem either submits a support ticket (costs Seeed $5-15 to resolve) or returns the kit ($240 lost revenue + shipping). If armOS prevents 50% of setup failures, and 20% of buyers currently have setup issues, that is a direct savings of $2-7 per kit sold.

2. **Competitive differentiation:** Waveshare, WowRobo, and OpenELAB all sell near-identical SO-101 kits. The hardware is commoditized -- Feetech STS3215 servos are the same in every box. Software is the only axis for differentiation. "Includes armOS -- zero-config setup" is a product listing bullet point that none of their competitors can match.

3. **Higher conversion rate:** A buyer comparing SO-101 kits on Amazon sees one listing that says "Includes plug-and-play software" and four that say "Linux knowledge required." Which one do they click?

### Revenue Share Model

| Tier | What Seeed Does | What armOS Gets | Revenue |
|---|---|---|---|
| **Tier 1: Documentation** | Links to armOS in product docs and wiki | Distribution, SEO backlinks | Free |
| **Tier 2: Co-branded** | "Recommended by armOS" badge on listing, armOS download link in box insert | Brand association, qualified traffic | Free |
| **Tier 3: Bundled** | Pre-flashed USB/microSD in every kit | Direct distribution to every buyer | $3-5 per unit to armOS |
| **Tier 4: Cloud revenue share** | Seeed promotes armOS cloud training to their customers | Qualified leads for cloud training | 10% of cloud training revenue from Seeed-referred users |

**Start at Tier 1.** It costs Seeed nothing and lets them evaluate the partnership risk-free. Tier 3 is the goal, but it requires armOS to prove itself first.

### Beyond Seeed: The Hardware Certification Program

As armOS supports more robots, create a "Works with armOS" certification:

- Hardware vendors submit their robot for testing
- armOS team (or community volunteers) creates and validates a robot profile
- Certified products get a badge for their product listing and a dedicated page on armos.dev
- Certification is free for the first 20 products (seed the ecosystem), then $500-2,000 per certification to cover testing costs

This is the WiFi Alliance / USB-IF model adapted for hobby robotics. It creates a quality signal in a market that currently has none.

### Week 1 Action

Draft the Seeed Studio outreach email (template is already in strategy-content-enhancements.md -- personalize it with specific LeRobot issue numbers and community quotes about SO-101 setup pain). Do NOT send until the demo video and MVP image exist. The email is only as strong as the demo it links to.

### Priority: P2 (partnership outreach begins after MVP ships, Sprint 7+)

---

## 5. Developer Ecosystem: Make Contributing Irresistible

### Robot Profile Bounties

The robot profile ecosystem is armOS's network-effect moat. Accelerate it with bounties:

| Bounty Tier | Amount | Criteria |
|---|---|---|
| **Bronze** | $50 | Submit a working robot profile (YAML + calibration + basic teleop confirmed) |
| **Silver** | $150 | Bronze + diagnostic rules + tuned protection settings + documentation |
| **Gold** | $500 | Silver + video tutorial + contributed to the curriculum (lesson using this robot) |

**Funding:** Initially from project funds or a community bounty pool (GitHub Sponsors, Open Collective). Later, hardware vendors fund bounties for their own products -- they want an armOS profile because it sells more kits.

**Quality gate:** All profile PRs go through CI validation (servo ID ranges, YAML schema check, calibration bounds check) and a human review by a maintainer. Bounty is paid on merge, not on submission.

### Plugin of the Month

Spotlight one community contribution per month on the armOS blog and social channels:

- Detailed writeup of what the plugin/profile does and how it was built
- Interview with the contributor (async, 5 questions over Discord DM)
- "Featured Contributor" badge in the TUI and on Discord
- Shared on all armOS social channels

This costs zero dollars and gives contributors meaningful recognition. Recognition is the primary motivator in open source -- money is secondary.

### armOS Conf (Virtual, Annual, Free)

A one-day virtual conference. Zero budget required:

| Time | Session | Speaker |
|---|---|---|
| 10:00 | Keynote: State of armOS | Bradley (founder) |
| 10:30 | How I built the [X] robot profile | Community contributor |
| 11:00 | armOS in the classroom: a semester report | University partner |
| 11:30 | Lightning talks (5 min each, 6 slots) | Community |
| 12:30 | Live demo: new feature preview | Core team |
| 13:00 | Open Q&A / roadmap discussion | Everyone |

**Platform:** Discord Stage or YouTube Live (free). Record everything. Post recordings to YouTube. The recordings become evergreen content.

**Timing:** Schedule the first armOS Conf 6 months after launch, when there is enough community to fill 6 lightning talk slots. If there are not 6 people willing to give a 5-minute talk, the community is not ready for a conf.

### Week 1 Action

Create a `CONTRIBUTING.md` in the repo with clear instructions for submitting a robot profile. Include a YAML template, a checklist of what a complete profile includes, and a "your first contribution" walkthrough. Label 3-5 GitHub issues as "good first issue" with clear descriptions.

### Priority: P1 (CONTRIBUTING.md in Sprint 2, bounties in Sprint 7+, conf at 6 months post-launch)

---

## 6. Frontier Distribution: Meet Users Where They Already Are

### "Try armOS in Your Browser" (No Hardware Required)

Build a browser-based demo using a simulated arm:

- **Platform:** HuggingFace Spaces (free hosting for ML demos) or GitHub Codespaces
- **Implementation:** A lightweight Python simulation of the SO-101 (6-DOF arm rendered in a web canvas) with the armOS TUI running in an xterm.js terminal
- **What the user can do:** Run calibration (simulated), teleop with keyboard/mouse (simulated), see the diagnostic dashboard with fake telemetry data
- **What the user cannot do:** Connect real hardware (obviously)
- **Purpose:** Let people experience the armOS workflow before committing to hardware. This is the "try before you buy" that no other robotics tool offers.

**Effort estimate:** 2-3 weeks for a basic simulation. The armOS TUI already runs in a terminal -- the work is building the simulated servo backend and a web-based arm visualizer.

### Flatpak/Snap: armOS Without Rebooting

Not everyone wants to boot from USB. Offer armOS as a Flatpak or Snap package that installs on any existing Linux system:

```bash
sudo snap install armos
armos setup  # configures udev rules, installs dependencies in a container
armos start  # launches the TUI dashboard
```

**Trade-offs:**
- Loses the "zero-config" purity of the USB boot (host OS quirks can still cause problems)
- Gains a massive distribution channel (Snap Store has millions of users)
- Significantly lower barrier to trying armOS for existing Linux users
- Can coexist with the USB image -- different packaging for different audiences

**Recommendation:** Build the USB image first (it is the purest expression of the vision). Add Snap packaging in Horizon 2 once the core is stable. The Snap version can share 95% of the codebase -- it is just a different packaging format, not a different product.

### Pre-Installed on Refurbished Laptops

The OLPC (One Laptop Per Child) model, adapted for robotics:

- Partner with a refurbished laptop vendor (there are dozens on Amazon and eBay)
- Pre-install armOS on the internal drive (not USB -- persistent, full-speed)
- Sell as a bundle: refurbished ThinkPad + SO-101 kit + armOS pre-installed = $350-450 total
- Target: schools in developing countries, maker spaces, STEM after-school programs

**Why refurbished ThinkPads:** They are $80-150 on eBay, nearly indestructible, and armOS runs perfectly on 2016+ Intel hardware. A ThinkPad T460 with 8 GB RAM is an ideal armOS machine and costs less than the robot kit itself.

**Revenue model:** $10-20 markup on the laptop for armOS pre-installation. Or free for educational orders (funded by grants).

**Timing:** This is a Horizon 2 play (6-18 months post-launch). It requires a stable armOS image, a reliable supply chain for refurbished laptops, and enough demand to justify the logistics.

### Week 1 Action

Create a GitHub issue titled "Browser-based armOS demo (HuggingFace Spaces)" with a design sketch: xterm.js terminal on the left, simulated arm visualization on the right, pre-loaded with a fake SO-101 profile. Tag it "help wanted" -- this is a great community contribution project for someone with web dev skills.

### Priority: P2 (browser demo in Sprint 8+, Snap in Horizon 2, laptop bundles in Horizon 2-3)

---

## 7. Content Flywheel: Turn Every Interaction into Content

### Debug Sessions Become Blog Posts

Every time Claude Code helps a user debug a problem on armOS, the session contains:
1. The symptoms (what went wrong)
2. The diagnosis (what Claude found)
3. The fix (what was changed)

This is a blog post. Automatically.

**Implementation:**
- Add a `--save-session` flag to armOS's Claude Code integration
- When a debug session resolves successfully, offer: "This might help other users. Publish an anonymized version to the armOS knowledge base? (y/n)"
- Strip personal info, format as Markdown, submit as a draft to the armOS blog or knowledge base
- A maintainer reviews and publishes (no auto-publish -- quality matters)

**Why this works:** The armOS knowledge base grows proportionally to the number of problems users encounter. More users = more problems = more solutions = better knowledge base = fewer problems for future users. This is the data flywheel applied to documentation.

### "This Week in armOS" Auto-Generated Newsletter

Pull from GitHub activity to auto-generate a weekly digest:

| Section | Data Source |
|---|---|
| New features | Merged PRs with label "feature" |
| Bug fixes | Merged PRs with label "fix" |
| New robot profiles | Merged PRs with label "profile" |
| Community spotlight | Most-reacted Discord message or most-starred community project |
| Stats | GitHub stars delta, Discord member delta, downloads delta |
| Coming next | Open PRs with label "in-progress" |

**Implementation:** A GitHub Action that runs weekly, collects data via GitHub API and Discord API, renders a Markdown template, and posts to the blog + emails subscribers.

**Effort:** 1-2 days to build. This is a solved problem -- many open-source projects do this (Rust's "This Week in Rust" is the gold standard). The key is starting it early, even when the content is thin. Consistency > volume.

### User Setup Gallery

A page on armos.dev/gallery showing user-submitted photos and descriptions of their armOS setups:

- Submit via a simple form: photo, robot type, computer model, one sentence about their use case
- Displayed as a card grid (photo + caption)
- Sortable by robot type, date, popularity

**Why this works:** Social proof. When a prospective user visits armos.dev and sees 50 different setups from around the world -- university labs in Japan, maker spaces in Brazil, home offices in Germany -- they think "this is real." A gallery of 50 setups is more convincing than any feature list.

**Week 1 Action:** Add a `#show-your-setup` channel to the Discord server. Pin a message explaining the format: "Post a photo of your armOS setup with your robot type and one sentence about what you're working on." Seed it with Bradley's own Surface Pro 7 + SO-101 setup. The Discord channel is the gallery MVP -- a web page comes later.

### Priority: P2 (newsletter in Sprint 6, debug-to-blog in Sprint 8+, gallery from day 1 on Discord)

---

## 8. Execution Roadmap: What to Build When

### Sprint 2-4 (MVP Phase) -- Focus: Core Product

| Item | Type | From This Document |
|---|---|---|
| `first-boot.sh` conversational hardware detection | Feature | Section 1 |
| `CONTRIBUTING.md` + robot profile template | Community | Section 5 |
| Discord server with #show-your-setup | Community | Section 7 |
| Demo video (90 seconds, USB to teleop) | Marketing | Prerequisite for everything |

### Sprint 5-6 (Launch Phase) -- Focus: Distribution and Content

| Item | Type | From This Document |
|---|---|---|
| Teleop clip capture (`--clip` flag) | Feature | Section 2 |
| Curriculum Lesson 1 | Content | Section 3 |
| "This Week in armOS" newsletter setup | Content | Section 7 |
| Georgia Tech cold email | Partnership | Section 3 |
| HuggingFace Learn outreach | Partnership | Section 3 |

### Sprint 7-8 (Growth Phase) -- Focus: Ecosystem and Partnerships

| Item | Type | From This Document |
|---|---|---|
| Achievement system in TUI | Feature | Section 2 |
| Robot profile bounty program launch | Community | Section 5 |
| Seeed Studio outreach email | Partnership | Section 4 |
| Browser demo on HuggingFace Spaces (issue created) | Distribution | Section 6 |
| Watermark on shared clips | Growth | Section 2 |

### Sprint 9-12 (Scale Phase) -- Focus: Flywheel

| Item | Type | From This Document |
|---|---|---|
| Offline LLM onboarding (Phi-3-mini) | Feature | Section 1 |
| Debug-session-to-blog-post pipeline | Content | Section 7 |
| "Works with armOS" certification program | Ecosystem | Section 4 |
| Student competition platform ("armOS Challenges") | Community | Section 3 |
| Snap/Flatpak packaging | Distribution | Section 6 |

### 6 Months Post-Launch

| Item | Type |
|---|---|
| armOS Conf (virtual, free) | Community |
| Refurbished laptop bundles (exploration) | Distribution |
| Cloud training revenue share with hardware partners | Revenue |

---

## 9. Metrics That Matter

### Leading Indicators (track weekly from day 1)

| Metric | Target (3 months) | Target (12 months) | Why It Matters |
|---|---|---|---|
| GitHub stars | 500 | 2,000 | Awareness and interest |
| Discord members | 200 | 1,500 | Active community size |
| Unique USB image downloads | 100 | 2,000 | Actual adoption |
| First-boot completion rate | 80% | 95% | Onboarding quality |
| Time from boot to first teleop | <10 min | <5 min | Core value prop |
| Clips shared (with watermark) | 10 | 500 | Viral reach |
| Community-contributed robot profiles | 3 | 20 | Ecosystem health |
| Curriculum downloads | 50 | 1,000 | Education channel |

### Vanity Metrics to Ignore

- Twitter follower count (does not correlate with adoption)
- Blog post word count (quality > quantity)
- Number of Slack/Discord channels (fragmentation, not growth)
- "Partnerships in discussion" (only signed partnerships count)

---

## 10. What Could Go Wrong (and What to Do About It)

| Risk | Scenario | Mitigation |
|---|---|---|
| **AI onboarding is annoying** | Users want to click buttons, not type responses | Offer both: conversational mode (default for first boot) and classic TUI menu (accessible via `--menu` flag). Let users choose. |
| **Gamification feels patronizing** | Experienced users do not want "achievements" | Make achievements opt-in and invisible by default. Only show the sidebar if the user enables it. The progression system is for beginners. |
| **Clips leak private info** | A user's home environment is visible in shared clips | Only capture the robot camera feed, not the laptop screen. Add a "blur background" option using a lightweight segmentation model. |
| **Bounties attract low-quality submissions** | Drive-by contributions that do not actually work | Require video proof of teleop working with the submitted profile. CI checks catch schema errors but cannot catch "the arm moves wrong." |
| **Curriculum is ignored** | Professors do not adopt it | The curriculum must be good enough to use standalone, not just an armOS advertisement. If a professor could use it without armOS (by following manual setup), it is good enough. armOS just makes it painless. |
| **Seeed says no** | The biggest hardware partner passes | Go to Waveshare, WowRobo, or Feetech directly. The pitch works for any vendor. Seeed is the ideal first partner but not the only option. |

---

## Summary: The Three Bets

This strategy makes three bets about what drives adoption of a robotics OS:

1. **AI is the interface, not a feature.** The onboarding conversation is the product. Everything else (diagnostics, calibration, data collection) flows from "the computer talks to you about your robot." This is armOS's soul.

2. **Every user is a content creator.** The clip system, watermarks, gallery, and challenges turn passive users into active distributors. A single viral clip of a robot arm picking up a block, watermarked "Built with armOS," is worth more than a $10,000 ad campaign.

3. **Education is the distribution channel.** One professor = 50 users per semester, forever. The curriculum kit is not a side project -- it is the primary growth engine. Build it with the same rigor as the core product.

If even one of these three bets pays off, armOS reaches 2,000+ users in year one. If all three hit, the "Android of robotics" vision becomes plausible.

---

*Frontier community growth strategy for armOS. Authored 2026-03-15.*
