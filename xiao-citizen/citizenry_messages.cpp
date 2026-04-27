// linux-usb/xiao-citizen/citizenry_messages.cpp
//
// Implementation of the Phase 2 message builders. Each helper builds an
// Envelope, signs it (canonical_signable_bytes → Identity::sign_hex), then
// hands back the wire bytes from envelope_to_wire(). The signing key is the
// firmware's only Identity; the dispatcher's own auto-learn covers our own
// pubkey for self-loopback paths during testing.

#include "citizenry_messages.h"

namespace {

// Default TTLs (seconds) — mirror citizenry/protocol.py constants.
constexpr double TTL_HEARTBEAT     = 6.0;
constexpr double TTL_DISCOVER      = 5.0;
constexpr double TTL_ADVERTISE     = 30.0;
constexpr double TTL_REPORT        = 60.0;
constexpr double TTL_ACCEPT_REJECT = 10.0;

// Sign env in place, return wire bytes.
std::string finalize(const Identity& id, Envelope& env) {
    std::string canonical = canonical_signable_bytes(env);
    env.signature = id.sign_hex(canonical);
    return envelope_to_wire(env);
}

// 3.2: minimal base64 encoder (standard alphabet, '=' padding). The Phase 3
// REPORT frame_capture body carries an OV2640 JPEG (~10–20 KB at QVGA q=12);
// the encoded string is ~4/3 of that and lives on the heap until the wire
// envelope is serialised. Decoder side is Python's base64.b64decode which
// expects canonical padding.
constexpr char B64_ALPHABET[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

std::string b64_encode(const uint8_t* data, size_t len) {
    std::string out;
    out.reserve(((len + 2) / 3) * 4);
    size_t i = 0;
    for (; i + 3 <= len; i += 3) {
        uint32_t v = ((uint32_t)data[i] << 16)
                   | ((uint32_t)data[i+1] << 8)
                   |  (uint32_t)data[i+2];
        out.push_back(B64_ALPHABET[(v >> 18) & 0x3f]);
        out.push_back(B64_ALPHABET[(v >> 12) & 0x3f]);
        out.push_back(B64_ALPHABET[(v >>  6) & 0x3f]);
        out.push_back(B64_ALPHABET[ v        & 0x3f]);
    }
    size_t rem = len - i;
    if (rem == 1) {
        uint32_t v = (uint32_t)data[i] << 16;
        out.push_back(B64_ALPHABET[(v >> 18) & 0x3f]);
        out.push_back(B64_ALPHABET[(v >> 12) & 0x3f]);
        out.push_back('=');
        out.push_back('=');
    } else if (rem == 2) {
        uint32_t v = ((uint32_t)data[i] << 16) | ((uint32_t)data[i+1] << 8);
        out.push_back(B64_ALPHABET[(v >> 18) & 0x3f]);
        out.push_back(B64_ALPHABET[(v >> 12) & 0x3f]);
        out.push_back(B64_ALPHABET[(v >>  6) & 0x3f]);
        out.push_back('=');
    }
    return out;
}

} // anon

std::string build_discover(const Identity& id,
                           const std::string& citizen_name,
                           uint16_t unicast_port,
                           double now_unix_secs) {
    Envelope env;
    env.version   = 1;
    env.type      = MsgType::DISCOVER;
    env.sender    = id.pubkey_hex();
    env.recipient = "*";
    env.timestamp = now_unix_secs;
    env.ttl       = TTL_DISCOVER;
    env.body_set_string("name", citizen_name);
    env.body_set_string("type", "sensor");
    env.body_set_int("unicast_port", unicast_port);
    return finalize(id, env);
}

std::string build_heartbeat(const Identity& id,
                            const std::string& citizen_name,
                            uint16_t unicast_port,
                            double uptime_secs,
                            double now_unix_secs) {
    Envelope env;
    env.version   = 1;
    env.type      = MsgType::HEARTBEAT;
    env.sender    = id.pubkey_hex();
    env.recipient = "*";
    env.timestamp = now_unix_secs;
    env.ttl       = TTL_HEARTBEAT;
    env.body_set_string("name", citizen_name);
    env.body_set_string("state", "ok");
    env.body_set_double("health", 1.0);
    env.body_set_int("unicast_port", unicast_port);
    env.body_set_double("uptime", uptime_secs);
    return finalize(id, env);
}

// HeartbeatScheduler. The first call latches the current clock and emits
// a beat (so the citizen announces itself promptly after boot); thereafter
// beats fire whenever (now_ms - last_beat_ms) >= period_ms. Wraparound of
// the 32-bit Arduino millis() clock is handled via unsigned subtraction —
// the math stays correct for any non-negative elapsed interval up to ~49 days.
bool HeartbeatScheduler::tick(uint32_t now_ms) {
    if (!_started) {
        _started = true;
        _last_beat_ms = now_ms;
        return true;
    }
    if ((uint32_t)(now_ms - _last_beat_ms) >= _period_ms) {
        _last_beat_ms = now_ms;
        return true;
    }
    return false;
}

std::string build_advertise(const Identity& id,
                            const std::string& citizen_name,
                            uint16_t unicast_port,
                            bool has_constitution,
                            const std::string& recipient_pubkey_hex,
                            double now_unix_secs) {
    Envelope env;
    env.version   = 1;
    env.type      = MsgType::ADVERTISE;
    env.sender    = id.pubkey_hex();
    env.recipient = recipient_pubkey_hex;
    env.timestamp = now_unix_secs;
    env.ttl       = TTL_ADVERTISE;
    env.body_set_string("name", citizen_name);
    env.body_set_string("type", "sensor");
    env.body_set_double("health", 1.0);
    env.body_set_string("state", "ok");
    env.body_set_int("unicast_port", unicast_port);
    env.body_set_bool("has_constitution", has_constitution);
    // capabilities array — XIAO Sense exposes both the streaming (Phase 1
    // legacy /stream) and the citizenry-native frame_capture (Phase 3) paths.
    JsonValue caps; caps.kind = JsonValue::Array;
    JsonValue v1; v1.kind = JsonValue::String; v1.s = "video_stream";
    JsonValue v2; v2.kind = JsonValue::String; v2.s = "frame_capture";
    caps.a.push_back(v1);
    caps.a.push_back(v2);
    env.body["capabilities"] = caps;
    return finalize(id, env);
}

bool advertise_target_for_discover(const InboundEnvelope& m,
                                   uint16_t fallback_port,
                                   AdvertiseTarget& out) {
    if (m.type != MsgType::DISCOVER) return false;
    if (m.sender.empty()) return false;
    out.recipient_pubkey_hex = m.sender;
    auto it = m.body.find("unicast_port");
    if (it != m.body.end() && it->second.kind == JsonValue::Int) {
        long long p = it->second.i;
        // Defensive clamp — Python serializes any int into the body.
        if (p > 0 && p <= 65535) {
            out.reply_port = (uint16_t)p;
            return true;
        }
    }
    out.reply_port = fallback_port;
    return true;
}

std::string build_report_govern_ack(const Identity& id,
                                    int constitution_version,
                                    const std::string& governor_pubkey_hex,
                                    double now_unix_secs) {
    Envelope env;
    env.version   = 1;
    env.type      = MsgType::REPORT;
    env.sender    = id.pubkey_hex();
    env.recipient = governor_pubkey_hex;
    env.timestamp = now_unix_secs;
    env.ttl       = TTL_REPORT;
    env.body_set_string("task", "govern_ack");
    env.body_set_string("result", "success");
    env.body_set_int("constitution_version", constitution_version);
    return finalize(id, env);
}

// 3.1: ACCEPT_REJECT (type 5). The body shape mirrors the Pi-side
// CameraCitizen.send_accept / send_reject — proposer correlates by task_id.
std::string build_accept(const Identity& id,
                         const std::string& proposer_pubkey_hex,
                         const std::string& task,
                         const std::string& task_id,
                         double now_unix_secs) {
    Envelope env;
    env.version   = 1;
    env.type      = MsgType::ACCEPT_REJECT;
    env.sender    = id.pubkey_hex();
    env.recipient = proposer_pubkey_hex;
    env.timestamp = now_unix_secs;
    env.ttl       = TTL_ACCEPT_REJECT;
    env.body_set_string("result", "accept");
    env.body_set_string("task", task);
    env.body_set_string("task_id", task_id);
    return finalize(id, env);
}

std::string build_reject(const Identity& id,
                         const std::string& proposer_pubkey_hex,
                         const std::string& reason,
                         double now_unix_secs) {
    Envelope env;
    env.version   = 1;
    env.type      = MsgType::ACCEPT_REJECT;
    env.sender    = id.pubkey_hex();
    env.recipient = proposer_pubkey_hex;
    env.timestamp = now_unix_secs;
    env.ttl       = TTL_ACCEPT_REJECT;
    env.body_set_string("result", "reject");
    env.body_set_string("reason", reason);
    return finalize(id, env);
}

// 3.2: REPORT frame_capture. The body is the same shape Pi-side
// CameraCitizen.send_report_frame_capture emits, so a Surface harness or
// any other proposer can correlate by task_id without protocol changes.
std::string build_report_frame_capture(const Identity& id,
                                       const std::string& proposer_pubkey_hex,
                                       const std::string& task_id,
                                       const uint8_t* jpeg_buf,
                                       size_t jpeg_len,
                                       uint16_t width,
                                       uint16_t height,
                                       double now_unix_secs) {
    Envelope env;
    env.version   = 1;
    env.type      = MsgType::REPORT;
    env.sender    = id.pubkey_hex();
    env.recipient = proposer_pubkey_hex;
    env.timestamp = now_unix_secs;
    env.ttl       = TTL_REPORT;
    env.body_set_string("type", "frame_capture");
    env.body_set_string("task_id", task_id);
    env.body_set_string("frame", b64_encode(jpeg_buf, jpeg_len));
    env.body_set_int("width",  width);
    env.body_set_int("height", height);
    // XIAO has no RTC, so this is seconds-since-boot when called from the
    // Arduino path. Phase 4 SNTP will replace with wallclock.
    env.body_set_double("timestamp", now_unix_secs);
    return finalize(id, env);
}

// 3.3: PROPOSE handler. Splits hardware concerns out via CameraSource so
// the host tests don't pull esp_camera. Caveat: the dispatcher hasn't been
// extended to plumb source IP through InboundEnvelope yet (Phase 4) so the
// caller in the sketch unicasts via multicast — recipient pubkey filtering
// keeps it correct, just noisier.
std::vector<std::string>
handle_propose_frame_capture(const InboundEnvelope& m,
                             const Identity& id,
                             CameraSource& cam,
                             uint16_t fallback_reply_port,
                             double now_unix_secs,
                             FrameCaptureTarget& out) {
    std::vector<std::string> result;
    out.proposer_pubkey_hex.clear();
    out.reply_port = 0;
    out.task_id.clear();

    if (m.type != MsgType::PROPOSE) return result;
    if (m.sender.empty())            return result;

    // Pull task / task_id from the body. body shape:
    //   {task: "frame_capture", task_id: "..."}
    std::string task, task_id;
    auto it_task = m.body.find("task");
    if (it_task != m.body.end() && it_task->second.kind == JsonValue::String)
        task = it_task->second.s;
    auto it_tid = m.body.find("task_id");
    if (it_tid != m.body.end() && it_tid->second.kind == JsonValue::String)
        task_id = it_tid->second.s;

    out.proposer_pubkey_hex = m.sender;
    out.reply_port          = fallback_reply_port;
    out.task_id             = task_id;

    if (task != "frame_capture") {
        result.push_back(build_reject(id, m.sender,
                                      "unknown task: " + task,
                                      now_unix_secs));
        return result;
    }
    if (!cam.ready()) {
        result.push_back(build_reject(id, m.sender,
                                      "camera not available",
                                      now_unix_secs));
        return result;
    }

    // Commit to the work — emit ACCEPT first so the proposer's state machine
    // doesn't time out while we grab/encode (~50–200 ms on hardware).
    result.push_back(build_accept(id, m.sender, "frame_capture",
                                  task_id, now_unix_secs));

    const uint8_t* buf = nullptr;
    size_t         len = 0;
    uint16_t       w = 0, h = 0;
    if (!cam.grab(&buf, &len, &w, &h)) {
        // Capture failed AFTER we accepted. Keep the ACCEPT, attach a
        // failure REPORT so the proposer's state machine resolves cleanly
        // (rather than waiting out a TTL).
        Envelope env;
        env.version   = 1;
        env.type      = MsgType::REPORT;
        env.sender    = id.pubkey_hex();
        env.recipient = m.sender;
        env.timestamp = now_unix_secs;
        env.ttl       = TTL_REPORT;
        env.body_set_string("type",    "task_complete");
        env.body_set_string("task_id", task_id);
        env.body_set_string("result",  "failed");
        env.body_set_string("reason",  "frame capture failed");
        result.push_back(finalize(id, env));
        cam.release();
        return result;
    }
    result.push_back(build_report_frame_capture(id, m.sender, task_id,
                                                buf, len, w, h,
                                                now_unix_secs));
    cam.release();
    return result;
}

// Re-emit a sub-tree of the body in canonical form so we cache the exact bytes
// that signed the GOVERN. This isn't a perfect serialization (it doesn't
// include the envelope wrapper, only the inner body) but it's deterministic
// and stable enough for the v1 store format. Phase 4 may upgrade to keeping
// the full canonical_signable_bytes + signature pair instead.
namespace {
std::string canonical_body_only(const JsonObject& body) {
    Envelope tmp;
    tmp.version = 0; tmp.type = 0; tmp.sender = ""; tmp.recipient = "";
    tmp.timestamp = 0.0; tmp.ttl = 0.0;
    tmp.body = body;
    // Strip back to just the body's canonical map. canonical_signable_bytes
    // emits the full envelope; we slice the body sub-string out by simply
    // re-canonicalising the body itself via a fresh envelope-with-empty-
    // outer-fields and grabbing its '"body":<stuff>' substring. Cheaper:
    // run write_canonical against the body directly. We re-use envelope
    // canonicalisation indirectly here — a future commit may expose
    // canonical_object_bytes() publicly.
    std::string full = canonical_signable_bytes(tmp);
    auto pos = full.find("\"body\":");
    if (pos == std::string::npos) return "";
    return full.substr(pos + 7);   // after "body":
}
} // anon

std::string handle_govern(const InboundEnvelope& m,
                          const Identity& id,
                          ConstitutionStore& store,
                          uint16_t fallback_reply_port,
                          double now_unix_secs,
                          GovernAckTarget& out) {
    out.recipient_pubkey_hex.clear();
    out.reply_port = 0;
    out.constitution_version = 0;
    if (m.type != MsgType::GOVERN) return "";
    if (m.sender.empty()) return "";
    // The Python governor (surface_citizen) sends GOVERN with body shape
    //   {type:"constitution", constitution:{version:N, articles:[...], ...}}
    // so the version lives one level down. Older test governors that wrap
    // the constitution flat in the body (just {version:N, note:...}) are
    // also accepted as a backwards-compat shortcut.
    int version = 0;
    bool found = false;
    auto cit = m.body.find("constitution");
    if (cit != m.body.end() && cit->second.kind == JsonValue::Object) {
        auto vit = cit->second.o.find("version");
        if (vit != cit->second.o.end() && vit->second.kind == JsonValue::Int) {
            version = (int)vit->second.i;
            found = true;
        }
    }
    if (!found) {
        auto vit = m.body.find("version");
        if (vit != m.body.end() && vit->second.kind == JsonValue::Int) {
            version = (int)vit->second.i;
            found = true;
        }
    }
    if (!found) {
        // GOVERN with no resolvable version is malformed enough to refuse.
        return "";
    }
    std::string canonical = canonical_body_only(m.body);
    if (!store.save(version, canonical)) return "";

    out.recipient_pubkey_hex = m.sender;
    out.reply_port = fallback_reply_port;   // governor's reply port from sketch state
    out.constitution_version = version;
    return build_report_govern_ack(id, version, m.sender, now_unix_secs);
}
