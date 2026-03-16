"""Allow running as: python -m citizenry [role] [options]

Default (no args): Launch the Governor CLI with natural language governance.
Roles: surface, pi, camera, cli
"""

import sys
import asyncio


def main():
    role = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("surface", "pi", "camera", "cli", "help") else "cli"

    if role == "help":
        print("Usage: python -m citizenry [role] [options]")
        print()
        print("  cli      — Governor CLI with natural language (default)")
        print("  surface  — Surface Pro 7 governor with teleop")
        print("  pi       — Pi 5 follower arm citizen")
        print("  camera   — USB camera citizen")
        print()
        print("Examples:")
        print("  python -m citizenry                    # NL governance CLI")
        print("  python -m citizenry surface             # Teleop governor")
        print("  python -m citizenry pi                  # Follower arm")
        print("  python -m citizenry camera --name cam1  # Camera citizen")
        sys.exit(0)

    if role in ("cli",):
        if len(sys.argv) > 1 and sys.argv[1] == "cli":
            sys.argv.pop(1)
        from .governor_cli import run_cli
        asyncio.run(run_cli())
    elif role == "surface":
        sys.argv.pop(1)
        from .run_surface import cli
        cli()
    elif role == "pi":
        sys.argv.pop(1)
        from .run_pi import cli
        cli()
    elif role == "camera":
        sys.argv.pop(1)
        from .run_camera import main as camera_main
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--camera", type=int, default=0)
        parser.add_argument("--width", type=int, default=640)
        parser.add_argument("--height", type=int, default=480)
        parser.add_argument("--name", default="camera-sense")
        args = parser.parse_args()
        asyncio.run(camera_main(args.camera, (args.width, args.height), args.name))


if __name__ == "__main__":
    main()
