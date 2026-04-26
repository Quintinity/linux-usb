// linux-usb/xiao-citizen/citizenry_envelope.cpp
#include "citizenry_envelope.h"

#include <cstdio>
#include <functional>
#include <sstream>
#include <map>

// JSON parser selection. The host tests use the vendored nlohmann/json
// single-header so they don't depend on Arduino. The firmware build uses
// ArduinoJson v7 (already vendored as a system library on the Pi build host).
#ifdef ARDUINO_HOST_TEST
  #include "tests/vendor/nlohmann/json.hpp"
#else
  // Include the .hpp form so ArduinoJson stays in its own namespace.
  // The plain `<ArduinoJson.h>` header injects `using namespace ArduinoJson`
  // at global scope, which collides with our top-level JsonObject / JsonValue
  // / JsonArray typedefs in citizenry_envelope.h.
  #include <ArduinoJson.hpp>
#endif

void Envelope::body_set_string(const std::string& k, const std::string& v) {
    JsonValue jv; jv.kind = JsonValue::String; jv.s = v;
    body[k] = jv;
}
void Envelope::body_set_int(const std::string& k, long long v) {
    JsonValue jv; jv.kind = JsonValue::Int; jv.i = v;
    body[k] = jv;
}
void Envelope::body_set_double(const std::string& k, double v) {
    JsonValue jv; jv.kind = JsonValue::Double; jv.d = v;
    body[k] = jv;
}
void Envelope::body_set_bool(const std::string& k, bool v) {
    JsonValue jv; jv.kind = JsonValue::Bool; jv.b = v;
    body[k] = jv;
}
void Envelope::body_set_null(const std::string& k) {
    JsonValue jv; jv.kind = JsonValue::Null;
    body[k] = jv;
}

namespace {

void write_canonical(std::ostringstream& os, const JsonValue& v);
void write_string(std::ostringstream& os, const std::string& s);
void write_object(std::ostringstream& os, const JsonObject& obj);

} // anon

// File-scope wrappers exposed so envelope_to_wire (also in this file but
// outside the anonymous namespace) can reuse the same canonical writers
// instead of duplicating string-escape and object-emit logic.
static void write_string_canonical(std::ostringstream& os, const std::string& s) { write_string(os, s); }
static void write_object_canonical(std::ostringstream& os, const JsonObject& o) { write_object(os, o); }

namespace {

void write_string(std::ostringstream& os, const std::string& s) {
    os << '"';
    for (char c : s) {
        switch (c) {
            case '"':  os << "\\\""; break;
            case '\\': os << "\\\\"; break;
            case '\b': os << "\\b"; break;
            case '\f': os << "\\f"; break;
            case '\n': os << "\\n"; break;
            case '\r': os << "\\r"; break;
            case '\t': os << "\\t"; break;
            default:
                if ((unsigned char)c < 0x20) { char buf[8]; std::snprintf(buf, sizeof(buf), "\\u%04x", c); os << buf; }
                else os << c;
        }
    }
    os << '"';
}

void write_double(std::ostringstream& os, double d) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.3f", d);
    os << buf;
}

void write_object(std::ostringstream& os, const JsonObject& obj) {
    os << '{';
    bool first = true;
    // std::map already sorts keys lexicographically — that matches Python sort_keys=True
    for (const auto& kv : obj) {
        if (!first) os << ',';
        write_string(os, kv.first);
        os << ':';
        write_canonical(os, kv.second);
        first = false;
    }
    os << '}';
}

void write_array(std::ostringstream& os, const JsonArray& arr) {
    os << '[';
    bool first = true;
    for (const auto& v : arr) {
        if (!first) os << ',';
        write_canonical(os, v);
        first = false;
    }
    os << ']';
}

void write_canonical(std::ostringstream& os, const JsonValue& v) {
    switch (v.kind) {
        case JsonValue::Null:   os << "null"; break;
        case JsonValue::Bool:   os << (v.b ? "true" : "false"); break;
        case JsonValue::Int:    os << v.i; break;
        case JsonValue::Double: write_double(os, v.d); break;
        case JsonValue::String: write_string(os, v.s); break;
        case JsonValue::Object: write_object(os, v.o); break;
        case JsonValue::Array:  write_array(os, v.a); break;
    }
}

} // namespace

std::string canonical_signable_bytes(const Envelope& env) {
    // Build a synthetic top-level object with the 7 envelope fields
    // (everything except the signature). std::map auto-sorts keys.
    std::map<std::string, std::function<void(std::ostringstream&)>> fields = {
        {"body",       [&](auto& os){ write_object(os, env.body); }},
        {"recipient",  [&](auto& os){ write_string(os, env.recipient); }},
        {"sender",     [&](auto& os){ write_string(os, env.sender); }},
        {"timestamp",  [&](auto& os){ write_double(os, env.timestamp); }},
        {"ttl",        [&](auto& os){ write_double(os, env.ttl); }},
        {"type",       [&](auto& os){ os << env.type; }},
        {"version",    [&](auto& os){ os << env.version; }},
    };
    std::ostringstream os;
    os << '{';
    bool first = true;
    for (auto& kv : fields) {
        if (!first) os << ',';
        write_string(os, kv.first);
        os << ':';
        kv.second(os);
        first = false;
    }
    os << '}';
    return os.str();
}

// ==================== wire format (full envelope incl. signature) ====================
//
// The Python side emits `json.dumps(asdict(self), sort_keys=True, separators=(",",":"))`.
// That uses Python's default float repr (e.g. 6.0 → "6.0"), NOT the %.3f canonical form.
// Receivers always re-canonicalise via canonical_signable_bytes() before verifying, so
// float-precision drift on the wire is a non-issue: the reconstructed double survives
// the round-trip with full IEEE-754 precision through Python's repr and our %.3f.
//
// Our writer mirrors Python's: sorted keys, no whitespace, %.3f for the two
// timestamp/ttl floats so receivers (including Python ones) see byte-identical
// canonical signables. We deliberately keep this writer simple — it only needs to
// emit Envelope shapes, not arbitrary JSON.

std::string envelope_to_wire(const Envelope& env) {
    // Field order is alphabetical so std::map<>s implicit ordering matches
    // Python's sort_keys=True. Top-level keys: body, recipient, sender,
    // signature, timestamp, ttl, type, version.
    std::ostringstream os;
    os << '{';
    os << "\"body\":";   write_object_canonical(os, env.body);
    os << ",\"recipient\":"; write_string_canonical(os, env.recipient);
    os << ",\"sender\":";    write_string_canonical(os, env.sender);
    os << ",\"signature\":"; write_string_canonical(os, env.signature);
    os << ",\"timestamp\":"; { char b[64]; std::snprintf(b, sizeof(b), "%.3f", env.timestamp); os << b; }
    os << ",\"ttl\":";       { char b[64]; std::snprintf(b, sizeof(b), "%.3f", env.ttl); os << b; }
    os << ",\"type\":" << env.type;
    os << ",\"version\":" << env.version;
    os << '}';
    return os.str();
}

#ifdef ARDUINO_HOST_TEST
namespace {
JsonValue from_nlohmann(const nlohmann::json& j) {
    JsonValue v;
    if (j.is_null()) v.kind = JsonValue::Null;
    else if (j.is_boolean()) { v.kind = JsonValue::Bool; v.b = j.get<bool>(); }
    else if (j.is_number_integer() || j.is_number_unsigned()) { v.kind = JsonValue::Int; v.i = j.get<long long>(); }
    else if (j.is_number_float()) { v.kind = JsonValue::Double; v.d = j.get<double>(); }
    else if (j.is_string()) { v.kind = JsonValue::String; v.s = j.get<std::string>(); }
    else if (j.is_object()) {
        v.kind = JsonValue::Object;
        for (auto it = j.begin(); it != j.end(); ++it) v.o[it.key()] = from_nlohmann(it.value());
    } else if (j.is_array()) {
        v.kind = JsonValue::Array;
        for (auto& el : j) v.a.push_back(from_nlohmann(el));
    }
    return v;
}
} // anon
#else
namespace {
// ArduinoJson v7 path. ArduinoJson::JsonVariantConst → our JsonValue.
JsonValue from_arduinojson(ArduinoJson::JsonVariantConst j) {
    JsonValue v;
    if (j.isNull()) v.kind = JsonValue::Null;
    else if (j.is<bool>()) { v.kind = JsonValue::Bool; v.b = j.as<bool>(); }
    else if (j.is<long long>()) { v.kind = JsonValue::Int; v.i = j.as<long long>(); }
    else if (j.is<double>() || j.is<float>()) { v.kind = JsonValue::Double; v.d = j.as<double>(); }
    else if (j.is<const char*>()) { v.kind = JsonValue::String; v.s = j.as<const char*>(); }
    else if (j.is<ArduinoJson::JsonObjectConst>()) {
        v.kind = JsonValue::Object;
        for (ArduinoJson::JsonPairConst kv : j.as<ArduinoJson::JsonObjectConst>())
            v.o[std::string(kv.key().c_str())] = from_arduinojson(kv.value());
    } else if (j.is<ArduinoJson::JsonArrayConst>()) {
        v.kind = JsonValue::Array;
        for (ArduinoJson::JsonVariantConst el : j.as<ArduinoJson::JsonArrayConst>())
            v.a.push_back(from_arduinojson(el));
    }
    return v;
}
} // anon
#endif

bool envelope_from_wire(const std::string& bytes, Envelope& out) {
#ifdef ARDUINO_HOST_TEST
    nlohmann::json doc;
    try {
        doc = nlohmann::json::parse(bytes);
    } catch (...) {
        return false;
    }
    if (!doc.is_object()) return false;
    // Required keys.
    for (const char* k : {"version","type","sender","recipient","timestamp","ttl","body","signature"}) {
        if (!doc.contains(k)) return false;
    }
    out.version = doc["version"].get<int>();
    out.type    = doc["type"].get<int>();
    out.sender  = doc["sender"].get<std::string>();
    out.recipient = doc["recipient"].get<std::string>();
    // Allow integer-valued timestamps/ttl (Python may serialize 6.0 as "6" if
    // someone constructs an Envelope with int instead of float — defensive).
    if (doc["timestamp"].is_number()) out.timestamp = doc["timestamp"].get<double>(); else return false;
    if (doc["ttl"].is_number())       out.ttl       = doc["ttl"].get<double>();       else return false;
    out.signature = doc["signature"].get<std::string>();
    out.body.clear();
    if (!doc["body"].is_object()) return false;
    for (auto it = doc["body"].begin(); it != doc["body"].end(); ++it) {
        out.body[it.key()] = from_nlohmann(it.value());
    }
    return true;
#else
    // ArduinoJson v7 — sized for Phase 2 envelopes. PROPOSE/REPORT bodies
    // with base64 JPEGs (Phase 3) need a larger doc; for now keep it tight.
    ArduinoJson::JsonDocument doc;
    ArduinoJson::DeserializationError err = ArduinoJson::deserializeJson(doc, bytes.data(), bytes.size());
    if (err) return false;
    if (!doc.is<ArduinoJson::JsonObjectConst>()) return false;
    ArduinoJson::JsonObjectConst obj = doc.as<ArduinoJson::JsonObjectConst>();
    for (const char* k : {"version","type","sender","recipient","timestamp","ttl","body","signature"}) {
        if (!obj[k]) return false;
    }
    out.version   = obj["version"].as<int>();
    out.type      = obj["type"].as<int>();
    out.sender    = obj["sender"].as<const char*>();
    out.recipient = obj["recipient"].as<const char*>();
    out.timestamp = obj["timestamp"].as<double>();
    out.ttl       = obj["ttl"].as<double>();
    out.signature = obj["signature"].as<const char*>();
    out.body.clear();
    if (!obj["body"].is<ArduinoJson::JsonObjectConst>()) return false;
    for (ArduinoJson::JsonPairConst kv : obj["body"].as<ArduinoJson::JsonObjectConst>()) {
        out.body[std::string(kv.key().c_str())] = from_arduinojson(kv.value());
    }
    return true;
#endif
}
