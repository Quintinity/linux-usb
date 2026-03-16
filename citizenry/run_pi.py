#!/usr/bin/env python3
"""Run Pi citizens with auto-detection.

Scans for all connected servo controllers and cameras, spawns the right
citizen for each. Watches for USB hotplug — new devices auto-join,
unplugged devices broadcast will and stop.

Usage:
    python -m citizenry.run_pi                    # Auto-detect everything
    python -m citizenry.run_pi --port /dev/ttyACM0  # Legacy single-arm mode
"""

import argparse
import asyncio
import signal
import time
from pathlib import Path

from .pi_citizen import PiCitizen
from .camera_citizen import CameraCitizen


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


async def _run_auto_detect():
    """Auto-detect all hardware and spawn citizens."""
    print("[auto-detect] Scanning for hardware...")

    citizens: dict[str, any] = {}
    stop_event = asyncio.Event()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    # Scan for servo controllers
    servo_ports = _find_servo_ports()
    for i, port in enumerate(servo_ports):
        name = f"pi-arm-{i}" if len(servo_ports) > 1 else "pi-follower"
        print(f"[auto-detect] Servo controller: {port} → {name}")
        try:
            citizen = PiCitizen(follower_port=port)
            citizen.name = name
            await citizen.start()
            citizens[port] = citizen
        except Exception as e:
            print(f"[auto-detect] Failed on {port}: {e}")

    # Scan for cameras
    camera_paths = _find_cameras()
    for i, cam_path in enumerate(camera_paths):
        name = f"pi-camera-{i}" if len(camera_paths) > 1 else "pi-camera"
        cam_index = int(cam_path.replace("/dev/video", ""))
        print(f"[auto-detect] Camera: {cam_path} → {name}")
        try:
            citizen = CameraCitizen(camera_index=cam_index, name=name)
            await citizen.start()
            citizens[cam_path] = citizen
        except Exception as e:
            print(f"[auto-detect] Failed on {cam_path}: {e}")

    if not citizens:
        print("[auto-detect] No hardware found. Waiting for USB hotplug...")

    print(f"[auto-detect] {len(citizens)} citizens started. Monitoring for hotplug...")

    # Background hotplug monitor
    monitor_task = asyncio.create_task(_hotplug_loop(citizens, stop_event))

    await stop_event.wait()
    print("\nshutting down all citizens...")
    monitor_task.cancel()

    for port, citizen in citizens.items():
        try:
            await citizen.stop()
        except Exception:
            pass
    print(f"[auto-detect] {len(citizens)} citizens stopped.")


async def _hotplug_loop(citizens: dict, stop_event: asyncio.Event):
    """Poll for USB changes every 3 seconds."""
    known_servos = set(_find_servo_ports())
    known_cameras = set(_find_cameras())

    try:
        while not stop_event.is_set():
            await asyncio.sleep(3)

            current_servos = set(_find_servo_ports())

            # New servo controllers
            for port in current_servos - known_servos:
                idx = len([c for c in citizens.values() if isinstance(c, PiCitizen)])
                name = f"pi-arm-{idx}"
                print(f"[hotplug] New servo: {port} → {name}")
                try:
                    citizen = PiCitizen(follower_port=port)
                    citizen.name = name
                    await citizen.start()
                    citizens[port] = citizen
                except Exception as e:
                    print(f"[hotplug] Failed: {e}")

            # Removed servo controllers
            for port in known_servos - current_servos:
                if port in citizens:
                    print(f"[hotplug] Servo removed: {port}")
                    try:
                        await citizens[port].stop()
                    except Exception:
                        pass
                    del citizens[port]

            current_cameras = set(_find_cameras())

            # New cameras
            for cam_path in current_cameras - known_cameras:
                idx = len([c for c in citizens.values() if isinstance(c, CameraCitizen)])
                name = f"pi-camera-{idx}"
                cam_index = int(cam_path.replace("/dev/video", ""))
                print(f"[hotplug] New camera: {cam_path} → {name}")
                try:
                    citizen = CameraCitizen(camera_index=cam_index, name=name)
                    await citizen.start()
                    citizens[cam_path] = citizen
                except Exception as e:
                    print(f"[hotplug] Failed: {e}")

            # Removed cameras
            for cam_path in known_cameras - current_cameras:
                if cam_path in citizens:
                    print(f"[hotplug] Camera removed: {cam_path}")
                    try:
                        await citizens[cam_path].stop()
                    except Exception:
                        pass
                    del citizens[cam_path]

            known_servos = current_servos
            known_cameras = current_cameras

    except asyncio.CancelledError:
        pass


def _find_servo_ports() -> list[str]:
    """Find all Feetech/Dynamixel servo controllers via sysfs."""
    ports = []
    tty_path = Path("/sys/class/tty")
    if not tty_path.exists():
        return sorted(str(p) for p in Path("/dev").glob("ttyACM*"))

    for entry in sorted(tty_path.iterdir()):
        try:
            device_path = entry / "device"
            if not device_path.exists():
                continue
            usb_path = (device_path / "..").resolve()
            vid_path = usb_path / "idVendor"
            if not vid_path.exists():
                continue
            vid = vid_path.read_text().strip()
            if vid in ("1a86", "0403"):  # Feetech CH340 / Dynamixel FTDI
                ports.append(f"/dev/{entry.name}")
        except Exception:
            continue
    return sorted(ports)


def _find_cameras() -> list[str]:
    """Find USB cameras (V4L2 capture devices)."""
    cameras = []
    for dev in sorted(Path("/dev").glob("video*")):
        try:
            num = int(dev.name.replace("video", ""))
            if num > 3:  # Skip codec/ISP devices
                continue
        except ValueError:
            continue
        try:
            import cv2
            cap = cv2.VideoCapture(str(dev))
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    cameras.append(str(dev))
            else:
                cap.release()
        except Exception:
            continue
    return cameras


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
