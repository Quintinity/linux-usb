"""Persistence for citizen state that survives restarts.

Stores neighbor tables and constitutions as JSON files in ~/.citizenry/.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


CITIZENRY_DIR = Path.home() / ".citizenry"


@dataclass
class NeighborRecord:
    pubkey: str
    name: str
    citizen_type: str
    capabilities: list[str]
    last_addr: tuple[str, int]
    last_seen: float
    has_constitution: bool


def _ensure_dir() -> None:
    CITIZENRY_DIR.mkdir(parents=True, exist_ok=True)


# --- Neighbor persistence ---------------------------------------------------

def save_neighbors(name: str, neighbors: dict[str, NeighborRecord]) -> None:
    """Save the neighbor table to ~/.citizenry/<name>.neighbors.json."""
    _ensure_dir()
    path = CITIZENRY_DIR / f"{name}.neighbors.json"
    data = {k: asdict(v) for k, v in neighbors.items()}
    # Convert last_addr tuples to lists for JSON (they round-trip as lists)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        tmp.replace(path)
    except OSError:
        if tmp.exists():
            tmp.unlink()
        raise


def load_neighbors(name: str) -> dict[str, NeighborRecord]:
    """Load the neighbor table from disk. Returns empty dict on any error."""
    path = CITIZENRY_DIR / f"{name}.neighbors.json"
    try:
        data = json.loads(path.read_text())
        result: dict[str, NeighborRecord] = {}
        for k, v in data.items():
            # JSON stores last_addr as a list; convert back to tuple
            v["last_addr"] = tuple(v["last_addr"])
            result[k] = NeighborRecord(**v)
        return result
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return {}


# --- Constitution persistence -----------------------------------------------

def save_constitution(name: str, constitution: dict) -> None:
    """Save the received constitution to ~/.citizenry/<name>.constitution.json."""
    _ensure_dir()
    path = CITIZENRY_DIR / f"{name}.constitution.json"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(constitution, indent=2) + "\n")
        tmp.replace(path)
    except OSError:
        if tmp.exists():
            tmp.unlink()
        raise


def load_constitution(name: str) -> dict | None:
    """Load constitution from disk. Returns None if not found or corrupted."""
    path = CITIZENRY_DIR / f"{name}.constitution.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


# --- v2.0: Contracts persistence ----------------------------------------------

def save_contracts(name: str, contracts: list[dict]) -> None:
    """Save active symbiosis contracts to ~/.citizenry/<name>.contracts.json."""
    _ensure_dir()
    path = CITIZENRY_DIR / f"{name}.contracts.json"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(contracts, indent=2) + "\n")
        tmp.replace(path)
    except OSError:
        if tmp.exists():
            tmp.unlink()
        raise


def load_contracts(name: str) -> list[dict]:
    """Load contracts from disk. Returns empty list on any error."""
    path = CITIZENRY_DIR / f"{name}.contracts.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []


# --- v2.0: Immune memory persistence -----------------------------------------

def save_immune_memory(name: str, patterns: list[dict]) -> None:
    """Save immune memory patterns to ~/.citizenry/<name>.immune.json."""
    _ensure_dir()
    path = CITIZENRY_DIR / f"{name}.immune.json"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(patterns, indent=2) + "\n")
        tmp.replace(path)
    except OSError:
        if tmp.exists():
            tmp.unlink()
        raise


def load_immune_memory(name: str) -> list[dict]:
    """Load immune memory from disk. Returns empty list on any error."""
    path = CITIZENRY_DIR / f"{name}.immune.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
