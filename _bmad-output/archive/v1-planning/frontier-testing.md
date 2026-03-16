# armOS -- Frontier Testing Strategy

**Author:** Quinn (QA Engineer)
**Date:** 2026-03-15
**Status:** ACTION -- implement incrementally starting Sprint 2
**Scope:** Next-generation testing infrastructure that uses simulation, AI, chaos engineering, and automation to achieve confidence levels impossible with traditional testing alone

---

## Executive Summary

The QA review (review-qa.md) established the test pyramid for armOS. The QA execution enhancements (qa-execution-enhancements.md) extended it for business scenarios. This document goes further: it defines a testing infrastructure where **a simulated SO-101 runs the actual armOS code in CI, AI generates and maintains test cases, real hardware runs nightly regression, and chaos engineering proves resilience before users discover fragility.**

These are not theoretical proposals. Each section specifies concrete tools, implementation steps, and the sprint where work should begin.

---

## 1. Digital Twin Testing -- MuJoCo Simulation of SO-101

### The Problem

Every test in review-qa.md that touches servo behavior uses `MockServoProtocol` -- a Python object that stores positions in a dictionary. It validates logic but cannot catch physics-dependent bugs: overshoot on fast moves, gravity-induced drift, torque limits exceeded during specific arm configurations, or timing-dependent control loop instabilities.

### The Solution: MuJoCo Digital Twin

Build a MuJoCo simulation of the SO-101 arm that implements `ServoProtocol`, replacing the mock with a physics engine. The teleop loop, diagnostics, calibration, and data collection code run unmodified against simulated servos that obey physics.

### Implementation

#### 1.1 SO-101 URDF/MJCF Model

```
tools/simulation/
    so101.xml                  # MuJoCo MJCF model of SO-101 (6-DOF, STS3215 actuators)
    so101_scene.xml            # Scene with table, gravity, lighting
    assets/
        meshes/                # STL meshes from SO-101 CAD files (simplified for sim)
```

**Source geometry:** SO-101 CAD files are available from Seeed Studio's GitHub. Convert STL meshes to convex hulls using `trimesh` for collision. Define joint limits, gear ratios, and damping from the STS3215 datasheet:

| Parameter | STS3215 Value | MJCF Attribute |
|-----------|--------------|----------------|
| Stall torque | 19 kg-cm @ 12V | `joint/actuator @ctrlrange` |
| No-load speed | 0.222 sec/60deg | `actuator @kv` (back-EMF constant) |
| Position range | 0-4095 (0-360 deg) | `joint @range` |
| Gear ratio | 254:1 | `actuator @gear` |
| Weight per servo | 60g | `body @mass` |

#### 1.2 SimServoProtocol -- The Bridge

```python
# armos/hal/plugins/sim_feetech.py

import mujoco
import numpy as np
from armos.hal.servo_protocol import ServoProtocol, CommunicationError

class SimFeetechProtocol(ServoProtocol):
    """MuJoCo-backed servo protocol for testing without hardware.

    Runs the actual MuJoCo physics step on every sync_write, reads
    joint positions/velocities/torques on sync_read. Simulates real
    STS3215 register behavior including:
    - Position feedback with quantization noise (12-bit ADC)
    - Voltage reporting (configurable, defaults to 7.4V)
    - Temperature model (rises under sustained load)
    - Communication latency (configurable delay per read/write)
    - Overload protection triggering
    """

    def __init__(self, model_path: str = "tools/simulation/so101.xml"):
        self._model = mujoco.MjModel.from_xml_path(model_path)
        self._data = mujoco.MjData(self._model)
        self._connected = False
        self._servo_temps: dict[int, float] = {}  # Thermal model state
        self._latency_ms: float = 0.5             # Simulated bus latency
        self._fail_rate: float = 0.0
        self._voltage: float = 7.4

    def connect(self, port: str, baudrate: int = 1_000_000) -> None:
        self._connected = True
        mujoco.mj_resetData(self._model, self._data)

    def sync_read(self, servo_ids: list[int], address: int, length: int) -> list[bytes]:
        """Read positions from MuJoCo joint state, quantized to 12-bit."""
        if random.random() < self._fail_rate:
            raise CommunicationError("Simulated packet loss")
        time.sleep(self._latency_ms / 1000)
        results = []
        for sid in servo_ids:
            joint_idx = self._servo_id_to_joint(sid)
            pos_rad = self._data.qpos[joint_idx]
            pos_raw = int((pos_rad / (2 * np.pi)) * 4096) % 4096
            results.append(pos_raw.to_bytes(2, 'little'))
        return results

    def sync_write(self, servo_ids: list[int], address: int, data: list[bytes]) -> None:
        """Write goal positions, then step physics."""
        for sid, d in zip(servo_ids, data):
            joint_idx = self._servo_id_to_joint(sid)
            pos_raw = int.from_bytes(d[:2], 'little')
            pos_rad = (pos_raw / 4096) * 2 * np.pi
            self._data.ctrl[joint_idx] = pos_rad
        # Step physics (1ms timestep, run enough steps to match real servo update rate)
        for _ in range(int(self._latency_ms)):
            mujoco.mj_step(self._model, self._data)
        self._update_thermal_model()

    # Fault injection methods
    def inject_voltage_sag(self, voltage: float) -> None:
        self._voltage = voltage

    def inject_packet_loss(self, rate: float) -> None:
        self._fail_rate = rate

    def inject_servo_jam(self, servo_id: int) -> None:
        """Lock a joint to simulate mechanical jam."""
        joint_idx = self._servo_id_to_joint(servo_id)
        self._model.jnt_limited[joint_idx] = True
        # Set both limits to current position
        pos = self._data.qpos[joint_idx]
        self._model.jnt_range[joint_idx] = [pos, pos]
```

#### 1.3 Simulated Fault Scenarios

These faults cannot be tested with `MockServoProtocol` because they depend on physics:

| Fault | Simulation Method | What It Catches |
|-------|------------------|-----------------|
| Gravity-induced drift | Disable torque on joint 2 (shoulder), let arm droop | Does the watchdog detect position deviation? |
| Payload overload | Add a 500g mass to end effector | Does overload protection fire correctly? |
| Collision with table | Place obstacle in workspace, command move through it | Does the safety system halt on excessive torque? |
| Servo jam (stripped gear) | Lock joint via `inject_servo_jam()` | Does the teleop loop detect position error and alert? |
| Oscillation/instability | Set PD gains too high, command step input | Does the system detect oscillation and reduce gains? |
| Multi-servo cascading failure | Fail servos 1 and 2 simultaneously | Does graceful degradation work, or does the whole arm go limp? |

#### 1.4 CI Pipeline Integration

```yaml
# .github/workflows/simulation-tests.yml
name: Simulation Tests
on: [push, pull_request]

jobs:
  sim-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install mujoco numpy armos[dev]
      - name: Run simulation test suite
        run: |
          pytest tests/simulation/ -v --timeout=120
      - name: Run 60-second simulated teleop
        run: |
          python -m armos.teleop --protocol sim_feetech --duration 60 --benchmark
      - name: Upload latency report
        uses: actions/upload-artifact@v4
        with:
          name: latency-report
          path: benchmark_results/
```

**Every PR runs against a simulated robot.** The simulation test suite takes approximately 2 minutes on a GitHub Actions runner (MuJoCo runs headless, no GPU required).

#### 1.5 Tools and Dependencies

| Tool | Version | Purpose | License |
|------|---------|---------|---------|
| MuJoCo | 3.x | Physics simulation engine | Apache 2.0 |
| mujoco (Python) | 3.x | Python bindings for MuJoCo | Apache 2.0 |
| trimesh | latest | STL mesh processing for collision geometry | MIT |
| numpy | latest | Array operations for joint state | BSD |

**Why MuJoCo over PyBullet:** MuJoCo has better contact dynamics, faster simulation speed, and is the standard in the LeRobot ecosystem. LeRobot's own simulation examples use MuJoCo. Using the same engine reduces impedance mismatch when users go from armOS simulation to LeRobot sim-to-real training.

#### 1.6 Sprint Allocation

| Task | Sprint | Size | Depends On |
|------|--------|------|------------|
| SO-101 MJCF model (geometry + joint limits) | 2 | M | SO-101 CAD files |
| SimFeetechProtocol (basic position read/write) | 2 | M | Story 2.1 (ServoProtocol ABC) |
| Thermal and voltage simulation | 3 | S | SimFeetechProtocol |
| Fault injection methods | 3 | S | SimFeetechProtocol |
| CI pipeline integration | 3 | S | SimFeetechProtocol |
| Full teleop loop in simulation | 5 | M | Story 6.2 (teleop) |
| Simulated data collection pipeline | 6 | M | Story 9.3 (data collection) |

---

## 2. AI-Generated Test Cases

### The Problem

Writing tests for a robotics HAL is tedious and error-prone. The servo protocol has hundreds of edge cases (malformed packets, out-of-range values, timing violations). Humans miss edge cases; AI can generate them systematically.

### 2.1 Claude-Generated pytest Suites

Feed the PRD, architecture, and ServoProtocol ABC to Claude and ask it to generate exhaustive test cases. This is not a one-time exercise -- it runs on every interface change.

#### Implementation: Test Generation Script

```python
# tools/generate_tests.py

"""
Generate pytest test cases from armOS interface definitions.

Usage:
    python tools/generate_tests.py --interface armos.hal.servo_protocol.ServoProtocol
    python tools/generate_tests.py --schema armos/profiles/schema.py
    python tools/generate_tests.py --all

Reads the interface definition (ABC methods, type hints, docstrings),
the PRD acceptance criteria, and existing test coverage gaps,
then generates pytest files using Claude API.
"""

import ast
import inspect
import subprocess
from pathlib import Path

def extract_interface(module_path: str) -> dict:
    """Parse ABC and extract method signatures, type hints, docstrings."""
    # AST parsing to get method signatures without importing
    ...

def get_coverage_gaps(test_dir: str, source_dir: str) -> list[str]:
    """Run pytest-cov and identify uncovered branches."""
    result = subprocess.run(
        ["pytest", "--cov", source_dir, "--cov-report=json", test_dir],
        capture_output=True
    )
    # Parse coverage JSON, return list of uncovered lines/branches
    ...

def generate_tests_with_claude(interface: dict, gaps: list[str]) -> str:
    """Call Claude API with interface + gaps, get back pytest code."""
    prompt = f"""
    Generate pytest test cases for this interface:
    {interface}

    These lines/branches are not yet covered:
    {gaps}

    Requirements:
    - Use pytest parametrize for edge cases
    - Include both happy path and error cases
    - Test boundary values (0, max, max+1, negative)
    - Test type errors (wrong types passed to each parameter)
    - Each test must have a descriptive name explaining what it verifies
    - Use MockServoProtocol from conftest.py
    """
    # Call Claude API
    ...
```

#### When to Run

- **On interface change:** When any ABC or Pydantic model changes, re-generate tests for that interface. Diff against existing tests, present new tests for review.
- **On coverage drop:** When coverage falls below 80%, identify gaps and generate tests targeting uncovered branches.
- **Sprint planning:** At the start of each sprint, generate tests for the stories in that sprint. Tests exist before code -- true TDD.

### 2.2 Property-Based Testing with Hypothesis

Property-based testing is especially valuable for the servo protocol where inputs have wide ranges and complex invariants.

#### Implementation

```python
# tests/property/test_servo_protocol_properties.py

from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

# Strategy: valid servo ID (1-253 for Feetech)
servo_id = st.integers(min_value=1, max_value=253)

# Strategy: valid position (0-4095 for 12-bit encoder)
position = st.integers(min_value=0, max_value=4095)

# Strategy: raw serial bytes (for fuzzing)
raw_bytes = st.binary(min_size=1, max_size=256)


class TestSyncReadWriteRoundTrip:
    """Property: writing a position and reading it back returns the same value."""

    @given(
        ids=st.lists(servo_id, min_size=1, max_size=6, unique=True),
        positions=st.lists(position, min_size=1, max_size=6),
    )
    def test_write_read_roundtrip(self, mock_protocol, ids, positions):
        assume(len(ids) == len(positions))
        # Write positions
        data = [p.to_bytes(2, 'little') for p in positions]
        mock_protocol.sync_write(ids, 0x2A, data)  # Goal Position register
        # Read back
        result = mock_protocol.sync_read(ids, 0x38, 2)  # Present Position register
        read_positions = [int.from_bytes(r, 'little') for r in result]
        for written, read in zip(positions, read_positions):
            assert abs(written - read) <= 1  # Allow 1-tick quantization


class TestProfileValidationProperties:
    """Property: any valid profile can be serialized and deserialized without loss."""

    @given(
        servo_count=st.integers(min_value=1, max_value=12),
        overload_torque=st.integers(min_value=50, max_value=500),
        max_temperature=st.integers(min_value=50, max_value=85),
    )
    def test_profile_roundtrip(self, servo_count, overload_torque, max_temperature):
        profile = generate_random_profile(servo_count, overload_torque, max_temperature)
        yaml_str = profile.to_yaml()
        reloaded = RobotProfile.from_yaml(yaml_str)
        assert profile == reloaded


class ServoStateMachine(RuleBasedStateMachine):
    """Stateful test: model the servo protocol as a state machine.
    Any sequence of valid operations should not crash or corrupt state."""

    def __init__(self):
        super().__init__()
        self.protocol = MockServoProtocol(servo_ids=[1, 2, 3, 4, 5, 6])
        self.protocol.connect("/dev/ttyUSB0")
        self.expected_positions = {i: 2048 for i in range(1, 7)}

    @rule(servo_id=servo_id, position=position)
    def write_position(self, servo_id, position):
        assume(servo_id in range(1, 7))
        self.protocol.sync_write([servo_id], 0x2A, [position.to_bytes(2, 'little')])
        self.expected_positions[servo_id] = position

    @rule(servo_id=servo_id)
    def read_position(self, servo_id):
        assume(servo_id in range(1, 7))
        result = self.protocol.sync_read([servo_id], 0x38, 2)
        actual = int.from_bytes(result[0], 'little')
        assert abs(actual - self.expected_positions[servo_id]) <= 1

    @rule()
    def ping_all(self):
        for sid in range(1, 7):
            assert self.protocol.ping(sid) is True

    @invariant()
    def no_servo_lost(self):
        """After any sequence of operations, all servos are still reachable."""
        for sid in range(1, 7):
            assert self.protocol.ping(sid) is True


TestServoStateMachine = ServoStateMachine.TestCase
```

### 2.3 Serial Protocol Fuzzing

Feed random bytes to the serial packet parser. It must never crash, never corrupt state, and always return a clear error.

#### Implementation

```python
# tests/fuzz/test_serial_fuzz.py

from hypothesis import given, strategies as st, settings

@given(data=st.binary(min_size=1, max_size=1024))
@settings(max_examples=10_000)
def test_packet_parser_never_crashes(data):
    """Feed random bytes to the Feetech packet parser.
    It must return either a valid packet or a ParseError. Never crash."""
    try:
        packet = FeetechPacket.from_bytes(data)
        # If it parsed, validate it has required fields
        assert packet.servo_id is not None
        assert packet.instruction is not None
    except PacketParseError as e:
        # Expected for random data -- just verify it is a clean error
        assert str(e)  # Error message is not empty
    except Exception as e:
        # Any other exception is a bug
        pytest.fail(f"Unexpected exception on input {data.hex()}: {e}")


@given(
    header=st.just(b'\xFF\xFF'),
    servo_id=st.integers(min_value=0, max_value=255),
    length=st.integers(min_value=0, max_value=255),
    instruction=st.integers(min_value=0, max_value=255),
    params=st.binary(min_size=0, max_size=200),
)
def test_structured_fuzz_with_valid_header(header, servo_id, length, instruction, params):
    """Fuzz with valid Feetech header but random body.
    Tests the parser's handling of length mismatches, bad checksums, etc."""
    packet_bytes = header + bytes([servo_id, length, instruction]) + params
    try:
        FeetechPacket.from_bytes(packet_bytes)
    except PacketParseError:
        pass  # Expected
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")
```

### 2.4 Mutation Testing

Mutation testing answers: "Are our tests actually catching bugs, or are they just running code?" Use `mutmut` to inject small changes (mutations) into the source code and verify that tests catch them.

#### Implementation

```toml
# pyproject.toml

[tool.mutmut]
paths_to_mutate = "armos/hal/,armos/diagnostics/,armos/profiles/"
tests_dir = "tests/"
runner = "pytest"
# Require 90%+ mutation kill rate for critical modules
```

```yaml
# .github/workflows/mutation-tests.yml (weekly)
name: Mutation Testing
on:
  schedule:
    - cron: '0 2 * * 0'  # Every Sunday at 2 AM

jobs:
  mutmut:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install mutmut armos[dev]
      - run: mutmut run --paths-to-mutate armos/hal/ --CI
      - run: mutmut results
      - name: Fail if mutation score below 85%
        run: |
          score=$(mutmut results --json | python -c "import sys,json; d=json.load(sys.stdin); print(d['killed']/(d['killed']+d['survived'])*100)")
          python -c "assert $score >= 85, f'Mutation score {$score}% < 85%'"
```

**Target mutation kill rates:**

| Module | Target | Rationale |
|--------|--------|-----------|
| `armos/hal/` | 90% | Safety-critical: wrong servo commands damage hardware |
| `armos/diagnostics/` | 85% | Diagnostic false-negatives hide real problems |
| `armos/profiles/` | 90% | Profile validation is the first line of defense |
| `armos/ui/` | 70% | UI bugs are less dangerous than HAL bugs |

### 2.5 Sprint Allocation

| Task | Sprint | Size |
|------|--------|------|
| Hypothesis property tests for ServoProtocol | 2 | M |
| Hypothesis stateful tests (ServoStateMachine) | 3 | S |
| Serial protocol fuzzing | 3 | S |
| Profile validation property tests | 3 | S |
| mutmut configuration and baseline | 4 | S |
| Weekly mutation test CI job | 4 | S |
| Claude test generation script (v1) | 5 | M |

---

## 3. Hardware-in-the-Loop CI

### The Problem

Simulation catches physics bugs. Mocks catch logic bugs. But neither catches the real-world serial timing, USB controller quirks, or servo firmware edge cases that account for the majority of field failures. The product validation report documents failures that only manifest on real hardware: sync_read timeouts on specific USB hubs, servo responses arriving out of order, voltage sag under specific arm configurations.

### The Solution: Self-Hosted GitHub Actions Runner with Real SO-101

A dedicated machine with a real SO-101 connected runs hardware tests on every merge to main and on a nightly schedule.

### 3.1 Hardware Test Rig

```
[Self-Hosted Runner: Intel NUC or Surface Pro 7]
    |
    |-- USB-A: CH340 serial adapter --> SO-101 Follower arm (6x STS3215)
    |-- USB-A: CH340 serial adapter --> SO-101 Leader arm (6x STS3215)
    |-- USB-C: Powered USB hub
    |       |-- USB camera (1080p)
    |       |-- Yepkit YKUSH (switchable USB hub for disconnect testing)
    |
    |-- 12V power supply (bench supply with programmable output)
    |       |-- Relay board (for automated power cycling)
```

### 3.2 GitHub Actions Self-Hosted Runner Configuration

```yaml
# .github/workflows/hardware-tests.yml
name: Hardware-in-the-Loop Tests
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 3 * * *'  # Nightly at 3 AM

jobs:
  hardware-tests:
    runs-on: [self-hosted, armos-hw-rig]
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - name: Activate armos environment
        run: source /opt/armos/env/bin/activate
      - name: Verify hardware connected
        run: |
          armos detect --json | python -c "
          import sys, json
          hw = json.load(sys.stdin)
          assert hw['follower']['connected'], 'Follower arm not detected'
          assert hw['leader']['connected'], 'Leader arm not detected'
          "
      - name: Run hardware test suite
        run: pytest tests/hardware/ -v --timeout=300 --hw-rig
      - name: Run 60-second teleop benchmark
        run: armos teleop --duration 60 --benchmark --output benchmark_results.json
      - name: Check latency regression
        run: |
          python tools/check_latency_regression.py benchmark_results.json \
            --baseline benchmarks/baseline.json \
            --threshold 20  # percent regression allowed
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: hw-test-results-${{ github.sha }}
          path: |
            benchmark_results.json
            tests/hardware/results/
```

### 3.3 Automated Test Sequence

The hardware test suite runs the full robot workflow without human intervention:

```python
# tests/hardware/test_full_workflow.py

import pytest
import time

pytestmark = pytest.mark.hardware  # Skip unless --hw-rig flag is set


class TestHardwareWorkflow:
    """Full hardware-in-the-loop test sequence.
    Requires real SO-101 connected to the test runner."""

    def test_01_detect_hardware(self, hw_rig):
        """Both arms detected on expected ports."""
        result = hw_rig.detect()
        assert result.follower.port == "/dev/ttyUSB0"
        assert result.leader.port == "/dev/ttyUSB1"
        assert len(result.follower.servos) == 6
        assert len(result.leader.servos) == 6

    def test_02_ping_all_servos(self, hw_rig):
        """All 12 servos respond to ping."""
        for arm in [hw_rig.follower, hw_rig.leader]:
            for servo_id in arm.servo_ids:
                assert arm.protocol.ping(servo_id), f"Servo {servo_id} not responding"

    def test_03_read_telemetry(self, hw_rig):
        """All servos return valid telemetry."""
        for arm in [hw_rig.follower, hw_rig.leader]:
            telemetry = arm.protocol.get_telemetry(arm.servo_ids)
            for t in telemetry:
                assert 5.0 < t.voltage < 13.0, f"Voltage out of range: {t.voltage}V"
                assert 15 < t.temperature < 70, f"Temp out of range: {t.temperature}C"
                assert 0 <= t.position <= 4095, f"Position out of range: {t.position}"

    def test_04_calibration_roundtrip(self, hw_rig, tmp_path):
        """Calibrate, save, reload, verify positions match."""
        cal_path = tmp_path / "calibration.json"
        cal_data = hw_rig.calibrate_non_interactive()
        cal_data.save(cal_path)
        reloaded = CalibrationData.load(cal_path)
        assert cal_data == reloaded

    def test_05_teleop_60_seconds(self, hw_rig):
        """Run leader-follower teleop for 60 seconds. Verify latency and stability."""
        stats = hw_rig.run_teleop(duration_seconds=60)
        assert stats.p95_latency_ms < 20, f"p95 latency {stats.p95_latency_ms}ms > 20ms"
        assert stats.dropped_frames == 0, f"Dropped {stats.dropped_frames} frames"
        assert stats.communication_errors < 5, f"{stats.communication_errors} comm errors"

    def test_06_data_collection_5_episodes(self, hw_rig, tmp_path):
        """Record 5 episodes of 3 seconds each. Verify dataset integrity."""
        dataset_path = tmp_path / "test_dataset"
        hw_rig.record(
            task="test",
            episodes=5,
            episode_duration=3,
            output=dataset_path,
        )
        # Verify dataset
        assert (dataset_path / "meta" / "info.json").exists()
        import json
        info = json.loads((dataset_path / "meta" / "info.json").read_text())
        assert info["total_episodes"] == 5

    def test_07_diagnostics_all_pass(self, hw_rig):
        """Run full diagnostic suite. All checks must pass on a healthy rig."""
        results = hw_rig.run_diagnostics()
        failures = [r for r in results if r.status == "FAIL"]
        assert len(failures) == 0, f"Diagnostic failures: {failures}"
```

### 3.4 Handling Flaky Hardware Tests

Hardware tests are inherently flakier than software tests. A servo might occasionally drop a packet, a USB hub might glitch, or the power supply might have a momentary dip. Traditional binary pass/fail does not work.

#### Statistical Pass/Fail Thresholds

```python
# tests/hardware/conftest.py

class HardwareTestThresholds:
    """Statistical thresholds for hardware tests.
    A test passes if it meets the threshold over N runs."""

    # Communication reliability: 99.5% of reads succeed (allow 0.5% transient failures)
    COMM_RELIABILITY_MIN = 0.995

    # Teleop latency: p95 under 20ms in 4 out of 5 runs
    TELEOP_LATENCY_PASS_RATIO = 4 / 5
    TELEOP_LATENCY_P95_MAX_MS = 20

    # Diagnostic pass rate: all checks pass in 9 out of 10 runs
    DIAGNOSTIC_PASS_RATIO = 9 / 10

    # Maximum allowed flake rate before a test is quarantined
    MAX_FLAKE_RATE = 0.10  # 10%


def run_with_retries(test_fn, max_attempts=5, pass_ratio=0.8):
    """Run a hardware test multiple times and apply statistical pass/fail.

    A test passes if it succeeds in at least (pass_ratio * max_attempts) runs.
    Individual failures are logged as warnings, not errors.
    """
    results = []
    for attempt in range(max_attempts):
        try:
            test_fn()
            results.append(True)
        except AssertionError as e:
            results.append(False)
            logger.warning(f"Attempt {attempt+1}/{max_attempts} failed: {e}")

    pass_count = sum(results)
    required = int(max_attempts * pass_ratio)
    if pass_count < required:
        pytest.fail(
            f"Hardware test passed {pass_count}/{max_attempts} "
            f"(required {required}/{max_attempts})"
        )
```

#### Flake Tracking

```python
# tools/track_flakes.py

"""
Analyze hardware test results over time to identify:
1. Tests that flake more than 10% -- quarantine them
2. Tests that started flaking recently -- hardware degradation?
3. Correlation between flakes and time of day -- thermal issues?
"""

def analyze_flake_history(results_dir: Path, window_days: int = 30) -> FlakeReport:
    # Parse all test result JSON files from the last N days
    # Calculate per-test flake rate
    # Flag tests exceeding MAX_FLAKE_RATE
    # Detect upward flake trends (linear regression on failure rate)
    ...
```

### 3.5 Sprint Allocation

| Task | Sprint | Size | Hardware Cost |
|------|--------|------|---------------|
| Self-hosted runner setup (NUC or spare laptop) | 4 | M | $0-400 |
| Hardware test fixture (conftest, detect, ping) | 5 | M | $0 |
| Teleop benchmark test | 5 | S | $0 |
| Full workflow test | 6 | M | $0 |
| Yepkit YKUSH integration (automated USB disconnect) | 6 | M | $50 |
| Statistical pass/fail framework | 6 | S | $0 |
| Flake tracking and quarantine | 7 | S | $0 |
| Nightly schedule and alerting | 7 | S | $0 |

---

## 4. Chaos Engineering for Robots

### The Problem

Review-qa.md identified that NFR6 (retry on transient failure) and NFR7 (bus disconnection detection) are not testable without fault injection. The QA execution enhancements (DM-3, DM-4) require cable disconnect and power glitch recovery for demo mode. But these are currently manual tests. Chaos engineering automates them.

### 4.1 USB Disconnect Chaos

**Tool:** Yepkit YKUSH (programmable USB hub with per-port power switching, controllable via `ykushcmd`)

```python
# tests/chaos/test_usb_disconnect.py

import subprocess
import time
import pytest

pytestmark = pytest.mark.chaos


class TestUSBDisconnectChaos:
    """Randomly disconnect USB cables during active robot operations.
    Requires Yepkit YKUSH hub connected to the test rig."""

    def test_disconnect_during_teleop(self, hw_rig, ykush):
        """Pull the follower USB cable during active teleop.
        Verify: alert fires within 2 seconds, no data corruption."""

        # Start teleop in background
        teleop = hw_rig.start_teleop_async()
        time.sleep(5)  # Let teleop stabilize

        # Disconnect follower arm
        ykush.power_off(port=1)  # Port 1 = follower CH340
        disconnect_time = time.monotonic()

        # Wait for alert
        alert = teleop.wait_for_alert(timeout=3.0)
        alert_time = time.monotonic()

        assert alert is not None, "No disconnect alert fired within 3 seconds"
        assert alert.type == "BUS_DISCONNECT"
        assert (alert_time - disconnect_time) < 2.0, \
            f"Alert took {alert_time - disconnect_time:.1f}s (max 2.0s)"

        # Reconnect
        ykush.power_on(port=1)
        time.sleep(3)  # Allow re-enumeration

        # Verify recovery
        recovery_alert = teleop.wait_for_alert(timeout=5.0, type="BUS_RECONNECTED")
        assert recovery_alert is not None, "No reconnection alert"

        teleop.stop()
        assert teleop.stats.data_corruption_events == 0

    def test_random_disconnects_over_10_minutes(self, hw_rig, ykush):
        """Randomly disconnect and reconnect USB ports over 10 minutes.
        Verify: system always recovers, no zombie processes, no memory leaks."""

        teleop = hw_rig.start_teleop_async()
        rss_start = get_process_rss(teleop.pid)

        for _ in range(20):  # 20 random disconnect/reconnect cycles
            port = random.choice([1, 2])  # Follower or leader
            ykush.power_off(port=port)
            time.sleep(random.uniform(0.5, 3.0))
            ykush.power_on(port=port)
            time.sleep(random.uniform(2.0, 5.0))  # Allow re-enumeration

        teleop.stop()
        rss_end = get_process_rss(teleop.pid)

        assert teleop.stats.unrecovered_disconnects == 0
        assert (rss_end - rss_start) < 50 * 1024 * 1024  # < 50MB growth
```

### 4.2 Voltage Drop Chaos

**Tool:** Programmable bench power supply with SCPI control (e.g., Rigol DP832, Korad KA3005P) or a relay-controlled voltage divider for budget setups.

```python
# tests/chaos/test_voltage_chaos.py

class TestVoltageChaos:
    """Inject voltage drops via programmable power supply.
    Requires SCPI-controllable power supply or relay board."""

    def test_voltage_sag_during_teleop(self, hw_rig, power_supply):
        """Drop voltage from 7.4V to 6.0V during teleop.
        Verify: voltage alert fires, servos safe-stop, no position jump on recovery."""

        power_supply.set_voltage(7.4)
        teleop = hw_rig.start_teleop_async()
        time.sleep(5)

        # Record arm positions before sag
        positions_before = hw_rig.follower.read_positions()

        # Sag voltage
        power_supply.set_voltage(6.0)
        alert = teleop.wait_for_alert(timeout=3.0, type="VOLTAGE_LOW")
        assert alert is not None

        # Restore voltage
        power_supply.set_voltage(7.4)
        time.sleep(2)

        # Verify no position jump (servos should not have moved during sag)
        positions_after = hw_rig.follower.read_positions()
        for i, (before, after) in enumerate(zip(positions_before, positions_after)):
            assert abs(before - after) < 50, \
                f"Servo {i} jumped {abs(before - after)} ticks during voltage recovery"

    def test_complete_power_loss(self, hw_rig, power_supply):
        """Cut power entirely during teleop. Verify graceful handling."""
        power_supply.set_voltage(7.4)
        teleop = hw_rig.start_teleop_async()
        time.sleep(5)

        power_supply.set_voltage(0.0)  # Total power loss
        time.sleep(1)

        # Servos will stop responding -- verify armOS detects this
        alert = teleop.wait_for_alert(timeout=3.0)
        assert alert is not None
        assert alert.type in ["BUS_DISCONNECT", "VOLTAGE_CRITICAL", "SERVO_UNRESPONSIVE"]

        # Restore power
        power_supply.set_voltage(7.4)
        time.sleep(5)  # Servos re-initialize

        teleop.stop()
```

### 4.3 Individual Servo Failure Chaos

Kill responses from individual servos to verify graceful degradation. This uses the `FaultInjector` wrapper from review-qa.md (C2).

```python
# tests/chaos/test_servo_failure.py

class TestServoFailureChaos:

    def test_single_servo_failure_during_teleop(self, hw_rig):
        """One servo stops responding. Verify: that joint stops,
        other joints continue, user is alerted."""
        injector = FaultInjector(hw_rig.follower.protocol)
        hw_rig.follower.protocol = injector

        teleop = hw_rig.start_teleop_async()
        time.sleep(5)

        # Kill servo 3 (elbow)
        injector.fail_servo(servo_id=3, mode="silent")  # Stop responding to reads

        alert = teleop.wait_for_alert(timeout=3.0)
        assert alert is not None
        assert "servo 3" in alert.message.lower()

        # Verify other servos still moving
        positions_1 = hw_rig.follower.read_positions(exclude=[3])
        time.sleep(1)
        positions_2 = hw_rig.follower.read_positions(exclude=[3])
        # At least some joints should have different positions (leader is being moved)
        assert positions_1 != positions_2, "All other joints frozen"

    def test_cascading_servo_failures(self, hw_rig):
        """Fail servos one by one. Verify armOS degrades gracefully
        and eventually halts when too many servos are offline."""
        injector = FaultInjector(hw_rig.follower.protocol)
        hw_rig.follower.protocol = injector

        teleop = hw_rig.start_teleop_async()
        time.sleep(3)

        for servo_id in [1, 2, 3, 4, 5, 6]:
            injector.fail_servo(servo_id=servo_id, mode="silent")
            time.sleep(2)
            alerts = teleop.get_alerts()
            # Should see incremental alerts
            assert any(f"servo {servo_id}" in a.message.lower() for a in alerts)

        # With all servos failed, teleop should have stopped
        assert teleop.state == "halted"
        assert "all servos" in teleop.halt_reason.lower() or "arm offline" in teleop.halt_reason.lower()
```

### 4.4 Network Partition Chaos (Cloud Upload)

For Growth phase cloud training integration. Simulate network failures during dataset upload.

```python
# tests/chaos/test_network_chaos.py
# Uses toxiproxy (https://github.com/Shopify/toxiproxy) for network fault injection

class TestNetworkChaos:

    def test_upload_survives_network_partition(self, upload_client, toxiproxy):
        """Cut network at 50% upload progress. Verify resume on reconnect."""
        dataset = create_test_dataset(size_mb=100)

        # Start upload
        upload = upload_client.upload_async(dataset)

        # Wait for 50% progress
        upload.wait_for_progress(0.5)

        # Cut network
        toxiproxy.add_toxic("upload_proxy", type="timeout", attributes={"timeout": 0})
        time.sleep(5)

        # Verify upload is paused, not failed
        assert upload.state == "paused" or upload.state == "retrying"

        # Restore network
        toxiproxy.remove_toxic("upload_proxy", "timeout")

        # Wait for completion
        upload.wait_for_completion(timeout=120)
        assert upload.state == "completed"
        assert upload.bytes_reuploaded < upload.total_bytes * 0.1  # Less than 10% re-upload
```

### 4.5 Chaos Test Schedule

| Test Category | Trigger | Frequency | Hardware Required |
|---------------|---------|-----------|-------------------|
| USB disconnect (basic) | Merge to main | Every merge | Yepkit YKUSH |
| USB disconnect (random, extended) | Schedule | Nightly | Yepkit YKUSH |
| Voltage sag | Schedule | Weekly | Programmable PSU |
| Individual servo failure | Merge to main | Every merge | FaultInjector (software only) |
| Cascading failure | Schedule | Nightly | FaultInjector (software only) |
| Network partition | Schedule | Nightly (Growth phase) | toxiproxy |

---

## 5. Visual Regression Testing

### The Problem

The TUI (Textual-based) is the primary user interface. A CSS change, a widget refactor, or a Textual version bump could break the layout in ways that unit tests cannot detect. The QA review (C8) identified that no TUI story tests screen size behavior or layout correctness.

### 5.1 Textual Snapshot Testing

Textual has built-in snapshot testing via `textual.testing`. It renders the app to a virtual terminal and compares the output character-by-character against a saved snapshot.

```python
# tests/visual/test_tui_snapshots.py

from textual.testing import ScreenshotFixture
import pytest


class TestTUISnapshots:
    """Visual regression tests for armOS TUI screens.
    Uses Textual's built-in snapshot testing."""

    @pytest.fixture
    def app(self):
        from armos.ui.tui import ArmOSApp
        return ArmOSApp(mock_hardware=True)

    async def test_dashboard_initial(self, snap_compare, app):
        """Main dashboard on first launch with hardware detected."""
        assert snap_compare(app, terminal_size=(120, 40))

    async def test_dashboard_80x24(self, snap_compare, app):
        """Dashboard at minimum terminal size (80x24)."""
        assert snap_compare(app, terminal_size=(80, 24))

    async def test_dashboard_wide(self, snap_compare, app):
        """Dashboard on a wide terminal (200x50, projector mode)."""
        assert snap_compare(app, terminal_size=(200, 50))

    async def test_teleop_active(self, snap_compare, app):
        """Teleop screen with live position data."""
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("t")  # Launch teleop
            await pilot.pause()
            assert snap_compare(app)

    async def test_diagnostics_all_pass(self, snap_compare, app):
        """Diagnostics screen with all checks passing."""
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("d")  # Launch diagnostics
            await pilot.pause()
            assert snap_compare(app)

    async def test_diagnostics_with_failures(self, snap_compare, app):
        """Diagnostics screen with some checks failing (red/yellow indicators)."""
        app.mock_hardware.inject_voltage_sag(servo_id=1, voltage=6.0)
        app.mock_hardware.inject_overheat(servo_id=3, temp=68)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("d")
            await pilot.pause()
            assert snap_compare(app)

    async def test_calibration_wizard(self, snap_compare, app):
        """Calibration wizard first step."""
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("c")  # Launch calibration
            await pilot.pause()
            assert snap_compare(app)

    async def test_error_no_hardware(self, snap_compare):
        """TUI launched with no hardware connected."""
        app = ArmOSApp(mock_hardware=False, detect_hardware=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert snap_compare(app)
```

**Updating snapshots:** When a visual change is intentional, run `pytest tests/visual/ --snapshot-update` to regenerate the golden files. The snapshot diffs are committed alongside the code change for review.

### 5.2 Screenshot Comparison for Non-Textual Screens

For the boot splash and GRUB menu, Textual snapshot testing does not apply. Use QEMU's screendump capability.

```bash
#!/bin/bash
# tools/test-boot-visual.sh
# Capture GRUB menu and boot splash screenshots from QEMU

ISO=$1
SNAPSHOT_DIR="tests/visual/boot_snapshots"

# Start QEMU with VNC and monitor socket
qemu-system-x86_64 \
    -bios /usr/share/OVMF/OVMF_CODE.fd \
    -cdrom "$ISO" \
    -m 4096 \
    -display vnc=:99 \
    -monitor unix:/tmp/qemu-monitor.sock,server,nowait \
    -no-reboot &

QEMU_PID=$!

# Wait for GRUB menu (5 seconds after start)
sleep 5
echo "screendump ${SNAPSHOT_DIR}/grub_menu_actual.ppm" | socat - UNIX:/tmp/qemu-monitor.sock

# Wait for boot splash (30 seconds)
sleep 25
echo "screendump ${SNAPSHOT_DIR}/boot_splash_actual.ppm" | socat - UNIX:/tmp/qemu-monitor.sock

# Wait for login prompt (60 more seconds)
sleep 60
echo "screendump ${SNAPSHOT_DIR}/login_screen_actual.ppm" | socat - UNIX:/tmp/qemu-monitor.sock

kill $QEMU_PID

# Compare against golden snapshots using ImageMagick
for screen in grub_menu boot_splash login_screen; do
    compare -metric RMSE \
        "${SNAPSHOT_DIR}/${screen}_expected.ppm" \
        "${SNAPSHOT_DIR}/${screen}_actual.ppm" \
        "${SNAPSHOT_DIR}/${screen}_diff.ppm" 2>&1 | {
        read rmse
        # Allow small differences (font rendering, timing)
        python3 -c "
rmse = float('${rmse}'.split()[0])
assert rmse < 500, f'Visual regression in ${screen}: RMSE={rmse} (threshold 500)'
print(f'${screen}: RMSE={rmse} -- PASS')
"
    }
done
```

### 5.3 Sprint Allocation

| Task | Sprint | Size |
|------|--------|------|
| Textual snapshot testing infrastructure | 6a | S |
| Dashboard snapshots (all states) | 6a | M |
| Teleop/diagnostics/calibration snapshots | 6b | M |
| QEMU boot screenshot comparison | 7 | M |
| CI integration for visual tests | 7 | S |

---

## 6. Performance Benchmarking

### The Problem

NFR1 (20ms teleop latency) is the headline performance requirement. But latency can regress silently: a new telemetry feature adds 2ms, a profile validation adds 1ms, a logging statement adds 0.5ms. Without automated benchmarking, death by a thousand cuts is inevitable.

### 6.1 Continuous Latency Benchmarking

```python
# tests/perf/test_teleop_latency.py

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

class TestTeleopLatency:
    """Automated latency measurement for the teleop control loop.
    Runs against SimFeetechProtocol (no hardware required)."""

    def test_single_cycle_latency(self, benchmark, sim_protocol):
        """Measure one sync_read + sync_write cycle."""
        servo_ids = [1, 2, 3, 4, 5, 6]
        goal_positions = [2048] * 6

        def one_cycle():
            positions = sim_protocol.sync_read(servo_ids, 0x38, 2)
            data = [p.to_bytes(2, 'little') for p in goal_positions]
            sim_protocol.sync_write(servo_ids, 0x2A, data)

        result = benchmark.pedantic(one_cycle, iterations=1000, rounds=10)
        # Benchmark stores stats; CI comparison handles regression detection

    def test_full_loop_with_telemetry(self, benchmark, sim_protocol, mock_telemetry):
        """Measure complete teleop loop: read leader + write follower + telemetry update."""

        def full_loop():
            # Read leader positions
            leader_pos = sim_protocol.sync_read([1,2,3,4,5,6], 0x38, 2)
            # Write to follower
            sim_protocol.sync_write([1,2,3,4,5,6], 0x2A, leader_pos)
            # Update telemetry (non-blocking)
            mock_telemetry.update()

        result = benchmark.pedantic(full_loop, iterations=1000, rounds=10)

    def test_latency_percentiles_60s(self, sim_protocol):
        """Run teleop for 60 seconds, measure latency distribution."""
        latencies = []
        start = time.monotonic()
        while time.monotonic() - start < 60:
            t0 = time.perf_counter_ns()
            # Full teleop cycle
            leader = sim_protocol.sync_read([1,2,3,4,5,6], 0x38, 2)
            sim_protocol.sync_write([1,2,3,4,5,6], 0x2A, leader)
            t1 = time.perf_counter_ns()
            latencies.append((t1 - t0) / 1_000_000)  # ns to ms
            time.sleep(0.01)  # ~100Hz target loop rate

        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)

        assert p95 < 20.0, f"p95 latency {p95:.1f}ms exceeds 20ms limit"
        print(f"Latency: p50={p50:.1f}ms, p95={p95:.1f}ms, p99={p99:.1f}ms")
```

### 6.2 Memory Profiling

```python
# tests/perf/test_memory.py

import tracemalloc
import pytest

class TestMemoryStability:
    """Verify no memory leaks during extended operation."""

    def test_teleop_1_hour_memory(self, sim_protocol):
        """Run simulated teleop for 1 hour. Memory growth must be < 50MB."""
        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        # Run teleop loop for 1 hour (accelerated: 10,000 cycles = ~100 seconds at 100Hz)
        for _ in range(10_000):
            leader = sim_protocol.sync_read([1,2,3,4,5,6], 0x38, 2)
            sim_protocol.sync_write([1,2,3,4,5,6], 0x2A, leader)

        snapshot_end = tracemalloc.take_snapshot()
        stats = snapshot_end.compare_to(snapshot_start, 'lineno')

        total_growth = sum(stat.size_diff for stat in stats if stat.size_diff > 0)
        assert total_growth < 50 * 1024 * 1024, \
            f"Memory grew {total_growth / 1024 / 1024:.1f}MB (limit 50MB)"

        # Report top 10 memory consumers
        for stat in stats[:10]:
            print(stat)

    def test_telemetry_stream_memory(self, sim_protocol):
        """Stream telemetry at 10Hz for 10,000 cycles. No unbounded growth."""
        tracemalloc.start()

        telemetry_stream = TelemetryStream(sim_protocol, poll_hz=10)
        telemetry_stream.start()

        for _ in range(10_000):
            data = telemetry_stream.get_latest()
            time.sleep(0.001)  # Simulate consumer

        telemetry_stream.stop()
        snapshot = tracemalloc.take_snapshot()

        # Check for common leak patterns
        for stat in snapshot.statistics('traceback')[:5]:
            # Telemetry buffers should be bounded (ring buffer)
            assert stat.size < 10 * 1024 * 1024, \
                f"Possible leak: {stat.size / 1024 / 1024:.1f}MB at {stat.traceback}"
```

### 6.3 CPU Usage Tracking

```python
# tests/perf/test_cpu.py

import psutil
import os

class TestCPUUsage:
    """Verify CPU usage stays within bounds during normal operation."""

    def test_teleop_cpu_usage(self, sim_protocol):
        """Teleop loop must not exceed 30% CPU on a single core."""
        process = psutil.Process(os.getpid())

        # Warm up
        for _ in range(100):
            sim_protocol.sync_read([1,2,3,4,5,6], 0x38, 2)
            sim_protocol.sync_write([1,2,3,4,5,6], 0x2A, [b'\x00\x08'] * 6)

        # Measure
        cpu_samples = []
        for _ in range(60):  # 60 one-second samples
            cpu = process.cpu_percent(interval=1.0)
            cpu_samples.append(cpu)

        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)

        assert avg_cpu < 30, f"Average CPU {avg_cpu:.1f}% exceeds 30% limit"
        assert max_cpu < 60, f"Peak CPU {max_cpu:.1f}% exceeds 60% limit"

    def test_idle_cpu_usage(self, sim_protocol):
        """When TUI is running but no teleop, CPU should be < 5%."""
        process = psutil.Process(os.getpid())
        # Simulate idle TUI (just telemetry polling at 10Hz)
        cpu_samples = []
        for _ in range(10):
            sim_protocol.sync_read([1,2,3,4,5,6], 0x38, 2)
            cpu = process.cpu_percent(interval=1.0)
            cpu_samples.append(cpu)

        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        assert avg_cpu < 5, f"Idle CPU {avg_cpu:.1f}% exceeds 5% limit"
```

### 6.4 Automated Regression Detection

```yaml
# .github/workflows/perf-regression.yml
name: Performance Regression Check
on: [push, pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install armos[dev] pytest-benchmark
      - name: Run benchmarks
        run: pytest tests/perf/ --benchmark-only --benchmark-json=benchmark.json
      - name: Compare against baseline
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark.json
          alert-threshold: '120%'        # Fail if 20% slower
          comment-on-alert: true          # Comment on PR
          fail-on-alert: true
          github-token: ${{ secrets.GITHUB_TOKEN }}
          auto-push: true                 # Update baseline on main
          benchmark-data-dir-path: benchmarks/
```

### 6.5 Sprint Allocation

| Task | Sprint | Size |
|------|--------|------|
| pytest-benchmark setup and first benchmarks | 2 | S |
| Teleop latency benchmark (sim) | 5 | M |
| Memory profiling tests | 5 | S |
| CPU usage tests | 5 | S |
| Automated regression detection in CI | 5 | S |
| 1-hour stability benchmark (nightly) | 6 | M |

---

## 7. User Testing at Scale

### The Problem

SC1 (5 minutes boot to teleop) is the headline success metric. But we have never measured it with real users. The QA review (C7) flags that first-time calibration alone might exceed 5 minutes. We need data, not assumptions.

### 7.1 Remote Usability Testing Protocol

Ship USB sticks to 10 testers. Collect screen recordings and timing data.

#### Recruitment

- **Source:** LeRobot Discord, r/robotics, HuggingFace community
- **Criteria:** Must own or have access to an SO-101 kit. Mix of experience levels (3 beginners, 4 intermediate, 3 advanced).
- **Incentive:** Free armOS USB stick (they keep it) + name in contributors list

#### Test Kit (Shipped to Each Tester)

1. Pre-flashed USB stick with armOS
2. Printed quick-start card (4x6 postcard, front and back)
3. Consent form for screen recording and telemetry
4. Prepaid return envelope (for the USB stick, if they want to send it back)

#### Instrumentation: Automatic Timing

```python
# armos/telemetry/ux_timing.py

"""
Automatically measure "time to first teleop" without user action.
Records timestamps for key milestones and writes a UX timing report.
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


@dataclass
class UXTimingReport:
    session_id: str
    boot_complete: datetime | None = None        # systemd reports multi-user.target
    tui_launched: datetime | None = None          # ArmOSApp.__init__() called
    hardware_detected: datetime | None = None     # First successful armos detect
    calibration_started: datetime | None = None   # User enters calibration wizard
    calibration_completed: datetime | None = None # Calibration saved
    teleop_started: datetime | None = None        # First teleop cycle
    first_movement: datetime | None = None        # First position delta > 100 ticks
    milestones: list[tuple[str, datetime]] = field(default_factory=list)

    @property
    def boot_to_teleop_seconds(self) -> float | None:
        if self.boot_complete and self.teleop_started:
            return (self.teleop_started - self.boot_complete).total_seconds()
        return None

    @property
    def boot_to_first_movement_seconds(self) -> float | None:
        if self.boot_complete and self.first_movement:
            return (self.first_movement - self.boot_complete).total_seconds()
        return None

    def save(self, path: Path) -> None:
        data = {
            "session_id": self.session_id,
            "boot_to_teleop_s": self.boot_to_teleop_seconds,
            "boot_to_first_movement_s": self.boot_to_first_movement_seconds,
            "milestones": [
                {"name": name, "timestamp": ts.isoformat()}
                for name, ts in self.milestones
            ],
        }
        path.write_text(json.dumps(data, indent=2))
```

#### Data Collection

Each tester's armOS USB automatically records:
- UX timing report (boot-to-teleop, per-milestone timestamps)
- Screen recording via `asciinema` (terminal recording, lightweight, no video encoding)
- System logs (`dmesg`, `journalctl` for hardware detection timing)
- Telemetry opt-in data (if consented): hardware model, boot time, error counts

#### Analysis

```python
# tools/analyze_usability.py

def analyze_tester_data(reports: list[UXTimingReport]) -> UsabilityReport:
    boot_to_teleop = [r.boot_to_teleop_seconds for r in reports if r.boot_to_teleop_seconds]

    return UsabilityReport(
        n_testers=len(reports),
        n_successful=len(boot_to_teleop),
        median_boot_to_teleop=np.median(boot_to_teleop),
        p90_boot_to_teleop=np.percentile(boot_to_teleop, 90),
        fastest=min(boot_to_teleop),
        slowest=max(boot_to_teleop),
        meets_sc1=(np.percentile(boot_to_teleop, 90) < 300),  # 5 minutes
        bottleneck=identify_bottleneck(reports),  # Which milestone takes longest?
    )
```

### 7.2 A/B Testing First-Run Flows

Once the telemetry infrastructure exists (Sprint 11), A/B test different onboarding approaches:

| Variant | Description | Hypothesis |
|---------|-------------|------------|
| A: Guided wizard | Step-by-step wizard with explanations at each step | Slower but fewer errors |
| B: Auto-everything | Detect, load default calibration, auto-start teleop | Faster for experienced users, confusing for beginners |
| C: Video-guided | Embedded ASCII-art diagrams showing what to do physically | Best for first-time robot builders |

**Implementation:** First-run variant is assigned by `hash(usb_serial_number) % 3`. The variant is recorded in the UX timing report. After 100+ sessions, compare boot-to-teleop times across variants.

### 7.3 Telemetry-Driven UX Optimization

With user consent, collect aggregate data to find UX friction:

| Metric | What It Reveals |
|--------|----------------|
| Time in calibration wizard | Is calibration the bottleneck? |
| Calibration retry count | Are users struggling with the homing procedure? |
| Error message frequency | Which errors do users hit most? |
| Feature discovery rate | Do users find the diagnostic tool? The monitor? |
| Session duration | Are sessions getting longer (engagement) or shorter (frustration)? |
| Drop-off point | Where do users quit? After boot? After calibration? |

### 7.4 Sprint Allocation

| Task | Sprint | Size |
|------|--------|------|
| UX timing instrumentation | 6a | S |
| asciinema integration for session recording | 6a | S |
| Usability test protocol document | 7 | S |
| Ship USB sticks to 10 testers | 8 (launch prep) | -- |
| Analyze results and iterate | 9 (post-launch) | M |
| A/B testing infrastructure | 11 (telemetry sprint) | L |

---

## 8. Implementation Priority Matrix

All frontier testing initiatives ranked by impact and feasibility.

| Initiative | Impact | Feasibility | Sprint Start | Estimated Total Cost |
|-----------|--------|-------------|--------------|---------------------|
| **MuJoCo digital twin** | Very High | Medium | Sprint 2 | $0 (open source) |
| **Hypothesis property tests** | High | High | Sprint 2 | $0 |
| **Performance benchmarking in CI** | High | High | Sprint 2 | $0 |
| **Serial protocol fuzzing** | High | High | Sprint 3 | $0 |
| **Textual snapshot testing** | Medium | High | Sprint 6a | $0 |
| **Hardware-in-the-loop CI** | Very High | Medium | Sprint 5 | $50-450 (YKUSH + optional NUC) |
| **Mutation testing** | Medium | High | Sprint 4 | $0 |
| **USB disconnect chaos** | Very High | Medium | Sprint 6 | $50 (YKUSH) |
| **Voltage chaos testing** | High | Low | Sprint 7+ | $40-200 (PSU) |
| **UX timing instrumentation** | High | High | Sprint 6a | $0 |
| **Remote usability testing** | Very High | Medium | Sprint 8 | $100-200 (shipping) |
| **AI test generation** | Medium | Medium | Sprint 5 | $0-20/month (API) |
| **Boot visual regression** | Low | Medium | Sprint 7 | $0 |
| **A/B testing** | Medium | Low | Sprint 11 | $0 |
| **Network chaos (toxiproxy)** | Medium | Medium | Growth phase | $0 |

---

## 9. Tool Summary

| Tool | Purpose | License | Install |
|------|---------|---------|---------|
| MuJoCo 3.x | Physics simulation for digital twin | Apache 2.0 | `pip install mujoco` |
| Hypothesis | Property-based and stateful testing | MPL 2.0 | `pip install hypothesis` |
| mutmut | Mutation testing | BSD | `pip install mutmut` |
| pytest-benchmark | Continuous performance benchmarking | BSD | `pip install pytest-benchmark` |
| github-action-benchmark | PR-level perf regression detection | MIT | GitHub Action |
| tracemalloc | Memory leak detection | stdlib | Built into Python 3.12 |
| psutil | CPU/memory monitoring | BSD | `pip install psutil` |
| Textual pilot | TUI snapshot testing | MIT | Built into Textual |
| ImageMagick | Boot screen visual comparison | Apache 2.0 | `apt install imagemagick` |
| Yepkit YKUSH | Programmable USB disconnect | N/A | Hardware ($50) |
| ykushcmd | YKUSH CLI control | GPL | `apt install ykushcmd` |
| toxiproxy | Network fault injection | MIT | Binary download |
| asciinema | Terminal session recording | GPL 3.0 | `apt install asciinema` |
| QEMU + OVMF | ISO boot testing and screenshot capture | GPL | `apt install qemu-system-x86 ovmf` |
| socat | QEMU monitor communication | GPL | `apt install socat` |

---

## 10. Success Criteria for This Document

This frontier testing strategy succeeds when:

1. **Every PR runs against a simulated SO-101** -- physics-aware tests catch bugs that mocks miss
2. **Latency regression is caught before merge** -- no PR lands that makes teleop slower
3. **Nightly hardware tests run unattended** -- real servo communication is tested every 24 hours
4. **Chaos tests prove resilience** -- USB disconnect, voltage sag, and servo failure are tested automatically
5. **We know the real boot-to-teleop time** -- measured from 10+ real users, not guessed
6. **Mutation score exceeds 85%** -- our tests actually catch bugs, not just run code
7. **Visual regressions are caught in CI** -- TUI changes are reviewed as screenshots, not just code

---

*Frontier testing strategy for armOS USB -- generated by Quinn (QA Engineer).*
