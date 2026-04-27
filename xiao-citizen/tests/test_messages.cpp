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

    // ---- 2.4: ADVERTISE (unicast) ----
    {
        const std::string PEER = std::string(64, 'e');
        std::string wire = build_advertise(id, NAME, PORT, /*has_constitution=*/true, PEER, NOW);
        check("advertise non-empty", !wire.empty());
        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        check("advertise delivered", disp.deliver(wire) == DispatchResult::Delivered);
        check("advertise type=3", captured.type == 3);
        check("advertise recipient=peer", captured.recipient == PEER);
        check("advertise body.name", body_str(captured.body, "name") == NAME);
        check("advertise body.type=sensor", body_str(captured.body, "type") == "sensor");
        check("advertise body.state=ok", body_str(captured.body, "state") == "ok");
        check("advertise body.health=1.0", body_dbl(captured.body, "health") == 1.0);
        check("advertise body.unicast_port", body_int(captured.body, "unicast_port") == PORT);
        auto it = captured.body.find("capabilities");
        check("advertise body.capabilities exists", it != captured.body.end());
        bool caps_ok = false;
        if (it != captured.body.end() && it->second.kind == JsonValue::Array) {
            const auto& arr = it->second.a;
            caps_ok = (arr.size() == 2)
                   && arr[0].kind == JsonValue::String && arr[0].s == "video_stream"
                   && arr[1].kind == JsonValue::String && arr[1].s == "frame_capture";
        }
        check("advertise body.capabilities content", caps_ok);
        auto it2 = captured.body.find("has_constitution");
        check("advertise body.has_constitution=true",
              it2 != captured.body.end() && it2->second.kind == JsonValue::Bool && it2->second.b);
    }

    // ---- 2.4: ADVERTISE with has_constitution=false (post-boot, pre-govern) ----
    {
        const std::string PEER = std::string(64, 'd');
        std::string wire = build_advertise(id, NAME, PORT, /*has_constitution=*/false, PEER, NOW);
        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        check("advertise(false) delivered", disp.deliver(wire) == DispatchResult::Delivered);
        auto it = captured.body.find("has_constitution");
        check("advertise body.has_constitution=false",
              it != captured.body.end() && it->second.kind == JsonValue::Bool && !it->second.b);
    }

    // ---- 2.4: advertise_target_for_discover extracts recipient + reply port ----
    {
        // Build a DISCOVER with body.unicast_port=4242, then deliver it,
        // then ask the helper for the ADVERTISE target.
        std::string wire = build_discover(id, "peer-001", 4242, NOW);
        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        check("target: setup deliver", disp.deliver(wire) == DispatchResult::Delivered);
        AdvertiseTarget t;
        check("target: extracts ok", advertise_target_for_discover(captured, /*fallback*/0, t));
        check("target: recipient=sender", t.recipient_pubkey_hex == captured.sender);
        check("target: reply_port from body", t.reply_port == 4242);
    }

    // ---- 2.4: target falls back when DISCOVER body lacks unicast_port ----
    {
        // Build an oddball DISCOVER without unicast_port (legacy citizen).
        Envelope env;
        env.version   = 1;
        env.type      = 2;
        env.sender    = id.pubkey_hex();
        env.recipient = "*";
        env.timestamp = NOW;
        env.ttl       = 5.0;
        env.body_set_string("name", "old-citizen");
        env.signature = id.sign_hex(canonical_signable_bytes(env));
        std::string wire = envelope_to_wire(env);
        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        check("target-fallback: deliver", disp.deliver(wire) == DispatchResult::Delivered);
        AdvertiseTarget t;
        check("target-fallback: extracts ok",
              advertise_target_for_discover(captured, /*fallback*/9999, t));
        check("target-fallback: reply_port=9999", t.reply_port == 9999);
    }

    // ---- 2.4: target rejects non-DISCOVER inbound envelopes ----
    {
        // Heartbeat must not be turned into an advertise target.
        std::string wire = build_heartbeat(id, NAME, PORT, 1.0, NOW);
        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        disp.deliver(wire);
        AdvertiseTarget t;
        check("target rejects non-discover",
              !advertise_target_for_discover(captured, 0, t));
    }

    // ---- 2.6: build_report_govern_ack (unicast to governor) ----
    {
        const std::string GOVERNOR = std::string(64, 'a');
        std::string wire = build_report_govern_ack(id, /*version=*/3, GOVERNOR, NOW);
        check("govern_ack non-empty", !wire.empty());

        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        check("govern_ack delivered", disp.deliver(wire) == DispatchResult::Delivered);
        check("govern_ack type=6 (REPORT)", captured.type == 6);
        check("govern_ack sender == us",   captured.sender == id.pubkey_hex());
        check("govern_ack recipient=gov",  captured.recipient == GOVERNOR);
        check("govern_ack body.task=govern_ack",
              body_str(captured.body, "task") == "govern_ack");
        check("govern_ack body.result=success",
              body_str(captured.body, "result") == "success");
        check("govern_ack body.constitution_version=3",
              body_int(captured.body, "constitution_version") == 3);
    }

    // ---- 2.6: handle_govern happy path — receive GOVERN, persist, return ACK ----
    {
        // The governor is a different identity. We simulate the inbound by
        // building a GOVERN envelope on its behalf, delivering it through the
        // dispatcher (so signature verifies), capturing the InboundEnvelope,
        // then handing it to handle_govern.
        Identity governor;
        governor.from_seed(hex_decode(
            "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"));

        Envelope gov_env;
        gov_env.version   = 1;
        gov_env.type      = MsgType::GOVERN;
        gov_env.sender    = governor.pubkey_hex();
        gov_env.recipient = id.pubkey_hex();
        gov_env.timestamp = NOW;
        gov_env.ttl       = 3600.0;
        gov_env.body_set_string("type", "constitution");
        // Nested constitution body (matches Python's send_govern(...) shape).
        JsonValue cons; cons.kind = JsonValue::Object;
        JsonValue v_ver; v_ver.kind = JsonValue::Int; v_ver.i = 7;
        cons.o["version"] = v_ver;
        JsonValue v_articles; v_articles.kind = JsonValue::Array;
        cons.o["articles"] = v_articles;
        gov_env.body["constitution"] = cons;
        gov_env.signature = governor.sign_hex(canonical_signable_bytes(gov_env));
        std::string wire = envelope_to_wire(gov_env);

        InboundEnvelope inbound;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ inbound = m; });
        check("govern: setup delivered", disp.deliver(wire) == DispatchResult::Delivered);
        check("govern: setup type=7", inbound.type == 7);

        InMemoryConstitutionStore store;
        GovernAckTarget tgt;
        std::string ack_wire = handle_govern(inbound, id, store,
                                             /*fallback_reply_port=*/4242,
                                             NOW, tgt);
        check("govern: ack non-empty",         !ack_wire.empty());
        check("govern: store populated",        store.has());
        // Persistence carries through.
        int sv = 0; std::string sb;
        check("govern: store.load ok",          store.load(sv, sb));
        check("govern: persisted version=7",    sv == 7);
        check("govern: persisted body non-empty", !sb.empty());
        // Target is filled.
        check("govern: target recipient = governor",
              tgt.recipient_pubkey_hex == governor.pubkey_hex());
        check("govern: target reply_port = fallback",
              tgt.reply_port == 4242);
        check("govern: target version=7",        tgt.constitution_version == 7);

        // The returned wire bytes must dispatch as a valid REPORT govern_ack.
        InboundEnvelope ack;
        Dispatcher d2;
        d2.set_now(NOW);
        d2.set_handler([&](const InboundEnvelope& m){ ack = m; });
        check("govern: ack delivered",          d2.deliver(ack_wire) == DispatchResult::Delivered);
        check("govern: ack type=6",             ack.type == 6);
        check("govern: ack sender == us",       ack.sender == id.pubkey_hex());
        check("govern: ack recipient = gov",    ack.recipient == governor.pubkey_hex());
        check("govern: ack body.task",          body_str(ack.body, "task") == "govern_ack");
        check("govern: ack body.result",        body_str(ack.body, "result") == "success");
        check("govern: ack body.version=7",
              body_int(ack.body, "constitution_version") == 7);
    }

    // ---- 2.6: handle_govern accepts top-level body.version (sketch fallback) ----
    {
        // Some early Phase 2 governors may send a flatter body that places
        // `version` at the top level. The handler must still accept it.
        Identity governor;
        governor.from_seed(hex_decode(
            "1111111111111111111111111111111111111111111111111111111111111111"));
        Envelope gov_env;
        gov_env.version   = 1;
        gov_env.type      = MsgType::GOVERN;
        gov_env.sender    = governor.pubkey_hex();
        gov_env.recipient = id.pubkey_hex();
        gov_env.timestamp = NOW;
        gov_env.ttl       = 3600.0;
        gov_env.body_set_int("version", 2);
        gov_env.body_set_string("note", "flat-shape");
        gov_env.signature = governor.sign_hex(canonical_signable_bytes(gov_env));

        InboundEnvelope inbound;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ inbound = m; });
        disp.deliver(envelope_to_wire(gov_env));

        InMemoryConstitutionStore store;
        GovernAckTarget tgt;
        std::string ack = handle_govern(inbound, id, store, 1234, NOW, tgt);
        check("govern flat: ack non-empty", !ack.empty());
        check("govern flat: version=2",     tgt.constitution_version == 2);
    }

    // ---- 2.6: handle_govern rejects wrong message type ----
    {
        std::string wire = build_heartbeat(id, NAME, PORT, 1.0, NOW);
        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        disp.deliver(wire);

        InMemoryConstitutionStore store;
        GovernAckTarget tgt;
        std::string ack = handle_govern(captured, id, store, 1234, NOW, tgt);
        check("govern: rejects HEARTBEAT (returns empty)", ack.empty());
        check("govern: rejected → store untouched",        !store.has());
        check("govern: rejected → no recipient set",        tgt.recipient_pubkey_hex.empty());
    }

    // ---- 2.6: handle_govern rejects missing version ----
    {
        Identity governor;
        governor.from_seed(hex_decode(
            "2222222222222222222222222222222222222222222222222222222222222222"));
        Envelope gov_env;
        gov_env.version   = 1;
        gov_env.type      = MsgType::GOVERN;
        gov_env.sender    = governor.pubkey_hex();
        gov_env.recipient = id.pubkey_hex();
        gov_env.timestamp = NOW;
        gov_env.ttl       = 3600.0;
        gov_env.body_set_string("type", "constitution");
        // No constitution.version anywhere — body has only `type`.
        gov_env.signature = governor.sign_hex(canonical_signable_bytes(gov_env));

        InboundEnvelope inbound;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ inbound = m; });
        disp.deliver(envelope_to_wire(gov_env));

        InMemoryConstitutionStore store;
        GovernAckTarget tgt;
        std::string ack = handle_govern(inbound, id, store, 1234, NOW, tgt);
        check("govern: missing version rejected", ack.empty());
        check("govern: missing version → store untouched", !store.has());
    }

    // ---- 2.6: handle_govern rejects invalid version kind (string) ----
    {
        Identity governor;
        governor.from_seed(hex_decode(
            "3333333333333333333333333333333333333333333333333333333333333333"));
        Envelope gov_env;
        gov_env.version   = 1;
        gov_env.type      = MsgType::GOVERN;
        gov_env.sender    = governor.pubkey_hex();
        gov_env.recipient = id.pubkey_hex();
        gov_env.timestamp = NOW;
        gov_env.ttl       = 3600.0;
        gov_env.body_set_string("type", "constitution");
        // Constitution with version as a STRING — must be refused.
        JsonValue cons; cons.kind = JsonValue::Object;
        JsonValue v_ver; v_ver.kind = JsonValue::String; v_ver.s = "v1";
        cons.o["version"] = v_ver;
        gov_env.body["constitution"] = cons;
        gov_env.signature = governor.sign_hex(canonical_signable_bytes(gov_env));

        InboundEnvelope inbound;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ inbound = m; });
        disp.deliver(envelope_to_wire(gov_env));

        InMemoryConstitutionStore store;
        GovernAckTarget tgt;
        std::string ack = handle_govern(inbound, id, store, 1234, NOW, tgt);
        check("govern: string version rejected", ack.empty());
        check("govern: string version → store untouched", !store.has());
    }

    // ---- 3.1: build_accept (ACCEPT_REJECT type 5) ----
    {
        const std::string PROPOSER = std::string(64, 'b');
        std::string wire = build_accept(id, PROPOSER, /*task=*/"frame_capture",
                                        /*task_id=*/"abc-123", NOW);
        check("accept non-empty", !wire.empty());
        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        check("accept delivered (sig verifies)",
              disp.deliver(wire) == DispatchResult::Delivered);
        check("accept type=5 (ACCEPT_REJECT)", captured.type == MsgType::ACCEPT_REJECT);
        check("accept sender == us",   captured.sender == id.pubkey_hex());
        check("accept recipient = proposer", captured.recipient == PROPOSER);
        check("accept body.result=accept", body_str(captured.body, "result") == "accept");
        check("accept body.task=frame_capture", body_str(captured.body, "task") == "frame_capture");
        check("accept body.task_id=abc-123",   body_str(captured.body, "task_id") == "abc-123");
    }

    // ---- 3.1: build_reject (ACCEPT_REJECT type 5) ----
    {
        const std::string PROPOSER = std::string(64, 'c');
        std::string wire = build_reject(id, PROPOSER, "camera not available", NOW);
        check("reject non-empty", !wire.empty());
        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        check("reject delivered (sig verifies)",
              disp.deliver(wire) == DispatchResult::Delivered);
        check("reject type=5",        captured.type == MsgType::ACCEPT_REJECT);
        check("reject recipient",     captured.recipient == PROPOSER);
        check("reject body.result=reject", body_str(captured.body, "result") == "reject");
        check("reject body.reason",   body_str(captured.body, "reason") == "camera not available");
        // No task / task_id — those belong only on accept.
        check("reject body has no task",    captured.body.find("task")    == captured.body.end());
        check("reject body has no task_id", captured.body.find("task_id") == captured.body.end());
    }

    // ---- 3.2: build_report_frame_capture (REPORT type 6) ----
    {
        const std::string PROPOSER = std::string(64, 'd');
        // Synthetic 6-byte JPEG-shaped payload — content opaque to the builder.
        // base64 of {0xff,0xd8,0xff,0xe0,0xff,0xd9} == "/9j/4P/Z" (no padding;
        // 6 bytes = 8 base64 chars, exact fit).
        const uint8_t fake_jpg[] = {0xff, 0xd8, 0xff, 0xe0, 0xff, 0xd9};
        std::string wire = build_report_frame_capture(
            id, PROPOSER, /*task_id=*/"task-1",
            fake_jpg, sizeof(fake_jpg),
            /*width=*/320, /*height=*/240, NOW);
        check("frame_capture non-empty", !wire.empty());

        InboundEnvelope captured;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ captured = m; });
        check("frame_capture delivered (sig verifies)",
              disp.deliver(wire) == DispatchResult::Delivered);
        check("frame_capture type=6 (REPORT)", captured.type == MsgType::REPORT);
        check("frame_capture sender == us",     captured.sender == id.pubkey_hex());
        check("frame_capture recipient = proposer", captured.recipient == PROPOSER);
        check("frame_capture body.type=frame_capture",
              body_str(captured.body, "type") == "frame_capture");
        check("frame_capture body.task_id=task-1",
              body_str(captured.body, "task_id") == "task-1");
        check("frame_capture body.frame == base64(input)",
              body_str(captured.body, "frame") == "/9j/4P/Z");
        check("frame_capture body.width=320",  body_int(captured.body, "width")  == 320);
        check("frame_capture body.height=240", body_int(captured.body, "height") == 240);
        check("frame_capture body.timestamp",  body_dbl(captured.body, "timestamp") == NOW);
    }

    // ---- 3.2: b64 padding edge cases — 1-byte, 2-byte, 3-byte, larger ----
    {
        const std::string PROPOSER = std::string(64, 'e');
        // 1 byte → 4 chars with two = pads. base64("M") == "TQ==".
        const uint8_t one[]   = { 'M' };
        // 2 bytes → 4 chars with one = pad. base64("Ma") == "TWE=".
        const uint8_t two[]   = { 'M','a' };
        // 3 bytes → 4 chars no pad. base64("Man") == "TWFu".
        const uint8_t three[] = { 'M','a','n' };
        struct Case { const uint8_t* b; size_t n; const char* expect; const char* name; };
        Case cases[] = {
            { one,   1, "TQ==", "b64 1-byte" },
            { two,   2, "TWE=", "b64 2-byte" },
            { three, 3, "TWFu", "b64 3-byte" },
        };
        for (const auto& c : cases) {
            std::string wire = build_report_frame_capture(
                id, PROPOSER, "tid", c.b, c.n, 1, 1, NOW);
            InboundEnvelope cap;
            Dispatcher disp;
            disp.set_now(NOW);
            disp.set_handler([&](const InboundEnvelope& m){ cap = m; });
            check(std::string(c.name) + " delivered",
                  disp.deliver(wire) == DispatchResult::Delivered);
            check(std::string(c.name) + " encodes correctly",
                  body_str(cap.body, "frame") == c.expect);
        }
    }

    // ---- 3.2: empty payload encodes to empty string and still verifies ----
    {
        const std::string PROPOSER = std::string(64, 'f');
        std::string wire = build_report_frame_capture(
            id, PROPOSER, "empty", nullptr, 0, 0, 0, NOW);
        InboundEnvelope cap;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ cap = m; });
        check("empty payload delivered (sig verifies)",
              disp.deliver(wire) == DispatchResult::Delivered);
        check("empty payload frame=''", body_str(cap.body, "frame") == "");
    }

    // ---- 3.3: handle_propose_frame_capture happy path ----
    {
        // Stub camera that returns a fixed 6-byte payload.
        struct FakeCam : public CameraSource {
            bool grab(const uint8_t** b, size_t* l, uint16_t* w, uint16_t* h) override {
                static const uint8_t fake[] = {0xff,0xd8,0x01,0x02,0xff,0xd9};
                *b = fake; *l = sizeof(fake); *w = 320; *h = 240;
                _grabbed = true;
                return true;
            }
            void release() override { _released = true; }
            bool ready() const override { return true; }
            bool _grabbed = false, _released = false;
        } cam;

        // Build a signed PROPOSE on behalf of a separate proposer identity.
        Identity proposer;
        proposer.from_seed(hex_decode(
            "5555555555555555555555555555555555555555555555555555555555555555"));
        Envelope prop_env;
        prop_env.version   = 1;
        prop_env.type      = MsgType::PROPOSE;
        prop_env.sender    = proposer.pubkey_hex();
        prop_env.recipient = id.pubkey_hex();
        prop_env.timestamp = NOW;
        prop_env.ttl       = 10.0;
        prop_env.body_set_string("task",    "frame_capture");
        prop_env.body_set_string("task_id", "task-7");
        prop_env.signature = proposer.sign_hex(canonical_signable_bytes(prop_env));
        std::string wire = envelope_to_wire(prop_env);

        InboundEnvelope inbound;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ inbound = m; });
        check("propose: setup delivered", disp.deliver(wire) == DispatchResult::Delivered);
        check("propose: setup type=4",   inbound.type == MsgType::PROPOSE);

        FrameCaptureTarget tgt;
        auto envs = handle_propose_frame_capture(inbound, id, cam,
                                                 /*fallback_reply_port=*/4242,
                                                 NOW, tgt);
        check("propose: 2 envelopes returned", envs.size() == 2);
        // First: ACCEPT_REJECT accept
        InboundEnvelope a;
        Dispatcher d2;
        d2.set_now(NOW);
        d2.set_handler([&](const InboundEnvelope& m){ a = m; });
        check("propose: accept delivered", d2.deliver(envs[0]) == DispatchResult::Delivered);
        check("propose: accept type=5", a.type == MsgType::ACCEPT_REJECT);
        check("propose: accept body.result=accept",
              body_str(a.body, "result") == "accept");
        check("propose: accept body.task=frame_capture",
              body_str(a.body, "task") == "frame_capture");
        check("propose: accept body.task_id=task-7",
              body_str(a.body, "task_id") == "task-7");
        // Second: REPORT frame_capture
        InboundEnvelope r;
        Dispatcher d3;
        d3.set_now(NOW);
        d3.set_handler([&](const InboundEnvelope& m){ r = m; });
        check("propose: report delivered", d3.deliver(envs[1]) == DispatchResult::Delivered);
        check("propose: report type=6 (REPORT)", r.type == MsgType::REPORT);
        check("propose: report body.type=frame_capture",
              body_str(r.body, "type") == "frame_capture");
        check("propose: report body.task_id=task-7",
              body_str(r.body, "task_id") == "task-7");
        check("propose: report body.frame matches b64",
              body_str(r.body, "frame") == "/9gBAv/Z");
        check("propose: report body.width=320",  body_int(r.body, "width")  == 320);
        check("propose: report body.height=240", body_int(r.body, "height") == 240);
        // Both envelopes addressed to the proposer pubkey
        check("propose: accept recipient = proposer", a.recipient == proposer.pubkey_hex());
        check("propose: report recipient = proposer", r.recipient == proposer.pubkey_hex());
        // Camera lifecycle
        check("propose: camera grabbed",  cam._grabbed);
        check("propose: camera released", cam._released);
        // Target out-params
        check("propose: target proposer = sender", tgt.proposer_pubkey_hex == proposer.pubkey_hex());
        check("propose: target task_id = task-7",  tgt.task_id == "task-7");
        check("propose: target reply_port fallback", tgt.reply_port == 4242);
    }

    // ---- 3.3: rejects when camera is not ready ----
    {
        struct DeadCam : public CameraSource {
            bool grab(const uint8_t**, size_t*, uint16_t*, uint16_t*) override { return false; }
            void release() override {}
            bool ready() const override { return false; }
        } cam;

        Identity proposer;
        proposer.from_seed(hex_decode(
            "6666666666666666666666666666666666666666666666666666666666666666"));
        Envelope prop_env;
        prop_env.version   = 1;
        prop_env.type      = MsgType::PROPOSE;
        prop_env.sender    = proposer.pubkey_hex();
        prop_env.recipient = id.pubkey_hex();
        prop_env.timestamp = NOW;
        prop_env.ttl       = 10.0;
        prop_env.body_set_string("task",    "frame_capture");
        prop_env.body_set_string("task_id", "task-x");
        prop_env.signature = proposer.sign_hex(canonical_signable_bytes(prop_env));

        InboundEnvelope inbound;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ inbound = m; });
        disp.deliver(envelope_to_wire(prop_env));

        FrameCaptureTarget tgt;
        auto envs = handle_propose_frame_capture(inbound, id, cam, 0, NOW, tgt);
        check("propose-not-ready: 1 envelope (reject only)", envs.size() == 1);
        InboundEnvelope a;
        Dispatcher d2;
        d2.set_now(NOW);
        d2.set_handler([&](const InboundEnvelope& m){ a = m; });
        check("propose-not-ready: reject delivered", d2.deliver(envs[0]) == DispatchResult::Delivered);
        check("propose-not-ready: result=reject", body_str(a.body, "result") == "reject");
        check("propose-not-ready: reason mentions camera",
              body_str(a.body, "reason").find("camera") != std::string::npos);
    }

    // ---- 3.3: rejects unknown task name ----
    {
        struct UnusedCam : public CameraSource {
            bool grab(const uint8_t**, size_t*, uint16_t*, uint16_t*) override { return false; }
            void release() override {}
            bool ready() const override { return true; }
        } cam;

        Identity proposer;
        proposer.from_seed(hex_decode(
            "7777777777777777777777777777777777777777777777777777777777777777"));
        Envelope prop_env;
        prop_env.version   = 1;
        prop_env.type      = MsgType::PROPOSE;
        prop_env.sender    = proposer.pubkey_hex();
        prop_env.recipient = id.pubkey_hex();
        prop_env.timestamp = NOW;
        prop_env.ttl       = 10.0;
        prop_env.body_set_string("task",    "wash_the_dishes");
        prop_env.body_set_string("task_id", "task-y");
        prop_env.signature = proposer.sign_hex(canonical_signable_bytes(prop_env));

        InboundEnvelope inbound;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ inbound = m; });
        disp.deliver(envelope_to_wire(prop_env));

        FrameCaptureTarget tgt;
        auto envs = handle_propose_frame_capture(inbound, id, cam, 0, NOW, tgt);
        check("propose-unknown: 1 envelope (reject only)", envs.size() == 1);
        InboundEnvelope a;
        Dispatcher d2;
        d2.set_now(NOW);
        d2.set_handler([&](const InboundEnvelope& m){ a = m; });
        check("propose-unknown: reject delivered", d2.deliver(envs[0]) == DispatchResult::Delivered);
        check("propose-unknown: result=reject", body_str(a.body, "result") == "reject");
        check("propose-unknown: reason names task",
              body_str(a.body, "reason").find("wash_the_dishes") != std::string::npos);
    }

    // ---- 3.3: ignores non-PROPOSE messages (returns empty vector) ----
    {
        struct UnusedCam : public CameraSource {
            bool grab(const uint8_t**, size_t*, uint16_t*, uint16_t*) override { return false; }
            void release() override {}
            bool ready() const override { return true; }
        } cam;
        // Feed a heartbeat in.
        std::string wire = build_heartbeat(id, NAME, PORT, 1.0, NOW);
        InboundEnvelope inbound;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ inbound = m; });
        disp.deliver(wire);

        FrameCaptureTarget tgt;
        auto envs = handle_propose_frame_capture(inbound, id, cam, 0, NOW, tgt);
        check("propose-wrong-type: empty envelope vec", envs.empty());
        check("propose-wrong-type: target untouched", tgt.proposer_pubkey_hex.empty());
    }

    // ---- 3.3: capture failure after accept emits accept + failure REPORT ----
    {
        struct FailCam : public CameraSource {
            bool grab(const uint8_t**, size_t*, uint16_t*, uint16_t*) override { return false; }
            void release() override { _released = true; }
            bool ready() const override { return true; }
            bool _released = false;
        } cam;

        Identity proposer;
        proposer.from_seed(hex_decode(
            "8888888888888888888888888888888888888888888888888888888888888888"));
        Envelope prop_env;
        prop_env.version   = 1;
        prop_env.type      = MsgType::PROPOSE;
        prop_env.sender    = proposer.pubkey_hex();
        prop_env.recipient = id.pubkey_hex();
        prop_env.timestamp = NOW;
        prop_env.ttl       = 10.0;
        prop_env.body_set_string("task",    "frame_capture");
        prop_env.body_set_string("task_id", "task-fail");
        prop_env.signature = proposer.sign_hex(canonical_signable_bytes(prop_env));

        InboundEnvelope inbound;
        Dispatcher disp;
        disp.set_now(NOW);
        disp.set_handler([&](const InboundEnvelope& m){ inbound = m; });
        disp.deliver(envelope_to_wire(prop_env));

        FrameCaptureTarget tgt;
        auto envs = handle_propose_frame_capture(inbound, id, cam, 0, NOW, tgt);
        check("propose-fail: 2 envelopes (accept + failure REPORT)", envs.size() == 2);
        InboundEnvelope a, r;
        Dispatcher d2;
        d2.set_now(NOW);
        d2.set_handler([&](const InboundEnvelope& m){ a = m; });
        d2.deliver(envs[0]);
        Dispatcher d3;
        d3.set_now(NOW);
        d3.set_handler([&](const InboundEnvelope& m){ r = m; });
        d3.deliver(envs[1]);
        check("propose-fail: first is accept", body_str(a.body, "result") == "accept");
        check("propose-fail: second is REPORT", r.type == MsgType::REPORT);
        check("propose-fail: REPORT type=task_complete",
              body_str(r.body, "type") == "task_complete");
        check("propose-fail: REPORT result=failed",
              body_str(r.body, "result") == "failed");
        check("propose-fail: camera released even on failure", cam._released);
    }

    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
