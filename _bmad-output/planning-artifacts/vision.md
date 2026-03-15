# armOS -- Vision Document

## One Sentence

**armOS is the Android of robotics** -- a free, open operating system that makes any computer a robot brain in minutes.

---

## The Insight

We spent three days setting up a single SO-101 arm on a Surface Pro 7. Not building anything. Not training a model. Just getting the hardware to respond to commands. The list of things that went wrong:

- The Linux kernel did not support the Surface Type Cover or touchscreen.
- `brltty` silently hijacked the USB-serial port, making the servo controller invisible.
- Servo overload protection tripped at factory defaults, causing random shutdowns.
- The power supply sagged under load, producing intermittent stuttering that looked like a software bug.
- LeRobot's `sync_read` failed silently on communication errors, requiring a custom retry patch.
- Every servo's PID and protection registers needed individual EEPROM tuning.

Every single person who buys an SO-101 kit will hit some subset of these problems. There are an estimated 3,000 to 5,000 SO-101 arms in the field today. The LeRobot project has 22,000+ GitHub stars and 15,000+ Discord members. Over 3,000 people participated in LeRobot hackathons across 100+ cities. **The knowledge to solve their setup problems exists -- it is trapped in GitHub issues, Discord threads, and Claude Code conversations.**

armOS captures that knowledge in software.

---

## The Problem

Robotics in 2026 is where personal computing was in 1978. Every robot has its own software stack, its own drivers, its own configuration ritual. A PhD student spends 3 days installing ROS2. A hobbyist spends a weekend debugging USB serial drivers. A teacher gives up and shows YouTube videos instead of letting students touch real hardware.

The hardware is finally cheap enough -- a complete 6-DOF arm is $220. The AI is finally good enough -- LeRobot can train policies from 50 demonstrations. **But the software layer between them is still a nightmare.**

---

## The Vision

**Boot from USB. Detect hardware. Start building.**

```
+--------------------------------------------------------------+
|                        THE STACK                              |
|                                                               |
|   +------------------------------------------------------+   |
|   |  Applications                                        |   |
|   |  * Teleop  * Data Collection  * Policy Inference     |   |
|   |  * Teaching  * Remote Operation  * Simulation        |   |
|   +-------------------------+----------------------------+   |
|   +-------------------------+----------------------------+   |
|   |  AI Framework Layer                                  |   |
|   |  * LeRobot  * ROS2 Bridge  * Custom Policies         |   |
|   +-------------------------+----------------------------+   |
|   +-------------------------+----------------------------+   |
|   |  armOS Core                                          |   |
|   |  * Hardware Abstraction  * Robot Profiles            |   |
|   |  * Diagnostics Engine    * Telemetry                 |   |
|   |  * Calibration           * Safety Watchdog           |   |
|   +-------------------------+----------------------------+   |
|   +-------------------------+----------------------------+   |
|   |  Hardware                                            |   |
|   |  * Any servo protocol  * Any camera  * Any computer  |   |
|   +------------------------------------------------------+   |
|                                                               |
|   Insert USB. Power on. Build robots.                         |
+--------------------------------------------------------------+
```

---

## Three Horizons

### Horizon 1: The USB Stick (Now -- 6 months)

A 9-sprint MVP delivered in 18 weeks by a solo engineer with AI pair programming.

- Boot any x86 machine from USB -- zero installation, zero configuration
- Auto-detect SO-101 and Waveshare Gripper-A (same STS3215 bus, zero new driver work)
- Calibrate, teleop, collect data -- all from a terminal UI dashboard
- Built-in diagnostics that explain what went wrong in plain English ("Servo 3 overloaded -- reduce speed or increase torque limit. Current load: 87%.")
- Real-time telemetry: voltage, temperature, position, and load for every servo, color-coded green/yellow/red
- OAK-D Lite depth camera support for data collection
- AI-powered conversational onboarding: Claude Code greets users on first boot, detects hardware, and walks them through setup like a patient lab partner
- *"The fastest path from unboxing a robot arm to moving it"*

### Horizon 2: The Platform (6--18 months)

armOS becomes the layer that hardware companies ship with their products.

- **LeKiwi mobile base support** -- the #1 expansion target. Same Feetech servos, same LeRobot framework. A $440 mobile manipulator (LeKiwi base + SO-101 arm) running armOS on a Raspberry Pi 5.
- **Raspberry Pi 5 ARM image** alongside the x86 USB ISO -- unlocking embedded robots with onboard compute.
- **Fleet management web dashboard** -- a classroom with 30 arms, centrally managed. Track which stations are active, which hardware is connected, aggregate diagnostics. Powered by Foxglove or Rerun.io for 3D telemetry visualization.
- **Robot profile marketplace** -- like Docker Hub for robots. Community members publish profiles with tuned calibrations, diagnostic rules, and protection settings. Hardware vendors publish official profiles. Free listings drive ecosystem growth; paid premium profiles generate 20-30% commission revenue.
- **CAN bus servo driver** -- unlocks MyActuator RMD, Damiao DM-J, and CubeMars AK series brushless actuators, opening the path from $15 hobby servos to $150+ professional actuators.
- **Docker container delivery** for developers and CI environments (`docker run --privileged --device=/dev/ttyUSB0 armos/armos:latest`)
- **ROS2 bridge** for interop with the industrial ecosystem
- **URDF/MJCF models** shipped with every profile for sim-to-real workflows
- **Reachy Mini Lite profile** -- a $299 USB-connected desktop humanoid
- *"The platform that robot hardware companies ship with their products"*

### Horizon 3: The Intelligence Layer (18--36 months)

The robot gets smarter every day, even on a CPU.

- **Octo-Small VLA inference on CPU at 5-10 Hz** (50-150ms per step). A 27M-parameter vision-language-action model, quantized to ONNX and accelerated with OpenVINO, running real-time policy inference on an Intel i5 with no GPU. Users collect 50 demonstrations, upload to the cloud for fine-tuning, and download a policy that runs locally at interactive speeds.
- **Self-diagnosing robots with isolation forest anomaly detection**. Three-layer telemetry analysis: threshold rules (instant), statistical change detection (CUSUM, 0.1ms), and scikit-learn isolation forests trained on each arm's "normal" behavior (5ms per prediction). The system detects servo degradation, loose cables, and calibration drift before the user notices. An optional LLM layer translates anomalies into plain English: "Servo 4 load has increased 23% over the past week. This usually means gear wear or increased friction. Consider inspecting the elbow joint."
- **Cross-robot learning via federated fleet intelligence**. Phase 1: centralized aggregation of anonymized calibration data and protection settings, producing "recommended defaults" that improve with every new arm. Phase 2: differential privacy when the fleet exceeds 1,000 instances. Phase 3: true federated learning with Flower (flwr.ai) for fleet-wide anomaly detection -- each arm trains locally, shares only model parameters, never raw telemetry. The result: when one SO-101 discovers that servo 3 drifts at temperatures above 45C, every SO-101 in the fleet learns to watch for it.
- **Natural language robot programming** ("pick up the red block"). Speech-to-text via Whisper, intent parsing via local SLM or cloud LLM, visual grounding via YOLO-World, analytical IK for trajectory planning -- full pipeline under 2 seconds.
- **MuJoCo digital twin in CI** -- every PR runs the actual armOS code against a physics-simulated SO-101. Chaos engineering injects voltage drops, communication timeouts, and servo failures into the simulation to prove resilience before users discover fragility.
- **Autonomous overnight data collection** -- DAgger-based (Dataset Aggregation) pipeline where the robot fills in easy trajectory variations autonomously after a human provides initial demonstrations.
- *"The robot that gets smarter every day"*

---

## Why armOS Wins

### vs. LeRobot Alone

LeRobot is a brilliant AI framework for robot learning. It is not an operating system. It requires a working Linux environment with correct Python versions, dependencies, and udev rules. It does not auto-detect hardware, diagnose servo problems, or provide a dashboard. armOS wraps LeRobot with everything it is missing -- hardware abstraction, diagnostics, profiles, and a TUI -- while contributing patches upstream. **armOS is complementary, not competitive.**

### vs. ROS2

ROS2 is an enterprise-grade distributed robotics framework. Its complexity is a feature for industrial teams managing fleets of warehouse robots. It is not a feature for a student trying to move a $220 arm. armOS occupies the "it just works" quadrant that ROS2 cannot reach without abandoning its architecture. For users who grow into ROS2, armOS provides a bridge.

### vs. phosphobot

phosphobot (YC-backed) ties software to their own hardware sales and a subscription model. armOS is open source (Apache 2.0), hardware-agnostic, and runs on any x86 laptop the user already owns. The bootable USB means zero commitment -- try it without buying anything from us, without touching your existing OS, without an internet connection.

### vs. Foxglove / Rerun.io

Foxglove ($58M raised) and Rerun.io ($20M raised) are visualization and data infrastructure tools. They do not control robots. armOS owns "getting started" and "daily operation"; they own "power user analysis." armOS integrates with them rather than competing.

### vs. NVIDIA Isaac

Isaac requires NVIDIA hardware and targets enterprise robotics. armOS runs on any Intel laptop. Different markets, different price points, different users. If a user grows from a $220 SO-101 into a Jetson-powered system, armOS provides an upgrade path via the Jetson Orin Nano image (Horizon 2-3).

### The Moats

1. **Diagnostic knowledge encoded as software.** We have already solved problems nobody else has documented -- overload protection tuning, sync_read retry patches, voltage sag detection, brltty conflicts. This cannot be replicated without months of hands-on hardware debugging.
2. **Network-effect profile ecosystem.** Every community-contributed robot profile makes armOS more valuable to all users and more attractive to new contributors. This is the Arduino library manager playbook.
3. **Zero-config USB boot.** Competitors require installation. armOS requires inserting a USB stick and pressing the power button. This is not a feature; it is a fundamentally different product category.
4. **AI-native interface.** Claude Code is not bolted on after the fact. The conversational onboarding IS the product. No other robotics tool has an AI that adapts to what it sees on the USB bus.
5. **Data flywheel.** More users produce more telemetry, more calibration data, and more profiles. Better defaults mean fewer problems. Fewer problems mean more users. This cycle compounds.

---

## The Market

| Segment | Size | Growth | Source |
|---------|------|--------|--------|
| Robot kits | $1.2-2.5B (2025) | $3.5-4.2B by 2032, 11-15% CAGR | Future Market Report |
| Educational robotics | $1.8B (2025) | $5.7B by 2030, 18.1% CAGR | Grand View Research |
| **armOS TAM** | **$3-4B** | **11-18% CAGR** | Combined |

The LeRobot ecosystem is the beachhead:

- **22,000+ GitHub stars**, 3,900+ forks
- **15,354 Discord members**
- **3,000+ hackathon participants** across 100+ cities (June 2025)
- **3,000-5,000 SO-101 arms** estimated in the field
- NVIDIA GR00T N1 model fine-tuned for LeRobot SO-100
- HuggingFace free robotics course built on LeRobot

An SO-101 at $220 plus an armOS USB stick equals a complete AI robotics workstation for under $250. Universal Robots and KUKA already ship USB sticks with their industrial robots -- armOS brings that same plug-and-play experience to the consumer market.

The broader context: $6B+ was committed to robotics startups in early 2025. Q2 2025 robotics deal value reached $8.8B. Figure AI raised $1B+ at a $39B valuation. Physical Intelligence raised $1.1B. HuggingFace acquired Pollen Robotics. **Embodied AI is the next frontier, and the hardware is finally cheap enough for everyone to participate.**

---

## Partnership Strategy

### Tier 1: Seeed Studio Bundle

Seeed Studio ($47M revenue, 252 employees) already sells SO-101 kits. The pitch is built around their economics: every SO-101 buyer who hits a setup problem either submits a support ticket ($5-15 to resolve) or returns the kit ($240 lost). If armOS prevents 50% of setup failures, that is direct savings per kit. The partnership ladder:

1. **Documentation** -- Seeed links to armOS in product docs (free, zero risk)
2. **Co-branded** -- "Recommended by armOS" badge on listings (free, brand association)
3. **Bundled** -- Pre-flashed USB in every kit ($3-5 per unit to armOS)
4. **Cloud revenue share** -- Seeed promotes armOS cloud training (10% of referred revenue)

### Tier 2: HuggingFace Certified Deployment

armOS becomes the recommended hardware deployment path for LeRobot. Joint blog post, mention in LeRobot documentation, shared Discord presence. HuggingFace has massive reach -- a single tweet from them can drive 1,000+ GitHub stars in a day. Their free robotics course needs a hardware lab component; armOS is the easiest path.

### Tier 3: "Works with armOS" Certification Program

Hardware vendors submit their robots for testing. armOS validates a profile. Certified products get a badge for their product listings and a dedicated page on armos.dev. Free for the first 20 products (seed the ecosystem), then $500-2,000 per certification. This is the WiFi Alliance model adapted for hobby robotics.

**Additional targets:** Waveshare (growing robot arm line), Feetech (servo manufacturer -- direct interest in reducing support burden), ROBOTIS (Koch arms, Dynamixel servos), Intel ("Robotics on Intel" co-marketing, OpenVINO integration), NVIDIA (Jetson edge deployment).

---

## How We Get There

The MVP ships in 9 sprints (18 weeks), built by one engineer with AI pair programming.

| Sprint | Weeks | Goal |
|--------|-------|------|
| 0 | 0-1 | CI/CD, test fixtures, MockServoProtocol, hardware inventory |
| 1 | 1-2 | Python package skeleton, CLI foundation, utility modules |
| 2 | 3-4 | Hardware abstraction layer + Feetech STS3215 driver |
| 3 | 5-6 | Robot profiles + SO-101 YAML profile + calibration |
| 4 | 7-8 | Diagnostics engine -- voltage, temperature, load monitoring |
| 5 | 9-10 | Telemetry streaming + safety watchdog |
| 6 | 11-12 | Calibration workflow + teleoperation |
| 7 | 13-14 | TUI dashboard -- the single-screen command center |
| 8 | 15-16 | USB image build pipeline (live Ubuntu + armOS pre-installed) |
| 9 | 17-18 | AI-assisted data collection + LeRobot integration |

**Post-MVP (Months 5-6):** Demo video production ($31 minimum viable, $150 high-quality -- entirely AI-generated hardware shots + real screen recordings, no camera crew needed). Open-source launch on GitHub. Community seeding on Hacker News, r/robotics, LeRobot Discord, and HuggingFace forums.

**Months 6-12:** First hardware partnership (Seeed Studio Tier 1). University pilot (Georgia Tech ECE 4560 is the primary target -- they already use SO-101). Robot profile bounty program ($50-500 per profile). "Robotics in 10 Lessons" curriculum for education distribution.

**Months 12-18:** Cloud training service launch. RPi 5 ARM image. LeKiwi profile. Fleet management dashboard. Marketplace beta. First armOS Conf (virtual, free).

---

## What Success Looks Like

### Year 1: Foundation

| KPI | Target |
|-----|--------|
| GitHub stars | 1,000+ |
| USB image downloads | 2,000+ |
| Discord members | 1,500 |
| Community-contributed robot profiles | 20+ |
| First-boot completion rate | 80% |
| Time from USB boot to first teleop | Under 5 minutes |
| Hardware partnerships signed | 1 (Seeed Studio Tier 1 minimum) |
| University pilots | 1 course, 20+ students |
| Revenue (conservative) | $8K |
| Revenue (moderate) | $56K |

### Year 2: Growth

| KPI | Target |
|-----|--------|
| Active users | 10,000+ |
| Robot profiles | 50+ |
| Cloud training runs | 500+/month |
| Education/enterprise customers | 5+ |
| Monthly recurring revenue | $10K+ |
| Revenue (moderate) | $265K |

### Year 3: Scale

| KPI | Target |
|-----|--------|
| armOS is the default answer to "how do I set up my robot arm?" | Industry standard for education |
| Active users | 50,000+ |
| Hardware partnerships | 3+ major distributors |
| Monthly recurring revenue | $50K+ |
| Revenue (moderate) | $600K |

---

## Why Now

1. **Hardware cost collapse.** A complete 6-DOF arm is $220 (was $5,000 five years ago). A mobile manipulator is $440.
2. **LeRobot exists.** HuggingFace democratized robot learning like they did NLP. 22,000 stars and accelerating.
3. **The SO-101 wave.** Thousands of kits shipping from Seeed Studio, Waveshare, and AliExpress -- all hitting the same setup problems.
4. **Small models are getting good fast.** Octo-Small (27M parameters) runs at 5-10 Hz on a CPU. In 2-3 years, 100M-parameter VLAs will match today's 7B models. CPU inference becomes increasingly viable.
5. **AI pair programming.** Claude Code can debug hardware problems in real-time, write servo drivers, and generate test suites. A solo developer with AI tools can build what used to require a team.
6. **Embodied AI is the next frontier.** $6B+ invested in robotics startups in 2025. Every major lab is building foundation models for physical intelligence.
7. **No one has built this.** Bootable USB for consumer robot arms is genuine whitespace. No funded competitor occupies this position.

---

## Core Principles

1. **Zero to robot in 5 minutes.** If it takes longer, we failed.
2. **Explain, don't error.** Every failure message tells you what happened, why, and how to fix it.
3. **Works offline.** Internet is optional after first boot. Ship a local LLM (Phi-3-mini, 2.3 GB) as a fallback for AI onboarding when Claude Code is unavailable.
4. **Open by default.** Apache 2.0 license. Community profiles. Upstream contributions to LeRobot.
5. **Hardware agnostic.** If it has servos and USB, armOS should support it. STS3215 today, CAN bus tomorrow, QDD actuators next year.
6. **AI-assisted, not AI-dependent.** Claude Code enhances the experience but is never required. Every workflow has a non-AI path.

---

*armOS: Boot from USB. Detect hardware. Start building.*
