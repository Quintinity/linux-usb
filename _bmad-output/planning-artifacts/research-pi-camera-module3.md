# Raspberry Pi Camera Module 3 -- Research Note for armOS Integration

**Date:** 2026-03-15
**Status:** ACTION -- decisions needed on camera selection and integration path

---

## 1. Camera Module 3 Variants and Specs

All variants use the **Sony IMX708** back-illuminated 12MP CMOS sensor with powered autofocus (PDAF + CDAF fallback) and HDR support.

| Variant | FOV (H) | FOV (Diag) | Price | IR Filter |
|---------|---------|-------------|-------|-----------|
| Standard | 66 deg | 75 deg | $25 | Yes |
| Standard NoIR | 66 deg | 75 deg | $25 | No |
| Wide | 102 deg | 120 deg | $35 | Yes |
| Wide NoIR | 102 deg | 120 deg | $35 | No |

### Resolution and Frame Rate Modes

| Resolution | FPS | Notes |
|-----------|-----|-------|
| 4608x2592 | 14 | Full sensor readout |
| 2304x1296 | 56 | 2x2 binned |
| 1536x864 | 120 | For high-speed capture |
| 2304x1296 | 30 | HDR mode (max resolution when HDR enabled) |

### Physical

- **Focus range:** 5 cm to infinity
- **Connector:** 15-pin MIPI CSI-2 ribbon cable (standard Pi camera connector)
- **Dimensions:** 25 x 24 mm (PCB)

---

## 2. CSI vs USB Camera on Raspberry Pi 5

| Metric | CSI (MIPI) | USB |
|--------|-----------|-----|
| Latency (1080p) | ~200 ms | ~800 ms |
| CPU usage | <5% (frames go through ISP/GPU) | ~17% (CPU handles capture) |
| Bandwidth ceiling | 10 Gb/s (4-lane CSI-2) | 480 MB/s (USB 3.0) |
| Frame capture path | Direct to ISP, GPU handles capture + encode | CPU captures frames, GPU encodes only |
| Driver stack | libcamera (native) | V4L2 / UVC |

**Verdict:** CSI is dramatically better for robot arms where latency and CPU headroom matter. The 4x latency advantage and 3x CPU savings are significant when the Pi is also running servo control loops and inference.

---

## 3. Capturing Frames with picamera2 (Python)

Picamera2 is the official Python library built on libcamera. It replaces the legacy picamera library.

### Basic frame capture

```python
from picamera2 import Picamera2
import cv2

picam2 = Picamera2()

# Configure for video capture at 1280x720
config = picam2.create_video_configuration(
    main={"size": (1280, 720), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()

# Grab a frame as a numpy array (OpenCV-compatible)
frame = picam2.capture_array()

# Process with OpenCV
gray = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
```

### Setting autofocus mode

```python
from libcamera import controls

# Continuous autofocus
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})

# Manual focus -- lock to fixed distance (e.g., 20cm = lens position 5.0)
picam2.set_controls({
    "AfMode": controls.AfModeEnum.Manual,
    "LensPosition": 5.0  # 1/distance_in_meters
})
```

### Key API methods

- `picam2.capture_array()` -- returns numpy array (RGB or BGR depending on config)
- `picam2.capture_file("image.jpg")` -- save to file
- `picam2.create_video_configuration()` -- optimized for streaming
- `picam2.create_still_configuration()` -- optimized for single shots

---

## 4. LeRobot Camera Support -- CSI Compatibility

### Current state (LeRobot v0.5.0)

LeRobot uses `OpenCVCamera` which calls `cv2.VideoCapture()` internally. This works with:
- USB UVC cameras (plug and play)
- V4L2 devices

**It does NOT work with CSI cameras on Bookworm** because OpenCV's VideoCapture does not support the libcamera backend. `cv2.VideoCapture(0)` will fail or return empty frames with a CSI camera on modern Raspberry Pi OS.

### The integration gap

OpenCV has an open issue (#21653) requesting libcamera support. As of 2025, it is not merged. This means:

1. LeRobot's `OpenCVCamera` cannot directly use Pi Camera Module 3 via CSI
2. A bridge is needed

### Workaround: picamera2-to-OpenCV bridge

```python
from picamera2 import Picamera2
import cv2

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"}
))
picam2.start()

# This produces numpy arrays identical to what cv2.VideoCapture would return
frame = picam2.capture_array()
# frame is now a standard numpy array usable by LeRobot's pipeline
```

### Integration options for armOS

**Option A: Write a `Picamera2Camera` class for LeRobot** that implements the same interface as `OpenCVCamera` but uses picamera2 internally. This is the cleanest path.

**Option B: Use LCCV** (github.com/kbarni/LCCV) -- a thin libcamera wrapper that provides an OpenCV-compatible VideoCapture interface. This might let LeRobot's existing OpenCVCamera work without modification.

**Option C: Use rpicam-vid to pipe MJPEG to a V4L2 loopback device**, then OpenCV reads from that. Hacky but requires zero LeRobot changes.

**Recommendation:** Option A is correct for armOS. Write a thin `Picamera2Camera` wrapper that matches LeRobot's camera interface. This gives full control over autofocus, HDR, and resolution without hacks.

---

## 5. Hailo AI HAT + Pi Camera Pipeline

### Architecture

The Hailo AI HAT+ connects via PCIe to the RPi 5. The official software stack integrates with:
- **rpicam-apps** (C++ camera framework) -- has built-in Hailo post-processing stages
- **picamera2** (Python) -- supported since Hailo SDK 4.18

### Frame flow

```
CSI Camera --> ISP (GPU) --> picamera2/rpicam-apps --> CPU memory --> PCIe --> Hailo NPU
                                                                          |
                                                                          v
                                                                     Inference result
```

### Is there true zero-copy?

**No confirmed zero-copy path exists** from CSI directly to Hailo NPU. Frames pass through:
1. CSI-2 interface to the Pi's ISP (hardware, fast)
2. ISP outputs to CPU-accessible memory
3. Software copies frame to Hailo NPU over PCIe

The PCIe link is fast (PCIe Gen 2 x1 = ~500 MB/s on Pi 5), so the copy overhead is small. For 1280x720 RGB at 30fps, that is roughly 83 MB/s -- well within PCIe budget.

### GStreamer pipeline

The Hailo examples use GStreamer internally. A typical detection pipeline:

```
libcamerasrc ! video/x-raw,width=1280,height=720 ! hailonet hef=model.hef ! hailooverlay ! autovideosink
```

However, the official Hailo team notes that `libcamerasrc` GStreamer plugin is limited and recommends using picamera2 directly with the Hailo Python API for more control:

```python
from picamera2 import Picamera2
from hailo_platform import HEF, VDevice, ConfigureParams

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(
    main={"size": (640, 640), "format": "RGB888"}
))
picam2.start()

# Load model on Hailo
hef = HEF("yolov6n.hef")
target = VDevice()
network_group = target.configure(hef)
# ... run inference on picam2.capture_array()
```

### Hailo SDK 4.18+ key details

- Official Python API support for RPi 5
- picamera2 examples for object detection and pose estimation
- Virtual environments require `--system-site-packages` flag to find hailo_platform

---

## 6. Camera Mounting for SO-101 Arms

### Available 3D-printable mounts

**Wrist camera mount (NekoMaker, Thingiverse #7143999)**
- Mounts on SO-101 gripper
- 2 mounting holes with hex nuts matching new SO-101 gripper design
- Updated from earlier single-screw design that had rotation issues
- CC BY-SA 4.0 license

**Snap-on camera mount (Starkosaure, Thingiverse #7033586)**
- Clips onto gripper with 20mm wood screw (no drilling, no glue)
- Pivot joint for adjustable camera angle
- Compatible with 28x28mm and 27x31mm camera mounting holes
- Hardware: 4 small plastic screws, 1x M4 15mm screw + nut, 1x 20mm wood screw

**Official SO-ARM100/101 repository**
- Includes optional camera mount designs in the repo
- Supports both gripper-mounted (wrist) and external (workspace) camera positions

### Recommendation for armOS

Use the **snap-on mount** for prototyping (quick install, adjustable angle). For production, design a custom mount that rigidly fixes the camera at a known angle and distance from the gripper -- autofocus can compensate for distance variation but a fixed geometry simplifies calibration.

---

## 7. Autofocus: Good or Bad for Robot Manipulation?

### Pros of autofocus for manipulation

- Objects at varying distances (reaching for items on a table) stay sharp
- PDAF is fast enough for real-time use (few hundred ms to lock)
- Macro mode works down to ~5cm, good for close gripper views
- Can be locked to manual mode if fixed focus is preferred

### Cons / risks

- **Focus hunting**: The AF algorithm can oscillate when the scene lacks contrast or has repetitive textures (common with plain tabletops)
- **Latency jitter**: AF adjustments can cause frame-to-frame sharpness variation during policy inference
- **Not fully reliable**: Forum reports indicate AF is "erratic" in some conditions, especially with large uniform areas in frame

### Recommendation

**Use manual focus mode for manipulation tasks.** Set `LensPosition` to a fixed value matching the expected working distance:

```python
# For wrist camera ~15-25cm from workspace:
picam2.set_controls({
    "AfMode": controls.AfModeEnum.Manual,
    "LensPosition": 5.0   # focuses at ~20cm (1/0.2m = 5.0)
})
```

This gives consistent frames without focus hunting. The autofocus hardware is still available for initial calibration or workspace overview tasks. This is strictly better than a fixed-focus camera because you can change the focus distance in software.

---

## 8. Pi Camera Module 3 vs OAK-D Lite

| Feature | Pi Camera Module 3 | OAK-D Lite |
|---------|-------------------|------------|
| Price | $25-35 | ~$150 |
| Resolution | 12MP (4608x2592) | 4K RGB + 2x 480p stereo |
| Depth sensing | No | Yes (stereo, cm-level accuracy) |
| On-device AI | No (needs Hailo HAT) | Yes (Myriad X VPU) |
| Interface | CSI-2 (Pi-specific) | USB 3.0 (universal) |
| Latency | ~200ms (CSI native) | Depends on USB/processing |
| CPU overhead | Very low (<5%) | Low (processing on Myriad X) |
| Autofocus | Yes (PDAF) | Yes (RGB camera) |
| Size | 25x24mm | 91x28mm |
| Pi 5 integration | Native (libcamera) | USB (OpenCV compatible) |
| LeRobot compat | Needs wrapper (see sec 4) | Works with OpenCVCamera |

### When to use which

- **Pi Camera Module 3**: Best for wrist camera (small, cheap, low latency via CSI, pairs with Hailo for inference). Two cameras = $50-70.
- **OAK-D Lite**: Best if you need depth perception for grasping or obstacle avoidance. Overkill for basic imitation learning. Works as a workspace overview camera.

### Recommendation for armOS

Use **Pi Camera Module 3 Wide ($35)** as the primary camera:
- Wide FOV captures more of the workspace from a wrist mount
- CSI gives lowest latency for control loops
- Pair with Hailo AI HAT for on-device inference
- Total camera cost: $35-70 (1-2 cameras) vs $150+ for OAK-D Lite

Add OAK-D Lite only if depth-based manipulation policies are needed later.

---

## 9. rpicam-apps on Bookworm -- Gotchas

### Known issues to watch for

1. **Command rename**: `libcamera-*` commands renamed to `rpicam-*` on Bookworm. Symlinks were provided but removed in rpicam-apps v1.8.0. Any scripts using `libcamera-still` etc. will break.

2. **config.txt pitfall**: `disable_fw_kms_setup=1` in `/boot/config.txt` prevents camera detection. Comment it out if camera is not found.

3. **Library loading after source builds**: After symlink removal, rpicam built from source cannot find `libcamera.so`. Use system packages when possible.

4. **June 2025 OS update breakage**: A Bookworm update broke libcamera commands for some users. Pin packages or test updates before deploying.

5. **Third-party camera drivers**: Arducam and other third-party cameras broke after May 2025 updates due to IPA module changes.

6. **Virtual environment gotcha**: picamera2 and Hailo libraries are installed as system packages. Python venvs must use `--system-site-packages` to access them:
   ```bash
   python3 -m venv --system-site-packages ~/armos-env
   ```

### Mitigation for armOS

- Pin the Raspberry Pi OS image version in the armOS build process
- Use `rpicam-*` command names exclusively (no legacy names)
- Always create venvs with `--system-site-packages`
- Test camera detection in the boot validation sequence

---

## 10. Integration Recommendation for armOS

### Camera hardware selection

**Primary: Pi Camera Module 3 Wide ($35)**
- Mount on wrist using snap-on or custom rigid mount
- 102-degree HFOV captures full workspace from close range
- Manual focus locked at working distance (~20cm)

**Optional: Second Pi Camera Module 3 Standard ($25)**
- Overhead/workspace view
- Narrower FOV for higher detail at distance

### Software architecture

```
Pi Camera Module 3 (CSI)
    |
    v
libcamera / ISP (hardware)
    |
    v
picamera2 (Python) -- capture_array() --> numpy RGB frame
    |                                         |
    v                                         v
Hailo NPU (inference)              LeRobot Picamera2Camera wrapper
    |                                         |
    v                                         v
Detection/pose results             Policy input (observation frames)
```

### Implementation tasks

1. **Write `Picamera2Camera` class** for LeRobot that wraps picamera2 and implements the same interface as `OpenCVCamera`. Key methods: `connect()`, `read()`, `disconnect()`, `async_read()`.

2. **Set manual focus** at fixed working distance for consistent frames during policy inference.

3. **Create armOS camera validation script** that checks:
   - Camera detected via `rpicam-hello --list-cameras`
   - picamera2 can capture a frame
   - Frame dimensions match expected config
   - Autofocus lock succeeds at target distance

4. **Pin OS image** to a tested Bookworm version to avoid libcamera breakage from updates.

5. **Design rigid wrist mount** (or adopt snap-on mount from Thingiverse #7033586) with fixed camera angle for repeatable calibration.

6. **GStreamer pipeline** for Hailo inference (secondary priority -- picamera2 + Hailo Python API is simpler and recommended by Hailo team).

---

## Sources

- [Raspberry Pi Camera Module 3 Product Page](https://www.raspberrypi.com/products/camera-module-3/)
- [Raspberry Pi Camera Documentation](https://www.raspberrypi.com/documentation/accessories/camera.html)
- [Picamera2 GitHub Repository](https://github.com/raspberrypi/picamera2)
- [Picamera2 Manual (PDF)](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [Camera Module 3 Product Brief (PDF)](https://datasheets.raspberrypi.com/camera/camera-module-3-product-brief.pdf)
- [LeRobot Camera Documentation](https://github.com/huggingface/lerobot/blob/main/docs/source/cameras.mdx)
- [OpenCV libcamera support issue #21653](https://github.com/opencv/opencv/issues/21653)
- [OpenCV + libcamera incompatibility #22820](https://github.com/opencv/opencv/issues/22820)
- [LCCV -- LibCamera wrapper for OpenCV](https://github.com/kbarni/LCCV)
- [Hailo RPi5 Examples](https://github.com/hailo-ai/hailo-rpi5-examples)
- [Hailo SDK 4.18 Release -- picamera2 Support](https://community.hailo.ai/t/new-release-4-18-raspberry-pi-ai-kit-now-with-hailo-python-api-support-clip-zero-shot-classification-and-picamera2-examples/3072)
- [AI HAT+ Documentation](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html)
- [SO-101 Wrist Camera Mount (Thingiverse)](https://www.thingiverse.com/thing:7143999)
- [Snap-on Camera Mount for SO-ARM100/101 (Thingiverse)](https://www.thingiverse.com/thing:7033586)
- [SO-ARM100 GitHub](https://github.com/TheRobotStudio/SO-ARM100)
- [MIPI CSI vs USB Camera Comparison (e-con Systems)](https://www.e-consystems.com/blog/camera/technology/mipi-camera-vs-usb-camera-a-detailed-comparison/)
- [CSI vs USB Camera Discussion (RPi Forums)](https://forums.raspberrypi.com/viewtopic.php?t=394659)
- [Camera Module 3 Autofocus Discussion (RPi Forums)](https://forums.raspberrypi.com/viewtopic.php?t=352804)
- [rpicam-apps Symlink Removal Issue #818](https://github.com/raspberrypi/rpicam-apps/issues/818)
- [OAK-D Lite with Raspberry Pi Guide](https://core-electronics.com.au/guides/oak-d-lite-raspberry-pi/)
