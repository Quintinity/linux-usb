// linux-usb/xiao-citizen/citizenry_dispatch.h
//
// Phase 2.1 dispatcher: turns raw inbound UDP bytes into a typed, verified
// InboundEnvelope handed off to a single user-supplied handler. Owns:
//
//   * envelope_from_wire() — parses the on-the-wire JSON
//   * signature verification (Identity::verify_hex) — using either the
//     envelope's `sender` field directly (TOFS) or a pre-loaded set of
//     known pubkeys when strict mode is on
//   * TTL check against an injectable clock
//   * type whitelist (1..7 per protocol.MessageType)
//
// Hardware and host both link this; nothing here pulls Arduino headers.

#pragma once

#include "citizenry_envelope.h"

#include <functional>
#include <cstdint>
#include <set>
#include <string>

// What the handler receives. Mirrors Envelope but stripped of signature
// (already verified) and exposed as const members.
struct InboundEnvelope {
    int version = 1;
    int type = 0;
    std::string sender;
    std::string recipient;
    double timestamp = 0.0;
    double ttl = 0.0;
    JsonObject body;
    // Phase 4 source-IP plumbing: transport-layer source so handlers can
    // unicast their reply (PROPOSE→REPORT especially needs this for >1 MTU
    // payloads). Set to 0/0 by host tests; firmware passes the real values.
    // Stored as uint32_t (host-order) + uint16_t to keep this header
    // free of <Arduino.h>; the sketch converts to IPAddress when sending.
    uint32_t source_ip = 0;
    uint16_t source_port = 0;
};

enum class DispatchResult {
    Delivered,
    DropMalformed,
    DropBadSig,
    DropExpired,
    DropUnknownType,
    DropUnknownSender,
};

// Friendly name for logging.
const char* dispatch_result_name(DispatchResult r);

class Dispatcher {
public:
    using Handler = std::function<void(const InboundEnvelope&)>;

    void set_handler(Handler h) { _handler = std::move(h); }

    // Inject the wall clock (unix seconds, double). Defaults to 0; firmware
    // wires this from time(nullptr) before each dispatch.
    void set_now(double now_unix_secs) { _now = now_unix_secs; }

    // Strict mode: reject envelopes whose sender pubkey we have never seen.
    // Default is OFF (trust-on-first-sight); Phase 4 may flip it ON globally.
    void set_strict_known_senders(bool s) { _strict = s; }

    // Add a pubkey to the known-sender set. Call this from the citizen's
    // Phase 2 logic when a DISCOVER/HEARTBEAT first reveals a new neighbor.
    void learn_sender(const std::string& pubkey_hex) {
        _known.insert(pubkey_hex);
    }

    bool knows_sender(const std::string& pubkey_hex) const {
        return _known.count(pubkey_hex) > 0;
    }

    // Decode + verify + dispatch. Returns the disposition.
    DispatchResult deliver(const std::string& wire_bytes);

    // Same, but stash the transport-layer source IP/port into the
    // InboundEnvelope handed to the handler. Firmware uses this to unicast
    // REPORT replies; host tests use the no-arg form.
    DispatchResult deliver(const std::string& wire_bytes,
                           uint32_t source_ip,
                           uint16_t source_port);

private:
    Handler _handler;
    double  _now = 0.0;
    bool    _strict = false;
    std::set<std::string> _known;
};
