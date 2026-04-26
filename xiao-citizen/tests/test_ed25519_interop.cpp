// linux-usb/xiao-citizen/tests/test_ed25519_interop.cpp
// For each fixture: derive keypair from signing_seed, sign canonical bytes,
// verify the signature matches Python's. Then verify Python's signature
// using only the verify_key.
#include "../citizenry_envelope.h"
#include "../citizenry_identity.h"
#include "fixture_loader.h"
#include <cstdio>
#include <string>

static int g_pass = 0, g_fail = 0;
static void check(const std::string& name, bool cond) {
    if (cond) { printf("PASS: %s\n", name.c_str()); g_pass++; }
    else      { printf("FAIL: %s\n", name.c_str()); g_fail++; }
}

int main() {
    auto fixtures = load_fixtures("fixtures.json");
    for (const auto& fx : fixtures) {
        // 1. Derive the keypair from the seed
        Identity id;
        id.from_seed(hex_decode(fx.signing_seed));
        check(fx.name + " pubkey matches", id.pubkey_hex() == fx.verify_key);

        // 2. Sign the canonical bytes with C++; expect exact same signature as Python's
        std::string canonical = canonical_signable_bytes(fx.envelope);
        std::string sig_cpp = id.sign_hex(canonical);
        check(fx.name + " sign matches python", sig_cpp == fx.signature);

        // 3. Verify Python's signature using only the public key
        bool ok = Identity::verify_hex(fx.verify_key, canonical, fx.signature);
        check(fx.name + " verify python sig", ok);

        // 4. Tampered bytes should fail
        std::string tampered = canonical;
        if (!tampered.empty()) tampered[0] ^= 0x01;
        bool tampered_ok = Identity::verify_hex(fx.verify_key, tampered, fx.signature);
        check(fx.name + " tamper detected", !tampered_ok);
    }
    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
