# UX Review: RobotOS USB

**Reviewer:** Sally (UX Designer)
**Date:** 2026-03-15
**Scope:** Full review of product-brief.md, prd.md, architecture.md, epics.md, sprint-plan.md
**Focus:** Making robotics accessible to non-technical users

---

## Executive Assessment

The planning artifacts describe a technically sound system, but the user experience layer is underspecified. The PRD commits to "zero manual terminal commands" (SC4), yet the TUI is relegated to Sprint 6 (the final sprint), the boot experience has no design, there is no first-run wizard, and the calibration UX assumes users already understand what "homing a joint" means. The current plan risks shipping a powerful tool that only power users can operate.

This review provides concrete UX designs for the gaps identified.

---

## 1. Boot Experience

### Current State in Artifacts

The architecture mentions GRUB with a kernel selection menu and "boot to dashboard within 90 seconds" (NFR5), but there is no design for what the user actually sees between pressing the power button and reaching a usable state.

### Problem

A hobbyist who boots this USB for the first time will see: BIOS splash, GRUB menu with cryptic kernel names, a wall of systemd boot text, and then... what? A bare Ubuntu desktop? The TUI auto-launching? Nothing in the artifacts specifies this.

### Recommendation: Branded Boot Sequence

```
PHASE 1: GRUB (2-3 seconds)
+----------------------------------------------------------+
|                                                          |
|                      RobotOS v0.1                        |
|                                                          |
|   > Start RobotOS                                        |
|     Start RobotOS (Surface Pro kernel)                   |
|     Advanced options                                     |
|                                                          |
|   RobotOS boots automatically in 5 seconds...            |
+----------------------------------------------------------+

PHASE 2: Plymouth splash (during kernel + systemd)
+----------------------------------------------------------+
|                                                          |
|                                                          |
|                                                          |
|                   [ Robot arm icon ]                      |
|                                                          |
|                      RobotOS                             |
|                                                          |
|                   ===----------- 30%                     |
|                                                          |
|            Detecting hardware...                          |
|                                                          |
+----------------------------------------------------------+

PHASE 3: Auto-launch TUI or first-run wizard
```

**Specific recommendations:**

- Ship a Plymouth theme that hides systemd output. Users should never see scrolling boot messages.
- GRUB menu should auto-select the default kernel after 5 seconds. The Surface kernel should be a secondary option, not a question users must answer.
- After boot completes, auto-launch `robotos tui` in a maximized terminal (or the first-run wizard if no calibration data exists).
- Add Story 8.5: "Plymouth boot splash and auto-launch" to Epic 8. Size: S. This is missing from the current plan.

---

## 2. First-Run Experience

### Current State in Artifacts

There is no first-run experience designed. The PRD says "boot to teleop in 5 minutes" but the artifacts assume the user somehow knows to run `robotos tui` or `robotos detect`.

### Recommendation: First-Run Wizard

The system should detect that it is a fresh boot (no calibration data, no saved preferences) and automatically launch a guided setup.

```
SCREEN 1: Welcome
+----------------------------------------------------------+
|                                                          |
|                  Welcome to RobotOS                      |
|                                                          |
|   Let's get your robot set up. This takes about          |
|   3 minutes.                                             |
|                                                          |
|   What you'll need:                                      |
|     [ ] Robot arm(s) connected via USB                   |
|     [ ] Power supply plugged into follower arm           |
|     [ ] (Optional) USB camera                            |
|                                                          |
|   Is everything connected?                               |
|                                                          |
|           [ Yes, let's go ]    [ Skip setup ]            |
|                                                          |
+----------------------------------------------------------+

SCREEN 2: Hardware Detection (automatic)
+----------------------------------------------------------+
|                                                          |
|                  Scanning for hardware...                 |
|                                                          |
|   USB Ports:                                             |
|     /dev/ttyUSB0  Feetech controller  [FOUND]           |
|     /dev/ttyUSB1  Feetech controller  [FOUND]           |
|                                                          |
|   Servo Bus 1: 6 servos detected                         |
|   Servo Bus 2: 6 servos detected                         |
|                                                          |
|   Match: SO-101 (leader + follower pair)                 |
|                                                          |
|   Camera:                                                |
|     /dev/video0   USB 2.0 Camera     [FOUND]            |
|                                                          |
|                          [ Continue ]                    |
|                                                          |
+----------------------------------------------------------+

SCREEN 3: Arm Assignment
+----------------------------------------------------------+
|                                                          |
|               Which arm is which?                        |
|                                                          |
|   Move a joint on the arm you want to use as the         |
|   LEADER (the one you'll control by hand).               |
|                                                          |
|   Listening for movement...                              |
|                                                          |
|     /dev/ttyUSB0:  [ waiting... ]                        |
|     /dev/ttyUSB1:  >>> MOVEMENT DETECTED <<<             |
|                                                          |
|   /dev/ttyUSB1 is your LEADER arm.                       |
|   /dev/ttyUSB0 is your FOLLOWER arm.                     |
|                                                          |
|        [ Correct ]           [ Swap them ]               |
|                                                          |
+----------------------------------------------------------+

SCREEN 4: Calibration (guided, per-joint)
+----------------------------------------------------------+
|                                                          |
|            Calibrating: Follower Arm                     |
|                                                          |
|   Joint 1 of 6: Shoulder Pan                             |
|                                                          |
|   Move this joint to its CENTER position,                |
|   then press Enter.                                      |
|                                                          |
|        +---+                                             |
|        | O-+--->  (rotate to center)                     |
|        +---+                                             |
|                                                          |
|   Current position: 2048                                 |
|   Voltage: 12.1V  Temp: 28C                             |
|                                                          |
|   [ Press Enter when centered ]    [ Skip joint ]        |
|                                                          |
+----------------------------------------------------------+

SCREEN 5: Ready
+----------------------------------------------------------+
|                                                          |
|                    Setup Complete!                        |
|                                                          |
|   Your SO-101 is calibrated and ready.                   |
|                                                          |
|   Quick start:                                           |
|     T  -  Start teleoperation                            |
|     D  -  Run diagnostics                                |
|     R  -  Record training data                           |
|     M  -  Monitor servo health                           |
|                                                          |
|   Press any key to continue to the dashboard.            |
|                                                          |
+----------------------------------------------------------+
```

**Specific recommendations:**

- Auto-detect first run by checking for calibration files in `~/.config/robotos/calibration/`.
- The arm assignment screen (Screen 3) solves a real pain point. Currently users must guess which `/dev/ttyUSB` is which. Listening for servo movement is far more intuitive than asking users to trace USB cables.
- Calibration should show a simple diagram of the joint being calibrated. ASCII art showing the physical motion expected.
- Add Epic 7 Story 7.0: "First-Run Setup Wizard" to the MVP. Size: L. This should run BEFORE the TUI dashboard on first boot.
- The wizard should save a `~/.config/robotos/setup-complete` flag so it only runs once.

---

## 3. TUI Design

### Current State in Artifacts

The architecture shows a single TUI wireframe with a telemetry table and keyboard shortcuts at the bottom. The epics define three stories (shell, telemetry panel, workflow launcher) but no navigation model.

### Problem

The current TUI design tries to show everything on one screen. With 12 servos (leader + follower), camera feeds, diagnostics, and workflow controls, this will be overwhelming on a typical laptop terminal (80x24 or 120x40).

### Recommendation: Tab-Based Navigation with Status Bar

```
MAIN DASHBOARD (default view)
+--[ RobotOS v0.1.0 ]--[ SO-101 ]--[ Connected ]----------+
|                                                           |
| TABS: [1:Dashboard] [2:Teleop] [3:Monitor] [4:Diagnose]  |
|       [5:Record] [6:Settings]                             |
|------------------------------------------------------------
|                                                           |
|  HARDWARE STATUS                                          |
|  +------------------------+  +------------------------+   |
|  | FOLLOWER ARM           |  | LEADER ARM             |   |
|  | Port: /dev/ttyUSB0     |  | Port: /dev/ttyUSB1     |   |
|  | Servos: 6/6 online     |  | Servos: 6/6 online     |   |
|  | Calibrated: YES        |  | Calibrated: YES        |   |
|  | Voltage: 12.1V [OK]    |  | Voltage: 5.0V [USB]    |   |
|  | Max temp: 31C [OK]     |  | Max temp: 27C [OK]     |   |
|  +------------------------+  +------------------------+   |
|                                                           |
|  QUICK ACTIONS                                            |
|  [T] Start Teleop  [D] Run Diagnostics  [R] Record Data  |
|                                                           |
|  ALERTS                                                   |
|  (none)                                                   |
|                                                           |
+---[ ? Help ] [ Q Quit ]----------------------------------+


TELEOP VIEW (Tab 2)
+--[ RobotOS v0.1.0 ]--[ SO-101 ]--[ TELEOP ACTIVE ]------+
|                                                           |
| TABS: [1:Dashboard] [2:Teleop] [3:Monitor] [4:Diagnose]  |
|------------------------------------------------------------
|                                                           |
|  LEADER (read)           -->    FOLLOWER (write)          |
|  shoulder_pan    2048          shoulder_pan    2048       |
|  shoulder_lift   1890          shoulder_lift   1892   +2  |
|  elbow_flex      2200          elbow_flex      2198   -2  |
|  wrist_flex      2048          wrist_flex      2049   +1  |
|  wrist_roll      2048          wrist_roll      2048    0  |
|  gripper         1500          gripper         1500    0  |
|                                                           |
|  HEALTH BAR:                                              |
|  Voltage  [============--------]  11.8V (ok)             |
|  Temp     [====----------------]  31C   (ok)             |
|  Load     [=======--------------]  33%  (ok)             |
|  Comms    [====================]  100%  (ok)             |
|                                                           |
|  Loop rate: 62 Hz | Errors: 0 | Uptime: 00:04:32         |
|                                                           |
+---[ Space: Pause ] [ S: Stop ] [ Q: Back to dashboard ]--+


MONITOR VIEW (Tab 3)
+--[ RobotOS v0.1.0 ]--[ SO-101 ]--[ Monitoring ]----------+
|                                                           |
| TABS: [1:Dashboard] [2:Teleop] [3:Monitor] [4:Diagnose]  |
|------------------------------------------------------------
|                                                           |
|  FOLLOWER ARM                             Refresh: 10 Hz |
|  Joint           Pos    Volt   Load   Temp   Status      |
|  shoulder_pan    2048   12.1V   3.2%   28C   [OK]        |
|  shoulder_lift   1890   12.0V  33.1%   31C   [OK]        |
|  elbow_flex      2200   11.9V  45.0%   33C   [WARN]      |
|  wrist_flex      2048   12.1V   1.2%   27C   [OK]        |
|  wrist_roll      2048   12.1V   0.8%   27C   [OK]        |
|  gripper         1500   12.0V   5.0%   28C   [OK]        |
|                                                           |
|  LEADER ARM                                               |
|  Joint           Pos    Volt   Load   Temp   Status      |
|  shoulder_pan    2048    5.0V   0.1%   26C   [OK]        |
|  (... same layout ...)                                    |
|                                                           |
|  ALERTS                                                   |
|  [WARN] elbow_flex load at 45% (threshold: 50%)          |
|                                                           |
+---[ L: Toggle logging ] [ F: Filter ] [ Q: Back ]--------+


DIAGNOSTICS VIEW (Tab 4)
+--[ RobotOS v0.1.0 ]--[ SO-101 ]--[ Diagnostics ]---------+
|                                                           |
| TABS: [1:Dashboard] [2:Teleop] [3:Monitor] [4:Diagnose]  |
|------------------------------------------------------------
|                                                           |
|  DIAGNOSTIC RESULTS              Last run: 12 sec ago    |
|                                                           |
|  [PASS]  Port Detection          USB ports accessible     |
|  [PASS]  Servo Ping              12/12 servos responding  |
|  [PASS]  Firmware Version        All >= 3.10              |
|  [WARN]  Power Health            Follower 11.8V (min 12V) |
|  [PASS]  Status Register         No error flags           |
|  [PASS]  EEPROM Config           Settings match profile   |
|  [PASS]  Comms Reliability       99.8% (200 cycles)       |
|  [PASS]  Torque Stress           99.5% (200 cycles)       |
|  [PASS]  Cross-Bus Teleop        100% (500 cycles)        |
|  [PASS]  Motor Isolation         All servos reliable      |
|  [PASS]  Calibration Valid       Both arms calibrated     |
|                                                           |
|  > [WARN] Power Health: Follower voltage at 11.8V.       |
|    Expected: 12V. Your power supply may be slightly       |
|    undersized. If you see stuttering during teleop,       |
|    upgrade to a 12V 5A (60W) power supply.                |
|                                                           |
+---[ R: Re-run ] [ E: Export JSON ] [ Q: Back ]------------+
```

**Navigation model:**

```
Number keys 1-6 switch tabs (always available)
Letter shortcuts within each tab for actions
Q always goes back/up one level
? always shows context-sensitive help
Escape cancels any active operation
```

**Specific recommendations:**

- Use Textual's `TabbedContent` widget for tab switching. Number keys 1-6 as accelerators.
- The status bar at the top should always show: version, profile name, and connection state. Color-code the connection state: green = connected, yellow = degraded, red = disconnected.
- The bottom bar should always show available keyboard shortcuts for the current context.
- Keep the dashboard (Tab 1) as a summary view. Detailed data lives in dedicated tabs.
- Alert notifications should appear as a toast/popup that auto-dismisses after 5 seconds, with a persistent alert log in the dashboard.

---

## 4. CLI UX

### Current State in Artifacts

The architecture defines these commands:
```
robotos detect, status, calibrate, teleop, record,
diagnose, monitor, exercise, config show, config edit,
profile list, profile create, serve
```

### Assessment

The command names are mostly good. Some issues:

| Issue | Problem | Recommendation |
|-------|---------|----------------|
| `detect` vs `status` | Overlapping. Both show hardware state. Users will not know which to run. | Merge into `robotos status`. Auto-detect on every status call. Add `--rescan` flag for forced re-enumeration. |
| `config show` / `config edit` | "config" is vague. Config of what? Profile? System preferences? | Rename to `robotos settings` for user preferences. Profile editing stays under `robotos profile edit`. |
| `exercise` | Not intuitive. "Exercise" does not communicate "move joints to test mechanics." | Rename to `robotos test-joints` or `robotos self-test`. |
| `serve` | Fine for developers. Meaningless to hobbyists. | Rename to `robotos web` with a clear description: "Start the web dashboard." |
| No `robotos help` narrative | `--help` shows flags. It does not teach workflow. | Add `robotos quickstart` that prints a step-by-step getting started guide. |

### Recommended Command Hierarchy

```
robotos                     # No args = launch TUI (not show help)
robotos status              # Show hardware, profile, calibration state
robotos calibrate           # Guided calibration wizard
robotos teleop              # Start teleoperation
robotos record              # Record training data
robotos diagnose            # Run diagnostic suite
robotos monitor             # Live telemetry stream
robotos self-test           # Exercise joints to verify mechanics
robotos profile list        # List available profiles
robotos profile show        # Show active profile details
robotos settings            # Show/edit user preferences
robotos web                 # Start web dashboard
robotos quickstart          # Print getting-started guide
robotos version             # Print version
```

**Key change:** Running `robotos` with no arguments should launch the TUI, not print help text. This is the "zero terminal commands" path. Users who boot the system and see a terminal just type `robotos` and get the full GUI experience.

---

## 5. Error Messages

### Current State in Artifacts

The PRD requires "actionable error messages with suggested fixes" (FR36) and "error messages include cause + remediation" (NFR12). Good requirements. But the artifacts provide no error message style guide or examples beyond the PRD's user journey UJ2.

### Recommendation: Error Message Framework

Every error message should follow this template:

```
[SEVERITY] WHAT HAPPENED
  WHY: probable cause in plain English
  FIX: specific action the user can take
  HELP: link or command for more info
```

### Error Catalog (key scenarios)

```
[ERROR] Follower arm not responding
  WHY:  No servos detected on /dev/ttyUSB0. The USB cable may be
        disconnected or the servo controller may not have power.
  FIX:  1. Check that the USB cable is firmly connected
        2. Check that the power supply is plugged in and switched on
        3. Try a different USB port
  HELP: robotos diagnose --port /dev/ttyUSB0

[WARNING] Voltage drop detected on follower arm
  WHY:  Voltage dropped to 6.8V (minimum safe: 7.0V). This usually
        means the power supply cannot deliver enough current when
        multiple servos move at once.
  FIX:  Upgrade to a 12V 5A (60W) power supply. The included 12V 2A
        supply is not sufficient for the SO-101 follower arm.
  HELP: robotos diagnose --check power

[ERROR] Servo 3 (elbow_flex) overload protection tripped
  WHY:  The servo shut itself down to prevent damage. This happens
        when the arm hits an obstacle or a joint is mechanically stuck.
  FIX:  1. Check for physical obstructions near the elbow joint
        2. Power-cycle the follower arm (unplug and replug power)
        3. If this keeps happening, the servo may need replacement
  HELP: robotos diagnose --check servo --id 3

[ERROR] Calibration data is stale
  WHY:  Servo positions have drifted more than 20% from calibrated
        values. This can happen if servos were physically moved or
        replaced since the last calibration.
  FIX:  Run calibration again: robotos calibrate
  HELP: robotos diagnose --check calibration

[WARNING] Serial port grabbed by brltty
  WHY:  The brltty service (Braille display driver) has claimed
        /dev/ttyUSB0, preventing RobotOS from communicating with
        your servo controller. This is a known Ubuntu issue.
  FIX:  RobotOS will disable brltty now. This is safe unless you
        use a Braille display. Allow? [Y/n]
  HELP: https://github.com/robotos/robotos/wiki/brltty
```

**Specific recommendations:**

- Never show raw Python tracebacks to end users. Catch all exceptions at the CLI boundary and translate to the template above.
- Use color: red for ERROR, yellow for WARNING, green for OK/PASS.
- In the TUI, errors should appear as modal dialogs that the user must acknowledge (not buried in a log).
- Add a `robotos logs` command that shows the full technical log for when users need to file bug reports or share with the AI assistant.

---

## 6. Calibration UX

### Current State in Artifacts

Story 6.1 specifies "Interactive Calibration Command" but the acceptance criteria describe a CLI-driven process without specifying the interaction model. The current LeRobot calibration requires users to manually move joints and press Enter in a terminal, with no visual feedback about what position is expected.

### Problem

Calibration is the single most confusing step for beginners. The term "homing" means nothing to someone who just unpacked a robot kit. Users do not know:
- What a "center position" looks like physically
- How far to move each joint
- Whether they moved it to the right place
- What happens if they get it wrong

### Recommendation: Visual Guided Calibration

```
CALIBRATION FLOW

Step 1: Explain what we're doing
+----------------------------------------------------------+
|                                                          |
|                Calibrating Follower Arm                   |
|                                                          |
|   Calibration teaches RobotOS where each joint's          |
|   center and limits are. You'll move each joint to        |
|   a specific position and press Enter.                    |
|                                                          |
|   This takes about 2 minutes.                             |
|                                                          |
|   TIP: Hold the arm gently. Don't force any joint.        |
|                                                          |
|                     [ Start ]                             |
|                                                          |
+----------------------------------------------------------+

Step 2: Per-joint calibration (repeat for each joint)
+----------------------------------------------------------+
|                                                          |
|   Joint 1 of 6: Shoulder Pan        [==----] 17%        |
|                                                          |
|   Move this joint to point STRAIGHT FORWARD.              |
|                                                          |
|         Top view:                                         |
|              |                                            |
|         +---------+                                       |
|         |  base   |                                       |
|         +---------+                                       |
|              |                                            |
|              v  <-- arm should point this way              |
|                                                          |
|   Live position: 2048  (target range: 1900-2100)          |
|   [|||||||||||||||.....] <-- position indicator            |
|                                                          |
|   Status: GOOD - position is within expected range        |
|                                                          |
|   [ Enter: Confirm ]  [ S: Skip ]  [ ?: Help ]           |
|                                                          |
+----------------------------------------------------------+

Step 3: Verification
+----------------------------------------------------------+
|                                                          |
|             Calibration Complete!                         |
|                                                          |
|   Joint             Center    Range     Status            |
|   shoulder_pan      2048      1024      [OK]             |
|   shoulder_lift     1890      900       [OK]             |
|   elbow_flex        2200      800       [OK]             |
|   wrist_flex        2048      1024      [OK]             |
|   wrist_roll        2048      1024      [OK]             |
|   gripper           1500      800       [OK]             |
|                                                          |
|   Calibration saved to:                                   |
|   ~/.config/robotos/calibration/so101-CH340-SN12345/      |
|                                                          |
|   [ Test it: press T for teleop ]  [ Done ]               |
|                                                          |
+----------------------------------------------------------+
```

**Specific recommendations:**

- Show a visual diagram for every joint. Even crude ASCII art of "which way to point this thing" eliminates guesswork.
- Show a live position indicator that updates in real-time as the user moves the joint. Color it green when the position is within the expected range.
- Show a progress bar (joint 1 of 6) so users know how long this will take.
- After calibration, offer an immediate test: "Press T to try teleoperation and verify your calibration works."
- Store a calibration timestamp and show "Last calibrated: 2 hours ago" in the dashboard to reassure users that their calibration is still valid.
- If calibration validation (Story 3.4) detects drift, show a specific message: "Your shoulder_pan has drifted. Recalibrate? [Y/n]" rather than a generic warning.

---

## 7. Status Indicators and Health Dashboard

### Problem

The architecture defines detailed telemetry data (voltage, current, load, temperature per servo) but there is no design for how to present this to someone who does not know what "12.1V" means or whether "33% load" is good or bad.

### Recommendation: Traffic Light Health Model

Present health as a simple three-state system with drill-down for experts:

```
BEGINNER VIEW (default)
+-----------------------------------+
|  Robot Health:  ALL GOOD           |
|                                    |
|  Follower arm:  [GREEN CIRCLE]     |
|  Leader arm:    [GREEN CIRCLE]     |
|  Camera:        [GREEN CIRCLE]     |
|  Power:         [GREEN CIRCLE]     |
+-----------------------------------+

WHEN SOMETHING IS WRONG:
+-----------------------------------+
|  Robot Health:  NEEDS ATTENTION    |
|                                    |
|  Follower arm:  [YELLOW CIRCLE]    |
|    > Power supply voltage is low   |
|    > Press Enter for details       |
|  Leader arm:    [GREEN CIRCLE]     |
|  Camera:        [GREEN CIRCLE]     |
+-----------------------------------+

EXPERT VIEW (press E to toggle)
+-----------------------------------+
|  Follower arm: /dev/ttyUSB0       |
|  Joint           V     Load  Temp |
|  shoulder_pan   12.1V   3%   28C  |
|  shoulder_lift  12.0V  33%   31C  |
|  elbow_flex     11.9V  45%   33C  |
|  wrist_flex     12.1V   1%   27C  |
|  wrist_roll     12.1V   1%   27C  |
|  gripper        12.0V   5%   28C  |
+-----------------------------------+
```

**Specific recommendations:**

- Default to the "traffic light" view. Three colors: green (healthy), yellow (warning), red (fault).
- Each yellow/red indicator must have a plain-English explanation immediately visible (not behind a click).
- Expert view is one keypress away (E for Expert / B for Basic toggle).
- Thresholds for color coding should come from the profile YAML (they are already defined as protection settings). Map them to display thresholds: green = 0-70% of limit, yellow = 70-90%, red = 90%+.

---

## 8. Progressive Disclosure

### Problem

The system must serve both a hobbyist who wants to teleop their first robot and a researcher who needs to tune PID coefficients and inspect EEPROM registers. The current plan puts everything at the same level.

### Recommendation: Three-Tier Interface

```
TIER 1: SIMPLE (default)
  - TUI dashboard with traffic light health
  - One-key actions: T=Teleop, D=Diagnose, R=Record
  - Calibration wizard with visual guides
  - Error messages with specific fix instructions

TIER 2: INTERMEDIATE (opt-in via menus)
  - Full telemetry table with numeric values
  - Diagnostic detail view with per-check results
  - Teleop parameters (speed scaling, deadband)
  - CSV log export
  - Profile viewer

TIER 3: EXPERT (CLI + config files)
  - robotos diagnose --json for scripting
  - Direct YAML profile editing
  - robotos monitor --hz 50 for high-rate telemetry
  - robotos config for tuning protection thresholds
  - Raw register read/write via robotos hal commands (future)
```

**Implementation:** The TUI defaults to Tier 1. A "Mode: [Simple] / Detailed / Expert" toggle in the settings tab (or a persistent setting in config.yaml) switches the display density. The CLI always provides the full Tier 3 interface.

---

## 9. Notification Patterns

### Current State in Artifacts

Story 5.3 defines "Fault Detection and Alert System" but there is no design for how alerts are presented across the different UI layers.

### Recommendation: Multi-Channel Alert System

```
SEVERITY LEVELS AND RESPONSE:

CRITICAL (red) - Requires immediate action, blocks operation
  Examples: servo overload trip, bus disconnection, voltage below safe minimum
  TUI: Modal dialog, blocks input until acknowledged
  CLI: Print to stderr, exit with error code
  Audio: Three short beeps (if speaker available)

WARNING (yellow) - Degraded operation, monitor closely
  Examples: voltage sag under load, temperature rising, calibration drift
  TUI: Toast notification (auto-dismiss 10s), persists in alert log
  CLI: Print warning, continue operation
  Audio: Single beep

INFO (blue) - Status change, no action needed
  Examples: device connected, calibration loaded, teleop started
  TUI: Brief status bar flash
  CLI: Print to stdout

ALERT DISPLAY IN TUI:

+----------------------------------------------------------+
|  [!] WARNING: Voltage dropped to 11.2V on follower arm   |
|      Power supply may be undersized. See diagnostics.     |
|                            [ Dismiss ]  [ Diagnose ]      |
+----------------------------------------------------------+
```

**Specific recommendations:**

- Critical alerts during teleop should auto-stop the follower arm (FR17 already requires this). The alert should explain WHY it stopped: "Teleoperation paused: elbow_flex overloaded. The arm has been safely stopped."
- Never show alerts as just a color change in a table cell. Users will miss it. Use a popup/toast for warnings and a modal for critical.
- Provide an alert history (`robotos logs --alerts`) so users can review what happened during a session.
- Consider a physical feedback option: if the servo controller supports it, flash an LED pattern on fault. (Out of scope for MVP but worth noting for Growth.)

---

## 10. Accessibility

### Current State in Artifacts

NFR13 requires "operable via keyboard, mouse, or touchscreen." This is a start but does not address users with limited mobility, which is directly relevant for a robotics tool (many robotics researchers have physical disabilities).

### Recommendations

| Concern | Recommendation |
|---------|----------------|
| Keyboard-only operation | Already planned (TUI is keyboard-first). Ensure all TUI actions are reachable without mouse. Document all keyboard shortcuts on a help screen (? key). |
| High contrast | Textual supports themes. Ship a high-contrast theme as an option: `robotos tui --theme high-contrast` or setting in config.yaml. |
| Screen reader | Textual has limited screen reader support today. For the web dashboard (Growth phase), ensure semantic HTML and ARIA labels. Flag this as a Growth accessibility story. |
| Font size | Allow configurable font size in the TUI settings. Textual's CSS system supports this. |
| Motor impairment | Avoid requiring rapid or precise input during calibration. All prompts should wait indefinitely for user input. Never time out a user interaction. |
| Color blindness | Do not rely solely on color to convey status. Use symbols alongside colors: [OK], [!!], [XX] in addition to green/yellow/red. The current architecture wireframe uses "ok" text alongside color, which is good. Standardize this pattern. |

**Specific recommendation for MVP:** Add a line to the Textual TUI acceptance criteria (Story 7.1): "Status indicators use both color AND text symbols (OK/WARN/FAIL) so that no information is conveyed by color alone."

---

## 11. Setup Wizard for Classroom/Fleet Deployment

### Current State in Artifacts

User Journey UJ5 (Classroom Setup) describes cloning USB images, but there is no UX design for how the teacher configures the "master" image.

### Recommendation: Export/Clone Wizard (Growth Phase)

```
CLONE WORKFLOW:

robotos export-config
+----------------------------------------------------------+
|                                                          |
|              Export Configuration                         |
|                                                          |
|   This will create a configuration bundle containing:     |
|     [x] SO-101 profile                                   |
|     [x] Calibration data (follower + leader)             |
|     [x] User preferences                                 |
|     [ ] Recorded datasets (523 MB)                       |
|                                                          |
|   Export to: ~/robotos-config-2026-03-15.tar.gz           |
|                                                          |
|                [ Export ]    [ Cancel ]                    |
|                                                          |
+----------------------------------------------------------+
```

This is Growth scope (Story 10.5) but the UX should be designed now to influence the config storage format in MVP.

---

## 12. Web Dashboard Layout (Vision Phase)

### Current State in Artifacts

The architecture specifies FastAPI + htmx but provides no layout design.

### Recommendation: Information Density Guidelines

The web dashboard serves a different use case than the TUI: it is for remote monitoring, multi-robot setups, and persistent display (e.g., a tablet mounted near the robot). Design for glanceability.

```
WEB DASHBOARD LAYOUT:

+--[ RobotOS ]---------+--[ SO-101 | Connected ]----------+
|                       |                                   |
|  ROBOT STATUS         |  LIVE TELEMETRY                   |
|                       |                                   |
|  Health: [GREEN]      |  Follower Arm                     |
|                       |  +----+----+----+----+----+----+  |
|  Follower: OK         |  | J1 | J2 | J3 | J4 | J5 | J6|  |
|  Leader:   OK         |  | ok | ok |WARN| ok | ok | ok |  |
|  Camera:   OK         |  +----+----+----+----+----+----+  |
|  Power:    OK         |                                   |
|                       |  Leader Arm                       |
|  QUICK ACTIONS        |  +----+----+----+----+----+----+  |
|                       |  | J1 | J2 | J3 | J4 | J5 | J6|  |
|  [Teleop]             |  | ok | ok | ok | ok | ok | ok |  |
|  [Calibrate]          |  +----+----+----+----+----+----+  |
|  [Diagnose]           |                                   |
|  [Record]             |  CAMERA FEED                      |
|                       |  +-----------------------------+  |
|  RECENT ALERTS        |  |                             |  |
|  (none)               |  |     [ live video feed ]     |  |
|                       |  |                             |  |
|  SESSION              |  +-----------------------------+  |
|  Uptime: 01:23:45     |                                   |
|  Episodes: 12/50      |  CHARTS (expandable)              |
|  Disk free: 8.2 GB    |  [Voltage over time]              |
|                       |  [Temperature over time]          |
+-----------------------+-----------------------------------+
```

**Design principles for the web UI:**

- Left sidebar: status and actions (always visible, 25% width).
- Main area: telemetry and feeds (75% width).
- Mobile-responsive: on narrow screens, stack sidebar above main content.
- No auto-refresh via polling. Use WebSocket for real-time updates (already in the architecture).
- Dark theme by default (robotics labs are often dimly lit).
- Large click targets for touch operation on tablets.

---

## 13. Flow Diagram: Complete User Journey

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
                    | (branded, 60-80s)|
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
              | (screens 1-5) |  | (main view)     |
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

## 14. Summary of Recommended Changes

### New Stories to Add to MVP

| Story | Epic | Size | Rationale |
|-------|------|------|-----------|
| 7.0: First-Run Setup Wizard | 7 | L | Without this, the "5-minute boot to teleop" goal (SC1) is impossible for non-technical users. The wizard IS the product for first-time users. |
| 8.5: Plymouth Boot Splash and Auto-Launch | 8 | S | Professional boot experience. Hides Linux complexity. |
| 7.x: Accessibility baseline (color-blind safe indicators, keyboard shortcut help screen) | 7 | S | Minimal cost, significant impact for inclusive design. |

### Changes to Existing Stories

| Story | Change |
|-------|--------|
| 7.1 (TUI Shell) | Add tab-based navigation model. Add "Mode" toggle for simple/detailed/expert views. Add: "Running `robotos` with no arguments launches the TUI." |
| 7.2 (Telemetry Panel) | Add traffic-light summary view as default, with numeric table as drill-down. Require both color AND text symbols for all status indicators. |
| 7.3 (Workflow Launcher) | Add toast/modal notification system for alerts during workflows. |
| 5.3 (Fault Detection) | Define alert severity levels (critical/warning/info) and display behavior for each UI layer. |
| 6.1 (Calibration) | Add per-joint ASCII diagrams and live position indicator. Add progress bar showing joint N of 6. |
| 6.4 (Hardware Detection) | Rename from `detect` to `status`. Add arm-identification-by-movement feature for the wizard. |
| 1.2 (CLI Structure) | Rename `exercise` to `self-test`. Rename `serve` to `web`. Add `quickstart` command. Running bare `robotos` should launch TUI, not print help. |

### Architecture Amendments

| Component | Recommendation |
|-----------|----------------|
| Error framework | Define a structured error type with severity/what/why/fix fields. All CLI and TUI errors must use this format. Add to architecture Section 10 as a pattern. |
| Boot sequence | Add Plymouth theme configuration to the ISO build spec (Section 3). Add auto-launch of TUI or wizard as a systemd user service. |
| Profile schema | Add display thresholds (green/yellow/red ranges) to the profile YAML so that UI health indicators are profile-aware, not hardcoded. |

### Sprint Impact

The new stories add approximately 6-8 weight points to Sprint 6. Given that Sprint 6 is already the heaviest sprint (33 points), the recommended 6a/6b split becomes mandatory:

- **Sprint 6a:** TUI (7.0, 7.1, 7.2, 7.3) + data collection (9.2, 9.3)
- **Sprint 6b:** USB image (8.1, 8.2, 8.3, 8.4, 8.5) + AI context (9.1)

The first-run wizard (7.0) should be built alongside the TUI shell (7.1) since they share the Textual application framework.

---

## 15. Key UX Principles for RobotOS

1. **Show, don't tell.** A diagram of which way to point a joint is worth a thousand words of documentation.
2. **Never show a blank screen.** If hardware is not detected, explain what to connect and how. If an operation fails, explain what went wrong and how to fix it.
3. **Respect the user's time.** Auto-detect everything possible. Never ask a question the system can answer itself (which port is which, what profile to use, etc.).
4. **Safe defaults.** Teleop should auto-stop on faults. Protection settings should be pre-configured. The user should have to opt IN to dangerous operations, not opt OUT.
5. **Two-keypress rule.** Any primary action (teleop, calibrate, diagnose, record) should be reachable in two keypresses or fewer from the main dashboard.
6. **Graceful degradation over hard failure.** If one servo drops, keep the others running and tell the user which one failed. Do not crash the entire session.
7. **Accessibility is not optional.** Color-blind users, keyboard-only users, and users with limited mobility are part of the target audience. Design for them from day one.

---

_UX review for RobotOS USB -- authored by Sally (UX Designer)._
