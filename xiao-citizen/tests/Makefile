# linux-usb/xiao-citizen/tests/Makefile
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2 -I..

TESTS = test_canonical_json test_envelope_codec test_ed25519_interop

all: $(TESTS)

test_canonical_json: test_canonical_json.cpp ../citizenry_envelope.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^

test_envelope_codec: test_envelope_codec.cpp ../citizenry_envelope.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^

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

run: all
	@for t in $(TESTS); do echo "=== $$t ==="; ./$$t || exit 1; done

clean:
	rm -f $(TESTS) *.o

.PHONY: all run clean
