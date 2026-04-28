// linux-usb/xiao-citizen/citizenry_dispatch.cpp
//
// See citizenry_dispatch.h for the contract. Implementation is deliberately
// dumb-pipe: parse → check known-pubkey-policy → verify Ed25519 → check TTL
// → check type whitelist → invoke handler. Every drop returns a distinct
// DispatchResult so the firmware can log per-reason counters.

#include "citizenry_dispatch.h"
#include "citizenry_identity.h"

#include <cstdio>

const char* dispatch_result_name(DispatchResult r) {
    switch (r) {
        case DispatchResult::Delivered:         return "Delivered";
        case DispatchResult::DropMalformed:     return "DropMalformed";
        case DispatchResult::DropBadSig:        return "DropBadSig";
        case DispatchResult::DropExpired:       return "DropExpired";
        case DispatchResult::DropUnknownType:   return "DropUnknownType";
        case DispatchResult::DropUnknownSender: return "DropUnknownSender";
    }
    return "?";
}

// Citizenry MessageType values (mirror protocol.MessageType).
static bool is_known_type(int t) {
    return t >= 1 && t <= 7;   // HEARTBEAT..GOVERN
}

DispatchResult Dispatcher::deliver(const std::string& wire_bytes) {
    return deliver(wire_bytes, /*source_ip=*/0, /*source_port=*/0);
}

DispatchResult Dispatcher::deliver(const std::string& wire_bytes,
                                   uint32_t source_ip,
                                   uint16_t source_port) {
    Envelope env;
    if (!envelope_from_wire(wire_bytes, env)) {
        return DispatchResult::DropMalformed;
    }
    if (!is_known_type(env.type)) {
        // Reject unknown types BEFORE expensive Ed25519 verification — saves
        // CPU on flooded multicast channels.
        return DispatchResult::DropUnknownType;
    }
    if (env.sender.empty() || env.signature.empty()) {
        return DispatchResult::DropMalformed;
    }
    if (_strict && !knows_sender(env.sender)) {
        return DispatchResult::DropUnknownSender;
    }
    // TTL check uses the dispatcher's injected clock. _now == 0 means
    // "not configured" — skip the check rather than reject everything.
    if (_now > 0.0 && _now > env.timestamp + env.ttl) {
        return DispatchResult::DropExpired;
    }
    // Trust-on-first-sight: signature is verified against the sender pubkey
    // carried in the envelope itself. A man-in-the-middle who can sign with
    // a different keypair will pass this check but be visible as a DIFFERENT
    // citizen pubkey, which is the same threat model Phase 1 already had.
    std::string canonical = canonical_signable_bytes(env);
    if (!Identity::verify_hex(env.sender, canonical, env.signature)) {
        return DispatchResult::DropBadSig;
    }
    // Auto-learn the sender even in non-strict mode so Task 2.5's neighbor
    // table can ask `knows_sender()` to filter table updates.
    _known.insert(env.sender);

    if (_handler) {
        InboundEnvelope m;
        m.version   = env.version;
        m.type      = env.type;
        m.sender    = env.sender;
        m.recipient = env.recipient;
        m.timestamp = env.timestamp;
        m.ttl       = env.ttl;
        m.body      = env.body;
        m.source_ip   = source_ip;
        m.source_port = source_port;
        _handler(m);
    }
    return DispatchResult::Delivered;
}
