---
project: armOS Citizenry v2.0
date: 2026-03-15
status: approved
---

# UX Design — armOS Citizenry v2.0 Dashboard

## Overview

The v1.5 ANSI TUI dashboard gets 4 new sections for v2.0 data. Same rendering approach: raw ANSI escape codes, 2Hz refresh, box-drawing characters. No web UI — terminal only.

## Dashboard Layout

```
╔══════════════════════════════════════════════════════════════════════╗
║ armOS CITIZENRY DASHBOARD  3 citizens                               ║
║ Governor: surface-governor [a1b2c3d4]  192.168.1.80  const:ok       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ CITIZEN            TYPE          STATE     HEALTH  LAST SEEN  ADDR   ║
║ ────────────────── ───────────── ───────── ──────── ─────────── ──── ║
║ pi-follower        manipulator   teleop    95%     0.3s ago   .85   ║
║                    [e5f6g7h8]                                        ║
║   caps: 6dof_arm, gripper, feetech_sts3215                          ║
║   skills: basic_movement(3) basic_grasp(2) pick_and_place(1)        ║
║                                                                      ║
║ camera-sense       sensor        idle      100%    0.1s ago   .80   ║
║                    [i9j0k1l2]                                        ║
║   caps: video_stream, frame_capture, color_detection                 ║
║   skills: frame_capture(1) color_detection(1)                        ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║ TASKS (2 active)                                                     ║
║ ────────────────── ───────────── ───────── ──────────────────────── ║
║ [abc123] pick_place  EXECUTING    pi-follower   prio:0.7  3 bids   ║
║ [def456] frame_cap   BIDDING      (auction)     prio:0.5  0 bids   ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║ CONTRACTS (1 active)                                                 ║
║ camera-sense ←→ pi-follower: visual_pick_and_place  health:ok       ║
║                                                                      ║
║ COMPOSITE CAPABILITIES                                               ║
║ visual_pick_and_place  color_sorting  visual_inspection              ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║ TELEOP                                                               ║
║ Status: STREAMING  FPS: 29.8  Frames: 4521  Drops: 0%              ║
║ Leader: surface-governor -> Follower: pi-follower                    ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║ TELEMETRY (pi-follower)                                              ║
║ Motor              Voltage  Current   Load    Temp   Status         ║
║ shoulder_pan         7.2V     32mA     8%    32°C   OK              ║
║ shoulder_lift        7.1V    156mA    42%    38°C   OK              ║
║ elbow_flex           7.2V     89mA    28%    35°C   OK              ║
║ wrist_flex           7.2V     12mA     3%    31°C   OK              ║
║ wrist_roll           7.2V      8mA     2%    30°C   OK              ║
║ gripper              7.2V     45mA    15%    33°C   OK              ║
║                                                                      ║
║ WARNINGS: (none)                                                     ║
║ IMMUNE: 4 patterns  |  last triggered: voltage_collapse 2h ago      ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║ MESSAGES (last 10)                                                   ║
║ 14:32:01 HEARTBEAT pi-follower health=0.95 state=teleop            ║
║ 14:32:00 ACCEPT    pi-follower -> pick_and_place                    ║
║ 14:31:59 PROPOSE   pick_and_place -> broadcast                      ║
║ 14:31:58 HEARTBEAT camera-sense health=1.0 state=idle              ║
╚══════════════════════════════════════════════════════════════════════╝
```

## New Sections

### TASKS Section
- Shows active tasks: id (truncated), type, status, assigned citizen, priority, bid count
- Color coding: BIDDING=yellow, EXECUTING=green, FAILED=red
- Completed tasks auto-remove after 10s

### CONTRACTS Section
- Shows active symbiosis contracts: provider ←→ consumer: composite capability
- Health status: ok (green), degraded (yellow), broken (red)
- Below: list of all discovered composite capabilities

### Citizen Skill Display
- Added below capabilities in the neighbor table
- Format: `skill_name(level)` — only shows unlocked skills
- Color: green for level 3+, default for level 1-2

### Immune Memory Line
- Shows total pattern count
- Shows last triggered pattern and how long ago
- Appears below the warnings line

### Warning Display (Enhanced)
- Severity colors: INFO=dim, WARNING=yellow, CRITICAL=red, EMERGENCY=red+bold+blinking
- Shows source citizen and affected motor
- Auto-decays (fades out) after 60s

## CLI Entry Points

### Surface (Governor + Camera)
```bash
# Run governor with integrated dashboard
python -m citizenry.run_surface --leader-port /dev/ttyACM1

# Run camera citizen (separate process on same machine)
python -m citizenry.run_camera --camera 0

# Run both together (future: single process)
```

### Pi (Follower)
```bash
# Unchanged from v1.5
python -m citizenry.run_pi --follower-port /dev/ttyACM0
```

### Deploy
```bash
# Unchanged from v1.5
./citizenry/deploy.sh --start
```
