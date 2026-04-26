// linux-usb/xiao-citizen/tests/fixture_loader.h
#pragma once
#include "../citizenry_envelope.h"
#include "vendor/nlohmann/json.hpp"
#include <fstream>
#include <string>
#include <vector>

struct Fixture {
    std::string name;
    Envelope envelope;
    std::string signable_bytes;   // raw bytes the C++ output must match
    std::string signature;        // hex
    std::string verify_key;       // hex
    std::string signing_seed;     // hex
};

inline std::string hex_decode(const std::string& h) {
    std::string out;
    out.reserve(h.size() / 2);
    for (size_t i = 0; i + 1 < h.size(); i += 2) {
        unsigned int b;
        std::sscanf(h.c_str() + i, "%2x", &b);
        out.push_back((char)b);
    }
    return out;
}

inline JsonValue from_nl(const nlohmann::json& j) {
    JsonValue v;
    if (j.is_null()) v.kind = JsonValue::Null;
    else if (j.is_boolean()) { v.kind = JsonValue::Bool; v.b = j.get<bool>(); }
    else if (j.is_number_integer()) { v.kind = JsonValue::Int; v.i = j.get<long long>(); }
    else if (j.is_number_float()) { v.kind = JsonValue::Double; v.d = j.get<double>(); }
    else if (j.is_string()) { v.kind = JsonValue::String; v.s = j.get<std::string>(); }
    else if (j.is_object()) {
        v.kind = JsonValue::Object;
        for (auto it = j.begin(); it != j.end(); ++it) v.o[it.key()] = from_nl(it.value());
    } else if (j.is_array()) {
        v.kind = JsonValue::Array;
        for (auto& el : j) v.a.push_back(from_nl(el));
    }
    return v;
}

inline std::vector<Fixture> load_fixtures(const std::string& path) {
    std::ifstream f(path);
    nlohmann::json doc;
    f >> doc;
    std::vector<Fixture> out;
    for (auto& fx : doc["fixtures"]) {
        Fixture x;
        x.name = fx["name"].get<std::string>();
        x.signable_bytes = hex_decode(fx["signable_bytes_hex"].get<std::string>());
        x.signature = fx["signature_hex"].get<std::string>();
        x.verify_key = fx["verify_key_hex"].get<std::string>();
        x.signing_seed = fx["signing_seed_hex"].get<std::string>();
        const auto& e = fx["envelope"];
        x.envelope.version = e["version"].get<int>();
        x.envelope.type = e["type"].get<int>();
        x.envelope.sender = e["sender"].get<std::string>();
        x.envelope.recipient = e["recipient"].get<std::string>();
        x.envelope.timestamp = e["timestamp"].get<double>();
        x.envelope.ttl = e["ttl"].get<double>();
        const auto& body = e["body"];
        for (auto it = body.begin(); it != body.end(); ++it)
            x.envelope.body[it.key()] = from_nl(it.value());
        out.push_back(x);
    }
    return out;
}
