// linux-usb/xiao-citizen/tests/test_messages.cpp
//
// Phase 2.2-2.4 message builders. Every helper produces a fully signed
// wire envelope ready to drop into CitizenryTransport::send_*. The test
// strategy is round-trip: build → feed back through the dispatcher →
// assert the inbound type and body fields the swarm will see match the
// constructor inputs.

#include "../citizenry_dispatch.h"
#include "../citizenry_envelope.h"
#include "../citizenry_identity.h"
#include "../citizenry_messages.h"
#include "fixture_loader.h"
#include <cstdio>

static int g_pass = 0, g_fail = 0;
static void check(const std::string& name, bool cond) {
    if (cond) { printf("PASS: %s\n", name.c_str()); g_pass++; }
    else      { printf("FAIL: %s\n", name.c_str()); g_fail++; }
}

// Pull a string body field; return empty if missing or wrong kind. Helpers
// for int/double bodies are added as their respective builder tests land.
static std::string body_str(const JsonObject& b, const std::string& k) {
    auto it = b.find(k);
    if (it == b.end() || it->second.kind != JsonValue::String) return "";
    return it->second.s;
}
static long long body_int(const JsonObject& b, const std::string& k, long long def = -1) {
    auto it = b.find(k);
    if (it == b.end() || it->second.kind != JsonValue::Int) return def;
    return it->second.i;
}

int main() {
    // Use the fixture seed so signatures verify deterministically.
    Identity id;
    id.from_seed(hex_decode("c0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ff"));

    const std::string NAME = "xiao-cam-934c";
    const uint16_t    PORT = 51404;
    const double      NOW  = 1700000000.500;

    // ---- 2.2: DISCOVER ----
    {
        std::string wire = build_discover(id, NAME, PORT, NOW);
        check("discover non-empty", !wire.empty());

        InboundEnvelope captured;
        bool got = false;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; got = true; });
        DispatchResult r = disp.deliver(wire);
        check("discover delivered", r == DispatchResult::Delivered);
        check("discover type=2", captured.type == 2);
        check("discover sender == our pubkey", captured.sender == id.pubkey_hex());
        check("discover recipient broadcast", captured.recipient == "*");
        check("discover body.name", body_str(captured.body, "name") == NAME);
        check("discover body.type=sensor", body_str(captured.body, "type") == "sensor");
        check("discover body.unicast_port", body_int(captured.body, "unicast_port") == PORT);
        check("discover handler invoked", got);
    }

    // (2.3 HEARTBEAT, 2.4 ADVERTISE, 2.6 REPORT cases append below as the
    //  matching builders land — see commits in this branch's history.)

    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
