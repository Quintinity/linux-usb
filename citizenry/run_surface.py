#!/usr/bin/env python3
"""Run the Surface Pro 7 governor citizen.

Usage:
    python -m citizenry surface [--leader-port /dev/ttyACM1] [--fps 60] [--dashboard]
"""

import argparse
import asyncio
import signal

from .surface_citizen import SurfaceCitizen
from .survey import survey_hardware


async def main(args):
    hw = await survey_hardware()
    print(f"[survey] cameras={len(hw.cameras)} accelerators={len(hw.accelerators)} "
          f"servo_buses={len(hw.servo_buses)} cpu={hw.compute.cpu_model}")
    citizen = SurfaceCitizen(
        leader_port=args.leader_port,
        teleop_fps=args.fps,
        hardware=hw,
    )

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(citizen)))

    await citizen.start()

    # Optionally start the dashboard
    if args.dashboard:
        from .dashboard import run_dashboard
        asyncio.create_task(run_dashboard(citizen))

    # Run until stopped
    try:
        while citizen._running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await citizen.stop()


async def shutdown(citizen):
    print("\nshutting down...")
    await citizen.stop()


def cli():
    parser = argparse.ArgumentParser(description="Surface Pro 7 — Governor Citizen")
    parser.add_argument("--leader-port", default="/dev/ttyACM1", help="Leader arm serial port")
    parser.add_argument("--fps", type=float, default=60.0, help="Teleop frame rate")
    parser.add_argument("--dashboard", action="store_true", help="Show live TUI dashboard")
    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
