// linux-usb/xiao-citizen/citizenry_messages.h
//
// Phase 2 message builders. Each helper takes the firmware's Identity plus
// the pieces of state the message body needs, and returns the on-the-wire
// JSON bytes ready to pass to CitizenryTransport::send_multicast() (broadcast
// shapes) or send_unicast() (targeted shapes).
//
// All builders sign with `id.sign_hex()` against the canonical signable
// bytes — the swarm's verifiers (Surface, Pi, Jetson, other XIAOs) all
// re-canonicalise before checking, so the wire form's float precision is
// not load-bearing.
//
// Default TTLs mirror citizenry/protocol.py:
//   HEARTBEAT 6 s, DISCOVER 5 s, ADVERTISE 30 s, REPORT 60 s.

#pragma once

#include "citizenry_dispatch.h"   // InboundEnvelope (forward-decl insufficient: AdvertiseTarget helper inspects body)
#include "citizenry_envelope.h"
#include "citizenry_identity.h"
#include <cstdint>
#include <string>

// MessageType enum mirror — kept here (rather than included from a shared
// header) because the dispatcher already validates 1..7 and the sketch
// doesn't need the enum for anything except picking which builder to call.
namespace MsgType {
    constexpr int HEARTBEAT     = 1;
    constexpr int DISCOVER      = 2;
    constexpr int ADVERTISE     = 3;
    constexpr int PROPOSE       = 4;
    constexpr int ACCEPT_REJECT = 5;
    constexpr int REPORT        = 6;
    constexpr int GOVERN        = 7;
}

// 2.2: DISCOVER (broadcast). Body: {name, type:"sensor", unicast_port}.
std::string build_discover(const Identity& id,
                           const std::string& citizen_name,
                           uint16_t unicast_port,
                           double now_unix_secs);

// 2.3: HEARTBEAT (broadcast). Body: {name, state, health, unicast_port, uptime}.
// Default cadence in the firmware loop is one beat per 2 s — see
// HeartbeatScheduler below for the pacing helper.
std::string build_heartbeat(const Identity& id,
                            const std::string& citizen_name,
                            uint16_t unicast_port,
                            double uptime_secs,
                            double now_unix_secs);

// Pure-logic 2 s cadence ticker. tick(now_ms) returns true iff a heartbeat
// is due at this tick (every 2000 ms after the first call). Lives outside
// the transport layer so it can be unit-tested with a synthetic clock.
class HeartbeatScheduler {
public:
    explicit HeartbeatScheduler(uint32_t period_ms = 2000) : _period_ms(period_ms) {}
    bool tick(uint32_t now_ms);     // returns true on each "beat now" boundary
    uint32_t period_ms() const { return _period_ms; }

private:
    uint32_t _period_ms;
    uint32_t _last_beat_ms = 0;
    bool     _started = false;
};

// 2.4: ADVERTISE (unicast). Body: {name, type, capabilities, health, state,
// unicast_port, has_constitution}. Recipient is the discoverer's pubkey
// hex; transport-layer destination IP is taken from the inbound DISCOVER's
// UDP source, transport-layer destination port from the body's
// `unicast_port` field (extract via advertise_target_for_discover).
std::string build_advertise(const Identity& id,
                            const std::string& citizen_name,
                            uint16_t unicast_port,
                            bool has_constitution,
                            const std::string& recipient_pubkey_hex,
                            double now_unix_secs);

// Pure-logic helper: given an inbound DISCOVER, return the recipient
// pubkey (always env.sender) and the unicast port to reply to (read from
// body.unicast_port, falling back to a caller-supplied default for
// older citizens that omit it). Returns false if the envelope isn't a
// DISCOVER or the body shape is wrong.
struct AdvertiseTarget {
    std::string recipient_pubkey_hex;
    uint16_t    reply_port = 0;
};
bool advertise_target_for_discover(const InboundEnvelope& m,
                                   uint16_t fallback_port,
                                   AdvertiseTarget& out);

// (2.6 REPORT govern_ack added in the subsequent commit in this branch.)
