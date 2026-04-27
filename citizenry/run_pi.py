#!/usr/bin/env python3
"""Run Pi citizens with auto-detection.

Surveys local hardware on startup, always spawns a brain citizen so the Pi
participates in the country regardless of what's plugged in, and additionally
spawns hardware-specific citizens (PiCitizen per servo bus, CameraCitizen per
USB camera). A hotplug loop re-surveys every 3s and reacts to deltas: spawns
new citizens for added devices, stops them for removed ones, and triggers a
mid-life ADVERTISE so the brain's capabilities propagate immediately.

Usage:
    python -m citizenry.run_pi                    # Auto-detect everything
    python -m citizenry.run_pi --port /dev/ttyACM0  # Legacy single-arm mode
"""

import argparse
import asyncio
import signal

from .pi_citizen import PiCitizen
from .camera_citizen import CameraCitizen
from .citizen import Citizen
from .survey import HardwareMap, project_capabilities, survey_hardware


async def main(args):
    if args.port and not args.auto_detect:
        await _run_single(args.port)
        return
    await _run_auto_detect()


async def _run_single(port: str):
    """Legacy: run a single follower citizen."""
    citizen = PiCitizen(follower_port=port)
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await citizen.start()
    print(f"Pi citizen running on {port}. Ctrl+C to stop.")
    await stop_event.wait()
    print("\nshutting down...")
    await citizen.stop()


def _brain_name(hw: HardwareMap) -> str:
    """Brain takes its dominant accelerator's name when present."""
    if any(a.kind.startswith("hailo") for a in hw.accelerators):
        return "pi-inference"
    if any(a.kind == "nvidia" for a in hw.accelerators):
        return "pi-gpu"
    if any(a.kind.startswith("coral") for a in hw.accelerators):
        return "pi-edge"
    return "pi-brain"


async def _spawn_servo_citizen(citizens: dict, bus, hw: HardwareMap, name: str):
    print(f"[hardware] Servo controller: {bus.port} → {name}")
    try:
        citizen = PiCitizen(follower_port=bus.port, hardware=hw)
        citizen.name = name
        await citizen.start()
        citizens[bus.port] = citizen
    except Exception as e:
        print(f"[hardware] Failed on {bus.port}: {e}")


async def _spawn_camera_citizen(citizens: dict, cam, name: str):
    print(f"[hardware] USB camera: {cam.path} → {name}")
    try:
        cam_index = int(cam.path.replace("/dev/video", ""))
        citizen = CameraCitizen(camera_index=cam_index, name=name)
        await citizen.start()
        citizens[cam.path] = citizen
    except Exception as e:
        print(f"[hardware] Failed on {cam.path}: {e}")


async def _stop_citizen(citizens: dict, key: str, label: str):
    if key in citizens:
        print(f"[hotplug] {label} removed: {key}")
        try:
            await citizens[key].stop()
        except Exception:
            pass
        del citizens[key]


async def _run_auto_detect():
    """Survey hardware, always spawn brain + per-device citizens, then hotplug-watch."""
    print("[auto-detect] Scanning for hardware...")

    hw = await survey_hardware()
    print(f"[survey] cameras={len(hw.cameras)} accelerators={len(hw.accelerators)} "
          f"servo_buses={len(hw.servo_buses)} cpu={hw.compute.cpu_model}")

    citizens: dict[str, any] = {}
    stop_event = asyncio.Event()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    # Brain is always present so the Pi is a country member even with no peripherals.
    brain_name = _brain_name(hw)
    brain_caps = project_capabilities(hw)
    print(f"[auto-detect] Brain '{brain_name}' caps={brain_caps}")
    brain = Citizen(name=brain_name, citizen_type="brain", capabilities=brain_caps)
    brain.hardware = hw
    await brain.start()
    citizens["brain"] = brain

    # Per-bus manipulation citizens (claim the actual servo controller).
    for i, bus in enumerate(hw.servo_buses):
        name = f"pi-arm-{i}" if len(hw.servo_buses) > 1 else "pi-follower"
        await _spawn_servo_citizen(citizens, bus, hw, name)

    # Per-USB-camera sensor citizens. CSI cameras are owned by the brain via its hw map.
    usb_cams = [c for c in hw.cameras if c.kind == "usb"]
    for i, cam in enumerate(usb_cams):
        name = f"pi-camera-{i}" if len(usb_cams) > 1 else "pi-camera"
        await _spawn_camera_citizen(citizens, cam, name)

    print(f"[auto-detect] {len(citizens)} citizens started. Monitoring for hotplug...")

    monitor_task = asyncio.create_task(_hotplug_loop(citizens, stop_event, hw))

    await stop_event.wait()
    print("\nshutting down all citizens...")
    monitor_task.cancel()

    for citizen in citizens.values():
        try:
            await citizen.stop()
        except Exception:
            pass
    print(f"[auto-detect] {len(citizens)} citizens stopped.")


async def _hotplug_loop(citizens: dict, stop_event: asyncio.Event, last_hw: HardwareMap):
    """Re-survey every 3s; spawn/stop citizens for deltas; brain re-advertises."""
    try:
        while not stop_event.is_set():
            await asyncio.sleep(3)

            current = await survey_hardware()
            delta = current.diff(last_hw)
            if delta.is_empty():
                continue

            print(f"[hotplug] survey delta: {delta.summary()}")

            for bus in delta.servo_buses_added:
                idx = sum(1 for c in citizens.values() if isinstance(c, PiCitizen))
                await _spawn_servo_citizen(citizens, bus, current, f"pi-arm-{idx}")
            for bus in delta.servo_buses_removed:
                await _stop_citizen(citizens, bus.port, "Servo")

            for cam in delta.cameras_added:
                if cam.kind != "usb":
                    continue  # CSI cams ride on the brain's hw map
                idx = sum(1 for c in citizens.values() if isinstance(c, CameraCitizen))
                await _spawn_camera_citizen(citizens, cam, f"pi-camera-{idx}")
            for cam in delta.cameras_removed:
                if cam.kind != "usb":
                    continue
                await _stop_citizen(citizens, cam.path, "Camera")

            # Brain mutates its caps + hardware in place and forces an immediate advertise.
            brain = citizens.get("brain")
            if brain is not None:
                new_caps = project_capabilities(current)
                if new_caps != brain.capabilities:
                    print(f"[hotplug] Brain caps {brain.capabilities} → {new_caps}")
                    brain.capabilities = new_caps
                brain.hardware = current
                brain._send_advertise()

            last_hw = current

    except asyncio.CancelledError:
        pass


def cli():
    parser = argparse.ArgumentParser(description="Pi 5 — Auto-Detecting Citizen Launcher")
    parser.add_argument("--port", default=None, help="Specific servo port (disables auto-detect)")
    parser.add_argument("--follower-port", default=None, dest="port", help="Alias for --port")
    parser.add_argument("--auto-detect", action="store_true", default=True)
    parser.add_argument("--no-auto-detect", action="store_false", dest="auto_detect")
    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
