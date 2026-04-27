// linux-usb/xiao-citizen/tests/test_neighbor.cpp
//
// Phase 2.5 neighbor table — synthetic-clock unit tests of TTL eviction.
// Every observation revives the row; tick() at increasing now_ms walks
// it through OK -> DEGRADED (3 missed beats) -> DEAD (10 missed beats).

#include "../citizenry_neighbor.h"
#include <cstdio>
#include <string>

static int g_pass = 0, g_fail = 0;
static void check(const std::string& name, bool cond) {
    if (cond) { printf("PASS: %s\n", name.c_str()); g_pass++; }
    else      { printf("FAIL: %s\n", name.c_str()); g_fail++; }
}

int main() {
    const std::string A = "aa" + std::string(62, '0');
    const std::string B = "bb" + std::string(62, '0');

    // ---- 1. Empty table is well-behaved ----
    {
        NeighborTable t;
        check("empty: size==0",  t.size() == 0);
        check("empty: alive==0", t.count_alive() == 0);
        check("empty: get null", t.get(A) == nullptr);
        check("empty: tick 0",   t.tick(0) == 0);
    }

    // ---- 2. observe() inserts new rows in OK state ----
    {
        NeighborTable t;
        bool is_new = t.observe(A, /*now_ms=*/100, "alpha", "sensor", "192.168.1.10", 51000);
        check("observe new returns true", is_new);
        check("observe size==1",          t.size() == 1);
        const Neighbor* n = t.get(A);
        check("observe row exists",       n != nullptr);
        if (n) {
            check("observe name",           n->name == "alpha");
            check("observe type",           n->type == "sensor");
            check("observe last_seen=100",  n->last_seen_ms == 100);
            check("observe state=OK",       n->state == NeighborState::Ok);
            check("observe source_ip",      n->source_ip == "192.168.1.10");
            check("observe reply_port",     n->reply_port == 51000);
        }
        // Re-observe at +1000 ms — must NOT report new and must update last_seen.
        bool again = t.observe(A, 1100);
        check("observe repeat returns false", !again);
        check("observe repeat updates last_seen", t.get(A)->last_seen_ms == 1100);
    }

    // ---- 3. State transitions OK -> DEGRADED -> DEAD ----
    {
        NeighborTable t;   // defaults: 2000 ms period, 3/10 misses
        t.observe(A, 0);
        // Just before 3 misses (3*2000=6000): still OK.
        uint32_t tr1 = t.tick(5999);
        check("tick 5999 no transition", tr1 == 0);
        check("@5999 state=OK", t.get(A)->state == NeighborState::Ok);
        // Crossing 6000: DEGRADED.
        uint32_t tr2 = t.tick(6000);
        check("tick 6000 one transition", tr2 == 1);
        check("@6000 state=DEGRADED", t.get(A)->state == NeighborState::Degraded);
        // Idempotent: repeating tick within range stays DEGRADED.
        uint32_t tr3 = t.tick(8000);
        check("tick 8000 no transition", tr3 == 0);
        check("@8000 state=DEGRADED", t.get(A)->state == NeighborState::Degraded);
        // 10 misses == 20000 ms: DEAD.
        uint32_t tr4 = t.tick(20000);
        check("tick 20000 one transition", tr4 == 1);
        check("@20000 state=DEAD", t.get(A)->state == NeighborState::Dead);
    }

    // ---- 4. observe() revives a DEAD neighbor immediately ----
    {
        NeighborTable t;
        t.observe(A, 0);
        t.tick(50000);   // way past DEAD threshold
        check("DEAD before revive", t.get(A)->state == NeighborState::Dead);
        bool is_new = t.observe(A, 50100);
        check("revive observe NOT new", !is_new);
        check("revive state=OK", t.get(A)->state == NeighborState::Ok);
        // tick() right after revive sees no transition.
        uint32_t tr = t.tick(50100);
        check("revive tick no transition", tr == 0);
    }

    // ---- 5. Multiple neighbors evict independently ----
    {
        NeighborTable t;
        t.observe(A, 0,    "alpha", "sensor");
        t.observe(B, 5000, "beta",  "arm");
        // At t=8000: A unseen 8000 ms (DEGRADED), B unseen 3000 ms (OK).
        uint32_t tr = t.tick(8000);
        check("multi tick 8000 one transition", tr == 1);
        check("multi A=DEGRADED", t.get(A)->state == NeighborState::Degraded);
        check("multi B=OK",       t.get(B)->state == NeighborState::Ok);
        // count_alive includes DEGRADED.
        check("multi alive=2", t.count_alive() == 2);
        // At t=25000: A unseen 25000 (DEAD), B unseen 20000 (DEAD).
        t.tick(25000);
        check("multi A=DEAD", t.get(A)->state == NeighborState::Dead);
        check("multi B=DEAD", t.get(B)->state == NeighborState::Dead);
        check("multi alive=0", t.count_alive() == 0);
        check("multi size=2 (DEAD kept)", t.size() == 2);
    }

    // ---- 6. snapshot() returns every row ----
    {
        NeighborTable t;
        t.observe(A, 0);
        t.observe(B, 0);
        auto snap = t.snapshot();
        check("snapshot size=2", snap.size() == 2);
        bool found_a = false, found_b = false;
        for (const auto& n : snap) {
            if (n.pubkey_hex == A) found_a = true;
            if (n.pubkey_hex == B) found_b = true;
        }
        check("snapshot has A", found_a);
        check("snapshot has B", found_b);
    }

    // ---- 7. Custom periods (in case Phase 4 wants tighter eviction) ----
    {
        NeighborTable t(/*period_ms=*/1000, /*degraded=*/2, /*dead=*/5);
        t.observe(A, 0);
        // 2 misses = 2000 ms → DEGRADED.
        t.tick(2000);
        check("custom @2000 DEGRADED", t.get(A)->state == NeighborState::Degraded);
        // 5 misses = 5000 ms → DEAD.
        t.tick(5000);
        check("custom @5000 DEAD",      t.get(A)->state == NeighborState::Dead);
    }

    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
