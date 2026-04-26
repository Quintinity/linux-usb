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

// build_report_govern_ack (2.6) added later.
