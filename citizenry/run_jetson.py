#!/usr/bin/env python3
"""Run citizens on the Jetson Orin Nano.

Surveys hardware on startup, spawns:
  - PolicyCitizen (always — the Jetson exists to run policies)
  - ManipulatorCitizen if a follower bus is detected
  - LeaderCitizen if a leader bus is detected
  - CameraCitizen per attached USB camera

A hotplug loop re-surveys every 3s and reacts to deltas.
"""

from __future__ import annotations

import argparse
import asyncio
import signal

from .leader_citizen import LeaderCitizen
from .manipulator_citizen import ManipulatorCitizen
from .camera_citizen import CameraCitizen
from .policy_citizen import PolicyCitizen
from .smolvla_runner import SmolVLARunner
from .survey import HardwareMap, survey_hardware


async def main(args):
    hw = await survey_hardware()
    print(f"[survey] cameras={len(hw.cameras)} accelerators={len(hw.accelerators)} "
          f"servo_buses={len(hw.servo_buses)} cpu={hw.compute.cpu_model}")

    runner = SmolVLARunner(model_id=args.model_id, device="cpu" if args.cpu else "cuda")
    print(f"[policy] loading {args.model_id} ...")
    runner.load()
    print("[policy] ready")

    citizens: dict[str, object] = {}
    policy = PolicyCitizen(runner=runner, name=args.name)
    await policy.start()
    citizens["policy"] = policy

    # If a follower / leader bus is present, spawn matching citizens.
    # ServoBus has no 'role' field — fall back to explicit port args for
    # disambiguation when multiple buses are present.
    for bus in hw.servo_buses:
        role = getattr(bus, "role", None)
        if role == "follower" or bus.port == args.follower_port:
            mc = ManipulatorCitizen(follower_port=bus.port, hardware=hw)
            await mc.start()
            citizens[f"manipulator:{bus.port}"] = mc
        elif role == "leader" or bus.port == args.leader_port:
            lc = LeaderCitizen(leader_port=bus.port)
            await lc.start()
            citizens[f"leader:{bus.port}"] = lc
        else:
            # No role hint and no explicit --follower/--leader-port match —
            # treat the first unmatched bus as a follower (Jetson default).
            has_follower = any(
                k.startswith("manipulator:") for k in citizens
            )
            if not has_follower:
                mc = ManipulatorCitizen(follower_port=bus.port, hardware=hw)
                await mc.start()
                citizens[f"manipulator:{bus.port}"] = mc

    # USB cameras. Assign roles by enumeration order so the first two cameras
    # advertise themselves as "wrist" and "base" — matching the default
    # policy_citizen.observation_cameras Law. Extra cameras get no role and
    # only respond to on-demand frame_capture proposals (no continuous
    # broadcast).
    roles = ["wrist", "base"]
    cam_enum_idx = 0
    for cam in hw.cameras:
        if cam.kind == "usb":
            try:
                idx = int(cam.path.replace("/dev/video", ""))
                role = roles[cam_enum_idx] if cam_enum_idx < len(roles) else None
                cc = CameraCitizen(
                    camera_index=idx,
                    name=f"jetson-cam-{idx}",
                    camera_role=role,
                )
                await cc.start()
                citizens[cam.path] = cc
                cam_enum_idx += 1
            except Exception as e:
                print(f"[hardware] camera {cam.path} failed: {e}")

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    print(f"[run_jetson] {len(citizens)} citizens running. Ctrl-C to stop.")
    await stop.wait()
    print("\nshutting down...")
    for c in citizens.values():
        try:
            await c.stop()
        except Exception:
            pass


def _parse():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", default="jetson-policy",
                   help="Name for the PolicyCitizen (default: jetson-policy)")
    p.add_argument("--model-id", default="lerobot/smolvla_base",
                   help="HuggingFace model ID for SmolVLA (default: lerobot/smolvla_base)")
    p.add_argument("--leader-port", default=None,
                   help="Serial port for the leader arm (overrides survey role detection)")
    p.add_argument("--follower-port", default=None,
                   help="Serial port for the follower arm (overrides survey role detection)")
    p.add_argument("--cpu", action="store_true",
                   help="Run on CPU instead of CUDA (slow; for debugging)")
    return p.parse_args()


def cli():
    asyncio.run(main(_parse()))


if __name__ == "__main__":
    cli()
