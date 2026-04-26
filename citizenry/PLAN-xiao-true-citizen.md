# Plan — XIAO ESP32S3 as a true citizen

**Goal:** Replace the Pi-side proxy (`citizenry-wifi-cam{,2}.service`) with a native Arduino-C++ implementation of the citizenry protocol on the XIAO ESP32S3 itself, so the cameras are first-class citizens that survive the Pi being offline.

**Author:** drafted 2026-04-27 after WiFi MJPEG firmware bring-up of two XIAO ESP32S3 Sense boards.

**Status:** PLAN — not started.

---

## Why

Today: XIAO → HTTP → Pi proxy → citizenry mesh. Pi outage = XIAOs disappear from the mesh. Pi has known WiFi flakiness (see `reference_pi5_access.md`). Architectural inversion: the *sensor* depends on a more failure-prone *brain*.

Native citizenry on the XIAO removes the Pi as SPOF and makes ESP32-S3 a reusable template for future non-Linux sensors (microphones, IMUs, custom boards).

## Non-goals

- Run claude-code or anything Linux-side on the XIAO. ESP32-S3 has no kernel; no shell; no filesystem in the Linux sense. The XIAO speaks the citizenry protocol; everything else (governance UI, planning) stays on Linux nodes.
- Marketplace bidding (skill-tree learning, score-based task allocation) on the XIAO. The XIAO accepts proposals if it can fulfil them; that's the whole protocol it needs.
- Multi-citizen-per-device. One XIAO = one citizen identity.

## Architecture before / after

```
TODAY                                  TARGET
─────────────────────────────          ─────────────────────────────
[XIAO] ──HTTP/MJPEG──▶ [Pi proxy]      [XIAO] ──UDP citizenry──▶ [mesh]
                          │                       │
                          ▼                       ▼
                     [citizenry mesh]       (proxy on Pi removed)

If Pi off: XIAO drops out of mesh      If Pi off: XIAO unaffected
```

## Protocol surface (what we have to implement)

Read from `protocol.py`, `transport.py`, `mdns.py`, `citizen.py` on the Surface:

### Wire layer
- **UDP multicast** `239.67.84.90:7770` — DISCOVER, HEARTBEAT, broadcast ADVERTISE
- **UDP unicast** ephemeral port — PROPOSE / ACCEPT_REJECT / REPORT / GOVERN, also unicast ADVERTISE in response to a DISCOVER
- **mDNS service** `_armos-citizen._udp.local.` with TXT properties: `type`, `pubkey` (first 16 hex chars), `caps` (comma-joined), `version`

### Identity
- Ed25519 keypair generated once, stored in NVS. Public key (hex) IS the citizen ID.
- All envelopes signed; recipients verify against sender's known pubkey.

### Envelope (JSON, signed)
```json
{
  "version": 1,
  "type": <int 1..7>,
  "sender": "<hex pubkey>",
  "recipient": "*" | "<hex pubkey>",
  "timestamp": <unix>,
  "ttl": <seconds>,
  "body": { ... },
  "signature": "<hex Ed25519>"
}
```

Signing: `sign(json.dumps(envelope_minus_signature, sort_keys=True, separators=(",",":")))`.
**Canonical JSON is a footgun** — must be byte-identical to Python's output.

### 7 message types and what we need to handle
| Type | Direction | Required for MVP? | Notes |
|---|---|---|---|
| 1 HEARTBEAT | XIAO → broadcast | YES | Every 2s, body `{state: "ok", health: 1.0}` |
| 2 DISCOVER | XIAO ← broadcast / XIAO → broadcast (on boot) | YES | Send on boot; respond with unicast ADVERTISE |
| 3 ADVERTISE | XIAO → unicast (in reply) and broadcast | YES | Body has `name`, `type`, `caps`, `unicast_port` |
| 4 PROPOSE | XIAO ← unicast | Tier 2 | Body has `task` ("frame_capture"), `task_id` |
| 5 ACCEPT_REJECT | XIAO → unicast | Tier 2 | Body has `accept: bool`, `task_id` |
| 6 REPORT | XIAO → unicast | Tier 2 | Body has `task_id`, `result`, `frame` (base64 JPEG) |
| 7 GOVERN | XIAO ← unicast (governor only) | YES (ack only) | Constitution sync; we just acknowledge for v1 |

## Library choices

| Need | Library | Why |
|---|---|---|
| WiFi STA | `WiFi.h` | bundled in arduino-esp32 |
| UDP unicast | `WiFiUdp.h` | bundled |
| **UDP multicast** | `lwip` directly via `igmp_joingroup()` + raw socket | Arduino's `WiFiUdp.beginMulticast()` works on most ESP32s; verify at MVP |
| mDNS service register | `ESPmDNS.h` (`MDNS.addService("_armos-citizen", "_udp", port); MDNS.addServiceTxt(...)`) | bundled |
| JSON | `ArduinoJson` v7+ | de facto Arduino JSON |
| **Canonical JSON for signing** | hand-written serializer with sorted keys + tight separators | ArduinoJson doesn't sort keys; if we use it for serialization we'll diverge from Python. Dedicated function `signable_bytes()` that matches Python byte-for-byte |
| Ed25519 sign / verify | `rweather/Crypto` (`Ed25519.h`) | pure-C, audited, works on ESP32 — ~5 KB code |
| Persistent keypair | `Preferences.h` | NVS-backed, bundled |
| OV2640 camera | `esp_camera` | already integrated in current firmware |

## Phased implementation

### Phase 0 — Skeleton (~2 hours)
- New sketch `xiao-citizen/xiao-citizen.ino` derived from current CameraWebServer
- WiFi connect + mDNS register with citizenry TXT props
- Preferences-backed Ed25519 keypair load-or-generate
- UDP multicast bind on `239.67.84.90:7770`
- UDP unicast bind on ephemeral port
- Canonical JSON serializer + signer + verifier (small, ~80 LOC)
- **Acceptance:** Surface governor's mDNS browser sees `xiao-cam-001` as a citizen via `_armos-citizen._udp.local.`. No envelopes flowing yet.

### Phase 1 — MVP citizen (~1 day on top of Phase 0)
- Send DISCOVER on boot
- Send HEARTBEAT every 2 s
- Respond to DISCOVER with unicast ADVERTISE
- Receive + verify HEARTBEAT / DISCOVER from neighbors → maintain neighbor table
- Receive + ack GOVERN (constitution) from governor — reply with REPORT `{ack: true}`
- **Acceptance:** Surface governor logs `NEW NEIGHBOR: xiao-cam-001` and successfully exchanges constitution. Heartbeats keep `xiao-cam-001` alive without DEGRADED→DEAD cycling. Pi proxy can be **stopped** for this XIAO at this point.

### Phase 2 — Frame capture (~half day on top of Phase 1)
- Receive PROPOSE — parse `body.task`
  - if `task == "frame_capture"`:
    - Send ACCEPT_REJECT `{accept: true, task_id: ...}`
    - Capture JPEG via `esp_camera_fb_get()`
    - Base64-encode + send REPORT `{task_id, result: "success", frame: "<b64>"}` to proposer
    - Free fb
  - else: ACCEPT_REJECT `{accept: false, reason: "unsupported"}`
- **Acceptance:** From Surface, sending a PROPOSE for frame_capture to xiao-cam-001 returns a valid JPEG via REPORT in <500ms.

### Phase 3 — Polish (~half day)
- Replay-attack protection (drop envelopes with old timestamps)
- Neighbor table TTL eviction (DEGRADED at 3 missed heartbeats, DEAD at 10)
- Memory-bounded queues (don't OOM on flood)
- Watchdog: if WiFi drops > 30s, reboot
- TXT-record updates on capability change (e.g. PSRAM full)
- **Acceptance:** XIAO survives 24h soak; Surface log shows clean BACK/DEGRADED transitions when WiFi flickers.

## Code budget

Rough LOC estimate broken down:
- WiFi + mDNS bootstrap: ~80 LOC
- UDP multicast + unicast wrappers: ~120 LOC
- Canonical JSON serializer + Ed25519 wrappers: ~150 LOC
- Citizen state machine + neighbor table: ~200 LOC
- Message handlers (7 types): ~250 LOC
- Camera frame proposal handler: ~80 LOC
- **Total**: ~880 LOC of Arduino C++ (≈ a long week-end of focused work for someone fluent)

Flash impact: +50 KB (ArduinoJson + Crypto + custom code).

## Library install commands

```bash
# On the Pi (where arduino-cli lives)
arduino-cli lib install "ArduinoJson"
arduino-cli lib install "Crypto"  # rweather/Crypto, includes Ed25519
```

## Testing strategy

### Unit-style on host (no XIAO needed)
- Implement `signable_bytes()` in C and compare byte-for-byte against Python's output for a fixed input. **This is the gating test** — if signatures don't match the Python format, nothing will work.
- Pre-compute a few signed envelopes in Python; verify them with the C++ Ed25519 code; confirm tampered envelopes fail.

### Integration on a single XIAO + Surface
- Phase 0 acceptance: mDNS visible
- Phase 1 acceptance: heartbeat keeps neighbor alive for 5 minutes without DEGRADED
- Phase 2 acceptance: scripted Python client sends PROPOSE → receives REPORT with valid JPEG

### Pre-flight before deploying to the second XIAO
- Confirm hostname/identity collision-safe: each XIAO regenerates keypair on first boot, uses `xiao-cam-NNN` hostname from a unique-per-board MAC-derived suffix or a hardcoded `#define CITIZEN_NAME`.

## Risks and mitigations

| Risk | Probability | Mitigation |
|---|---|---|
| Canonical JSON drift between Python and C++ | High | Round-trip test from day 0; Python and C++ both produce signed envelopes that the other can verify |
| ArduinoJson v7 API differences from older tutorials | Medium | Pin to a specific ArduinoJson version in the sketch's `#include` and document |
| `WiFiUdp.beginMulticast()` doesn't actually join the multicast group on ESP32-S3 | Medium | Drop to lwip raw socket via `igmp_joingroup()` if Arduino layer fails |
| Ed25519 key generation slow at first boot | Low | Generate once and persist; only first boot is slow (~1 s) |
| `Preferences` NVS corruption | Low | Catch exceptions on load; regenerate if missing/invalid |
| ESP32-S3 WiFi stack drops UDP packets under load | Medium | Heartbeat + neighbor TTL handles transient losses |
| Camera + WiFi on same SoC contend for resources | Medium | Already proven OK in CameraWebServer firmware; same RAM/PSRAM usage profile |
| Regression in Python protocol breaks XIAO compatibility silently | High (long-term) | Bump `PROTOCOL_VERSION`; XIAO refuses envelopes from a higher major version; XIAO's TXT advertises its version |

## Open questions to resolve before coding

1. **Identity persistence on factory reset**: should holding a button at boot regen the keypair, or do we leave it write-once?
2. **Citizen name**: hardcode `xiao-cam-001` per build (one binary per XIAO) or derive from MAC suffix (one binary, multiple XIAOs)? — recommend **derive from MAC**, e.g. `xiao-cam-` + last 4 hex of MAC. Saves having two firmware builds.
3. **Constitution storage**: do we persist the received constitution in NVS, or fetch fresh on every boot? — recommend **persist** to keep behavior stable across governor outages.
4. **OTA updates**: Arduino-ESP32 supports HTTPS OTA. Worth implementing day-1 so we don't have to physically reach the XIAOs every time we patch the protocol code? — **yes, add to Phase 3**.
5. **Broadcast vs multicast**: Bradley-Starlink router multicast handling unverified. May need to fall back to UDP broadcast on `255.255.255.255` if multicast fails on the LAN.

## Definition of "done"

For the **whole project**:
- Both XIAOs run native firmware, no Pi-side proxies.
- Surface governor sees both as direct neighbors with valid signatures.
- Killing `citizenry-pi.service` does NOT remove the XIAOs from the swarm.
- Surface can request a frame_capture from a XIAO and get a JPEG back via citizenry protocol (not HTTP).
- 24-hour soak with no manual intervention.
- This plan document updated to reflect what we actually built (gotchas, real LOC, real timings).

## Suggested next session shape

A clean ~2-day session focused only on this:
- **Day 1 morning**: Phase 0 (skeleton) — get to "appears in mDNS" milestone.
- **Day 1 afternoon**: round-trip signature interop test before going further. If Python and C++ can't agree on canonical JSON yet, fix that and stop.
- **Day 2 morning**: Phase 1 (heartbeat + advertise + govern ack).
- **Day 2 afternoon**: Phase 2 (frame_capture).

Phase 3 polish lives in a separate later session.

## Out of scope for this plan (but worth tracking elsewhere)

- Generalize the `xiao-citizen` template into an "armos-arduino" library that any ESP32-family board can include.
- Add an audio capture citizen (XIAO ESP32S3 Sense has a microphone we haven't used).
- Cross-LAN federation when the country grows beyond one WiFi.
