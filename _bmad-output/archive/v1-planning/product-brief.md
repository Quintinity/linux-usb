# Product Brief: RobotOS USB

## Vision

Transform the existing linux-usb project from a single-purpose Surface Pro 7 + SO-101 setup tool into a **universal robot operating system on a USB stick**. Plug the USB into any x86 computer, boot it, connect any supported robotic hardware, and have a working robot control station in minutes.

## Problem Statement

Setting up a computer to control a robot arm today requires:
- Hours of manual Linux configuration
- Deep knowledge of servo protocols, USB serial, udev rules, Python environments
- Hardware-specific kernel patches and driver installation
- Debugging communication failures with no visibility into servo state
- No standardized way to connect different robot hardware

Even with LeRobot, the setup process is fragile and hardware-specific. Our experience setting up the SO-101 on a Surface Pro 7 revealed dozens of failure modes (brltty stealing serial ports, power supply issues, servo overload protection, sync_read failures) that required deep debugging with custom diagnostic tools.

## Proposed Solution

**RobotOS** — a bootable USB operating system purpose-built for robotics:

### Core Capabilities

1. **Boot-from-USB**: Live or installed Ubuntu-based OS with all robotics dependencies pre-configured
2. **Hardware Auto-Detection**: Plug in a servo controller, camera, or sensor — the system identifies it, loads the right drivers, and configures access
3. **Universal Robot API**: A standard abstraction layer between hardware (Feetech, Dynamixel, etc.) and AI frameworks (LeRobot, ROS2, etc.)
4. **AI-Assisted Setup**: Claude Code as an intelligent configuration agent that adapts to the specific hardware detected
5. **Built-in Diagnostics**: The diagnostic suite (voltage monitoring, communication testing, overload detection) as first-class system tools
6. **Plug-and-Play Robot Profiles**: Pre-configured profiles for popular robots (SO-101, Koch, Aloha, etc.) that auto-apply calibration, protection settings, and teleop configs

### Hardware Abstraction

```
┌─────────────────────────────────────────────────┐
│              AI / Application Layer              │
│    (LeRobot, ROS2, Custom Policies, Teleop)     │
├─────────────────────────────────────────────────┤
│              RobotOS API Layer                   │
│   (Standard interface: connect, read, write,    │
│    calibrate, diagnose, monitor)                │
├─────────────────────────────────────────────────┤
│            Hardware Drivers                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Feetech  │ │Dynamixel │ │  Custom  │       │
│  │ STS3215  │ │  XL330   │ │ Drivers  │       │
│  └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────┤
│              USB / Serial Layer                  │
│         (auto-detect, udev, permissions)        │
└─────────────────────────────────────────────────┘
```

## Target Users

1. **Robotics hobbyists** — Want to get a robot arm working without Linux expertise
2. **AI researchers** — Need a quick way to collect training data on physical robots
3. **Educators** — Teaching robotics in classrooms where setup time must be minimal
4. **Makers/hackers** — Building custom robots and need a standard control platform

## Competitive Landscape

- **ROS2**: Industry standard but massive, complex to set up, steep learning curve
- **LeRobot**: Great AI framework but no OS layer, no hardware abstraction, fragile setup
- **Raspberry Pi OS**: General purpose, not robotics-specific
- **NVIDIA Isaac**: GPU-dependent, expensive hardware requirement

**RobotOS differentiator**: Zero-config, USB-bootable, AI-assisted, works on any x86 hardware you already own.

## Success Metrics

- Boot to working robot teleop in under 5 minutes on fresh hardware
- Support 3+ robot arm platforms (SO-101, Koch, Aloha)
- Support 3+ servo protocols (Feetech, Dynamixel, CAN-based)
- Zero manual terminal commands required for basic operation
- Community adoption: 100+ stars on GitHub within 6 months

## Constraints

- Must remain bootable from USB (no hard drive installation required)
- Must work without GPU (Intel integrated graphics as baseline)
- Must be fully open source
- Must not require internet after initial setup
- Python-based for maximum accessibility

## What We Already Have

- Working USB flash + install pipeline (flash.ps1, BOOT-GUIDE.md)
- AI-driven 5-phase setup automation (CLAUDE.md + setup.sh)
- LeRobot v0.5.0 integration with SO-101
- Comprehensive servo diagnostic suite (diagnose_arms.py, monitor_arm.py, etc.)
- Servo protection tuning knowledge and patches
- Memory/context portability system via claude-context/

## What Needs to Be Built

1. Hardware auto-detection layer (USB device enumeration + robot profile matching)
2. Universal robot API abstracting servo protocols
3. Pre-built OS image (instead of install-from-live-USB)
4. Web-based or TUI dashboard for robot status and control
5. Robot profile system (YAML-based hardware descriptions)
6. Plugin architecture for new robot hardware support
7. Offline-capable AI assistant integration

---

_Product brief for RobotOS USB — a universal robot operating system_
