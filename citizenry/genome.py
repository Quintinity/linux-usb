"""Citizen Genome — portable configuration DNA.

A genome captures everything a citizen has learned: calibration,
protection settings, skills, XP, immune memory, and hardware descriptor.
Genomes are versioned and signed by the governor for trust.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .persistence import CITIZENRY_DIR


@dataclass
class CitizenGenome:
    """The complete portable state of a citizen."""

    citizen_name: str = ""
    citizen_type: str = ""
    hardware: dict[str, Any] = field(default_factory=dict)
    calibration: dict[str, Any] = field(default_factory=dict)
    protection: dict[str, Any] = field(default_factory=dict)
    xp: dict[str, int] = field(default_factory=dict)
    skill_definitions: dict[str, Any] = field(default_factory=dict)
    immune_memory: list[dict] = field(default_factory=list)
    node_pubkey: str | None = None
    version: int = 1
    exported_at: float = field(default_factory=time.time)
    governor_signature: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> CitizenGenome:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, s: str) -> CitizenGenome:
        return cls.from_dict(json.loads(s))


def export_genome(genome: CitizenGenome, path: Path | None = None) -> Path:
    """Export a genome to a JSON file."""
    if path is None:
        CITIZENRY_DIR.mkdir(parents=True, exist_ok=True)
        path = CITIZENRY_DIR / f"{genome.citizen_name}.genome.json"
    genome.exported_at = time.time()
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(genome.to_json() + "\n")
        tmp.replace(path)
    except OSError:
        if tmp.exists():
            tmp.unlink()
        raise
    return path


def import_genome(path: Path) -> CitizenGenome:
    """Import a genome from a JSON file."""
    return CitizenGenome.from_json(path.read_text())


def load_genome(citizen_name: str) -> CitizenGenome | None:
    """Load a genome from the default location. Returns None if not found."""
    path = CITIZENRY_DIR / f"{citizen_name}.genome.json"
    try:
        return import_genome(path)
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def save_genome(genome: CitizenGenome) -> Path:
    """Save a genome to the default location."""
    return export_genome(genome)


def compute_fleet_average(genomes: list[CitizenGenome]) -> CitizenGenome:
    """Compute a fleet average genome from multiple genomes of the same type.

    Averages calibration values, takes union of immune memory,
    zeros XP (new citizen starts fresh), and uses the latest protection settings.
    """
    if not genomes:
        return CitizenGenome()

    avg = CitizenGenome(
        citizen_name="fleet_average",
        citizen_type=genomes[0].citizen_type,
        hardware=genomes[0].hardware.copy(),
        version=max(g.version for g in genomes),
    )

    # Average calibration
    cal_keys: set[str] = set()
    for g in genomes:
        cal_keys.update(g.calibration.keys())

    for key in cal_keys:
        values = [g.calibration[key] for g in genomes if key in g.calibration]
        if values and all(isinstance(v, (int, float)) for v in values):
            avg.calibration[key] = sum(values) / len(values)
        elif values:
            avg.calibration[key] = values[0]

    # Use latest protection settings
    latest = max(genomes, key=lambda g: g.exported_at)
    avg.protection = latest.protection.copy()

    # Union of immune memory (deduplicate by pattern_type)
    seen_patterns: set[str] = set()
    for g in genomes:
        for pattern in g.immune_memory:
            pt = pattern.get("pattern_type", "")
            if pt and pt not in seen_patterns:
                seen_patterns.add(pt)
                avg.immune_memory.append(pattern)

    # Union of skill definitions
    for g in genomes:
        avg.skill_definitions.update(g.skill_definitions)

    # XP starts at zero for new citizen
    avg.xp = {}

    return avg
