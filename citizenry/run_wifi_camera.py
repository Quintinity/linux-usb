#!/usr/bin/env python3
"""Launcher for a WiFi camera citizen.

Wraps the existing CameraCitizen with an HTTP MJPEG URL instead of a
local /dev/video index. Lets a network camera (e.g., XIAO ESP32S3 Sense
running CameraWebServer) participate in the citizenry as a sense node.

Usage:
    python -m citizenry.run_wifi_camera --url http://xiao-cam-001.local:81/stream
"""

from __future__ import annotations

import argparse
import asyncio
import signal

from .camera_citizen import CameraCitizen


async def main(args: argparse.Namespace) -> None:
    citizen = CameraCitizen(
        camera_index=args.url,  # cv2.VideoCapture accepts URL strings
        resolution=tuple(args.resolution),
        name=args.name,
    )
    await citizen.start()
    print(f"[wifi-camera] {args.name} → {args.url}")

    loop = asyncio.get_event_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()
    print("[wifi-camera] stopping …")
    await citizen.stop()


def cli() -> None:
    p = argparse.ArgumentParser(description="WiFi camera citizen")
    p.add_argument(
        "--url",
        default="http://xiao-cam-001.local:81/stream",
        help="MJPEG stream URL the camera serves",
    )
    p.add_argument("--name", default="wifi-cam-xiao-001", help="Citizen name in mesh")
    p.add_argument(
        "--resolution",
        type=int,
        nargs=2,
        default=[640, 480],
        metavar=("W", "H"),
        help="Hint resolution (advisory; XIAO stream resolution is set on the device)",
    )
    args = p.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
