"""Tests for citizen genome."""

import json
import pytest
from pathlib import Path

from citizenry.genome import (
    CitizenGenome, export_genome, import_genome, load_genome, save_genome,
    compute_fleet_average,
)


class TestCitizenGenome:
    def test_create(self):
        g = CitizenGenome(citizen_name="arm-1", citizen_type="manipulator")
        assert g.citizen_name == "arm-1"
        assert g.version == 1

    def test_roundtrip_dict(self):
        g = CitizenGenome(
            citizen_name="arm-1",
            citizen_type="manipulator",
            calibration={"offset_1": 0.3, "offset_2": -1.2},
            xp={"basic_grasp": 50},
        )
        d = g.to_dict()
        g2 = CitizenGenome.from_dict(d)
        assert g2.citizen_name == "arm-1"
        assert g2.calibration == {"offset_1": 0.3, "offset_2": -1.2}
        assert g2.xp == {"basic_grasp": 50}

    def test_roundtrip_json(self):
        g = CitizenGenome(
            citizen_name="arm-1",
            immune_memory=[{"pattern_type": "voltage_collapse"}],
        )
        j = g.to_json()
        g2 = CitizenGenome.from_json(j)
        assert len(g2.immune_memory) == 1


class TestGenomeExportImport:
    def test_export_import(self, tmp_path):
        g = CitizenGenome(
            citizen_name="test-arm",
            citizen_type="manipulator",
            xp={"basic_grasp": 100},
        )
        path = tmp_path / "test-arm.genome.json"
        export_genome(g, path)
        assert path.exists()

        g2 = import_genome(path)
        assert g2.citizen_name == "test-arm"
        assert g2.xp == {"basic_grasp": 100}

    def test_export_creates_valid_json(self, tmp_path):
        g = CitizenGenome(citizen_name="test")
        path = tmp_path / "test.genome.json"
        export_genome(g, path)
        data = json.loads(path.read_text())
        assert data["citizen_name"] == "test"


class TestFleetAverage:
    def test_empty_list(self):
        avg = compute_fleet_average([])
        assert avg.citizen_name == ""

    def test_single_genome(self):
        g = CitizenGenome(
            citizen_name="arm-1",
            citizen_type="manipulator",
            calibration={"offset": 1.0},
            xp={"grasp": 100},
        )
        avg = compute_fleet_average([g])
        assert avg.citizen_type == "manipulator"
        assert avg.calibration["offset"] == 1.0
        assert avg.xp == {}  # XP zeroed for new citizen

    def test_average_calibration(self):
        g1 = CitizenGenome(
            citizen_name="arm-1",
            citizen_type="manipulator",
            calibration={"offset": 1.0},
            exported_at=100.0,
        )
        g2 = CitizenGenome(
            citizen_name="arm-2",
            citizen_type="manipulator",
            calibration={"offset": 3.0},
            exported_at=200.0,
        )
        avg = compute_fleet_average([g1, g2])
        assert avg.calibration["offset"] == pytest.approx(2.0)

    def test_union_immune_memory(self):
        g1 = CitizenGenome(
            citizen_name="arm-1",
            citizen_type="manipulator",
            immune_memory=[{"pattern_type": "voltage_collapse"}],
            exported_at=100.0,
        )
        g2 = CitizenGenome(
            citizen_name="arm-2",
            citizen_type="manipulator",
            immune_memory=[
                {"pattern_type": "voltage_collapse"},
                {"pattern_type": "thermal_overload"},
            ],
            exported_at=200.0,
        )
        avg = compute_fleet_average([g1, g2])
        types = {p["pattern_type"] for p in avg.immune_memory}
        assert types == {"voltage_collapse", "thermal_overload"}

    def test_latest_protection_settings(self):
        g1 = CitizenGenome(
            citizen_name="arm-1",
            citizen_type="manipulator",
            protection={"max_torque": 400},
            exported_at=100.0,
        )
        g2 = CitizenGenome(
            citizen_name="arm-2",
            citizen_type="manipulator",
            protection={"max_torque": 500},
            exported_at=200.0,
        )
        avg = compute_fleet_average([g1, g2])
        assert avg.protection["max_torque"] == 500  # From latest


def test_genome_carries_node_pubkey():
    from citizenry.genome import CitizenGenome
    g = CitizenGenome(
        citizen_name="jetson-1",
        citizen_type="policy",
        node_pubkey="ab" * 32,
    )
    assert g.node_pubkey == "ab" * 32
    d = g.to_dict()
    assert d["node_pubkey"] == "ab" * 32
    assert CitizenGenome.from_dict(d).node_pubkey == "ab" * 32
