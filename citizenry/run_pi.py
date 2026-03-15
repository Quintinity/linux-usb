#!/usr/bin/env python3
"""Run the Pi 5 follower citizen.

Usage:
    python -m citizenry.run_pi [--follower-port /dev/ttyACM0]
"""

import argparse
import asyncio
import signal

from .pi_citizen import PiCitizen


async def main(args):
    citizen = PiCitizen(
        follower_port=args.follower_port,
    )

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(citizen)))

    await citizen.start()

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
    parser = argparse.ArgumentParser(description="Pi 5 — Follower Citizen")
    parser.add_argument("--follower-port", default="/dev/ttyACM0", help="Follower arm serial port")
    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
