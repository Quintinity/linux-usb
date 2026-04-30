"""v1 → v2 Constitution migration.

Reads an on-disk v1 Constitution JSON, mints a fresh Authority key (or
loads the existing one), re-signs the Constitution with v2 fields, and
writes back atomically with a ``.v1.bak.json`` backup alongside.

Idempotent: running twice on a v2 file is a noop.

CLI:
    python -m citizenry.scripts.migrate_constitution [path1.json path2.json ...]

If no paths are given, migrates every file under ``~/.citizenry/``
matching ``*.constitution.json``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable

import nacl.signing

from citizenry.authority import load_or_create_authority_key
from citizenry.constitution import Constitution


def migrate_v1_dict(
    v1_dict: dict,
    authority_signing_key: nacl.signing.SigningKey,
) -> dict:
    """Convert a v1 Constitution dict to a v2 Constitution dict, signed."""
    if v1_dict.get("version", 1) >= 2:
        return v1_dict  # already v2
    c = Constitution.from_dict(v1_dict)
    c.version = 2
    # Reset signature; will be replaced by sign() below.
    c.signature = ""
    c.authority_pubkey = ""
    c.sign(authority_signing_key)  # populates authority_pubkey + governor_pubkey
    return c.to_dict()


def migrate_file(
    path: Path,
    authority_signing_key: nacl.signing.SigningKey | None = None,
) -> bool:
    """Migrate one Constitution JSON file. Returns True if the file was changed."""
    if authority_signing_key is None:
        authority_signing_key = load_or_create_authority_key()
    raw = path.read_text()
    data = json.loads(raw)
    if data.get("version", 1) >= 2:
        return False
    backup = path.with_suffix(".v1.bak.json")
    backup.write_text(raw)
    new_dict = migrate_v1_dict(data, authority_signing_key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(new_dict, sort_keys=True, separators=(",", ":")))
    os.replace(tmp, path)
    return True


def _discover_default_paths() -> list[Path]:
    home = Path.home() / ".citizenry"
    if not home.exists():
        return []
    return sorted(home.glob("*.constitution.json"))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m citizenry.scripts.migrate_constitution",
        description="Migrate v1 Constitution JSON files to v2.",
    )
    parser.add_argument("paths", nargs="*", type=Path,
                        help="Constitution JSON files (default: ~/.citizenry/*.constitution.json)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    paths = args.paths or _discover_default_paths()
    if not paths:
        print("No Constitution files found.", file=sys.stderr)
        return 1
    auth = load_or_create_authority_key()
    changed = 0
    for p in paths:
        if args.dry_run:
            data = json.loads(p.read_text())
            v = data.get("version", 1)
            print(f"{p}: version={v} {'(would migrate)' if v < 2 else '(noop)'}")
            continue
        if migrate_file(p, authority_signing_key=auth):
            print(f"migrated: {p}")
            changed += 1
        else:
            print(f"already v2: {p}")
    print(f"done. {changed} file(s) migrated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
