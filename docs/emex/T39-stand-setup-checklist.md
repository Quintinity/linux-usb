---
task_id: T39
purpose: Master AV / power / network checklist for assembling, running, and powering down the EMEX 2026 stand.
format: Imperative checkbox checklist with five time-stamped sections.
placeholders:
  - "{{PLACEHOLDER: stand number, e.g. X42}}"
  - "{{PLACEHOLDER: venue Ethernet drop port location and credentials}}"
  - "{{PLACEHOLDER: 5G hotspot SIM ICCID + APN}}"
  - "{{PLACEHOLDER: monitor model — Cell 1 (recommend 27\" 1080p)}}"
  - "{{PLACEHOLDER: monitor model — Cell 2 (recommend 27\" 1080p)}}"
  - "{{PLACEHOLDER: monitor model — Cell 3 (recommend 27\" 1080p)}}"
  - "{{PLACEHOLDER: aisle-loop monitor model — recommend 24\" 1080p portrait-mountable}}"
  - "{{PLACEHOLDER: 32A NZ outlet position on stand floor plan}}"
  - "{{PLACEHOLDER: surge protector model + joule rating}}"
  - "{{PLACEHOLDER: governor laptop hostname — surface-lerobot-001}}"
  - "{{PLACEHOLDER: manipulator hostname — pi5-arm-001}}"
  - "{{PLACEHOLDER: XIAO camera hostnames — wifi-cam-xiao-001 etc.}}"
  - "{{PLACEHOLDER: stand-build contractor contact}}"
  - "{{PLACEHOLDER: venue contact for AV / power on the day}}"
last_updated: 2026-04-29
---

# T39 — Stand setup checklist (AV, power, network)

Master checklist for assembling and running the Quintinity stand at EMEX 2026 (Auckland Showgrounds, 26–28 May 2026, stand {{PLACEHOLDER: stand number, e.g. X42}}).

Goal: full stand ready in ≤ 2 hours on the day. The pre-flight in the home garage one week earlier is what makes that possible — do not skip it.

The two on-stand operators split tasks: **AV lead** owns monitors, cables, video loop. **Compute lead** owns the citizen mesh, MCP servers, Claude session, tablet UI.

Cross-references: pack-out at T48; spares list at T40; backup paths at T42.

---

## Section 1 — Pre-flight (T-7 days, home base garage)

Full stand assembled in the garage before the truck leaves. Catches the surprises early.

- [ ] **T-7 days, 09:00** — Lay out the floor plan in chalk on the garage floor at 1:1.
- [ ] Mount all three cell monitors on their stands; cable them to their host laptops/Pis.
- [ ] Mount the aisle-loop monitor in portrait if that's what the stand drawing calls for.
- [ ] Connect every cable end-to-end. Photograph each connector before tightening — that photo is the on-site reference.
- [ ] Power the whole stand from a single multi-box on a single 13A outlet (proxy for the venue 32A) and confirm no breaker trip across full demo run.
- [ ] Run the full triptych dry-run for 30 minutes. Watch for thermal throttling under enclosed-stand airflow.
- [ ] Photograph the working state: every cable run, every label, every monitor angle. Save to `docs/emex/setup-photos/` (gitignored).
- [ ] Pack each cable run into its own labelled bag. One bag per category (HDMI, USB-C, USB-A, Ethernet, power).
- [ ] Confirm tools and spares from T40 are physically present in the kit before sealing the cases.
- [ ] **T-7 days, 17:00** — Sign-off: stand-build contractor {{PLACEHOLDER: stand-build contractor contact}} confirms structure travels.

---

## Section 2 — Day before show (Mon 2026-05-25, on-site)

- [ ] **08:30** — Arrive Auckland Showgrounds. Check in at exhibitor desk. Collect lanyards, loading-dock pass, stand kit (table, chairs).
- [ ] **09:00** — Loading-dock window opens. Unload in pack-out reverse order (see T48). Heaviest first off the truck, lightest last.
- [ ] **09:30** — Verify stand allocation matches drawing. Flag any mismatch to {{PLACEHOLDER: venue contact for AV / power on the day}} immediately.
- [ ] **10:00** — Stand structure assembled (contractor lead).
- [ ] **11:00** — Tables and monitor mounts in position. Confirm 32A outlet at {{PLACEHOLDER: 32A NZ outlet position on stand floor plan}}.
- [ ] **11:15** — Lay surge protector {{PLACEHOLDER: surge protector model + joule rating}} between venue outlet and stand multi-box. Never plug the demo gear directly into the venue outlet.
- [ ] **11:30** — Three multi-boxes laid out: one per cell. Each multi-box on its own RCD if available.
- [ ] **12:00** — Lunch. Don't power anything on yet.
- [ ] **13:00** — Mount the three cell monitors and the aisle-loop monitor. Models:
  - Cell 1: {{PLACEHOLDER: monitor model — Cell 1 (recommend 27" 1080p)}}, HDMI 2 m run.
  - Cell 2: {{PLACEHOLDER: monitor model — Cell 2 (recommend 27" 1080p)}}, HDMI 2 m run.
  - Cell 3: {{PLACEHOLDER: monitor model — Cell 3 (recommend 27" 1080p)}}, HDMI 3 m run.
  - Aisle loop: {{PLACEHOLDER: aisle-loop monitor model — recommend 24" 1080p portrait-mountable}}, HDMI 5 m run with active extender.
- [ ] **13:30** — All HDMI cables seated and screwed where the connector supports it. Adaptors carry their own labels (USB-C-to-HDMI on the Surface).
- [ ] **13:45** — Brightness on every monitor set to 80%. Sleep timeout disabled. Auto-input-switch disabled.
- [ ] **14:00** — Network: connect to venue Ethernet drop {{PLACEHOLDER: venue Ethernet drop port location and credentials}}. If unreachable or unstable inside 10 minutes, fall back to 5G hotspot {{PLACEHOLDER: 5G hotspot SIM ICCID + APN}}.
- [ ] **14:15** — Confirm DNS resolves `api.anthropic.com` and the founding-five microsite from a stand laptop.
- [ ] **14:30** — Confirm mDNS resolves the Pi at `{{PLACEHOLDER: manipulator hostname — pi5-arm-001}}.local` from the Surface.
- [ ] **14:45** — Confirm multicast on `239.67.84.90:7770` carries citizen heartbeats end-to-end. The Surface (governor) and the Pi (manipulator) both publish PRESENT.
- [ ] **15:00** — Power-on sequence (rehearsed order — see Section 3).
- [ ] **15:30** — All three cells live.
- [ ] **16:00** — First on-stand triptych dry-run. Cell 1 → Cell 2 → Cell 3, end-to-end.
- [ ] **16:30** — Second dry-run with one of the four T42 backup paths exercised (rotate which one each evening).
- [ ] **17:00** — Final dry-run complete. Sign-off in the team channel: stand is show-ready.
- [ ] **17:15** — Power down (Section 4 sequence). Lock cabinet drawers. Take photographs of the final state.
- [ ] **17:30** — Off-site for sleep. Don't go for celebratory drinks — early start tomorrow.

---

## Section 3 — Show morning (each day, 08:00–09:00)

Doors open 09:00. Be live by 08:55. Power-on sequence is order-sensitive — citizen mesh first, applications last.

- [ ] **08:00** — Arrive on stand. Coffee on the way.
- [ ] **08:05** — Visual check: cables seated, no overnight pulls, monitor mounts firm.
- [ ] **08:10** — Power on the multi-box (single switch). Wait 30 seconds for inrush.
- [ ] **08:12** — Power on monitors. Confirm all four show "no signal" (expected — hosts not yet up).
- [ ] **08:15** — Power on the citizen mesh in this order:
  1. Surface (governor) — `{{PLACEHOLDER: governor laptop hostname — surface-lerobot-001}}`. Wait for `citizenry-governor` to publish PRESENT.
  2. Pi 5 (manipulator) — `{{PLACEHOLDER: manipulator hostname — pi5-arm-001}}`. Wait for PRESENT.
  3. Two XIAO cameras — `{{PLACEHOLDER: XIAO camera hostnames — wifi-cam-xiao-001 etc.}}`. Wait for PRESENT.
- [ ] **08:25** — Confirm all four citizens show PRESENT in the governor CLI.
- [ ] **08:27** — Start MCP servers in this order: TDM-MCP, Citizen-MCP. Wait for each to log "ready".
- [ ] **08:32** — Start the Claude orchestrator session. Wait for "session ready".
- [ ] **08:35** — Start the orchestrator on the Cell 3 laptop.
- [ ] **08:40** — Tablet UI: launch the approval-gate app on the iPad. Confirm gate state polls green-able.
- [ ] **08:45** — Aisle-loop monitor: start the 60-second video loop (T34 deliverable).
- [ ] **08:50** — Smoke tests (run all four; do not skip):
  1. **Cell 1 smoke** — Type one canned diagnostic question into the kiosk; expect streamed answer with citations within 4 seconds.
  2. **Cell 2 smoke** — Press teach-record on the leader; record 3 seconds; play back on the follower; arm completes within ±5 mm of the leader path.
  3. **Cell 3 smoke** — Run one end-to-end loop: TDM query → Claude reasoning → approval-gate tap → ledger write. End-to-end ≤ 5 seconds.
  4. **Backup-path smoke** — Pull the venue Ethernet for 10 seconds. Confirm the 5G hotspot takes over and Cell 1 falls back to cached responses (T42 backup C path).
- [ ] **08:55** — All green. Lanyards on. Stand opens.

---

## Section 4 — End of each day (17:00–17:30)

- [ ] **17:00** — Doors close. Don't pack down yet — visitors linger.
- [ ] **17:05** — Power-down sequence (reverse of Section 3): tablet UI → orchestrator → MCP servers → citizen mesh applications. Citizens themselves stay on overnight if power is on.
- [ ] **17:10** — Lead-iPad sync: export today's Tally submissions to the leads spreadsheet. Confirm row count matches stand counter.
- [ ] **17:15** — Demo VM checkpoint: snapshot the TDM demo VM. Push the snapshot to off-site backup before the iPad and laptops travel.
- [ ] **17:20** — Restock leave-behinds (T35), partnership outlines (T43), business cards.
- [ ] **17:25** — Photograph the stand state for tomorrow's reference.
- [ ] **17:30** — Lock cabinet. Power off the multi-box at the wall. Turn off lighting if separate.

---

## Section 5 — Pack-down (Thu 2026-05-28, 16:00–18:00)

Abbreviated — full pack-out procedure is in T48.

- [ ] **16:00** — Doors close, day 3. Final visitor sweep.
- [ ] **16:15** — Power-down sequence (Section 4). Wait for fans to stop on every box before unplugging.
- [ ] **16:30** — Disconnect cables in reverse of setup. Each cable into its labelled bag immediately — no loose cables in the kit.
- [ ] **17:00** — Monitors into original boxes. Padding on every corner.
- [ ] **17:15** — Citizen mesh hardware into padded transit cases. Arms upright, foam-supported (see T48 in-transit care).
- [ ] **17:45** — Stand structure dismantled (contractor lead).
- [ ] **18:00** — Loaded into vehicle in T48 loading order. Sign out at exhibitor desk.

---

## Backup paths (cross-reference)

- **Internet drops** — Cell 1 falls back to cached responses; Cell 3 switches to the 60-second video loop (T42 backup C "video loop only" mode).
- **API down** — Cell 2 stays live (replay-only); Cells 1 and 3 to pre-recorded video. Honest narration to visitors per T42.
- **Hardware failure** — hot-swap from spares kit (T40 + T24 hot-swap procedure).
- **Constitution rejection** — feature, not failure; lean into it (T42 backup D).
