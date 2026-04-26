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
#include "citizenry_identity.h"

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

static Identity g_identity;
static String   g_name;

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n=== xiao-citizen booting ===");

    g_name = make_citizen_name();
    Serial.printf("citizen name: %s\n", g_name.c_str());

    // WiFi
    WiFi.mode(WIFI_STA);
    WiFi.setHostname(g_name.c_str());
    WiFi.begin(WIFI_SSID, WIFI_PSK);
    Serial.print("WiFi");
    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 60) { delay(500); Serial.print('.'); tries++; }
    if (WiFi.status() != WL_CONNECTED) { Serial.println(" FAILED"); return; }
    Serial.printf("\nIP: %s\n", WiFi.localIP().toString().c_str());

    // Identity
    if (!g_identity.load_from_nvs()) {
        Serial.println("no keypair in NVS, generating fresh one (one-time, ~1s)...");
        g_identity.generate();
        g_identity.save_to_nvs();
    }
    // pubkey_hex() returns std::string; convert for Arduino printf via .c_str()
    Serial.printf("pubkey: %s\n", g_identity.pubkey_hex().c_str());

    // mDNS — TXT records and citizenry service get added in Task 1.3
    if (MDNS.begin(g_name.c_str())) {
        MDNS.addService("http", "tcp", 80);
        Serial.println("mDNS started");
    }
}

void loop() { delay(1000); }
