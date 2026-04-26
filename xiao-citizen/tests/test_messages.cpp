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

// Pull a string body field; return empty if missing or wrong kind.
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
static double body_dbl(const JsonObject& b, const std::string& k, double def = -1.0) {
    auto it = b.find(k);
    if (it == b.end() || it->second.kind != JsonValue::Double) return def;
    return it->second.d;
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

    // ---- 2.3: HEARTBEAT ----
    {
        std::string wire = build_heartbeat(id, NAME, PORT, /*uptime_secs=*/42.125, NOW);
        check("heartbeat non-empty", !wire.empty());
        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        check("heartbeat delivered", disp.deliver(wire) == DispatchResult::Delivered);
        check("heartbeat type=1", captured.type == 1);
        check("heartbeat recipient broadcast", captured.recipient == "*");
        check("heartbeat body.name", body_str(captured.body, "name") == NAME);
        check("heartbeat body.state=ok", body_str(captured.body, "state") == "ok");
        check("heartbeat body.health=1.0", body_dbl(captured.body, "health") == 1.0);
        check("heartbeat body.unicast_port", body_int(captured.body, "unicast_port") == PORT);
        // 42.125 round-trips through %.3f canonical losslessly.
        check("heartbeat body.uptime", body_dbl(captured.body, "uptime") == 42.125);
    }

    // ---- 2.3: HeartbeatScheduler cadence ----
    {
        HeartbeatScheduler sch(2000);
        // First tick at t=0 latches and emits.
        check("scheduler first tick beats", sch.tick(0));
        // Subsequent ticks within the period must NOT beat.
        check("scheduler t=500 silent",  !sch.tick(500));
        check("scheduler t=1000 silent", !sch.tick(1000));
        check("scheduler t=1999 silent", !sch.tick(1999));
        // Crossing the 2000ms boundary beats.
        check("scheduler t=2000 beats",   sch.tick(2000));
        // Then quiet again until 4000.
        check("scheduler t=2500 silent", !sch.tick(2500));
        check("scheduler t=3999 silent", !sch.tick(3999));
        check("scheduler t=4000 beats",   sch.tick(4000));
        // A long gap collapses to one beat (we don't catch up — the swarm
        // doesn't care about missed beats during boot/recovery).
        check("scheduler t=20000 beats",  sch.tick(20000));
        check("scheduler t=20100 silent",!sch.tick(20100));
    }

    // ---- 2.3: stale heartbeat (now > timestamp + ttl) is dropped ----
    {
        std::string wire = build_heartbeat(id, NAME, PORT, 1.0, NOW);
        Dispatcher disp;
        disp.set_now(NOW + 7.0);   // TTL_HEARTBEAT is 6.0 s
        disp.set_handler([](const InboundEnvelope&){});
        check("stale heartbeat dropped", disp.deliver(wire) == DispatchResult::DropExpired);
    }

    // (2.4 ADVERTISE, 2.6 REPORT cases append below as those builders land.)

    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
