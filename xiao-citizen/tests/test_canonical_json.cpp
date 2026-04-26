// linux-usb/xiao-citizen/tests/test_canonical_json.cpp (replace contents)
#include "../citizenry_envelope.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include "fixture_loader.h"   // small helper added next step

static int g_pass = 0, g_fail = 0;
static void check(const std::string& name, const std::string& got, const std::string& exp) {
    if (got == exp) { printf("PASS: %s\n", name.c_str()); g_pass++; }
    else { printf("FAIL: %s\n  got %zu bytes: %s\n  exp %zu bytes: %s\n",
                  name.c_str(), got.size(), got.c_str(), exp.size(), exp.c_str()); g_fail++; }
}

int main() {
    auto fixtures = load_fixtures("fixtures.json");
    if (fixtures.empty()) { fprintf(stderr, "no fixtures loaded\n"); return 2; }

    for (const auto& fx : fixtures) {
        std::string got = canonical_signable_bytes(fx.envelope);
        check(fx.name + " canonical_bytes", got, fx.signable_bytes);
    }
    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
