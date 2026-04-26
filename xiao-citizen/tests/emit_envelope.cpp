// linux-usb/xiao-citizen/tests/emit_envelope.cpp — small helper, not a test
#include "../citizenry_envelope.h"
#include "../citizenry_identity.h"
#include "fixture_loader.h"
#include <cstdio>
#include <iostream>
int main() {
    // Use the same test seed Python uses
    Identity id;
    std::string seed = hex_decode("c0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ff");
    id.from_seed(seed);

    Envelope env;
    env.version = 1; env.type = 1;
    env.sender = id.pubkey_hex();
    env.recipient = "*";
    env.timestamp = 1700000000.123;
    env.ttl = 6.0;
    env.body_set_string("name", "xiao-roundtrip");
    env.body_set_int("port", 12345);

    std::string canonical = canonical_signable_bytes(env);
    env.signature = id.sign_hex(canonical);

    // Print one JSON object Python can parse: {envelope, canonical_hex, signature, pubkey}.
    // Use %.3f for timestamp/ttl so they survive Python's json.loads as floats with the
    // same precision the C++ canonical bytes used (otherwise the Python side will see
    // e.g. "6" int and re-encode as "6" instead of "6.000", breaking signature match).
    char ts_buf[64], ttl_buf[64];
    std::snprintf(ts_buf, sizeof(ts_buf), "%.3f", env.timestamp);
    std::snprintf(ttl_buf, sizeof(ttl_buf), "%.3f", env.ttl);
    std::cout << "{"
              << "\"envelope\":{"
                << "\"version\":" << env.version
                << ",\"type\":" << env.type
                << ",\"sender\":\"" << env.sender << "\""
                << ",\"recipient\":\"" << env.recipient << "\""
                << ",\"timestamp\":" << ts_buf
                << ",\"ttl\":" << ttl_buf
                << ",\"body\":{\"name\":\"xiao-roundtrip\",\"port\":12345}"
              << "},"
              << "\"canonical_hex\":\"";
    for (char c : canonical) { char buf[3]; std::snprintf(buf, sizeof(buf), "%02x", (unsigned char)c); std::cout << buf; }
    std::cout << "\","
              << "\"signature\":\"" << env.signature << "\","
              << "\"pubkey\":\"" << id.pubkey_hex() << "\""
              << "}\n";
    return 0;
}
