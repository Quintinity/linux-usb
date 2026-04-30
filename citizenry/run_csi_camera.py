#!/usr/bin/env python3
"""Launcher for the Jetson CSI camera citizen (IMX219 via gst-launch).

Mirrors run_wifi_camera.py for the XIAO. Usage:

    python -m citizenry.run_csi_camera

Defaults are tuned for SmolVLA observation feed (input ~224×224, downscaled
on source to keep WiFi bandwidth small): 640×480 @ 30 fps, JPEG q=70,
auto white-balance. exposuretimerange + gainrange + wbmode are exposed
because the IMX219 in indoor/low light can ship near-black frames with
defaults.
"""

from __future__ import annotations

import argparse
import asyncio
import signal

from .csi_camera_citizen import CSICameraCitizen


async def main(args: argparse.Namespace) -> None:
    citizen = CSICameraCitizen(
        resolution=tuple(args.resolution),
        framerate=args.framerate,
        name=args.name,
        camera_role=args.camera_role,
        sensor_id=args.sensor_id,
        wbmode=args.wbmode,
        exposuretimerange=args.exposuretimerange,
        gainrange=args.gainrange,
        jpeg_quality=args.jpeg_quality,
    )
    await citizen.start()
    print(
        f"[csi-camera] {args.name} → IMX219 sensor-id={args.sensor_id} "
        f"{args.resolution[0]}x{args.resolution[1]}@{args.framerate}fps "
        f"q={args.jpeg_quality} wb={args.wbmode}"
    )

    loop = asyncio.get_event_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()
    print("[csi-camera] stopping …")
    await citizen.stop()


def cli() -> None:
    p = argparse.ArgumentParser(description="Jetson CSI camera citizen")
    p.add_argument("--name", default="jetson-csi-imx219", help="Citizen name in mesh")
    p.add_argument(
        "--resolution", type=int, nargs=2, default=[640, 480], metavar=("W", "H"),
        help="Output resolution (Argus scales internally; default 640x480 for SmolVLA feed)",
    )
    p.add_argument("--framerate", type=int, default=30,
                   help="Negotiated framerate (sensor-mode selection); default 30")
    p.add_argument("--sensor-id", type=int, default=0,
                   help="nvarguscamerasrc sensor-id (default 0)")
    p.add_argument("--wbmode", type=int, default=1,
                   help="0=off,1=auto,2=incandescent,3=fluorescent,4=warm-fl,5=daylight,6=cloudy,7=twilight,8=shade,9=manual; default 1=auto")
    p.add_argument("--exposuretimerange", default=None,
                   help='nvarguscamerasrc exposuretimerange="<min_ns> <max_ns>"; default unset (auto)')
    p.add_argument("--gainrange", default=None,
                   help='nvarguscamerasrc gainrange="<min> <max>"; default unset (auto)')
    p.add_argument("--jpeg-quality", type=int, default=70,
                   help="jpegenc quality 1-100; default 70")
    p.add_argument("--camera-role", default=None,
                   help="Optional role tag (e.g. 'wrist', 'overhead'); enables continuous broadcast")
    args = p.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
