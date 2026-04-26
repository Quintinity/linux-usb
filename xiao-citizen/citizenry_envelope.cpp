// linux-usb/xiao-citizen/citizenry_envelope.cpp
#include "citizenry_envelope.h"

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

std::string canonical_signable_bytes(const Envelope& /*env*/) {
    // STUB — Task 0.4 fills this in
    return "";
}

std::string envelope_to_wire(const Envelope& /*env*/) {
    return "";
}

bool envelope_from_wire(const std::string& /*bytes*/, Envelope& /*out*/) {
    return false;
}
