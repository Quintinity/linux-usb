// linux-usb/xiao-citizen/tests/test_dispatch.cpp
//
// Phase 2.1: dispatcher takes raw inbound UDP bytes, parses the envelope,
// looks up the sender's pubkey in a known-neighbor table (or trusts on first
// sight), verifies the Ed25519 signature, drops malformed/unknown/expired
// envelopes, and routes valid ones to a per-type handler callback.
//
// Tests are fixture-driven: every fixture in fixtures.json carries a
// `wire_hex` field — the on-the-wire bytes Python's Envelope.to_bytes()
// produces. We feed those bytes to the dispatcher and assert it emits
// the right (type, body) pair to the handler. Tampered/expired bytes
// must be dropped.

#include "../citizenry_dispatch.h"
#include "../citizenry_envelope.h"
#include "../citizenry_identity.h"
#include "fixture_loader.h"
#include <cstdio>
#include <string>
#include <vector>

static int g_pass = 0, g_fail = 0;
static void check(const std::string& name, bool cond) {
    if (cond) { printf("PASS: %s\n", name.c_str()); g_pass++; }
    else      { printf("FAIL: %s\n", name.c_str()); g_fail++; }
}

// Capture handler invocations for assertion.
struct Captured {
    int type = -1;
    std::string sender;
    JsonObject body;
    int call_count = 0;
};

int main() {
    auto fixtures = load_fixtures("fixtures.json");
    if (fixtures.empty()) { fprintf(stderr, "no fixtures loaded\n"); return 2; }

    // ---- 1. Each fixture's wire bytes parse + verify + dispatch by type. ----
    for (const auto& fx : fixtures) {
        Captured cap;
        Dispatcher disp;
        disp.set_handler([&](const InboundEnvelope& m) {
            cap.type = m.type;
            cap.sender = m.sender;
            cap.body = m.body;
            cap.call_count++;
        });
        // Pretend `now` is well within the envelope's TTL window — fixtures
        // were generated with Python time.time(), so use the timestamp itself
        // as the dispatcher's clock (subtract a microsecond so it's not exactly
        // expired).
        disp.set_now(fx.envelope.timestamp);
        // Trust on first sight: dispatcher learns the sender pubkey from
        // the envelope itself (this matches Phase 2's TOFS policy).
        DispatchResult r = disp.deliver(fx.wire_bytes);

        check(fx.name + " parses+verifies", r == DispatchResult::Delivered);
        check(fx.name + " handler called", cap.call_count == 1);
        check(fx.name + " type matches", cap.type == fx.envelope.type);
        check(fx.name + " sender matches", cap.sender == fx.envelope.sender);
    }

    // ---- 2. Tampered wire bytes (flip one signature byte) → DropBadSig. ----
    {
        const auto& fx = fixtures.front();
        std::string wire = fx.wire_bytes;
        // Find the signature in the JSON and flip a hex digit.
        size_t pos = wire.find("\"signature\":\"");
        if (pos != std::string::npos) {
            // The hex digit just past "signature":" — toggle a bit.
            size_t digit_pos = pos + std::string("\"signature\":\"").size();
            wire[digit_pos] = (wire[digit_pos] == 'a') ? 'b' : 'a';
        }
        Captured cap;
        Dispatcher disp;
        disp.set_handler([&](const InboundEnvelope&) { cap.call_count++; });
        disp.set_now(fx.envelope.timestamp);
        DispatchResult r = disp.deliver(wire);
        check("tampered sig → DropBadSig", r == DispatchResult::DropBadSig);
        check("tampered sig → handler not called", cap.call_count == 0);
    }

    // ---- 3. Garbage bytes → DropMalformed. ----
    {
        Dispatcher disp;
        Captured cap;
        disp.set_handler([&](const InboundEnvelope&) { cap.call_count++; });
        disp.set_now(1700000000.0);
        DispatchResult r = disp.deliver("not even json");
        check("garbage → DropMalformed", r == DispatchResult::DropMalformed);
        check("garbage → handler not called", cap.call_count == 0);
    }

    // ---- 4. Unknown message type → DropUnknownType. ----
    {
        // Build a valid-looking envelope with type=99 using the fixture's
        // signing seed so the signature actually verifies, but the type is
        // outside the IntEnum.
        const auto& fx = fixtures.front();
        Identity id;
        id.from_seed(hex_decode(fx.signing_seed));
        Envelope e;
        e.version = 1;
        e.type = 99;
        e.sender = id.pubkey_hex();
        e.recipient = "*";
        e.timestamp = fx.envelope.timestamp;
        e.ttl = 6.0;
        e.body_set_string("note", "unknown");
        std::string canon = canonical_signable_bytes(e);
        e.signature = id.sign_hex(canon);
        std::string wire = envelope_to_wire(e);

        Captured cap;
        Dispatcher disp;
        disp.set_handler([&](const InboundEnvelope&) { cap.call_count++; });
        disp.set_now(fx.envelope.timestamp);
        DispatchResult r = disp.deliver(wire);
        check("type=99 → DropUnknownType", r == DispatchResult::DropUnknownType);
        check("type=99 → handler not called", cap.call_count == 0);
    }

    // ---- 5. Expired envelope (now > timestamp + ttl) → DropExpired. ----
    {
        const auto& fx = fixtures.front();
        Captured cap;
        Dispatcher disp;
        disp.set_handler([&](const InboundEnvelope&) { cap.call_count++; });
        // Way past TTL.
        disp.set_now(fx.envelope.timestamp + fx.envelope.ttl + 60.0);
        DispatchResult r = disp.deliver(fx.wire_bytes);
        check("expired → DropExpired", r == DispatchResult::DropExpired);
        check("expired → handler not called", cap.call_count == 0);
    }

    // ---- 6. Trust-on-first-sight: a known-pubkey table refuses unknown
    //         senders when strict mode is enabled. ----
    {
        const auto& fx = fixtures.front();
        Dispatcher disp;
        disp.set_strict_known_senders(true);   // require pubkey in known table
        Captured cap;
        disp.set_handler([&](const InboundEnvelope&) { cap.call_count++; });
        disp.set_now(fx.envelope.timestamp);

        // Strict & empty table → reject.
        DispatchResult r1 = disp.deliver(fx.wire_bytes);
        check("strict unknown → DropUnknownSender", r1 == DispatchResult::DropUnknownSender);
        check("strict unknown → handler not called", cap.call_count == 0);

        // After learning the sender, accept.
        disp.learn_sender(fx.envelope.sender);
        DispatchResult r2 = disp.deliver(fx.wire_bytes);
        check("strict known → Delivered", r2 == DispatchResult::Delivered);
        check("strict known → handler called", cap.call_count == 1);
    }

    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
