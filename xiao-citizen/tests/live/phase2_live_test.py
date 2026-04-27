#!/usr/bin/env python3
"""Phase 2 live verification: drive DISCOVER + GOVERN at the native XIAO
firmware, verify ADVERTISE + REPORT govern_ack come back signed.

Usage:
    python3 phase2_live_test.py [xiao_ip]

If xiao_ip is omitted, defaults to 192.168.1.83 (xiao-cam-0000). Override
when testing the second XIAO or after a DHCP reshuffle.

Run from the lerobot-env (or any venv with pynacl):
    /home/bradley/lerobot-env/bin/python phase2_live_test.py
"""

import json, socket, struct, sys, time
sys.path.insert(0, "/home/bradley/linux-usb")
from citizenry.protocol import (
    Envelope, MessageType, make_envelope, MULTICAST_GROUP, MULTICAST_PORT,
)
import nacl.signing, nacl.encoding

XIAO_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.83"

# Ephemeral identity for the test driver
sk = nacl.signing.SigningKey.generate()
me_pubkey = sk.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()
print(f"test driver pubkey: {me_pubkey[:16]}...")

# --- listener ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("", MULTICAST_PORT))
mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
sock.settimeout(0.5)

# --- sender ---
tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

def send_mcast(env: Envelope):
    tx.sendto(env.to_bytes(), (MULTICAST_GROUP, MULTICAST_PORT))

def listen(filter_fn, timeout, label):
    print(f"  listening {timeout:.1f}s for {label}...")
    end = time.time() + timeout
    while time.time() < end:
        try:
            data, addr = sock.recvfrom(8192)
        except socket.timeout:
            continue
        try:
            j = json.loads(data)
        except: continue
        if filter_fn(j, addr):
            return j, addr
    return None, None

# ============ TEST 1: DISCOVER -> ADVERTISE ============
print("\n=== TEST 1: DISCOVER -> ADVERTISE ===")
disc = make_envelope(
    MessageType.DISCOVER,
    sender_pubkey=me_pubkey,
    body={"name": "phase2-test-driver", "type": "test", "unicast_port": 50000},
    signing_key=sk,
)
send_mcast(disc)
print(f"  sent DISCOVER (sender={me_pubkey[:16]}...)")

def is_advertise_for_me(j, addr):
    return (j.get("type") == int(MessageType.ADVERTISE)
            and j.get("recipient") == me_pubkey
            and addr[0] == XIAO_IP)

adv, addr = listen(is_advertise_for_me, 5.0, "ADVERTISE")
if adv is None:
    print("  ❌ no ADVERTISE received from XIAO")
else:
    print(f"  ✅ ADVERTISE received from {addr[0]}")
    print(f"     sender:    {adv['sender'][:16]}...")
    print(f"     recipient: {adv['recipient'][:16]}... (us)")
    print(f"     body:      {json.dumps(adv['body'])}")
    # verify signature
    vk = nacl.signing.VerifyKey(adv["sender"], encoder=nacl.encoding.HexEncoder)
    env_obj = Envelope(**adv)
    print(f"     sig valid: {env_obj.verify(vk)}")

# ============ TEST 2: GOVERN -> REPORT govern_ack ============
print("\n=== TEST 2: GOVERN -> REPORT govern_ack ===")
constitution_v = 7
govern = make_envelope(
    MessageType.GOVERN,
    sender_pubkey=me_pubkey,
    body={
        "type": "constitution",
        "constitution": {
            "version": constitution_v,
            "rules": ["test rule from phase 2 driver"],
        },
    },
    signing_key=sk,
)
send_mcast(govern)
print(f"  sent GOVERN v{constitution_v}")

def is_govern_ack_for_me(j, addr):
    return (j.get("type") == int(MessageType.REPORT)
            and addr[0] == XIAO_IP
            and isinstance(j.get("body"), dict)
            and j["body"].get("task") == "govern_ack")

rep, addr = listen(is_govern_ack_for_me, 5.0, "REPORT govern_ack")
if rep is None:
    print("  ❌ no REPORT govern_ack received from XIAO")
else:
    print(f"  ✅ REPORT govern_ack received from {addr[0]}")
    print(f"     sender:    {rep['sender'][:16]}...")
    print(f"     recipient: {rep['recipient'][:16]}...")
    print(f"     body:      {json.dumps(rep['body'])}")
    vk = nacl.signing.VerifyKey(rep["sender"], encoder=nacl.encoding.HexEncoder)
    env_obj = Envelope(**rep)
    print(f"     sig valid: {env_obj.verify(vk)}")
    body = rep["body"]
    print(f"     ack v={body.get('constitution_version')} (sent v={constitution_v})  result={body.get('result')}")

# ============ TEST 3: bad-shape GOVERN should be rejected ============
print("\n=== TEST 3: malformed GOVERN should be silently dropped ===")
bad = make_envelope(
    MessageType.GOVERN,
    sender_pubkey=me_pubkey,
    body={"type": "constitution", "constitution": {"rules": ["no version field"]}},  # no version
    signing_key=sk,
)
send_mcast(bad)
print(f"  sent malformed GOVERN (no version field)")
rep2, addr2 = listen(is_govern_ack_for_me, 3.0, "(should NOT see) REPORT govern_ack")
if rep2 is None:
    print("  ✅ no ack — correctly rejected")
else:
    print(f"  ❌ XIAO acked malformed GOVERN: {json.dumps(rep2['body'])}")

print("\nphase 2 live verification complete.")
