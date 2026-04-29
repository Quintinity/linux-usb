---
task_id: T23
purpose: Step-by-step procedure for swapping a failed Cell 2 triplet (SO-101 follower + Pi 5 + XIAO camera) on the EMEX 2026 stand in ≤ 8 minutes.
format: Sequenced procedure with time budget per step, two-person ideal vs one-person fallback, and a calibration-restore decision tree.
placeholders:
  - "{{PLACEHOLDER: spare SO-101 serial number + governor-key fingerprint}}"
  - "{{PLACEHOLDER: spare Pi 5 hostname pre-flashed — e.g. pi5-arm-spare-001}}"
  - "{{PLACEHOLDER: spare XIAO hostname + node-key fingerprint — e.g. wifi-cam-xiao-spare-001}}"
  - "{{PLACEHOLDER: governor laptop hostname — surface-lerobot-001}}"
  - "{{PLACEHOLDER: spare 12V PSU model + barrel polarity}}"
  - "{{POST-SHOW NOTE: hot-swap times actually achieved on stand, with any per-step deltas}}"
last_updated: 2026-04-29
---

# T23 — Hot-swap procedure (Cell 2 triplet)

Procedure for replacing a failed Cell 2 triplet — SO-101 follower + Pi 5 manipulator + XIAO camera — on the EMEX stand without taking the stand offline.

Target: **≤ 8 minutes total**, two-person ideal, one-person fallback ≤ 10 minutes. Beyond 10 minutes, abandon the swap and switch the cell to the 60-second video loop per T42 backup A escalation.

This document is referenced by:
- T40 spare-hardware checklist — defines the spare kit
- T42 backup plan A "arm jam" — invokes this procedure when power-cycle recovery fails
- T39 stand setup — cross-references hot-swap as the hardware-failure recovery path

Architectural note: the spare XIAO is a **native citizen**, not a Pi-proxy fallback. It carries its own Ed25519 keypair in NVS at `0x9000` and joins the mesh by signed multicast on `239.67.84.90:7770` exactly like the primary. Treat the swap as triplet-shaped: any one of the three units can fail and is swapped independently.

---

## Pre-conditions — when to invoke this procedure

Run hot-swap only when **all** of the following hold:

1. The 30-second power-cycle recovery (T42 backup A) has been attempted and the unit did not return to PRESENT in the governor CLI.
2. The failure is isolated to a single hardware unit (one arm, one Pi, one XIAO) — not a venue-side power or network outage. Confirm by checking that the other two cells are still live.
3. The visitor narrative is parked: the front-of-stand person has already said "give me 30 seconds to clear it" per T42 and is now bridging to a Cell 1 or Cell 3 conversation.
4. ≥ 8 minutes remain in the current visitor window. If a major demo loop is mid-run with < 5 minutes left, finish the current run on the video loop and swap during the natural lull.

**Do NOT hot-swap when:**

- The Constitution rejected an action (T42 backup D — that is a feature, lean into it).
- The MCP bridge timed out (T42 backup B — restart the orchestrator, do not swap hardware).
- The Anthropic API is down (T42 backup C — switch to video, do not swap hardware).
- Power-cycle has not been attempted yet — try the 30-second recovery first.

If in doubt, **pause via tablet first**: tap the safe-mode amendment on the iPad approval-gate UI to halt Cell 2 cleanly through the governor. That stops the bus, lets neighbours settle, and gives you time to decide whether the failure actually warrants a swap. The pause is auditable; the panic-rip is not.

---

## Two-person ideal procedure (target ≤ 8 min)

Roles: **Compute lead** owns the laptop, governor CLI, and citizen mesh handshake. **AV/hands lead** owns the physical swap — power, cables, motor chain, mount.

### Step 0 — Pause and brief (T+0:00 → T+0:30, 30 s)

- [ ] **Compute lead** taps the safe-mode amendment on the iPad. Cell 2 governor halts the failed unit; neighbours stay live.
- [ ] **AV lead** retrieves the spare triplet from the under-bench foam tray (T40 robot core entries 1–3). Place all three units on the bench — do not yet connect.
- [ ] Visual confirm of which unit failed: red LED on a XIAO, no PRESENT line for the Pi in the governor CLI, or audible servo silence on the SO-101. Often more than one is implicated; assume the whole triplet swaps unless the failure is unambiguous.

### Step 1 — Power-down the failed unit (T+0:30 → T+1:30, 60 s)

Order matters — avoid bus-glitching the live neighbours.

- [ ] **AV lead** switches the Cell 2 multi-box **at the wall**, not at the cell-side switch. The cell-side switch sometimes back-feeds via USB; wall-side cuts cleanly.
- [ ] Wait for the 12V PSU LED on the failed SO-101 to extinguish. Do not unplug while lit — Feetech servos can latch overload faults that need a full cold-cycle to clear, and an unclean power-off will trip the latch on the *spare* the moment it joins the chain.
- [ ] Disconnect in this order: USB-C from the Pi (data), 12V barrel jack from the SO-101 PSU brick, USB-A from the servo controller, then the motor-chain ribbon at the controller end. Last off the chain is the daisy-chain ribbon — pulling it under load will crash any neighbour still on the same physical bench bus.
- [ ] Lift the failed arm off its mount. Set it aside on the post-failure shelf — do not put it back in the spares tray; it is now the suspect, not a spare.

### Step 2 — Physical swap mechanics (T+1:30 → T+3:30, 120 s)

- [ ] **AV lead** mounts the spare SO-101 on the same fixture. The mount holes are factory-symmetric — do not re-shim.
- [ ] Plug the spare 12V PSU ({{PLACEHOLDER: spare 12V PSU model + barrel polarity}}) into the multi-box but **do not energise yet**. Confirm barrel polarity by sticker — a reversed barrel will brick the controller in under one second.
- [ ] Reconnect motor chain at the controller end first, then the controller's USB-A to the spare Pi. The chain end goes on with a firm push to seat — partial seats give intermittent reads that look exactly like a broken servo and burn debugging time you do not have.
- [ ] Plug the spare Pi's USB-C power into the multi-box (not yet on).
- [ ] Mount the spare XIAO in the camera bracket. Connect its USB-C (5V, data not required) to the multi-box.
- [ ] Confirm every cable is in its strain-relief clip before the next step. A snagged cable on a live arm is the second-most-common cause of show-floor injury after gripper pinches.

### Step 3 — Energise and join mesh (T+3:30 → T+5:00, 90 s)

- [ ] **AV lead** flips the Cell 2 multi-box back on at the wall.
- [ ] **Compute lead** watches the governor CLI on `{{PLACEHOLDER: governor laptop hostname — surface-lerobot-001}}`:
  1. Within ~ 15 s the spare Pi multicasts DISCOVER. Governor responds with the Constitution + Laws bundle.
  2. Within ~ 30 s the spare Pi returns PROPOSE-ratify with its Ed25519 signature over the canonical Constitution hash. Governor records ratification in the audit ledger.
  3. The spare XIAO follows the same DISCOVER → ratify path. First HEARTBEAT carries its `camera_role` and pubkey ({{PLACEHOLDER: spare XIAO hostname + node-key fingerprint — e.g. wifi-cam-xiao-spare-001}}).
  4. The spare SO-101 itself does not multicast — it appears in the mesh through its Pi manipulator citizen advertising the new arm serial ({{PLACEHOLDER: spare SO-101 serial number + governor-key fingerprint}}).
- [ ] **Tablet UI** transitions: the Cell 2 row turns from amber ("paused") to green ("ratified, ready") once all three new pubkeys are in the governor's accepted set. If the row stays amber past T+5:00, the Constitution exchange has stalled — see Rollback below.

### Step 4 — Calibration restore (T+5:00 → T+6:30, 90 s)

The spare arm needs calibration before it can teleop. Decision tree:

```
Is a recent calibration JSON for THIS spare arm serial on the spare Pi?
├── YES (pre-staged at home base, file mtime ≤ 7 days old)
│   └── Spare Pi auto-loads from ~/.cache/huggingface/lerobot/calibration/
│       robots/so_follower/<serial>.json on citizen-start.
│       AV lead does nothing. Compute lead verifies "calibration loaded"
│       in the manipulator citizen log line. (90 s budget held.)
│
├── NO, but the failed arm's calibration file is recoverable
│   └── If the failed Pi is still readable over USB-Ethernet gadget,
│       scp ~/.cache/huggingface/lerobot/calibration/robots/so_follower/*.json
│       to the spare Pi. Re-mount the spare arm motors to the same physical
│       positions noted in the file (mid-pose photo on bench laminate).
│       Restart manipulator citizen. (~ 90 s if file copy works first try.)
│
└── NO, and not recoverable
    └── Fast re-calibrate: `lerobot-calibrate --robot=so_follower
        --port=/dev/ttyACM0 --quick`. Quick mode skips the full sweep and
        captures only the home, mid, and extents. ~ 5 min, blowing the
        budget. If you go this route, accept that total swap time is
        ≥ 10 min and Cell 2 stays on the video loop until calibration
        completes — do not rush calibration to save 30 seconds; a
        miscalibrated arm will throw torque-limit Constitution rejects
        on every demo run.
```

**Default expectation:** the spare Pi ships with the most recent calibration JSON for the spare arm pre-staged. Confirm this during the T-7 garage pre-flight (T39 Section 1) — the JSON's mtime must be no older than the last mechanical work on the spare. If the spare arm has been re-shimmed or had a servo replaced since the file was captured, treat the file as stale and pre-stage a fresh one before the truck leaves.

### Step 5 — Smoke test (T+6:30 → T+7:30, 60 s)

- [ ] **Compute lead** sends one signed teleop motion through the lerobot-MCP server: `safe_dance --duration=5s --amplitude=0.2`. The signed action goes through the governor, the Pi forwards to the spare arm, the arm executes a low-amplitude wave, and the audit ledger records exactly one new entry tagged with the new arm serial.
- [ ] Verify three signals:
  1. Arm completes the motion without overload latch (no LED red, no Constitution reject).
  2. New audit-ledger entry visible on Cell 2 monitor with the spare's pubkey fingerprint.
  3. XIAO frame_stream visible on Cell 2 — confirms the spare camera is live and signing frames.
- [ ] **AV lead** confirms physical: arm at expected pose, no servo whine, no smoke, no smell of warm PSU.

### Step 6 — Resume demo (T+7:30 → T+8:00, 30 s)

- [ ] **Compute lead** taps the safe-mode amendment off on the iPad. Cell 2 returns to live.
- [ ] **Front-of-stand person** picks the visitor narrative back up: *"And we're live again — the audit trail follows the citizen, not the hardware. That's a new arm in there now, with its own pubkey, ratified by the governor 90 seconds ago."*
- [ ] Total elapsed: 8:00. Log the swap time in the team channel (post-show notes).

---

## Time budget summary

| Step | Description | Duration | Cumulative |
|---|---|---|---|
| 0 | Pause and brief | 30 s | 0:30 |
| 1 | Power-down failed unit | 60 s | 1:30 |
| 2 | Physical swap | 120 s | 3:30 |
| 3 | Energise and mesh join | 90 s | 5:00 |
| 4 | Calibration restore (pre-staged path) | 90 s | 6:30 |
| 5 | Smoke test | 60 s | 7:30 |
| 6 | Resume demo | 30 s | 8:00 |

Total: **8:00**. Calibration step holds the budget only on the pre-staged path — fall through to fast re-calibrate and the budget blows past 10 min.

---

## One-person fallback (target ≤ 10 min)

If only one operator is on stand (visitor surge has the other engaged, or partner is at lunch):

- Front-of-stand visitor *must* be parked first — hand them a T35 leave-behind, point them at Cell 1 or Cell 3, set the video loop running on Cell 2. Do not start the swap with a visitor watching Cell 2.
- Combine roles, lose ~ 90 s in context-switching between laptop and physical work. Realistic budget: **9:30–10:00**.
- Skip the formal pause-brief (Step 0); the safe-mode amendment is already implied by powering down at the wall.
- Smoke test (Step 5) becomes a single check rather than three — visual confirmation of the dance motion is enough; the audit-ledger and frame_stream checks happen during the next live run.

If the one-person budget exceeds 10 minutes, abandon the swap and leave Cell 2 on the video loop for the rest of the session. Better to demo 2 cells well than 3 cells poorly.

---

## XIAO-only swap (sub-procedure)

If only the XIAO failed and arm + Pi are healthy, the swap collapses to ~ 4 minutes:

- [ ] Power-down the XIAO via its USB-C only (do not cut the cell multi-box — the arm and Pi keep running).
- [ ] Mount and plug the spare XIAO. WiFi credentials are baked into the spare's NVS at provisioning time.
- [ ] Spare XIAO multicasts DISCOVER → governor sends Constitution → ratify → first HEARTBEAT → frame_stream live.
- [ ] No calibration step required for cameras.
- [ ] Smoke test: visitor sees the camera feed return on the Cell 2 monitor; one frame_stream packet logged in the audit ledger.

**Critical**: if the spare XIAO needs to be re-flashed in the field (e.g. firmware corruption, NVS dump for diagnostics already done), use **partition-aware flashing only**:

```
esptool --chip esp32s3 --port /dev/ttyACM0 write-flash 0x10000 xiao-citizen.ino.bin
```

Never flash `merged.bin` at `0x0`. The merged image overwrites NVS at `0x9000`, which wipes the device's Ed25519 keypair and forces the governor to re-trust a brand-new identity. The mesh will technically still work, but every prior signature in the audit ledger is now orphan-keyed — a bad look at a show whose entire pitch is "every decision traced". Pre-staged spares already carry their keypair; preserve it.

---

## Rollback if swap fails

Failure modes during the swap and what to do about them:

1. **Spare unit does not multicast PRESENT within 60 s of power-on.**
   - Check WiFi association first (XIAO blue LED, Pi `iw dev`). Most likely cause: 5G hotspot or venue Ethernet has dropped — *not* a hardware fault on the spare. Roll back: power down the spare, re-energise the original failed unit if it is the cell or network at fault, and re-run T42 backup C (network outage path).

2. **Spare ratifies but Constitution exchange stalls amber on tablet.**
   - The governor accepted the unit's signature but the Laws bundle did not round-trip. Most often the manipulator citizen is on a stale Constitution version. On the spare Pi: `systemctl restart citizen-manipulator`; the next ratification round will pull the current Laws set. If still amber after one restart, abandon the swap — Cell 2 to video loop.

3. **Calibration JSON loads but arm immediately throws torque-limit reject.**
   - The pre-staged calibration is for a different mechanical state of the arm. Do not "just relax the Constitution cap" — that defeats the demo's whole pitch. Fall through to fast re-calibrate (Step 4 third branch) and accept the budget blow-out, or abandon the swap.

4. **PSU LED does not come on after multi-box energise.**
   - Spare PSU is dead. Replace from the secondary PSU spare in T40 power section. If no secondary PSU is available, abandon — Cell 2 to video loop.

5. **Total swap exceeds 10 minutes.**
   - Stop. Switch Cell 2 to the 60-second video loop per T42 backup A escalation. Run Cell 1 and Cell 3 only for the rest of the session. Diagnose the swap blocker between sessions, on the bench, with a fresh head.

The flipchart fallback (drawn-from-memory triptych explanation per T42) is the absolute last resort — only if Cell 2's video loop also fails. The flipchart sits behind the bench in case it is needed; do not over-rehearse it because going there means three things have already failed.

---

## Pre-show preparation (does not happen on stand)

For this procedure to hit 8 minutes, the spare triplet must be pre-staged at home base. During T39 Section 1 (T-7 days garage pre-flight):

- [ ] Spare Pi 5 imaged, hostname `{{PLACEHOLDER: spare Pi 5 hostname pre-flashed — e.g. pi5-arm-spare-001}}`, joined to the home mesh, ratified Constitution at least once. Confirm pubkey fingerprint matches the registered spare on the governor.
- [ ] Spare XIAO flashed (partition-aware), WiFi credentials baked, NVS keypair generated and recorded. Confirm pubkey fingerprint matches the registered spare on the governor.
- [ ] Spare SO-101 powered up on bench, calibrated against the spare Pi, calibration JSON exported to `~/.cache/huggingface/lerobot/calibration/robots/so_follower/<spare-serial>.json` on the spare Pi. Mid-pose photographed and the photo laminated to the inside of the spare's foam tray.
- [ ] One full bench dry-run of this procedure end-to-end. Capture actual elapsed time per step. If any step blows its budget, fix it now, not on stand.
- [ ] All three pubkeys added to the governor's `known_spares` set so the first DISCOVER on stand does not require manual approval — the show-floor mesh-join must be hands-off.

**Lessons captured.** {{POST-SHOW NOTE: hot-swap times actually achieved on stand, with any per-step deltas}}
