// linux-usb/xiao-citizen/citizenry_neighbor.h
//
// Phase 2.5: pure-logic neighbor table.
//
// On every successful HEARTBEAT or ADVERTISE the dispatcher hands the
// envelope to NeighborTable::observe(...), which stamps the sender's
// last-seen wallclock. NeighborTable::tick() runs from the sketch's
// loop() with the current millis(): any neighbor unseen for >= 3 *
// HEARTBEAT_PERIOD_MS transitions OK -> DEGRADED, >= 10 * period
// transitions DEGRADED -> DEAD. DEAD neighbors are kept (Phase 4 may
// hard-evict at a longer threshold), but the public count() / list()
// can filter them out so callers don't see corpses.

#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <vector>

enum class NeighborState {
    Ok,         // last seen within 3 heartbeat periods
    Degraded,   // unseen 3..9 heartbeat periods
    Dead,       // unseen >=10 heartbeat periods
};

const char* neighbor_state_name(NeighborState s);

struct Neighbor {
    std::string  pubkey_hex;
    std::string  name;             // populated from HEARTBEAT/ADVERTISE body if present
    std::string  type;             // "sensor" / "arm" / etc.
    uint32_t     last_seen_ms = 0;
    NeighborState state = NeighborState::Ok;
    // Source addr captured from the transport callback (Phase 3 PROPOSE
    // path needs this). Filled in only when observe() is called with a
    // non-empty source IP string.
    std::string  source_ip;
    uint16_t     reply_port = 0;
};

class NeighborTable {
public:
    // Defaults: 2 s heartbeat period × 3 (DEGRADED) and × 10 (DEAD).
    NeighborTable(uint32_t heartbeat_period_ms = 2000,
                  uint32_t degraded_misses = 3,
                  uint32_t dead_misses = 10)
        : _period_ms(heartbeat_period_ms),
          _degraded_misses(degraded_misses),
          _dead_misses(dead_misses) {}

    // Stamp last-seen for `pubkey` at `now_ms`. If new, insert with state
    // Ok. The optional name/type/source_ip/reply_port enrich the row but
    // are otherwise ignored. Returns true if this was a NEW neighbor.
    bool observe(const std::string& pubkey,
                 uint32_t now_ms,
                 const std::string& name = {},
                 const std::string& type = {},
                 const std::string& source_ip = {},
                 uint16_t reply_port = 0);

    // Re-evaluate every neighbor's state against `now_ms`. Returns the
    // count of state transitions (so the firmware can log them).
    uint32_t tick(uint32_t now_ms);

    // Lookup helpers.
    const Neighbor* get(const std::string& pubkey) const;
    size_t size() const { return _rows.size(); }
    size_t count_alive() const;   // OK + DEGRADED, excludes DEAD
    std::vector<Neighbor> snapshot() const;   // copy of every row

    uint32_t period_ms() const { return _period_ms; }

private:
    uint32_t _period_ms;
    uint32_t _degraded_misses;
    uint32_t _dead_misses;
    std::map<std::string, Neighbor> _rows;
};
