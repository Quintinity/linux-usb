# Technical Research: Raspberry Pi 5 + AI HAT for armOS

**Date:** 2026-03-15
**Author:** Mary (Business Analyst)
**Status:** Research Complete

---

## Table of Contents

1. [Raspberry Pi AI HAT+ Product Line](#1-raspberry-pi-ai-hat-product-line)
2. [Hailo SDK and Model Compilation Pipeline](#2-hailo-sdk-and-model-compilation-pipeline)
3. [Hailo + LeRobot Integration Status](#3-hailo--lerobot-integration-status)
4. [Hailo + ONNX Runtime](#4-hailo--onnx-runtime)
5. [RPi 5 + LeRobot Performance](#5-rpi-5--lerobot-performance)
6. [RPi 5 Image Delivery Approaches](#6-rpi-5-image-delivery-approaches)
7. [RPi 5 USB-Serial Servo Control](#7-rpi-5-usb-serial-servo-control)
8. [Power Budget Analysis](#8-power-budget-analysis)
9. [Competing AI Accelerators](#9-competing-ai-accelerators)
10. [LeKiwi Hardware Stack](#10-lekiwi-hardware-stack)
11. [Real-World Projects and Gaps](#11-real-world-projects-and-gaps)
12. [Recommendations for armOS](#12-recommendations-for-armos)

---

## 1. Raspberry Pi AI HAT+ Product Line

Three products are currently available:

| Product | Chip | TOPS | On-board RAM | PCIe | Price | Status |
|---------|------|------|--------------|------|-------|--------|
| AI HAT+ 13 | Hailo-8L | 13 (INT8) | None | Gen 2 | $70 | Available |
| AI HAT+ 26 | Hailo-8 | 26 (INT8) | None | Gen 3 | $110 | Available |
| AI HAT+ 2 | Hailo-10H | 40 (INT4) | 8 GB | Gen 3 | $130 | Available (Jan 2026) |

### Key Specs

- **Interface:** All connect via the RPi 5's PCIe FPC connector. The 26 TOPS and 40 TOPS variants auto-negotiate PCIe Gen 3.0.
- **PCIe power limit:** 5W maximum through the RPi 5's PCIe FPC header.
- **Hailo-8L power:** ~1.5-2.5W typical (3-4 TOPS/W efficiency).
- **Hailo-8 power:** 2.5W typical, 8.25W max at full utilization (exceeds PCIe budget -- unclear how this is managed).
- **Hailo-10H power:** Max 3W (per RPi documentation).
- **AI HAT+ 2 differentiator:** The 8 GB on-board RAM enables LLMs, VLMs, and generative AI models that cannot fit on the Hailo-8/8L (which have no dedicated RAM and rely on streaming).

### Form Factor

All AI HAT+ boards sit on top of the RPi 5 via the standard 40-pin GPIO header for mechanical mounting and the PCIe FPC for data. They add ~10mm to the stack height.

**Sources:**
- [Raspberry Pi AI HAT+ Documentation](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html)
- [Jeff Geerling: Testing Raspberry Pi's AI Kit](https://www.jeffgeerling.com/blog/2024/testing-raspberry-pis-ai-kit-13-tops-70/)
- [Raspberry Pi AI HAT+ 2 Announcement](https://www.raspberrypi.com/news/introducing-the-raspberry-pi-ai-hat-plus-2-generative-ai-on-raspberry-pi-5/)
- [Buy AI HAT+](https://www.raspberrypi.com/products/ai-hat/)
- [Buy AI HAT+ 2](https://www.raspberrypi.com/products/ai-hat-plus-2/)

---

## 2. Hailo SDK and Model Compilation Pipeline

### The Pipeline: ONNX -> HAR -> HEF

Converting a model for Hailo follows three stages:

1. **Parse:** `translate_onnx_model()` converts ONNX to Hailo Archive (HAR) format
2. **Optimize & Quantize:** 8-bit quantization using calibration data (`client_runner.optimize(calib_dataset)`)
3. **Compile:** Generate the Hailo Executable Format (.hef) binary (`client_runner.compile()`)

### Tools Required

| Tool | Notes |
|------|-------|
| **Hailo Dataflow Compiler (DFC)** | x86 Linux only. Not on PyPI. Download from Hailo Developer Zone (registration required). |
| **Hailo Model Zoo** | Pre-built model scripts and calibration configs. GitHub: `hailo-ai/hailo_model_zoo` |
| **HailoRT** | Runtime library for RPi. Available via apt on Raspberry Pi OS. |
| **Python 3.10** | Required for DFC compatibility |

### Developer Experience Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Platform support | Poor | DFC only runs on x86 Linux. No ARM, no macOS, no Windows native. WSL works. |
| Installation | Poor | Not pip-installable. Manual download + registration wall. |
| RAM requirements | High | 32 GB RAM recommended for quantization |
| Documentation | Fair | Hailo docs exist but are fragmented across community wiki, PDF datasheets, and GitHub |
| Model coverage | Good for vision | YOLO, ResNet, MobileNet, EfficientNet, pose estimation all supported |
| Model coverage for robotics | **Non-existent** | No ACT, no diffusion policy, no VLA models in the model zoo |
| Python API | Good | Full programmatic access to parse/optimize/compile pipeline |
| CLI | Good | Single-command compilation for supported models |

### Critical Gap for armOS

The Hailo Model Zoo contains **zero robotics-specific models**. It is focused on:
- Image classification
- Object detection (YOLO family)
- Semantic/instance segmentation
- Pose estimation
- LLMs/VLMs (Hailo-10H only)

There are no pre-compiled HEF files for ACT (Action Chunking Transformer), diffusion policies, or any robot manipulation models. Any robotics model would need to be manually converted through the full DFC pipeline, which is non-trivial and may hit unsupported operator issues.

**Sources:**
- [Cytron: ONNX to HEF Conversion Tutorial](https://www.cytron.io/tutorial/raspberry-pi-ai-kit-onnx-to-hef-conversion)
- [RidgeRun: Convert ONNX Models to Hailo8L](https://www.ridgerun.ai/post/convert-onnx-model-to-hailo8l)
- [Hailo Community: Access to Dataflow Compiler](https://community.hailo.ai/t/access-to-hailo-dataflow-compiler-and-full-sdk/14792)
- [Hailo Model Zoo GitHub](https://github.com/hailo-ai/hailo_model_zoo)
- [Hailo Model Zoo GenAI GitHub](https://github.com/hailo-ai/hailo_model_zoo_genai)

---

## 3. Hailo + LeRobot Integration Status

### Current State: No Direct Integration Exists

As of March 2026, there is **no known integration** between Hailo's AI accelerator and LeRobot's inference pipeline. The two ecosystems are completely separate:

- **Hailo** focuses on vision models (detection, segmentation, pose estimation)
- **LeRobot** uses PyTorch-based policies (ACT, Diffusion Policy, Pi0/Pi0.5 VLA models)

### LeRobot's RPi 5 Support

LeRobot does support Raspberry Pi 5, but exclusively as a **thin client** in a client-server architecture:

- **PR #703** (by ma3oun) added RPi 5 client + remote inference server support
- The RPi 5 handles: sensor data acquisition, camera capture, servo control
- A remote GPU server handles: policy inference (ACT, Pi0, etc.)
- **Status:** PR #703 was closed as stale (Nov 2025) but the architecture concept lives on in LeRobot's current `PolicyServer` + `RobotClient` design

### LeRobot Async Inference Architecture

LeRobot now has a production `PolicyServer` pattern:
- Policy inference runs on accelerated hardware (GPU server)
- `RobotClient` runs on edge device (RPi 5) controlling servos and cameras
- Communication over ZeroMQ (TCP sockets)
- Async design decouples action prediction from execution (~2x speedup in task completion)

### What Would Be Needed for Hailo + LeRobot

To run LeRobot policies locally on Hailo, you would need to:
1. Export a trained ACT/Diffusion policy to ONNX
2. Compile it through the Hailo DFC to HEF format
3. Write a custom inference wrapper replacing PyTorch with HailoRT
4. Handle any unsupported operators (attention layers, etc.)

This is a significant engineering effort with no guarantee of success, as transformer-based models may not compile cleanly for the Hailo architecture.

**Sources:**
- [LeRobot PR #703: Raspberry Pi client and remote inference](https://github.com/huggingface/lerobot/pull/703)
- [LeRobot Async Inference Blog](https://huggingface.co/blog/async-robot-inference)
- [LeRobot Async Docs](https://huggingface.co/docs/lerobot/en/async)
- [Hailo RPi5 Examples GitHub](https://github.com/hailo-ai/hailo-rpi5-examples)

---

## 4. Hailo + ONNX Runtime

### Status: Preview Only, No Plans for Production Release

| Aspect | Detail |
|--------|--------|
| Repository | [fgervais/hailo-onnxruntime](https://github.com/fgervais/hailo-onnxruntime) (fork of onnxruntime) |
| Execution Provider | `HailoExecutionProvider` with `CPUExecutionProvider` fallback |
| Status | **PREVIEW** -- Hailo has explicitly stated: "Currently, there are no plans to further develop ONNX Runtime for Hailo devices." |
| Reason | "ONNX Runtime relies on a blocking execution model, which limits its ability to take full advantage of Hailo's architecture." |
| Recommendation | Hailo recommends HailoRT APIs directly for production use |

### Implications for armOS

This is a significant finding. The ONNX Runtime path -- which would be the cleanest way to integrate Hailo acceleration into LeRobot's existing PyTorch/ONNX pipeline -- is a **dead end**. Hailo has no plans to support it.

The only viable path for Hailo acceleration is:
1. Convert models to HEF via the Dataflow Compiler
2. Use HailoRT C++/Python APIs directly
3. This requires a custom inference backend, not a drop-in replacement

**Sources:**
- [Hailo Community: ONNXRuntime Release Plan](https://community.hailo.ai/t/hailo-ai-onnxruntime-release-plan/17300)
- [fgervais/hailo-onnxruntime GitHub](https://github.com/fgervais/hailo-onnxruntime)
- [Hailo Community: Running Model with ONNX Runtime](https://community.hailo.ai/t/running-model-on-hailo-with-onnx-runtime-workflow-clarification/17958)

---

## 5. RPi 5 + LeRobot Performance

### Published Benchmarks

No specific LeRobot + RPi 5 + ACT policy benchmarks have been published. Here is what we can infer from related data:

| Workload | Platform | Performance |
|----------|----------|-------------|
| YOLOv8n (640x640), CPU only | RPi 5 | ~12 FPS |
| YOLOv8n (640x640), Hailo-8 | RPi 5 | ~431 FPS |
| YOLOv8s (640x640), Hailo-8 | RPi 5 | ~491 FPS |
| ShuffleNet v2, CPU (2 threads) | RPi 5 | ~14 FPS (72ms latency) |
| Generic PyTorch (JIT compiled) | RPi 5 | ~30 FPS (vs 20 FPS without JIT) |
| LeRobot teleop (servo control loop) | RPi 5 | 30 FPS target (achievable per docs) |

### LeRobot-Specific Performance Notes

- LeRobot achieves **30 FPS teleop** on RPi 5 when using a dedicated process for camera image writing
- ACT policy inference was tested on RPi 5 via PR #703 but no latency numbers were published
- Pi0/Pi0.5 VLA models are far too large for local RPi 5 inference (requires GPU server)
- The `PolicyServer` async architecture reports **~2x speedup** in task completion time vs synchronous

### Estimated Local Inference (CPU-only on RPi 5)

Based on general PyTorch ARM performance:
- **ACT policy (small):** Likely 2-5 FPS on RPi 5 CPU (unaccelerated)
- **Diffusion policy:** Likely <1 FPS (iterative denoising is compute-heavy)
- **Pi0 VLA model:** Not feasible locally (3B+ parameters)

### Key Takeaway

The RPi 5 is viable as a **robot control client** (servo + camera at 30 FPS) but cannot run modern policy inference locally at useful speeds without acceleration. The recommended architecture is client-server.

**Sources:**
- [PyTorch: Real-Time Inference on RPi 4 and 5](https://docs.pytorch.org/tutorials/intermediate/realtime_rpi.html)
- [Seeed Studio: YOLOv8s Benchmark on RPi5 with Hailo 8L](https://wiki.seeedstudio.com/benchmark_on_rpi5_and_cm4_running_yolov8s_with_rpi_ai_kit/)
- [Raspberry Pi Forums: RPi5 Benchmark with Hailo](https://forums.raspberrypi.com/viewtopic.php?t=373867)

---

## 6. RPi 5 Image Delivery Approaches

### How LeKiwi / LeRobot Does It

LeKiwi uses the **simplest possible approach** -- no custom images, no Docker, no Ansible:

1. Flash standard **Raspberry Pi OS (64-bit)** via Raspberry Pi Imager
2. Enable SSH
3. SSH into the Pi
4. Clone the LeRobot repo and `pip install -e ".[lekiwi]"`
5. Configure motor IDs and calibrate

This is a manual, step-by-step process. There is no pre-built image, no automation tooling, and no containerization.

### How Other Projects Handle RPi Image Delivery

| Project | Approach | Notes |
|---------|----------|-------|
| **LeKiwi / LeRobot** | Manual: flash stock OS + pip install | No automation |
| **TurtleBot** | Custom Ubuntu + ROS 2 image | Pre-built .img files for SD card |
| **Home Assistant** | Custom OS image (HAOS) | Downloadable .img, OTA updates |
| **Frigate NVR** | Docker container on stock OS | `docker-compose.yml` |
| **balenaOS** | Custom minimal OS + Docker | Fleet management, OTA updates |
| **Ansible-based** | Stock OS + Ansible playbooks | e.g., `rpi-automation/infra-ansible` |

### Recommendation for armOS

For a product, the LeKiwi approach (manual pip install) is not scalable. Options ranked by maturity:

1. **Custom Raspberry Pi OS image** (`.img` file) -- most user-friendly, hardest to maintain
2. **Docker on stock Raspberry Pi OS** -- good balance of reproducibility and flexibility
3. **Ansible playbook on stock OS** -- good for fleet management, requires SSH access
4. **balenaOS** -- best for fleet management and OTA, adds vendor dependency

**Sources:**
- [LeKiwi Documentation (HuggingFace)](https://huggingface.co/docs/lerobot/lekiwi)
- [LeKiwi Software Setup (DeepWiki)](https://deepwiki.com/SIGRobotics-UIUC/LeKiwi/5-software-setup)
- [Seeed Studio: LeKiwi in LeRobot](https://wiki.seeedstudio.com/lerobot_lekiwi/)

---

## 7. RPi 5 USB-Serial Servo Control

### Feetech STS3215 Serial Protocol

| Parameter | Value |
|-----------|-------|
| Protocol | Half-duplex async serial (TTL) |
| Default baud rate | 1,000,000 bps (1 Mbaud) |
| Supported baud rates | 38,400 - 1,000,000 bps |
| ID range | 0-253 (bus supports 254 devices) |
| Connector | Daisy-chain bus (single data wire) |

### USB-to-Serial Adapter Comparison

| Chip | Max Baud | 1 Mbaud Support | Cost | Reliability | Notes |
|------|----------|-----------------|------|-------------|-------|
| **CH340** | 1 Mbps+ | Yes, reliable | $0.50-1.00 | Good on Linux | Windows 11 driver issues; LeRobot uses these |
| **CP2102** | 500 Kbps | No (need CP2102N for 3 Mbps) | $1-3 | Excellent | Original CP2102 caps at 500K; CP2102N is fine |
| **FTDI FT232** | 3 Mbps | Yes | $3-5 | Gold standard | Most expensive but best driver support |

### Latency Considerations

- The Feetech servo driver board used with LeRobot typically uses a CH340-based USB-to-serial chip
- USB-serial adapters on Linux have a default `latency_timer` of 16ms, which can be reduced to 1ms:
  ```
  echo 1 | sudo tee /sys/bus/usb-serial/devices/ttyUSB0/latency_timer
  ```
- At 1 Mbaud, a 10-byte servo command takes ~0.1ms wire time; the USB frame latency dominates
- LeRobot's `sync_read` operations poll all 6 servo positions in one bus transaction
- Some users report needing 200ms packet timeout for reliable communication

### RPi 5 vs x86 for Serial

- RPi 5 has native UART pins (GPIO 14/15) that can bypass USB entirely for lower latency
- For USB-serial, RPi 5 uses the same `dwc2` USB controller as Pi 4; no known latency regressions
- The Linux `SCServo_Linux` SDK (enhanced fork of Feetech's SDK) is tested on RPi and Ubuntu

### Verdict

RPi 5 can reliably control STS3215 servos at 1 Mbaud via USB-serial. The CH340 adapters used by the standard Feetech driver board work fine on Linux. Setting `latency_timer=1` is recommended for best performance.

**Sources:**
- [Waveshare: ST3215 Servo Wiki](https://www.waveshare.com/wiki/ST3215_Servo)
- [SCServo_Linux GitHub](https://github.com/adityakamath/SCServo_Linux)
- [LeRobot Issue #526: STS3215 Serial Read Failure](https://github.com/huggingface/lerobot/issues/526)
- [Raspberry Pi Forums: USB Serial Latency](https://forums.raspberrypi.com/viewtopic.php?t=376795)

---

## 8. Power Budget Analysis

### Component Power Draw

| Component | Idle | Typical Load | Peak | Voltage |
|-----------|------|-------------|------|---------|
| **RPi 5** | 3-4W | 6-8W | 9W | 5V |
| **AI HAT+ (Hailo-8L, 13T)** | ~0.5W | ~1.5-2.5W | ~3W | Via PCIe (5W max) |
| **AI HAT+ (Hailo-8, 26T)** | ~0.5W | ~2.5W | ~8.25W | Via PCIe (5W max) |
| **AI HAT+ 2 (Hailo-10H, 40T)** | ~0.5W | ~2W | ~3W | Via PCIe (5W max) |
| **Feetech servo controller** | Negligible | Negligible | Negligible | USB-powered (logic only) |
| **STS3215 servo x6 (arm)** | ~0.5W each | ~2W each | ~5W each | **7.4-12V separate supply** |
| **USB camera x2** | ~0.5W each | ~1W each | ~1.5W each | 5V via USB |

### Total System Power Estimates

**Scenario A: RPi 5 + AI HAT+ 13T (vision only, no servos on RPi power)**

| Component | Watts |
|-----------|-------|
| RPi 5 under load | 7W |
| AI HAT+ 13T | 2W |
| 2x USB cameras | 2W |
| **Total from 5V PSU** | **~11W** |

The official RPi 5 27W PSU (5V/5A = 25W capacity) handles this easily.

**Scenario B: Full robot system (RPi + AI HAT + servos)**

| Component | Watts | Supply |
|-----------|-------|--------|
| RPi 5 + AI HAT + cameras | ~11W | 5V/5A USB-C PSU |
| 6x STS3215 servos (arm) | 12-30W | **Separate 7.4-12V supply** |
| 3x STS3215 servos (wheels, LeKiwi) | 6-15W | **Separate 12V supply** |

**Critical rule:** Never power servos from the RPi 5's GPIO 5V pins. Servo current draw causes brownouts and resets. The LeKiwi design uses a separate 12V battery with a buck converter.

### PSU Recommendations

| Use Case | PSU |
|----------|-----|
| RPi 5 + AI HAT (development) | Official RPi 27W USB-C PSU ($12) |
| Servo arm (6 DOF) | 7.4V 3A+ bench supply or 2S LiPo battery |
| LeKiwi mobile (arm + wheels) | 12V 5A battery pack (included in kit) |
| Full system (desktop) | Dual supply: 5V/5A for Pi, 12V/5A for servos |

**Sources:**
- [The Pi Hut: RPi 5 Power Supply Guide](https://support.thepihut.com/hc/en-us/articles/13852538984221-Which-power-supply-do-I-need-for-my-Raspberry-Pi-5)
- [Jeff Geerling: RPi 5 Power Consumption](https://www.jeffgeerling.com/blog/2023/reducing-raspberry-pi-5s-power-consumption-140x/)
- [Adafruit: Powering Servos](https://learn.adafruit.com/adafruit-16-channel-pwm-servo-hat-for-raspberry-pi/powering-servos)
- [Hailo-8 Power Consumption Discussion](https://community.hailo.ai/t/hailo-8-power-consumption/2879)

---

## 9. Competing AI Accelerators for RPi 5

| Accelerator | TOPS | Interface | Power | Price | Status | RPi 5 Support |
|-------------|------|-----------|-------|-------|--------|---------------|
| **Hailo-8L (AI HAT+ 13T)** | 13 | PCIe M.2 | ~2W | $70 | Active, recommended | Official, excellent |
| **Hailo-8 (AI HAT+ 26T)** | 26 | PCIe M.2 | ~2.5W | $110 | Active | Official, excellent |
| **Hailo-10H (AI HAT+ 2)** | 40 (INT4) | PCIe M.2 | ~3W | $130 | Active (Jan 2026) | Official, excellent |
| **Google Coral USB** | 4 | USB 3.0 | 2W | $60 | Legacy, not recommended for new projects | Works but no official support |
| **Google Coral M.2 Dual** | 8 | PCIe M.2 | 4W | $75 | Legacy | Works with M.2 HAT |
| **Intel NCS2** | ~1 | USB 3.0 | ~1W | N/A | **Discontinued** (last order Feb 2022) | Not recommended |
| **OpenNCC NCB** | ~1 | USB | ~1W | ~$70 | Niche (Movidius VPU) | Drop-in NCS2 replacement |

### Assessment

- **Hailo is the clear winner** for RPi 5. It is the only actively-supported, officially-integrated AI accelerator.
- **Coral USB** is still functional but no longer recommended (Frigate, the major user, recommends Hailo instead).
- **Intel NCS2** is dead -- discontinued with no successor in the USB form factor.
- **No competitor** offers the PCIe integration that Hailo has with the RPi 5.

**Sources:**
- [Seeed Studio: RPi AI Kit vs Coral Comparison](https://www.seeedstudio.com/blog/2024/07/16/raspberry-pi-ai-kit-vs-coral-usb-accelerator-vs-coral-m-2-accelerator-with-dual-edge-tpu/)
- [Edge AI Showdown: Hailo vs Coral](https://buyzero.de/en/blogs/news/edge-ai-showdown-hailo-vs-coral-which-chip-is-right-for-you)
- [Intel NCS2 Discontinuation Notice](https://www.intel.com/content/www/us/en/support/articles/000093181/boards-and-kits.html)
- [Frigate: Recommended Hardware](https://docs.frigate.video/frigate/hardware/)

---

## 10. LeKiwi Hardware Stack

### Bill of Materials

| Component | Model | Purpose | Price (est.) |
|-----------|-------|---------|-------------|
| Compute | Raspberry Pi 5 (4GB or 8GB) | Main controller | $60-80 |
| Storage | microSD card (32GB+) or NVMe SSD | OS + LeRobot | $10-30 |
| Arm servos | 6x Feetech STS3215 (7.4V, 19kg) | SO-101 arm joints | ~$15 each ($90) |
| Wheel servos | 3x Feetech STS3215 (12V, 30kg) | Omnidirectional drive | ~$18 each ($54) |
| Servo controller | Feetech Bus Servo Driver Board | USB-serial to servo bus | ~$5 |
| Camera | USB camera (1-2x) | Vision for data collection | $20-40 each |
| Chassis | 3D-printed enclosure | Structural | BOM cost ~$10-20 |
| Wheels | 3x omnidirectional wheels | Kiwi drive | Included in kit |
| Power | 12V battery + buck converter | Servo + Pi power | ~$30-50 |
| Cables | DC Y-cable, USB cables, servo wires | Connections | ~$10 |

**Complete Kit Price:** Seeed Studio sells the LeKiwi Kit (12V version) with 3D-printed parts and battery. The complete robot (arm + base + Pi) is estimated at $400-600.

### Architecture

```
[Laptop/PC]  <--ZeroMQ (TCP)--> [Raspberry Pi 5]
                                      |
                                      |-- USB-serial --> [Servo Bus: 6 arm + 3 wheel motors]
                                      |-- USB ---------> [Camera 1]
                                      |-- USB ---------> [Camera 2]
                                      |
                                      |-- 12V battery -> [Servos via driver board]
                                      |-- 5V buck -----> [RPi 5 power]
```

### Software Stack

- **On RPi 5:** `lerobot` with `[lekiwi]` extras (Feetech SDK + ZeroMQ)
  - Runs `lekiwi_host` script: servo control loop, camera streaming, ZeroMQ server
- **On Laptop:** `lerobot` with `[lekiwi]` extras
  - Runs teleop client, data recording, or policy evaluation
  - Connects to Pi via `tcp://<pi-ip>:5555` (control) and `tcp://<pi-ip>:5556` (video)

### Key Design Decisions

- **No AI HAT used** -- LeKiwi does not use any AI accelerator on the Pi
- **Remote inference only** -- All policy inference happens on the laptop/server
- **ZeroMQ for communication** -- Simple, fast, no ROS dependency
- **Single motor bus** -- Arm (IDs 1-6) and wheels (IDs 7-9) share one serial bus

**Sources:**
- [LeKiwi Documentation (HuggingFace)](https://huggingface.co/docs/lerobot/lekiwi)
- [SIGRobotics-UIUC/LeKiwi GitHub](https://github.com/SIGRobotics-UIUC/LeKiwi)
- [Seeed Studio: LeKiwi in LeRobot](https://wiki.seeedstudio.com/lerobot_lekiwi/)
- [Foxglove: Upgrading LeKiwi](https://foxglove.dev/blog/upgrading-the-lekiwi-into-a-lidar-equipped-explorer)

---

## 11. Real-World Projects and Gaps

### What Exists

| Project | Hardware | AI Accel | Inference Location | Status |
|---------|----------|----------|--------------------|--------|
| **LeKiwi** | RPi 5 + SO-101 | None | Remote (laptop GPU) | Active, production |
| **Hiwonder kits** (ArmPi, etc.) | RPi 5 | None | Local CPU (simple models) | Commercial products |
| **Frigate NVR** | RPi 5 + Hailo | Hailo-8L | Local (object detection) | Mature, production |
| **Hailo RPi5 examples** | RPi 5 + Hailo | Hailo-8/8L | Local (YOLO, pose) | Demo/reference |

### What Does NOT Exist

- **No one is running robot arm manipulation policies on Hailo.** The Hailo model zoo has zero robotics manipulation models.
- **No one has compiled ACT or diffusion policies to HEF format.** These models use transformer architectures that may not compile cleanly.
- **No published benchmarks for LeRobot local inference on RPi 5.** The community uses remote GPU servers.
- **No turnkey RPi 5 + AI HAT + robot arm product.** This would be novel.

### Gap Analysis for armOS

| Capability | Available? | Effort to Build |
|------------|-----------|-----------------|
| RPi 5 servo control at 30 FPS | Yes | Low (LeKiwi proves it) |
| RPi 5 camera capture at 30 FPS | Yes | Low |
| Hailo vision inference (YOLO, pose) | Yes | Low (pre-built HEFs) |
| Hailo robotics policy inference | **No** | **Very High** (custom DFC compilation, unknown feasibility) |
| Remote policy inference over network | Yes | Medium (PolicyServer pattern exists) |
| Custom RPi OS image for turnkey setup | **No** | Medium |
| OTA updates for fleet | **No** | High (need balenaOS or custom solution) |

---

## 12. Recommendations for armOS

### Architecture Decision

**Recommended: Client-Server with Optional Local Vision**

```
[armOS RPi 5 + AI HAT+]
   |
   |-- Hailo: Local vision (object detection, scene understanding)
   |-- Servos: Local 30 FPS control loop
   |-- Cameras: Local capture
   |
   |---(Network)---> [Cloud/Local GPU Server]
                        |-- Policy inference (ACT, Pi0, etc.)
                        |-- Training
```

This architecture uses Hailo for what it is good at (fast vision inference) and offloads policy inference to a GPU server. This matches the LeRobot community's proven architecture.

### AI HAT Selection

| Use Case | Recommended HAT | Reason |
|----------|----------------|--------|
| Vision-only (object detection, pose) | AI HAT+ 13T ($70) | Sufficient for YOLO/pose at 30+ FPS |
| Vision + future local LLM/VLM | AI HAT+ 2 ($130) | 8GB RAM enables small LLMs for task understanding |
| Maximum vision performance | AI HAT+ 26T ($110) | Overkill for most robotics vision tasks |

**Recommendation:** Start with the **AI HAT+ 13T ($70)** for initial development. The 13 TOPS is more than sufficient for real-time object detection and pose estimation. Upgrade to AI HAT+ 2 only if on-device language model capability becomes a requirement.

### Image Delivery

**Recommendation:** Docker on stock Raspberry Pi OS.

- Use Raspberry Pi Imager for base OS (most users already know this)
- Provide a `docker-compose.yml` that pulls the armOS container
- Container includes: LeRobot, Feetech SDK, ZeroMQ, udev rules, calibration tools
- Enables OTA updates by pulling new container versions

### Key Risks

1. **Hailo cannot accelerate robot manipulation policies.** This is the biggest finding. The Hailo accelerator is excellent for vision but useless for ACT/diffusion policy inference. Plan for remote inference.
2. **ONNX Runtime on Hailo is a dead end.** Hailo has explicitly said no further development is planned. Do not design around this.
3. **No off-the-shelf robotics models for Hailo.** Any vision model used for robot workspace understanding will need custom compilation.
4. **Power management complexity.** Separate supplies for Pi and servos add cost and complexity.

### Bill of Materials (Recommended armOS Starter Kit)

| Item | Model | Price |
|------|-------|-------|
| Compute | Raspberry Pi 5 8GB | $80 |
| AI Accelerator | AI HAT+ 13T (Hailo-8L) | $70 |
| Storage | 64GB microSD | $12 |
| Power (Pi) | Official RPi 27W USB-C PSU | $12 |
| Servo controller | Feetech Bus Servo Driver Board | $5 |
| Servos (6 DOF arm) | 6x Feetech STS3215 | $90 |
| Power (servos) | 7.4V 3A bench PSU or 2S LiPo | $25 |
| Camera | 2x USB cameras | $40 |
| Cables/misc | USB cables, servo wires | $15 |
| **Total** | | **~$350** |

This does not include the 3D-printed arm structure or a GPU server for policy inference.

---

*Research conducted 2026-03-15. All prices in USD. Availability and specifications subject to change.*
