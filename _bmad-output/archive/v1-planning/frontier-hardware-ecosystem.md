# armOS Frontier Hardware Ecosystem Analysis

**Date:** 2026-03-15
**Author:** Mary (Analyst)
**Status:** Research Complete
**Scope:** Hardware frontiers beyond the SO-101 arm -- what armOS should target next, with real products, prices, and availability data.

---

## Table of Contents

1. [Beyond Robot Arms](#1-beyond-robot-arms)
2. [Compute Platforms Beyond x86](#2-compute-platforms-beyond-x86)
3. [Sensor Ecosystem](#3-sensor-ecosystem)
4. [Emerging Servo Technologies](#4-emerging-servo-technologies)
5. [Novel Form Factors](#5-novel-form-factors)
6. [Open Hardware Integration](#6-open-hardware-integration)
7. [Priority Matrix](#7-priority-matrix)
8. [Sources](#sources)

---

## 1. Beyond Robot Arms

### 1.1 Mobile Bases

| Product | Price | Notes |
|---------|-------|-------|
| **LeKiwi (LeRobot)** | ~$220+ (base kit) | 3-wheel omnidirectional Kiwi drive. Mounts SO-101 arm on top. Raspberry Pi 5 compatible. Fully integrated with LeRobot framework. **This is the #1 expansion target for armOS.** |
| **TurtleBot 4 Lite** | ~$1,200 | iRobot Create3 base + RPi 4 + OAK-D + 2D LiDAR. ROS2 native. Gold standard for education but 5x the price of an SO-101. |
| **TurtleBot 4 Standard** | ~$1,850 | Adds enclosure, display, more sensors. |
| **XLeRobot Mobile** | ~$170 (3,999 CNY for full system) | Chinese open-source alternative. Sim-to-real with ManiSkill. 1.6k GitHub stars and growing fast. |

**armOS opportunity:** LeKiwi is the obvious first target. It shares the SO-101 servo ecosystem (Feetech STS3215), uses the same LeRobot framework, and the price point ($220 base + $220 arm = ~$440 mobile manipulator) is in the sweet spot. armOS profile support for LeKiwi would require adding motor control for the 3 base drive motors and basic navigation.

### 1.2 Humanoid Robots

| Product | Price | DOF | Status |
|---------|-------|-----|--------|
| **Reachy Mini Lite** | $299 | Head movement, speech | Shipping late 2025. Needs external compute (USB to host PC). Desktop form factor, 28cm tall. |
| **Reachy Mini Wireless** | $449 | Same + RPi 5 onboard | Shipping fall 2025 through 2026. Self-contained. |
| **HopeJr** | ~$3,000 | 66 DOF, walks | Full humanoid. Waitlist open, first units shipping late 2025/early 2026. Open source. |
| **PAROL6** | ~$3,570 (assembled) | 6-DOF arm | Industrial-grade desktop arm. Open source BOM for self-build. 400mm reach. |

**armOS opportunity:** Reachy Mini Lite at $299 is compelling -- it connects via USB to a host computer, which is exactly the armOS use case. A Reachy Mini profile could ship in Horizon 2. HopeJr at $3,000 is further out but represents the direction the ecosystem is moving.

### 1.3 Grippers and End-Effectors

| Product | Price | Interface | Notes |
|---------|-------|-----------|-------|
| **Waveshare Gripper-A** | $47 | STS3215 serial bus | Direct SO-101 compatible. Same servo protocol, same bus. Plug and play. |
| **Waveshare Gripper-B** | $80 | CF35-12 serial bus | Higher torque (35kg.cm), constant force control. |
| **ServoCity Parallel Gripper Kit A** | ~$30-50 | Standard servo PWM | Requires PWM adapter. Not bus-compatible. |
| **Pololu Micro Gripper Kit** | ~$25 | Standard servo PWM | Tiny. Position feedback via potentiometer. |

**armOS opportunity:** Waveshare Gripper-A is the immediate target. Same STS3215 bus as the SO-101 means zero new driver work -- just a profile extension. The gripper appears as servo ID 7 on the existing bus. This could ship in armOS v1.0 as a profile option.

### 1.4 Drones with Manipulation

Aerial manipulation remains research-grade. An [open-source soft robotic platform for autonomous aerial manipulation](https://arxiv.org/abs/2409.07662) was published in 2024 using a Fin Ray-inspired gripper on a hexarotor with Dynamixel servos. The HKUST OmniNxt platform provides open-source omnidirectional aerial perception.

**armOS opportunity:** Not viable for Horizon 1-2. Drones involve flight controllers (PX4/ArduPilot), safety certification issues, and a fundamentally different control loop. Park this for Horizon 3.

### 1.5 Soft Robotics

Soft dielectric elastomer actuators and pneumatic soft grippers are advancing rapidly in research but lack standardized USB interfaces. The [Open Dynamic Robot Initiative](https://github.com/open-dynamic-robot-initiative/open_robot_actuator_hardware) provides open-source brushless actuator hardware under BSD 3-clause, and [OpenQDD](https://www.aaedmusa.com/projects/openqdd) offers 3D-printable quasi-direct-drive actuators.

**armOS opportunity:** Soft robotics lacks the USB-serial standardization that makes armOS valuable. Monitor but do not invest until interface standards emerge.

### 1.6 USB-Connected Robotic Hardware Under $500 (Summary)

| Category | Product | Price | USB? | armOS Priority |
|----------|---------|-------|------|----------------|
| Arm | SO-101 | $220 | Yes (CH340) | **Shipped** |
| Arm | XLeRobot | ~$170 | Yes | High |
| Gripper | Waveshare Gripper-A | $47 | Yes (STS3215 bus) | **High** |
| Mobile base | LeKiwi | ~$220 | Yes (RPi USB) | **High** |
| Humanoid | Reachy Mini Lite | $299 | Yes (USB to host) | Medium |
| Depth camera | OAK-D Lite | $149 | Yes (USB-C) | **High** |
| LiDAR | RPLiDAR A1 | ~$100 | Yes (USB) | Medium |
| Depth camera | RealSense D405 | $259 | Yes (USB-C) | Medium |

---

## 2. Compute Platforms Beyond x86

### 2.1 Raspberry Pi 5

| Variant | Price | Notes |
|---------|-------|-------|
| RPi 5 1GB | $45 | Too little RAM for LeRobot |
| RPi 5 4GB | $60 | Minimum viable for inference |
| RPi 5 8GB | ~$90 (post Feb 2026 price hike) | Recommended for LeRobot. RAM prices rising due to memory supply issues. |

**Can armOS boot on ARM?** Not as a bootable USB in the current architecture. The USB ISO is x86-only (GRUB + linux-surface kernel). However, armOS could ship as:
- A **Raspberry Pi OS image** (`.img` file flashed to SD card) -- analogous to the USB stick but for ARM
- A **Docker container** running on stock Raspberry Pi OS
- A **pip-installable package** that configures an existing RPi installation

The LeKiwi project already runs LeRobot on RPi 5, proving the compute is sufficient for inference and teleoperation. The RPi 5's Broadcom BCM2712 (quad Cortex-A76 @ 2.4GHz) handles the servo control loop comfortably.

**armOS opportunity:** High priority for Horizon 2. The RPi 5 is the natural compute platform for embedded robots (LeKiwi, Reachy Mini Wireless). armOS should provide an ARM image alongside the x86 USB ISO.

### 2.2 NVIDIA Jetson

| Variant | Price | AI Performance | Notes |
|---------|-------|---------------|-------|
| **Jetson Orin Nano Super** | $249 | 67 TOPS | Best value. 1.7x improvement over predecessor. Supports transformer-based models. |
| Jetson Orin NX 8GB | ~$399 | 70 TOPS | More IO, more RAM |
| Jetson AGX Orin 32GB | ~$999 | 200 TOPS | Overkill for arm-scale robots |

The Jetson Orin Nano Super at $249 is the GPU-accelerated compute target. It runs Linux (JetPack/Ubuntu-based), supports CUDA and TensorRT, and can do real-time policy inference that the RPi 5 and Intel integrated graphics cannot.

**armOS opportunity:** Horizon 2-3. An armOS JetPack image would unlock GPU-accelerated inference for LeRobot policies. The `InferenceBackend` abstraction in the architecture (TensorRT backend) already accounts for this. The $249 price point makes it accessible for advanced users.

### 2.3 Other SBCs

| Board | Price | CPU | Notes |
|-------|-------|-----|-------|
| **Orange Pi 5 Plus** | ~$90-150 | Rockchip RK3588 (8-core A76/A55) | 6 TOPS NPU. Up to 32GB RAM. PCIe 3.0. Strong contender. |
| Orange Pi 5 | ~$60-80 | Rockchip RK3588S | Cheaper variant, still powerful |
| Pine64 (RK3566) | ~$50 | Rockchip RK3566 | Open hardware ethos. Mainline Linux. Less powerful. |
| BeagleBone AI-64 | ~$120 | TDA4VM (dual A72 + C7x DSP) | TI ecosystem. Good for real-time servo control. |
| Libre Computer ROC-RK3588-PC | ~$150 | RK3588 | Alternative RK3588 board |

**armOS opportunity:** The Orange Pi 5 Plus with its RK3588 and 6 TOPS NPU is interesting as a middle ground between RPi 5 (no AI acceleration) and Jetson ($249). However, the software ecosystem is weaker. RPi 5 and Jetson should be the primary ARM targets; Orange Pi support can follow community demand.

### 2.4 Apple Silicon (ARM Laptops)

Apple Silicon Macs can run armOS in a VM (UTM/Parallels running Ubuntu ARM). The limiting factor is USB passthrough -- servo controllers and cameras need to be forwarded from macOS to the VM. This works but adds latency and complexity.

**armOS opportunity:** Low priority. Mac users who want to try armOS can use the Docker container approach (Section 5.2). Native macOS support is not worth the engineering investment given the small overlap between Mac users and robotics hardware users.

---

## 3. Sensor Ecosystem

### 3.1 Depth Cameras

| Camera | Price | Range | Interface | Status |
|--------|-------|-------|-----------|--------|
| **Luxonis OAK-D Lite** | $149 | 40cm - 8m | USB-C | **Best value.** On-device NN inference (Myriad X). Currently out of stock, price increase coming April 2026. |
| Luxonis OAK-D S2 | ~$199 | 35cm - 10m | USB-C | Next-gen standard model |
| Luxonis OAK-D Pro | ~$299 | 20cm - 35m | USB-C | IR illumination for low-light |
| **RealSense D405** | $259 | 7cm - 50cm | USB-C | **Best for manipulation.** Sub-mm accuracy at close range. 42x42x23mm, 60g. Ideal for wrist-mounted. |
| RealSense D435i | ~$300 | 30cm - 3m | USB-C | General purpose. RealSense Inc. (spun out from Intel July 2025, $50M Series A) continuing production. |
| Stereolabs ZED 2 | ~$449 | 0.3m - 20m | USB 3.0 | High-end. Requires NVIDIA GPU for depth computation. Not suitable for armOS's Intel-only target. |
| Stereolabs ZED Mini | ~$399 | 0.1m - 15m | USB 3.0 | Same GPU requirement. |

**Cheapest viable depth camera in 2026:** The **Luxonis OAK-D Lite at $149** is the answer. It provides stereo depth + on-device AI inference via USB-C with <5W power draw. For close-range manipulation tasks (picking objects with a gripper), the **RealSense D405 at $259** is superior due to sub-millimeter accuracy at 7-50cm.

**Key development:** Intel spun off RealSense as an independent company (RealSense Inc.) in July 2025 with a $50M Series A and a partnership with dormakaba. The D400 family (D405, D415, D435, D455) continues production under the new entity. This resolves the "Intel is discontinuing RealSense" concern.

### 3.2 LiDAR

| Sensor | Price | Range | Interface | Notes |
|--------|-------|-------|-----------|-------|
| **RPLiDAR A1** | ~$100 | 12m, 360 deg | USB | Most popular budget LiDAR for robotics. 5.5Hz scan rate, 8000 samples/sec. |
| RPLiDAR A2M12 | ~$200 | 18m, 360 deg | USB | Faster, longer range |
| LD06 (LDRobot) | ~$30-50 | 12m, 360 deg | UART/USB | Ultra-budget. Quality varies. |

**armOS opportunity:** LiDAR matters for mobile bases (LeKiwi, TurtleBot). The RPLiDAR A1 at ~$100 is the standard. armOS should support it in the LeKiwi profile for basic obstacle avoidance and mapping.

### 3.3 Force/Torque Sensors

Commercial F/T sensors (Robotiq FT-300, OnRobot Hex) cost $2,000-5,000 -- far outside the armOS price range. However:

- **Stanford capacitive 6-axis F/T sensor**: Under $10 in materials. Open-source design using capacitive sensing. Published 2025. Not yet a commercial product.
- **Vision-based force sensing**: A 2026 paper describes a [3D-printed miniature gripper with integrated camera for vision-based F/T sensing](https://www.nature.com/articles/s44182-026-00075-2) -- manufactured in a single print on a consumer printer. No dedicated sensor hardware needed.
- **Servo current as proxy**: The STS3215 already reports load current, which can be used as a rough force proxy. armOS's telemetry system already captures this data.

**armOS opportunity:** Skip dedicated F/T sensors for now. Use servo load current feedback (already available) and vision-based approaches as they mature. Add a `force_estimation` module in Horizon 3 that uses camera + servo current fusion.

---

## 4. Emerging Servo Technologies

### 4.1 Current Standard: Feetech STS3215

- **Price:** ~$15-23 per servo (varies by supplier and voltage variant)
- **Interface:** TTL serial bus (half-duplex UART via CH340 USB adapter)
- **Torque:** 19kg.cm @ 7.4V, 30kg.cm @ 12V
- **Feedback:** Position (12-bit magnetic encoder), speed, voltage, current, temperature, load
- **Limitations:** Brushed DC motor with plastic/metal gears. Gear backlash limits precision. ~0.1 degree resolution.

The STS3215 dominates the sub-$500 robot arm market due to its combination of low cost, serial bus daisy-chaining, and rich feedback. It is not being "replaced" in the near term -- it occupies a price point that brushless alternatives cannot yet match.

### 4.2 Brushless Servo Actuators

| Product | Price | Interface | Torque | Notes |
|---------|-------|-----------|--------|-------|
| **MyActuator RMD-L 4015** | ~$150 | CAN bus | Low | Smallest RMD. Entry-level brushless. |
| MyActuator RMD-X6 S2 | ~$200+ | CAN bus | 18 N.m | 36:1 reducer. Dual encoder. |
| MyActuator RMD-X8 S2 V3 | ~$300+ | CAN bus / RS485 | 25 N.m | Popular for medium robot arms. |
| MyActuator RMD-X10 S2 V3 | ~$400+ | CAN bus | 50+ N.m | Large arm joints. 48V. |

MyActuator's RMD series represents the next step up from the STS3215. They use FOC (Field Oriented Control) for smooth motion, have zero backlash planetary reducers, and dual encoders for absolute position. The price premium is 10-20x over the STS3215.

**armOS opportunity:** CAN bus support is a Horizon 2-3 feature. It requires a USB-to-CAN adapter ($15-30, e.g., CANable) and a new servo protocol driver. But it unlocks a whole class of higher-performance hardware.

### 4.3 CAN-Bus Servos for Humanoids (Damiao)

| Model | Price | Torque | Notes |
|-------|-------|--------|-------|
| **DM-J4310-2EC** | $116 | Low | Smallest joint. Good for wrist/finger. |
| DM-J4340-2EC | $155 | Medium | Arm joints. Dual encoder. |
| DM-J8006-2EC | $214 | High | Shoulder/hip joints. |
| DM-J10010-2EC | $357-503 | Very high | Heavy-duty joints. |

Damiao DM-J series motors are the go-to for Chinese open-source humanoid projects (including HopeJr-class robots). They support MIT mode (direct torque control), speed mode, and position mode over CAN bus at 1Mbps with real-time feedback.

**armOS opportunity:** Same as MyActuator -- CAN bus driver work enables both ecosystems. A single `can_servo_driver` module with per-manufacturer protocol plugins would cover MyActuator RMD, Damiao DM-J, and CubeMars AK series.

### 4.4 Quasi-Direct Drive (QDD) Actuators

| Product | Price | Notes |
|---------|-------|-------|
| **CubeMars AK10-9** (Skyentific edition) | ~$150-200 | Popular with YouTube robotics community. 18 N.m rated, 53 N.m peak. |
| CubeMars AKE80-8 KV30 | ~$300+ | 52 N.m/kg torque density. 9 arcmin backlash. |
| CubeMars AKE90-8 KV35 | ~$400+ | 121 N.m/kg. Research-grade. |
| **OpenQDD** | ~$50 (self-build) | 3D-printed, open-source. Good for learning. |

QDD actuators skip the gearbox entirely (or use very low ratio planetary gears), relying on high-torque brushless motors for direct drive. This gives backdrivability (the robot feels compliant when you push it), which is critical for safe human-robot interaction and learning from demonstration.

**armOS opportunity:** QDD actuators are the future of compliant manipulation. armOS should plan for CAN bus support (which covers QDD actuators from CubeMars, MyActuator, and Damiao simultaneously).

### 4.5 What Replaces the STS3215?

Nothing replaces it at its price point ($15-23). The STS3215 will remain the standard for sub-$500 robot arms for at least 2-3 more years. The upgrade path is:

1. **STS3215** ($15-23) -- Current. Brushed, geared, TTL serial. Good enough for learning and data collection.
2. **Damiao DM-J4310** ($116) -- Next step. Brushless, CAN bus, direct drive. For users who outgrow the STS3215.
3. **MyActuator RMD-X8** ($300+) -- Professional. High torque, dual encoder. For research labs.
4. **CubeMars AKE series** ($300+) -- Cutting edge. QDD with backdrivability. For compliant manipulation research.

armOS should support this upgrade path: same software, different profile, better hardware.

---

## 5. Novel Form Factors

### 5.1 Embedded Brain (RPi Inside the Robot)

The LeKiwi already does this -- a Raspberry Pi 5 sits on the mobile base, running LeRobot directly. The host computer only handles teleoperation input (leader arm).

**armOS as an embedded image:** An armOS Raspberry Pi image pre-configured for a specific robot (LeKiwi, Reachy Mini) would eliminate the "boot from USB" step entirely. Flash the SD card, insert it, power on, and the robot is ready. This is the natural evolution for robots with onboard compute.

**Implementation:** Yocto or Buildroot-based minimal Linux image with armOS pre-installed. Or simpler: a Raspberry Pi OS image with armOS installed via `pip install armos` during image build.

### 5.2 Docker Container

```
docker run -it --privileged --device=/dev/ttyUSB0 armos/armos:latest
```

**Advantages:**
- Works on any Linux host (x86 or ARM) without rebooting
- No conflict with host OS packages
- Easy version management and rollback
- CI/CD friendly for testing

**Disadvantages:**
- `--privileged` and `--device` flags needed for USB access (security concern)
- Adds ~50ms latency for USB serial passthrough (negligible for servo control)
- Users must already have Docker installed (not zero-knowledge-required)

**armOS opportunity:** Docker is the right delivery mechanism for developers and CI environments. It complements (not replaces) the USB boot image for the zero-to-robot experience. Ship both starting Horizon 2.

### 5.3 Cloud Teleoperation (5G Edge)

In February 2026, NTT DOCOMO and Keio University demonstrated real-time robot teleoperation over commercial 5G with haptic feedback using Configured Grant for deterministic low-latency scheduling. The system achieved stable control of a remote robot arm with tactile and force feedback.

Advantech is shipping edge AI solutions with NVIDIA Jetson Thor for robotics, combining Docker containers, 5G connectivity, and GPU inference at the edge.

**armOS opportunity:** Cloud/remote teleoperation is Horizon 3. The technical stack is: armOS on the robot (embedded) + 5G/WiFi + armOS TUI on the operator's machine. The existing WebSocket-based fleet management architecture (Section 4 of architecture-enhancements.md) could be extended for remote teleoperation with latency-compensating control.

### 5.4 Phone via USB-OTG

Android phones support USB-OTG, which can connect to CH340 USB-serial adapters. Theoretically, an Android app could communicate with STS3215 servos directly.

**armOS opportunity:** Very low priority. The Android app development effort is high, and phones lack the compute for LeRobot inference. A phone-as-camera (streaming video to armOS over WiFi) is more practical than phone-as-brain.

---

## 6. Open Hardware Integration

### 6.1 URDF/MJCF Model Library

[URDF Hub](https://www.urdfhub.com/) provides 50+ open-source robot models in URDF and XACRO formats, compatible with Gazebo, Isaac Sim, PyBullet, and MuJoCo. Recent developments include:

- **URDF+**: Extended format supporting kinematic loops (parallel mechanisms)
- **URDD**: Universal Robot Description Directory -- modular JSON/YAML representation
- **URDF Studio**: Web-based visual URDF editor with generative AI assistance

armOS robot profiles (YAML) should include a `urdf_path` field pointing to the robot's URDF model:

```yaml
# In profile.yaml
simulation:
  urdf: models/so101.urdf
  mjcf: models/so101.xml
  scale: 1.0
```

This enables sim-to-real workflows: simulate in MuJoCo/Isaac, deploy on armOS.

**armOS opportunity:** Ship URDF models for all supported robots in the profile registry. This is a Horizon 2 feature that connects armOS to the broader simulation ecosystem.

### 6.2 Standard Connector Pinouts

The hobby robotics world lacks connector standardization. The SO-101 uses:
- **Servo bus:** 3-pin Feetech TTL (GND, VCC, DATA) -- proprietary connector
- **USB:** USB-A to CH340 adapter
- **Power:** Barrel jack (12V) or direct wire

armOS cannot fix hardware connector standards, but it can document them exhaustively in robot profiles and provide wiring diagrams in the diagnostics TUI ("Connect the white wire to DATA, red to VCC, black to GND").

### 6.3 Power Distribution

The SO-101 power architecture is simple (single 12V supply, servos in parallel). More complex robots (mobile bases, humanoids) need:
- Voltage regulation (12V bus servos + 5V logic + 3.3V sensors)
- Current monitoring per limb
- E-stop (emergency power cutoff)
- Battery management (for mobile robots)

Open-source power distribution boards exist in the drone ecosystem (PDB/BEC boards, $10-30) but nothing standardized for robot arms.

**armOS opportunity:** Not a hardware problem armOS solves directly, but the diagnostics engine should monitor voltage and current (already implemented for SO-101) and provide alerts when power is insufficient. Extend this to per-joint current monitoring for multi-limb robots.

### 6.4 3D-Printable Adapter Plates

The LeRobot ecosystem is built on 3D printing. Adapter plates between components (arm-to-base, gripper-to-wrist, camera-to-frame) are typically custom STL files shared on GitHub.

**armOS opportunity:** The profile registry should include STL files for standard adapters. When a user installs the `so101-lekiwi` profile, they get the mounting bracket STL alongside the YAML configuration. This is low-effort, high-value.

---

## 7. Priority Matrix

### Horizon 1 (Now - 6 months): Ship with armOS v1.0

| Item | Effort | Impact | Notes |
|------|--------|--------|-------|
| Waveshare Gripper-A profile | Low | High | Same bus as SO-101. Profile addition only. |
| OAK-D Lite camera support | Medium | High | USB depth camera. Needs driver integration. |
| Voltage/current diagnostics for 12V systems | Low | High | Already partially implemented. |

### Horizon 2 (6-18 months): Platform Expansion

| Item | Effort | Impact | Notes |
|------|--------|--------|-------|
| **Raspberry Pi 5 ARM image** | High | **Very High** | Unlocks LeKiwi, Reachy Mini, embedded robots. |
| **LeKiwi mobile base profile** | Medium | **Very High** | First mobile robot. Huge community demand. |
| **Docker container delivery** | Medium | High | Developer-friendly. CI/CD. |
| CAN bus servo driver | High | High | Unlocks MyActuator, Damiao, CubeMars. |
| RPLiDAR A1 support | Low | Medium | Needed for LeKiwi navigation. |
| Reachy Mini Lite profile | Medium | Medium | $299 humanoid with USB interface. |
| URDF models in profiles | Low | Medium | Sim-to-real bridge. |
| RealSense D405 support | Low | Medium | Best close-range depth for manipulation. |

### Horizon 3 (18-36 months): Next Generation

| Item | Effort | Impact | Notes |
|------|--------|--------|-------|
| Jetson Orin Nano image | High | High | GPU-accelerated inference. |
| HopeJr humanoid profile | Very High | Medium | 66-DOF, complex control. |
| Cloud teleoperation (5G) | Very High | Medium | Remote robot control. |
| QDD actuator profiles | Medium | Medium | Compliant manipulation. |
| Force estimation module | High | Medium | Camera + servo current fusion. |

### Do Not Pursue

| Item | Reason |
|------|--------|
| Drone manipulation | Entirely different control domain. Safety certification issues. |
| Soft robotics | No standardized USB interface. |
| Phone as robot brain | Insufficient compute. High app development cost. |
| Apple Silicon native | Tiny market overlap. Docker covers the use case. |
| ZED cameras | Require NVIDIA GPU for depth. Incompatible with Intel-only target. |

---

## Sources

### Mobile Bases & Humanoids
- [LeKiwi - Hugging Face Documentation](https://huggingface.co/docs/lerobot/en/lekiwi)
- [LeKiwi Bundle - ROBOTIS](https://robotis.us/lekiwi-bundle-low-cost-mobile-manpulator/)
- [Seeed Studio LeKiwi Kit (12V) - OpenELAB](https://openelab.io/products/seeed-studio-lekiwi-kit12v-version-mobile-base-with-3d-printed-parts-and-battery)
- [Reachy Mini - Official Site](https://reachymini.net/)
- [Hugging Face unveils two new humanoid robots - TechCrunch](https://techcrunch.com/2025/05/29/hugging-face-unveils-two-new-humanoid-robots/)
- [Hugging Face opens orders for Reachy Mini - TechCrunch](https://techcrunch.com/2025/07/09/hugging-face-opens-up-orders-for-its-reachy-mini-desktop-robots/)
- [Affordable robotics: HuggingFace $3K humanoid and $300 desktop robot - NotebookCheck](https://www.notebookcheck.net/Affordable-robotics-Hugging-Face-introduces-3-000-humanoid-and-300-desktop-robot.1029422.0.html)
- [TurtleBot 4 - Clearpath Robotics](https://clearpathrobotics.com/turtlebot-4/)
- [XLeRobot - 36kr](https://eu.36kr.com/en/p/3456298009974408)
- [PAROL6 Robot Arm - Source Robotics](https://source-robotics.com/products/parol6-robotic-arm)

### Compute Platforms
- [Raspberry Pi 5 - Official](https://www.raspberrypi.com/products/raspberry-pi-5/)
- [RPi 5 price increases - NotebookCheck](https://www.notebookcheck.net/Raspberry-Pi-5-now-costs-up-to-205-due-to-RAM-crisis.1218213.0.html)
- [Jetson Orin Nano Super - NVIDIA](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/)
- [Jetson Orin Nano Super $249 announcement - HotHardware](https://hothardware.com/news/nvidia-jetson-orin-nano-affordable-ai-supercomputer)
- [Orange Pi SBC with 176 TOPS - NotebookCheck](https://www.notebookcheck.net/Orange-Pi-New-SBC-or-mini-PC-with-up-to-96GB-RAM-runs-circles-around-Raspberry-Pi-5-with-176-TOPS.1194902.0.html)
- [Best Raspberry Pi alternatives 2025 - Electromaker](https://www.electromaker.io/blog/article/10-best-raspberry-pi-alternatives)

### Sensors
- [OAK-D Lite - Luxonis Store](https://shop.luxonis.com/products/oak-d-lite-1)
- [RealSense D405 - RealSense](https://www.realsenseai.com/products/stereo-depth-camera-d405/)
- [Intel RealSense spin-off - Tom's Hardware](https://www.tomshardware.com/tech-industry/intel-to-spin-off-realsense-depth-camera-business-by-mid-2025-but-it-will-remain-part-of-the-intel-capital-portfolio)
- [Intel will keep selling RealSense - IEEE Spectrum](https://spectrum.ieee.org/intel-realsense)
- [RPLiDAR A1 - Slamtec](https://www.slamtec.com/en/lidar/a1)
- [3D-printed gripper with vision-based F/T sensing - Nature npj Robotics](https://www.nature.com/articles/s44182-026-00075-2)
- [Stanford capacitive F/T sensor - Stanford Tech Finder](https://techfinder.stanford.edu/technology/using-capacitive-sensing-create-robust-low-cost-force-torque-sensors-real-world-robotics)

### Servo Technologies
- [STS3215 Overview - Indystry.cc](https://indystry.cc/sts3215-best-motors-for-your-next-robot/)
- [MyActuator RMD Series - RobotShop](https://ca.robotshop.com/collections/myactuator)
- [Damiao DM-J Series - FoxTech Robot](https://www.foxtechrobotics.com/damiao-motor.html)
- [CubeMars AKE QDD Motors](https://www.cubemars.com/ake-qdd-motors.html)
- [AK10-9 QDD Actuator - Skyentific](https://skyentific.com/products/p10-planetary-qdd-actuator)
- [Open Dynamic Robot Initiative - GitHub](https://github.com/open-dynamic-robot-initiative/open_robot_actuator_hardware)
- [OpenQDD Actuator - Aaed Musa](https://www.aaedmusa.com/projects/openqdd)
- [Waveshare Gripper-A](https://www.waveshare.com/gripper-a.htm)

### Novel Form Factors
- [5G robot teleoperation - Interesting Engineering](https://interestingengineering.com/ai-robotics/5g-configured-grant-robot-teleoperation)
- [Open-source soft robotic aerial manipulation - arXiv](https://arxiv.org/abs/2409.07662)
- [Bimanual mobile manipulator under $1300 - arXiv](https://arxiv.org/html/2603.09051v1)

### Open Hardware
- [URDF Hub](https://www.urdfhub.com/)
- [Awesome URDF - GitHub](https://github.com/gbionics/awesome-urdf)
- [URDF Studio - GitHub](https://github.com/OpenLegged/URDF-Studio)
- [LeRobotDepot - Community hardware repository](https://github.com/maximilienroberti/lerobotdepot)
- [Awesome Open Source Robots - GitHub](https://github.com/PathOn-AI/awesome-opensource-robots)

---

*Frontier hardware ecosystem analysis for armOS -- Mary (Analyst)*
