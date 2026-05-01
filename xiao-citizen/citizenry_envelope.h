// linux-usb/xiao-citizen/citizenry_envelope.h
#pragma once
#include <string>
#include <map>
#include <vector>
#include <variant>

// Body values can be string, int, double, bool, null, or a nested map/list.
// For simplicity we use a sealed variant tree — this matches what the wire
// protocol actually carries (no functions, no binary blobs except base64-strings).
struct JsonValue;
using JsonObject = std::map<std::string, JsonValue>;
using JsonArray = std::vector<JsonValue>;

struct JsonValue {
    enum Kind { Null, Bool, Int, Double, String, Object, Array };
    Kind kind = Null;
    bool b = false;
    long long i = 0;
    double d = 0.0;
    std::string s;
    JsonObject o;
    JsonArray a;
};

struct Envelope {
    int version = 1;
    int type = 0;
    std::string sender;     // hex pubkey
    std::string recipient;  // "*" or hex pubkey
    double timestamp = 0.0; // unix seconds, will be %.3f formatted
    double ttl = 0.0;
    JsonObject body;
    std::string signature;  // hex Ed25519 signature

    // ---- transport-only metadata (NOT signable, NOT serialised on wire) ----
    // Populated by citizenry_dispatch.cpp after RX; empty otherwise.
    // Mirrors citizenry/protocol.py Envelope.source_ip / source_port.
    // Excluded from canonical_signable_bytes() and envelope_to_wire() — both
    // functions enumerate fields explicitly, so adding struct members here
    // is automatically a no-op for emit. See citizenry_envelope.cpp.
    std::string source_ip;
    int         source_port = 0;

    void body_clear() { body.clear(); }
    void body_set_string(const std::string& k, const std::string& v);
    void body_set_int(const std::string& k, long long v);
    void body_set_double(const std::string& k, double v);
    void body_set_bool(const std::string& k, bool v);
    void body_set_null(const std::string& k);
};

// Produce the canonical-JSON bytes that get signed.
// Matches Python protocol.py _canonical_dumps() byte-for-byte.
std::string canonical_signable_bytes(const Envelope& env);

// Serialize the full envelope (with signature) for wire transmission.
std::string envelope_to_wire(const Envelope& env);

// Parse a wire envelope.
bool envelope_from_wire(const std::string& bytes, Envelope& out);
