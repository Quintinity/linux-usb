// linux-usb/xiao-citizen/xiao-citizen.ino
//
// Phase 1 skeleton: boot, WiFi, NVS-backed Ed25519 identity, mDNS http.
// UDP transport and citizenry mDNS TXT records are added in Tasks 1.2/1.3.
//
// Hardware-only sketch. Host tests under tests/ exercise the codec/identity
// modules with -DARDUINO_HOST_TEST so they don't pull <WiFi.h> etc.

#include <WiFi.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include "esp_camera.h"
#include "board_config.h"
#include "camera_pins.h"
#include "citizenry_camera.h"
#include "citizenry_camera.h"
#include "citizenry_constitution_store.h"
#include "citizenry_dispatch.h"
#include "citizenry_identity.h"
#include "citizenry_messages.h"
#include "citizenry_transport.h"

// Defined in app_httpd.cpp — starts the legacy CameraWebServer on :80
// (/index, /capture, /status, ...) and the streaming server on :81.
// Must be called after WiFi joins and citizenry_camera_begin() succeeds;
// the registered URI handlers use the same mutexed grab API the citizenry
// path uses, so concurrent /capture and PROPOSE→REPORT requests are safe.
extern void startCameraServer();

// ===== build-time configuration =====
static const char* WIFI_SSID = "Bradley-Starlink";
static const char* WIFI_PSK  = "gjnl1105";

// Citizen name = "xiao-cam-" + last 4 hex of MAC (lowercase, no colons)
static String make_citizen_name() {
    uint8_t mac[6];
    WiFi.macAddress(mac);
    char buf[32];
    snprintf(buf, sizeof(buf), "xiao-cam-%02x%02x", mac[4], mac[5]);
    for (char* p = buf; *p; p++) if (*p >= 'A' && *p <= 'Z') *p += 32;
    return String(buf);
}

// Derive a deterministic per-device unicast port from the last two bytes of
// the MAC (range 50000-65535). Arduino WiFiUDP doesn't expose the OS-picked
// port when binding to 0, so we choose explicitly and announce via mDNS TXT.
static uint16_t make_unicast_port() {
    uint8_t mac[6];
    WiFi.macAddress(mac);
    uint16_t low = ((uint16_t)mac[4] << 8) | mac[5];
    return 50000u + (low % 15000u);
}

static Identity                       g_identity;
static String                         g_name;
static CitizenryTransport             g_xport;
static Dispatcher                     g_dispatcher;
static PreferencesConstitutionStore   g_constitution;
static HeartbeatScheduler             g_heartbeat;
static uint32_t                       g_boot_ms = 0;

// 3.4: thin Arduino adapter that lets handle_propose_frame_capture call
// the mutex'd OV2640 grab without dragging esp_camera into the host tests.
class XiaoCameraSource : public CameraSource {
public:
    bool grab(const uint8_t** b, size_t* l, uint16_t* w, uint16_t* h) override {
        _fb = citizenry_camera_grab(/*timeout_ms=*/1000);
        if (!_fb) return false;
        *b = _fb->buf;
        *l = _fb->len;
        *w = citizenry_camera_width();
        *h = citizenry_camera_height();
        return true;
    }
    void release() override {
        if (_fb) { citizenry_camera_release(_fb); _fb = nullptr; }
    }
    bool ready() const override { return citizenry_camera_ready(); }
private:
    camera_fb_t* _fb = nullptr;
};
static XiaoCameraSource g_camera_src;

// The reply port we ask the governor to use for the ack envelope. UDP is
// connectionless so the governor will actually reply to the *source* port
// of our outbound REPORT (i.e. our unicast socket); we still set this so
// the body shape matches the protocol.
static uint16_t                       g_unicast_port = 0;

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n=== xiao-citizen booting ===");

    // WiFi must be initialised before WiFi.macAddress() returns the real MAC;
    // otherwise it reads zeros and we end up with names like xiao-cam-0000.
    WiFi.mode(WIFI_STA);
    g_name = make_citizen_name();
    Serial.printf("citizen name: %s\n", g_name.c_str());

    WiFi.setHostname(g_name.c_str());
    WiFi.begin(WIFI_SSID, WIFI_PSK);
    Serial.print("WiFi");
    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 60) { delay(500); Serial.print('.'); tries++; }
    if (WiFi.status() != WL_CONNECTED) { Serial.println(" FAILED"); return; }
    Serial.printf("\nIP: %s\n", WiFi.localIP().toString().c_str());

    // Camera — Phase 3.0 wires the OV2640 lifecycle behind a mutex so the
    // legacy http /capture path and the citizenry PROPOSE→REPORT path can
    // coexist. Failure here is non-fatal: PROPOSE handlers will REJECT.
    if (!citizenry_camera_begin()) {
        Serial.println("camera_begin FAILED — frame_capture will REJECT");
    } else {
        Serial.printf("camera ready %ux%u jpg\n",
                      (unsigned)citizenry_camera_width(),
                      (unsigned)citizenry_camera_height());
        // Start the legacy CameraWebServer on :80 (and stream on :81). The
        // PROPOSE→REPORT frame_capture path returns a frame_url pointing at
        // the /capture endpoint — Arduino's WiFiUDP can't IP-fragment, so
        // sending a 30 KB JPEG inline over UDP fails silently. TCP via this
        // endpoint delivers reliably.
        startCameraServer();
        Serial.println("camera HTTP server up on :80 (/capture, /stream:81)");
    }

    // Identity
    if (!g_identity.load_from_nvs()) {
        Serial.println("no keypair in NVS, generating fresh one (one-time, ~1s)...");
        g_identity.generate();
        g_identity.save_to_nvs();
    }
    // pubkey_hex() returns std::string; convert for Arduino printf via .c_str()
    Serial.printf("pubkey: %s\n", g_identity.pubkey_hex().c_str());

    // Transport — UDP multicast group + per-device unicast socket on a
    // MAC-derived port (announced via mDNS TXT in Task 1.3).
    uint16_t ucast_port = make_unicast_port();
    g_unicast_port = ucast_port;

    // Dispatcher: the single inbound handler. Per-type routing happens here
    // — Phase 2 currently routes only GOVERN (Task 2.6); Phase 3 will add
    // PROPOSE. Other types (HEARTBEAT/ADVERTISE/DISCOVER) are observed but
    // not yet acted upon by the firmware.
    g_dispatcher.set_handler([](const InboundEnvelope& m) {
        switch (m.type) {
            case MsgType::GOVERN: {
                GovernAckTarget tgt;
                std::string ack = handle_govern(m, g_identity, g_constitution,
                                                g_unicast_port,
                                                (double)time(nullptr), tgt);
                if (ack.empty()) {
                    Serial.println("[govern] rejected (bad shape or save failed)");
                    return;
                }
                // Phase 2 firmware doesn't yet have the governor's source IP
                // wired through the dispatcher, so we broadcast the ack.
                // The governor accepts unicast replies on its own multicast
                // listener too — see citizenry/protocol.py recipient handling.
                g_xport.send_multicast(ack);
                Serial.printf("[govern] ack sent v=%d\n", tgt.constitution_version);
                break;
            }
            case MsgType::DISCOVER: {
                AdvertiseTarget tgt;
                if (!advertise_target_for_discover(m, g_unicast_port, tgt)) {
                    Serial.println("[discover] bad shape");
                    return;
                }
                std::string adv = build_advertise(g_identity, std::string(g_name.c_str()),
                                                  g_unicast_port, g_constitution.has(),
                                                  tgt.recipient_pubkey_hex,
                                                  (double)time(nullptr));
                // Source IP not piped through dispatcher (Phase 4 fix); reply via
                // multicast. The discoverer filters by recipient pubkey.
                g_xport.send_multicast(adv);
                Serial.println("[discover] advertised");
                break;
            }
            case MsgType::PROPOSE: {
                FrameCaptureTarget tgt;
                // Tell the handler the URL prefix (http://<our_ip>) so the
                // REPORT body advertises the right /capture endpoint. The
                // proposer fetches the JPEG over TCP — see citizenry_messages.h
                // build_report_frame_capture comment for why we don't inline
                // the JPEG over UDP.
                std::string base_url = std::string("http://") +
                    std::string(WiFi.localIP().toString().c_str());
                auto envs = handle_propose_frame_capture(
                    m, g_identity, g_camera_src,
                    g_unicast_port, (double)time(nullptr), tgt, base_url);
                // REPORT envelopes routinely exceed Ethernet MTU once the
                // base64'd JPEG is in the body (~30 KB). UDP multicast over
                // WiFi drops fragmented packets unreliably, so we unicast
                // every reply to the proposer's actual transport-layer
                // source — which Phase 4 source-IP plumbing made available
                // on InboundEnvelope. Falls back to multicast if the
                // dispatcher didn't capture a source (host tests, replays).
                IPAddress dst(m.source_ip);
                uint16_t  dst_port = m.source_port;
                bool can_unicast = (m.source_ip != 0 && dst_port != 0);
                for (const auto& e : envs) {
                    if (can_unicast) g_xport.send_unicast(e, dst, dst_port);
                    else             g_xport.send_multicast(e);
                }
                Serial.printf("[propose] task_id=%s emitted=%u via %s\n",
                              tgt.task_id.c_str(), (unsigned)envs.size(),
                              can_unicast ? "unicast" : "multicast");
                break;
            }
            default:
                Serial.printf("[recv envelope type=%d]\n", m.type);
                break;
        }
    });

    bool xport_ok = g_xport.begin([](const std::string& bytes, IPAddress ip, uint16_t port) {
        // Drop everything into the dispatcher; it parses, verifies, and
        // routes. The per-message logging happens inside the type switch.
        // Source IP/port are plumbed through so PROPOSE→REPORT can unicast.
        g_dispatcher.set_now((double)time(nullptr));
        DispatchResult r = g_dispatcher.deliver(bytes, (uint32_t)ip, port);
        if (r != DispatchResult::Delivered) {
            Serial.printf("[drop %s]\n", dispatch_result_name(r));
        }
    }, ucast_port);
    if (xport_ok) {
        Serial.printf("transport ready, unicast=:%u\n", g_xport.unicast_port());
    } else {
        Serial.println("transport begin FAILED");
    }

    // mDNS — citizenry service (matches Python mdns.py SERVICE_TYPE) +
    // legacy http for /capture and /stream from app_httpd.cpp.
    if (MDNS.begin(g_name.c_str())) {
        // pubkey_hex() returns std::string; substr() (not Arduino .substring())
        std::string pub16 = g_identity.pubkey_hex().substr(0, 16);
        MDNS.addService("armos-citizen", "udp", g_xport.unicast_port());
        MDNS.addServiceTxt("armos-citizen", "udp", "type", "sensor");
        MDNS.addServiceTxt("armos-citizen", "udp", "pubkey", pub16.c_str());
        MDNS.addServiceTxt("armos-citizen", "udp", "caps", "video_stream,frame_capture");
        MDNS.addServiceTxt("armos-citizen", "udp", "version", "1");
        MDNS.addService("http", "tcp", 80);
        Serial.println("mDNS armos-citizen registered");
    } else {
        Serial.println("MDNS.begin FAILED");
    }

    // Mark boot moment for uptime; send one-shot DISCOVER so live citizens
    // ADVERTISE back without waiting for our first heartbeat.
    g_boot_ms = millis();
    std::string disc = build_discover(g_identity, std::string(g_name.c_str()),
                                      g_unicast_port, (double)time(nullptr));
    g_xport.send_multicast(disc);
    Serial.println("DISCOVER broadcast");
}

void loop() {
    g_xport.poll();
    if (g_heartbeat.tick(millis())) {
        double uptime = (millis() - g_boot_ms) / 1000.0;
        std::string hb = build_heartbeat(g_identity, std::string(g_name.c_str()),
                                         g_unicast_port, uptime,
                                         (double)time(nullptr));
        g_xport.send_multicast(hb);
    }
    delay(2);
}
