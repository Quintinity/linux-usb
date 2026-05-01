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

    // Sub-2: source_ip / source_port are local-only metadata. Setting them on
    // an envelope MUST NOT change canonical_signable_bytes() or envelope_to_wire()
    // — otherwise every existing signature breaks and Python/C++ interop diverges.
    if (!fixtures.empty()) {
        Envelope copy = fixtures[0].envelope;
        std::string canonical_before = canonical_signable_bytes(copy);
        copy.source_ip = "192.168.1.42";
        copy.source_port = 50001;
        std::string canonical_after = canonical_signable_bytes(copy);
        check("source_fields_excluded_from_canonical", canonical_after, canonical_before);

        std::string wire = envelope_to_wire(copy);
        bool leaked = (wire.find("source_ip") != std::string::npos)
                   || (wire.find("source_port") != std::string::npos);
        check("source_fields_excluded_from_wire",
              leaked ? std::string("LEAKED") : std::string("OK"),
              std::string("OK"));
    }

    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
