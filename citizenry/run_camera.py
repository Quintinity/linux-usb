#!/usr/bin/env python3
"""Run a camera citizen on the local machine."""

import asyncio
import argparse
import signal

from .camera_citizen import CameraCitizen


async def main(camera_index: int, resolution: tuple[int, int], name: str):
    citizen = CameraCitizen(
        camera_index=camera_index,
        resolution=resolution,
        name=name,
    )

    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await citizen.start()
    print(f"Camera citizen '{name}' running. Press Ctrl+C to stop.")

    await stop_event.wait()
    await citizen.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a camera citizen")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    parser.add_argument("--name", default="camera-sense", help="Citizen name")
    args = parser.parse_args()

    asyncio.run(main(args.camera, (args.width, args.height), args.name))
