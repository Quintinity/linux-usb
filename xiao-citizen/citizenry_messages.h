// linux-usb/xiao-citizen/citizenry_messages.h
//
// Phase 2 message builders. Each helper takes the firmware's Identity plus
// the pieces of state the message body needs, and returns the on-the-wire
// JSON bytes ready to pass to CitizenryTransport::send_multicast() (broadcast
// shapes) or send_unicast() (targeted shapes).
//
// All builders sign with `id.sign_hex()` against the canonical signable
// bytes — the swarm's verifiers (Surface, Pi, Jetson, other XIAOs) all
// re-canonicalise before checking, so the wire form's float precision is
// not load-bearing.
//
// Default TTLs mirror citizenry/protocol.py:
//   HEARTBEAT 6 s, DISCOVER 5 s, ADVERTISE 30 s, REPORT 60 s.

#pragma once

#include "citizenry_dispatch.h"   // InboundEnvelope (forward-decl insufficient: AdvertiseTarget helper inspects body)
#include "citizenry_envelope.h"
#include "citizenry_identity.h"
#include <cstdint>
#include <string>
#include <vector>

// MessageType enum mirror — kept here (rather than included from a shared
// header) because the dispatcher already validates 1..7 and the sketch
// doesn't need the enum for anything except picking which builder to call.
namespace MsgType {
    constexpr int HEARTBEAT     = 1;
    constexpr int DISCOVER      = 2;
    constexpr int ADVERTISE     = 3;
    constexpr int PROPOSE       = 4;
    constexpr int ACCEPT_REJECT = 5;
    constexpr int REPORT        = 6;
    constexpr int GOVERN        = 7;
}

// 2.2: DISCOVER (broadcast). Body: {name, type:"sensor", unicast_port}.
std::string build_discover(const Identity& id,
                           const std::string& citizen_name,
                           uint16_t unicast_port,
                           double now_unix_secs);

// 2.3: HEARTBEAT (broadcast). Body: {name, state, health, unicast_port, uptime}.
// Default cadence in the firmware loop is one beat per 2 s — see
// HeartbeatScheduler below for the pacing helper.
std::string build_heartbeat(const Identity& id,
                            const std::string& citizen_name,
                            uint16_t unicast_port,
                            double uptime_secs,
                            double now_unix_secs);

// Pure-logic 2 s cadence ticker. tick(now_ms) returns true iff a heartbeat
// is due at this tick (every 2000 ms after the first call). Lives outside
// the transport layer so it can be unit-tested with a synthetic clock.
class HeartbeatScheduler {
public:
    explicit HeartbeatScheduler(uint32_t period_ms = 2000) : _period_ms(period_ms) {}
    bool tick(uint32_t now_ms);     // returns true on each "beat now" boundary
    uint32_t period_ms() const { return _period_ms; }

private:
    uint32_t _period_ms;
    uint32_t _last_beat_ms = 0;
    bool     _started = false;
};

// 2.4: ADVERTISE (unicast). Body: {name, type, capabilities, health, state,
// unicast_port, has_constitution}. Recipient is the discoverer's pubkey
// hex; transport-layer destination IP is taken from the inbound DISCOVER's
// UDP source, transport-layer destination port from the body's
// `unicast_port` field (extract via advertise_target_for_discover).
std::string build_advertise(const Identity& id,
                            const std::string& citizen_name,
                            uint16_t unicast_port,
                            bool has_constitution,
                            const std::string& recipient_pubkey_hex,
                            double now_unix_secs);

// Pure-logic helper: given an inbound DISCOVER, return the recipient
// pubkey (always env.sender) and the unicast port to reply to (read from
// body.unicast_port, falling back to a caller-supplied default for
// older citizens that omit it). Returns false if the envelope isn't a
// DISCOVER or the body shape is wrong.
struct AdvertiseTarget {
    std::string recipient_pubkey_hex;
    uint16_t    reply_port = 0;
};
bool advertise_target_for_discover(const InboundEnvelope& m,
                                   uint16_t fallback_port,
                                   AdvertiseTarget& out);

// 2.6: REPORT govern_ack (unicast to governor). Body: {task:"govern_ack",
// result:"success", constitution_version}.
std::string build_report_govern_ack(const Identity& id,
                                    int constitution_version,
                                    const std::string& governor_pubkey_hex,
                                    double now_unix_secs);

// 3.1: ACCEPT_REJECT (unicast). Body: {result:"accept", task, task_id}.
// Sent in response to a PROPOSE the citizen will execute. The proposer
// uses task_id to correlate the eventual REPORT.
std::string build_accept(const Identity& id,
                         const std::string& proposer_pubkey_hex,
                         const std::string& task,
                         const std::string& task_id,
                         double now_unix_secs);

// 3.1: ACCEPT_REJECT (unicast). Body: {result:"reject", reason}.
std::string build_reject(const Identity& id,
                         const std::string& proposer_pubkey_hex,
                         const std::string& reason,
                         double now_unix_secs);

// 3.2: REPORT frame_capture (unicast to proposer). Body:
// {type:"frame_capture", task_id, frame:<base64 JPEG>, width, height,
//  timestamp}. Mirrors citizenry/camera_citizen.py send_report_frame_capture.
// `jpeg_buf` is base64-encoded into the body; ownership of the buffer stays
// with the caller (the caller releases the camera FB after this returns).
// timestamp echoes now_unix_secs (XIAO has no RTC; Phase 4 SNTP fixes that).
std::string build_report_frame_capture(const Identity& id,
                                       const std::string& proposer_pubkey_hex,
                                       const std::string& task_id,
                                       const uint8_t* jpeg_buf,
                                       size_t jpeg_len,
                                       uint16_t width,
                                       uint16_t height,
                                       double now_unix_secs);

// 3.3: hardware-abstract camera interface so the PROPOSE handler is host-
// testable. The Arduino impl (XiaoCameraSource in xiao-citizen.ino) wraps
// citizenry_camera_grab/release; host tests use a stub.
class CameraSource {
public:
    virtual ~CameraSource() = default;
    // grab() yields a JPEG buffer + dimensions. The pointer is borrowed and
    // must remain valid until release() is called. Return false if the
    // capture fails or the camera is not ready.
    virtual bool grab(const uint8_t** out_buf, size_t* out_len,
                      uint16_t* out_w, uint16_t* out_h) = 0;
    virtual void release() = 0;
    // ready() is the cheap "would grab() plausibly succeed" probe used to
    // emit a fast REJECT before any frame buffer churn.
    virtual bool ready() const = 0;
};

// 3.3: PROPOSE handler for task=="frame_capture". Returns vector of envelope
// wire bytes to emit, in order. Always emits ACCEPT_REJECT (accept or reject)
// first. On accept the second envelope is the REPORT frame_capture (or a
// REPORT task_complete with result:"failed" if the actual capture failed
// after we already accepted). Empty vector only on a non-PROPOSE inbound.
struct FrameCaptureTarget {
    std::string proposer_pubkey_hex;
    uint16_t    reply_port = 0;
    std::string task_id;
};
std::vector<std::string>
handle_propose_frame_capture(const InboundEnvelope& m,
                             const Identity& id,
                             CameraSource& cam,
                             uint16_t fallback_reply_port,
                             double now_unix_secs,
                             FrameCaptureTarget& out);

// 2.6: persistence interface for the constitution (the GOVERN body). Hardware
// implementation is NVS-backed (Preferences); the host tests use an in-memory
// shim. The interface is intentionally tiny — store the version number, the
// raw signable_bytes-canonical body (so future code can re-verify a
// re-broadcast GOVERN against the cached signature), and a have-we-got-one
// flag for the ADVERTISE body.
class ConstitutionStore {
public:
    virtual ~ConstitutionStore() = default;
    virtual bool save(int version, const std::string& canonical_body) = 0;
    virtual bool load(int& version, std::string& canonical_body) = 0;
    virtual bool has() const = 0;
};

// In-memory shim for host tests. Not used in firmware; the sketch wires
// Preferences directly behind the same interface.
class InMemoryConstitutionStore : public ConstitutionStore {
public:
    bool save(int version, const std::string& canonical_body) override {
        _version = version;
        _body = canonical_body;
        _has = true;
        return true;
    }
    bool load(int& version, std::string& canonical_body) override {
        if (!_has) return false;
        version = _version;
        canonical_body = _body;
        return true;
    }
    bool has() const override { return _has; }

private:
    int _version = 0;
    std::string _body;
    bool _has = false;
};

// 2.6: pure-logic GOVERN handler. Given an inbound GOVERN, persist its body
// to `store`, then build a REPORT govern_ack signed by `id` and addressed
// to the governor (the GOVERN's sender). Returns the wire bytes for the
// REPORT, plus the recipient pubkey + reply port via out-params so the
// firmware can transport.send_unicast(). Returns empty string on rejection
// (wrong type, missing version, save failure).
struct GovernAckTarget {
    std::string recipient_pubkey_hex;
    uint16_t    reply_port = 0;
    int         constitution_version = 0;
};
std::string handle_govern(const InboundEnvelope& m,
                          const Identity& id,
                          ConstitutionStore& store,
                          uint16_t fallback_reply_port,
                          double now_unix_secs,
                          GovernAckTarget& out);
