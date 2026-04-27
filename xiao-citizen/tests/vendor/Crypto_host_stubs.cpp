// Host-only stubs for rweather/Crypto symbols that pull in Arduino-only
// dependencies (RNG hardware sources, NoiseSource, ChaCha). The Ed25519
// sign/verify path used by Phase 0 tests does not exercise RNG.rand(); we
// only need the symbol to satisfy the linker.
#include "Crypto/RNG.h"
#include <cstring>

RNGClass::RNGClass() : credits(0), firstSave(0), initialized(0), trngPending(0),
    timer(0), timeout(0), count(0), trngPosn(0) {
    std::memset(block, 0, sizeof(block));
    std::memset(stream, 0, sizeof(stream));
    std::memset(noiseSources, 0, sizeof(noiseSources));
}
RNGClass::~RNGClass() {}

void RNGClass::begin(const char* /*tag*/) {}
void RNGClass::addNoiseSource(NoiseSource& /*source*/) {}
void RNGClass::setAutoSaveTime(uint16_t /*minutes*/) {}

void RNGClass::rand(uint8_t* data, size_t len) {
    // Phase 0 host tests never hit this path (we use seeded keys), but if
    // something does call it, write zeros so behaviour is deterministic.
    std::memset(data, 0, len);
}
bool RNGClass::available(size_t /*len*/) const { return true; }
void RNGClass::stir(const uint8_t* /*data*/, size_t /*len*/, unsigned int /*credit*/) {}
void RNGClass::save() {}
void RNGClass::loop() {}
void RNGClass::destroy() {}
void RNGClass::rekey() {}
void RNGClass::mixTRNG() {}

RNGClass RNG;
