// linux-usb/xiao-citizen/citizenry_identity.cpp
#include "citizenry_identity.h"
#ifdef ARDUINO_HOST_TEST
  // Host-only test build pulls the vendored rweather/Crypto sources.
  #include "tests/vendor/Crypto/Ed25519.h"
#else
  // Arduino build uses the installed rweather Crypto library.
  #include <Ed25519.h>
#endif
#include <cstdio>
#include <cstring>

static std::string to_hex(const uint8_t* b, size_t n) {
    static const char* H = "0123456789abcdef";
    std::string out; out.reserve(n * 2);
    for (size_t i = 0; i < n; i++) { out.push_back(H[b[i] >> 4]); out.push_back(H[b[i] & 0xF]); }
    return out;
}

static void from_hex(const std::string& h, uint8_t* out, size_t n) {
    for (size_t i = 0; i < n; i++) {
        unsigned int v;
        std::sscanf(h.c_str() + i * 2, "%2x", &v);
        out[i] = (uint8_t)v;
    }
}

void Identity::generate() {
    Ed25519::generatePrivateKey(priv_);
    Ed25519::derivePublicKey(pub_, priv_);
}

void Identity::from_seed(const std::string& seed_bytes) {
    // rweather's Ed25519 takes a 32-byte private key (the seed). Copy and derive pub.
    std::memcpy(priv_, seed_bytes.data(), 32);
    Ed25519::derivePublicKey(pub_, priv_);
}

std::string Identity::pubkey_hex() const {
    return to_hex(pub_, 32);
}

std::string Identity::sign_hex(const std::string& msg) const {
    uint8_t sig[64];
    Ed25519::sign(sig, priv_, pub_, msg.data(), msg.size());
    return to_hex(sig, 64);
}

bool Identity::verify_hex(const std::string& pubkey_hex,
                          const std::string& msg,
                          const std::string& sig_hex) {
    uint8_t pub[32], sig[64];
    if (pubkey_hex.size() != 64 || sig_hex.size() != 128) return false;
    from_hex(pubkey_hex, pub, 32);
    from_hex(sig_hex, sig, 64);
    return Ed25519::verify(sig, pub, msg.data(), msg.size());
}

#ifndef ARDUINO_HOST_TEST
#include <Preferences.h>

bool Identity::load_from_nvs() {
    Preferences prefs;
    if (!prefs.begin("xiao-citizen", true)) return false;
    size_t got = prefs.getBytes("priv", priv_, 32);
    prefs.end();
    if (got != 32) return false;
    Ed25519::derivePublicKey(pub_, priv_);
    return true;
}

void Identity::save_to_nvs() const {
    Preferences prefs;
    prefs.begin("xiao-citizen", false);
    prefs.putBytes("priv", priv_, 32);
    prefs.end();
}
#endif

