// linux-usb/xiao-citizen/citizenry_transport.cpp
//
// Hardware-only. Host tests skip this file because the build is gated
// behind ARDUINO_HOST_TEST in the header.
#ifndef ARDUINO_HOST_TEST

#include "citizenry_transport.h"
#include <Arduino.h>

static const char*    MCAST_GROUP = "239.67.84.90";
static const uint16_t MCAST_PORT  = 7770;

bool CitizenryTransport::begin(OnPacket cb, uint16_t ucast_port) {
    _cb = cb;
    // Unicast: bind a caller-chosen port. Arduino's WiFiUDP/NetworkUDP does not
    // expose a localPort() accessor for an OS-chosen ephemeral port, so the
    // sketch derives a stable per-device port (e.g. from the MAC) and passes
    // it in here.
    if (!_ucast.begin(ucast_port)) { Serial.println("unicast bind failed"); return false; }
    _ucast_port = ucast_port;
    Serial.printf("unicast bound to :%u\n", _ucast_port);

    // Multicast: join group
    IPAddress group;
    group.fromString(MCAST_GROUP);
    if (!_mcast.beginMulticast(group, MCAST_PORT)) {
        Serial.println("multicast bind failed");
        return false;
    }
    Serial.printf("multicast joined %s:%u\n", MCAST_GROUP, MCAST_PORT);
    return true;
}

void CitizenryTransport::poll() {
    char buf[2048];
    int n;
    while ((n = _mcast.parsePacket()) > 0) {
        n = _mcast.read((uint8_t*)buf, sizeof(buf));
        if (n > 0 && _cb) _cb(std::string(buf, n), _mcast.remoteIP(), _mcast.remotePort());
    }
    while ((n = _ucast.parsePacket()) > 0) {
        n = _ucast.read((uint8_t*)buf, sizeof(buf));
        if (n > 0 && _cb) _cb(std::string(buf, n), _ucast.remoteIP(), _ucast.remotePort());
    }
}

void CitizenryTransport::send_multicast(const std::string& bytes) {
    IPAddress group; group.fromString(MCAST_GROUP);
    _mcast.beginPacket(group, MCAST_PORT);
    _mcast.write((const uint8_t*)bytes.data(), bytes.size());
    _mcast.endPacket();
}

void CitizenryTransport::send_unicast(const std::string& bytes, IPAddress ip, uint16_t port) {
    _ucast.beginPacket(ip, port);
    _ucast.write((const uint8_t*)bytes.data(), bytes.size());
    _ucast.endPacket();
}

#endif  // !ARDUINO_HOST_TEST
