# armOS — Vision Document

## One Sentence

**armOS is the Android of robotics** — a free, open operating system that makes any computer a robot brain in minutes.

## The Problem

Robotics in 2026 is where personal computing was in 1978. Every robot has its own software stack, its own drivers, its own configuration ritual. A PhD student spends 3 days installing ROS2. A hobbyist spends a weekend debugging USB serial drivers. A teacher gives up and shows YouTube videos instead of letting students touch real hardware.

The hardware is finally cheap enough ($200 for a complete 6-DOF arm). The AI is finally good enough (LeRobot can train policies from 50 demonstrations). **But the software layer between them is still a nightmare.**

## The Insight

We discovered this firsthand: setting up a single SO-101 arm on a Surface Pro 7 required:
- Patching the Linux kernel
- Debugging brltty stealing serial ports
- Diagnosing servo overload protection settings
- Building custom voltage monitoring tools
- Patching LeRobot's retry logic
- Tuning PID and protection registers by hand

Every single person who buys an SO-101 kit will hit some subset of these problems. **The knowledge to solve them exists — it's just trapped in GitHub issues, Discord threads, and Claude Code conversations.**

## The Vision

**armOS captures that knowledge in software.**

```
┌──────────────────────────────────────────────────────────────┐
│                        THE STACK                             │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐   │
│   │  Applications                                        │   │
│   │  • Teleop  • Data Collection  • Policy Inference     │   │
│   │  • Teaching  • Remote Operation  • Simulation        │   │
│   └──────────────────────────┬───────────────────────────┘   │
│   ┌──────────────────────────┴───────────────────────────┐   │
│   │  AI Framework Layer                                  │   │
│   │  • LeRobot  • ROS2 Bridge  • Custom Policies        │   │
│   └──────────────────────────┬───────────────────────────┘   │
│   ┌──────────────────────────┴───────────────────────────┐   │
│   │  armOS Core                                          │   │
│   │  • Hardware Abstraction  • Robot Profiles            │   │
│   │  • Diagnostics Engine    • Telemetry                 │   │
│   │  • Calibration           • Safety Watchdog           │   │
│   └──────────────────────────┬───────────────────────────┘   │
│   ┌──────────────────────────┴───────────────────────────┐   │
│   │  Hardware                                            │   │
│   │  • Any servo protocol  • Any camera  • Any computer  │   │
│   └──────────────────────────────────────────────────────┘   │
│                                                              │
│   Boot from USB. Detect hardware. Start building.            │
└──────────────────────────────────────────────────────────────┘
```

## Three Horizons

### Horizon 1: The USB Stick (Now - 6 months)

- Boot any x86 machine from USB
- Auto-detect SO-101 and other popular arms
- Calibrate, teleop, collect data — all from a TUI
- Built-in diagnostics that explain what's wrong in plain English
- *"The fastest path from unboxing a robot arm to moving it"*

### Horizon 2: The Platform (6-18 months)

- Community robot profile repository (like Docker Hub for robots)
- Cloud training pipeline — collect data locally, train in the cloud, deploy back
- Plugin ecosystem for new servo protocols, sensors, grippers
- Web dashboard for fleet management (classroom with 30 arms)
- ROS2 bridge for interop with the industrial ecosystem
- *"The platform that robot hardware companies ship with their products"*

### Horizon 3: The Intelligence Layer (18-36 months)

- AI agent that watches your robot and suggests improvements
- Automatic anomaly detection (servo degrading, cable loose, calibration drifting)
- Cross-robot learning — what works on one SO-101 helps all SO-101s
- Natural language robot programming ("pick up the red block")
- Sim-to-real pipeline built in
- *"The robot that gets smarter every day"*

## Why Now

1. **Hardware cost collapse** — A complete 6-DOF arm is $200 (was $5,000 five years ago)
2. **LeRobot exists** — HuggingFace democratized robot learning like they did NLP
3. **Claude Code exists** — An AI that can debug hardware problems in real-time
4. **The SO-101 wave** — Thousands of kits shipping, all hitting the same setup problems
5. **Embodied AI is the next frontier** — Every major lab is investing

## The Moat

1. **The diagnostic knowledge** — We've already solved problems nobody else has documented (overload protection tuning, sync_read retry patches, voltage monitoring)
2. **Community profiles** — Network effect: every new robot profile makes armOS more valuable
3. **Boot-from-USB** — Zero commitment. Try it without touching your existing OS
4. **AI-native** — Claude Code integration is not an afterthought, it's the core experience
5. **Data flywheel** — More users → more telemetry data → better defaults → fewer problems → more users

## What Success Looks Like

- **Year 1**: 1,000 GitHub stars. Every SO-101 tutorial recommends armOS. Seeed Studio bundles a USB stick.
- **Year 2**: 10,000 active users. 50+ robot profiles contributed. Cloud training has paying customers.
- **Year 3**: armOS is the default answer to "how do I set up my robot arm?" Industry standard for education.

## Core Principles

1. **Zero to robot in 5 minutes** — If it takes longer, we failed
2. **Explain, don't error** — Every failure message tells you what happened, why, and how to fix it
3. **Works offline** — Internet is optional after first boot
4. **Open by default** — MIT license, community profiles, upstream contributions
5. **Hardware agnostic** — If it has servos and USB, armOS should support it
6. **AI-assisted, not AI-dependent** — Claude Code enhances the experience but isn't required

---

*armOS: Boot from USB. Detect hardware. Start building.*
