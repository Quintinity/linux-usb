---
task_id: T48
purpose: Pack-out and transport plan for moving the EMEX 2026 stand and kit between home base and Auckland Showgrounds.
format: Sequenced checklist organised by phase (loading, transport, in-transit, arrival, return).
placeholders:
  - "{{PLACEHOLDER: home base address — pack/load origin}}"
  - "{{PLACEHOLDER: vehicle make/model + registration}}"
  - "{{PLACEHOLDER: drive distance + estimated travel time to Auckland Showgrounds}}"
  - "{{PLACEHOLDER: transit insurance policy number + insurer name}}"
  - "{{PLACEHOLDER: insurance excess + total cover amount}}"
  - "{{PLACEHOLDER: venue check-in contact name + phone}}"
  - "{{PLACEHOLDER: loading-dock window — start and end times}}"
  - "{{PLACEHOLDER: stand allocation reference from venue exhibitor pack}}"
  - "{{PLACEHOLDER: off-site backup target for lead data — e.g. encrypted cloud bucket URL}}"
  - "{{PLACEHOLDER: T35 leave-behind print run pickup detail}}"
  - "{{PLACEHOLDER: T43 partnership outline print run pickup detail}}"
last_updated: 2026-04-29
---

# T48 — Pack-out checklist + transport plan

Two transit legs: home base → Auckland Showgrounds (Sun 2026-05-25 morning) and Auckland Showgrounds → home base (Thu 2026-05-28 evening). Plan both ways. The return is the easier of the two — but it's also when fatigue costs gear.

Loading origin: {{PLACEHOLDER: home base address — pack/load origin}}.
Vehicle: {{PLACEHOLDER: vehicle make/model + registration}}.
Estimated drive: {{PLACEHOLDER: drive distance + estimated travel time to Auckland Showgrounds}}, plus 30 min loading and 30 min unloading.

Cross-references: stand setup at T39; spares list at T40.

---

## Loading order (home → venue)

Heaviest at the bottom. Easy-access items at the top. Pack the truck so the first thing off is the first thing needed.

- [ ] **Bottom layer — heaviest, structural**
  - [ ] Stand structure flat-pack (contractor-supplied, in their cases).
  - [ ] Robot rig: SO-101 leader and follower in foam-padded transit cases. Arms upright, gripper closed, no slack in the cabling.
  - [ ] Pi 5 (manipulator) and XIAO cameras boxed and padded inside the rig case.
- [ ] **Layer 2 — fragile but boxed**
  - [ ] Foam fixture for kit-sort task in its own carton, fixture-side up, padded all sides.
  - [ ] Spare hardware kit (T40), excluding backup hardware kit which travels on top.
- [ ] **Layer 3 — display**
  - [ ] Monitors in original boxes if available; otherwise foam-corner protected and bagged.
  - [ ] Monitor mounts and stands in a dedicated box.
- [ ] **Layer 4 — compute and tablets**
  - [ ] Surface laptops in padded sleeves inside a hard case.
  - [ ] iPads in padded sleeves inside a hard case.
- [ ] **Layer 5 — consumables and prints**
  - [ ] Leave-behinds in a waterproof tote: T35 general (200 copies — {{PLACEHOLDER: T35 leave-behind print run pickup detail}}), T43 partnership outline (50 copies — {{PLACEHOLDER: T43 partnership outline print run pickup detail}}), business cards, lanyards, name badges.
  - [ ] Cables — one labelled bag per category (HDMI, USB-C, USB-A, Ethernet, power). Bags inside one shared cable tote.
  - [ ] Tools — screwdriver kit, multimeter, tape, ties — in a tool roll.
- [ ] **Top layer — easy access**
  - [ ] Backup hardware kit (T40 robot core + T40 network) — must come off first if anything fails on the day.
  - [ ] First-aid kit, hand sanitiser, safety glasses.
  - [ ] Day-of paperwork: stand allocation, exhibitor pack, parking pass, this checklist.

---

## Transport (outbound, Sun 2026-05-25)

- [ ] **05:30** — Vehicle loaded the night before in reverse-arrival order. Sleep first, drive second.
- [ ] **06:00** — Pre-departure walk-around: lights, indicators, tyre pressure, fuel.
- [ ] **06:15** — Depart home base. Coffee at the first stop, not before driving.
- [ ] **In transit** — see In-transit care below.
- [ ] **Arrival window** — aim 08:30 at Auckland Showgrounds. Check in with {{PLACEHOLDER: venue check-in contact name + phone}}. Loading-dock window is {{PLACEHOLDER: loading-dock window — start and end times}}.
- [ ] **Loading dock** — present stand allocation {{PLACEHOLDER: stand allocation reference from venue exhibitor pack}}. Follow venue traffic marshals; don't park elsewhere "just for a moment".
- [ ] **Unload** — reverse loading order. Top-layer first off, structure last.

Total estimate: ~3 hours door-to-stand including loading at home and unloading at venue, plus drive time of {{PLACEHOLDER: drive distance + estimated travel time to Auckland Showgrounds}}.

---

## Insurance

- [ ] **Confirm cover before transit.** Total kit value sits well above NZ$5k once monitors, robots, laptops, tablets, and the spares kit are counted. Transit insurance must cover at least the higher of replacement value or {{PLACEHOLDER: insurance excess + total cover amount}}.
- [ ] **Policy.** {{PLACEHOLDER: transit insurance policy number + insurer name}}. Carry the policy summary in the day-of paperwork pouch.
- [ ] **Verify exclusions.** Some NZ transit policies exclude unattended vehicles overnight or roadside breakdowns. Read the schedule before the trip, not at the side of the road.

---

## In-transit care

- [ ] **Temperature.** Don't park in direct sun for hours. Servos and lithium cells degrade fast above 50 °C in cabin temperature. If a stop runs long, park in shade.
- [ ] **Vibration.** Servos are sensitive — every bump on the trip is a bump on the gear-train. Strap the cases. No loose cargo. Air pressure on the vehicle to spec, not over.
- [ ] **Arms upright.** Lay the SO-101s with the arm vertical and the gripper closed. Lubricant migrates if the arm sits sideways for a long drive — and migrated grease in the wrong gear stage is a failure that shows up at the worst time.
- [ ] **Smoke and dust.** No smoking in the vehicle, ever, but particularly with the gear loaded. Dust ingress through unsealed cases is the silent killer of optical encoders.
- [ ] **Eyes on the cargo.** If the vehicle is left, take the laptops, iPads, and the encrypted USB sticks with you. Hardware can be replaced in a week; the data on the leads iPad cannot.

---

## Arrival (at venue)

- [ ] **08:30** — Auckland Showgrounds gate. Show exhibitor pass.
- [ ] **08:35** — Loading-dock check-in: {{PLACEHOLDER: venue check-in contact name + phone}}. Confirm dock window {{PLACEHOLDER: loading-dock window — start and end times}}.
- [ ] **08:45** — Unload to stand allocation {{PLACEHOLDER: stand allocation reference from venue exhibitor pack}}. Wheel everything to the stand on a single trolley run if possible — the dock has limited dwell time.
- [ ] **09:15** — Stand allocation matches drawing? If not, raise immediately to venue contact.
- [ ] **09:30** — Hand off to T39 setup checklist.

---

## Return-trip (Thu 2026-05-28 evening)

Same checklist in reverse, with one critical pre-pack step: lead data has to be off the iPads before the iPads travel.

- [ ] **15:30** — Post-show debrief on stand: 30-min recap of leads, follow-ups, and what to fix tomorrow. Notes captured in the team channel.
- [ ] **16:00** — **Lead-iPad data export.** Export Tally form submissions, on-stand iPad notes, and any photos to the off-site backup target {{PLACEHOLDER: off-site backup target for lead data — e.g. encrypted cloud bucket URL}}. Verify the count matches the stand counter. Do not pack iPads until export is confirmed.
- [ ] **16:30** — Pack-down sequence (T39 Section 5).
- [ ] **17:30** — Vehicle loaded in arrival-order reverse: heaviest at the bottom (now structure rather than rig — rig is dirtier and more fragile after 3 days of demo, so it sits in the most-padded position on top of the structure but below the spares kit).
- [ ] **18:00** — Final walk of the stand area. Pick up cable scraps, business cards, anything left. Sign out at exhibitor desk.
- [ ] **18:15** — Depart Auckland Showgrounds.
- [ ] **In transit** — same care as outbound. Operators are tired; don't push to drive home in one shot if fatigue says no. Auckland-side overnight stop is acceptable; unloading at home base in the morning is fine.
- [ ] **Arrival home base** — unload in reverse loading order. Spares kit and anything that needs urgent triage off first; structure last.
- [ ] **+24 hours** — gear inspection: power on every laptop, Pi, XIAO, and arm. Anything that took transit damage gets logged before it sits in a case for a week and gets forgotten.

---

## Pre-flight before the return trip (do not skip)

- [ ] Lead-iPad data exported to off-site backup. Row count verified.
- [ ] Encrypted USB sticks pulled from the stand laptops and travel in a separate pouch (not inside the laptop sleeve — if the bag walks, you don't lose both).
- [ ] Demo VM final snapshot pushed to off-site backup.
- [ ] Venue stand area photographed empty and clean (insurance and goodwill).
- [ ] Power confirmed off at the wall before the multi-box is unplugged.
