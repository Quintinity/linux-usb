# linux-usb/xiao-citizen/tests/Makefile
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2 -I..

# Phase 0 tests + Phase 2 dispatcher.
TESTS = test_canonical_json test_ed25519_interop test_dispatch

all: $(TESTS)

test_canonical_json: test_canonical_json.cpp ../citizenry_envelope.cpp
	$(CXX) $(CXXFLAGS) -DARDUINO_HOST_TEST -Ivendor -o $@ $^

# test_ed25519_interop links rweather/Crypto Ed25519 (vendored).
# We exclude RNG.cpp and NoiseSource.cpp (they pull in Arduino-only deps
# like ChaCha and <Arduino.h>); a host-only stub provides the RNG symbol
# the Ed25519/Curve25519 paths reference but do not actually call from
# sign/verify with seeded keys.
CRYPTO_SRCS = vendor/Crypto/BigNumberUtil.cpp \
              vendor/Crypto/Crypto.cpp \
              vendor/Crypto/Curve25519.cpp \
              vendor/Crypto/Ed25519.cpp \
              vendor/Crypto/Hash.cpp \
              vendor/Crypto/SHA512.cpp \
              vendor/Crypto_host_stubs.cpp

test_ed25519_interop: test_ed25519_interop.cpp ../citizenry_envelope.cpp ../citizenry_identity.cpp $(CRYPTO_SRCS)
	$(CXX) $(CXXFLAGS) -DARDUINO_HOST_TEST -Ivendor -Ivendor/Crypto -o $@ $^

emit_envelope: emit_envelope.cpp ../citizenry_envelope.cpp ../citizenry_identity.cpp $(CRYPTO_SRCS)
	$(CXX) $(CXXFLAGS) -DARDUINO_HOST_TEST -Ivendor -Ivendor/Crypto -o $@ $^

run: all
	@for t in $(TESTS); do echo "=== $$t ==="; ./$$t || exit 1; done

clean:
	rm -f $(TESTS) *.o

.PHONY: all run clean

# Phase 2.1 dispatcher test. Pulls citizenry_envelope (now with envelope_to_wire / from_wire)
# and citizenry_dispatch.cpp; reuses the rweather/Crypto sources from the Ed25519 test.
test_dispatch: test_dispatch.cpp ../citizenry_envelope.cpp ../citizenry_identity.cpp ../citizenry_dispatch.cpp $(CRYPTO_SRCS)
	$(CXX) $(CXXFLAGS) -DARDUINO_HOST_TEST -Ivendor -Ivendor/Crypto -o $@ $^
