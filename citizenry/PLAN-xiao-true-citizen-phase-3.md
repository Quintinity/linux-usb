# XIAO True-Citizen Phase 3 Implementation Plan — Frame Capture

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add native camera frame capture to the XIAO citizenry firmware so it can serve `frame_capture` PROPOSEs end-to-end (`PROPOSE → ACCEPT_REJECT → REPORT { frame: <base64 JPEG>, width, height }`) — byte-compatible with the existing Pi-side `CameraCitizen` proxy. Once verified live, the Pi-side proxy `citizenry-wifi-cam.service` becomes redundant and can be decommissioned.

**Architecture:** Reuse the OV2640 capture pipeline already wired in `app_httpd.cpp` (`esp_camera_fb_get / esp_camera_fb_return`). The native JPEG output of the sensor (no recompression) is base64-encoded into a REPORT envelope addressed to the proposer. A camera-access mutex serializes the existing HTTP `/capture` endpoint and the new citizenry path so they don't both grab the same frame buffer. Reply transport falls back to multicast for now (same Phase 4 caveat as ADVERTISE / GOVERN ack — recipient pubkey filtering keeps it correct, just noisier); a Phase 4 task will pipe transport-layer source IP through `InboundEnvelope` and switch this to unicast.

**Tech Stack:** Arduino-ESP32 core 3.3.8, esp_camera (OV2640 in `PIXFORMAT_JPEG`), ArduinoJson v7, rweather/Crypto, FreeRTOS mutex (`SemaphoreHandle_t`). Host tests in g++ exercising the builders + dispatcher dispatch. Live tests in Python from the Surface using the Phase 2 `phase2_live_test.py` pattern.

---

## What changed from v2 plan

The Phase 1–2 portions of `PLAN-xiao-true-citizen-v2.md` shipped on `main` as of 2026-04-27. v2 lists Phase 3 as a single coarse phase ("Frame capture: PROPOSE → REPORT"); this document is the executable expansion of that phase using the same TDD-flavored task layout that worked for Phases 0–2. Nothing in v2 is invalidated; this is the next layer.

Phase 4 issues recorded in the merge commit (`docs/superpowers/plans/...` / merge commit on `main`) are explicitly **not** in scope here:

- timestamps remain seconds-since-boot (no SNTP)
- ADVERTISE / GOVERN ack stay multicast (no source-IP plumbing through `InboundEnvelope`)
- merged.bin reflash still wipes NVS

Phase 3 inherits all three caveats. The plan calls them out in-place where they show up.

---

## File structure

```
linux-usb/
├── citizenry/                                          (Python, mostly unchanged)
│   └── tests/
│       └── test_xiao_frame_capture.py                  ← NEW: gold-master fixtures for frame_capture wire shape
│
└── xiao-citizen/                                       (firmware)
    ├── xiao-citizen.ino                                ← MODIFIED: camera init in setup(); PROPOSE route in dispatcher
    ├── citizenry_camera.h / .cpp                       ← NEW: thin wrapper over esp_camera with mutex'd capture
    ├── citizenry_messages.h / .cpp                     ← MODIFIED: build_accept, build_reject, build_report_frame
    ├── tests/
    │   ├── test_messages.cpp                           ← MODIFIED: assertions for the three new builders
    │   ├── live/
    │   │   └── phase3_live_test.py                     ← NEW: end-to-end frame-capture verification harness
    │   └── ...
    └── app_httpd.cpp                                   ← MODIFIED: wrap esp_camera_fb_get with the shared mutex
```

**Why this layout:** `citizenry_camera.{h,cpp}` is the new responsibility (camera lifecycle + mutexed capture). `citizenry_messages.cpp` already owns "wire builder + small handler" — `build_accept` / `build_reject` / `build_report_frame_capture` belong with their cousins. The `app_httpd.cpp` change is a one-line wrap to share the same mutex; we leave the rest of the legacy CameraWebServer code untouched.

---

## Phase 3 success criteria

A Surface-driven test harness sends a signed PROPOSE `{task: "frame_capture", task_id: "..."}` to `xiao-cam-0000.local`. Within 2 s the XIAO replies with:

1. an ACCEPT_REJECT envelope (type 5, `body: {result: "accept", task_id: ...}`), and
2. a REPORT envelope (type 6, `body: {type: "frame_capture", task_id: <echoed>, frame: <base64 JPEG bytes that decode to a non-empty JPEG with valid SOI/EOI markers>, width: 320, height: 240}`).

Both envelopes verify under the XIAO's pubkey; both have the proposer's pubkey as `recipient`. The harness saves the decoded JPEG and prints its size; size > 5 KB and < 30 KB confirms a real frame from the OV2640. A second consecutive PROPOSE returns a fresh frame (timestamp differs). The legacy HTTP `GET /capture` endpoint still serves a JPEG concurrently with citizenry traffic without crashing.

Hardware verification gate: this must be observed live on `xiao-cam-0000` (192.168.1.83) before Phase 3 is considered shipped. Compile-only is **not** sufficient — the camera path is hardware-dependent.

---

## Phase 3 — Task list

### Task 3.0: Pull camera init out of app_httpd into a shared module

`app_httpd.cpp` currently has `esp_camera_init()` calls inline plus per-handler `esp_camera_fb_get` / `esp_camera_fb_return`. We need a shared init that the citizenry path also uses, plus a mutex so two consumers can't grab the FB at once.

**Files:**
- Create: `xiao-citizen/citizenry_camera.h`
- Create: `xiao-citizen/citizenry_camera.cpp`
- Modify: `xiao-citizen/app_httpd.cpp` (one line: replace direct `esp_camera_fb_get` with the wrapper)
- Modify: `xiao-citizen/xiao-citizen.ino` (call `citizenry_camera_begin()` in setup before `WiFi.begin`)

- [ ] **Step 1: Sketch the API in the header**

```cpp
// xiao-citizen/citizenry_camera.h
#pragma once
#ifndef ARDUINO_HOST_TEST   // hardware-only; host tests skip the camera path entirely

#include "esp_camera.h"

// Initialise the OV2640 with a Phase 3 sensible default (QVGA, JPEG, q=12).
// Returns true on success. Idempotent — second call is a no-op.
bool citizenry_camera_begin();

// Mutex'd grab; release with citizenry_camera_release(fb). Returns NULL on
// timeout or hardware error. Caller MUST balance with release. Timeout in ms.
camera_fb_t* citizenry_camera_grab(uint32_t timeout_ms = 1000);
void         citizenry_camera_release(camera_fb_t* fb);

// Cheap accessors for the configured sensor — used by build_report_frame_capture
// to fill width/height without re-reading the FB metadata.
uint16_t citizenry_camera_width();
uint16_t citizenry_camera_height();

#endif // !ARDUINO_HOST_TEST
```

- [ ] **Step 2: Implement camera_begin + the mutex**

```cpp
// xiao-citizen/citizenry_camera.cpp
#ifndef ARDUINO_HOST_TEST
#include "citizenry_camera.h"
#include "board_config.h"
#include "camera_pins.h"
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <Arduino.h>

static SemaphoreHandle_t s_camera_mtx = nullptr;
static bool              s_inited     = false;
static uint16_t          s_width      = 320;
static uint16_t          s_height     = 240;

bool citizenry_camera_begin() {
    if (s_inited) return true;
    if (!s_camera_mtx) s_camera_mtx = xSemaphoreCreateMutex();

    camera_config_t cfg = {};
    cfg.ledc_channel = LEDC_CHANNEL_0;
    cfg.ledc_timer   = LEDC_TIMER_0;
    cfg.pin_d0       = Y2_GPIO_NUM;
    cfg.pin_d1       = Y3_GPIO_NUM;
    cfg.pin_d2       = Y4_GPIO_NUM;
    cfg.pin_d3       = Y5_GPIO_NUM;
    cfg.pin_d4       = Y6_GPIO_NUM;
    cfg.pin_d5       = Y7_GPIO_NUM;
    cfg.pin_d6       = Y8_GPIO_NUM;
    cfg.pin_d7       = Y9_GPIO_NUM;
    cfg.pin_xclk     = XCLK_GPIO_NUM;
    cfg.pin_pclk     = PCLK_GPIO_NUM;
    cfg.pin_vsync    = VSYNC_GPIO_NUM;
    cfg.pin_href     = HREF_GPIO_NUM;
    cfg.pin_sccb_sda = SIOD_GPIO_NUM;
    cfg.pin_sccb_scl = SIOC_GPIO_NUM;
    cfg.pin_pwdn     = PWDN_GPIO_NUM;
    cfg.pin_reset    = RESET_GPIO_NUM;
    cfg.xclk_freq_hz = 20'000'000;
    cfg.frame_size   = FRAMESIZE_QVGA;
    cfg.pixel_format = PIXFORMAT_JPEG;
    cfg.grab_mode    = CAMERA_GRAB_LATEST;
    cfg.fb_location  = CAMERA_FB_IN_PSRAM;
    cfg.jpeg_quality = 12;
    cfg.fb_count     = 2;

    if (esp_camera_init(&cfg) != ESP_OK) return false;
    s_width  = 320;
    s_height = 240;
    s_inited = true;
    return true;
}

camera_fb_t* citizenry_camera_grab(uint32_t timeout_ms) {
    if (!s_inited) return nullptr;
    if (xSemaphoreTake(s_camera_mtx, pdMS_TO_TICKS(timeout_ms)) != pdTRUE) return nullptr;
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        xSemaphoreGive(s_camera_mtx);
        return nullptr;
    }
    return fb;  // mutex held until release
}

void citizenry_camera_release(camera_fb_t* fb) {
    if (fb) esp_camera_fb_return(fb);
    if (s_camera_mtx) xSemaphoreGive(s_camera_mtx);
}

uint16_t citizenry_camera_width()  { return s_width; }
uint16_t citizenry_camera_height() { return s_height; }
#endif
```

- [ ] **Step 3: Replace the existing camera init in the sketch**

Read `xiao-citizen/xiao-citizen.ino` first — Phase 1 may already do `esp_camera_init` for the legacy HTTP path. If so, *delete* it; `citizenry_camera_begin()` is now the sole owner. Add the new call right after WiFi connects:

```cpp
if (!citizenry_camera_begin()) {
    Serial.println("camera_begin FAILED");
    // fall through; live without camera. PROPOSE handlers will REJECT.
}
```

- [ ] **Step 4: Patch app_httpd.cpp to use the mutex'd path**

Find each `esp_camera_fb_get()` / `esp_camera_fb_return(fb)` pair in `app_httpd.cpp` and replace with `citizenry_camera_grab()` / `citizenry_camera_release(fb)`. Three call sites by `grep -nE "esp_camera_fb_(get|return)" app_httpd.cpp`. NULL-check semantics are unchanged.

- [ ] **Step 5: Pi compile + commit**

```bash
scp xiao-citizen/citizenry_camera.{h,cpp} xiao-citizen/xiao-citizen.ino xiao-citizen/app_httpd.cpp \
    bradley@raspberry-lerobot-001.local:~/xiao-citizen-build/xiao-citizen/
ssh bradley@raspberry-lerobot-001.local 'cd ~/xiao-citizen-build/xiao-citizen && rm -rf build && \
    arduino-cli compile --fqbn "esp32:esp32:XIAO_ESP32S3:PSRAM=opi,USBMode=default,CDCOnBoot=default,UploadSpeed=921600,FlashSize=8M,FlashMode=qio,PartitionScheme=default_8MB" \
    --build-path ./build . 2>&1 | tail -3'
```

Expected: program % rises by ~2–3 KB; SRAM essentially unchanged.

```bash
git add xiao-citizen/citizenry_camera.h xiao-citizen/citizenry_camera.cpp \
        xiao-citizen/xiao-citizen.ino xiao-citizen/app_httpd.cpp
git commit -m "xiao-citizen: shared mutexed camera wrapper for citizenry + http /capture (Task 3.0)"
```

---

### Task 3.1: build_accept / build_reject helpers (ACCEPT_REJECT, type 5)

The Pi-side `CameraCitizen.send_accept` and `send_reject` produce `type=5` envelopes whose body shape we mirror. Pure-logic builders, host-testable.

**Files:**
- Modify: `xiao-citizen/citizenry_messages.h`
- Modify: `xiao-citizen/citizenry_messages.cpp`
- Modify: `xiao-citizen/tests/test_messages.cpp`

- [ ] **Step 1: Write failing tests for build_accept and build_reject**

Add to `tests/test_messages.cpp` after the existing message-builder tests:

```cpp
// ---- 8. build_accept ----
{
    Identity id; id.generate();
    std::string proposer = "deadbeef".repeat(8); // 64-char hex placeholder
    std::string accept = build_accept(id, proposer, "frame_capture",
                                      /*task_id=*/"abc-123",
                                      /*now=*/123.456);
    auto m = parse_inbound(accept);
    check("accept type=5", m.type == MsgType::ACCEPT_REJECT);
    check("accept recipient is proposer", m.recipient == proposer);
    check("accept body.result", m.body_get_string("result") == "accept");
    check("accept body.task", m.body_get_string("task") == "frame_capture");
    check("accept body.task_id", m.body_get_string("task_id") == "abc-123");
    check("accept signature verifies",
          verify_envelope_bytes(accept, id.pubkey_hex()));
}

// ---- 9. build_reject ----
{
    Identity id; id.generate();
    std::string proposer = "feedface".repeat(8);
    std::string reject = build_reject(id, proposer,
                                      /*reason=*/"camera not available",
                                      /*now=*/200.0);
    auto m = parse_inbound(reject);
    check("reject type=5", m.type == MsgType::ACCEPT_REJECT);
    check("reject body.result", m.body_get_string("result") == "reject");
    check("reject body.reason", m.body_get_string("reason") == "camera not available");
    check("reject signature verifies",
          verify_envelope_bytes(reject, id.pubkey_hex()));
}
```

(Use whatever helper names are actually in test_messages.cpp — read it before writing. The pattern above mirrors the dispatcher tests.)

Run: `cd xiao-citizen/tests && make test_messages && ./test_messages`

Expected: compile error (build_accept / build_reject undefined).

- [ ] **Step 2: Add the declarations**

```cpp
// in citizenry_messages.h, after build_advertise

// 3.1: ACCEPT_REJECT (unicast). Body: {result:"accept", task, task_id}.
std::string build_accept(const Identity& id,
                         const std::string& proposer_pubkey_hex,
                         const std::string& task,
                         const std::string& task_id,
                         double now_unix_secs);

// 3.1: ACCEPT_REJECT (unicast). Body: {result:"reject", reason}.
std::string build_reject(const Identity& id,
                         const std::string& proposer_pubkey_hex,
                         const std::string& reason,
                         double now_unix_secs);
```

- [ ] **Step 3: Implement them**

In `citizenry_messages.cpp`, copy the `build_advertise` pattern. Add `TTL_ACCEPT_REJECT = 10.0` (mirrors `TTL_ACCEPT_REJECT` in `citizenry/protocol.py`). Both build a JsonDocument, set the body, sign via `Identity::sign_hex`, serialize via the canonical-JSON path.

```cpp
constexpr double TTL_ACCEPT_REJECT = 10.0;

std::string build_accept(const Identity& id,
                         const std::string& proposer_pubkey_hex,
                         const std::string& task,
                         const std::string& task_id,
                         double now_unix_secs) {
    JsonDocument body;
    body["result"]  = "accept";
    body["task"]    = task;
    body["task_id"] = task_id;
    return make_signed_envelope(id, MsgType::ACCEPT_REJECT,
                                proposer_pubkey_hex,
                                now_unix_secs, TTL_ACCEPT_REJECT, body);
}

std::string build_reject(const Identity& id,
                         const std::string& proposer_pubkey_hex,
                         const std::string& reason,
                         double now_unix_secs) {
    JsonDocument body;
    body["result"] = "reject";
    body["reason"] = reason;
    return make_signed_envelope(id, MsgType::ACCEPT_REJECT,
                                proposer_pubkey_hex,
                                now_unix_secs, TTL_ACCEPT_REJECT, body);
}
```

(`make_signed_envelope` is the existing helper used by `build_advertise` etc.; if it's named something else in the file, use that.)

- [ ] **Step 4: Run tests + commit**

```bash
cd xiao-citizen/tests && make clean && make run | grep -E "===|passed|FAIL"
```

Expected: 4 new assertions passed in `test_messages`, total moves from 85 → 89.

```bash
git add xiao-citizen/citizenry_messages.{h,cpp} xiao-citizen/tests/test_messages.cpp
git commit -m "xiao-citizen: build_accept / build_reject (ACCEPT_REJECT type 5) (Task 3.1)"
```

---

### Task 3.2: build_report_frame_capture + base64 encoder

The big one for memory. We're building a REPORT envelope with a base64'd JPEG in the body.

**Files:**
- Modify: `xiao-citizen/citizenry_messages.h`
- Modify: `xiao-citizen/citizenry_messages.cpp`
- Modify: `xiao-citizen/tests/test_messages.cpp`

- [ ] **Step 1: Write a failing test for the wire shape**

```cpp
// ---- 10. build_report_frame_capture ----
{
    Identity id; id.generate();
    std::string proposer = "abad1dea".repeat(8);
    // Synthetic 6-byte "JPEG" payload — content opaque to the builder
    uint8_t fake_jpg[] = {0xff, 0xd8, 0xff, 0xe0, 0xff, 0xd9};
    std::string rep = build_report_frame_capture(
        id, proposer,
        /*task_id=*/"task-1",
        fake_jpg, sizeof(fake_jpg),
        /*width=*/320, /*height=*/240,
        /*now=*/77.0);
    auto m = parse_inbound(rep);
    check("frame report type=6", m.type == MsgType::REPORT);
    check("frame report recipient", m.recipient == proposer);
    check("frame report body.type", m.body_get_string("type") == "frame_capture");
    check("frame report body.task_id", m.body_get_string("task_id") == "task-1");
    check("frame report body.width", m.body_get_int("width") == 320);
    check("frame report body.height", m.body_get_int("height") == 240);
    // base64 of {0xff,0xd8,0xff,0xe0,0xff,0xd9} = "/9j/4P/Z"
    check("frame report body.frame is base64 of input",
          m.body_get_string("frame") == "/9j/4P/Z");
    check("frame report sig verifies",
          verify_envelope_bytes(rep, id.pubkey_hex()));
}
```

Run, expect compile fail.

- [ ] **Step 2: Add a tiny base64 encoder**

Add to `citizenry_messages.cpp` (file-local — no need to expose). Use the standard alphabet, no padding-stripping; decoder side is the Python harness which uses `base64.b64decode` and accepts canonical padding.

```cpp
namespace {
constexpr char B64_ALPHABET[] =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

std::string b64_encode(const uint8_t* data, size_t len) {
    std::string out;
    out.reserve(((len + 2) / 3) * 4);
    size_t i = 0;
    for (; i + 2 < len; i += 3) {
        uint32_t v = (data[i] << 16) | (data[i+1] << 8) | data[i+2];
        out.push_back(B64_ALPHABET[(v >> 18) & 0x3f]);
        out.push_back(B64_ALPHABET[(v >> 12) & 0x3f]);
        out.push_back(B64_ALPHABET[(v >>  6) & 0x3f]);
        out.push_back(B64_ALPHABET[ v        & 0x3f]);
    }
    if (i < len) {
        uint32_t v = data[i] << 16;
        if (i + 1 < len) v |= data[i+1] << 8;
        out.push_back(B64_ALPHABET[(v >> 18) & 0x3f]);
        out.push_back(B64_ALPHABET[(v >> 12) & 0x3f]);
        out.push_back(i + 1 < len ? B64_ALPHABET[(v >> 6) & 0x3f] : '=');
        out.push_back('=');
    }
    return out;
}
}
```

- [ ] **Step 3: Implement build_report_frame_capture**

```cpp
// in citizenry_messages.h
std::string build_report_frame_capture(const Identity& id,
                                       const std::string& proposer_pubkey_hex,
                                       const std::string& task_id,
                                       const uint8_t* jpeg_buf,
                                       size_t jpeg_len,
                                       uint16_t width,
                                       uint16_t height,
                                       double now_unix_secs);
```

```cpp
// in citizenry_messages.cpp
std::string build_report_frame_capture(const Identity& id,
                                       const std::string& proposer_pubkey_hex,
                                       const std::string& task_id,
                                       const uint8_t* jpeg_buf,
                                       size_t jpeg_len,
                                       uint16_t width,
                                       uint16_t height,
                                       double now_unix_secs) {
    JsonDocument body;
    body["type"]      = "frame_capture";
    body["task_id"]   = task_id;
    body["frame"]     = b64_encode(jpeg_buf, jpeg_len);
    body["width"]     = width;
    body["height"]    = height;
    body["timestamp"] = now_unix_secs;   // Python schema includes this; XIAO has no RTC, so it's seconds-since-boot
    return make_signed_envelope(id, MsgType::REPORT,
                                proposer_pubkey_hex,
                                now_unix_secs, TTL_REPORT, body);
}
```

JsonDocument is small-buffer-optimised; with a ~20 KB base64 payload it'll spill to heap. That's fine — ESP32-S3 has 245 KB free heap per the Phase 2 compile output. If memory allocation fails on hardware (unlikely), the call returns an empty string and the dispatcher converts that into a REJECT.

- [ ] **Step 4: Run tests + commit**

```bash
cd xiao-citizen/tests && make clean && make run | grep -E "===|passed|FAIL"
```

Expected: total assertions 89 → 97 (8 new for build_report_frame_capture).

```bash
git add xiao-citizen/citizenry_messages.{h,cpp} xiao-citizen/tests/test_messages.cpp
git commit -m "xiao-citizen: build_report_frame_capture + b64 encoder (Task 3.2)"
```

---

### Task 3.3: handle_propose for task=="frame_capture"

The pure-logic dispatcher hook that ties Tasks 3.0–3.2 together. Same `handle_govern` shape: takes inbound + identity + camera handle, returns wire bytes for the ACCEPT and the REPORT (or just a REJECT). Hardware-coupled at the camera-grab call, so we split the logic into a host-testable helper.

**Files:**
- Modify: `xiao-citizen/citizenry_messages.h`
- Modify: `xiao-citizen/citizenry_messages.cpp`
- Modify: `xiao-citizen/tests/test_messages.cpp`

- [ ] **Step 1: Define a CameraSource interface**

Same trick as `ConstitutionStore` — abstract the hardware behind a 2-method virtual class so host tests can use a fake.

```cpp
// in citizenry_messages.h
class CameraSource {
public:
    virtual ~CameraSource() = default;
    // Returns true on success. Caller takes ownership of the data via the
    // CameraSource's own buffer — must call release() after use.
    virtual bool grab(const uint8_t** out_buf, size_t* out_len,
                      uint16_t* out_w, uint16_t* out_h) = 0;
    virtual void release() = 0;
    virtual bool ready() const = 0;
};

// 3.3: PROPOSE handler for frame_capture. Returns vector of envelope wire
// bytes to emit, in order. Empty on shape rejection. Always emits ACCEPT or
// REJECT first, then (on accept + successful capture) the REPORT.
struct FrameCaptureTarget {
    std::string proposer_pubkey_hex;
    uint16_t    reply_port = 0;
    std::string task_id;
};
std::vector<std::string>
handle_propose_frame_capture(const InboundEnvelope& m,
                             const Identity& id,
                             CameraSource& cam,
                             uint16_t fallback_reply_port,
                             double now_unix_secs,
                             FrameCaptureTarget& out);
```

- [ ] **Step 2: Failing host test using a stub CameraSource**

```cpp
// ---- 11. handle_propose_frame_capture happy path ----
{
    class FakeCam : public CameraSource {
    public:
        bool grab(const uint8_t** b, size_t* l, uint16_t* w, uint16_t* h) override {
            static const uint8_t fake[] = {0xff,0xd8,0x01,0x02,0xff,0xd9};
            *b = fake; *l = sizeof(fake); *w = 320; *h = 240;
            _grabbed = true;
            return true;
        }
        void release() override { _released = true; }
        bool ready() const override { return true; }
        bool _grabbed = false, _released = false;
    } cam;

    Identity id; id.generate();
    Identity proposer; proposer.generate();
    auto inbound = make_propose(proposer, "frame_capture", "task-7", id.pubkey_hex(), 100.0);
    auto m = parse_inbound(inbound);

    FrameCaptureTarget tgt;
    auto out = handle_propose_frame_capture(m, id, cam, /*fallback*/0, /*now*/100.5, tgt);

    check("two envelopes returned", out.size() == 2);
    auto a = parse_inbound(out[0]);
    check("first is ACCEPT_REJECT", a.type == MsgType::ACCEPT_REJECT);
    check("first body.result=accept", a.body_get_string("result") == "accept");
    auto r = parse_inbound(out[1]);
    check("second is REPORT", r.type == MsgType::REPORT);
    check("second body.type=frame_capture", r.body_get_string("type") == "frame_capture");
    check("second body.task_id echoed", r.body_get_string("task_id") == "task-7");
    check("camera grabbed", cam._grabbed);
    check("camera released", cam._released);
    check("target task_id", tgt.task_id == "task-7");
    check("target proposer", tgt.proposer_pubkey_hex == proposer.pubkey_hex());
}

// ---- 12. handle_propose rejects when camera unready ----
{
    class DeadCam : public CameraSource {
    public:
        bool grab(const uint8_t**, size_t*, uint16_t*, uint16_t*) override { return false; }
        void release() override {}
        bool ready() const override { return false; }
    } cam;
    Identity id; id.generate();
    Identity proposer; proposer.generate();
    auto inbound = make_propose(proposer, "frame_capture", "task-x", id.pubkey_hex(), 100.0);
    auto m = parse_inbound(inbound);
    FrameCaptureTarget tgt;
    auto out = handle_propose_frame_capture(m, id, cam, 0, 100.5, tgt);
    check("one envelope returned", out.size() == 1);
    auto a = parse_inbound(out[0]);
    check("only is reject", a.body_get_string("result") == "reject");
    check("reason mentions camera", a.body_get_string("reason").find("camera") != std::string::npos);
}

// ---- 13. handle_propose rejects unknown task ----
{
    class UnusedCam : public CameraSource {
    public:
        bool grab(const uint8_t**, size_t*, uint16_t*, uint16_t*) override { return false; }
        void release() override {}
        bool ready() const override { return true; }
    } cam;
    Identity id; id.generate();
    Identity proposer; proposer.generate();
    auto inbound = make_propose(proposer, "wash_the_dishes", "task-y", id.pubkey_hex(), 100.0);
    auto m = parse_inbound(inbound);
    FrameCaptureTarget tgt;
    auto out = handle_propose_frame_capture(m, id, cam, 0, 100.5, tgt);
    check("one reject", out.size() == 1);
    auto a = parse_inbound(out[0]);
    check("rejected", a.body_get_string("result") == "reject");
    check("reason names task",
          a.body_get_string("reason").find("wash_the_dishes") != std::string::npos);
}
```

`make_propose` is a host test helper that builds a signed PROPOSE — add it next to the existing `make_inbound_*` helpers in the test file (or its `_helpers.h`). Pattern is identical to other helpers; just `make_envelope(MsgType::PROPOSE, ...)`.

Run, expect compile fail.

- [ ] **Step 3: Implement handle_propose_frame_capture**

```cpp
std::vector<std::string>
handle_propose_frame_capture(const InboundEnvelope& m,
                             const Identity& id,
                             CameraSource& cam,
                             uint16_t fallback_reply_port,
                             double now_unix_secs,
                             FrameCaptureTarget& out) {
    std::vector<std::string> result;
    if (m.type != MsgType::PROPOSE) return result;

    std::string task    = m.body_get_string("task");
    std::string task_id = m.body_get_string("task_id");
    out.proposer_pubkey_hex = m.sender;
    out.reply_port          = fallback_reply_port; // dispatcher doesn't pipe source port yet (Phase 4)
    out.task_id             = task_id;

    if (task != "frame_capture") {
        result.push_back(build_reject(id, m.sender,
                                      "unknown task: " + task, now_unix_secs));
        return result;
    }
    if (!cam.ready()) {
        result.push_back(build_reject(id, m.sender,
                                      "camera not available", now_unix_secs));
        return result;
    }

    // ACCEPT first so the proposer knows we're committed even if the capture
    // takes >1 s.
    result.push_back(build_accept(id, m.sender, "frame_capture", task_id, now_unix_secs));

    const uint8_t* buf = nullptr; size_t len = 0;
    uint16_t w = 0, h = 0;
    bool ok = cam.grab(&buf, &len, &w, &h);
    if (!ok) {
        // Replace the ACCEPT with a REJECT — the capture failed AFTER we said yes.
        // Better contract: keep the ACCEPT (we did try) and emit a task_complete
        // REPORT with result:"failed". Easier on the proposer's state machine.
        // Build a minimal "failure" REPORT here.
        JsonDocument body;
        body["type"]    = "task_complete";
        body["task_id"] = task_id;
        body["result"]  = "failed";
        body["reason"]  = "frame capture failed";
        result.push_back(make_signed_envelope(id, MsgType::REPORT, m.sender,
                                              now_unix_secs, TTL_REPORT, body));
        cam.release();
        return result;
    }
    result.push_back(build_report_frame_capture(id, m.sender, task_id,
                                                buf, len, w, h, now_unix_secs));
    cam.release();
    return result;
}
```

- [ ] **Step 4: Run tests + commit**

```bash
cd xiao-citizen/tests && make clean && make run | grep -E "===|passed|FAIL"
```

Expected: total assertions 97 → ~110.

```bash
git add xiao-citizen/citizenry_messages.{h,cpp} xiao-citizen/tests/test_messages.cpp
git commit -m "xiao-citizen: handle_propose_frame_capture + CameraSource interface (Task 3.3)"
```

---

### Task 3.4: Wire into the sketch — PROPOSE route + Arduino CameraSource

Now the firmware-side adapter that wraps `citizenry_camera_*` in a `CameraSource` and routes PROPOSEs to `handle_propose_frame_capture`.

**Files:**
- Modify: `xiao-citizen/xiao-citizen.ino`

- [ ] **Step 1: Add an Arduino CameraSource implementation in the sketch**

```cpp
#ifndef ARDUINO_HOST_TEST
class XiaoCameraSource : public CameraSource {
public:
    bool grab(const uint8_t** b, size_t* l, uint16_t* w, uint16_t* h) override {
        _fb = citizenry_camera_grab(/*timeout_ms=*/1000);
        if (!_fb) return false;
        *b = _fb->buf;
        *l = _fb->len;
        *w = citizenry_camera_width();
        *h = citizenry_camera_height();
        return true;
    }
    void release() override {
        if (_fb) { citizenry_camera_release(_fb); _fb = nullptr; }
    }
    bool ready() const override { return true; }   // begin() already gated; if init failed earlier we'd not reach here
private:
    camera_fb_t* _fb = nullptr;
};
#endif

static XiaoCameraSource g_camera_src;
```

- [ ] **Step 2: Add the PROPOSE case to the dispatcher switch**

In the `g_dispatcher.set_handler` lambda (already handles GOVERN and DISCOVER), add:

```cpp
case MsgType::PROPOSE: {
    FrameCaptureTarget tgt;
    auto envs = handle_propose_frame_capture(m, g_identity, g_camera_src,
                                             g_unicast_port,
                                             (double)time(nullptr), tgt);
    for (const auto& e : envs) {
        // Same multicast workaround as ADVERTISE / GOVERN ack — Phase 4 will
        // promote to unicast once source IP is plumbed through.
        g_xport.send_multicast(e);
    }
    Serial.printf("[propose] task=%s task_id=%s emitted=%u\n",
                  m.body_get_string("task").c_str(),
                  tgt.task_id.c_str(), (unsigned)envs.size());
    break;
}
```

- [ ] **Step 3: Pi compile**

```bash
scp xiao-citizen/xiao-citizen.ino bradley@raspberry-lerobot-001.local:~/xiao-citizen-build/xiao-citizen/
ssh bradley@raspberry-lerobot-001.local 'cd ~/xiao-citizen-build/xiao-citizen && rm -rf build && \
    arduino-cli compile --fqbn ... --build-path ./build . 2>&1 | tail -3'
```

Expected: program % rises by ~1–2 KB; SRAM essentially unchanged. Sketch warning-free.

- [ ] **Step 4: Commit**

```bash
git add xiao-citizen/xiao-citizen.ino
git commit -m "xiao-citizen: route PROPOSE to handle_propose_frame_capture; XiaoCameraSource adapter (Task 3.4)"
```

---

### Task 3.5: Live verification harness

Mirror `phase2_live_test.py` but for frame_capture. Single Python script that synthesises a PROPOSE, listens for ACCEPT then REPORT, and verifies the JPEG payload.

**Files:**
- Create: `xiao-citizen/tests/live/phase3_live_test.py`

- [ ] **Step 1: Write the harness**

```python
#!/usr/bin/env python3
"""Phase 3 live verification: drive PROPOSE frame_capture, verify
ACCEPT + REPORT with valid JPEG payload."""

import json, socket, struct, sys, time, base64, os
sys.path.insert(0, "/home/bradley/linux-usb")
from citizenry.protocol import (
    Envelope, MessageType, make_envelope, MULTICAST_GROUP, MULTICAST_PORT,
)
import nacl.signing, nacl.encoding

XIAO_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.83"

sk = nacl.signing.SigningKey.generate()
me = sk.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()
print(f"test driver pubkey: {me[:16]}...")

# listener
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("", MULTICAST_PORT))
mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
sock.settimeout(0.5)

tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

# We'll need the XIAO's pubkey to address the PROPOSE. Grab it from a
# heartbeat first.
print("learning XIAO pubkey from a heartbeat...")
xiao_pubkey = None
end = time.time() + 5
while time.time() < end and not xiao_pubkey:
    try:
        data, addr = sock.recvfrom(8192)
        if addr[0] != XIAO_IP: continue
        j = json.loads(data)
        if j.get("type") == int(MessageType.HEARTBEAT):
            xiao_pubkey = j["sender"]
            print(f"  XIAO pubkey: {xiao_pubkey[:16]}...")
    except socket.timeout: pass

if not xiao_pubkey:
    print("FATAL: no XIAO heartbeat seen in 5 s. Is firmware running?")
    sys.exit(2)

# Send PROPOSE addressed specifically to the XIAO
task_id = f"phase3-{int(time.time())}"
prop = make_envelope(
    MessageType.PROPOSE, sender_pubkey=me,
    body={"task": "frame_capture", "task_id": task_id},
    signing_key=sk, recipient=xiao_pubkey,
)
tx.sendto(prop.to_bytes(), (MULTICAST_GROUP, MULTICAST_PORT))
print(f"sent PROPOSE frame_capture task_id={task_id}")

got_accept = False
got_report = False
report_body = None
deadline = time.time() + 8
while time.time() < deadline and not (got_accept and got_report):
    try:
        data, addr = sock.recvfrom(65536)
    except socket.timeout: continue
    if addr[0] != XIAO_IP: continue
    try: j = json.loads(data)
    except: continue
    if j.get("recipient") != me: continue
    t = j.get("type")
    if t == int(MessageType.ACCEPT_REJECT):
        body = j.get("body") or {}
        if body.get("task_id") == task_id and body.get("result") == "accept":
            got_accept = True
            print("  ✅ ACCEPT received")
    elif t == int(MessageType.REPORT):
        body = j.get("body") or {}
        if body.get("task_id") == task_id and body.get("type") == "frame_capture":
            got_report = True
            report_body = body
            print("  ✅ REPORT frame_capture received")

if not got_accept:
    print("  ❌ no ACCEPT")
    sys.exit(3)
if not got_report:
    print("  ❌ no REPORT")
    sys.exit(4)

# Decode and validate JPEG
b64 = report_body["frame"]
jpg = base64.b64decode(b64)
print(f"  JPEG size: {len(jpg)} bytes  ({report_body['width']}x{report_body['height']})")
assert jpg[:2] == b"\xff\xd8", f"bad SOI: {jpg[:4].hex()}"
assert jpg[-2:] == b"\xff\xd9", f"bad EOI: {jpg[-4:].hex()}"
out_path = f"/tmp/phase3_{task_id}.jpg"
with open(out_path, "wb") as f: f.write(jpg)
print(f"  saved frame to {out_path}")

print("\nphase 3 live verification PASS")
```

- [ ] **Step 2: Run it before flashing — should fail**

Run from Surface against the currently-flashed Phase 2 firmware (no PROPOSE handler). Expected: ACCEPT/REPORT timeout, exit 3 or 4. This proves the harness actually waits for the new behaviour and isn't a no-op.

```bash
/home/bradley/lerobot-env/bin/python xiao-citizen/tests/live/phase3_live_test.py
```

- [ ] **Step 3: Commit harness**

```bash
git add xiao-citizen/tests/live/phase3_live_test.py
git commit -m "xiao-citizen: phase 3 live verification harness (Task 3.5)"
```

---

### Task 3.6: Hardware verification

The actual gate. Flash the new firmware and run the harness against it.

- [ ] **Step 1: User dance** — unplug XIAO USB, hold BOOT, plug in while holding BOOT, count to 2, release BOOT. Confirm `lsusb` shows `303a:1001` before flashing.

- [ ] **Step 2: Flash**

```bash
ssh bradley@raspberry-lerobot-001.local 'cd ~/xiao-citizen-build/xiao-citizen/build && \
    /home/bradley/.arduino15/packages/esp32/tools/esptool_py/5.2.0/esptool \
    --chip esp32s3 --port /dev/ttyACM0 --baud 921600 \
    --before no_reset --after hard_reset write-flash 0x0 xiao-citizen.ino.merged.bin'
```

Expected: "Hash of data verified." Then user presses RESET button to clean-boot (esptool's hard_reset is unreliable for our Arduino-CDC build; same as Phase 1/2).

- [ ] **Step 3: Wait for boot + heartbeat presence**

```bash
sleep 15 && avahi-browse -atrp _armos-citizen._udp 2>/dev/null | grep '^=' | awk -F';' '{print $4, $7":"$9}' | sort -u
```

Expected: `xiao-cam-0000.local:57708` listed.

- [ ] **Step 4: Run the harness**

```bash
/home/bradley/lerobot-env/bin/python xiao-citizen/tests/live/phase3_live_test.py
```

Expected:
- ACCEPT and REPORT both arrive within 8 s
- JPEG SOI/EOI markers valid
- frame size 5–30 KB
- frame saved to /tmp/phase3_*.jpg — open it visually in image viewer to sanity-check

- [ ] **Step 5: Sanity check the legacy HTTP endpoint still works**

```bash
curl -s -o /tmp/phase3_http.jpg http://192.168.1.83/capture && file /tmp/phase3_http.jpg
```

Expected: `/tmp/phase3_http.jpg: JPEG image data, ...`. The mutex'd camera grab from Task 3.0 means citizenry traffic and HTTP `/capture` coexist.

- [ ] **Step 6: Run the harness twice in quick succession**

Confirms a second PROPOSE returns a *fresh* frame (different bytes) and that no state is leaked across handlers.

```bash
/home/bradley/lerobot-env/bin/python xiao-citizen/tests/live/phase3_live_test.py
/home/bradley/lerobot-env/bin/python xiao-citizen/tests/live/phase3_live_test.py
md5sum /tmp/phase3_*.jpg | sort
```

Expected: at least the two most recent files have distinct md5s.

- [ ] **Step 7: Update Phase 3 execution report**

Write `~/jetson-setup/phase-3-execution-report.md` (parallel to the Phase 2 report) summarising tasks shipped, host-test totals, compile sizes, hardware verification results, and any issues.

- [ ] **Step 8: Tag the phase**

```bash
git tag -a phase-3-shipped -m "XIAO Phase 3: native frame capture verified live on xiao-cam-0000"
```

---

## Phase 3 — Decommission the Pi-side proxy (optional follow-up)

Once the second XIAO (`xiao-cam-002`) is also running Phase 3 firmware:

```bash
ssh bradley@raspberry-lerobot-001.local 'sudo systemctl stop citizenry-wifi-cam.service citizenry-wifi-cam2.service'
ssh bradley@raspberry-lerobot-001.local 'sudo systemctl disable citizenry-wifi-cam.service citizenry-wifi-cam2.service'
```

Verify the mesh still has both cameras (now natively, no proxy):

```bash
avahi-browse -atrp _armos-citizen._udp | grep xiao-cam
```

Don't delete the proxy code (`citizenry/run_wifi_camera.py`, `citizenry/camera_citizen.py`) — keep it as a reference / fallback for any USB camera that joins the country.

---

## Self-review checklist (executor: please verify before marking phase done)

- [ ] All host-test totals match the increments stated in each task
- [ ] No `static_assert` or `#error` lines hiding in any new file
- [ ] `Serial.print` calls don't reference variables that don't exist
- [ ] The `make_signed_envelope` / `parse_inbound` / `make_propose` helper names actually match what's in the existing test file
- [ ] `time(nullptr)` cast to double is used consistently — search for stray `time(0)` or `millis()/1000.0` mixing
- [ ] Compile size delta is reasonable: < 20 KB program, < 4 KB SRAM
- [ ] Phase 4 caveats from the Phase 2 merge commit are NOT re-introduced anywhere — no SNTP code, no source-IP changes, no NVS-preserving flash. Those belong in Phase 4.
