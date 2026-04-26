// linux-usb/xiao-citizen/citizenry_envelope.cpp
#include "citizenry_envelope.h"

#include <cstdio>
#include <functional>
#include <sstream>
#include <map>

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

std::string envelope_to_wire(const Envelope& /*env*/) {
    return "";
}

bool envelope_from_wire(const std::string& /*bytes*/, Envelope& /*out*/) {
    return false;
}
