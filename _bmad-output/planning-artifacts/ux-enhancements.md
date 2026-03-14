# armOS UX Enhancement Designs: Critical Flows

**Author:** Sally (UX Designer)
**Date:** 2026-03-15
**Status:** Detailed wireframes for 7 critical user flows
**Depends on:** vision.md, business-plan.md, market-research.md, product-validation.md, review-ux.md

---

## Table of Contents

1. [First Boot Experience](#1-first-boot-experience)
2. [Demo Mode](#2-demo-mode)
3. [Educator Flow](#3-educator-flow)
4. [Hackathon Flow](#4-hackathon-flow)
5. [Unboxing Flow](#5-unboxing-flow)
6. [Error Recovery Flow](#6-error-recovery-flow)
7. [Profile Sharing Flow](#7-profile-sharing-flow)

---

## 1. First Boot Experience

**Goal:** From BIOS to moving a robot arm in under 5 minutes. Every second of dead air or confusion is a user lost.

**Timing budget:**

| Phase | Target | Max Acceptable |
|-------|--------|----------------|
| GRUB menu | 0s (auto-select) | 5s (user reads, presses Enter) |
| Kernel + systemd boot | 30s | 60s |
| Plymouth splash | During boot | During boot |
| Desktop + TUI auto-launch | 5s | 10s |
| First-run wizard complete | 120s | 180s |
| First teleop movement | 180s | 300s |
| **Total: power button to robot moves** | **~3 min** | **~5 min** |

### Screen 1: GRUB (0-5 seconds)

```
+------------------------------------------------------------------+
|                                                                    |
|                                                                    |
|                         a r m O S  v0.1                            |
|                                                                    |
|                                                                    |
|    > Start armOS                                                   |
|      Start armOS (Surface Pro kernel)                              |
|      Advanced options...                                           |
|      Boot from local disk                                          |
|                                                                    |
|                                                                    |
|    Starting automatically in 5...                                  |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- Custom GRUB theme with dark background, armOS branding. No default purple Ubuntu.
- Auto-selects "Start armOS" after 5 seconds. No user action needed.
- Surface Pro kernel is a separate option because it includes linux-surface patches that can cause issues on non-Surface hardware. Users never need to think about this unless they are on a Surface.
- "Boot from local disk" lets users exit back to their installed OS without removing the USB. Critical for trust -- users need to know this is reversible.

### Screen 2: Plymouth Splash (30-60 seconds)

```
+------------------------------------------------------------------+
|                                                                    |
|                                                                    |
|                                                                    |
|                                                                    |
|                          ___                                       |
|                         /   \                                      |
|                        | O   |----+                                |
|                         \___/    |                                  |
|                                  +--[ ]                            |
|                                                                    |
|                        a r m O S                                   |
|                                                                    |
|                 [=========-----------]  45%                         |
|                                                                    |
|                   Detecting hardware...                             |
|                                                                    |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- Custom Plymouth theme replaces the Ubuntu boot animation. Users must never see scrolling systemd text.
- Progress bar advances based on systemd target completion (not a fake timer).
- Status text cycles through real stages: "Loading kernel modules..." / "Detecting hardware..." / "Starting services..." / "Almost ready..."
- Dark background, white text. Minimal. Professional.
- The progress bar manages expectations. Without it, 45 seconds of black screen feels broken.

### Screen 3: Hardware Detection Splash (5-10 seconds, during late boot)

```
+------------------------------------------------------------------+
|                                                                    |
|                        a r m O S                                   |
|                                                                    |
|                 [====================]  100%                        |
|                                                                    |
|     Hardware detected:                                             |
|       [OK] USB serial: 2 Feetech controllers found                |
|       [OK] Camera: 1 USB camera found                             |
|       [--] Wi-Fi: scanning...                                      |
|                                                                    |
|                   Launching setup...                                |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- This is still the Plymouth splash, but in the final seconds it shows what hardware was found. This builds confidence immediately -- before the user has done anything, the system is already working.
- Hardware detection runs as a late-boot systemd service that writes results to a shared file. Plymouth reads it.
- If NO hardware is found, the message changes to: "No robot hardware detected. Connect your robot arm and we'll find it." This is not an error -- it is guidance.

### Screen 4: First-Run Wizard -- Welcome

Condition: No `~/.config/armos/setup-complete` file exists.

```
+------------------------------------------------------------------+
|                                                                    |
|                    Welcome to armOS                                 |
|                                                                    |
|  Let's get your robot moving. This takes about 3 minutes.          |
|                                                                    |
|  Before we start, make sure:                                       |
|                                                                    |
|    [x] Robot arm(s) connected via USB                              |
|        (we found 2 Feetech controllers)                            |
|                                                                    |
|    [?] Power supply plugged into follower arm                      |
|        (we'll check voltage in a moment)                           |
|                                                                    |
|    [x] USB camera connected (optional)                             |
|        (found: USB 2.0 Camera on /dev/video0)                      |
|                                                                    |
|                                                                    |
|         [ Yes, let's go ]         [ Skip setup ]                   |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- Pre-fills checkboxes with detection results. The user sees that the system already knows what is connected. This is the "it just works" moment.
- The power supply gets a [?] because we cannot confirm voltage until we query the servos. Honest uncertainty.
- "Skip setup" goes to the raw TUI dashboard for power users. No gates.

### Screen 5: First-Run Wizard -- Arm Identification

```
+------------------------------------------------------------------+
|                                                                    |
|                 Which arm is which?                                 |
|                                                                    |
|  Wiggle a joint on the arm you want to use as the                  |
|  LEADER (the arm you move by hand).                                |
|                                                                    |
|  Listening for movement...                                         |
|                                                                    |
|    /dev/ttyUSB0:  [  waiting...  ]                                 |
|    /dev/ttyUSB1:  [  waiting...  ]                                 |
|                                                                    |
|                                                                    |
|                                                                    |
|                                                                    |
|                                                                    |
|                                                                    |
|  TIP: The leader arm is usually the one WITHOUT a power            |
|  supply. It runs on USB power alone.                               |
|                                                                    |
+------------------------------------------------------------------+
```

After user wiggles a joint:

```
+------------------------------------------------------------------+
|                                                                    |
|                 Which arm is which?                                 |
|                                                                    |
|  Wiggle a joint on the arm you want to use as the                  |
|  LEADER (the arm you move by hand).                                |
|                                                                    |
|                                                                    |
|    /dev/ttyUSB0:  [  waiting...       ]                            |
|    /dev/ttyUSB1:  [ >>> MOVEMENT! <<< ]                            |
|                                                                    |
|  Got it!                                                           |
|    /dev/ttyUSB1  =  LEADER arm  (you move this one)                |
|    /dev/ttyUSB0  =  FOLLOWER arm  (this one copies)                |
|                                                                    |
|  Is that right?                                                    |
|                                                                    |
|         [ Yes, correct ]          [ No, swap them ]                |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- This solves the #1 setup confusion from LeRobot issues: "which ttyUSB is which?" Instead of asking the user to trace cables, we listen for physical movement.
- Implementation: poll `Present_Position` on both buses at ~10Hz. First bus that shows position change > 50 ticks is identified as the arm being moved.
- "Is that right?" + swap option handles the case where the user accidentally bumps the wrong arm.
- Single-arm setups skip this screen entirely.

### Screen 6: First-Run Wizard -- Power Check

```
+------------------------------------------------------------------+
|                                                                    |
|                 Checking power supply...                            |
|                                                                    |
|  Follower arm (/dev/ttyUSB0):                                      |
|                                                                    |
|    Voltage:  12.1V  [=================---]  [OK]                   |
|                                                                    |
|    This looks good. Your power supply is providing                  |
|    enough voltage for normal operation.                             |
|                                                                    |
|                                                                    |
|  Leader arm (/dev/ttyUSB1):                                        |
|                                                                    |
|    Voltage:  5.0V  [====----------------]  [USB POWERED]           |
|                                                                    |
|    This is normal. The leader arm runs on USB bus power.            |
|                                                                    |
|                                                                    |
|                        [ Continue ]                                 |
|                                                                    |
+------------------------------------------------------------------+
```

Alternate: power problem detected:

```
+------------------------------------------------------------------+
|                                                                    |
|                 Checking power supply...                            |
|                                                                    |
|  Follower arm (/dev/ttyUSB0):                                      |
|                                                                    |
|    Voltage:  7.2V  [=========-----------]  [!! LOW !!]             |
|                                                                    |
|    WARNING: Voltage is below 11.0V. Your power supply              |
|    may not deliver enough current for all 6 servos.                |
|                                                                    |
|    What to do:                                                     |
|    1. Check that the power supply is rated 12V / 5A (60W)          |
|    2. Check that the barrel connector is fully seated               |
|    3. If using a USB-C power adapter, it may not provide           |
|       enough current -- use the included barrel jack supply         |
|                                                                    |
|    You can continue, but teleop may stutter under load.            |
|                                                                    |
|         [ Continue anyway ]       [ I'll fix this first ]          |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- We check voltage BEFORE calibration so we can warn early. A bad power supply causes servo jitter during calibration, which wastes the user's time.
- "I'll fix this first" pauses the wizard. When the user plugs in a better supply and presses Enter, we re-check.
- We never block on a warning. "Continue anyway" always works. The user might be using 7.4V LiPo intentionally.

### Screen 7: First-Run Wizard -- Calibration

```
+------------------------------------------------------------------+
|                                                                    |
|         Calibrating: Follower Arm            [=------] 1/6         |
|                                                                    |
|  Joint 1: SHOULDER PAN                                             |
|                                                                    |
|  Move this joint so the arm points STRAIGHT FORWARD.               |
|                                                                    |
|         Top-down view:                                             |
|                                                                    |
|              [ base ]                                              |
|                 |                                                   |
|                 |                                                   |
|                 v  <-- arm points this way                          |
|                                                                    |
|  Live position:  2048     (target: 1900 - 2100)                    |
|  [||||||||||||||||||||.......]                                      |
|   ^--- you are here                                                |
|                                                                    |
|  Status:  GOOD -- position is within expected range                |
|                                                                    |
|  [ Enter: Confirm ]    [ S: Skip ]    [ ?: What is this? ]        |
+------------------------------------------------------------------+
```

Next joint:

```
+------------------------------------------------------------------+
|                                                                    |
|         Calibrating: Follower Arm            [===----] 2/6         |
|                                                                    |
|  Joint 2: SHOULDER LIFT                                            |
|                                                                    |
|  Move this joint so the upper arm points STRAIGHT UP.              |
|                                                                    |
|         Side view:                                                 |
|                 ^                                                   |
|                 |  <-- upper arm points up                          |
|                 |                                                   |
|              [base]                                                |
|                                                                    |
|  Live position:  1923     (target: 1800 - 2100)                    |
|  [||||||||||||||||||........]                                       |
|   ^--- you are here                                                |
|                                                                    |
|  Status:  GOOD -- position is within expected range                |
|                                                                    |
|  [ Enter: Confirm ]    [ S: Skip ]    [ ?: What is this? ]        |
+------------------------------------------------------------------+
```

Gripper joint:

```
+------------------------------------------------------------------+
|                                                                    |
|         Calibrating: Follower Arm            [======] 6/6          |
|                                                                    |
|  Joint 6: GRIPPER                                                  |
|                                                                    |
|  Open the gripper fully, then close it fully.                      |
|  We'll record both positions.                                      |
|                                                                    |
|         Front view:                                                |
|              ___   ___                                              |
|             |   | |   |                                            |
|             |   | |   |   <-- open like this                       |
|             |___| |___|                                            |
|                                                                    |
|  Step 1 of 2: OPEN the gripper all the way.                        |
|  Live position:  1024                                              |
|                                                                    |
|  [ Enter: Record open position ]    [ S: Skip ]                   |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- One joint at a time. Never show all 6 at once -- that is overwhelming.
- ASCII art for every joint. Each diagram shows the specific physical motion expected. Even crude art is 10x better than "move to center position."
- Live position indicator updates in real-time (10Hz). Color-coded: green when in range, yellow when close, white when far.
- Progress bar (1/6, 2/6...) sets expectations. Users need to know this ends.
- "What is this?" explains calibration conceptually for the curious. Most users will just follow the pictures.
- After the follower arm, the wizard calibrates the leader arm with the same flow.

### Screen 8: First-Run Wizard -- Calibration Complete

```
+------------------------------------------------------------------+
|                                                                    |
|                  Calibration Complete!                              |
|                                                                    |
|  Both arms are calibrated and ready.                               |
|                                                                    |
|  Summary:                                                          |
|    Follower arm: 6/6 joints calibrated    [OK]                     |
|    Leader arm:   6/6 joints calibrated    [OK]                     |
|                                                                    |
|  Calibration saved to:                                             |
|  ~/.config/armos/calibration/so101-2xCH340/                       |
|                                                                    |
|                                                                    |
|  Ready to try it? Move the leader arm and the follower             |
|  will copy your movements in real time.                            |
|                                                                    |
|                                                                    |
|     [ T: Start Teleop! ]      [ D: Go to Dashboard ]              |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- Immediate gratification. The moment calibration ends, the user is one keypress from teleop. No menus to navigate, no commands to type.
- We save the `setup-complete` flag here. Next boot skips the wizard.
- The calibration path includes the adapter serial number so multiple robots can be calibrated on the same USB.

### Screen 9: Teleop Running

```
+------------------------------------------------------------------+
|  armOS v0.1  |  SO-101  |  TELEOP ACTIVE            00:01:23      |
+------------------------------------------------------------------+
|                                                                    |
|  LEADER (you move)           -->    FOLLOWER (copies you)          |
|                                                                    |
|  shoulder_pan    2048              shoulder_pan    2048         0   |
|  shoulder_lift   1923              shoulder_lift   1925        +2   |
|  elbow_flex      2100              elbow_flex      2098        -2   |
|  wrist_flex      2048              wrist_flex      2049        +1   |
|  wrist_roll      2048              wrist_roll      2048         0   |
|  gripper         1500              gripper         1500         0   |
|                                                                    |
|  HEALTH:                                                           |
|  Voltage   [=================---]  12.0V  ok                      |
|  Load      [=========-----------]  38%    ok                      |
|  Comms     [====================]  100%   ok                      |
|                                                                    |
|  Loop: 62 Hz  |  Errors: 0  |  Lag: <1ms                          |
|                                                                    |
+--[ Space: Pause ]--[ R: Record ]--[ S: Stop ]--[ Q: Dashboard ]---+
```

**Design decisions:**
- This is the payoff screen. The user sees their arm moving and the data confirming it.
- The delta column (rightmost) shows the difference between leader and follower. Should be near zero. If numbers grow, there is a problem.
- Health bars are always visible during teleop. Voltage sag and communication drops must be caught immediately.
- "R: Record" transitions to data collection without stopping teleop. Minimal friction for the "I want to collect training data" use case.

### Flow Diagram: Complete First Boot

```
Power button
    |
    v
[GRUB] ----5s auto-select----> [Plymouth splash]
    |                                |
    | (user selects option)          | 30-60 seconds
    v                                v
[Kernel boots]                  [Hardware detect]
                                     |
                            +--------+--------+
                            |                 |
                     First boot?          Returning?
                            |                 |
                            v                 v
                    [Welcome screen]     [TUI Dashboard]
                            |
                            v
                    [Arm identification]
                       (wiggle test)
                            |
                            v
                    [Power check]
                            |
                            v
                    [Calibration: Follower]
                       (6 joints)
                            |
                            v
                    [Calibration: Leader]
                       (6 joints)
                            |
                            v
                    [Complete! Start teleop?]
                            |
                            v
                    [TELEOP RUNNING]

    Total time: ~3-5 minutes from power button
```

---

## 2. Demo Mode

**Goal:** Trade show booth, YouTube recording, or classroom demonstration. The robot does something impressive with zero setup, zero explanation, and zero risk of failure.

**Entry:** `armos demo` from CLI, or a boot-time option.

### GRUB Entry for Demo Mode

```
+------------------------------------------------------------------+
|                                                                    |
|                         a r m O S  v0.1                            |
|                                                                    |
|    > Start armOS                                                   |
|      Start armOS (Surface Pro kernel)                              |
|      Demo Mode (auto-run showcase)                                 |
|      Advanced options...                                           |
|                                                                    |
|    Starting automatically in 5...                                  |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decision:** Demo mode is a GRUB option so you can set it as default. At a trade show, the booth staff just power-cycles the laptop and it starts running.

### Screen 1: Demo Mode -- Splash (5 seconds)

```
+------------------------------------------------------------------+
|                                                                    |
|                                                                    |
|                                                                    |
|                         a r m O S                                  |
|                                                                    |
|               Boot from USB. Detect hardware.                      |
|                     Start building.                                |
|                                                                    |
|                                                                    |
|             Detected: SO-101 (leader + follower)                   |
|                                                                    |
|                 Starting demo in 5...4...3...                       |
|                                                                    |
|                                                                    |
+------------------------------------------------------------------+
```

### Screen 2: Demo Mode -- Running

```
+------------------------------------------------------------------+
|  armOS DEMO  |  SO-101  |  Move the leader arm!       00:02:15    |
+==================================================================+
|                                                                    |
|  +---------------------------+  +------------------------------+   |
|  |                           |  |                              |   |
|  |    LEADER                 |  |    FOLLOWER                  |   |
|  |                           |  |                              |   |
|  |    shoulder_pan    2048   |  |    shoulder_pan    2048      |   |
|  |    shoulder_lift   1923   |  |    shoulder_lift   1925      |   |
|  |    elbow_flex      2100   |  |    elbow_flex      2098      |   |
|  |    wrist_flex      2048   |  |    wrist_flex      2049      |   |
|  |    wrist_roll      2048   |  |    wrist_roll      2048      |   |
|  |    gripper         1500   |  |    gripper         1500      |   |
|  |                           |  |                              |   |
|  +---------------------------+  +------------------------------+   |
|                                                                    |
|  [====================================] Voltage: 12.1V  Temp: 29C |
|                                                                    |
|  Move the leader arm and the follower copies your movements!       |
|  This is how you collect training data for robot AI.               |
|                                                                    |
+--[ This laptop booted from a USB stick in under 2 minutes ]-------+
```

### Screen 3: Demo Mode -- Auto-Routine (no human interaction)

For unattended demo (e.g., loop at a booth):

```
+------------------------------------------------------------------+
|  armOS DEMO  |  SO-101  |  Auto-Routine: Pick & Place  00:00:15   |
+==================================================================+
|                                                                    |
|  The follower arm is running a pre-trained AI policy.              |
|  No human is controlling it right now.                             |
|                                                                    |
|  +------------------------------------------------------------+   |
|  |                                                              |   |
|  |                    [ Camera Feed ]                           |   |
|  |                                                              |   |
|  |              Live view from USB camera                       |   |
|  |                                                              |   |
|  +------------------------------------------------------------+   |
|                                                                    |
|  Policy: pick_and_place_v3       Confidence: 92%                   |
|  Episode: 3 of 10 (looping)     Success rate: 8/10                |
|                                                                    |
|  This policy was trained from 50 human demonstrations              |
|  collected with armOS and trained in the cloud.                    |
|                                                                    |
+--[ armOS: from USB stick to robot AI in minutes ]--[ armos.dev ]--+
```

### Demo Mode Features

| Feature | Implementation | Why |
|---------|---------------|-----|
| Auto-calibration | Uses pre-stored calibration from last run | No setup delay at booth |
| Auto-start teleop | Launches teleop 5s after boot | Passersby can walk up and move the arm |
| Auto-routine loop | Cycles through pre-trained policies | Runs unattended during lunch break |
| Big text mode | Larger fonts, high contrast | Readable from 3 meters away at a booth |
| QR code on screen | Links to armos.dev or GitHub | Visitor scans to learn more |
| Marketing tagline | Rotates at bottom of screen | Every screenshot is marketing material |
| Crash recovery | Watchdog restarts demo on any failure | Must never show an error at a trade show |
| Kiosk lock | Ignores Ctrl+C, Alt+F4, etc. | Prevents passersby from exiting |

### Demo Mode Configuration

```yaml
# ~/.config/armos/demo.yaml
mode: demo
auto_start: true
teleop_on_boot: true
auto_routine:
  enabled: true
  policy: pick_and_place_v3
  loop: true
  episodes: 10
display:
  font_scale: 1.5
  show_qr: true
  qr_url: "https://armos.dev"
  tagline_rotate:
    - "Boot from USB. Detect hardware. Start building."
    - "From unboxing to robot AI in 5 minutes."
    - "The operating system for robot arms."
  marketing_bar: true
kiosk:
  lock_keyboard: true
  restart_on_crash: true
  crash_restart_delay: 5
```

### Flow Diagram: Demo Mode

```
Power button (or power cycle)
    |
    v
[GRUB: Demo Mode selected] --auto 3s--> [Plymouth splash]
    |                                          |
    v                                          v
[Boot with demo flag]                    [Hardware detect]
    |                                          |
    v                                          v
[Load pre-stored calibration]           [Skip wizard]
    |                                          |
    +-----------------+------------------------+
                      |
              +-------+-------+
              |               |
         Has policy?     No policy
              |               |
              v               v
    [Auto-routine loop]  [Teleop mode]
    (unattended, loops)  (interactive, waits
     pre-trained policy)  for someone to
                          move leader arm)
              |               |
              +-------+-------+
                      |
              [Crash watchdog]
              (restart in 5s on any failure)
```

---

## 3. Educator Flow

**Goal:** A teacher sets up 30 identical robot arms for a classroom. Bulk configuration, central monitoring, student identity, no per-station debugging.

**Timing goal:** 30 arms configured and tested in under 2 hours (4 minutes per arm, done in parallel batches).

### Step 1: Teacher Creates Master Configuration

The teacher sets up ONE arm station perfectly, then exports it.

```
+------------------------------------------------------------------+
|  armOS  |  Educator Tools  |  Create Classroom Config              |
+------------------------------------------------------------------+
|                                                                    |
|  Step 1 of 4: Configure Master Station                             |
|                                                                    |
|  You've calibrated this arm and verified teleop works.             |
|  Now let's package this configuration for your classroom.          |
|                                                                    |
|  What to include:                                                  |
|    [x] Robot profile (SO-101)                                      |
|    [x] Calibration template (students will re-calibrate)           |
|    [x] Protection settings (conservative -- safer for students)    |
|    [x] Classroom mode (locked settings, student login)             |
|    [ ] Specific calibration data (only for identical arms)         |
|    [ ] Pre-recorded demo dataset                                   |
|                                                                    |
|  Class name:  [ Robotics 101 -- Spring 2027_____________ ]        |
|  Stations:    [ 30 ]                                               |
|                                                                    |
|              [ Next: Student Setup ]                               |
|                                                                    |
+------------------------------------------------------------------+
```

### Step 2: Student Roster

```
+------------------------------------------------------------------+
|  armOS  |  Educator Tools  |  Student Setup                        |
+------------------------------------------------------------------+
|                                                                    |
|  Step 2 of 4: Student Accounts                                     |
|                                                                    |
|  How should students log in?                                       |
|                                                                    |
|    ( ) No login -- any student can use any station                 |
|    (*) Simple PIN -- each student gets a 4-digit code              |
|    ( ) Roster import -- upload a CSV with names                    |
|                                                                    |
|  Generate PINs for 30 students?                                    |
|                                                                    |
|    Station 01:  PIN 4821     Station 16:  PIN 3092                 |
|    Station 02:  PIN 7305     Station 17:  PIN 6157                 |
|    Station 03:  PIN 1947     Station 18:  PIN 8423                 |
|    ...                       ...                                   |
|    Station 15:  PIN 5638     Station 30:  PIN 2764                 |
|                                                                    |
|  [ Print PIN list ]    [ Export CSV ]    [ Next: USB Cloning ]     |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- PINs, not passwords. Students are not going to remember passwords for a robotics lab.
- Printable PIN list lets the teacher hand out slips of paper.
- "No login" option for low-stakes environments (workshops, hackathons).

### Step 3: USB Cloning

```
+------------------------------------------------------------------+
|  armOS  |  Educator Tools  |  USB Cloning                          |
+------------------------------------------------------------------+
|                                                                    |
|  Step 3 of 4: Clone to USB Drives                                  |
|                                                                    |
|  Insert blank USB drives. armOS will clone itself with your        |
|  classroom configuration onto each one.                            |
|                                                                    |
|  USB drives detected:                                              |
|    [OK]  /dev/sdb  SanDisk 32GB       Ready to clone              |
|    [OK]  /dev/sdc  Kingston 16GB      Ready to clone              |
|    [OK]  /dev/sdd  SanDisk 32GB       Ready to clone              |
|    [OK]  /dev/sde  Samsung 64GB       Ready to clone              |
|    [!!]  /dev/sdf  Generic 4GB        TOO SMALL (min 8GB)         |
|                                                                    |
|  Each clone takes ~8 minutes on USB 3.0.                           |
|  4 drives x 8 min = ~8 min (parallel cloning).                     |
|  30 drives in 8 batches = ~64 minutes total.                       |
|                                                                    |
|       [ Clone All Ready Drives ]       [ Cancel ]                  |
|                                                                    |
+------------------------------------------------------------------+
```

Cloning progress:

```
+------------------------------------------------------------------+
|  armOS  |  Educator Tools  |  Cloning...                           |
+------------------------------------------------------------------+
|                                                                    |
|  Cloning classroom "Robotics 101 -- Spring 2027"                   |
|  Batch 1 of 8                                                      |
|                                                                    |
|    /dev/sdb  [===============-------]  62%   Station 01            |
|    /dev/sdc  [==============---------]  58%   Station 02            |
|    /dev/sdd  [================------]  68%   Station 03            |
|    /dev/sde  [============----------]  52%   Station 04            |
|                                                                    |
|  Estimated time remaining: 3 min 14 sec                            |
|                                                                    |
|  Completed: 0 / 30                                                 |
|                                                                    |
|  Each USB will boot with:                                          |
|    - Pre-configured SO-101 profile                                 |
|    - Student login prompt (PIN)                                    |
|    - Conservative protection settings                              |
|    - Locked settings (students cannot change profiles)             |
|                                                                    |
|                          [ Cancel ]                                |
+------------------------------------------------------------------+
```

### Step 4: Classroom Dashboard (Teacher's Station)

```
+------------------------------------------------------------------+
|  armOS  |  CLASSROOM: Robotics 101  |  Teacher Dashboard           |
+==================================================================+
|                                                                    |
|  30 stations  |  28 online  |  2 offline  |  1 alert               |
|                                                                    |
|  +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+  |
|  | S01 | S02 | S03 | S04 | S05 | S06 | S07 | S08 | S09 | S10 |  |
|  | [G] | [G] | [Y] | [G] | [G] | [G] | [G] | [G] | [--]| [G] |  |
|  +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+  |
|  | S11 | S12 | S13 | S14 | S15 | S16 | S17 | S18 | S19 | S20 |  |
|  | [G] | [G] | [G] | [G] | [G] | [G] | [G] | [G] | [G] | [--]|  |
|  +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+  |
|  | S21 | S22 | S23 | S24 | S25 | S26 | S27 | S28 | S29 | S30 |  |
|  | [G] | [G] | [G] | [G] | [G] | [G] | [G] | [G] | [G] | [G] |  |
|  +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+  |
|                                                                    |
|  [G]=Good  [Y]=Warning  [R]=Fault  [--]=Offline                   |
|                                                                    |
|  ALERTS:                                                           |
|  [Y] Station 03: Voltage low (10.8V). Check power supply.         |
|                                                                    |
|  ACTIVITY:                                                         |
|  12 students teleoperating  |  8 calibrating  |  8 idle            |
|                                                                    |
+--[ B: Broadcast message ]--[ L: Lock all ]--[ D: Drill down ]-----+
```

### Drill-Down: Single Station

```
+------------------------------------------------------------------+
|  armOS  |  CLASSROOM  |  Station 03 Detail                         |
+------------------------------------------------------------------+
|                                                                    |
|  Station: 03           Student: Alice Chen (PIN 1947)              |
|  Status:  [WARNING]    Connected since: 14:23                      |
|                                                                    |
|  HARDWARE:                                                         |
|    Follower:  6/6 servos    Voltage: 10.8V [!! LOW]                |
|    Leader:    6/6 servos    Voltage: 5.0V  [USB]                   |
|    Camera:    Connected                                            |
|                                                                    |
|  ACTIVITY:                                                         |
|    Current: Teleoperating (started 14:31)                          |
|    Episodes recorded: 3                                            |
|    Total teleop time: 12 min                                       |
|                                                                    |
|  ALERTS:                                                           |
|    14:35  [WARN] Voltage dropped to 10.8V                          |
|    14:23  [INFO] Student logged in                                 |
|    14:22  [INFO] Station booted                                    |
|                                                                    |
|  ACTIONS:                                                          |
|    [ M: Send message ]  [ L: Lock station ]  [ R: Remote diag ]   |
|                                                                    |
+--[ B: Back to grid ]----------------------------------------------|
```

### Student Login Screen

What the student sees when they boot their station:

```
+------------------------------------------------------------------+
|                                                                    |
|                         a r m O S                                  |
|                                                                    |
|              Robotics 101 -- Spring 2027                           |
|              Station 03                                            |
|                                                                    |
|                                                                    |
|              Enter your PIN:  [ ____ ]                             |
|                                                                    |
|                                                                    |
|              (Ask your teacher if you don't have a PIN)            |
|                                                                    |
+------------------------------------------------------------------+
```

After login:

```
+------------------------------------------------------------------+
|  armOS  |  Station 03  |  Alice Chen                               |
+==================================================================+
|                                                                    |
|  Welcome, Alice!                                                   |
|                                                                    |
|  Today's Lab: Teleoperation and Data Collection                    |
|                                                                    |
|  Steps:                                                            |
|    1. [x] Log in                                                   |
|    2. [ ] Calibrate your arm (if not done)                         |
|    3. [ ] Practice teleoperation for 5 minutes                     |
|    4. [ ] Record 10 pick-and-place episodes                        |
|    5. [ ] Upload your dataset                                      |
|                                                                    |
|  Your arm:  SO-101 Follower  |  Calibrated: Yes  |  Health: [OK]  |
|                                                                    |
|     [ T: Start Teleop ]    [ C: Calibrate ]    [ ?: Help ]        |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- The teacher defines the lab steps in a config file. armOS renders them as a checklist. Students see their progress.
- Locked mode: students cannot change protection settings, profiles, or system config. They can calibrate, teleop, and record.
- The teacher dashboard uses mDNS/Avahi to discover stations on the local network. No IP configuration needed.
- "Broadcast message" lets the teacher send a message to all stations (e.g., "Stop teleop, we're starting the lecture").

### Bulk Calibration Strategy

Calibrating 30 arms individually takes ~3 min each = 90 minutes. That is too long.

**Solution: Jig-based batch calibration**

```
+------------------------------------------------------------------+
|  armOS  |  Educator Tools  |  Batch Calibration                    |
+------------------------------------------------------------------+
|                                                                    |
|  Batch calibration uses a physical jig to position all arms        |
|  identically, then records calibration for all at once.            |
|                                                                    |
|  Instructions:                                                     |
|    1. Place each arm in the calibration jig (included with         |
|       educator kit) so all joints are at known positions.          |
|    2. Connect all arms via USB hub.                                |
|    3. Press "Calibrate All" below.                                 |
|                                                                    |
|  Connected arms: 6 of 30 (connect more, or calibrate in batches)  |
|                                                                    |
|    /dev/ttyUSB0:  6 servos  [READY]                                |
|    /dev/ttyUSB1:  6 servos  [READY]                                |
|    /dev/ttyUSB2:  6 servos  [READY]                                |
|    /dev/ttyUSB3:  6 servos  [READY]                                |
|    /dev/ttyUSB4:  6 servos  [READY]                                |
|    /dev/ttyUSB5:  6 servos  [READY]                                |
|                                                                    |
|      [ Calibrate All 6 ]       [ Add More Arms ]                  |
|                                                                    |
+------------------------------------------------------------------+
```

**Alternative: Skip calibration entirely.** If all arms are assembled identically (same 3D print, same servo brand), the factory default positions may be close enough. The teacher tests one arm, and if the calibration is acceptable, deploys it to all 30 USBs. Students only re-calibrate if their specific arm drifts.

### Educator Flow Diagram

```
Teacher's laptop
    |
    v
[Set up ONE arm perfectly]
    |
    v
[armos educator create-class]
    |
    +---> Configure: class name, student count, PINs
    |
    +---> Select: which settings to lock
    |
    +---> Clone: USB drives in batches of 4-8
    |
    v
[Distribute USBs to stations]
    |
    v
[Students boot, enter PIN]
    |
    v
[Students calibrate their own arm]
    |
    v
[Students complete lab checklist]
    |                             Teacher's laptop
    |                                  |
    +-----(mDNS discovery)---------->  |
                                       v
                              [Teacher dashboard]
                              [30-station grid view]
                              [alerts, activity, progress]
```

---

## 4. Hackathon Flow

**Goal:** Participant receives USB stick at check-in. First teleop in under 10 minutes including booting a borrowed laptop. First data collection in under 20 minutes.

**Context:** The LeRobot hackathon had 3,000 participants across 100+ cities. That is our target event.

### Check-In

Physical handoff at registration:

```
+----------------------------------------------------+
|                                                      |
|  HACKATHON CHECK-IN                                  |
|                                                      |
|  You receive:                                        |
|    1. armOS USB stick (pre-configured)               |
|    2. Station number card (matches your table)       |
|    3. Quick start card (see below)                   |
|                                                      |
|  Your table has:                                     |
|    - SO-101 arm pair (leader + follower)             |
|    - 12V power supply (already plugged in)           |
|    - USB camera                                      |
|    - Laptop (any x86, provided or bring your own)    |
|                                                      |
+----------------------------------------------------+
```

### Quick Start Card (physical, printed, 4x6 inches)

```
+----------------------------------------------------+
|                                                      |
|  armOS QUICK START           [QR code -> armos.dev]  |
|                                                      |
|  1. Plug USB stick into laptop                       |
|  2. Restart laptop, boot from USB                    |
|     (F12 or F2 at startup for boot menu)             |
|  3. Wait 2 minutes. armOS handles the rest.          |
|  4. Follow the on-screen wizard.                     |
|  5. Move the LEADER arm. The FOLLOWER copies.        |
|                                                      |
|  STUCK?  Flag down a mentor.                         |
|  Wi-Fi:  HackathonNet / password: robots2027         |
|                                                      |
|  Your station PIN: 4821                              |
|                                                      |
+----------------------------------------------------+
```

### Hackathon Boot Screen (customized)

```
+------------------------------------------------------------------+
|                                                                    |
|                         a r m O S                                  |
|                                                                    |
|            LeRobot Hackathon -- San Francisco                      |
|                   March 2027                                       |
|                                                                    |
|                                                                    |
|             Detected: SO-101 (leader + follower)                   |
|             Camera: USB 2.0 Camera                                 |
|                                                                    |
|             Welcome! Follow the wizard to get started.              |
|                                                                    |
+------------------------------------------------------------------+
```

### Hackathon Wizard (abbreviated)

The hackathon wizard is shorter than the standard first-run wizard. Assumptions: arms are pre-assembled, power supply is already connected, camera is already connected.

```
+------------------------------------------------------------------+
|                                                                    |
|  HACKATHON SETUP                              Step 1 of 3          |
|                                                                    |
|  Identifying arms... wiggle the LEADER arm.                        |
|                                                                    |
|    /dev/ttyUSB0:  [  waiting...       ]                            |
|    /dev/ttyUSB1:  [ >>> MOVEMENT! <<< ]                            |
|                                                                    |
|    Leader: ttyUSB1    Follower: ttyUSB0                            |
|                                                                    |
|         [ Correct ]            [ Swap ]                            |
|                                                                    |
+------------------------------------------------------------------+
```

```
+------------------------------------------------------------------+
|                                                                    |
|  HACKATHON SETUP                              Step 2 of 3          |
|                                                                    |
|  Quick calibration... follow the guide for each joint.             |
|                                                                    |
|  Joint 1/6: SHOULDER PAN -- point arm STRAIGHT FORWARD             |
|                                                                    |
|  Live: 2048  [||||||||||||||||||..........]  [OK]                  |
|                                                                    |
|  [ Enter: Confirm ]                                                |
|                                                                    |
+------------------------------------------------------------------+
```

```
+------------------------------------------------------------------+
|                                                                    |
|  HACKATHON SETUP                              Step 3 of 3          |
|                                                                    |
|  You're ready! Time from boot: 6 minutes 12 seconds.              |
|                                                                    |
|  Start teleoperating now. Your schedule:                           |
|                                                                    |
|    14:00 - 14:30  Practice teleop, explore the arm                 |
|    14:30 - 16:00  Collect training data (goal: 50 episodes)        |
|    16:00 - 17:00  Upload data, start cloud training                |
|    17:00 - 18:00  Download policy, test inference                  |
|    18:00           Demo your results!                              |
|                                                                    |
|      [ T: Start Teleop Now! ]       [ D: Dashboard ]              |
|                                                                    |
+------------------------------------------------------------------+
```

### Hackathon Leaderboard (optional, projected on wall)

```
+------------------------------------------------------------------+
|  armOS HACKATHON LEADERBOARD                        Live           |
+==================================================================+
|                                                                    |
|  RANK  TEAM         EPISODES   BEST POLICY   STATUS                |
|  ----  ----------   --------   -----------   -------               |
|   1.   Team Alpha       87     pick_place    Training...           |
|   2.   RoboWizards      72     sort_blocks   Training...           |
|   3.   ArmChair AI      65     stack_cups    Collecting            |
|   4.   The Graspers     51     pick_place    Training...           |
|   5.   Bot Squad        43     sort_blocks   Collecting            |
|   ...                                                              |
|  24.   First Timers      8     --            Calibrating           |
|                                                                    |
|  TOTAL: 24 teams  |  847 episodes collected  |  6 training jobs    |
|                                                                    |
+------------------------------------------------------------------+
```

### Hackathon Timing Goals

| Milestone | Target | Hard Limit |
|-----------|--------|------------|
| USB inserted to GRUB | 0s (auto) | 30s |
| Boot complete | 90s | 120s |
| Wizard complete | 5 min | 8 min |
| First teleop movement | 6 min | 10 min |
| First recorded episode | 10 min | 15 min |
| 50 episodes collected | 2 hours | 3 hours |
| Policy trained (cloud) | +30 min | +60 min |
| Inference running locally | +5 min | +10 min |

### Flow Diagram: Hackathon

```
Check-in: receive USB + quick start card
    |
    v
[Plug USB into any laptop]
    |
    v
[Boot from USB] --- 90 seconds ---> [Hackathon wizard]
    |                                       |
    |                                  3 steps only:
    |                                  1. Wiggle test
    |                                  2. Quick calibrate
    |                                  3. Ready!
    |                                       |
    v                                       v
[Teleop running] ------------- 6 min from power button
    |
    v
[Record episodes] ------------ 10 min from power button
    |
    v
[Upload to cloud training] --- 2 hours in
    |
    v
[Download policy, run inference] -- 2.5 hours in
    |
    v
[Demo to judges] ------------- end of hackathon
```

---

## 5. Unboxing Flow

**Goal:** Customer buys a Seeed Studio SO-101 kit and an armOS USB stick (bundled or separate purchase). The entire experience from opening the shipping box to moving the robot is designed.

### What's in the Box (armOS Edition Kit)

```
+------------------------------------------------------------------+
|                                                                    |
|  SEEED STUDIO SO-101 + armOS EDITION                               |
|                                                                    |
|  Box contents:                                                     |
|                                                                    |
|  +----------------+  +----------------+  +----------------+        |
|  | SO-101 Leader  |  | SO-101 Follower|  | armOS USB      |        |
|  | Arm Kit        |  | Arm Kit        |  | Stick          |        |
|  | (assembled or  |  | (assembled or  |  |                |        |
|  |  3D print kit) |  |  3D print kit) |  | [armOS logo]   |        |
|  +----------------+  +----------------+  +----------------+        |
|                                                                    |
|  +----------------+  +----------------+  +----------------+        |
|  | 12V 5A Power   |  | USB-A Cable    |  | Quick Start    |        |
|  | Supply         |  | (x2)           |  | Guide          |        |
|  | (barrel jack)  |  |                |  | (printed card)  |        |
|  +----------------+  +----------------+  +----------------+        |
|                                                                    |
|  Optional add-ons (separate purchase):                             |
|    - USB camera for data collection                                |
|    - USB hub (if laptop has only 1 USB port)                       |
|                                                                    |
+------------------------------------------------------------------+
```

### Quick Start Guide (printed, in the box)

Side 1:

```
+------------------------------------------------------------------+
|                                                                    |
|  armOS QUICK START GUIDE                                           |
|                                                                    |
|  STEP 1: CONNECT HARDWARE                                          |
|                                                                    |
|      [Laptop]                                                      |
|        |   |                                                       |
|       USB  USB                                                     |
|        |    |                                                       |
|   [Leader] [Follower]------[12V Power]                             |
|     arm       arm           supply                                 |
|                                                                    |
|  - Plug both arms into laptop USB ports                            |
|  - Plug 12V power supply into the FOLLOWER arm only                |
|  - (Optional) Plug USB camera into laptop                          |
|                                                                    |
|  STEP 2: BOOT                                                      |
|                                                                    |
|  - Insert the armOS USB stick                                      |
|  - Restart your laptop                                             |
|  - Press F12 (or F2 or DEL) during startup for boot menu           |
|  - Select the armOS USB drive                                      |
|                                                                    |
|  STEP 3: FOLLOW THE WIZARD                                         |
|                                                                    |
|  - armOS will detect your hardware automatically                   |
|  - Follow the on-screen calibration guide                          |
|  - Move the leader arm -- the follower copies!                     |
|                                                                    |
|  Need help? Scan the QR code -->   [QR: armos.dev/help]           |
|                                                                    |
+------------------------------------------------------------------+
```

Side 2:

```
+------------------------------------------------------------------+
|                                                                    |
|  BOOT MENU KEYS BY MANUFACTURER                                   |
|                                                                    |
|  If your laptop doesn't boot from USB automatically:              |
|                                                                    |
|    Dell .............. F12                                          |
|    HP ................ F9                                           |
|    Lenovo ............ F12                                          |
|    ASUS .............. F8 or F2 (enter BIOS, change boot order)    |
|    Acer .............. F12                                          |
|    Microsoft Surface . Volume Down (hold while pressing power)     |
|    Toshiba ........... F12                                          |
|    Samsung ........... F2 (enter BIOS)                              |
|    Other ............. Try F2, F12, DEL, or ESC                    |
|                                                                    |
|  TROUBLESHOOTING                                                   |
|                                                                    |
|  "USB not in boot menu"                                            |
|    --> Enter BIOS, disable Secure Boot, enable USB boot            |
|                                                                    |
|  "Arm not detected"                                                |
|    --> Try a different USB port. Check cable connection.            |
|                                                                    |
|  "Follower arm doesn't move"                                      |
|    --> Check 12V power supply is plugged in and switched on.       |
|                                                                    |
|  "Servos make clicking sounds"                                     |
|    --> Power supply may be too weak. Use the included 12V 5A.     |
|                                                                    |
|  Full documentation: armos.dev/docs                                |
|  Community Discord: armos.dev/discord                              |
|                                                                    |
+------------------------------------------------------------------+
```

### Unboxing Timeline (target experience)

```
Minute 0:    Open box
             |
Minute 1:    Identify parts (quick start guide helps)
             |
Minute 2:    Connect follower arm USB + power supply
             Connect leader arm USB
             |
Minute 3:    Insert armOS USB, restart laptop
             |
Minute 4:    GRUB menu appears, auto-boots
             |
Minute 5:    Plymouth splash, hardware detected
             |
Minute 6:    First-run wizard starts
             |
Minute 7:    Arm identification (wiggle test)
             |
Minute 8:    Power check passes
             |
Minute 10:   Calibration complete (6 joints x 2 arms)
             |
Minute 11:   TELEOP RUNNING -- ROBOT MOVES!
```

**Design decisions:**
- The quick start guide is a physical card, not a URL. When you open a box, you do not want to navigate to a website on your phone.
- Boot menu keys table is critical. "How do I boot from USB?" is the #1 question we will get. Preempt it.
- The 12V 5A power supply is specifically called out. The #1 hardware failure is an underpowered supply.
- Two USB cables are included because many laptops only have 2 USB ports and users will not have spares.

### First-Time Boot Detection

If armOS detects it is being booted for the first time on this specific laptop (by checking hardware fingerprint), it shows a special welcome:

```
+------------------------------------------------------------------+
|                                                                    |
|                    Welcome to armOS!                                |
|                                                                    |
|  It looks like this is your first time booting armOS               |
|  on this computer.                                                 |
|                                                                    |
|  Your computer:                                                    |
|    Model: Dell Latitude 5520                                       |
|    CPU: Intel Core i5-1135G7                                       |
|    RAM: 16 GB                                                      |
|    USB ports: 3 available                                          |
|                                                                    |
|  Compatibility: EXCELLENT                                          |
|    All hardware checks passed.                                     |
|                                                                    |
|  NOTE: Your existing operating system is untouched.                |
|  armOS runs entirely from the USB stick. Remove it                 |
|  and restart to return to your normal OS.                          |
|                                                                    |
|                      [ Continue ]                                  |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decision:** The "your OS is untouched" message is critical for trust. Users are plugging a mysterious USB stick into their laptop. They need to know it is safe.

---

## 6. Error Recovery Flow

**Goal:** When something goes wrong, armOS diagnoses the problem, explains it in plain English, and guides the user to a fix. No error is a dead end.

### Error Severity Model

```
CRITICAL  ----  Robot stopped. Immediate action needed.
                Red background. Modal dialog. Audio beep.
                User must acknowledge before continuing.

WARNING   ----  Robot still works, but something is degraded.
                Yellow banner. Toast notification (10s).
                Actionable advice shown.

INFO      ----  Status change. No action needed.
                Brief flash in status bar. Logged.
```

### Scenario 1: Power Supply Too Weak

**Detection:** Voltage reads below 11.0V on follower arm during teleop.

```
+------------------------------------------------------------------+
|                                                                    |
|  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    |
|  !!                                                          !!    |
|  !!   [WARNING] LOW VOLTAGE ON FOLLOWER ARM                  !!    |
|  !!                                                          !!    |
|  !!   Voltage: 9.2V (expected: 12V)                          !!    |
|  !!                                                          !!    |
|  !!   WHAT'S HAPPENING:                                      !!    |
|  !!   Your power supply can't deliver enough current.        !!    |
|  !!   When multiple servos move at once, the voltage drops   !!    |
|  !!   and servos stutter or freeze.                          !!    |
|  !!                                                          !!    |
|  !!   HOW TO FIX:                                            !!    |
|  !!   1. Check that your power supply is rated 12V / 5A      !!    |
|  !!      (60W minimum). Look at the label on the adapter.    !!    |
|  !!   2. If it says 12V / 2A, that's too weak. You need      !!    |
|  !!      a bigger one. Search "12V 5A barrel jack adapter."   !!    |
|  !!   3. Check that the barrel connector is fully pushed in.  !!    |
|  !!                                                          !!    |
|  !!   Teleop is paused. Fix the power and press R to resume.  !!    |
|  !!                                                          !!    |
|  !!   [ R: Resume ]    [ D: Run diagnostics ]    [ Q: Quit ] !!    |
|  !!                                                          !!    |
|  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    |
|                                                                    |
+------------------------------------------------------------------+
```

**Decision tree for voltage errors:**

```
Voltage reading
    |
    +-- > 11.5V ---------> [OK] no action
    |
    +-- 11.0V - 11.5V ---> [WARN] toast: "Voltage slightly low.
    |                        Consider upgrading power supply."
    |
    +-- 9.0V - 11.0V ----> [WARN] modal: "Low voltage. Teleop may
    |                        stutter. See fix steps above."
    |
    +-- 7.0V - 9.0V -----> [CRITICAL] auto-stop teleop.
    |                        "Voltage dangerously low. Servos
    |                         may behave unpredictably."
    |
    +-- < 7.0V -----------> [CRITICAL] disable all motor commands.
                             "Voltage critically low. Motors
                              disabled for safety."
```

### Scenario 2: Servo Overload

**Detection:** Status register shows overload flag, or load exceeds 90%.

```
+------------------------------------------------------------------+
|                                                                    |
|  [CRITICAL] SERVO OVERLOADED                                       |
|                                                                    |
|  Joint: elbow_flex (servo ID 3)                                    |
|  Load: 98% --> OVERLOAD PROTECTION TRIPPED                        |
|                                                                    |
|  The servo has shut itself down to prevent damage.                 |
|  This is a safety feature, not a malfunction.                      |
|                                                                    |
|  COMMON CAUSES:                                                    |
|                                                                    |
|   1. ARM HIT AN OBSTACLE                                          |
|      Is something blocking the elbow? Remove it.                   |
|                                                                    |
|   2. JOINT IS MECHANICALLY STUCK                                   |
|      A 3D-printed part may be rubbing. Gently wiggle              |
|      the joint by hand (with power off) to check.                  |
|                                                                    |
|   3. ARM TRIED TO MOVE TOO FAR                                    |
|      Calibration limits may be wrong. Re-calibrate                |
|      after clearing this error.                                    |
|                                                                    |
|  TO RECOVER:                                                       |
|    1. Remove any obstruction                                       |
|    2. Press C to clear the error and re-enable the servo           |
|    3. If it happens again, run diagnostics                         |
|                                                                    |
|  [ C: Clear error ]  [ D: Diagnose ]  [ P: Power cycle arm ]     |
|                                                                    |
+------------------------------------------------------------------+
```

### Scenario 3: Cable Loose / Servo Disconnected

**Detection:** `sync_read` fails for specific servo IDs, or servo count drops below expected.

```
+------------------------------------------------------------------+
|                                                                    |
|  [CRITICAL] SERVO LOST                                             |
|                                                                    |
|  Can't communicate with: wrist_roll (servo ID 5)                  |
|  on the FOLLOWER arm.                                              |
|                                                                    |
|  Other servos on this arm are still responding.                    |
|  Teleop is paused for safety.                                      |
|                                                                    |
|  MOST LIKELY:                                                      |
|                                                                    |
|    The servo cable came loose.                                     |
|                                                                    |
|    +------+    +------+    +------+                                |
|    | J4   |----| J5   |----| J6   |                                |
|    | OK   |    | LOST |    | ???  |                                |
|    +------+    +------+    +------+                                |
|                  ^                                                  |
|                  |                                                  |
|            Check cable here                                        |
|                                                                    |
|  The cable between joints 4 and 5 (wrist_flex to wrist_roll)      |
|  is the most likely culprit. It's the small white connector.       |
|                                                                    |
|  Push the connector firmly into both ends. You should hear         |
|  a click.                                                          |
|                                                                    |
|  [ R: Retry detection ]   [ S: Skip servo, continue with 5 ]     |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- The ASCII diagram shows WHERE the cable is. This is worth a thousand words.
- We identify the cable by its position in the daisy chain (between joints 4 and 5), not by its servo ID. Users think in physical terms, not protocol terms.
- "Skip servo, continue with 5" allows graceful degradation. If a non-critical servo is lost, the user can keep working.

### Scenario 4: USB Disconnected Mid-Session

```
+------------------------------------------------------------------+
|                                                                    |
|  [CRITICAL] ARM DISCONNECTED                                       |
|                                                                    |
|  The FOLLOWER arm (/dev/ttyUSB0) is no longer responding.          |
|  Teleop has been stopped.                                          |
|                                                                    |
|  WHAT TO CHECK:                                                    |
|                                                                    |
|    1. Is the USB cable still plugged in?                           |
|       (Check both the laptop end and the arm end)                   |
|                                                                    |
|    2. Did the USB hub lose power?                                  |
|       (If using a hub, check its power supply)                     |
|                                                                    |
|    3. Was the arm bumped? The USB-C connector on some              |
|       laptops can be jostled loose.                                |
|                                                                    |
|  armOS is watching for the arm to reconnect...                     |
|                                                                    |
|  [ Waiting... will auto-resume when detected ]                     |
|                                                                    |
|  (or press Q to quit to dashboard)                                 |
|                                                                    |
+------------------------------------------------------------------+
```

After user reconnects:

```
+------------------------------------------------------------------+
|                                                                    |
|  [OK] ARM RECONNECTED                                              |
|                                                                    |
|  The follower arm is back online.                                  |
|                                                                    |
|  Quick health check:                                               |
|    Servos: 6/6 responding    [OK]                                  |
|    Voltage: 12.1V            [OK]                                  |
|    Calibration: still valid  [OK]                                  |
|                                                                    |
|  Ready to resume teleop.                                           |
|                                                                    |
|  [ T: Resume teleop ]    [ D: Run full diagnostics first ]        |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- Auto-detection of reconnection. The user plugs the cable back in and armOS picks it up. No restart needed.
- Quick health check on reconnect confirms the arm is in a good state before resuming.
- "Still valid" calibration check compares current servo positions to stored calibration data. If positions drifted during disconnect, we flag it.

### Scenario 5: brltty Conflict (first boot only)

```
+------------------------------------------------------------------+
|                                                                    |
|  [INFO] Serial Port Configuration                                  |
|                                                                    |
|  armOS detected that brltty (a Braille display driver) is          |
|  running. This service sometimes claims USB serial ports           |
|  that are needed for robot communication.                          |
|                                                                    |
|  On armOS, brltty has been disabled by default.                    |
|                                                                    |
|  If you use a Braille display and need brltty, you can             |
|  re-enable it in Settings > System > Accessibility.                |
|                                                                    |
|  No action needed. This is already handled.                        |
|                                                                    |
|                        [ OK ]                                      |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decision:** On armOS, brltty is removed from the image entirely. This screen only appears if the user installs it manually or if we detect remnants. The point is: armOS solves this problem before the user ever encounters it.

### Error Recovery Flow Diagram

```
[Error occurs during operation]
    |
    v
[Classify severity]
    |
    +-- CRITICAL ---------> [Auto-stop affected operations]
    |                              |
    |                              v
    |                        [Modal dialog]
    |                        - What happened (plain English)
    |                        - Most likely cause
    |                        - Step-by-step fix
    |                        - ASCII diagram if relevant
    |                              |
    |                        [User takes action]
    |                              |
    |                        [Verify fix worked]
    |                              |
    |                     +--------+--------+
    |                     |                 |
    |                   Fixed            Not fixed
    |                     |                 |
    |                     v                 v
    |              [Resume operation]  [Escalate to diagnostics]
    |                                       |
    |                                       v
    |                              [armos diagnose]
    |                              [Full system check]
    |                                       |
    |                              [Detailed report with
    |                               per-component status]
    |
    +-- WARNING ----------> [Toast notification]
    |                        - Brief description
    |                        - One-line fix suggestion
    |                        - Continue operating
    |                              |
    |                        [Log for later review]
    |
    +-- INFO -------------> [Status bar flash]
                             [Log only]
```

---

## 7. Profile Sharing Flow

**Goal:** A user calibrates a robot, tunes its settings, and wants to share that configuration so others with the same hardware can skip setup. Think Docker Hub for robot configurations.

### Creating a Profile

After a successful calibration and teleop test:

```
+------------------------------------------------------------------+
|  armOS  |  Profile Manager  |  Create New Profile                  |
+------------------------------------------------------------------+
|                                                                    |
|  Share your robot configuration with the community.                |
|                                                                    |
|  Robot type:     SO-101 (auto-detected)                            |
|  Servo model:    Feetech STS3215 (auto-detected)                  |
|  Controller:     CH340 USB-serial (auto-detected)                  |
|                                                                    |
|  Profile name:   [ so101-standard_________________ ]               |
|  Description:    [ Standard SO-101 with STS3215 servos.            |
|                    Tested with 12V 5A power supply.                |
|                    3D printed parts from Seeed STL files.__ ]      |
|  Author:         [ bradley_________________________ ]               |
|                                                                    |
|  What to include:                                                  |
|    [x] Servo protection settings (overload, temp limits)           |
|    [x] Calibration template (joint ranges and centers)             |
|    [x] Teleop configuration (speed scaling, deadband)              |
|    [x] Diagnostic thresholds (voltage, load, temp)                 |
|    [ ] My specific calibration values (only useful for             |
|        identical physical builds)                                   |
|                                                                    |
|              [ Preview ]    [ Save Locally ]    [ Share ]          |
|                                                                    |
+------------------------------------------------------------------+
```

### Profile Preview

```
+------------------------------------------------------------------+
|  armOS  |  Profile Preview                                         |
+------------------------------------------------------------------+
|                                                                    |
|  # so101-standard                                                  |
|  # Standard SO-101 with STS3215 servos                             |
|                                                                    |
|  robot:                                                            |
|    type: SO-101                                                    |
|    servos: 6                                                       |
|    protocol: feetech_sts                                           |
|                                                                    |
|  protection:                                                       |
|    max_temperature: 65                                             |
|    overload_threshold: 85                                          |
|    voltage_min: 9.0                                                |
|    voltage_max: 13.5                                               |
|                                                                    |
|  calibration_template:                                             |
|    shoulder_pan:   { center: 2048, range: 1024 }                   |
|    shoulder_lift:  { center: 1890, range: 900  }                   |
|    elbow_flex:     { center: 2200, range: 800  }                   |
|    wrist_flex:     { center: 2048, range: 1024 }                   |
|    wrist_roll:     { center: 2048, range: 1024 }                   |
|    gripper:        { center: 1500, range: 800  }                   |
|                                                                    |
|  teleop:                                                           |
|    speed_scale: 0.8                                                |
|    deadband: 5                                                     |
|    loop_hz: 60                                                     |
|                                                                    |
|  (YAML file: 42 lines, 1.2 KB)                                    |
|                                                                    |
|  [ Edit ]    [ Save Locally ]    [ Share to Community ]            |
|                                                                    |
+------------------------------------------------------------------+
```

### Sharing Options

```
+------------------------------------------------------------------+
|  armOS  |  Share Profile                                           |
+------------------------------------------------------------------+
|                                                                    |
|  How do you want to share "so101-standard"?                        |
|                                                                    |
|                                                                    |
|  1. EXPORT FILE                                                    |
|     Save as a .yaml file you can email, post,                      |
|     or upload anywhere.                                            |
|     --> Saves to ~/armos-profiles/so101-standard.yaml              |
|                                                                    |
|                                                                    |
|  2. PUBLISH TO armOS COMMUNITY HUB                                 |
|     Share on hub.armos.dev for anyone to discover                  |
|     and install with one command.                                  |
|     --> Requires a free armos.dev account                          |
|                                                                    |
|                                                                    |
|  3. GENERATE QR CODE                                               |
|     A scannable code that contains the full profile.               |
|     Great for workshops and meetups.                               |
|     --> Works offline, no account needed                           |
|                                                                    |
|                                                                    |
|  4. COPY TO CLIPBOARD                                              |
|     Copy the YAML to paste into Discord, GitHub,                   |
|     or a forum post.                                               |
|                                                                    |
|                                                                    |
|  [ 1 ]  [ 2 ]  [ 3 ]  [ 4 ]                   [ Cancel ]         |
|                                                                    |
+------------------------------------------------------------------+
```

### Community Hub: Browsing Profiles

```
+------------------------------------------------------------------+
|  armOS  |  Community Hub  |  Robot Profiles                        |
+------------------------------------------------------------------+
|                                                                    |
|  Search: [ SO-101________________________ ]  [ Search ]            |
|                                                                    |
|  Filter: [x] SO-101  [ ] Koch  [ ] Aloha  [ ] Custom              |
|  Sort:   [Downloads]  [Recent]  [Rating]                           |
|                                                                    |
|  RESULTS:                                                          |
|                                                                    |
|  +--------------------------------------------------------------+ |
|  | so101-standard                             by: bradley        | |
|  | Standard SO-101 with STS3215 servos. Tested with 12V 5A.     | |
|  | Downloads: 342  |  Rating: 4.8/5  |  Updated: 2027-01-15     | |
|  | [x] Verified by armOS team                                    | |
|  |                        [ Install ]  [ Details ]               | |
|  +--------------------------------------------------------------+ |
|                                                                    |
|  +--------------------------------------------------------------+ |
|  | so101-seeed-pro                            by: seeed_official | |
|  | Official profile for Seeed Studio SO-101 Pro kit.             | |
|  | Downloads: 1,204  |  Rating: 4.9/5  |  Updated: 2027-02-01   | |
|  | [x] Official manufacturer profile                             | |
|  |                        [ Install ]  [ Details ]               | |
|  +--------------------------------------------------------------+ |
|                                                                    |
|  +--------------------------------------------------------------+ |
|  | so101-high-speed                           by: robo_racer     | |
|  | Tuned for maximum teleop speed. Reduced protection margins.   | |
|  | Downloads: 89  |  Rating: 4.2/5  |  Updated: 2026-12-20      | |
|  | [!] Caution: reduced safety margins                           | |
|  |                        [ Install ]  [ Details ]               | |
|  +--------------------------------------------------------------+ |
|                                                                    |
+--[ Page 1 of 3 ]--[ N: Next ]--[ P: Previous ]-------------------+
```

### Installing a Community Profile

```
+------------------------------------------------------------------+
|  armOS  |  Install Profile                                         |
+------------------------------------------------------------------+
|                                                                    |
|  Installing: so101-seeed-pro (by seeed_official)                   |
|                                                                    |
|  This profile will configure:                                      |
|    [x] Servo protection settings                                   |
|    [x] Calibration template                                        |
|    [x] Teleop configuration                                        |
|    [x] Diagnostic thresholds                                       |
|                                                                    |
|  Changes from your current profile:                                |
|                                                                    |
|    protection.overload_threshold:  85 --> 80  (more conservative)  |
|    teleop.speed_scale:             0.8 --> 0.7  (slower)           |
|    teleop.loop_hz:                 60  --> 50   (lower)            |
|    + added: diagnostic.comm_retry: 3   (new setting)               |
|                                                                    |
|  Your current calibration data will NOT be overwritten.            |
|  You may need to re-calibrate if joint ranges changed.             |
|                                                                    |
|  [ Apply ]    [ Apply + Re-calibrate ]    [ Cancel ]              |
|                                                                    |
+------------------------------------------------------------------+
```

### QR Code Sharing (for workshops)

```
+------------------------------------------------------------------+
|  armOS  |  QR Profile Share                                        |
+------------------------------------------------------------------+
|                                                                    |
|  Scan this code to install the "so101-standard" profile:           |
|                                                                    |
|           +---------------------------+                            |
|           |                           |                            |
|           |     [QR CODE IMAGE]       |                            |
|           |                           |                            |
|           |     (contains full YAML   |                            |
|           |      encoded as URL)      |                            |
|           |                           |                            |
|           +---------------------------+                            |
|                                                                    |
|  On the receiving armOS station, run:                              |
|                                                                    |
|    armos profile scan                                              |
|                                                                    |
|  This opens the camera to read the QR code. No internet needed.    |
|                                                                    |
|  Or import from URL:                                               |
|    armos profile install https://hub.armos.dev/p/so101-standard    |
|                                                                    |
|                                                                    |
|  [ Print QR ]    [ Save QR as image ]    [ Done ]                 |
|                                                                    |
+------------------------------------------------------------------+
```

### Profile Sharing Flow Diagram

```
[User has working robot configuration]
    |
    v
[armos profile create]
    |
    +-- Auto-detect: robot type, servos, controller
    |
    +-- User adds: name, description, author
    |
    +-- User selects: what to include
    |
    v
[Profile saved locally as YAML]
    |
    +------- Export file ---------> [.yaml file on disk]
    |                                (email, upload, etc.)
    |
    +------- Publish to hub ------> [hub.armos.dev]
    |                                (searchable, rated,
    |                                 version controlled)
    |
    +------- Generate QR ---------> [QR code on screen]
    |                                (scan with armos
    |                                 profile scan)
    |
    +------- Copy to clipboard ---> [paste into Discord/
                                     GitHub/forum]

[Another user wants this profile]
    |
    +------- From hub ------------> armos profile install so101-standard
    |
    +------- From file -----------> armos profile import ./profile.yaml
    |
    +------- From QR code --------> armos profile scan (uses camera)
    |
    +------- From URL ------------> armos profile install https://...
    |
    v
[Diff shown: current vs new profile]
    |
    v
[User confirms changes]
    |
    v
[Profile applied. Re-calibrate if needed.]
```

---

## Cross-Cutting Design Decisions

### Consistent Screen Layout

Every screen in armOS follows this template:

```
+--[ armOS vX.Y ]--[ Context ]--[ Status ]----------[ Timer ]------+
|                                                                    |
|  CONTENT AREA                                                      |
|  (varies by screen)                                                |
|                                                                    |
|                                                                    |
+--[ Action Keys ]---------------------------------------------------+
```

- **Top bar:** Always shows version, context (what screen/mode), status (connected/disconnected), and a timer when relevant.
- **Bottom bar:** Always shows available keyboard shortcuts for the current screen.
- **Content area:** Never more than one scrolling region. If content overflows, paginate.

### Color Palette (TUI)

| Element | Color | Meaning |
|---------|-------|---------|
| OK / Pass / Connected | Green | Everything is fine |
| Warning / Degraded | Yellow | Needs attention, not urgent |
| Error / Fault / Critical | Red | Immediate action needed |
| Info / Status change | Blue | Informational |
| Active selection / Focus | Cyan | Currently selected item |
| Disabled / Unavailable | Dim gray | Cannot interact |
| User input fields | White on dark | Where to type |
| Marketing / branding | Bold white | Logo, taglines |

All status indicators use BOTH color AND text: `[OK]`, `[WARN]`, `[FAIL]`, `[--]`. No information is conveyed by color alone (accessibility requirement).

### Timing Goals Summary

| Flow | Target | Hard Limit |
|------|--------|------------|
| First boot to teleop | 3 min | 5 min |
| Demo mode: boot to running | 2 min | 3 min |
| Educator: clone 30 USBs | 90 min | 120 min |
| Hackathon: boot to teleop | 6 min | 10 min |
| Unboxing: box open to teleop | 11 min | 15 min |
| Error recovery: fault to resume | 30 sec | 2 min |
| Profile install from hub | 10 sec | 30 sec |

### What We Never Show to Users

1. Python tracebacks
2. Raw systemd output during boot
3. Servo register addresses or hex values
4. File paths longer than needed (use `~` not `/home/username`)
5. Technical jargon without explanation ("sync_read", "EEPROM", "PID")
6. Blank screens with no status or guidance
7. Errors without fix instructions

---

_UX enhancement designs for armOS -- authored by Sally (UX Designer), 2026-03-15._
_These flows implement the vision of "zero to robot in 5 minutes" across every user persona and entry point._
