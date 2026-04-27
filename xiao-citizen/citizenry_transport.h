// linux-usb/xiao-citizen/citizenry_transport.h
//
// UDP transport for the citizenry wire protocol. Owns one ephemeral unicast
// socket and one socket joined to the multicast group 239.67.84.90:7770.
// Hardware-only (uses WiFiUDP / Arduino IPAddress); host tests do not need
// this file.
#pragma once

#ifndef ARDUINO_HOST_TEST

#include <WiFiUdp.h>
#include <functional>
#include <string>

class CitizenryTransport {
public:
    using OnPacket = std::function<void(const std::string&, IPAddress, uint16_t)>;

    // Bind unicast to ucast_port (caller chooses; should be unique per device on
    // the LAN — derive from MAC). Joins the citizenry multicast group.
    bool begin(OnPacket cb, uint16_t ucast_port);
    void poll();                                                     // call from loop()
    void send_multicast(const std::string& bytes);
    void send_unicast(const std::string& bytes, IPAddress ip, uint16_t port);
    uint16_t unicast_port() const { return _ucast_port; }

private:
    WiFiUDP _ucast;
    WiFiUDP _mcast;
    OnPacket _cb;
    uint16_t _ucast_port = 0;
};

#endif  // !ARDUINO_HOST_TEST
