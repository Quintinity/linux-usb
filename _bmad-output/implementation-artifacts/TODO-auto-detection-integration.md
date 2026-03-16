---
status: todo
priority: high
created: 2026-03-16
---

# TODO: Wire Auto-Detection into Live Citizen Runtime

## Problem
When a new USB device is plugged into the Pi, nothing happens automatically.
The user must manually start a new citizen process. The `armos/detection/`
module exists (USBMonitor, CitizenFactory, device_db) but isn't wired into
the running citizenry.

## Additional Issue Found
The governor auto-proposes teleop to the first arm it discovers, which locks
that arm into "busy" state. When a second arm joins, it can't receive tasks
because the governor already committed to teleop with arm-1. Need a smarter
governor that pauses teleop when marketplace tasks arrive.

## What Needs to Happen

### 1. Pi-side auto-detection daemon
- Background thread/task in the Pi citizen process watches for USB hotplug
- New servo controller → scan motors → match profile → spawn new citizen
- New camera → spawn CameraCitizen
- Hot-unplug → citizen broadcasts will and stops

### 2. Governor teleop management
- Don't auto-propose teleop on first arm discovery
- Only start teleop when explicitly requested ("start teleop")
- Or: pause teleop when marketplace tasks arrive (already partially done)
- Or: teleop is just another marketplace task that can be preempted

### 3. Multi-arm governor awareness
- Governor should track which arms are available vs busy
- Tasks should be routed to idle arms, not busy-in-teleop arms
- The marketplace already handles this (busy arms reject bids) but the
  teleop lock prevents arms from ever becoming idle

## Files to Modify
- `citizenry/run_pi.py` — add auto-detection loop
- `citizenry/surface_citizen.py` — smarter teleop management
- `armos/detection/usb_monitor.py` — wire into asyncio event loop
- `armos/detection/citizen_factory.py` — spawn citizen from detected device

## Acceptance Criteria
- Plug in a new servo controller → citizen auto-starts within 5 seconds
- Plug in a new camera → camera citizen auto-starts
- Unplug a device → citizen broadcasts will and stops
- Governor doesn't lock arms in teleop by default
