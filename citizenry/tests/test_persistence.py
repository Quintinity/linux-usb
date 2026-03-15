"""Tests for v2.0 persistence — contracts and immune memory."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from citizenry.persistence import (
    save_contracts, load_contracts,
    save_immune_memory, load_immune_memory,
    CITIZENRY_DIR,
)


@pytest.fixture
def tmp_citizenry(tmp_path, monkeypatch):
    """Override CITIZENRY_DIR to a temp directory."""
    import citizenry.persistence as p
    monkeypatch.setattr(p, "CITIZENRY_DIR", tmp_path)
    return tmp_path


class TestContractPersistence:
    def test_save_and_load(self, tmp_citizenry):
        contracts = [
            {"id": "c1", "provider": "aaa", "consumer": "bbb", "status": "active"},
            {"id": "c2", "provider": "ccc", "consumer": "ddd", "status": "proposed"},
        ]
        save_contracts("test-citizen", contracts)
        loaded = load_contracts("test-citizen")
        assert len(loaded) == 2
        assert loaded[0]["id"] == "c1"
        assert loaded[1]["status"] == "proposed"

    def test_load_missing(self, tmp_citizenry):
        loaded = load_contracts("nonexistent")
        assert loaded == []

    def test_load_corrupted(self, tmp_citizenry):
        path = tmp_citizenry / "bad.contracts.json"
        path.write_text("not json{{{")
        loaded = load_contracts("bad")
        assert loaded == []

    def test_overwrite(self, tmp_citizenry):
        save_contracts("test", [{"id": "old"}])
        save_contracts("test", [{"id": "new"}])
        loaded = load_contracts("test")
        assert len(loaded) == 1
        assert loaded[0]["id"] == "new"


class TestImmuneMemoryPersistence:
    def test_save_and_load(self, tmp_citizenry):
        patterns = [
            {"pattern_type": "voltage_collapse", "severity": "critical"},
            {"pattern_type": "thermal_overload", "severity": "warning"},
        ]
        save_immune_memory("test-citizen", patterns)
        loaded = load_immune_memory("test-citizen")
        assert len(loaded) == 2
        assert loaded[0]["pattern_type"] == "voltage_collapse"

    def test_load_missing(self, tmp_citizenry):
        loaded = load_immune_memory("nonexistent")
        assert loaded == []

    def test_valid_json(self, tmp_citizenry):
        patterns = [{"pattern_type": "test"}]
        save_immune_memory("test", patterns)
        path = tmp_citizenry / "test.immune.json"
        data = json.loads(path.read_text())
        assert isinstance(data, list)
