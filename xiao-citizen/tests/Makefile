# linux-usb/xiao-citizen/tests/Makefile
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2 -I..

TESTS = test_canonical_json test_envelope_codec test_ed25519_interop

all: $(TESTS)

test_canonical_json: test_canonical_json.cpp ../citizenry_envelope.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^

test_envelope_codec: test_envelope_codec.cpp ../citizenry_envelope.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^

# test_ed25519_interop links rweather/Crypto Ed25519 (vendored)
test_ed25519_interop: test_ed25519_interop.cpp ../citizenry_envelope.cpp ../citizenry_identity.cpp $(wildcard vendor/Crypto/*.cpp)
	$(CXX) $(CXXFLAGS) -DARDUINO_HOST_TEST -Ivendor/Crypto -o $@ $^

run: all
	@for t in $(TESTS); do echo "=== $$t ==="; ./$$t || exit 1; done

clean:
	rm -f $(TESTS) *.o

.PHONY: all run clean
