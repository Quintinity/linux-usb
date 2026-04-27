// linux-usb/xiao-citizen/citizenry_identity.h
#pragma once
#include <cstdint>
#include <string>

class Identity {
public:
    void generate();                                 // make a fresh keypair (Phase 1 will use this on first boot)
    void from_seed(const std::string& seed_bytes);   // 32 bytes
    std::string pubkey_hex() const;
    std::string sign_hex(const std::string& msg) const;
    static bool verify_hex(const std::string& pubkey_hex,
                           const std::string& msg,
                           const std::string& sig_hex);

#ifndef ARDUINO_HOST_TEST
    bool load_from_nvs();    // populated in Phase 1 — uses Preferences on hardware
    void save_to_nvs() const;
#endif

    uint8_t priv_[64] = {0};   // Ed25519 expanded private key (64 bytes from rweather)
    uint8_t pub_[32]  = {0};
};
