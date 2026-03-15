"""Allow running as: python -m citizenry <surface|pi>"""

import sys


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("surface", "pi"):
        print("Usage: python -m citizenry <surface|pi> [options]")
        print()
        print("  surface  — Run the Surface Pro 7 governor citizen")
        print("  pi       — Run the Pi 5 follower citizen")
        sys.exit(1)

    role = sys.argv.pop(1)  # Remove role arg so argparse sees the rest

    if role == "surface":
        from .run_surface import cli
        cli()
    elif role == "pi":
        from .run_pi import cli
        cli()


if __name__ == "__main__":
    main()
