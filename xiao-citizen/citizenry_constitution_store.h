// linux-usb/xiao-citizen/citizenry_constitution_store.h
//
// Phase 2.6: Arduino-only NVS-backed ConstitutionStore implementation.
//
// The interface (`ConstitutionStore`, `InMemoryConstitutionStore`) lives in
// citizenry_messages.h so host tests can link against it. The Preferences-
// backed implementation is hardware-only — it pulls <Preferences.h>, which
// in turn pulls the ESP-IDF NVS partition driver. We hide it behind the
// same ARDUINO_HOST_TEST guard the rest of the firmware uses so g++ on the
// laptop never touches it.
//
// Storage layout (NVS namespace "citizenry"):
//   key "cv"   : int32_t  constitution version
//   key "cb"   : string   canonical body bytes (the GOVERN's body sub-tree)
//   key "ch"   : uint8_t  1 == have-a-constitution, 0/missing == fresh boot
//
// The sketch instantiates one PreferencesConstitutionStore at file scope
// and passes a reference to it into the GOVERN routing lambda.

#pragma once

#ifndef ARDUINO_HOST_TEST

#include "citizenry_messages.h"
#include <Preferences.h>

class PreferencesConstitutionStore : public ConstitutionStore {
public:
    // The NVS namespace defaults to "citizenry" — same one the Identity uses
    // for its keypair, but with non-overlapping keys (kp/sk vs cv/cb/ch).
    explicit PreferencesConstitutionStore(const char* ns = "citizenry") : _ns(ns) {}

    bool save(int version, const std::string& canonical_body) override {
        Preferences p;
        if (!p.begin(_ns, /*readOnly=*/false)) return false;
        bool ok = true;
        ok &= (p.putInt("cv", version) == sizeof(int32_t));
        ok &= (p.putString("cb", canonical_body.c_str()) == canonical_body.size());
        ok &= (p.putUChar("ch", 1) == sizeof(uint8_t));
        p.end();
        return ok;
    }

    bool load(int& version, std::string& canonical_body) override {
        Preferences p;
        if (!p.begin(_ns, /*readOnly=*/true)) return false;
        if (p.getUChar("ch", 0) != 1) { p.end(); return false; }
        version = p.getInt("cv", 0);
        String body = p.getString("cb", "");
        canonical_body = std::string(body.c_str(), body.length());
        p.end();
        return true;
    }

    bool has() const override {
        // Preferences.begin is non-const; cast away (ESP32 Preferences API
        // does not expose a const peek path). Safe — read-only mode.
        Preferences p;
        if (!p.begin(_ns, /*readOnly=*/true)) return false;
        bool h = (p.getUChar("ch", 0) == 1);
        p.end();
        return h;
    }

private:
    const char* _ns;
};

#endif  // !ARDUINO_HOST_TEST
