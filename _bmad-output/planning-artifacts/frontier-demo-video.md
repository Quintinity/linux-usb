# Frontier: AI-Generated Demo Video Production Pipeline

**Authors:** Paige (Tech Writer) and Sally (UX Designer)
**Date:** 2026-03-15
**Input:** 90-second demo video script from strategy-content-enhancements.md

---

## Executive Summary

The original script calls for a single continuous take with real hardware. That is still the gold standard -- but we cannot record it until the software exists. This document designs a parallel track: an AI-generated version that can ship on Day -14 (two weeks before launch) using no camera, no studio, and no finished armOS build. It also goes beyond video into interactive experiences.

**Total estimated cost: $150-400 for the full pipeline.**

---

## PART 1: VISUAL GENERATION

### Model Selection Matrix (as of March 2026)

| Model | Best at | Worst at | Cost | Verdict for armOS |
|---|---|---|---|---|
| **Runway Gen-4 Turbo** | Consistent motion, camera control, subject locking | Long takes (>10s), text rendering | $0.50/5s clip | **Primary pick for hardware shots (1, 2, 3, 6, 10)** -- best at maintaining object consistency across frames |
| **Kling 2.0** | Realistic hand motion, object interaction | Western aesthetics sometimes drift | $0.20/5s clip | **Secondary pick for hand close-ups (2, 6)** -- cheapest option with good hand physics |
| **Veo 2** | Cinematic quality, lighting, long coherent clips | Availability (still gated), fine text | Waitlist / Google One AI Premium | **Use if access is available** -- best raw quality |
| **Sora** | Cinematic b-roll, camera movement | Precise UI text, hands, fine detail | $0.40/5s clip via ChatGPT Pro | Skip -- too unpredictable for technical content |
| **Pika 2.0** | Stylized content, effects | Photorealism for hardware | $0.25/clip | Skip -- wrong aesthetic for a credibility play |
| **Flux 1.1 Pro / SDXL** | Still product shots, hero images | Video (stills only) | $0.04/image | **Use for thumbnail, product shots, end card** |
| **ComfyUI + AnimateDiff** | Free, local, controllable | Quality ceiling, hands | Free (local GPU) | **Fallback if budget is zero** -- needs an NVIDIA GPU |

### The Hybrid Approach (Recommended)

Do not try to AI-generate the entire video. Instead, split into three visual layers:

**Layer 1: Screen recordings (Shots 4, 5, 7, 8, 9) -- REAL, not AI**
Record actual screen content from a VM or prototype TUI. This is the most important layer because viewers will scrutinize UI text. AI cannot reliably render terminal text at legible resolution.

- Run a QEMU/KVM VM with a mockup TUI (even a Python curses script that fakes the dashboard)
- Use OBS Studio to capture at 1080p or 4K
- Apply AI upscaling with Topaz Video AI ($199 one-time) or Real-ESRGAN (free) if the source is low-res
- Add the timer overlay in post with FFmpeg

**Layer 2: Hardware shots (Shots 1, 2, 3, 6, 10) -- AI-GENERATED**
These are the "hands on a table" shots. AI video models handle this well because the camera is mostly static and the subjects (laptop, USB stick, robot arm) are common training data.

**Layer 3: End card and thumbnail (Shot 11, thumbnail) -- AI IMAGE + DESIGN**
Static or near-static. Generate with Flux, composite in Figma or Canva.

---

## PART 2: VOICE AND NARRATION

### The Original Script Says: No Narration

The original concept is silent with text overlays. This is the right call for the "credibility through simplicity" positioning. However, we should produce two versions:

| Version | Audio | Use Case |
|---|---|---|
| **A: Silent + text overlays** | Ambient keyboard/click SFX only | GitHub README embed, landing page autoplay (muted) |
| **B: Narrated** | Voiceover + subtle music bed | YouTube, Twitter/X, conference talks |

### Voice AI Recommendation

| Tool | Quality | Latency | Cost | Verdict |
|---|---|---|---|---|
| **ElevenLabs** (Turbo v3) | Best-in-class naturalness, breathing, pacing | Real-time | $5/mo (Starter) or $0.30/1K chars | **Primary pick** -- use "Adam" or "Charlie" voice for calm, technical male narrator; "Rachel" for female |
| **Cartesia Sonic 2** | Excellent, very fast | Sub-200ms | $0.15/1K chars | **Runner-up** -- slightly less natural but cheaper and faster |
| **Play.ht 3.0** | Good | Moderate | $0.20/1K chars | Skip -- no advantage over ElevenLabs |
| **OpenAI TTS** | Good but robotic for long form | Real-time | $15/1M chars | Skip -- too flat for a demo video |

**Recommended voice direction:** Male, 30s, American English, calm and confident. Not a "YouTube voice" -- think conference keynote. Measured pace. No excitement. Let the demo speak for itself.

### Narration Script (Version B only, ~180 words at 2 words/sec)

```
[0:00] A laptop. A robot arm. A USB stick.
[0:05] Insert the stick.
[0:10] Power on.
[0:15] armOS boots. No installation. No configuration.
[0:25] The dashboard appears. Nothing is connected yet.
[0:35] Plug in the robot arm.
[0:45] Detected automatically. Feetech STS3215 controller. SO-101 profile loaded. Zero configuration.
[0:55] Calibrate. One click. Sixty seconds.
[1:05] Start teleoperation. Live servo telemetry -- voltage, position, load -- all streaming in real time.
[1:15] Move the leader arm. The follower mirrors it instantly.
[1:22] From USB stick to this. Under five minutes.
[1:28] armOS. Boot from USB. Detect hardware. Start building.
```

**ElevenLabs cost for this script:** ~$0.05 (180 words, ~900 characters).

### Background Music

| Tool | Quality | Cost | Verdict |
|---|---|---|---|
| **Suno v4** | Very good, full songs | $10/mo (Pro) | **Use for Version B** -- generate a minimal ambient electronic track |
| **Udio v2** | Comparable to Suno | $10/mo (Pro) | Alternative if Suno output is too "musical" |
| **Epidemic Sound** | Professional library | $15/mo | **Safe fallback** -- guaranteed quality, cleared for commercial use |

**Music prompt for Suno/Udio:**
```
Minimal ambient electronic, soft pads, no percussion for first 30 seconds,
subtle beat enters at 0:30, builds gently, resolves at 1:25. Tech demo
background. Not cinematic. Not corporate. Think Tycho meets Brian Eno.
90 seconds. Stereo. 48kHz.
```

**Music cost:** ~$0.50 per generation, expect 5-10 attempts = $5.

---

## PART 3: EXACT PROMPTS FOR EACH SHOT

### Shot 1 (0:00-0:05): Wide shot -- table with laptop, arm, USB stick

**Tool:** Runway Gen-4 Turbo (video) or Flux 1.1 Pro (still + Ken Burns)

**Runway prompt:**
```
Static wide shot of a clean, well-lit desk in a modern home office. On the desk:
a closed silver laptop (generic, ThinkPad-style), a small white 6-DOF robot arm
(tabletop size, about 30cm tall, white plastic with visible servo motors), and a
small black USB flash drive placed between them. Soft overhead lighting. Shallow
depth of field. No people visible. No text on screen. Photorealistic.
Camera: locked tripod, eye-level, slight wide angle.
```

**Negative prompt:** `cartoon, anime, illustration, blurry, dark, cluttered desk, multiple monitors, gaming setup, RGB lighting`

**Aspect ratio:** 16:9, 1080p
**Duration:** 5 seconds
**Estimated cost:** $0.50

**Flux fallback (still image with Ken Burns zoom):**
```
Professional product photography of a clean desk workspace. A closed silver
ThinkPad laptop, a small white SO-101 robot arm (6-DOF, tabletop, ~30cm tall,
white plastic servos), and a black USB stick arranged on a light wood desk.
Soft natural lighting from the left. Shallow depth of field. Minimalist
background. Shot on Sony A7IV, 35mm f/1.8.
```
**Aspect ratio:** 16:9
**Cost:** $0.04

---

### Shot 2 (0:05-0:10): Close-up -- hands insert USB stick

**Tool:** Runway Gen-4 Turbo or Kling 2.0

**Runway prompt:**
```
Close-up shot of two hands picking up a small black USB flash drive from a desk
and inserting it into the USB-A port on the left side of a silver laptop.
Smooth, deliberate motion. Well-lit. Soft focus background. Camera follows the
hands slightly. Photorealistic.
Camera: handheld, slight movement, close-up macro feel.
```

**Negative prompt:** `extra fingers, deformed hands, blurry, cartoon, dark lighting, gloves`

**Kling 2.0 prompt (if Runway hands look wrong):**
```
A person's hands carefully inserting a black USB flash drive into a silver laptop.
Close-up shot. Natural office lighting. Realistic skin texture. Smooth motion.
```

**Aspect ratio:** 16:9
**Duration:** 5 seconds
**Cost:** $0.20-0.50

---

### Shot 3 (0:10-0:15): Medium shot -- open laptop, press power

**Tool:** Runway Gen-4 Turbo

**Prompt:**
```
Medium shot from slightly above. Hands open a silver laptop lid, revealing a dark
screen. One hand reaches to the top-right of the keyboard and presses the power
button. The screen begins to glow faintly. Clean desk, robot arm visible in the
background out of focus. Natural lighting.
Camera: static tripod, slight high angle.
```

**Negative prompt:** `text on screen, Windows logo, macOS, cartoon, dark room, gaming laptop`

**Duration:** 5 seconds
**Cost:** $0.50

---

### Shot 4 (0:15-0:25): Screen capture -- GRUB and boot

**Tool:** REAL SCREEN RECORDING (not AI)

**Method:**
1. Create a GRUB theme mockup or boot a real Linux VM with custom GRUB entry "armOS"
2. Record with OBS at 1080p60
3. Speed up to 2x with FFmpeg: `ffmpeg -i boot.mp4 -filter:v "setpts=0.5*PTS" -an boot_2x.mp4`
4. Add "2x" speed indicator overlay
5. Add timer overlay

**If AI-generating as a fallback (Runway):**
```
Screen recording of a Linux boot sequence. GRUB bootloader menu on dark
background with white text, "armOS" highlighted. Boot messages scrolling
rapidly. Terminal-style green and white text on black background. Ends with
a logo splash screen.
Camera: direct screen capture, no angle.
```
**Warning:** AI will not render legible terminal text. Use real recording.

**Duration:** 10 seconds
**Cost:** $0 (real recording)

---

### Shot 5 (0:25-0:35): Screen capture -- TUI dashboard (no hardware)

**Tool:** REAL SCREEN RECORDING

**Method:**
1. Build a mock TUI with Python `textual` or `rich` library:
   - Header: "armOS v1.0 -- Dashboard"
   - Status panel: "No hardware detected" (yellow)
   - Menu: [Scan] [Calibrate] [Teleop] [Settings] [Quit]
   - Footer: system info
2. Record with OBS
3. Add timer overlay

**Python mock TUI script** (build this in ~2 hours):
```python
# Use textual framework to create a pixel-perfect mockup
# This is faster and more convincing than AI generation
# The mock does not need to be functional -- just look right
```

**Duration:** 10 seconds
**Cost:** $0

---

### Shot 6 (0:35-0:45): Close-up -- plug USB-serial cable

**Tool:** Runway Gen-4 Turbo or Kling 2.0

**Prompt:**
```
Close-up of hands plugging a USB cable into a small USB hub connected to a
silver laptop. The cable runs off-screen to the right toward a robot arm.
Deliberate, confident motion. Well-lit desk. Shallow depth of field.
Camera: handheld close-up, slight rack focus from hands to cable.
```

**Negative prompt:** `extra fingers, deformed hands, tangled cables, messy desk, dark`

**Duration:** 10 seconds
**Cost:** $0.50-1.00

---

### Shot 7 (0:45-0:55): Screen capture -- auto-detection

**Tool:** REAL SCREEN RECORDING

**Method:**
1. Extend the mock TUI to animate: status changes from yellow "No hardware" to green "Feetech STS3215 detected -- SO-101 profile loaded"
2. Show green checkmarks appearing one by one
3. Record with OBS

**Duration:** 10 seconds
**Cost:** $0

---

### Shot 8 (0:55-1:05): Screen capture -- calibration

**Tool:** REAL SCREEN RECORDING

**Method:**
1. Mock TUI shows calibration progress bar filling over ~8 seconds
2. Joints listed: Base, Shoulder, Elbow, Wrist Pitch, Wrist Roll, Gripper -- each gets a green check
3. "Calibration complete" message

**Duration:** 10 seconds
**Cost:** $0

---

### Shot 9 (1:05-1:15): Screen capture -- telemetry panel

**Tool:** REAL SCREEN RECORDING

**Method:**
1. Mock TUI shows live-updating telemetry:
   - 6 servos with voltage (7.2V), temperature (32C), position (deg), load (%)
   - Values updating every 100ms (use random jitter around baseline values)
   - Color-coded: green = normal, yellow = warning, red = critical
2. This is the most complex mock but the most impressive
3. Use `textual` DataTable with live updates

**Duration:** 10 seconds
**Cost:** $0

---

### Shot 10 (1:15-1:25): Wide shot -- robot arms moving

**Tool:** Runway Gen-4 Turbo (primary) + Kling 2.0 (backup)

**This is the hardest shot and the most important.**

**Runway prompt:**
```
Wide shot of two small white 6-DOF robot arms on a desk, side by side. The left
arm (leader) is being moved by a human hand gripping the gripper. The right arm
(follower) mirrors the exact same motion simultaneously. A silver laptop in the
background shows a terminal with green text. Smooth, continuous motion. Both arms
move fluidly in sync. Well-lit home office. Photorealistic.
Camera: static tripod, slightly elevated, both arms and laptop visible.
```

**Negative prompt:** `industrial robot, large robot, factory, dark room, cartoon, jerky motion, frozen arm, single arm only`

**Generation strategy:**
- Generate 10+ variations and pick the one where both arms move convincingly
- If no AI model produces convincing synchronized arm motion, use a REAL recording of the actual SO-101 arms -- this shot is the one that justifies owning the hardware
- Alternatively: use a 3D render from Blender with the SO-101 URDF model

**Duration:** 10 seconds
**Cost:** $1.00-5.00 (multiple attempts)

**Blender fallback (free, highest fidelity):**
- Import SO-101 URDF/STL files
- Animate mirrored joint trajectories
- Render with Cycles at 1080p
- Composite onto a desk background (AI-generated still from Flux)
- Rendering time: ~1-2 hours on any GPU

---

### Shot 11 (1:25-1:30): Fade to black + end card

**Tool:** Figma/Canva + Flux for background

**Flux prompt for end card background:**
```
Minimal dark gradient background, deep navy to black, subtle circuit board
pattern barely visible. Clean. Modern. No text. 16:9 aspect ratio. 4K.
```

**Text overlay (added in Figma/FFmpeg):**
```
armOS
Boot from USB. Detect hardware. Start building.

github.com/[org]/armOS
Free and open source.
```

**Font:** Inter or JetBrains Mono. White on dark.

**Duration:** 5 seconds + 3 seconds
**Cost:** $0.04

---

### Thumbnail

**Tool:** Flux 1.1 Pro + Canva

**Flux prompt (left half -- "the old way"):**
```
Overhead photo of a messy desk covered in tangled USB cables, a laptop showing
a terminal full of red error messages, scattered screwdrivers, and a disconnected
robot arm lying on its side. Harsh fluorescent lighting. Frustrating mood.
Photorealistic.
```

**Flux prompt (right half -- "the armOS way"):**
```
Overhead photo of a clean, minimal desk with a silver laptop showing a clean
green terminal dashboard, a white robot arm standing upright and operational,
and a single USB stick. Soft warm lighting. Calm, organized mood. Photorealistic.
```

**Composite in Canva:** Split down the middle with a diagonal line. Left = chaos. Right = calm. Bold text overlay: "5 minutes."

**Cost:** $0.08 (two Flux generations)

---

## PART 4: EDITING PIPELINE

### Recommended: FFmpeg + Python (Programmatic Assembly)

For a 90-second video with precise timing, programmatic assembly beats manual editing. It is reproducible, version-controllable, and free.

**Pipeline script (`assemble_demo.py`):**

```python
"""
Assembles the armOS demo video from individual shot clips.
Requires: ffmpeg, Python 3.10+
"""
import subprocess
import json

SHOTS = [
    {"file": "shots/01_wide_table.mp4",      "start": 0,  "duration": 5,  "overlay": "armOS: USB boot to robot teleop"},
    {"file": "shots/02_insert_usb.mp4",       "start": 0,  "duration": 5,  "overlay": None},
    {"file": "shots/03_open_laptop.mp4",      "start": 0,  "duration": 5,  "overlay": None},
    {"file": "shots/04_boot_grub.mp4",        "start": 0,  "duration": 10, "overlay": None},
    {"file": "shots/05_tui_dashboard.mp4",    "start": 0,  "duration": 10, "overlay": None},
    {"file": "shots/06_plug_cable.mp4",       "start": 0,  "duration": 10, "overlay": None},
    {"file": "shots/07_auto_detect.mp4",      "start": 0,  "duration": 10, "overlay": "Auto-detected. Zero configuration."},
    {"file": "shots/08_calibrate.mp4",        "start": 0,  "duration": 10, "overlay": None},
    {"file": "shots/09_telemetry.mp4",        "start": 0,  "duration": 10, "overlay": None},
    {"file": "shots/10_arms_moving.mp4",      "start": 0,  "duration": 10, "overlay": "From USB stick to this."},
    {"file": "shots/11_end_card.mp4",         "start": 0,  "duration": 8,  "overlay": None},
]

def build_filter_complex(shots):
    """Generate FFmpeg filter_complex for concatenation with overlays and timer."""
    filters = []
    inputs = []

    for i, shot in enumerate(shots):
        inputs.extend(["-i", shot["file"]])
        # Scale all to 1080p, add timer overlay
        filters.append(
            f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
            f"drawtext=text='%{{pts\\:hms}}':x=w-tw-40:y=40:"
            f"fontsize=36:fontcolor=white:font=JetBrains Mono"
            f"[v{i}]"
        )

    # Concatenate
    concat_input = "".join(f"[v{i}]" for i in range(len(shots)))
    filters.append(f"{concat_input}concat=n={len(shots)}:v=1:a=0[outv]")

    return inputs, ";".join(filters)

def assemble():
    inputs, filter_complex = build_filter_complex(SHOTS)
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "armos_demo_v1.mp4"
    ]
    subprocess.run(cmd, check=True)

    # Mux narration + music for Version B
    subprocess.run([
        "ffmpeg", "-y",
        "-i", "armos_demo_v1.mp4",
        "-i", "audio/narration.mp3",
        "-i", "audio/music_bed.mp3",
        "-filter_complex",
        "[1:a]volume=1.0[narr];[2:a]volume=0.3[music];[narr][music]amix=inputs=2[outa]",
        "-map", "0:v", "-map", "[outa]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "armos_demo_v1_narrated.mp4"
    ], check=True)

if __name__ == "__main__":
    assemble()
```

### Timer Overlay (FFmpeg drawtext)

The timer is the hero of the video. Start it at Shot 2 (0:05) and run continuously:

```bash
ffmpeg -i concatenated.mp4 \
  -vf "drawtext=text='%{pts\:hms}':x=w-tw-40:y=40:fontsize=48:\
  fontcolor=white@0.9:borderw=2:bordercolor=black@0.6:\
  font='JetBrains Mono':enable='between(t,5,85)'" \
  -c:v libx264 -crf 18 output_with_timer.mp4
```

### Text Overlays (FFmpeg drawtext or ASS subtitles)

For precise text overlay timing and styling, use ASS subtitles:

```ass
[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Style: Overlay,JetBrains Mono,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,40,40,80,1
Style: BigOverlay,JetBrains Mono,56,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,2,40,40,80,1

[Events]
Dialogue: 0,0:00:00.00,0:00:05.00,BigOverlay,,0,0,0,,armOS: USB boot to robot teleop
Dialogue: 0,0:00:45.00,0:00:55.00,Overlay,,0,0,0,,Auto-detected. Zero configuration.
Dialogue: 0,0:01:15.00,0:01:25.00,BigOverlay,,0,0,0,,From USB stick to this.
Dialogue: 0,0:01:25.00,0:01:30.00,BigOverlay,,0,0,0,,armOS. Boot from USB.\NDetect hardware. Start building.
```

### Subtitle Generation (for YouTube/accessibility)

Use OpenAI Whisper on the narrated version:

```bash
pip install openai-whisper
whisper armos_demo_v1_narrated.mp4 --model medium --output_format srt --language en
```

Cost: $0 (runs locally). Accuracy: 98%+ for clear narration.

### Alternative: Descript or CapCut

- **Descript** ($24/mo): Best if you want to edit by editing the transcript text. Overkill for a 90-second video with no spoken corrections.
- **CapCut** (free): Good for quick social media cuts (15-second Twitter clip). Use CapCut to create the short-form derivatives, not the main video.

**Verdict:** FFmpeg + Python for the main assembly (reproducible, free). CapCut for social media cuts.

---

## PART 5: BEYOND VIDEO -- INTERACTIVE EXPERIENCES

### 5A: Browser-Based armOS TUI Simulator

**Concept:** A "try before you download" experience embedded on the landing page. Visitors interact with a simulated armOS TUI in their browser -- complete with fake boot sequence, auto-detection, and telemetry.

**Implementation:**

| Approach | Tech Stack | Effort | Fidelity |
|---|---|---|---|
| **xterm.js terminal emulator** | TypeScript, xterm.js, pre-scripted ANSI sequences | 2-3 days | High -- looks like a real terminal |
| **Textual web export** | Python Textual app served via textual-web | 1 day | Very high -- actual TUI framework in browser |
| **WebAssembly Linux VM** | v86 (x86 emulator in JS) running a minimal Linux | 1 week | Extreme -- real Linux boot in browser |
| **Asciinema recording** | asciinema + asciinema-player embed | 2 hours | Medium -- playback only, not interactive |

**Recommended: xterm.js with scripted sequences**

```javascript
// Landing page: embedded terminal that "boots" armOS
const term = new Terminal({ theme: { background: '#1a1a2e' } });
term.open(document.getElementById('terminal'));

async function simulateBoot() {
  await typeText(term, "Loading armOS v1.0...", 50);
  await showProgressBar(term, 30);
  await typeText(term, "\n[OK] Hardware scan complete", 30);
  await typeText(term, "\n[OK] Feetech STS3215 detected on /dev/ttyUSB0", 30);
  await typeText(term, "\n[OK] SO-101 profile loaded", 30);
  await pause(500);
  await renderDashboard(term);  // Full TUI mockup
}
```

**Host on:** GitHub Pages (free) or Vercel (free tier).
**Cost:** $0 (developer time only).

### 5B: Rerun.io Embedded Telemetry Visualization

**Concept:** Embed a Rerun.io viewer on the landing page showing REAL telemetry data from an actual SO-101 teleop session. Visitors can scrub through time, rotate the 3D view, and inspect servo data.

**Implementation:**
1. Record a 60-second teleop session using `rerun` SDK logging
2. Export as `.rrd` file
3. Embed using Rerun's web viewer: `<iframe src="https://app.rerun.io/viewer?url=..."/>`

**Data to log:**
- 3D joint positions (animated robot arm model)
- Servo voltage, temperature, load (time series plots)
- Camera feed from USB camera (if available)
- Joint trajectory traces

**This is extremely compelling** because it shows real data, not a simulation. A visitor can zoom into a servo's voltage curve and see the 7.2V rail sag during fast moves. That level of transparency builds trust with the robotics audience.

**Cost:** $0 (Rerun is open source, hosting on their free viewer).

### 5C: HuggingFace Spaces Demo

**Concept:** A Gradio app on HuggingFace Spaces that lets visitors:
1. Upload a photo of their robot arm
2. armOS identifies the servos and suggests a profile
3. Shows what the TUI would look like for their specific hardware

**This is a stretch goal** but would be a powerful lead generation tool.

**Cost:** $0 (HuggingFace Spaces free tier).

---

## PART 6: DISTRIBUTION STRATEGY

### Primary Platforms

| Platform | Format | Duration | Purpose | CTA |
|---|---|---|---|---|
| **YouTube** | Full 90s, 1080p, narrated (Version B) | 1:30 | SEO, embed source, evergreen | "Link in description" to GitHub |
| **GitHub README** | Embedded YouTube or direct MP4 | 1:30 | First impression for repo visitors | Star the repo |
| **Landing page** | Autoplay muted (Version A), interactive TUI below | 1:30 | Conversion | Download / Join Discord |
| **Twitter/X** | 15-second highlight clip (Shot 10 money shot + end card) | 0:15 | Viral reach | "Full demo in thread" |
| **LinkedIn** | 30-second cut (problem + solution + money shot) | 0:30 | Professional reach | Landing page link |
| **HuggingFace** | Full video in model card / Space | 1:30 | ML community | GitHub link |
| **Reddit** (r/robotics, r/linux) | v.redd.it upload, 30-second cut | 0:30 | Community reach | Comment with GitHub link |
| **Discord** (LeRobot server) | Direct upload, full 90s | 1:30 | Core audience | GitHub link |

### Short-Form Derivatives (cut from the main video)

| Clip | Shots Used | Duration | Platform |
|---|---|---|---|
| "The money shot" | 10 + 11 | 15s | Twitter, Instagram Reels, TikTok |
| "Zero to teleop" | 2 + 7 + 10 | 30s | LinkedIn, Reddit |
| "Auto-detection" | 6 + 7 | 15s | Twitter (tech audience) |
| "Boot speed" | 3 + 4 + 5 | 15s | Twitter (Linux audience) |

Generate all derivatives with a single FFmpeg script:

```bash
# Money shot clip
ffmpeg -i armos_demo_v1.mp4 -ss 75 -t 15 -c:v libx264 -crf 20 clips/money_shot.mp4

# Zero to teleop clip
ffmpeg -i armos_demo_v1.mp4 \
  -filter_complex "[0:v]trim=5:10,setpts=PTS-STARTPTS[a]; \
  [0:v]trim=45:55,setpts=PTS-STARTPTS[b]; \
  [0:v]trim=75:85,setpts=PTS-STARTPTS[c]; \
  [a][b][c]concat=n=3:v=1:a=0[out]" \
  -map "[out]" clips/zero_to_teleop.mp4
```

---

## COST ESTIMATE

### Minimum Viable Video (Budget: ~$30)

| Item | Tool | Cost |
|---|---|---|
| Shots 1, 2, 3, 6 (hardware) | Kling 2.0 (cheapest) | $5 (25 clips at $0.20) |
| Shot 10 (arms moving) | Runway Gen-4 (need quality) | $10 (20 attempts at $0.50) |
| Shots 4, 5, 7, 8, 9 (screen) | Real recording (OBS + mock TUI) | $0 |
| Shot 11 + thumbnail | Flux 1.1 Pro | $1 |
| Narration | ElevenLabs Starter | $5/mo |
| Music | Suno Pro | $10/mo |
| Editing | FFmpeg + Python | $0 |
| Subtitles | Whisper (local) | $0 |
| **Total** | | **~$31** |

### High-Quality Video (Budget: ~$150)

| Item | Tool | Cost |
|---|---|---|
| Hardware shots | Runway Gen-4 Turbo (50 generations) | $25 |
| Arms moving (many attempts) | Runway Gen-4 Turbo (40 generations) | $20 |
| AI upscaling | Topaz Video AI (if needed) | $0 (use Real-ESRGAN free) |
| Screen recordings | OBS + mock TUI (Python Textual) | $0 |
| Thumbnail + end card | Flux 1.1 Pro (20 generations) | $1 |
| Narration | ElevenLabs Starter | $5 |
| Music | Suno Pro (1 month) | $10 |
| Editing | FFmpeg + Python | $0 |
| Interactive TUI (landing page) | xterm.js (developer time) | $0 |
| Rerun.io embed | Open source | $0 |
| **Total** | | **~$61** |

### Premium Video (Budget: ~$400)

| Item | Tool | Cost |
|---|---|---|
| All AI video shots | Runway Gen-4 Turbo (200 generations) | $100 |
| Blender render of SO-101 (Shot 10) | Blender + Cycles | $0 (time investment) |
| Professional upscaling | Topaz Video AI license | $199 |
| Narration (multiple voices/takes) | ElevenLabs Scale | $22/mo |
| Music (multiple tracks) | Suno Pro + Epidemic Sound | $25/mo |
| Descript (if manual editing needed) | Descript Pro | $24/mo |
| HuggingFace Spaces demo | Gradio + free tier | $0 |
| **Total** | | **~$370** |

---

## PRODUCTION TIMELINE

| Day | Task | Output |
|---|---|---|
| 1 | Build mock TUI with Python Textual (all screen shots) | 5 screen recording clips |
| 1 | Generate AI hardware shots (Shots 1, 2, 3, 6) | 4 video clips |
| 2 | Generate Shot 10 (arms moving) -- expect many iterations | 1 video clip |
| 2 | Generate narration (ElevenLabs) and music (Suno) | 2 audio files |
| 2 | Generate thumbnail and end card (Flux + Canva) | 2 images |
| 3 | Assemble with FFmpeg pipeline, add timer and overlays | 2 video files (silent + narrated) |
| 3 | Generate short-form clips for social media | 4 clips |
| 3 | Build xterm.js interactive demo for landing page | 1 HTML/JS embed |
| 4 | Upload to YouTube, embed in README, deploy landing page | Published |

**Total production time: 4 days, 1 person, no camera.**

---

## CRITICAL DECISION: AI-GENERATED VS. REAL RECORDING

After designing this entire pipeline, here is the honest assessment:

**Shots that MUST be real (AI cannot do them convincingly):**
- Shots 4, 5, 7, 8, 9 (screen captures with legible text) -- use mock TUI recordings
- Shot 10 (synchronized robot arms) -- AI cannot reliably generate two arms moving in sync. Use either real hardware or a Blender render with the actual URDF.

**Shots where AI adds genuine value:**
- Shots 1, 2, 3, 6 (hardware b-roll) -- AI handles these well and saves the cost/logistics of a camera setup
- Shot 11 + thumbnail -- AI-generated backgrounds with text overlay

**The hybrid approach is the answer.** About 60% of the video is real screen recordings (the credibility content) and 40% is AI-generated hardware b-roll (the production polish). This gives you a professional-looking video without a camera crew, while keeping the parts that matter most -- the actual software working -- grounded in reality.

**When the real software ships, re-record the entire video as one continuous take.** The AI version is the pre-launch placeholder. The real recording is the post-launch proof.
