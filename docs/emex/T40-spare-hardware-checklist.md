---
task_id: T40
purpose: Packing list of spare hardware, cables, and peripherals to bring to EMEX 2026 for hot-swap and repair.
format: Categorised table with quantity, source, reason, and hot-swap target time per item.
placeholders:
  - "{{PLACEHOLDER: spare SO-101 serial number + governor-key fingerprint}}"
  - "{{PLACEHOLDER: spare Pi 5 hostname pre-flashed — e.g. pi5-arm-spare-001}}"
  - "{{PLACEHOLDER: spare XIAO hostname + WiFi SSID baked}}"
  - "{{PLACEHOLDER: 5G hotspot model + carrier + APN}}"
  - "{{PLACEHOLDER: spare SIM ICCID + carrier + plan size}}"
  - "{{PLACEHOLDER: ethernet switch model — recommend 5-port unmanaged gigabit}}"
  - "{{PLACEHOLDER: M3 component supplier + part numbers}}"
  - "{{PLACEHOLDER: foam tray supplier}}"
  - "{{PLACEHOLDER: T23 spare-hardware-kit doc — forward reference, not yet authored}}"
  - "{{PLACEHOLDER: T24 hot-swap recovery procedure doc — forward reference, not yet authored}}"
last_updated: 2026-04-29
---

# T40 — Spare hardware / cables / peripherals checklist

What goes in the spares kit. Pack so any single failure visible from the aisle is recoverable in under 10 minutes.

Hot-swap target times reference T23 (spare hardware kit) and T24 (hot-swap recovery procedure). Both forward references — neither doc is authored yet as of 2026-04-29; flag for follow-up.

---

## Robot core

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| SO-101 arm, configurable as leader OR follower | 1 | {{PLACEHOLDER: spare SO-101 serial number + governor-key fingerprint}}, pre-paired with citizen mesh | Single point of failure on Cell 2 — if either arm dies, the cell is gone without this | 8 min (per T24) |
| Pi 5 with citizenry image flashed and tested | 1 | {{PLACEHOLDER: spare Pi 5 hostname pre-flashed — e.g. pi5-arm-spare-001}}, mDNS already advertises | Manipulator citizen — if the Pi dies, Cell 2 dies | 6 min |
| XIAO ESP32S3 with WiFi credentials baked + provisioned | 1 | {{PLACEHOLDER: spare XIAO hostname + WiFi SSID baked}} | Stand-camera citizen — visible to visitors; visible failure | 4 min |

---

## Compute / display

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| Surface charger (65 W USB-C PD) | 2 | OEM | Charger failure is the most common fault on multi-day shows | 1 min |
| Surface mouse (USB or Bluetooth) | 1 | OEM | Trackpad failure under heavy demo use | 1 min |
| iPad (configured for tablet UI / approval gate) | 1 | Pre-provisioned, signed in to the approval-gate app | Cell 3 approval-gate tablet failure breaks the demo | 3 min |
| HDMI-to-USB-C adapter | 1 | Standard | Surface uses USB-C → HDMI; lose this and a monitor goes dark | 1 min |

---

## Cables

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| USB-C cable (data + 60W PD, 1 m) | 5 | Standard | Charger and Pi connections | 1 min |
| USB-A-to-USB-C cable (1 m) | 3 | Standard | Servo controllers and peripherals | 1 min |
| HDMI cable (2 m, high-speed) | 3 | Standard | Monitor runs | 1 min |
| Ethernet Cat6 (2 m) | 3 | Standard | Pi, Surface, hotspot | 1 min |
| Multi-port USB hub (powered, 4-port USB-A + USB-C) | 2 | Standard | Surface only has one of each port | 1 min |
| USB extension cable (2 m) | 2 | Standard | Reach across cell when cable runs are awkward | 1 min |

---

## Power

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| Power strip (NZ 6-outlet, 1.8 m lead) | 2 | Standard | One per cell as backup if a primary fails | 1 min |
| Laptop charger, generic 65 W USB-C PD | 2 | Standard | Backup if Surface chargers fail and OEM not on hand | 1 min |
| Surge protector (whole-stand, in-line with venue outlet) | 1 | See T39 | Must always be between venue and demo gear | n/a |
| Gaff tape (50 mm, black) | 1 roll | Standard | Cable management, trip-hazard cover | n/a |

---

## Network

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| Dedicated 5G hotspot | 1 | {{PLACEHOLDER: 5G hotspot model + carrier + APN}} | Don't trust venue WiFi; this is the primary uplink in practice | 2 min |
| Spare SIM, NZ data plan, ≥ 50 GB | 1 | {{PLACEHOLDER: spare SIM ICCID + carrier + plan size}} | Hotspot SIM corruption is rare but show-stopping | 3 min |
| Ethernet switch (5-port unmanaged gigabit) | 1 | {{PLACEHOLDER: ethernet switch model — recommend 5-port unmanaged gigabit}} | Wires the citizen mesh together over a single venue drop | 2 min |

---

## Storage

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| microSD card with citizenry image (32 GB+) | 2 | Pre-flashed, tested boot on a spare Pi | Pi storage corruption recovery | 5 min (re-flash on site) |
| USB stick with deployment artefacts (TDM dist, citizen-mcp source, governor-CLI build) | 2 | Built from current main, encrypted at rest | If the Surface needs a clean reinstall mid-show | 30 min |

---

## Demo physicals

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| Foam tray for kit-sort fixture | 1 | {{PLACEHOLDER: foam tray supplier}} | Worn or damaged tray ruins the visual | 2 min |
| M3 kit components (cap-screw + washer + lock-nut + spring), 50 of each | 2 bags | {{PLACEHOLDER: M3 component supplier + part numbers}} | Visitors will pocket parts; budget for it | n/a |
| Spare bin for sorted output | 1 | Standard | Replacement if the demo bin gets damaged | 1 min |

---

## Tools

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| Multimeter (continuity + DC volt) | 1 | Standard | Diagnose power and cable faults | n/a |
| Screwdriver kit: Phillips, flathead, T6/T8/T10 Torx, JIS for SO-101 servos | 1 | Standard | SO-101 servos take JIS specifically — Phillips will cam them out | n/a |
| Wire strippers | 1 | Standard | Field repair on chewed cable jackets | n/a |
| Electrical tape (black) | 1 roll | Standard | Quick splice insulation | n/a |
| Cable ties (assorted) | 1 bag | Standard | Cable management on stand and in transit | n/a |
| Isopropyl alcohol (90%+) + microfiber cloth | 1 | Standard | Servo contact cleaning, lens cleaning | n/a |

---

## Safety

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| First-aid kit (NZ workplace standard) | 1 | Standard | Required on stand; visitors handle moving robots | n/a |
| Hand sanitiser (250 mL pump bottle) | 2 | Standard | Operators handle visitor hands all day; one per cell | n/a |
| Safety glasses (clear) | 2 spare | Standard | Replace lost or scratched primary set | n/a |

---

## Stand-care

| Item | Quantity | Source | Reason | Hot-swap target |
|---|---|---|---|---|
| Sharpie + sticky labels | 1 set | Standard | On-the-fly cable labelling | n/a |
| Business-card stand | 1 | Standard | Front-of-stand display | n/a |
| Leave-behind topper holder (A4 portrait) | 2 | Standard | One for T35 general leave-behind, one for T43 partnership outline | n/a |

---

## What NOT to bring

No laptop carrying production keys outside `~/.citizenry/node.key` and no laptop you'd cry over losing — show floors get bumped, dropped, and occasionally stolen. No Accord-named confidential data on any device, ever; the demo runs anonymised by default and only swaps to the named version after Accord sign-off lands (target 2026-05-15). No untested gear: every item in the kit must have powered up and run through its role at least once during W2/W3 bench testing. No personal cards, USB sticks, or external drives beyond the two USB sticks listed under Storage above. No spare batteries beyond what's fitted to laptops and tablets — surplus lithium is an airline and venue compliance headache.

---

## Forward references

- **T23** — spare hardware kit doc. Lists per-citizen pairing procedure for the spare SO-101 + Pi + XIAO. {{PLACEHOLDER: T23 spare-hardware-kit doc — forward reference, not yet authored}}
- **T24** — hot-swap recovery procedure. Defines the recovery time targets above. {{PLACEHOLDER: T24 hot-swap recovery procedure doc — forward reference, not yet authored}}
