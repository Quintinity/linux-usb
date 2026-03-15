# armOS UX Design Document

**Author:** Consolidated from UX review, UX enhancements, community growth strategy, PRD enhancements, and content strategy
**Date:** 2026-03-15
**Status:** Comprehensive UX specification for armOS v0.1 through v1.0
**Sources:** review-ux.md, ux-enhancements.md, frontier-community-growth.md, prd-enhancements.md, strategy-content-enhancements.md

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Information Architecture](#2-information-architecture)
3. [Screen Layout Template](#3-screen-layout-template)
4. [Color Palette and Accessibility](#4-color-palette-and-accessibility)
5. [Critical Flow 1: First Boot Experience](#5-critical-flow-1-first-boot-experience)
6. [Critical Flow 2: Demo Mode](#6-critical-flow-2-demo-mode)
7. [Critical Flow 3: Educator Flow](#7-critical-flow-3-educator-flow)
8. [Critical Flow 4: Hackathon Flow](#8-critical-flow-4-hackathon-flow)
9. [Critical Flow 5: Unboxing Flow](#9-critical-flow-5-unboxing-flow)
10. [Critical Flow 6: Error Recovery Flow](#10-critical-flow-6-error-recovery-flow)
11. [Critical Flow 7: Profile Sharing Flow](#11-critical-flow-7-profile-sharing-flow)
12. [Error Message Framework](#12-error-message-framework)
13. [Notification Patterns](#13-notification-patterns)
14. [Achievement and Gamification System](#14-achievement-and-gamification-system)
15. [CLI Command Naming and Discoverability](#15-cli-command-naming-and-discoverability)
16. [Timing Goals](#16-timing-goals)

---

## 1. Design Principles

These principles govern every screen, message, and interaction in armOS. When in doubt, apply these in priority order.

### P1: Zero to Robot in 5 Minutes

The core promise. Every design decision is measured against the question: "Does this get the user from power button to moving robot faster or slower?" If a feature adds time to first teleop, it must justify itself with a proportional safety or comprehension benefit.

### P2: Explain, Don't Error

No error is a dead end. Every failure state must include:
- **WHAT** happened (in plain English, not technical jargon)
- **WHY** it probably happened (the most likely cause)
- **FIX** steps (specific, numbered, actionable)
- **HELP** link (a command or URL for deeper investigation)

Never show raw Python tracebacks, hex register values, or unexplained file paths to end users.

### P3: Progressive Disclosure

The system serves hobbyists, educators, and researchers. Present complexity in three tiers:

| Tier | Audience | What They See |
|------|----------|---------------|
| **Simple** (default) | Hobbyist, student, first-timer | Traffic light health, one-key actions, visual calibration guides, plain-English errors |
| **Intermediate** (opt-in via menus) | Experienced user, educator | Full telemetry tables, diagnostic details, teleop parameters, CSV export, profile viewer |
| **Expert** (CLI + config files) | Researcher, contributor | JSON output for scripting, YAML profile editing, high-rate telemetry, raw register access |

The TUI defaults to Tier 1. A persistent "Mode" toggle in settings switches display density. The CLI always provides Tier 3.

### P4: Show, Don't Tell

A diagram of which way to point a joint is worth a thousand words of documentation. Use ASCII art for calibration, cable diagrams for error recovery, and live position indicators for real-time feedback.

### P5: Respect the User's Time

Auto-detect everything possible. Never ask a question the system can answer itself: which port is which, what profile to use, whether the power supply is adequate. If the system can figure it out, do it silently and confirm the result.

### P6: Safe Defaults

Teleop auto-stops on faults. Protection settings are pre-configured. The user must opt IN to dangerous operations, not opt OUT. Conservative servo limits ship by default; power users relax them deliberately.

### P7: Two-Keypress Rule

Any primary action (teleop, calibrate, diagnose, record) must be reachable in two keypresses or fewer from the main dashboard.

### P8: Graceful Degradation Over Hard Failure

If one servo drops, keep the others running and tell the user which one failed. Do not crash the entire session. Offer "Skip servo, continue with 5" when a non-critical component is lost.

### P9: Accessibility Is Not Optional

Color-blind users, keyboard-only users, and users with limited mobility are part of the target audience. Design for them from day one. No information is conveyed by color alone.

---

## 2. Information Architecture

### 2.1 TUI Tab Structure

The TUI uses tab-based navigation with a persistent status bar. Number keys 1-6 switch tabs from any screen.

```
+--[ armOS v0.1.0 ]--[ SO-101 ]--[ Connected ]------------------+
|                                                                  |
| TABS: [1:Dashboard] [2:Teleop] [3:Monitor] [4:Diagnose]        |
|       [5:Record] [6:Settings]                                    |
|------------------------------------------------------------------
|                                                                  |
|  (Tab content area)                                              |
|                                                                  |
+--[ ? Help ] [ Q Quit ]------------------------------------------+
```

**Tab Descriptions:**

| Tab | Key | Purpose | Primary Actions |
|-----|-----|---------|-----------------|
| Dashboard | 1 | Hardware status overview, quick actions, alerts | T=Teleop, D=Diagnose, R=Record |
| Teleop | 2 | Leader/follower position mirror, health bars, loop stats | Space=Pause, R=Record, S=Stop |
| Monitor | 3 | Per-servo telemetry table (position, voltage, load, temp) | L=Toggle logging, F=Filter |
| Diagnose | 4 | Diagnostic suite results, per-check pass/warn/fail | R=Re-run, E=Export JSON |
| Record | 5 | Data collection controls, episode count, dataset stats | Space=Start/Stop, U=Upload |
| Settings | 6 | User preferences, mode toggle, profile management | Enter=Edit, R=Reset defaults |

### 2.2 CLI Command Map

```
armos                        # No args = launch TUI (not help)
armos status                 # Hardware, profile, calibration state
armos calibrate              # Guided calibration wizard
armos teleop                 # Start teleoperation
armos record                 # Record training data
armos diagnose               # Run diagnostic suite
armos monitor                # Live telemetry stream
armos self-test              # Exercise joints to verify mechanics
armos demo                   # Launch demo mode
armos profile list           # List available profiles
armos profile show           # Show active profile details
armos profile create         # Create new profile from current config
armos profile install <name> # Install community profile
armos profile import <file>  # Import profile from file
armos profile export <file>  # Export current profile
armos profile scan           # Scan QR code to import profile
armos settings               # Show/edit user preferences
armos web                    # Start web dashboard
armos quickstart             # Print getting-started guide
armos logs                   # Show full technical log
armos logs --alerts          # Show alert history
armos version                # Print version
armos educator create-class  # Educator: create classroom config
armos educator dashboard     # Educator: launch fleet dashboard
```

**Key naming decisions:**
- Running `armos` with no arguments launches the TUI. This is the "zero terminal commands" path.
- `detect` merged into `status` -- auto-detect on every call, `--rescan` flag for forced re-enumeration.
- `exercise` renamed to `self-test` -- communicates "test mechanics" to non-experts.
- `serve` renamed to `web` -- clear description for hobbyists.
- `config` renamed to `settings` for user preferences. Profile editing stays under `armos profile`.

### 2.3 Screen Navigation Flow

```
                    +------------------+
                    |   Insert USB,    |
                    |   boot from USB  |
                    +--------+---------+
                             |
                    +--------v---------+
                    | GRUB (auto-boot  |
                    |   in 5 seconds)  |
                    +--------+---------+
                             |
                    +--------v---------+
                    | Plymouth splash  |
                    | (branded, 30-60s)|
                    +--------+---------+
                             |
                    +--------v---------+
                    | First run?       |
                    +--+------------+--+
                       |            |
                      YES          NO
                       |            |
              +--------v------+  +--v--------------+
              | Setup Wizard  |  | TUI Dashboard   |
              | (screens 1-8) |  | (main view)     |
              +--------+------+  +--+-----------+--+
                       |            |           |
                       +------+-----+           |
                              |                 |
                     +--------v--------+        |
                     | Dashboard with  |        |
                     | hardware status |        |
                     +---+---+---+----+        |
                         |   |   |              |
                   +-----+   |   +------+       |
                   |         |          |       |
             +-----v--+ +---v----+ +---v----+  |
             | Teleop | | Record | |Diagnose|  |
             +-----+--+ +---+----+ +---+----+  |
                   |         |          |       |
                   +----+----+----+-----+       |
                        |              |        |
                   +----v----+    +----v----+   |
                   | Success |    | Error   |   |
                   +---------+    | Dialog  |   |
                                  | (fix    |   |
                                  |  steps) |   |
                                  +----+----+   |
                                       |        |
                                       +--------+
                                    (back to dashboard)
```

---

## 3. Screen Layout Template

Every screen in armOS follows this consistent template:

```
+--[ armOS vX.Y ]--[ Context ]--[ Status ]----------[ Timer ]------+
|                                                                    |
|  CONTENT AREA                                                      |
|  (varies by screen)                                                |
|                                                                    |
|                                                                    |
+--[ Action Keys ]---------------------------------------------------+
```

**Rules:**
- **Top bar:** Always shows version, context (current screen/mode), connection status (color-coded), and a timer when relevant (teleop uptime, calibration duration, etc.).
- **Bottom bar:** Always shows available keyboard shortcuts for the current screen. Shortcuts change with context.
- **Content area:** Never more than one scrolling region per screen. If content overflows, paginate with N/P keys.
- **Navigation:** Number keys 1-6 switch tabs (always available). Q goes back/up one level. ? shows context-sensitive help. Escape cancels any active operation.

---

## 4. Color Palette and Accessibility

### 4.1 TUI Color Palette

| Element | Color | Hex | Meaning |
|---------|-------|-----|---------|
| OK / Pass / Connected | Green | #00FF00 | Everything is fine |
| Warning / Degraded | Yellow | #FFFF00 | Needs attention, not urgent |
| Error / Fault / Critical | Red | #FF0000 | Immediate action needed |
| Info / Status change | Blue | #0088FF | Informational |
| Active selection / Focus | Cyan | #00FFFF | Currently selected item |
| Disabled / Unavailable | Dim gray | #666666 | Cannot interact |
| User input fields | White on dark | #FFFFFF | Where to type |
| Marketing / branding | Bold white | #FFFFFF | Logo, taglines |

### 4.2 Status Indicator Standard

All status indicators use BOTH color AND text symbols. No information is conveyed by color alone.

| State | Symbol | Color | Example |
|-------|--------|-------|---------|
| Healthy | `[OK]` | Green | `Voltage: 12.1V [OK]` |
| Warning | `[WARN]` or `[!!]` | Yellow | `Voltage: 10.8V [!! LOW]` |
| Fault | `[FAIL]` or `[XX]` | Red | `Servo 3: [FAIL] Overload` |
| Offline | `[--]` | Dim gray | `Camera: [--] Not connected` |
| Checking | `[..]` | Blue | `Wi-Fi: [..] scanning...` |

### 4.3 Health Display Model

**Default view (Simple tier):** Traffic light model.

```
+-----------------------------------+
|  Robot Health:  ALL GOOD           |
|                                    |
|  Follower arm:  [OK]              |
|  Leader arm:    [OK]              |
|  Camera:        [OK]              |
|  Power:         [OK]              |
+-----------------------------------+
```

**When degraded:**

```
+-----------------------------------+
|  Robot Health:  NEEDS ATTENTION    |
|                                    |
|  Follower arm:  [!! LOW VOLTAGE]  |
|    > Power supply voltage is low   |
|    > Press Enter for details       |
|  Leader arm:    [OK]              |
|  Camera:        [OK]              |
+-----------------------------------+
```

**Expert view (press E to toggle):** Full telemetry table with numeric values per servo.

### 4.4 Accessibility Requirements

| Concern | Requirement |
|---------|-------------|
| Color blindness | All status uses color + text symbol. Never color alone. |
| Keyboard-only | All actions reachable without mouse. All shortcuts on help screen (? key). |
| High contrast | Ship a `--theme high-contrast` option. Setting persists in config.yaml. |
| Screen reader | Growth phase: semantic HTML + ARIA labels for web dashboard. |
| Font size | Configurable in TUI settings. Textual CSS supports this. |
| Motor impairment | All prompts wait indefinitely. Never time out user input. |
| Thresholds | Green = 0-70% of limit, Yellow = 70-90%, Red = 90%+. Derived from profile YAML. |

---

## 5. Critical Flow 1: First Boot Experience

**Goal:** From BIOS to moving a robot arm in under 5 minutes. Every second of dead air or confusion is a user lost.

### Timing Budget

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
- Surface Pro kernel is a separate option (linux-surface patches can cause issues on non-Surface hardware).
- "Boot from local disk" lets users exit to their installed OS without removing the USB. Critical for trust.

### Screen 2: Plymouth Splash (30-60 seconds)

```
+------------------------------------------------------------------+
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
+------------------------------------------------------------------+
```

**Design decisions:**
- Custom Plymouth theme hides all systemd output. Users must never see scrolling boot text.
- Progress bar advances based on systemd target completion (not a fake timer).
- Status text cycles through real stages: "Loading kernel modules..." / "Detecting hardware..." / "Starting services..." / "Almost ready..."
- Dark background, white text. Minimal. Professional.

### Screen 3: Hardware Detection Splash (5-10 seconds)

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
- Still the Plymouth splash, but in the final seconds it shows detected hardware. Builds confidence immediately.
- If NO hardware is found: "No robot hardware detected. Connect your robot arm and we'll find it." Guidance, not an error.

### Screen 4: Welcome (First-Run Wizard)

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
|         [ Yes, let's go ]         [ Skip setup ]                   |
|                                                                    |
+------------------------------------------------------------------+
```

**Design decisions:**
- Pre-fills checkboxes with detection results. The "it just works" moment.
- Power supply gets [?] because voltage cannot be confirmed until servos are queried.
- "Skip setup" goes to the raw TUI dashboard for power users. No gates.

### Screen 5: Arm Identification (Wiggle Test)

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
- Solves the #1 setup confusion: "which ttyUSB is which?" Instead of tracing cables, listen for physical movement.
- Implementation: poll `Present_Position` on both buses at ~10Hz. First bus showing position change > 50 ticks is identified.
- Single-arm setups skip this screen entirely.

### Screen 6: Power Check

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
|  Leader arm (/dev/ttyUSB1):                                        |
|                                                                    |
|    Voltage:  5.0V  [====----------------]  [USB POWERED]           |
|                                                                    |
|    This is normal. The leader arm runs on USB bus power.            |
|                                                                    |
|                        [ Continue ]                                 |
|                                                                    |
+------------------------------------------------------------------+
```

If voltage is low (alternate view):

```
+------------------------------------------------------------------+
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
- Check voltage BEFORE calibration to warn early. Bad power causes servo jitter during calibration.
- Never block on a warning. "Continue anyway" always works (user might be using 7.4V LiPo intentionally).

### Screen 7: Calibration (per-joint)

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

Subsequent joints show different ASCII diagrams:

- **Shoulder lift:** Side view, arrow pointing up
- **Elbow flex:** Side view showing bend angle
- **Wrist flex/roll:** Front view of wrist orientation
- **Gripper:** Front view showing open/close positions (2-step: record open, then close)

**Design decisions:**
- One joint at a time. Never show all 6 at once.
- ASCII art for every joint. Even crude art is 10x better than "move to center position."
- Live position indicator updates at 10Hz. Color-coded: green in range, yellow close, white far.
- Progress bar (1/6, 2/6...) sets expectations.

### Screen 8: Calibration Complete

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
|  Ready to try it? Move the leader arm and the follower             |
|  will copy your movements in real time.                            |
|                                                                    |
|     [ T: Start Teleop! ]      [ D: Go to Dashboard ]              |
|                                                                    |
+------------------------------------------------------------------+
```

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

### First Boot Flow Diagram

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

## 6. Critical Flow 2: Demo Mode

**Goal:** Trade show booth, YouTube recording, or classroom demonstration. The robot does something impressive with zero setup, zero explanation, and zero risk of failure.

**Entry:** `armos demo` from CLI, or a GRUB boot-time option.

### GRUB Entry

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

### Demo Splash (5 seconds)

```
+------------------------------------------------------------------+
|                                                                    |
|                         a r m O S                                  |
|                                                                    |
|               Boot from USB. Detect hardware.                      |
|                     Start building.                                |
|                                                                    |
|             Detected: SO-101 (leader + follower)                   |
|                                                                    |
|                 Starting demo in 5...4...3...                       |
|                                                                    |
+------------------------------------------------------------------+
```

### Demo Running (interactive teleop)

```
+------------------------------------------------------------------+
|  armOS DEMO  |  SO-101  |  Move the leader arm!       00:02:15    |
+==================================================================+
|                                                                    |
|  +---------------------------+  +------------------------------+   |
|  |    LEADER                 |  |    FOLLOWER                  |   |
|  |    shoulder_pan    2048   |  |    shoulder_pan    2048      |   |
|  |    shoulder_lift   1923   |  |    shoulder_lift   1925      |   |
|  |    elbow_flex      2100   |  |    elbow_flex      2098      |   |
|  |    wrist_flex      2048   |  |    wrist_flex      2049      |   |
|  |    wrist_roll      2048   |  |    wrist_roll      2048      |   |
|  |    gripper         1500   |  |    gripper         1500      |   |
|  +---------------------------+  +------------------------------+   |
|                                                                    |
|  [====================================] Voltage: 12.1V  Temp: 29C |
|                                                                    |
|  Move the leader arm and the follower copies your movements!       |
|  This is how you collect training data for robot AI.               |
|                                                                    |
+--[ This laptop booted from a USB stick in under 2 minutes ]-------+
```

### Auto-Routine (unattended booth loop)

```
+------------------------------------------------------------------+
|  armOS DEMO  |  SO-101  |  Auto-Routine: Pick & Place  00:00:15   |
+==================================================================+
|                                                                    |
|  The follower arm is running a pre-trained AI policy.              |
|  No human is controlling it right now.                             |
|                                                                    |
|  +------------------------------------------------------------+   |
|  |                    [ Camera Feed ]                           |   |
|  |              Live view from USB camera                       |   |
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

| Feature | Why |
|---------|-----|
| Auto-calibration from last run | No setup delay at booth |
| Auto-start teleop 5s after boot | Passersby walk up and move the arm |
| Auto-routine loop | Runs unattended during breaks |
| Big text mode (1.5x font) | Readable from 3 meters at a booth |
| QR code on screen | Visitor scans to learn more |
| Marketing tagline rotation | Every screenshot is marketing material |
| Crash recovery watchdog | Must never show an error at a trade show |
| Kiosk lock (ignores Ctrl+C) | Prevents passersby from exiting |

### Demo Configuration

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

### Demo Mode Flow

```
Power button (or power cycle)
    |
    v
[GRUB: Demo Mode] --auto 3s--> [Plymouth] --> [Hardware detect]
    |                                               |
    v                                               v
[Load pre-stored calibration]              [Skip wizard]
    |                                               |
    +-----------------------+-----------------------+
                            |
                    +-------+-------+
                    |               |
               Has policy?     No policy
                    |               |
                    v               v
          [Auto-routine loop]  [Teleop mode]
          (unattended, loops)  (interactive)
                    |               |
                    +-------+-------+
                            |
                    [Crash watchdog]
                    (restart in 5s)
```

---

## 7. Critical Flow 3: Educator Flow

**Goal:** A teacher sets up 30 identical robot arms for a classroom. Bulk configuration, central monitoring, no per-station debugging.

**Timing goal:** 30 arms configured and tested in under 2 hours (4 min per arm, done in parallel batches).

### Step 1: Create Master Configuration

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
|    ...                       ...                                   |
|    Station 15:  PIN 5638     Station 30:  PIN 2764                 |
|                                                                    |
|  [ Print PIN list ]    [ Export CSV ]    [ Next: USB Cloning ]     |
|                                                                    |
+------------------------------------------------------------------+
```

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

### Student Login Screen

```
+------------------------------------------------------------------+
|                                                                    |
|                         a r m O S                                  |
|                                                                    |
|              Robotics 101 -- Spring 2027                           |
|              Station 03                                            |
|                                                                    |
|              Enter your PIN:  [ ____ ]                             |
|                                                                    |
|              (Ask your teacher if you don't have a PIN)            |
|                                                                    |
+------------------------------------------------------------------+
```

### Student Dashboard (after login)

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
    +---> Select: which settings to lock
    +---> Clone: USB drives in batches of 4-8
    |
    v
[Distribute USBs to stations]
    |
    v
[Students boot, enter PIN]  -----(mDNS)----->  [Teacher dashboard]
    |                                            [30-station grid]
    v                                            [alerts, progress]
[Students calibrate, complete lab checklist]
```

---

## 8. Critical Flow 4: Hackathon Flow

**Goal:** Participant receives USB stick at check-in. First teleop in under 10 minutes. First data collection in under 20 minutes.

**Context:** The LeRobot hackathon had 3,000 participants across 100+ cities. That is the target event.

### Quick Start Card (physical, 4x6 inches)

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
+----------------------------------------------------+
```

### Hackathon Boot Screen

```
+------------------------------------------------------------------+
|                                                                    |
|                         a r m O S                                  |
|                                                                    |
|            LeRobot Hackathon -- San Francisco                      |
|                   March 2027                                       |
|                                                                    |
|             Detected: SO-101 (leader + follower)                   |
|             Camera: USB 2.0 Camera                                 |
|                                                                    |
|             Welcome! Follow the wizard to get started.              |
|                                                                    |
+------------------------------------------------------------------+
```

### Abbreviated Hackathon Wizard (3 steps only)

**Step 1:** Wiggle test (arm identification)
**Step 2:** Quick calibration (same per-joint flow, faster pacing)
**Step 3:** Ready screen with schedule

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

### Hackathon Leaderboard (projected on wall)

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

---

## 9. Critical Flow 5: Unboxing Flow

**Goal:** Customer buys a Seeed Studio SO-101 kit with armOS USB bundled. The entire experience from opening the box to moving the robot is designed.

### Quick Start Guide (printed in the box)

**Side 1: Setup steps**

```
+------------------------------------------------------------------+
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
|  - Insert the armOS USB stick                                      |
|  - Restart your laptop                                             |
|  - Press F12 (or F2 or DEL) during startup for boot menu           |
|  - Select the armOS USB drive                                      |
|                                                                    |
|  STEP 3: FOLLOW THE WIZARD                                         |
|  - armOS will detect your hardware automatically                   |
|  - Follow the on-screen calibration guide                          |
|  - Move the leader arm -- the follower copies!                     |
|                                                                    |
|  Need help? Scan the QR code -->   [QR: armos.dev/help]           |
+------------------------------------------------------------------+
```

**Side 2: Boot keys and troubleshooting**

```
+------------------------------------------------------------------+
|  BOOT MENU KEYS BY MANUFACTURER                                   |
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
|  "Arm not detected"                                                |
|    --> Try a different USB port. Check cable connection.            |
|  "Follower arm doesn't move"                                      |
|    --> Check 12V power supply is plugged in and switched on.       |
|  "Servos make clicking sounds"                                     |
|    --> Power supply may be too weak. Use the included 12V 5A.     |
|                                                                    |
|  Full documentation: armos.dev/docs                                |
|  Community Discord: armos.dev/discord                              |
+------------------------------------------------------------------+
```

### First-Time Boot Detection (co-branded)

```
+------------------------------------------------------------------+
|                                                                    |
|                    Welcome to armOS!                                |
|          Powered by armOS -- Seeed Studio SO-101 Edition           |
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
+------------------------------------------------------------------+
```

### Unboxing Timeline

```
Minute 0:    Open box
Minute 1:    Identify parts (quick start guide helps)
Minute 2:    Connect follower arm USB + power supply
             Connect leader arm USB
Minute 3:    Insert armOS USB, restart laptop
Minute 4:    GRUB menu appears, auto-boots
Minute 5:    Plymouth splash, hardware detected
Minute 6:    First-run wizard starts
Minute 7:    Arm identification (wiggle test)
Minute 8:    Power check passes
Minute 10:   Calibration complete (6 joints x 2 arms)
Minute 11:   TELEOP RUNNING -- ROBOT MOVES!
```

---

## 10. Critical Flow 6: Error Recovery Flow

**Goal:** When something goes wrong, armOS diagnoses the problem, explains it in plain English, and guides the user to a fix. No error is a dead end.

### Error Severity Model

```
CRITICAL  ----  Robot stopped. Immediate action needed.
                Red background. Modal dialog. Audio beep (3x).
                User must acknowledge before continuing.

WARNING   ----  Robot still works, but something is degraded.
                Yellow banner. Toast notification (10s auto-dismiss).
                Actionable advice shown.

INFO      ----  Status change. No action needed.
                Brief flash in status bar. Logged only.
```

### Scenario 1: Power Supply Too Weak

Detection: Voltage reads below 11.0V on follower arm during teleop.

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
+------------------------------------------------------------------+
```

**Voltage decision tree:**

```
Voltage reading
    |
    +-- > 11.5V ---------> [OK] no action
    |
    +-- 11.0V - 11.5V ---> [WARN] toast: "Voltage slightly low."
    |
    +-- 9.0V - 11.0V ----> [WARN] modal: "Low voltage. Teleop may stutter."
    |
    +-- 7.0V - 9.0V -----> [CRITICAL] auto-stop teleop.
    |
    +-- < 7.0V -----------> [CRITICAL] disable all motor commands.
```

### Scenario 2: Servo Overload

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
+------------------------------------------------------------------+
```

### Scenario 3: Cable Loose / Servo Disconnected

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
|  is the most likely culprit. Push the connector firmly into        |
|  both ends. You should hear a click.                               |
|                                                                    |
|  [ R: Retry detection ]   [ S: Skip servo, continue with 5 ]     |
+------------------------------------------------------------------+
```

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
|       (Check both the laptop end and the arm end)                  |
|    2. Did the USB hub lose power?                                  |
|    3. Was the arm bumped? USB-C connectors can jiggle loose.       |
|                                                                    |
|  armOS is watching for the arm to reconnect...                     |
|                                                                    |
|  [ Waiting... will auto-resume when detected ]                     |
|  (or press Q to quit to dashboard)                                 |
+------------------------------------------------------------------+
```

After reconnection:

```
+------------------------------------------------------------------+
|                                                                    |
|  [OK] ARM RECONNECTED                                              |
|                                                                    |
|  Quick health check:                                               |
|    Servos: 6/6 responding    [OK]                                  |
|    Voltage: 12.1V            [OK]                                  |
|    Calibration: still valid  [OK]                                  |
|                                                                    |
|  [ T: Resume teleop ]    [ D: Run full diagnostics first ]        |
+------------------------------------------------------------------+
```

### Scenario 5: brltty Conflict

```
+------------------------------------------------------------------+
|                                                                    |
|  [INFO] Serial Port Configuration                                  |
|                                                                    |
|  armOS detected that brltty (a Braille display driver) is          |
|  running. This service sometimes claims USB serial ports           |
|  needed for robot communication.                                   |
|                                                                    |
|  On armOS, brltty has been disabled by default.                    |
|                                                                    |
|  If you use a Braille display, re-enable it in                     |
|  Settings > System > Accessibility.                                |
|                                                                    |
|  No action needed. This is already handled.                        |
|                                                                    |
|                        [ OK ]                                      |
+------------------------------------------------------------------+
```

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
    |              [Resume operation]  [Escalate: armos diagnose]
    |                                       |
    |                                  [Full system check]
    |                                       |
    |                                  [Detailed report]
    |
    +-- WARNING ----------> [Toast notification (10s)]
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

## 11. Critical Flow 7: Profile Sharing Flow

**Goal:** A user calibrates a robot, tunes settings, and shares the configuration so others with the same hardware can skip setup. Think Docker Hub for robot configurations.

### Creating a Profile

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
|                    Tested with 12V 5A power supply.__ ]            |
|  Author:         [ bradley_________________________ ]               |
|                                                                    |
|  What to include:                                                  |
|    [x] Servo protection settings (overload, temp limits)           |
|    [x] Calibration template (joint ranges and centers)             |
|    [x] Teleop configuration (speed scaling, deadband)              |
|    [x] Diagnostic thresholds (voltage, load, temp)                 |
|    [ ] My specific calibration values                              |
|                                                                    |
|              [ Preview ]    [ Save Locally ]    [ Share ]          |
+------------------------------------------------------------------+
```

### Profile Preview

```
+------------------------------------------------------------------+
|  armOS  |  Profile Preview                                         |
+------------------------------------------------------------------+
|                                                                    |
|  # so101-standard                                                  |
|  robot:                                                            |
|    type: SO-101                                                    |
|    servos: 6                                                       |
|    protocol: feetech_sts                                           |
|  protection:                                                       |
|    max_temperature: 65                                             |
|    overload_threshold: 85                                          |
|    voltage_min: 9.0                                                |
|    voltage_max: 13.5                                               |
|  calibration_template:                                             |
|    shoulder_pan:   { center: 2048, range: 1024 }                   |
|    shoulder_lift:  { center: 1890, range: 900  }                   |
|    elbow_flex:     { center: 2200, range: 800  }                   |
|    wrist_flex:     { center: 2048, range: 1024 }                   |
|    wrist_roll:     { center: 2048, range: 1024 }                   |
|    gripper:        { center: 1500, range: 800  }                   |
|  teleop:                                                           |
|    speed_scale: 0.8                                                |
|    deadband: 5                                                     |
|    loop_hz: 60                                                     |
|                                                                    |
|  (YAML file: 42 lines, 1.2 KB)                                    |
|                                                                    |
|  [ Edit ]    [ Save Locally ]    [ Share to Community ]            |
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
|  1. EXPORT FILE                                                    |
|     Save as .yaml to email, post, or upload.                       |
|     --> ~/armos-profiles/so101-standard.yaml                       |
|                                                                    |
|  2. PUBLISH TO armOS COMMUNITY HUB                                 |
|     Share on hub.armos.dev for anyone to discover.                 |
|     --> Requires a free armos.dev account                          |
|                                                                    |
|  3. GENERATE QR CODE                                               |
|     Scannable code with full profile. Works offline.               |
|     Great for workshops and meetups.                               |
|                                                                    |
|  4. COPY TO CLIPBOARD                                              |
|     Paste into Discord, GitHub, or a forum post.                   |
|                                                                    |
|  [ 1 ]  [ 2 ]  [ 3 ]  [ 4 ]                   [ Cancel ]         |
+------------------------------------------------------------------+
```

### Community Hub: Browsing Profiles

```
+------------------------------------------------------------------+
|  armOS  |  Community Hub  |  Robot Profiles                        |
+------------------------------------------------------------------+
|                                                                    |
|  Search: [ SO-101________________________ ]  [ Search ]            |
|  Filter: [x] SO-101  [ ] Koch  [ ] Aloha  [ ] Custom              |
|  Sort:   [Downloads]  [Recent]  [Rating]                           |
|                                                                    |
|  +--------------------------------------------------------------+ |
|  | so101-standard                             by: bradley        | |
|  | Standard SO-101 with STS3215 servos.                          | |
|  | Downloads: 342  |  Rating: 4.8/5  |  Updated: 2027-01-15     | |
|  | [x] Verified by armOS team                                    | |
|  |                        [ Install ]  [ Details ]               | |
|  +--------------------------------------------------------------+ |
|                                                                    |
|  +--------------------------------------------------------------+ |
|  | so101-seeed-pro                            by: seeed_official | |
|  | Official profile for Seeed Studio SO-101 Pro kit.             | |
|  | Downloads: 1,204  |  Rating: 4.9/5                           | |
|  | [x] Official manufacturer profile                             | |
|  |                        [ Install ]  [ Details ]               | |
|  +--------------------------------------------------------------+ |
|                                                                    |
+--[ Page 1 of 3 ]--[ N: Next ]--[ P: Previous ]-------------------+
```

### Installing a Profile (diff view)

```
+------------------------------------------------------------------+
|  armOS  |  Install Profile                                         |
+------------------------------------------------------------------+
|                                                                    |
|  Installing: so101-seeed-pro (by seeed_official)                   |
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
    +-- User adds: name, description, author
    +-- User selects: what to include
    |
    v
[Profile saved locally as YAML]
    |
    +------- Export file ---------> [.yaml on disk]
    +------- Publish to hub ------> [hub.armos.dev]
    +------- Generate QR ---------> [QR code on screen]
    +------- Copy clipboard ------> [paste anywhere]

[Another user wants this profile]
    |
    +------- From hub ------------> armos profile install so101-standard
    +------- From file -----------> armos profile import ./profile.yaml
    +------- From QR code --------> armos profile scan (uses camera)
    +------- From URL ------------> armos profile install https://...
    |
    v
[Diff shown: current vs new] --> [User confirms] --> [Applied]
```

---

## 12. Error Message Framework

### Template

Every user-facing error follows this structure:

```
[SEVERITY] WHAT HAPPENED
  WHY:  Probable cause in plain English
  FIX:  Specific action the user can take (numbered steps)
  HELP: Command or link for more info
```

### Error Catalog

```
[ERROR] Follower arm not responding
  WHY:  No servos detected on /dev/ttyUSB0. The USB cable may be
        disconnected or the servo controller may not have power.
  FIX:  1. Check that the USB cable is firmly connected
        2. Check that the power supply is plugged in and switched on
        3. Try a different USB port
  HELP: armos diagnose --port /dev/ttyUSB0

[WARNING] Voltage drop detected on follower arm
  WHY:  Voltage dropped to 6.8V (minimum safe: 7.0V). This usually
        means the power supply cannot deliver enough current when
        multiple servos move at once.
  FIX:  Upgrade to a 12V 5A (60W) power supply. The included 12V 2A
        supply is not sufficient for the SO-101 follower arm.
  HELP: armos diagnose --check power

[ERROR] Servo 3 (elbow_flex) overload protection tripped
  WHY:  The servo shut itself down to prevent damage. This happens
        when the arm hits an obstacle or a joint is mechanically stuck.
  FIX:  1. Check for physical obstructions near the elbow joint
        2. Power-cycle the follower arm (unplug and replug power)
        3. If this keeps happening, the servo may need replacement
  HELP: armos diagnose --check servo --id 3

[ERROR] Calibration data is stale
  WHY:  Servo positions have drifted more than 20% from calibrated
        values. This can happen if servos were physically moved or
        replaced since the last calibration.
  FIX:  Run calibration again: armos calibrate
  HELP: armos diagnose --check calibration

[WARNING] Serial port grabbed by brltty
  WHY:  The brltty service (Braille display driver) has claimed
        /dev/ttyUSB0, preventing armOS from communicating with
        your servo controller. This is a known Ubuntu issue.
  FIX:  armOS will disable brltty now. This is safe unless you
        use a Braille display. Allow? [Y/n]
  HELP: armos.dev/docs/troubleshooting/brltty
```

### Rules

1. Never show raw Python tracebacks to end users. Catch all exceptions at the CLI boundary.
2. Use color: red for ERROR, yellow for WARNING, green for OK/PASS.
3. In the TUI, errors appear as modal dialogs that must be acknowledged (not buried in logs).
4. `armos logs` shows the full technical log for bug reports or AI assistant debugging.
5. Use `~` not `/home/username` in displayed paths.
6. Never show servo register addresses, hex values, or "sync_read" without explanation.

---

## 13. Notification Patterns

### Severity Levels and Response Behavior

| Severity | TUI Behavior | CLI Behavior | Audio |
|----------|-------------|-------------|-------|
| **CRITICAL** (red) | Modal dialog, blocks input until acknowledged | Print to stderr, exit with error code | Three short beeps |
| **WARNING** (yellow) | Toast notification, auto-dismiss 10s, persists in alert log | Print warning, continue operation | Single beep |
| **INFO** (blue) | Brief status bar flash | Print to stdout | None |

### Toast Notification Layout

```
+----------------------------------------------------------+
|  [!] WARNING: Voltage dropped to 11.2V on follower arm   |
|      Power supply may be undersized. See diagnostics.     |
|                            [ Dismiss ]  [ Diagnose ]      |
+----------------------------------------------------------+
```

### Rules

- Critical alerts during teleop auto-stop the follower arm. The alert explains WHY it stopped.
- Never show alerts as just a color change in a table cell. Use popups/toasts for warnings and modals for critical.
- Alert history available via `armos logs --alerts`.
- Alerts during data recording automatically annotate the episode with the fault condition.

---

## 14. Achievement and Gamification System

### Design Philosophy

Achievements are structured onboarding progression, not a gimmick. They answer "what should I do next?" for new users. Opt-in and invisible by default for experienced users who find them patronizing.

### Achievement Table

| Achievement | Trigger | Why It Matters |
|---|---|---|
| **First Boot** | Boot armOS for the first time | Confirms the USB works |
| **Hardware Detected** | Auto-detect completes successfully | Confirms the robot is connected |
| **Calibrated** | Complete calibration for both arms | The first real milestone |
| **First Teleop** | Run teleop for 30+ seconds | The "it works!" moment |
| **Smooth Operator** | 60 seconds of teleop with zero communication errors | Validates hardware reliability |
| **Data Collector** | Record 10+ demonstration episodes | Enters the ML pipeline |
| **Diagnostician** | Run the full diagnostic suite | Learns the diagnostic tools |
| **Contributor** | Submit a robot profile or bug report | Community participation |
| **Fleet Commander** | Connect 2+ arms simultaneously | Advanced use case |

### Display

- Show achievements as a sidebar in the TUI dashboard (opt-in via Settings > Gamification).
- Unlocked achievements show in green with timestamp.
- Locked achievements show dimmed with a hint about what triggers them.
- Progress toward partial achievements shows a bar (e.g., "Data Collector: 7/10 episodes").

### Leaderboard (Optional, Opt-In)

Track anonymized metrics: total teleop hours, episodes collected, unique robot profiles tested. Display on armos.dev/community. Creates friendly competition and makes the community feel alive.

### Clip Capture Integration

Build clip capture directly into teleop for viral sharing:

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

**Implementation:**
- Continuous 60-second ring buffer using ffmpeg. Press [C] saves last 15 seconds. Zero cost until clip requested.
- Subtle watermark: "Built with armOS | armos.dev" in bottom-right corner.
- Format options: 720p MP4 vertical (TikTok/Reels) or horizontal (YouTube/X).
- Metadata: robot type, servo count, armOS version embedded in MP4.

### Priority

- Achievements: Sprint 7+ (Growth phase)
- Clip capture: Sprint 5-6 (Launch phase)

---

## 15. CLI Command Naming and Discoverability

### Naming Principles

| Principle | Example |
|-----------|---------|
| Verb-first for actions | `armos calibrate`, not `armos calibration` |
| Noun-first for resources | `armos profile list`, not `armos list-profiles` |
| No abbreviations in command names | `armos diagnose`, not `armos diag` |
| Common aliases accepted | `armos teleop` and `armos tele` both work |
| No arguments = interactive mode | `armos` launches TUI, `armos calibrate` launches wizard |

### Discoverability Features

1. **`armos quickstart`** -- Prints a step-by-step getting started guide (not flags and options, but a workflow narrative).

2. **`armos` with no args launches TUI** -- The "zero terminal commands" path. Users who see a terminal just type `armos` and get the full GUI.

3. **Context-sensitive help** -- `?` key in any TUI screen shows help for that specific screen.

4. **Command suggestions** -- Misspelled commands show "Did you mean...?" suggestions.

5. **Workflow hints** -- After completing an action, suggest the next logical step:
   - After `armos calibrate`: "Calibration complete. Try `armos teleop` to test it."
   - After `armos diagnose`: "All checks passed. Ready for `armos teleop` or `armos record`."

### What We Never Show to Users

1. Python tracebacks
2. Raw systemd output during boot
3. Servo register addresses or hex values
4. File paths longer than needed (use `~` not `/home/username`)
5. Technical jargon without explanation ("sync_read", "EEPROM", "PID")
6. Blank screens with no status or guidance
7. Errors without fix instructions

---

## 16. Timing Goals

### Summary Table (All Flows)

| Flow | Target | Hard Limit | Phase |
|------|--------|------------|-------|
| **First boot to teleop** | 3 min | 5 min | MVP |
| **Demo mode: boot to running** | 2 min | 3 min | MVP |
| **Educator: clone 30 USBs** | 90 min | 120 min | Growth |
| **Hackathon: boot to teleop** | 6 min | 10 min | MVP |
| **Hackathon: boot to first recording** | 10 min | 15 min | MVP |
| **Hackathon: 50 episodes collected** | 2 hours | 3 hours | Growth |
| **Hackathon: policy trained (cloud)** | +30 min | +60 min | Growth |
| **Unboxing: box open to teleop** | 11 min | 15 min | MVP |
| **Error recovery: fault to resume** | 30 sec | 2 min | MVP |
| **Profile install from hub** | 10 sec | 30 sec | Growth |
| **Returning boot (not first run)** | 90 sec | 120 sec | MVP |
| **Calibration (both arms)** | 3 min | 5 min | MVP |

### First Boot Timing Breakdown

| Phase | Target | Max |
|-------|--------|-----|
| GRUB menu | 0s (auto-select) | 5s |
| Kernel + systemd boot | 30s | 60s |
| Plymouth splash | During boot | During boot |
| Desktop + TUI auto-launch | 5s | 10s |
| First-run wizard | 120s | 180s |
| First teleop movement | 180s | 300s |

### Hackathon Timing Breakdown

| Milestone | Target | Hard Limit |
|-----------|--------|------------|
| USB inserted to GRUB | 0s (auto) | 30s |
| Boot complete | 90s | 120s |
| Wizard complete | 5 min | 8 min |
| First teleop movement | 6 min | 10 min |
| First recorded episode | 10 min | 15 min |

### How to Measure

- Boot time: measured from GRUB selection to TUI render (systemd-analyze)
- Wizard time: measured from wizard launch to `setup-complete` flag written
- Teleop time: measured from wizard completion to first position write confirmed
- All timings tracked via opt-in telemetry (FR55-FR57) for fleet-wide analysis

---

*Consolidated UX design document for armOS. Sources: review-ux.md, ux-enhancements.md, frontier-community-growth.md, prd-enhancements.md, strategy-content-enhancements.md. Authored 2026-03-15.*
