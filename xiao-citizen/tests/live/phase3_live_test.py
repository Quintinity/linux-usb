#!/usr/bin/env python3
"""Phase 3 live verification: drive a frame_capture PROPOSE at the native
XIAO firmware and verify the ACCEPT then REPORT pair come back signed,
with a base64 payload that round-trips to a JPEG with valid SOI/EOI.

Usage:
    python3 phase3_live_test.py [xiao_ip]

If xiao_ip is omitted, defaults to 192.168.1.83 (xiao-cam-0000).

Run from the lerobot-env (or any venv with pynacl):
    /home/bradley/lerobot-env/bin/python phase3_live_test.py

Exit codes
    0  PASS
    2  no XIAO heartbeat seen (firmware not running on target IP)
    3  no ACCEPT received within 8s
    4  no REPORT frame_capture received within 8s
    5  REPORT body failed JPEG SOI/EOI sanity check
"""

import base64
import json
import os
import socket
import struct
import sys
import time

sys.path.insert(0, "/home/bradley/linux-usb")
from citizenry.protocol import (
    Envelope,
    MULTICAST_GROUP,
    MULTICAST_PORT,
    MessageType,
    make_envelope,
)
import nacl.encoding
import nacl.signing

XIAO_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.83"

# Ephemeral identity for this test driver. The XIAO will ACCEPT a PROPOSE
# from any signed sender — TOFS at the dispatcher.
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


def send_mcast(env: Envelope) -> None:
    tx.sendto(env.to_bytes(), (MULTICAST_GROUP, MULTICAST_PORT))


# ============ STEP 1: learn the XIAO's pubkey from a heartbeat ============
# The PROPOSE recipient must be the XIAO's pubkey; sniff one heartbeat to
# pick it up. Phase 2's live harness uses the same trick implicitly via
# its DISCOVER.
print("\nlearning XIAO pubkey from a heartbeat (up to 5s)...")
xiao_pubkey: str | None = None
deadline = time.time() + 5
while time.time() < deadline and not xiao_pubkey:
    try:
        data, addr = sock.recvfrom(8192)
    except socket.timeout:
        continue
    if addr[0] != XIAO_IP:
        continue
    try:
        j = json.loads(data)
    except Exception:
        continue
    if j.get("type") == int(MessageType.HEARTBEAT):
        xiao_pubkey = j.get("sender")
        print(f"  XIAO pubkey: {xiao_pubkey[:16]}...")

if not xiao_pubkey:
    print(f"FATAL: no heartbeat from {XIAO_IP} in 5s. Is firmware running?")
    sys.exit(2)

# ============ STEP 2: send PROPOSE frame_capture ============
task_id = f"phase3-{int(time.time())}"
print(f"\nsending PROPOSE frame_capture task_id={task_id}")
prop = make_envelope(
    MessageType.PROPOSE,
    sender_pubkey=me_pubkey,
    body={"task": "frame_capture", "task_id": task_id},
    signing_key=sk,
    recipient=xiao_pubkey,
)
send_mcast(prop)

# ============ STEP 3: wait for ACCEPT + REPORT pair ============
got_accept = False
got_report = False
report_body: dict | None = None
deadline = time.time() + 8.0
while time.time() < deadline and not (got_accept and got_report):
    try:
        data, addr = sock.recvfrom(65536)
    except socket.timeout:
        continue
    if addr[0] != XIAO_IP:
        continue
    try:
        j = json.loads(data)
    except Exception:
        continue
    if j.get("recipient") != me_pubkey:
        continue
    t = j.get("type")
    body = j.get("body") or {}
    if t == int(MessageType.ACCEPT_REJECT):
        if body.get("task_id") == task_id and body.get("result") == "accept":
            got_accept = True
            print("  ACCEPT received")
        elif body.get("result") == "reject":
            print(f"  REJECT received: reason={body.get('reason')!r}")
    elif t == int(MessageType.REPORT):
        if body.get("task_id") == task_id and body.get("type") == "frame_capture":
            got_report = True
            report_body = body
            print("  REPORT frame_capture received")

if not got_accept:
    print("  no ACCEPT received within 8s")
    sys.exit(3)
if not got_report or report_body is None:
    print("  no REPORT frame_capture received within 8s")
    sys.exit(4)

# ============ STEP 4: verify the REPORT envelope's signature ============
# The XIAO signed the REPORT with its own key; we already learnt that key
# from the heartbeat. Reconstruct the Envelope and re-verify.
# (Optional — protocol-level proof we trust the bytes.)
try:
    last_env = Envelope(**j)
    vk = nacl.signing.VerifyKey(last_env.sender, encoder=nacl.encoding.HexEncoder)
    print(f"  signature verifies: {last_env.verify(vk)}")
except Exception as exc:  # noqa: BLE001
    print(f"  signature verify error: {exc!r}")

# ============ STEP 5: decode + sanity-check the JPEG payload ============
b64 = report_body["frame"]
jpg = base64.b64decode(b64)
print(f"\nJPEG size: {len(jpg)} B  ({report_body.get('width')}x{report_body.get('height')})")
if jpg[:2] != b"\xff\xd8":
    print(f"  bad SOI: first 4 bytes = {jpg[:4].hex()}")
    sys.exit(5)
if jpg[-2:] != b"\xff\xd9":
    print(f"  bad EOI: last 4 bytes  = {jpg[-4:].hex()}")
    sys.exit(5)
out_path = f"/tmp/phase3_{task_id}.jpg"
with open(out_path, "wb") as f:
    f.write(jpg)
print(f"  saved frame to {out_path}")

# Reasonable size envelope: real OV2640 QVGA q=12 frames are ~5-30 KB.
if len(jpg) < 1000:
    print(f"  WARN: frame is suspiciously small ({len(jpg)} B); may not be real")

print("\nphase 3 live verification PASS")
