"""Tests for immune memory."""

import pytest
from citizenry.immune import (
    FaultPattern, ImmuneMemory, bootstrap_immune_memory, KNOWN_PATTERNS,
)


class TestFaultPattern:
    def test_create(self):
        p = FaultPattern(pattern_type="voltage_collapse", severity="critical")
        assert p.pattern_type == "voltage_collapse"
        assert p.occurrences == 1
        assert len(p.id) == 12

    def test_roundtrip(self):
        p = FaultPattern(
            pattern_type="thermal",
            conditions={"max_temperature": {"max": 60}},
            mitigation="reduce_speed",
        )
        d = p.to_dict()
        p2 = FaultPattern.from_dict(d)
        assert p2.pattern_type == "thermal"
        assert p2.conditions == {"max_temperature": {"max": 60}}


class TestImmuneMemory:
    def test_add_pattern(self):
        mem = ImmuneMemory()
        p = FaultPattern(pattern_type="test")
        mem.add(p)
        assert len(mem.get_all()) == 1

    def test_deduplicate_by_type(self):
        mem = ImmuneMemory()
        p1 = FaultPattern(pattern_type="voltage_collapse")
        p2 = FaultPattern(pattern_type="voltage_collapse")
        mem.add(p1)
        mem.add(p2)
        assert len(mem.get_all()) == 1
        assert mem.get_all()[0].occurrences == 2

    def test_match_threshold_exceeded(self):
        mem = ImmuneMemory()
        mem.add(FaultPattern(
            pattern_type="thermal",
            conditions={"max_temperature": {"max": 60}},
        ))
        matches = mem.match({"max_temperature": 65})
        assert len(matches) == 1
        assert matches[0].pattern_type == "thermal"

    def test_match_below_threshold(self):
        mem = ImmuneMemory()
        mem.add(FaultPattern(
            pattern_type="thermal",
            conditions={"max_temperature": {"max": 60}},
        ))
        matches = mem.match({"max_temperature": 45})
        assert len(matches) == 0

    def test_match_min_threshold(self):
        mem = ImmuneMemory()
        mem.add(FaultPattern(
            pattern_type="voltage",
            conditions={"min_voltage": {"min": 6.0}},
        ))
        matches = mem.match({"min_voltage": 5.2})
        assert len(matches) == 1

    def test_merge(self):
        mem1 = ImmuneMemory()
        mem1.add(FaultPattern(pattern_type="a"))

        patterns = [
            FaultPattern(pattern_type="b"),
            FaultPattern(pattern_type="a"),  # Duplicate
        ]
        added = mem1.merge(patterns)
        assert added == 1  # Only "b" is new
        assert len(mem1.get_all()) == 2

    def test_prune_lru(self):
        mem = ImmuneMemory()
        mem.MAX_PATTERNS = 5
        for i in range(10):
            mem.add(FaultPattern(pattern_type=f"type_{i}"))
        assert len(mem.get_all()) <= 5

    def test_serialization(self):
        mem = ImmuneMemory()
        mem.add(FaultPattern(pattern_type="test", severity="critical"))
        data = mem.to_list()
        mem2 = ImmuneMemory.from_list(data)
        assert len(mem2.get_all()) == 1
        assert mem2.get_all()[0].pattern_type == "test"


class TestBootstrap:
    def test_bootstrap_has_known_patterns(self):
        mem = bootstrap_immune_memory()
        types = {p.pattern_type for p in mem.get_all()}
        assert "voltage_collapse" in types
        assert "thermal_overload" in types
        assert "overcurrent" in types
        assert "servo_error_flag" in types

    def test_known_patterns_count(self):
        assert len(KNOWN_PATTERNS) >= 4
