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
constexpr double TTL_HEARTBEAT = 6.0;
constexpr double TTL_DISCOVER  = 5.0;
constexpr double TTL_ADVERTISE = 30.0;
constexpr double TTL_REPORT    = 60.0;

// Sign env in place, return wire bytes.
std::string finalize(const Identity& id, Envelope& env) {
    std::string canonical = canonical_signable_bytes(env);
    env.signature = id.sign_hex(canonical);
    return envelope_to_wire(env);
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
