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
// Other TTLs (HEARTBEAT, ADVERTISE, REPORT) are introduced as their
// builders land in subsequent commits.
constexpr double TTL_DISCOVER  = 5.0;

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

// build_heartbeat (2.3), build_advertise (2.4), build_report_govern_ack
// (2.6) are added in their own commits below to keep each commit
// self-contained.
