---
task_id: T18
purpose: Build spec for the kit-component sort demo fixture (foam tray + parts cup + mounting) used on Cell 2 at EMEX 2026.
format: Structured build doc — parts list, dimensioned tray spec, workspace layout, mounting, reset procedure, build steps.
placeholders:
  - "{{PLACEHOLDER: M3 cap-screw vendor SKU — recommend Blacks Fasteners NZ stainless A2 8mm}}"
  - "{{PLACEHOLDER: M3 washer vendor SKU — recommend Blacks Fasteners NZ stainless A2 form A}}"
  - "{{PLACEHOLDER: M3 nyloc lock-nut vendor SKU — recommend Blacks Fasteners NZ stainless A2}}"
  - "{{PLACEHOLDER: M3 spring vendor SKU — recommend Century Spring NZ compression 4mm OD x 10mm free length}}"
  - "{{PLACEHOLDER: parts cup vendor SKU — recommend Sistema 200ml round, clear PP, NZ supermarket}}"
  - "{{PLACEHOLDER: foam tray supplier — recommend Para Rubber NZ closed-cell EVA 20mm sheet}}"
  - "{{PLACEHOLDER: laser-etch shop — recommend Ponoko Auckland or local maker space}}"
  - "{{PLACEHOLDER: 3M VHB tape SKU — recommend 5952 black 1.1mm}}"
  - "{{PLACEHOLDER: magnetic retrieval wand SKU — recommend Mitre 10 telescoping}}"
  - "{{PLACEHOLDER: photo TBD — Bradley to attach — overall fixture top-down on stand surface}}"
  - "{{PLACEHOLDER: photo TBD — Bradley to attach — labelled tray close-up showing all four compartments}}"
  - "{{PLACEHOLDER: photo TBD — Bradley to attach — workspace layout with arm + tray + cup, side elevation}}"
  - "{{PLACEHOLDER: photo TBD — Bradley to attach — reset wand on ferrous spill}}"
last_updated: 2026-04-29
---

# T18 — Fixture build spec (kit-component sort demo)

Build doc for the Cell 2 demo fixture: a labelled foam tray plus a parts cup, used by the SO-101 follower (autonomous) and SO-101 leader-teleop (operator-driven) to sort M3 cap-screws, washers, lock-nuts, and springs into their compartments.

The demo task is locked: SO-101 picks each component from a parts cup and places it into its labelled compartment of the foam tray. Photogenic, demonstrably "manufacturing", quick reset cycle. This doc specifies what to build so the same fixture works for both arms with no swap.

Cross-references: T34 video script (block 2 shoots this fixture), T39 stand setup, T40 spares (foam tray + kit components are listed there), T48 pack-out (fixture transport).

---

## 1. Parts list

Four components, all M3, all chosen for visible difference under stand lighting (silver screw + silver washer + silver nyloc with white nylon insert + bare-steel spring — three of four are ferrous which matters for reset, see Section 6).

### Per demo run (one full sort)

| Component | Per-run qty | Spec | Vendor SKU |
|---|---|---|---|
| M3 cap-screw, 8 mm, stainless A2 | 1 | Hex socket head, fully threaded, 5.5 mm head dia | {{PLACEHOLDER: M3 cap-screw vendor SKU — recommend Blacks Fasteners NZ stainless A2 8mm}} |
| M3 washer, form A, stainless A2 | 1 | 7 mm OD, 0.5 mm thick | {{PLACEHOLDER: M3 washer vendor SKU — recommend Blacks Fasteners NZ stainless A2 form A}} |
| M3 nyloc lock-nut, stainless A2 | 1 | Standard height, 5.5 mm AF, white nylon insert | {{PLACEHOLDER: M3 nyloc lock-nut vendor SKU — recommend Blacks Fasteners NZ stainless A2}} |
| M3 compression spring | 1 | 4 mm OD, 10 mm free length, 0.5 mm wire, plain steel | {{PLACEHOLDER: M3 spring vendor SKU — recommend Century Spring NZ compression 4mm OD x 10mm free length}} |

### Per show (3 days × ~250 demo runs/day = ~750 runs target)

Per run we use 1 of each. Buffer 3× because visitors pocket parts (this is universal at trade shows — budget for it, don't fight it), parts roll off the stand, and the cup gets knocked. Round to bag sizes available from suppliers.

| Component | Primary qty (in cup) | Spare bag (kit case) | Deep spare (transit case) |
|---|---|---|---|
| M3 cap-screw 8 mm | 50 | 100 | 100 |
| M3 washer | 50 | 100 | 100 |
| M3 nyloc lock-nut | 50 | 100 | 100 |
| M3 compression spring | 50 | 100 | 100 |

Total per component across the kit: 250. Loss tolerance: ~2 per hour pocketed × 24 stand hours = ~50 lost. Spill tolerance: 1 cup-knock per day at ~50 parts on the floor = 150 over the show. The deep spare absorbs both.

Per-show qty aligns with what T40 lists ("M3 kit components, 50 of each, 2 bags") — this doc upgrades the count: T40's row should be read as 250 of each, packaged as primary + spare + deep-spare. See Section 11 follow-up.

---

## 2. Foam tray dimensions

Closed-cell EVA, 20 mm thick. Closed-cell holds a crisp pocket edge under stand lighting and doesn't shed crumbs into the parts. Density 80 kg/m³ (firm enough that a dropped lock-nut doesn't bounce out, soft enough that a misplaced part doesn't ping off-camera).

**Overall tray:** 200 × 100 × 20 mm (matches the plan's T18 inline note). Black EVA — high contrast against bare steel parts, kind to the camera exposure.

**Four compartments**, laid out 2×2 on the long axis:

```
+----------------+----------------+
|     SCREW      |     WASHER     |
|   (slot A)     |    (slot B)    |
+----------------+----------------+
|    LOCK-NUT    |     SPRING     |
|    (slot C)    |    (slot D)    |
+----------------+----------------+
```

Each compartment is a cylindrical pocket, 12 mm dia × 12 mm deep, centred on its quadrant. Quadrant centres at (50, 25), (150, 25), (50, 75), (150, 75) mm from the tray's near-left corner.

Pocket dimensions chosen to:
- Accept any of the four parts (largest is the 8 mm cap-screw at 5.5 mm head; 12 mm gives 3 mm clearance all round — generous because the gripper needs forgiveness).
- Stay shallower than tray thickness (12 mm pocket in 20 mm foam leaves 8 mm floor — won't punch through, won't flex when a part lands).
- Match all four pockets so the spec is one number, not four — easier to laser-cut, easier to verify on site.

**Labelling:** laser-etched directly into the foam, white-filled, on the upper edge of each pocket inside a 25 × 8 mm flat zone. Labels: `SCREW`, `WASHER`, `LOCK-NUT`, `SPRING` in 5 mm sans-serif.

Why laser-etched and not stickers: stickers peel under stand-handling, look amateur, and shed adhesive on the foam surface. Laser-etch on EVA gives a clean white-on-black mark that survives the show. {{PLACEHOLDER: laser-etch shop — recommend Ponoko Auckland or local maker space}} can do this in one pass alongside the perimeter cut.

Backup labelling option (if etch slot isn't available before pack-out): 25 × 8 mm engraved acrylic insert glued into a routed pocket on the upper edge of each compartment. More work, more parts, but survives transit better than printed labels.

---

## 3. Parts cup spec

**Recommendation: single mixed cup.**

Rationale:
- The demo is a sort task — mixing the parts is the whole point. Per-type cups undermine the visual story (visitor sees "robot moves screw to screw slot", not "robot identifies and sorts").
- A single cup is one reach target the policy has to learn, not four. Cell 2 has limited bench-test time before the show; one target is faster to get reliable.
- Per-type cups would also need their own X positions, chewing into the SO-101 reach envelope (≤300 mm from base per the plan). Four cups + tray won't all fit inside reach.
- Reset is faster: scoop the tray back into one cup, not four.

**Cup spec:** clear PP food container, 200 mL, ~95 mm dia × 50 mm tall, flat bottom. Clear so the camera sees the parts at the bottom; PP because it survives drops, doesn't shatter. {{PLACEHOLDER: parts cup vendor SKU — recommend Sistema 200ml round, clear PP, NZ supermarket}}.

Filled to ~30 mm depth (50 of each part = ~150 parts total = roughly half full). Half full is the sweet spot: shallow enough that the gripper reaches the bottom, deep enough that the parts don't slosh out on every grab.

---

## 4. Workspace layout

SO-101 has 6 DoF (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper). Effective horizontal reach with a clean grasp pose is ~300 mm from the base centre (the plan calls this ≤30 cm and the calibration file at `~/.cache/huggingface/lerobot/calibration/robots/so_follower/follower.json` defines the joint ranges that bound it). Both fixture targets (tray + cup) must sit inside that radius and above the gripper's safe minimum height (gripper closed pose, ~40 mm above bench surface).

Top-down layout (arm base at origin, looking down at the bench):

```
                       Y (away from operator)
                       ^
                       |
                   +--------+
                   |  TRAY  |  tray centre at (0, +220) mm
                   | 200x100|  long axis on X
                   +--------+
                       |
                       |
                       |
                  +---ARM---+         +---+
                  |  base   |         |CUP|  cup centre at (+180, +60) mm
                  | (0, 0)  |---------|95mm|
                  +---------+         +---+
                       |
                       |
                       v (towards operator / camera)
                       |
                  X --->
```

Distances:
- **Tray:** centre at X=0, Y=+220 mm from arm base centre, long axis aligned with X. Near edge of tray at Y=+170 mm; far edge at Y=+270 mm. All four compartments are inside the 300 mm reach (worst case is the far-corner pocket at sqrt(100² + 270²) ≈ 288 mm).
- **Cup:** centre at X=+180 mm, Y=+60 mm (front-right quadrant from arm's perspective). Distance from base ≈ sqrt(180² + 60²) ≈ 190 mm — comfortably inside reach. Sits to the right of the operator's working hand for the leader-teleop case (Bradley is right-handed; operators hand naturally enters from the front-right when teaching).
- **Heights:** both tray top surface and cup rim sit at the same Z (the stand bench surface). Bench is 95 cm above stand floor per plan Task 18 step 3 (visitor reach height). Gripper safe minimum height is ~40 mm above bench, so cup rim at 50 mm above bench leaves 10 mm gripper clearance; pocket lip at 0 mm (flush with tray top, foam below) leaves the gripper full pocket depth to descend.

This layout works for both arms:
- **Follower-only autonomous:** policy drives the same arm to the same waypoints. No human, no teleop.
- **Leader-teleop:** operator stands behind the stand bench, in front of the camera, leader on a parallel bench. The operator's leader arm and the follower arm are mirrors. The fixture in front of the follower is what the camera sees; the fixture-side targets are identical.

The cup in the front-right and tray straight ahead also keeps the cable/PSU run (which lives behind the arm per the persona doc) out of the camera's frame — the videographer (T34) shoots block 2 from the front-left of the bench at a low angle. The PSU and bus cables stay behind and below the camera line.

---

## 5. Mounting / non-slip

Both the tray and cup must not move during the demo. A 5 mm tray creep accumulates over 250 runs/day into a missed pocket on day 3.

**Tray:** 3M VHB tape (4 strips, 80 × 20 mm, on the four corners of the underside). VHB sticks the tray to the bench top hard enough to need a putty knife to remove for transit. {{PLACEHOLDER: 3M VHB tape SKU — recommend 5952 black 1.1mm}}.

Alternative if the bench surface is something VHB doesn't like (raw plywood, painted melamine in poor condition): four self-adhesive silicone non-slip feet on the underside (one per corner), plus a single strip of double-sided gaffer tape across the centre underside. Less permanent, easier to reset between days.

**Cup:** silicone non-slip pad under the cup (one circular 100 mm dia pad, food-grade silicone, 2 mm thick). The cup is intentionally not stuck-down: visitor or operator nudges it during reset, and that's fine. Gripper grasp tolerance is wider than cup-position tolerance — the policy locates the cup centre, not the cup edge.

For the full pre-flight at home base (T39 Section 1), confirm that 250 demo runs do not displace either fixture. If the cup walks more than 5 mm in a 30-minute run, swap silicone pad for a recessed silicone tray (3 mm well, cup sits in it).

---

## 6. Reset between attempts

Three of the four parts are ferrous (cap-screw, lock-nut, spring; washer is stainless A2 — very weakly ferrous, in practice non-ferrous). Reset path differs for clean-tray vs spilled-on-bench.

**Clean tray reset (every successful sort, ~250 times/day):**
- Operator tilts tray over cup, parts pour back in. ~3 seconds.
- Manual scoop with a 50 mm wide silicone spatula gets the last few. ~5 seconds.
- Total: ~8 seconds. Does not break the demo loop pacing.

**Spilled-on-bench reset (after a knock or a botched grasp):**
- Magnetic retrieval wand for the three ferrous components. {{PLACEHOLDER: magnetic retrieval wand SKU — recommend Mitre 10 telescoping}}. Telescoping wand reaches under the arm base and behind cable runs without moving the arm.
- Manual pickup for washers (non-ferrous in practice).
- Total: ~30 seconds. Visitors don't mind watching this — it's also "manufacturing".

**Mid-day full reset (once at lunch, once at 14:30):**
- Empty cup into a clean bench bowl, count parts, top up to ~50 of each from the spare bag.
- Inspect tray pockets for dust or worn etch labels. Wipe with isopropyl per T40's "Tools" row.
- Total: ~5 minutes. Schedule into the natural lulls.

Place the magnetic wand on the operator side of the bench, clipped to the bench edge with the same VHB used on the tray. Visible to the operator, out of the camera's frame.

---

## 7. Per-show quantities (T40 alignment)

| Item | Primary (on stand) | Spare (kit case) | Deep spare (transit case) |
|---|---|---|---|
| Foam tray (etched, mounted) | 1 | 1 | 1 |
| Parts cup | 1 | 1 | 1 |
| Silicone non-slip pad | 1 | 2 | 2 |
| 3M VHB strips, pre-cut | (under tray) | 4 strips | 4 strips |
| Magnetic retrieval wand | 1 | 1 | 0 |
| Silicone scoop spatula | 1 | 1 | 0 |
| M3 cap-screw 8 mm | 50 (in cup) | 100 | 100 |
| M3 washer | 50 | 100 | 100 |
| M3 lock-nut | 50 | 100 | 100 |
| M3 spring | 50 | 100 | 100 |

This supersedes T40's "Foam tray for kit-sort fixture: 1" and "M3 kit components: 50 of each, 2 bags" rows — see Section 11 follow-up.

---

## 8. Build steps and time estimate

Total build time: ~4 hours, plus ~3 days lead time for the laser-etch run.

1. **Source materials** (~30 min, week before build) — order EVA sheet, M3 components, cup, VHB, silicone pads, magnetic wand. All NZ-local except the etch shop is whoever has capacity.
2. **Design DXF** (~30 min) — perimeter 200 × 100 mm, four 12 mm dia pockets at the quadrant centres, four 25 × 8 mm label etch zones above the pockets. Save to `~/linux-usb/citizenry/demos/emex/fixture/tray.dxf`.
3. **Send to laser-etch shop** (~3 days lead time) — perimeter cut 20 mm depth, pocket cut 12 mm depth, label etch surface only, fill etch with white acrylic paint pen on collection.
4. **Mount tray on bench** (~15 min) — clean bench surface with isopropyl, apply 4× VHB strips to tray underside, position per Section 4 layout, press for 30 seconds.
5. **Place cup with non-slip pad** (~2 min) — silicone pad first, cup centred on pad, position per Section 4 layout.
6. **Fill cup** (~5 min) — 50 of each component, mix gently with the spatula. Don't shake — springs tangle.
7. **Mount magnetic wand and spatula** (~5 min) — VHB clip on bench edge, both tools clipped at operator side.
8. **Photograph the as-built fixture** (~20 min) — overall top-down, tray close-up, cup close-up, side elevation showing arm + tray + cup, reset wand in use. Save to `~/linux-usb/citizenry/demos/emex/fixture/`.
9. **Bench-test 30 demo runs** (~30 min) — manual teleop, tray sort, reset. Confirm no fixture creep, no pocket-edge wear, no part jamming.
10. **Iterate** (~variable) — adjust cup X-position if cable run interferes, swap silicone pad for recessed tray if cup walks, re-etch labels if white-fill flakes.

Pre-flight validation (T39 Section 1, T-7 days): the home-base run is the integration test. If the fixture survives 30 minutes of dry-run there, it survives the show.

---

## 9. Photograph references

- {{PLACEHOLDER: photo TBD — Bradley to attach — overall fixture top-down on stand surface}}
- {{PLACEHOLDER: photo TBD — Bradley to attach — labelled tray close-up showing all four compartments}}
- {{PLACEHOLDER: photo TBD — Bradley to attach — workspace layout with arm + tray + cup, side elevation}}
- {{PLACEHOLDER: photo TBD — Bradley to attach — reset wand on ferrous spill}}

Take all four photos before pack-out so the fixture can be rebuilt at the venue from the photos alone if anything is damaged in transit (per plan Task 18 Step 4).

---

## 10. Compatibility check — both demo modes

Same fixture serves both demos with zero physical reconfiguration:

| Aspect | Follower-only autonomous | Leader-teleop |
|---|---|---|
| Tray position | (0, +220) mm from follower base | Same — follower is the visible arm |
| Cup position | (+180, +60) mm from follower base | Same |
| Mounting | VHB on tray, silicone pad on cup | Same |
| Reset | Manual scoop + magnetic wand | Same |
| Camera frame | Front-left, low angle (T34 block 2) | Same |
| Cable management | PSU + bus behind arm, out of frame | Same — leader's PSU and bus are at the leader bench, not in the follower-side frame |

The leader arm (operator-side bench) does not need a fixture — it's a kinaesthetic input device. Only the follower bench has the tray + cup.

---

## 11. Open follow-ups

- **T40 quantity row supersession** — T40 lists "M3 kit components: 50 of each, 2 bags". This doc specifies 250 of each across primary + spare + deep-spare. T40 should be updated to reference T18 for the canonical count, or its row updated in place. Out of scope for this doc; flag for Bradley.
- **T34 block 2 framing** — the videographer placeholders in T34 don't yet pin a camera height or angle. With the fixture spec locked, the front-left low-angle shot (described in Section 4 above) should be added to T34 as a concrete shot description.
- **Vendor SKUs** — every supplier placeholder in the frontmatter needs Bradley to pin the actual SKU before the W2/W3 procurement run.
- **Etch shop slot** — book a slot at the laser-etch shop early; lead time is the long pole on the build schedule.
- **Photos** — all four photo references are placeholders; Bradley to capture during the home-base build.

---

## Cross-references

- Plan: `docs/superpowers/plans/2026-04-27-emex-sprint-phase-0.md` Task 18 (inline notes that this doc supersedes).
- Stand setup: `docs/emex/T39-stand-setup-checklist.md`.
- Spares: `docs/emex/T40-spare-hardware-checklist.md` (foam tray + M3 component rows).
- Video: `docs/emex/T34-stand-video-script.md` block 2.
- Pack-out: `docs/emex/T48-packout-and-transport.md`.
- Calibration source-of-truth (reach envelope): `~/.cache/huggingface/lerobot/calibration/robots/so_follower/follower.json`.
