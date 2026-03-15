"""Tests for the mycelium warning network."""

import time
import pytest
from citizenry.mycelium import (
    Warning, Severity, MyceliumNetwork, MITIGATION_FACTORS, WARNING_DECAY_TIME,
)


class TestWarning:
    def test_create(self):
        w = Warning(severity=Severity.CRITICAL, detail="voltage_collapse")
        assert w.severity == Severity.CRITICAL
        assert w.detail == "voltage_collapse"

    def test_to_report_body(self):
        w = Warning(
            severity=Severity.WARNING,
            detail="thermal",
            motor="elbow_flex",
            value=58.0,
            threshold=60.0,
        )
        body = w.to_report_body()
        assert body["type"] == "warning"
        assert body["severity"] == "warning"
        assert body["motor"] == "elbow_flex"

    def test_from_report_body(self):
        body = {
            "type": "warning",
            "severity": "critical",
            "detail": "voltage_collapse",
            "motor": "shoulder_pan",
            "value": 5.2,
            "threshold": 6.0,
        }
        w = Warning.from_report_body(body)
        assert w.severity == Severity.CRITICAL
        assert w.value == 5.2


class TestMyceliumNetwork:
    def test_add_warning(self):
        net = MyceliumNetwork()
        net.add_warning(Warning(severity=Severity.WARNING, detail="test"))
        assert net.active_count() == 1

    def test_deduplication(self):
        net = MyceliumNetwork()
        w1 = Warning(severity=Severity.WARNING, detail="test", source_citizen="aaa")
        w2 = Warning(severity=Severity.WARNING, detail="test", source_citizen="aaa")
        net.add_warning(w1)
        net.add_warning(w2)
        assert net.active_count() == 1  # Deduplicated

    def test_different_warnings_not_deduplicated(self):
        net = MyceliumNetwork()
        net.add_warning(Warning(severity=Severity.WARNING, detail="thermal"))
        net.add_warning(Warning(severity=Severity.WARNING, detail="voltage"))
        assert net.active_count() == 2

    def test_mitigation_factor_no_warnings(self):
        net = MyceliumNetwork()
        assert net.current_mitigation_factor() == 1.0

    def test_mitigation_factor_warning(self):
        net = MyceliumNetwork()
        net.add_warning(Warning(severity=Severity.WARNING))
        assert net.current_mitigation_factor() == 0.75

    def test_mitigation_factor_critical(self):
        net = MyceliumNetwork()
        net.add_warning(Warning(severity=Severity.CRITICAL))
        assert net.current_mitigation_factor() == 0.50

    def test_mitigation_factor_emergency(self):
        net = MyceliumNetwork()
        net.add_warning(Warning(severity=Severity.EMERGENCY))
        assert net.current_mitigation_factor() == 0.0

    def test_should_stop(self):
        net = MyceliumNetwork()
        assert not net.should_stop()
        net.add_warning(Warning(severity=Severity.EMERGENCY))
        assert net.should_stop()

    def test_decay_removes_old(self):
        net = MyceliumNetwork()
        old = Warning(severity=Severity.WARNING, detail="old")
        old.timestamp = time.time() - WARNING_DECAY_TIME - 1
        net.active_warnings.append(old)
        net.add_warning(Warning(severity=Severity.WARNING, detail="new"))
        expired = net.decay_warnings()
        assert len(expired) == 1
        assert net.active_count() == 1

    def test_slow_channel_payload(self):
        net = MyceliumNetwork()
        net.add_warning(Warning(severity=Severity.INFO, detail="info_warn"))
        net.add_warning(Warning(severity=Severity.CRITICAL, detail="critical_warn"))
        payload = net.get_slow_channel_payload()
        # Only info/warning severity on slow channel
        assert len(payload) == 1
        assert payload[0]["detail"] == "info_warn"

    def test_fast_channel_warnings(self):
        net = MyceliumNetwork()
        net.add_warning(Warning(severity=Severity.INFO, detail="slow"))
        net.add_warning(Warning(severity=Severity.CRITICAL, detail="fast"))
        fast = net.get_fast_channel_warnings()
        assert len(fast) == 1
        assert fast[0].detail == "fast"
