// linux-usb/xiao-citizen/citizenry_neighbor.cpp
//
// See citizenry_neighbor.h for the contract. The eviction math uses unsigned
// subtraction so wraparound of millis() is safe up to 49 days of uptime.

#include "citizenry_neighbor.h"

const char* neighbor_state_name(NeighborState s) {
    switch (s) {
        case NeighborState::Ok:       return "OK";
        case NeighborState::Degraded: return "DEGRADED";
        case NeighborState::Dead:     return "DEAD";
    }
    return "?";
}

bool NeighborTable::observe(const std::string& pubkey,
                            uint32_t now_ms,
                            const std::string& name,
                            const std::string& type,
                            const std::string& source_ip,
                            uint16_t reply_port) {
    auto it = _rows.find(pubkey);
    bool is_new = (it == _rows.end());
    if (is_new) {
        Neighbor n;
        n.pubkey_hex   = pubkey;
        n.last_seen_ms = now_ms;
        n.state        = NeighborState::Ok;
        if (!name.empty())      n.name = name;
        if (!type.empty())      n.type = type;
        if (!source_ip.empty()) n.source_ip = source_ip;
        if (reply_port != 0)    n.reply_port = reply_port;
        _rows[pubkey] = n;
        return true;
    }
    Neighbor& n = it->second;
    n.last_seen_ms = now_ms;
    n.state = NeighborState::Ok;   // observation immediately revives
    // Enrich progressively — if a HEARTBEAT carries name/type/etc. update.
    if (!name.empty())      n.name = name;
    if (!type.empty())      n.type = type;
    if (!source_ip.empty()) n.source_ip = source_ip;
    if (reply_port != 0)    n.reply_port = reply_port;
    return false;
}

uint32_t NeighborTable::tick(uint32_t now_ms) {
    uint32_t transitions = 0;
    const uint32_t degraded_threshold = _period_ms * _degraded_misses;
    const uint32_t dead_threshold     = _period_ms * _dead_misses;
    for (auto& kv : _rows) {
        Neighbor& n = kv.second;
        // Unsigned subtraction handles millis() wraparound correctly.
        uint32_t age = now_ms - n.last_seen_ms;
        NeighborState was = n.state;
        if (age >= dead_threshold) {
            n.state = NeighborState::Dead;
        } else if (age >= degraded_threshold) {
            n.state = NeighborState::Degraded;
        } else {
            n.state = NeighborState::Ok;
        }
        if (n.state != was) transitions++;
    }
    return transitions;
}

const Neighbor* NeighborTable::get(const std::string& pubkey) const {
    auto it = _rows.find(pubkey);
    if (it == _rows.end()) return nullptr;
    return &it->second;
}

size_t NeighborTable::count_alive() const {
    size_t n = 0;
    for (const auto& kv : _rows) {
        if (kv.second.state != NeighborState::Dead) n++;
    }
    return n;
}

std::vector<Neighbor> NeighborTable::snapshot() const {
    std::vector<Neighbor> out;
    out.reserve(_rows.size());
    for (const auto& kv : _rows) out.push_back(kv.second);
    return out;
}
