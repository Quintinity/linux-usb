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

// (2.3 HEARTBEAT, 2.4 ADVERTISE, 2.6 REPORT govern_ack are added in the
//  subsequent commits in this branch.)
