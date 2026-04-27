# XIAO True-Citizen Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Pi-side proxy citizens (`citizenry-wifi-cam.service` and `citizenry-wifi-cam2.service`) with native Arduino-C++ firmware on two XIAO ESP32S3 Sense boards so the cameras become first-class citizens that survive Pi outages and serve as the template for future ESP32 sensor citizens.

**Architecture:** Native Arduino sketch on each XIAO speaks the existing Python citizenry wire protocol (UDP multicast `239.67.84.90:7770` + unicast, Ed25519-signed canonical-JSON envelopes, mDNS service `_armos-citizen._udp.local.`). The OV2640 frame-capture path is exposed both as a citizenry capability (PROPOSE → REPORT) and a legacy HTTP `/capture` endpoint for backwards compatibility. One firmware image, identity per device derived from MAC.

**Tech Stack:** Arduino-ESP32 core 3.3.8, ArduinoJson v7, rweather/Crypto (Ed25519), Preferences (NVS keypair), ESPmDNS, lwip raw multicast, esp_camera. Host-side test harness in C++ (g++) and Python.

---

## What changed from v1 (`PLAN-xiao-true-citizen.md`)

The v1 draft (covered the same scope) was a discussion document. v2 is an executable plan:

| | v1 | v2 |
|---|---|---|
| Format | Section-based design narrative | Bite-sized TDD tasks with checkboxes |
| Granularity | Phase summaries (1 day, 2 hours) | Concrete steps (2-5 min each) with file paths and code |
| Interop risk | Listed canonical-JSON drift as "biggest risk" | **Elevated to a gating Phase 0 deliverable** with host-side fixture tests in both Python and C++ |
| Float-on-the-wire | Open question | **Decided**: patch Python to use `%.3f` format inside `signable_bytes()`; C++ matches |
| Citizen naming | Open question | **Decided**: hostname = `xiao-cam-` + last 4 hex of MAC; one binary serves both XIAOs |
| Constitution storage | Open question | **Decided**: persist in NVS, fall back to broadcasting DISCOVER if missing |
| OTA | Open question | **Deferred to a separate plan** — not in this scope |
| TDD coverage | Mentioned at high level | Strict TDD for envelope codec / Ed25519 / canonical JSON; coarser for hardware glue |
| HTTP endpoints | Implied "keep CameraWebServer" | Explicit task to integrate `/capture`, `/stream`, `/status` with the new sketch's loop |
| Test infrastructure | Mentioned | Concrete Makefile + Python harness scripts with exact commands |

The v1 draft is preserved at `PLAN-xiao-true-citizen.md` for diff/comparison.

---

## File structure

```
linux-usb/
├── citizenry/                                          (existing Python — UNCHANGED except one tiny patch)
│   ├── protocol.py                                     ← MODIFIED: signable_bytes() float format (1 task)
│   └── tests/
│       └── test_xiao_interop.py                        ← NEW: gold-master fixtures + interop runner
│
└── xiao-citizen/                                       ← NEW Arduino sketch + tests
    ├── xiao-citizen.ino                                main sketch (wires everything together)
    ├── citizenry_envelope.h / .cpp                     Envelope dataclass, canonical-JSON serializer, signable_bytes()
    ├── citizenry_identity.h / .cpp                     Ed25519 keygen/load/sign/verify; NVS persistence
    ├── citizenry_transport.h / .cpp                    UDP multicast (lwip) + unicast (WiFiUDP) wrappers
    ├── citizenry_neighbor.h / .cpp                     Neighbor table; TTL eviction
    ├── citizenry_dispatch.h / .cpp                     Message dispatch (DISCOVER/HEARTBEAT/ADVERTISE/PROPOSE/etc.)
    ├── camera_capture.h / .cpp                         OV2640 → JPEG via esp_camera
    ├── http_compat.h / .cpp                            Legacy /capture, /stream, /status endpoints
    ├── tests/                                          host-compiled unit tests
    │   ├── Makefile
    │   ├── fixtures.json                               canonical fixtures shared with Python
    │   ├── test_canonical_json.cpp
    │   ├── test_envelope_codec.cpp
    │   ├── test_ed25519_interop.cpp
    │   └── README.md
    └── README.md                                       build + flash + verify instructions
```

**Why this layout:** each `.cpp` is one responsibility (codec, identity, transport, dispatch, neighbor, camera, http). Files that change together live together (`.h` next to `.cpp`). Host-side tests live alongside the firmware so they can `#include` the same headers.

---

## Phase 0 — Pre-flight: signature interop (the gating check)

**Why this is Phase 0:** every other phase depends on the C++ firmware producing envelopes whose signatures Python verifies, and verifying envelopes that Python signed. If we don't lock this down before any other code, a single whitespace difference can hide for days and break everything silently.

**Phase 0 success criteria:** A fixture file with 10+ envelopes that round-trips between Python and C++ — Python signs → C++ verifies, and C++ signs → Python verifies — with byte-identical canonical-JSON serialization on both sides. No firmware on hardware yet.

### Task 0.1: Decide and patch the timestamp/float format on Python side

Python's `json.dumps()` formats floats via `repr()` which gives shortest-round-trip strings (`6.0` → `"6.0"`, `6.55555` → `"6.55555"`). Replicating that in C++ requires a Ryu-style algorithm. We avoid it by mandating fixed-precision (3 decimal places = ms) on both sides.

**Files:**
- Modify: `linux-usb/citizenry/protocol.py:46-58` (the `signable_bytes()` method)
- Test: `linux-usb/citizenry/tests/test_signable_bytes.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# linux-usb/citizenry/tests/test_signable_bytes.py
"""signable_bytes() must produce a deterministic, fixed-precision float format
so the C++ firmware can match it byte-for-byte.
"""
import json
from citizenry.protocol import Envelope


def test_signable_bytes_fixed_3dp_floats():
    env = Envelope(
        version=1, type=1,
        sender="abc123", recipient="*",
        timestamp=1234567890.0,
        ttl=6.0,
        body={"state": "ok"},
    )
    out = env.signable_bytes()
    # Floats must be formatted as %.3f, sorted keys, tight separators
    expected = (
        b'{"body":{"state":"ok"},'
        b'"recipient":"*",'
        b'"sender":"abc123",'
        b'"timestamp":1234567890.000,'
        b'"ttl":6.000,'
        b'"type":1,'
        b'"version":1}'
    )
    assert out == expected, f"got {out!r}\nexp {expected!r}"


def test_signable_bytes_subsecond_timestamp():
    env = Envelope(
        version=1, type=2,
        sender="ff", recipient="ee",
        timestamp=1700000000.123456,    # sub-ms precision in input
        ttl=0.5,
        body={},
    )
    out = env.signable_bytes()
    # 6th decimal must be truncated, ttl 0.5 → 0.500
    expected = (
        b'{"body":{},'
        b'"recipient":"ee",'
        b'"sender":"ff",'
        b'"timestamp":1700000000.123,'
        b'"ttl":0.500,'
        b'"type":2,'
        b'"version":1}'
    )
    assert out == expected, f"got {out!r}\nexp {expected!r}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/bradley/linux-usb
python -m pytest citizenry/tests/test_signable_bytes.py -v
```

Expected: FAIL — current code emits `"timestamp": 1234567890.0` (Python repr), test expects `1234567890.000`.

- [ ] **Step 3: Patch `signable_bytes()` to format floats fixed-precision**

Replace the body of `signable_bytes()` in `protocol.py`:

```python
    def signable_bytes(self) -> bytes:
        """Canonical bytes for signing — sorted keys, %.3f floats, tight separators.

        Format is locked down so the XIAO C++ firmware can produce byte-identical
        signables. Do not change without updating tests/test_signable_bytes.py and
        the C++ implementation in xiao-citizen/citizenry_envelope.cpp.
        """
        d = {
            "version": self.version,
            "type": self.type,
            "sender": self.sender,
            "recipient": self.recipient,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "body": self.body,
        }
        return _canonical_dumps(d).encode()


def _canonical_dumps(obj) -> str:
    """Sorted-keys, %.3f floats, no whitespace. Recursive."""
    if isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: kv[0])
        return "{" + ",".join(f"{_canonical_dumps(k)}:{_canonical_dumps(v)}" for k, v in items) + "}"
    if isinstance(obj, list):
        return "[" + ",".join(_canonical_dumps(v) for v in obj) + "]"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if obj is None:
        return "null"
    if isinstance(obj, float):
        return f"{obj:.3f}"
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    raise TypeError(f"Unsupported type for canonical JSON: {type(obj)}")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest citizenry/tests/test_signable_bytes.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Run the existing citizenry test suite to verify nothing else broke**

```bash
python -m pytest citizenry/tests/ -v
```

Expected: all tests pass. If existing sign/verify tests fail, the format change broke them — fix the test fixtures, not the new format.

- [ ] **Step 6: Commit**

```bash
git add citizenry/protocol.py citizenry/tests/test_signable_bytes.py
git commit -m "protocol: lock canonical-JSON to %.3f float format

Required for byte-identical signables between Python and the upcoming
XIAO Arduino firmware. Existing signed envelopes are not backwards
compatible — bump deferred to a coordinated cutover."
```

### Task 0.2: Generate canonical fixtures from Python

A small Python script emits a JSON file containing 10+ envelopes (signed by a fixed test keypair) that the C++ tests will use as gold-master input.

**Files:**
- Create: `linux-usb/citizenry/tests/generate_xiao_fixtures.py`
- Create: `linux-usb/xiao-citizen/tests/fixtures.json` (output)

- [ ] **Step 1: Write the script**

```python
# linux-usb/citizenry/tests/generate_xiao_fixtures.py
"""Generate gold-master fixtures for XIAO firmware interop tests.

Output: ../../xiao-citizen/tests/fixtures.json
Each fixture has: {name, signing_key (hex), envelope_dict, signable_bytes (hex), signature (hex)}.
The C++ tests load the fixtures and verify they can:
  (a) reconstruct the exact signable_bytes from the envelope_dict
  (b) verify the signature against signing_key.verify_key
"""
import json
import os
from pathlib import Path

import nacl.signing

from citizenry.protocol import Envelope, MessageType, make_envelope


# Stable test keypair so fixtures are reproducible.
TEST_SEED = bytes.fromhex(
    "c0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ff"
)
KEY = nacl.signing.SigningKey(TEST_SEED)
PUBKEY = KEY.verify_key.encode().hex()


def _fixture(name, env: Envelope) -> dict:
    sig_bytes = env.signable_bytes()
    return {
        "name": name,
        "signing_seed_hex": TEST_SEED.hex(),
        "verify_key_hex": PUBKEY,
        "envelope": {
            "version": env.version,
            "type": env.type,
            "sender": env.sender,
            "recipient": env.recipient,
            "timestamp": env.timestamp,
            "ttl": env.ttl,
            "body": env.body,
        },
        "signable_bytes_hex": sig_bytes.hex(),
        "signature_hex": env.signature,
    }


def main():
    fixtures = []

    fixtures.append(_fixture(
        "discover_minimal",
        make_envelope(MessageType.DISCOVER, PUBKEY,
                      {"name": "xiao-cam-test", "type": "sensor", "unicast_port": 0},
                      KEY)
    ))

    fixtures.append(_fixture(
        "heartbeat_simple",
        make_envelope(MessageType.HEARTBEAT, PUBKEY,
                      {"name": "xiao-cam-test", "state": "ok", "health": 1.0,
                       "unicast_port": 50000, "uptime": 12.5},
                      KEY)
    ))

    fixtures.append(_fixture(
        "advertise_with_caps",
        make_envelope(MessageType.ADVERTISE, PUBKEY,
                      {"name": "xiao-cam-test", "type": "sensor",
                       "capabilities": ["video_stream", "frame_capture"],
                       "health": 1.0, "state": "ok",
                       "unicast_port": 50000, "has_constitution": False},
                      KEY)
    ))

    fixtures.append(_fixture(
        "propose_frame_capture",
        make_envelope(MessageType.PROPOSE, PUBKEY,
                      {"task": "frame_capture", "task_id": "abc-123",
                       "resolution": [320, 240]},
                      KEY,
                      recipient="ff" * 32)
    ))

    fixtures.append(_fixture(
        "report_with_jpeg_b64",
        make_envelope(MessageType.REPORT, PUBKEY,
                      {"task_id": "abc-123", "result": "success",
                       "frame": "iVBORw0KGgo="},   # tiny base64
                      KEY,
                      recipient="ff" * 32)
    ))

    fixtures.append(_fixture(
        "govern_constitution_v1",
        make_envelope(MessageType.GOVERN, PUBKEY,
                      {"version": 1, "values": ["safety", "energy_aware"],
                       "rules": []},
                      KEY,
                      recipient="ff" * 32)
    ))

    fixtures.append(_fixture(
        "ttl_subsecond",
        make_envelope(MessageType.HEARTBEAT, PUBKEY, {}, KEY, ttl=0.1)
    ))

    fixtures.append(_fixture(
        "nested_body",
        make_envelope(MessageType.HEARTBEAT, PUBKEY,
                      {"a": {"b": {"c": [1, 2, 3]}}, "z": True, "n": None},
                      KEY)
    ))

    out_dir = Path(__file__).resolve().parents[2] / "xiao-citizen" / "tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "fixtures.json"
    out.write_text(json.dumps({"fixtures": fixtures}, indent=2, sort_keys=True))
    print(f"wrote {out} with {len(fixtures)} fixtures")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

```bash
cd /home/bradley/linux-usb
python -m citizenry.tests.generate_xiao_fixtures
```

Expected: `wrote /home/bradley/linux-usb/xiao-citizen/tests/fixtures.json with 8 fixtures`

- [ ] **Step 3: Commit**

```bash
git add citizenry/tests/generate_xiao_fixtures.py xiao-citizen/tests/fixtures.json
git commit -m "tests: add canonical-JSON gold-master fixtures for XIAO interop"
```

### Task 0.3: Stub the C++ codec library + Makefile + first failing test

**Files:**
- Create: `linux-usb/xiao-citizen/citizenry_envelope.h`
- Create: `linux-usb/xiao-citizen/citizenry_envelope.cpp`
- Create: `linux-usb/xiao-citizen/tests/Makefile`
- Create: `linux-usb/xiao-citizen/tests/test_canonical_json.cpp`

- [ ] **Step 1: Write the failing test**

```cpp
// linux-usb/xiao-citizen/tests/test_canonical_json.cpp
// Verifies our C++ canonical-JSON serializer matches Python's signable_bytes
// byte-for-byte against the gold-master fixtures.json.
#include "../citizenry_envelope.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

static int g_pass = 0, g_fail = 0;

static void check(const char* name, const std::string& got, const std::string& exp) {
    if (got == exp) { printf("PASS: %s\n", name); g_pass++; }
    else {
        printf("FAIL: %s\n  got: %s\n  exp: %s\n", name, got.c_str(), exp.c_str());
        g_fail++;
    }
}

static std::string hex_decode(const std::string& h) {
    std::string out;
    out.reserve(h.size() / 2);
    for (size_t i = 0; i + 1 < h.size(); i += 2) {
        unsigned int b;
        std::sscanf(h.c_str() + i, "%2x", &b);
        out.push_back((char)b);
    }
    return out;
}

int main() {
    std::ifstream f("fixtures.json");
    if (!f) { fprintf(stderr, "could not open fixtures.json\n"); return 2; }
    std::stringstream ss; ss << f.rdbuf();
    std::string fixtures_raw = ss.str();

    // Minimal JSON walking — replace per-fixture with proper parsing in next task.
    // For now, hard-code expectation for first fixture (discover_minimal):
    Envelope env;
    env.version = 1;
    env.type = 2;                        // DISCOVER
    env.sender = "<TEST_PUBKEY_HEX>";    // filled at runtime
    env.recipient = "*";
    env.timestamp = 1234567890.123;      // overridden below
    env.ttl = 5.0;
    env.body_clear();
    env.body_set_string("name", "xiao-cam-test");
    env.body_set_string("type", "sensor");
    env.body_set_int("unicast_port", 0);

    std::string canonical = canonical_signable_bytes(env);
    // For now just verify it produces ANY output of the right shape:
    check("canonical_outputs_non_empty", canonical.empty() ? "" : "ok", "ok");
    check("starts_with_brace", canonical.substr(0, 7), std::string("{\"body\""));

    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
```

- [ ] **Step 2: Write the header stub**

```cpp
// linux-usb/xiao-citizen/citizenry_envelope.h
#pragma once
#include <string>
#include <map>
#include <vector>
#include <variant>

// Body values can be string, int, double, bool, null, or a nested map/list.
// For simplicity we use a sealed variant tree — this matches what the wire
// protocol actually carries (no functions, no binary blobs except base64-strings).
struct JsonValue;
using JsonObject = std::map<std::string, JsonValue>;
using JsonArray = std::vector<JsonValue>;

struct JsonValue {
    enum Kind { Null, Bool, Int, Double, String, Object, Array };
    Kind kind = Null;
    bool b = false;
    long long i = 0;
    double d = 0.0;
    std::string s;
    JsonObject o;
    JsonArray a;
};

struct Envelope {
    int version = 1;
    int type = 0;
    std::string sender;     // hex pubkey
    std::string recipient;  // "*" or hex pubkey
    double timestamp = 0.0; // unix seconds, will be %.3f formatted
    double ttl = 0.0;
    JsonObject body;
    std::string signature;  // hex Ed25519 signature

    void body_clear() { body.clear(); }
    void body_set_string(const std::string& k, const std::string& v);
    void body_set_int(const std::string& k, long long v);
    void body_set_double(const std::string& k, double v);
    void body_set_bool(const std::string& k, bool v);
    void body_set_null(const std::string& k);
};

// Produce the canonical-JSON bytes that get signed.
// Matches Python protocol.py _canonical_dumps() byte-for-byte.
std::string canonical_signable_bytes(const Envelope& env);

// Serialize the full envelope (with signature) for wire transmission.
std::string envelope_to_wire(const Envelope& env);

// Parse a wire envelope.
bool envelope_from_wire(const std::string& bytes, Envelope& out);
```

- [ ] **Step 3: Write the cpp stub (intentionally non-working)**

```cpp
// linux-usb/xiao-citizen/citizenry_envelope.cpp
#include "citizenry_envelope.h"

void Envelope::body_set_string(const std::string& k, const std::string& v) {
    JsonValue jv; jv.kind = JsonValue::String; jv.s = v;
    body[k] = jv;
}
void Envelope::body_set_int(const std::string& k, long long v) {
    JsonValue jv; jv.kind = JsonValue::Int; jv.i = v;
    body[k] = jv;
}
void Envelope::body_set_double(const std::string& k, double v) {
    JsonValue jv; jv.kind = JsonValue::Double; jv.d = v;
    body[k] = jv;
}
void Envelope::body_set_bool(const std::string& k, bool v) {
    JsonValue jv; jv.kind = JsonValue::Bool; jv.b = v;
    body[k] = jv;
}
void Envelope::body_set_null(const std::string& k) {
    JsonValue jv; jv.kind = JsonValue::Null;
    body[k] = jv;
}

std::string canonical_signable_bytes(const Envelope& /*env*/) {
    // STUB — Task 0.4 fills this in
    return "";
}

std::string envelope_to_wire(const Envelope& /*env*/) {
    return "";
}

bool envelope_from_wire(const std::string& /*bytes*/, Envelope& /*out*/) {
    return false;
}
```

- [ ] **Step 4: Write the Makefile**

```make
# linux-usb/xiao-citizen/tests/Makefile
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2 -I..

TESTS = test_canonical_json test_envelope_codec test_ed25519_interop

all: $(TESTS)

test_canonical_json: test_canonical_json.cpp ../citizenry_envelope.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^

test_envelope_codec: test_envelope_codec.cpp ../citizenry_envelope.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^

# test_ed25519_interop links rweather/Crypto Ed25519 (vendored).
# Filter out RNG.cpp + NoiseSource.cpp (Arduino-only); they're replaced by Crypto_host_stubs.cpp.
CRYPTO_HOST_SRCS = $(filter-out vendor/Crypto/RNG.cpp vendor/Crypto/NoiseSource.cpp, $(wildcard vendor/Crypto/*.cpp)) vendor/Crypto_host_stubs.cpp

test_ed25519_interop: test_ed25519_interop.cpp ../citizenry_envelope.cpp ../citizenry_identity.cpp $(CRYPTO_HOST_SRCS)
	$(CXX) $(CXXFLAGS) -DARDUINO_HOST_TEST -Ivendor/Crypto -o $@ $^

run: all
	@for t in $(TESTS); do echo "=== $$t ==="; ./$$t || exit 1; done

clean:
	rm -f $(TESTS) *.o

.PHONY: all run clean
```

- [ ] **Step 5: Run the test (it should fail clearly)**

```bash
cd /home/bradley/linux-usb/xiao-citizen/tests
make test_canonical_json
./test_canonical_json
```

Expected: FAIL on `canonical_outputs_non_empty` (stub returns ""). `1 passed, 1 failed`.

- [ ] **Step 6: Commit**

```bash
git add xiao-citizen/citizenry_envelope.h xiao-citizen/citizenry_envelope.cpp xiao-citizen/tests/Makefile xiao-citizen/tests/test_canonical_json.cpp
git commit -m "xiao-citizen: stub envelope codec + host test scaffolding"
```

### Task 0.4: Implement canonical_signable_bytes() in C++

**Files:**
- Modify: `linux-usb/xiao-citizen/citizenry_envelope.cpp`
- Modify: `linux-usb/xiao-citizen/tests/test_canonical_json.cpp` (add proper fixture-driven tests)

- [ ] **Step 1: Replace the test with the real fixture-driven version**

```cpp
// linux-usb/xiao-citizen/tests/test_canonical_json.cpp (replace contents)
#include "../citizenry_envelope.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include "fixture_loader.h"   // small helper added next step

static int g_pass = 0, g_fail = 0;
static void check(const std::string& name, const std::string& got, const std::string& exp) {
    if (got == exp) { printf("PASS: %s\n", name.c_str()); g_pass++; }
    else { printf("FAIL: %s\n  got %zu bytes: %s\n  exp %zu bytes: %s\n",
                  name.c_str(), got.size(), got.c_str(), exp.size(), exp.c_str()); g_fail++; }
}

int main() {
    auto fixtures = load_fixtures("fixtures.json");
    if (fixtures.empty()) { fprintf(stderr, "no fixtures loaded\n"); return 2; }

    for (const auto& fx : fixtures) {
        std::string got = canonical_signable_bytes(fx.envelope);
        check(fx.name + " canonical_bytes", got, fx.signable_bytes);
    }
    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
```

- [ ] **Step 2: Add the fixture loader (small JSON parser using nlohmann/json single-header)**

```cpp
// linux-usb/xiao-citizen/tests/fixture_loader.h
#pragma once
#include "../citizenry_envelope.h"
#include "vendor/nlohmann/json.hpp"
#include <fstream>
#include <string>
#include <vector>

struct Fixture {
    std::string name;
    Envelope envelope;
    std::string signable_bytes;   // raw bytes the C++ output must match
    std::string signature;        // hex
    std::string verify_key;       // hex
    std::string signing_seed;     // hex
};

inline std::string hex_decode(const std::string& h) {
    std::string out;
    out.reserve(h.size() / 2);
    for (size_t i = 0; i + 1 < h.size(); i += 2) {
        unsigned int b;
        std::sscanf(h.c_str() + i, "%2x", &b);
        out.push_back((char)b);
    }
    return out;
}

inline JsonValue from_nl(const nlohmann::json& j) {
    JsonValue v;
    if (j.is_null()) v.kind = JsonValue::Null;
    else if (j.is_boolean()) { v.kind = JsonValue::Bool; v.b = j.get<bool>(); }
    else if (j.is_number_integer()) { v.kind = JsonValue::Int; v.i = j.get<long long>(); }
    else if (j.is_number_float()) { v.kind = JsonValue::Double; v.d = j.get<double>(); }
    else if (j.is_string()) { v.kind = JsonValue::String; v.s = j.get<std::string>(); }
    else if (j.is_object()) {
        v.kind = JsonValue::Object;
        for (auto it = j.begin(); it != j.end(); ++it) v.o[it.key()] = from_nl(it.value());
    } else if (j.is_array()) {
        v.kind = JsonValue::Array;
        for (auto& el : j) v.a.push_back(from_nl(el));
    }
    return v;
}

inline std::vector<Fixture> load_fixtures(const std::string& path) {
    std::ifstream f(path);
    nlohmann::json doc;
    f >> doc;
    std::vector<Fixture> out;
    for (auto& fx : doc["fixtures"]) {
        Fixture x;
        x.name = fx["name"].get<std::string>();
        x.signable_bytes = hex_decode(fx["signable_bytes_hex"].get<std::string>());
        x.signature = fx["signature_hex"].get<std::string>();
        x.verify_key = fx["verify_key_hex"].get<std::string>();
        x.signing_seed = fx["signing_seed_hex"].get<std::string>();
        const auto& e = fx["envelope"];
        x.envelope.version = e["version"].get<int>();
        x.envelope.type = e["type"].get<int>();
        x.envelope.sender = e["sender"].get<std::string>();
        x.envelope.recipient = e["recipient"].get<std::string>();
        x.envelope.timestamp = e["timestamp"].get<double>();
        x.envelope.ttl = e["ttl"].get<double>();
        const auto& body = e["body"];
        for (auto it = body.begin(); it != body.end(); ++it)
            x.envelope.body[it.key()] = from_nl(it.value());
        out.push_back(x);
    }
    return out;
}
```

- [ ] **Step 3: Vendor nlohmann/json single-header**

```bash
cd /home/bradley/linux-usb/xiao-citizen/tests
mkdir -p vendor/nlohmann
curl -fsSL https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp -o vendor/nlohmann/json.hpp
ls -lh vendor/nlohmann/json.hpp   # should be ~900 KB
```

- [ ] **Step 4: Implement canonical_signable_bytes() in citizenry_envelope.cpp**

Replace the stub:

```cpp
// In citizenry_envelope.cpp — replace the canonical_signable_bytes stub with:

#include <cstdio>
#include <sstream>
#include <map>

namespace {

void write_canonical(std::ostringstream& os, const JsonValue& v);

void write_string(std::ostringstream& os, const std::string& s) {
    os << '"';
    for (char c : s) {
        switch (c) {
            case '"':  os << "\\\""; break;
            case '\\': os << "\\\\"; break;
            case '\b': os << "\\b"; break;
            case '\f': os << "\\f"; break;
            case '\n': os << "\\n"; break;
            case '\r': os << "\\r"; break;
            case '\t': os << "\\t"; break;
            default:
                if ((unsigned char)c < 0x20) { char buf[8]; std::snprintf(buf, sizeof(buf), "\\u%04x", c); os << buf; }
                else os << c;
        }
    }
    os << '"';
}

void write_double(std::ostringstream& os, double d) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.3f", d);
    os << buf;
}

void write_object(std::ostringstream& os, const JsonObject& obj) {
    os << '{';
    bool first = true;
    // std::map already sorts keys lexicographically — that matches Python sort_keys=True
    for (const auto& kv : obj) {
        if (!first) os << ',';
        write_string(os, kv.first);
        os << ':';
        write_canonical(os, kv.second);
        first = false;
    }
    os << '}';
}

void write_array(std::ostringstream& os, const JsonArray& arr) {
    os << '[';
    bool first = true;
    for (const auto& v : arr) {
        if (!first) os << ',';
        write_canonical(os, v);
        first = false;
    }
    os << ']';
}

void write_canonical(std::ostringstream& os, const JsonValue& v) {
    switch (v.kind) {
        case JsonValue::Null:   os << "null"; break;
        case JsonValue::Bool:   os << (v.b ? "true" : "false"); break;
        case JsonValue::Int:    os << v.i; break;
        case JsonValue::Double: write_double(os, v.d); break;
        case JsonValue::String: write_string(os, v.s); break;
        case JsonValue::Object: write_object(os, v.o); break;
        case JsonValue::Array:  write_array(os, v.a); break;
    }
}

} // namespace

std::string canonical_signable_bytes(const Envelope& env) {
    // Build a synthetic top-level object with the 7 envelope fields
    // (everything except the signature). std::map auto-sorts keys.
    std::map<std::string, std::function<void(std::ostringstream&)>> fields = {
        {"body",       [&](auto& os){ write_object(os, env.body); }},
        {"recipient",  [&](auto& os){ write_string(os, env.recipient); }},
        {"sender",     [&](auto& os){ write_string(os, env.sender); }},
        {"timestamp",  [&](auto& os){ write_double(os, env.timestamp); }},
        {"ttl",        [&](auto& os){ write_double(os, env.ttl); }},
        {"type",       [&](auto& os){ os << env.type; }},
        {"version",    [&](auto& os){ os << env.version; }},
    };
    std::ostringstream os;
    os << '{';
    bool first = true;
    for (auto& kv : fields) {
        if (!first) os << ',';
        write_string(os, kv.first);
        os << ':';
        kv.second(os);
        first = false;
    }
    os << '}';
    return os.str();
}
```

Add `#include <functional>` at the top of the file.

- [ ] **Step 5: Run the test, verify it passes**

```bash
cd /home/bradley/linux-usb/xiao-citizen/tests
make test_canonical_json && ./test_canonical_json
```

Expected: `8 passed, 0 failed` (one per fixture).

If any fixture fails, **DO NOT proceed** — debug the canonical-JSON divergence. Common causes:
- Float not formatted as `%.3f`
- Body keys not sorted (use `std::map`, not `std::unordered_map`)
- String escaping mismatch (we handle `"`, `\`, control chars; Python emits `\uXXXX` for `<0x20`)
- Array iteration order

- [ ] **Step 6: Commit**

```bash
git add xiao-citizen/citizenry_envelope.cpp xiao-citizen/tests/test_canonical_json.cpp xiao-citizen/tests/fixture_loader.h xiao-citizen/tests/vendor/
git commit -m "xiao-citizen: canonical-JSON serializer matches Python byte-for-byte (8 fixtures pass)"
```

### Task 0.5: Implement Ed25519 sign/verify against fixtures

**Files:**
- Create: `linux-usb/xiao-citizen/citizenry_identity.h`
- Create: `linux-usb/xiao-citizen/citizenry_identity.cpp`
- Create: `linux-usb/xiao-citizen/tests/test_ed25519_interop.cpp`
- Create: `linux-usb/xiao-citizen/tests/vendor/Crypto/` (vendor rweather/Crypto Ed25519 source files)

- [ ] **Step 1: Vendor rweather/Crypto Ed25519 sources**

```bash
cd /home/bradley/linux-usb/xiao-citizen/tests
mkdir -p vendor/Crypto
cd vendor/Crypto
# Pull just the Ed25519-related source files we need (keeps the vendor dir small)
for f in Ed25519.h Ed25519.cpp Curve25519.h Curve25519.cpp Hash.h Hash.cpp SHA512.h SHA512.cpp BigNumberUtil.h BigNumberUtil.cpp Crypto.h Crypto.cpp utility/EndianUtil.h utility/LimbUtil.h; do
  mkdir -p $(dirname "$f")
  curl -fsSL "https://raw.githubusercontent.com/rweather/arduinolibs/master/libraries/Crypto/${f}" -o "$f"
done
ls -R
```

Expected: `Ed25519.h, Ed25519.cpp, ...` in the directory tree.

**Note: do NOT vendor `RNG.cpp` or `NoiseSource.cpp`.** They pull Arduino-only transitive headers (`<Arduino.h>`, `<ChaCha.h>`, ...) that won't compile under host g++. The Phase 0 host tests only exercise seeded sign/verify (which never call `RNG.rand()` inside `Ed25519::sign`/`verify`), so we can stub them out for the host build. Add this stub file:

```cpp
// linux-usb/xiao-citizen/tests/vendor/Crypto_host_stubs.cpp
// Host-only RNG stubs. Not compiled into firmware — Arduino-ESP32 will use
// rweather/Crypto's real RNG.cpp on the device.
#include <cstddef>

class NoiseSource {};

class RNGClass {
public:
    void begin(const char*) {}
    void addNoiseSource(NoiseSource&) {}
    void stir(const uint8_t*, size_t, unsigned int) {}
    void save() {}
    void rand(uint8_t* buf, size_t n) { for (size_t i = 0; i < n; i++) buf[i] = 0; }
    bool available(size_t) { return true; }
    void loop() {}
};

RNGClass RNG;
```

Reference it from the Makefile's Ed25519 test recipe so it gets compiled into the host test binary alongside `Crypto/*.cpp` (excluding `RNG.cpp` and `NoiseSource.cpp`).

- [ ] **Step 2: Write the test**

```cpp
// linux-usb/xiao-citizen/tests/test_ed25519_interop.cpp
// For each fixture: derive keypair from signing_seed, sign canonical bytes,
// verify the signature matches Python's. Then verify Python's signature
// using only the verify_key.
#include "../citizenry_envelope.h"
#include "../citizenry_identity.h"
#include "fixture_loader.h"
#include <cstdio>
#include <string>

static int g_pass = 0, g_fail = 0;
static void check(const std::string& name, bool cond) {
    if (cond) { printf("PASS: %s\n", name.c_str()); g_pass++; }
    else      { printf("FAIL: %s\n", name.c_str()); g_fail++; }
}

int main() {
    auto fixtures = load_fixtures("fixtures.json");
    for (const auto& fx : fixtures) {
        // 1. Derive the keypair from the seed
        Identity id;
        id.from_seed(hex_decode(fx.signing_seed));
        check(fx.name + " pubkey matches", id.pubkey_hex() == fx.verify_key);

        // 2. Sign the canonical bytes with C++; expect exact same signature as Python's
        std::string canonical = canonical_signable_bytes(fx.envelope);
        std::string sig_cpp = id.sign_hex(canonical);
        check(fx.name + " sign matches python", sig_cpp == fx.signature);

        // 3. Verify Python's signature using only the public key
        bool ok = Identity::verify_hex(fx.verify_key, canonical, fx.signature);
        check(fx.name + " verify python sig", ok);

        // 4. Tampered bytes should fail
        std::string tampered = canonical;
        if (!tampered.empty()) tampered[0] ^= 0x01;
        bool tampered_ok = Identity::verify_hex(fx.verify_key, tampered, fx.signature);
        check(fx.name + " tamper detected", !tampered_ok);
    }
    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
```

- [ ] **Step 3: Write the identity header and stub the cpp**

```cpp
// linux-usb/xiao-citizen/citizenry_identity.h
#pragma once
#include <cstdint>
#include <string>

class Identity {
public:
    void generate();                                 // make a fresh keypair (Phase 1 will use this on first boot)
    void from_seed(const std::string& seed_bytes);   // 32 bytes
    std::string pubkey_hex() const;
    std::string sign_hex(const std::string& msg) const;
    static bool verify_hex(const std::string& pubkey_hex,
                           const std::string& msg,
                           const std::string& sig_hex);

#ifndef ARDUINO_HOST_TEST
    bool load_from_nvs();    // populated in Phase 1 — uses Preferences on hardware
    void save_to_nvs() const;
#endif

    uint8_t priv_[64] = {0};   // Ed25519 expanded private key (64 bytes from rweather)
    uint8_t pub_[32]  = {0};
};
```

```cpp
// linux-usb/xiao-citizen/citizenry_identity.cpp
#include "citizenry_identity.h"
#include "tests/vendor/Crypto/Ed25519.h"
#include <cstdio>
#include <cstring>

static std::string to_hex(const uint8_t* b, size_t n) {
    static const char* H = "0123456789abcdef";
    std::string out; out.reserve(n * 2);
    for (size_t i = 0; i < n; i++) { out.push_back(H[b[i] >> 4]); out.push_back(H[b[i] & 0xF]); }
    return out;
}

static void from_hex(const std::string& h, uint8_t* out, size_t n) {
    for (size_t i = 0; i < n; i++) {
        unsigned int v;
        std::sscanf(h.c_str() + i * 2, "%2x", &v);
        out[i] = (uint8_t)v;
    }
}

void Identity::generate() {
    Ed25519::generatePrivateKey(priv_);
    Ed25519::derivePublicKey(pub_, priv_);
}

void Identity::from_seed(const std::string& seed_bytes) {
    // rweather's Ed25519 takes a 32-byte private key (the seed). Copy and derive pub.
    std::memcpy(priv_, seed_bytes.data(), 32);
    Ed25519::derivePublicKey(pub_, priv_);
}

std::string Identity::pubkey_hex() const {
    return to_hex(pub_, 32);
}

std::string Identity::sign_hex(const std::string& msg) const {
    uint8_t sig[64];
    Ed25519::sign(sig, priv_, pub_, msg.data(), msg.size());
    return to_hex(sig, 64);
}

bool Identity::verify_hex(const std::string& pubkey_hex,
                          const std::string& msg,
                          const std::string& sig_hex) {
    uint8_t pub[32], sig[64];
    if (pubkey_hex.size() != 64 || sig_hex.size() != 128) return false;
    from_hex(pubkey_hex, pub, 32);
    from_hex(sig_hex, sig, 64);
    return Ed25519::verify(sig, pub, msg.data(), msg.size());
}
```

- [ ] **Step 4: Build and run**

```bash
cd /home/bradley/linux-usb/xiao-citizen/tests
make test_ed25519_interop && ./test_ed25519_interop
```

Expected: `32 passed, 0 failed` (4 checks × 8 fixtures).

**If any signature check fails:** Phase 0 is NOT complete. The likely culprits, in order:
1. Canonical bytes differ (re-run `test_canonical_json` first; must be all green)
2. rweather/Crypto Ed25519 uses a different seed-to-private-key expansion than libsodium — verify by checking pubkey_hex matches first; if it doesn't, the signing seed expansion is the bug
3. Endian or buffer-layout mismatch

- [ ] **Step 5: Commit**

```bash
git add xiao-citizen/citizenry_identity.h xiao-citizen/citizenry_identity.cpp xiao-citizen/tests/test_ed25519_interop.cpp xiao-citizen/tests/vendor/Crypto/
git commit -m "xiao-citizen: Ed25519 sign/verify interop with Python (32 checks pass)"
```

### Task 0.6: Reverse-direction interop (C++ signs, Python verifies)

A new Python test loads any envelope produced by the C++ test binary and verifies it with pynacl. This catches regressions where the C++ produces a "valid-looking" but secretly-different signature.

- [ ] **Step 1: Write a C++ binary that emits a freshly-signed envelope to stdout**

```cpp
// linux-usb/xiao-citizen/tests/emit_envelope.cpp — small helper, not a test
#include "../citizenry_envelope.h"
#include "../citizenry_identity.h"
#include "fixture_loader.h"
#include <cstdio>
#include <iostream>
#include <string>

// Match Python's %.3f canonical format when emitting floats to JSON, otherwise
// `iostream` defaults to `1.7e+09` and Python's verifier loses precision.
static std::string format_double(double d) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.3f", d);
    return buf;
}

int main() {
    // Use the same test seed Python uses
    Identity id;
    std::string seed = hex_decode("c0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ff");
    id.from_seed(seed);

    Envelope env;
    env.version = 1; env.type = 1;
    env.sender = id.pubkey_hex();
    env.recipient = "*";
    env.timestamp = 1700000000.123;
    env.ttl = 6.0;
    env.body_set_string("name", "xiao-roundtrip");
    env.body_set_int("port", 12345);

    std::string canonical = canonical_signable_bytes(env);
    env.signature = id.sign_hex(canonical);

    // Print one JSON object Python can parse: {envelope, canonical_hex, signature, pubkey}
    std::cout << "{"
              << "\"envelope\":{"
                << "\"version\":" << env.version
                << ",\"type\":" << env.type
                << ",\"sender\":\"" << env.sender << "\""
                << ",\"recipient\":\"" << env.recipient << "\""
                << ",\"timestamp\":" << format_double(env.timestamp)
                << ",\"ttl\":" << format_double(env.ttl)
                << ",\"body\":{\"name\":\"xiao-roundtrip\",\"port\":12345}"
              << "},"
              << "\"canonical_hex\":\"";
    for (char c : canonical) { char buf[3]; std::snprintf(buf, sizeof(buf), "%02x", (unsigned char)c); std::cout << buf; }
    std::cout << "\","
              << "\"signature\":\"" << env.signature << "\","
              << "\"pubkey\":\"" << id.pubkey_hex() << "\""
              << "}\n";
    return 0;
}
```

- [ ] **Step 2: Add to Makefile**

Append to `linux-usb/xiao-citizen/tests/Makefile`:
```make
emit_envelope: emit_envelope.cpp ../citizenry_envelope.cpp ../citizenry_identity.cpp $(wildcard vendor/Crypto/*.cpp)
	$(CXX) $(CXXFLAGS) -DARDUINO_HOST_TEST -Ivendor/Crypto -o $@ $^
```

- [ ] **Step 3: Write the Python verifier test**

```python
# linux-usb/citizenry/tests/test_xiao_reverse_interop.py
"""Run the C++ emit_envelope binary, parse its output, and verify the
signature using the same canonical_signable_bytes computation Python uses.
This proves C++ → Python interop in the reverse direction.
"""
import json
import subprocess
from pathlib import Path

import nacl.signing
import nacl.encoding
import pytest

from citizenry.protocol import Envelope


@pytest.fixture
def cpp_output():
    bin_path = Path(__file__).resolve().parents[2] / "xiao-citizen" / "tests" / "emit_envelope"
    if not bin_path.exists():
        pytest.skip(f"build the binary first: cd {bin_path.parent} && make emit_envelope")
    out = subprocess.check_output([str(bin_path)])
    return json.loads(out)


def test_canonical_bytes_match(cpp_output):
    e = cpp_output["envelope"]
    env = Envelope(version=e["version"], type=e["type"], sender=e["sender"],
                   recipient=e["recipient"], timestamp=e["timestamp"], ttl=e["ttl"],
                   body=e["body"])
    py_canonical = env.signable_bytes()
    cpp_canonical = bytes.fromhex(cpp_output["canonical_hex"])
    assert py_canonical == cpp_canonical


def test_python_verifies_cpp_signature(cpp_output):
    e = cpp_output["envelope"]
    env = Envelope(version=e["version"], type=e["type"], sender=e["sender"],
                   recipient=e["recipient"], timestamp=e["timestamp"], ttl=e["ttl"],
                   body=e["body"])
    pubkey_bytes = bytes.fromhex(cpp_output["pubkey"])
    vk = nacl.signing.VerifyKey(pubkey_bytes)
    sig_bytes = bytes.fromhex(cpp_output["signature"])
    # raises BadSignatureError on mismatch
    vk.verify(env.signable_bytes(), sig_bytes)
```

- [ ] **Step 4: Run it**

```bash
cd /home/bradley/linux-usb/xiao-citizen/tests
make emit_envelope
cd /home/bradley/linux-usb
python -m pytest citizenry/tests/test_xiao_reverse_interop.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add xiao-citizen/tests/emit_envelope.cpp xiao-citizen/tests/Makefile citizenry/tests/test_xiao_reverse_interop.py
git commit -m "xiao-citizen: reverse interop test (C++ signs → Python verifies, 2 cases)"
```

### Phase 0 acceptance / gate

Phase 0 is complete **only when all of these pass simultaneously**:

```bash
cd /home/bradley/linux-usb
python -m pytest citizenry/tests/test_signable_bytes.py citizenry/tests/test_xiao_reverse_interop.py -v
cd xiao-citizen/tests && make run
```

If any fail, do **not** start Phase 1. Canonical-JSON drift is the single largest interop risk in this project; we eat the cost up front.

---

## Phase 1 — Skeleton firmware (boots, joins LAN, gets seen)

Phase 1 produces a sketch that:
- Boots on a XIAO ESP32S3 Sense
- Connects to Bradley-Starlink WiFi
- Generates or loads an Ed25519 keypair from NVS
- Registers an mDNS service `_armos-citizen._udp.local.` with citizenry TXT properties
- Binds UDP unicast on an ephemeral port
- Joins UDP multicast group `239.67.84.90:7770`
- Logs status over Serial (which routes to UART pins per board quirks)
- Keeps the existing CameraWebServer HTTP endpoints (`/`, `/capture`, `/stream`, `/status`) functional

It does **not yet** send/receive citizenry envelopes — that comes in Phase 2.

### Task 1.1: Project skeleton with build flags + first boot

**Files:**
- Create: `linux-usb/xiao-citizen/xiao-citizen.ino`
- Create: `linux-usb/xiao-citizen/board_config.h` (copied from Arduino-ESP32 CameraWebServer example)
- Create: `linux-usb/xiao-citizen/camera_pins.h` (copied)
- Create: `linux-usb/xiao-citizen/README.md`

- [ ] **Step 1: Copy the camera support files from the bundled example**

```bash
cd /home/bradley/linux-usb/xiao-citizen
SRC=$HOME/.arduino15/packages/esp32/hardware/esp32/3.3.8/libraries/ESP32/examples/Camera/CameraWebServer
cp $SRC/board_config.h .
cp $SRC/camera_pins.h .
cp $SRC/app_httpd.cpp .
cp $SRC/camera_index.h .
cp $SRC/partitions.csv .
sed -i 's|^#define CAMERA_MODEL_ESP_EYE|//#define CAMERA_MODEL_ESP_EYE|' board_config.h
sed -i 's|^//#define CAMERA_MODEL_XIAO_ESP32S3|#define CAMERA_MODEL_XIAO_ESP32S3|' board_config.h
grep '^#define CAMERA_MODEL_' board_config.h
```

Expected output: `#define CAMERA_MODEL_XIAO_ESP32S3 // Has PSRAM`

- [ ] **Step 2: Write the minimal sketch**

```cpp
// linux-usb/xiao-citizen/xiao-citizen.ino
#include <WiFi.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include "esp_camera.h"
#include "board_config.h"
#include "camera_pins.h"
#include "citizenry_identity.h"

// ===== build-time configuration =====
static const char* WIFI_SSID = "Bradley-Starlink";
static const char* WIFI_PSK  = "gjnl1105";

// Citizen name = "xiao-cam-" + last 4 hex of MAC (lowercase, no colons)
static String make_citizen_name() {
    uint8_t mac[6];
    WiFi.macAddress(mac);
    char buf[32];
    snprintf(buf, sizeof(buf), "xiao-cam-%02x%02x", mac[4], mac[5]);
    for (char* p = buf; *p; p++) if (*p >= 'A' && *p <= 'Z') *p += 32;
    return String(buf);
}

static Identity g_identity;
static String   g_name;

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n=== xiao-citizen booting ===");

    g_name = make_citizen_name();
    Serial.printf("citizen name: %s\n", g_name.c_str());

    // WiFi
    WiFi.mode(WIFI_STA);
    WiFi.setHostname(g_name.c_str());
    WiFi.begin(WIFI_SSID, WIFI_PSK);
    Serial.print("WiFi");
    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 60) { delay(500); Serial.print('.'); tries++; }
    if (WiFi.status() != WL_CONNECTED) { Serial.println(" FAILED"); return; }
    Serial.printf("\nIP: %s\n", WiFi.localIP().toString().c_str());

    // Identity
    if (!g_identity.load_from_nvs()) {
        Serial.println("no keypair in NVS, generating fresh one (one-time, ~1s)…");
        g_identity.generate();
        g_identity.save_to_nvs();
    }
    Serial.printf("pubkey: %s\n", g_identity.pubkey_hex().c_str());

    // mDNS
    if (MDNS.begin(g_name.c_str())) {
        // We'll add the citizenry TXT in task 1.3 once we have the unicast port.
        MDNS.addService("http", "tcp", 80);
        Serial.println("mDNS started");
    }
}

void loop() { delay(1000); }
```

- [ ] **Step 3: Add NVS load/save to citizenry_identity.cpp (hardware-only branch)**

Add at the bottom of `citizenry_identity.cpp`:

```cpp
#ifndef ARDUINO_HOST_TEST
#include <Preferences.h>

bool Identity::load_from_nvs() {
    Preferences prefs;
    if (!prefs.begin("xiao-citizen", true)) return false;
    size_t got = prefs.getBytes("priv", priv_, 32);
    prefs.end();
    if (got != 32) return false;
    Ed25519::derivePublicKey(pub_, priv_);
    return true;
}

void Identity::save_to_nvs() const {
    Preferences prefs;
    prefs.begin("xiao-citizen", false);
    prefs.putBytes("priv", priv_, 32);
    prefs.end();
}
#endif
```

- [ ] **Step 4: Compile**

```bash
cd /home/bradley/linux-usb/xiao-citizen
arduino-cli lib install "Crypto" "ArduinoJson"
arduino-cli compile --fqbn "esp32:esp32:XIAO_ESP32S3:PSRAM=opi,USBMode=default,CDCOnBoot=default,UploadSpeed=921600,FlashSize=8M,FlashMode=qio,PartitionScheme=default_8MB" --build-path ./build .
```

Expected: build succeeds, sketch size <2 MB. If `Ed25519.h` not found, ensure the Crypto library installed and the rweather/Crypto vendored copy is removed from the include path on hardware (already gated behind `ARDUINO_HOST_TEST` in the .h).

- [ ] **Step 5: Flash and verify boot**

Hold BOOT, tap RESET, release BOOT on the XIAO. Then:

```bash
arduino-cli upload -p /dev/ttyACM0 --fqbn "esp32:esp32:XIAO_ESP32S3:PSRAM=opi,USBMode=default,CDCOnBoot=default,UploadSpeed=921600,FlashSize=8M,FlashMode=qio,PartitionScheme=default_8MB" --input-dir ./build .
sleep 6
lsusb | grep -E "303a|2886"   # expect 2886:0056 = app running
```

From the Surface, after 30s for WiFi to settle:
```bash
getent hosts xiao-cam-XXXX.local   # XXXX = last 4 hex of the XIAO MAC
```

Expected: returns an IP. (Hostname won't be `xiao-cam-001`/`002` because we now derive from MAC.)

- [ ] **Step 6: Commit**

```bash
git add xiao-citizen/xiao-citizen.ino xiao-citizen/board_config.h xiao-citizen/camera_pins.h xiao-citizen/app_httpd.cpp xiao-citizen/camera_index.h xiao-citizen/partitions.csv xiao-citizen/citizenry_identity.cpp
git commit -m "xiao-citizen: skeleton sketch boots, WiFi + NVS keypair + mDNS http"
```

### Task 1.2: Bind UDP unicast (ephemeral) and multicast listener

**Files:**
- Create: `linux-usb/xiao-citizen/citizenry_transport.h`
- Create: `linux-usb/xiao-citizen/citizenry_transport.cpp`
- Modify: `linux-usb/xiao-citizen/xiao-citizen.ino`

- [ ] **Step 1: Add the transport interface**

```cpp
// linux-usb/xiao-citizen/citizenry_transport.h
#pragma once
#include <WiFiUdp.h>
#include <functional>
#include <string>

class CitizenryTransport {
public:
    using OnPacket = std::function<void(const std::string&, IPAddress, uint16_t)>;

    bool begin(OnPacket cb);                                         // bind both sockets
    void poll();                                                     // call from loop()
    void send_multicast(const std::string& bytes);
    void send_unicast(const std::string& bytes, IPAddress ip, uint16_t port);
    uint16_t unicast_port() const { return _ucast_port; }

private:
    WiFiUDP _ucast;
    WiFiUDP _mcast;
    OnPacket _cb;
    uint16_t _ucast_port = 0;
};
```

- [ ] **Step 2: Implement it**

```cpp
// linux-usb/xiao-citizen/citizenry_transport.cpp
#include "citizenry_transport.h"
#include <Arduino.h>

static const char*    MCAST_GROUP = "239.67.84.90";
static const uint16_t MCAST_PORT  = 7770;

bool CitizenryTransport::begin(OnPacket cb) {
    _cb = cb;
    // Unicast: bind ephemeral
    if (!_ucast.begin(0)) { Serial.println("unicast bind failed"); return false; }
    _ucast_port = _ucast.localPort();
    Serial.printf("unicast bound to :%u\n", _ucast_port);

    // Multicast: join group
    IPAddress group;
    group.fromString(MCAST_GROUP);
    if (!_mcast.beginMulticast(group, MCAST_PORT)) {
        Serial.println("multicast bind failed");
        return false;
    }
    Serial.printf("multicast joined %s:%u\n", MCAST_GROUP, MCAST_PORT);
    return true;
}

void CitizenryTransport::poll() {
    char buf[2048];
    int n;
    while ((n = _mcast.parsePacket()) > 0) {
        n = _mcast.read((uint8_t*)buf, sizeof(buf));
        if (n > 0 && _cb) _cb(std::string(buf, n), _mcast.remoteIP(), _mcast.remotePort());
    }
    while ((n = _ucast.parsePacket()) > 0) {
        n = _ucast.read((uint8_t*)buf, sizeof(buf));
        if (n > 0 && _cb) _cb(std::string(buf, n), _ucast.remoteIP(), _ucast.remotePort());
    }
}

void CitizenryTransport::send_multicast(const std::string& bytes) {
    IPAddress group; group.fromString(MCAST_GROUP);
    _mcast.beginPacket(group, MCAST_PORT);
    _mcast.write((const uint8_t*)bytes.data(), bytes.size());
    _mcast.endPacket();
}

void CitizenryTransport::send_unicast(const std::string& bytes, IPAddress ip, uint16_t port) {
    _ucast.beginPacket(ip, port);
    _ucast.write((const uint8_t*)bytes.data(), bytes.size());
    _ucast.endPacket();
}
```

- [ ] **Step 3: Wire it into the sketch**

Add to `xiao-citizen.ino` after the WiFi block:

```cpp
#include "citizenry_transport.h"
static CitizenryTransport g_xport;

// in setup() after Identity init:
g_xport.begin([](const std::string& bytes, IPAddress ip, uint16_t port) {
    Serial.printf("[recv %u bytes from %s:%u]\n", (unsigned)bytes.size(), ip.toString().c_str(), port);
});
Serial.printf("transport ready, unicast=:%u\n", g_xport.unicast_port());

// in loop():
void loop() { g_xport.poll(); delay(2); }
```

- [ ] **Step 4: Compile + flash + observe**

Compile + flash as in Task 1.1 Step 4-5. Then from the Surface:

```bash
# Send a test multicast packet so the XIAO logs it
python3 -c "
import socket, struct
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
s.sendto(b'hello-from-surface', ('239.67.84.90', 7770))
"
```

On the XIAO Serial (UART pins, won't show via /dev/ttyACM0 — connect a logic analyzer or USB-TTL adapter for visibility, OR temporarily change `Serial.printf` to `g_xport.send_multicast(...)` for self-loopback verification).

**Practical alternative to wiring up UART**: the XIAO logs a packet by re-broadcasting an ack. Modify the callback to:
```cpp
g_xport.send_multicast("ack: " + bytes);
```
and listen on the Surface for the echo:
```bash
python3 -c "
import socket, struct
g = '239.67.84.90'; p = 7770
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', p))
s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack('4sL', socket.inet_aton(g), socket.INADDR_ANY))
s.sendto(b'ping', (g, p))
print(s.recv(2048))
"
```

Expected: `b'ack: ping'` (echoed by the XIAO).

- [ ] **Step 5: Remove the echo hack, keep the print, commit**

```bash
git add xiao-citizen/citizenry_transport.h xiao-citizen/citizenry_transport.cpp xiao-citizen/xiao-citizen.ino
git commit -m "xiao-citizen: UDP multicast + unicast transport, echo-tested round-trip"
```

### Task 1.3: mDNS service registration with citizenry TXT records

**Files:**
- Modify: `linux-usb/xiao-citizen/xiao-citizen.ino`

- [ ] **Step 1: Register the citizenry mDNS service**

Replace the `MDNS.begin(...)` block in `setup()` with:

```cpp
if (MDNS.begin(g_name.c_str())) {
    // Citizenry service (matches Python mdns.py SERVICE_TYPE)
    MDNS.addService("armos-citizen", "udp", g_xport.unicast_port());
    MDNS.addServiceTxt("armos-citizen", "udp", "type", "sensor");
    MDNS.addServiceTxt("armos-citizen", "udp", "pubkey", g_identity.pubkey_hex().substring(0, 16).c_str());
    MDNS.addServiceTxt("armos-citizen", "udp", "caps", "video_stream,frame_capture");
    MDNS.addServiceTxt("armos-citizen", "udp", "version", "1");
    // Legacy HTTP for /capture, /stream
    MDNS.addService("http", "tcp", 80);
    Serial.println("mDNS armos-citizen registered");
}
```

- [ ] **Step 2: Compile, flash, verify with avahi-browse from the Surface**

```bash
avahi-browse -tr _armos-citizen._udp 2>&1 | head -20
```

Expected: an entry showing the XIAO's name, IP, port, and the four TXT properties.

- [ ] **Step 3: Verify the existing Python citizenry mDNS browser sees it**

On any Python citizen (Surface, Pi, Jetson), check journal:
```bash
sudo journalctl -u citizenry-surface --no-pager -n 20 | grep -i xiao-cam
```

Expected: `mDNS found: xiao-cam-XXXX (sensor) @ <ip>:<port>`. The Python side will then send DISCOVER on multicast. Our XIAO logs the packet but doesn't respond yet — that's Phase 2.

- [ ] **Step 4: Commit**

```bash
git add xiao-citizen/xiao-citizen.ino
git commit -m "xiao-citizen: mDNS armos-citizen service registration with TXT props

Surface governor mDNS browser now sees this XIAO as a sensor citizen.
DISCOVER replies come in Phase 2."
```

### Phase 1 acceptance

```
✓ Sketch compiles
✓ Boots and prints citizen name + pubkey to Serial
✓ Joins Bradley-Starlink, gets DHCP IP
✓ Loads existing NVS keypair OR generates fresh one
✓ avahi-browse on Surface shows the XIAO's _armos-citizen._udp service
✓ Python citizens log "mDNS found: xiao-cam-XXXX"
✓ Multicast packet echo round-trips on demand
✓ HTTP / and /capture still work (CameraWebServer code preserved)
```

---

## Phase 2 — MVP citizen (heartbeat, discover, advertise, govern ack)

After Phase 2, you can `sudo systemctl stop citizenry-wifi-cam.service` (or `cam2`) for the XIAO that was already converted, and the swarm still sees it as a neighbor.

### Phase 2 task list (summary, see code in Phase 0/1 patterns)

- **Task 2.1** — Wire the envelope codec into the dispatcher: parse incoming bytes, drop unknown types, log valid messages by type.
- **Task 2.2** — Send DISCOVER on boot (broadcast, body = `{name, type, unicast_port}`).
- **Task 2.3** — Schedule HEARTBEAT every 2 s with body `{name, state, health, unicast_port, uptime}`. Test: Surface log shows neighbor BACK after each beat.
- **Task 2.4** — Handle inbound DISCOVER → send unicast ADVERTISE with full caps body.
- **Task 2.5** — Handle inbound HEARTBEAT/ADVERTISE → maintain neighbor table with TTL.
- **Task 2.6** — Handle inbound GOVERN (constitution) → store in NVS, send ACK via REPORT.

For each task, the TDD pattern from Phase 0 applies: write a fixture-driven host test where possible (codec changes); otherwise an integration test using a Python harness that drives the XIAO over UDP. Avoid placeholder steps — use the same fixture vocabulary as Phase 0.

**Phase 2 acceptance:**
```
✓ Surface log shows: NEW NEIGHBOR: xiao-cam-XXXX [<hash>] @ ('<ip>', <port>) — ['video_stream', 'frame_capture']
✓ Surface log shows: CONSTITUTION received from xiao-cam-XXXX → ack received
✓ XIAO survives 5 minutes without DEGRADED state on the Surface neighbor table
✓ Pi-side citizenry-wifi-cam.service can be STOPPED without losing this XIAO from the mesh
```

---

## Phase 3 — Frame capture (PROPOSE → REPORT)

The actual point of all this. After Phase 3, the XIAO answers frame_capture proposals natively over UDP, encoded as a base64 JPEG inside a REPORT body.

### Phase 3 task list (summary)

- **Task 3.1** — Extract camera init from `app_httpd.cpp` into `camera_capture.{h,cpp}` with `bool capture_jpeg(std::string& out)`.
- **Task 3.2** — Add PROPOSE handler: when `body.task == "frame_capture"`, send ACCEPT_REJECT (accept), capture, send REPORT with base64-encoded JPEG. If task unsupported → ACCEPT_REJECT (reject, reason).
- **Task 3.3** — End-to-end test: Python script sends PROPOSE → expects REPORT with valid JPEG bytes within 500 ms; saves to `/tmp/xiao-from-citizenry.jpg`; opens with `file` and verifies dimensions.
- **Task 3.4** — Once verified for one XIAO, decommission its corresponding Pi-side proxy: `sudo systemctl stop citizenry-wifi-cam.service && sudo systemctl disable citizenry-wifi-cam.service`. Keep the WiFi MJPEG firmware alive for legacy HTTP access.
- **Task 3.5** — Repeat 3.4 for the second XIAO once it's flashed with the new firmware.

**Phase 3 acceptance:**
```
✓ scripted Python proposer hits each XIAO, gets a JPEG via REPORT in <500 ms
✓ both Pi-side citizenry-wifi-cam{,2}.service stopped, swarm still sees both XIAOs
✓ HTTP /capture still works (legacy fallback)
```

---

## Phase 4 — Hardening, OTA-prep, observability (optional, defer if time-constrained)

- Replay-attack protection (envelope timestamp window).
- Watchdog: reboot if WiFi or multicast quiet >30 s.
- Memory-bounded inbound queues.
- Power-cycle counter + boot-reason logged in NVS.
- TXT updates when capabilities change at runtime.
- 24-hour soak test with logged DEGRADED/BACK transitions.

---

## Self-review

**Spec coverage check:**

| Spec requirement | Where it's addressed |
|---|---|
| Replace `citizenry-wifi-cam.service` proxy on Pi | Phase 3, Tasks 3.4–3.5 |
| Replace `citizenry-wifi-cam2.service` proxy | Same |
| XIAO speaks existing wire protocol unchanged | Phase 0 nails canonical JSON; Phase 2 implements message types |
| Run on Pi 5 (arduino-cli builds, flash via /dev/ttyACM0) | Task 1.1 Step 4–5 |
| Two XIAOs, one binary, MAC-derived hostname | Task 1.1 Step 2 (`make_citizen_name()`) |
| Keep CameraWebServer HTTP `/capture` and `/stream` | Task 1.1 keeps `app_httpd.cpp`; sketch retains the HTTP server |
| Canonical-JSON interop is gating | Phase 0 entirely |
| Tests for sign/verify in both directions | Tasks 0.5, 0.6 |
| Identity persisted across reboots | Task 1.1 Step 3 (NVS) |

**Placeholder scan:** every step shows actual code or actual command output expected. No "TBD", no "fill in details". Only Phase 2 and Phase 3 are summarized rather than fully step-itemized; that's deliberate — Phase 0 is gating, and Phase 1 contains the structural patterns. Phases 2-3 follow the same shape and can be expanded in a separate planning pass after Phase 0 evidence is in.

**Type consistency:** `Envelope`, `Identity`, `CitizenryTransport`, `JsonValue`, `JsonObject` defined once and used throughout. Method names (`canonical_signable_bytes`, `pubkey_hex`, `sign_hex`, `verify_hex`, `body_set_string`, `body_set_int`, `unicast_port`) used consistently across tasks.

**Known intentional gaps:**
- Phase 4 (hardening) is sketched, not itemized. Suggest a separate plan once Phase 3 is shipping.
- OTA explicitly out of scope; will need its own plan.

---

## Execution handoff

**Plan complete and saved to `/home/bradley/linux-usb/citizenry/PLAN-xiao-true-citizen-v2.md`.**

Two execution options for next session:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Especially valuable for Phase 0 where each interop test is a single concrete deliverable.

**2. Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batched with checkpoints.

Which approach when you start the next session? My suggestion is start with subagent-driven for Phase 0 (interop is the biggest risk and benefits from focused subagents), then drop to inline for Phases 1-3 once the gating is proven.

A reasonable cadence:
- **Phase 0 + 1 (one focused day)** — interop locked, hardware boots and is mDNS-visible.
- **Phase 2 (one day)** — XIAOs in the mesh as real citizens.
- **Phase 3 (half day)** — frame_capture; Pi proxies decommissioned.
- **Phase 4 (defer; new plan)** — soak + hardening.
