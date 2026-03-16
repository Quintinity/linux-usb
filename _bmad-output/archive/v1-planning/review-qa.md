# QA Review: RobotOS USB Planning Artifacts

**Reviewer:** Quinn (QA Engineer)
**Date:** 2026-03-15
**Scope:** Product brief, PRD, Architecture, Epics, Sprint plan
**Status:** Review complete -- action required before Sprint 1

---

## 1. Executive Summary

The planning artifacts are thorough and well-structured. Requirements are traceable from product brief through epics to sprint plan. However, there are significant gaps in testability, test infrastructure planning, and edge case coverage that must be addressed before implementation begins. The most critical issue is that **no test strategy, test infrastructure, or CI/CD pipeline is planned in any sprint**, yet the project depends on hardware abstraction correctness and real-time performance guarantees.

### Severity Summary

| Severity | Count | Description |
|----------|-------|-------------|
| BLOCKER | 3 | Must resolve before Sprint 1 starts |
| CRITICAL | 8 | Must resolve before the affected sprint starts |
| MAJOR | 11 | Should resolve within the sprint that touches the area |
| MINOR | 6 | Nice to have, can be backlogged |

---

## 2. Blocker Issues

### B1: No test infrastructure story in any sprint

**Problem:** There is no story for setting up pytest, test fixtures, mock hardware, or CI/CD. Story 1.1 creates pyproject.toml but does not mention test dependencies, test configuration, or a test runner. Every subsequent sprint produces untested code.

**Recommendation:** Add a Story 1.0 (or expand 1.1) in Sprint 1:
- pytest + pytest-cov + pytest-asyncio in dev dependencies
- `tests/` directory structure mirroring `robotos/`
- A `MockServoProtocol` implementing the ABC with in-memory state
- A `MockSerialPort` that simulates serial communication (configurable error rate)
- GitHub Actions CI workflow running tests on every push
- Minimum 80% line coverage gate for HAL and diagnostics modules

**Affected sprints:** All.

### B2: No definition of "tested" in any acceptance criteria

**Problem:** Acceptance criteria describe functional behavior ("when I call X, then Y") but none specify that automated tests must exist. A developer could satisfy every AC by manual testing, leaving zero regression safety.

**Recommendation:** Add to the project Definition of Done:
- Every story must ship with unit tests covering its acceptance criteria
- HAL plugin stories (2.1-2.4) must include integration tests runnable against mock hardware
- CLI command stories must include CLI integration tests using click.testing.CliRunner

### B3: Story 8.4 (Hardware Compatibility Testing) has no test protocol

**Problem:** The AC says "tested on 5+ hardware models" but does not define what "tested" means. Boot success? TUI launches? Teleop works? Servo communication succeeds? Without a defined protocol, this story is unverifiable.

**Recommendation:** Define a hardware compatibility test protocol:
1. USB boot to desktop within 90 seconds
2. `robotos --version` prints 0.1.0
3. `robotos detect` finds USB serial and camera (if connected)
4. `robotos tui` launches without error
5. Wi-Fi and keyboard functional (if applicable)
6. Log `systemd-analyze blame` and `dmesg` errors
7. Document results in a compatibility matrix with PASS/PARTIAL/FAIL per check

---

## 3. Critical Issues

### C1: NFR1 (20ms teleop latency) has no test plan

**Problem:** The PRD states "95th percentile latency shall not exceed 20ms, as measured by internal timing instrumentation." The architecture mentions a "latency histogram in the teleop controller" (Section 10.6). But no story includes building this instrumentation, and no acceptance criteria in Story 6.2 reference latency measurement.

**Recommendation:**
- Add to Story 6.2 AC: "The teleop loop records per-cycle timing. After a 60-second session, the p95 latency is reported in the session summary and must be under 20ms on reference hardware (Surface Pro 7)."
- Create a `robotos teleop --benchmark` mode that runs a fixed-duration session with synthetic (loopback) positions and reports latency percentiles.
- Add a latency regression test to CI using `MockServoProtocol` (verifying the control loop overhead, excluding real serial I/O).

### C2: NFR6 (retry on transient failure) is not testable without fault injection

**Problem:** Story 2.4 describes retry with port flush, but the only way to test it is to cause real communication failures. There is no fault injection mechanism in the mock or real system.

**Recommendation:**
- `MockServoProtocol` must support configurable failure modes: drop N% of reads, return corrupted data, simulate timeout, simulate bus disconnect.
- Add a `FaultInjector` wrapper class that wraps any `ServoProtocol` and injects failures according to a schedule. This enables both automated testing and manual chaos testing.
- Story 2.4 AC should include: "Given a MockServoProtocol configured to fail 10% of reads, when teleop runs for 1000 cycles, then all failures are retried and the session completes without interruption."

### C3: NFR7 (bus disconnection detection within 2 seconds) is not testable in CI

**Problem:** Story 5.3 specifies detecting bus disconnection within 2 seconds. This requires physically unplugging a USB cable. No automated or simulated test is described.

**Recommendation:**
- Define a `MockServoProtocol.simulate_disconnect()` method that causes all subsequent reads to raise `CommunicationError`.
- Add a timed integration test: call `simulate_disconnect()`, assert that the fault detection system fires an alert within 2 seconds.
- For hardware-in-the-loop testing, document a manual test procedure using a USB hub with switchable ports (e.g., Yepkit YKUSH).

### C4: Story 8.2 AC has a security contradiction with NFR21

**Problem:** Story 8.2 says the CH340 adapter should appear with "mode 0666 (no root required)." NFR21 says "MODE=0660, GROUP=robotos. No world-writable serial device nodes." These directly contradict each other.

**Recommendation:** Story 8.2 AC must be corrected to MODE=0660, GROUP=robotos. The architecture's udev rules (Section 4) already specify 0660. The 0666 in Story 8.2 appears to be carried over from the current CLAUDE.md setup (which uses 0666 for expedience).

### C5: No regression test plan for adding new servo protocols

**Problem:** The plugin architecture (Story 10.2) allows adding new ServoProtocol implementations. But there is no protocol conformance test suite that validates a plugin correctly implements the ABC contract. A new plugin could pass `isinstance` checks but have subtly wrong behavior.

**Recommendation:** Create a `ServoProtocolConformanceTests` base class that any plugin can inherit from to run a standard battery of tests:
- connect/disconnect lifecycle
- ping returns True for valid IDs, False for invalid
- sync_read/sync_write round-trip consistency
- get_telemetry returns valid ranges
- retry behavior on injected failures
- flush_port clears buffer state

This should be built in Sprint 2 alongside Story 2.1.

### C6: No test for calibration data integrity across reboots

**Problem:** Story 3.3 requires calibration to persist across reboots, and Story 8.2 requires persistence on the USB drive. But no test verifies that the persistent partition survives unclean shutdown (NFR9). An ext4 journal corruption could silently lose calibration.

**Recommendation:**
- Add an automated test that writes calibration data, simulates power loss (kill -9 the process mid-write), and verifies data integrity on re-read.
- For USB persistence testing, define a manual test: boot from USB, calibrate, hard power-off (hold power button), reboot, verify calibration loads.

### C7: No test for the "5 minutes boot to teleop" success metric (SC1)

**Problem:** SC1 is the headline success metric but no story includes a test for it. The 5-minute budget must account for: boot time (90s per NFR5) + hardware detection (5s per NFR3) + calibration (user-dependent) + teleop launch. First-time calibration alone could exceed 5 minutes.

**Recommendation:**
- Clarify SC1: is it 5 minutes *including* first-time calibration, or 5 minutes *with pre-existing calibration*? The user journey (UJ1) includes calibration, which suggests it is included. This may be unrealistic for a first-time user unfamiliar with robot arm homing.
- Add a timed usability test protocol: give a naive user a USB stick, SO-101, and a printed quick-start card. Time them from USB insertion to first successful leader-follower movement. Run with 3+ participants.
- If first-time calibration is included, consider shipping a "default calibration" in the SO-101 profile that works for most assembled kits, allowing users to skip calibration initially.

### C8: TUI stories (7.1-7.3) have no accessibility or error-state testing

**Problem:** NFR13 says the dashboard must be operable via keyboard, mouse, or touchscreen. No TUI story tests keyboard-only navigation, screen reader compatibility, or behavior when the terminal is too small.

**Recommendation:**
- Add AC to Story 7.1: "Given a terminal with 80x24 dimensions, when the TUI launches, then all panels are visible without horizontal scrolling."
- Add AC to Story 7.3: "Given keyboard-only input, when the user presses D, T, C, R, M, Q, then the corresponding workflow launches or quits."
- Test TUI behavior when hardware disconnects mid-workflow (e.g., USB cable pulled during teleop displayed in TUI).

---

## 4. Major Issues

### M1: Diagnostic tool testing (self-referential problem)

**Problem:** The diagnostic suite (Epic 4) tests hardware health. But what tests the diagnostic suite itself? If `PowerHealth` has a bug in its voltage threshold comparison, it could report PASS when the servo is actually failing. No story addresses testing the diagnostic checks.

**Recommendation:** Each diagnostic check should have unit tests with known-good and known-bad mock telemetry data:
- `PowerHealth` test: mock a servo returning 6.5V, assert FAIL. Mock 7.5V, assert PASS. Mock 6.9V, assert WARN.
- `CommsReliability` test: mock 199/200 successful reads, assert PASS. Mock 195/200, assert WARN. Mock 180/200, assert FAIL.
- `EEPROMConfig` test: mock register values mismatching profile, assert FAIL.

### M2: Story 2.2 (Bus Scan) does not cover edge cases

**Problem:** The AC covers the happy path (6 servos found) and one error case (servo not responding). Missing cases:
- Two servos with the same ID (wiring error)
- Servo responds to ping but fails on register read
- Baudrate mismatch (servo configured to different baud)
- Scan range does not cover the actual servo IDs (e.g., servos at IDs 7-12)

**Recommendation:** Add edge case ACs or document them as known limitations for MVP.

### M3: Story 3.1 profile validation does not cover all error modes

**Problem:** AC covers "missing required field." Other failure modes not tested:
- Invalid YAML syntax (tabs instead of spaces)
- Valid YAML but invalid values (servo_id: -1, overload_torque: 999)
- Profile references a servo protocol that is not installed
- Two joints in the same arm with the same servo_id
- Mismatched arm role (role: "actuator" on both arms)

**Recommendation:** Add Pydantic validation tests for each of these cases. The profile schema should be the first line of defense against configuration errors.

### M4: LeRobot bridge (Story 9.2) has no version compatibility test

**Problem:** The bridge translates RobotOS profiles to LeRobot config objects. LeRobot v0.5.0 is pinned, but the bridge's AC does not verify that the generated config actually works with LeRobot's internals. If LeRobot changes its config schema in a patch release, the bridge silently breaks.

**Recommendation:**
- Add an integration test that calls `LeRobotBridge.build_config()` and then passes the result to LeRobot's config validation.
- Pin LeRobot to an exact version (0.5.0, not >=0.5.0) in pyproject.toml. The current spec says `"lerobot>=0.5.0"` which allows untested upgrades.

### M5: Data collection (Story 9.3) episode boundary is ambiguous

**Problem:** The AC says "user presses Enter to advance" between episodes. But what happens if:
- User presses Enter immediately (zero-length episode)?
- User presses Ctrl+C during an episode (partial episode)?
- Disk is full during write?
- Camera frame drops during recording?

**Recommendation:** Add ACs for these edge cases. Especially important: "Given disk space is insufficient, when the system attempts to save an episode, then it alerts the user and does not corrupt existing episodes."

### M6: No load testing or stress testing plan for telemetry streaming

**Problem:** Story 5.1 specifies 10 Hz polling of all servos. With 12 servos across 2 arms, that is 120 telemetry reads per second plus serialization and backend dispatch. No test verifies this does not cause CPU saturation, memory growth, or serial bus contention with the teleop loop.

**Recommendation:**
- Add a benchmark test: run TelemetryStream at 10 Hz with MockServoProtocol for 60 seconds, assert CPU usage under 30%, memory growth under 10MB, no dropped samples.
- Test concurrent telemetry + teleop: verify that telemetry polling does not increase teleop loop latency beyond 20ms (NFR1).

### M7: Story 4.2 (XL) has no decomposition strategy for testing

**Problem:** Story 4.2 migrates 11 diagnostic checks. The sprint plan acknowledges it is the "biggest schedule risk." But there is no guidance on how to test each check independently during migration, or how to verify parity with the existing `diagnose_arms.py` output.

**Recommendation:**
- Run the existing `diagnose_arms.py` against real hardware and capture a "golden output" file.
- After migration, run `robotos diagnose --json` and compare results to the golden output.
- Each check should be independently testable with `robotos diagnose --check <name>`.

### M8: ISO build (Story 8.1) has no automated validation

**Problem:** The AC for 8.1 says "the ISO boots to a desktop on a x86 UEFI system within 90 seconds." This is only testable manually. With a 30-60 minute build time, manual testing creates a long and painful feedback loop.

**Recommendation:**
- Use QEMU/KVM to boot the ISO in a VM as part of CI. While this does not test real hardware, it validates:
  - ISO is bootable (UEFI boot via OVMF firmware)
  - System reaches login prompt
  - `robotos --version` works inside the VM
  - SO-101 profile is available
- Add a `test-iso.sh` script that automates this VM-based smoke test.

### M9: No test for concurrent serial port access

**Problem:** The architecture (Section 10.6) describes threading: teleop on main thread, telemetry on daemon thread, both accessing the serial port through a Lock. No test verifies the lock prevents data corruption under concurrent access.

**Recommendation:** Add a threading stress test: spawn teleop + telemetry threads against MockServoProtocol with a simulated 1ms serial latency. Run for 10,000 cycles. Assert no data corruption, no deadlocks, and no reads returning stale data.

### M10: flash.ps1 (Story 8.3) has no Windows testing in CI

**Problem:** The flash script runs on Windows PowerShell. No CI environment for Windows testing is described. The project already has a lesson learned about flash.ps1 breaking (commit 5bd7c54: "fix: replace em dashes with ASCII dashes in flash.ps1").

**Recommendation:**
- Add a GitHub Actions Windows runner that validates flash.ps1 syntax (`powershell -Command "& { . ./flash.ps1 -WhatIf }"`)
- Test the script's drive detection and confirmation prompts with mock inputs.

### M11: No end-to-end test definition

**Problem:** The closest thing to an E2E test is Story 8.4 (hardware compatibility) but that tests only boot, not the full workflow. No test exercises the complete path: boot -> detect -> calibrate -> teleop -> record -> stop.

**Recommendation:** Define an E2E test script (`tests/e2e/full_workflow.sh`) that:
1. Runs `robotos detect` and verifies output
2. Runs `robotos calibrate --arm follower --non-interactive` (with pre-recorded inputs)
3. Runs `robotos teleop --duration 10` (10-second session)
4. Runs `robotos record --task test --episodes 1 --duration 5`
5. Runs `robotos diagnose` and verifies no FAILs
6. Verifies dataset file exists and is valid

This can run against mock hardware in CI and real hardware in manual testing.

---

## 5. Minor Issues

### m1: Story 1.3 AC uses a magic number without explanation

The AC says `decode_sign_magnitude(1033, 1024)` returns `0.88%`. The derivation of 0.88% from 1033 and 1024 is not obvious. Test data should include the formula or a comment explaining the expected output.

### m2: Story 6.1 does not specify what "safe speed" means for exercise

Story 4.4 says "moves each joint through its range at a safe speed." What is safe? This should reference a profile parameter (e.g., `exercise_velocity: 100` in the profile schema).

### m3: No test for YAML profile comments surviving round-trip

NFR17 says profiles are "human-readable YAML, editable with any text editor." If the system ever writes profiles (export, profile wizard), it must preserve comments. No AC tests this.

### m4: Story 9.1 (Claude Code context) is not testable by automation

The AC says "Claude Code reads the CLAUDE.md" and "memory files document known hardware issues." This is inherently a human judgment. Consider adding a machine-checkable criterion: "CLAUDE.md contains the string 'robotos diagnose' and 'robotos teleop'."

### m5: Sprint 4 overload risk is acknowledged but not mitigated by testing

Sprint 4 has weight 24 (heaviest after Sprint 6). If stories overflow, they carry untested code into Sprint 5. The overflow plan should specify that any overflowed stories must carry their test backlog with them.

### m6: No smoke test for the `robotos` CLI entry point across Python versions

The project pins Python 3.12+, but no test verifies that the package actually fails gracefully on Python 3.11. A user on Ubuntu 22.04 (ships Python 3.10) who tries `pip install robotos` should get a clear error, not a cryptic import failure.

---

## 6. Proposed Test Strategy

### 6.1 Test Pyramid

```
                    /\
                   /  \         E2E Tests (2-3)
                  / E2E\        Full workflow on real or VM hardware
                 /------\
                / Integ. \      Integration Tests (~30)
               / Tests    \     CLI commands, HAL + profile, TUI workflows
              /------------\
             / Unit Tests    \  Unit Tests (~200+)
            / (foundation)    \ Profile validation, serial helpers, diagnostic
           /-------------------\ checks, telemetry processing, fault detection
```

### 6.2 Test Categories

| Category | What it tests | Tools | Runs in CI | Estimated count |
|----------|--------------|-------|------------|-----------------|
| Unit | Pure functions, data transformations, validation | pytest, pytest-cov | Yes | 200+ |
| Mock Hardware | HAL plugins against MockServoProtocol | pytest, custom mocks | Yes | 50+ |
| CLI Integration | Click commands via CliRunner | pytest, click.testing | Yes | 30+ |
| TUI Integration | Textual app behavior | pytest, textual pilot testing | Yes | 15+ |
| Performance | Latency, throughput, resource usage | pytest-benchmark, custom timing | Yes (mocked) | 10+ |
| ISO Smoke | VM boot and basic commands | QEMU/KVM, expect scripts | Yes (nightly) | 5+ |
| Hardware-in-the-Loop | Real servo communication | Custom test harness | Manual / scheduled | 20+ |
| Usability | Timed user workflows | Human testers, stopwatch | Manual | 5+ |
| Security | Permissions, no open ports, no world-writable | pytest, nmap, stat checks | Yes | 10+ |

### 6.3 Mock Strategy for Hardware Abstraction

```python
class MockServoProtocol(ServoProtocol):
    """In-memory servo simulation for testing without hardware."""

    def __init__(self, servo_ids: list[int], fail_rate: float = 0.0):
        self._servos: dict[int, dict] = {
            sid: {"position": 2048, "voltage": 12.0, "temp": 25,
                  "load": 0.0, "torque_enabled": False}
            for sid in servo_ids
        }
        self._fail_rate = fail_rate  # 0.0 to 1.0
        self._connected = False
        self._call_log: list[tuple] = []  # For assertion

    def connect(self, port: str, baudrate: int = 1_000_000) -> None:
        self._connected = True
        self._call_log.append(("connect", port, baudrate))

    def ping(self, servo_id: int) -> bool:
        if random.random() < self._fail_rate:
            raise CommunicationError("Simulated failure")
        return servo_id in self._servos

    def simulate_disconnect(self) -> None:
        """Cause all subsequent operations to fail."""
        self._fail_rate = 1.0

    def simulate_voltage_sag(self, servo_id: int, voltage: float) -> None:
        """Set a servo's voltage to simulate power supply issues."""
        self._servos[servo_id]["voltage"] = voltage

    def simulate_overheat(self, servo_id: int, temp: int) -> None:
        """Set a servo's temperature to simulate overheating."""
        self._servos[servo_id]["temp"] = temp

    # ... all other abstract methods implemented with in-memory state
```

This mock must be built in Sprint 1 and used by every subsequent sprint.

### 6.4 ISO Testing via QEMU

```bash
#!/bin/bash
# test-iso.sh -- Smoke test a RobotOS ISO in a VM

ISO=$1
TIMEOUT=120

# Boot with UEFI firmware
qemu-system-x86_64 \
    -bios /usr/share/OVMF/OVMF_CODE.fd \
    -cdrom "$ISO" \
    -m 4096 \
    -nographic \
    -serial mon:stdio \
    -no-reboot &

QEMU_PID=$!

# Wait for login prompt, then run checks
expect <<'EXPECT'
    set timeout 120
    expect "login:"
    send "robotos\r"
    expect "\\$"
    send "robotos --version\r"
    expect "0.1.0"
    send "robotos profile list\r"
    expect "SO-101"
    send "exit\r"
EXPECT

kill $QEMU_PID
```

### 6.5 Performance Testing Plan

| NFR | Test method | Pass criteria | When to run |
|-----|-----------|---------------|-------------|
| NFR1 (20ms teleop) | `robotos teleop --benchmark --duration 60` | p95 < 20ms | Every Sprint 5+ PR |
| NFR2 (3s bus scan) | Unit test with MockServoProtocol (12 servos, 1ms simulated latency) | < 3s wall clock | Every Sprint 2+ PR |
| NFR3 (5s auto-detect) | Integration test with mock pyudev events | < 5s from event to callback | Sprint 6+ |
| NFR4 (10 Hz dashboard) | Textual pilot test measuring frame updates over 10s | >= 95 frames in 10s | Sprint 6+ |
| NFR5 (90s boot) | QEMU boot test with timer | < 90s to login prompt | Nightly ISO build |

### 6.6 Reliability Testing Plan

| Scenario | Test method | Expected behavior |
|----------|-----------|-------------------|
| Single dropped packet | MockServoProtocol with 5% fail rate, 1000 cycles | All retried, zero user-visible errors |
| Bus disconnect | `simulate_disconnect()` during teleop | Alert within 2s, teleop halts gracefully |
| Power loss during calibration save | Kill process mid-write, re-read file | File is either complete or absent (atomic write) |
| Power loss during episode record | Kill process mid-write, re-read dataset | All previously completed episodes intact |
| Servo overheat during teleop | `simulate_overheat(servo_id=3, temp=65)` | Safety stop within 1 teleop cycle |
| Voltage sag under load | `simulate_voltage_sag(servo_id=1, voltage=6.5)` | WARN alert within 2s |
| Camera disconnect during recording | Mock camera returning empty frames | Episode marked with warning, recording continues |
| All servos on one arm fail | Fail rate 100% on follower bus | Teleop stops for that arm, alert displayed |

### 6.7 Security Testing Plan

| Check | Method | Pass criteria |
|-------|--------|---------------|
| No open ports | `ss -tlnp` on fresh boot | Zero LISTEN entries |
| Serial device permissions | `stat /dev/ttyUSB*` | MODE 0660, GROUP robotos |
| No world-writable files in /opt/robotos | `find /opt/robotos -perm -o+w` | Zero results |
| No secrets in ISO | Search ISO contents for API keys, passwords, tokens | Zero matches |
| Calibration files not world-readable | `stat ~/.config/robotos/calibration/*` | MODE 0640 or stricter |
| Web dashboard default bind | Start `robotos serve`, check `ss -tlnp` | Bound to 127.0.0.1 only |

---

## 7. Test Matrix

### 7.1 Hardware Compatibility Matrix (Story 8.4)

| Model | CPU | RAM | USB Ports | Boot | Detect | TUI | Teleop | Notes |
|-------|-----|-----|-----------|------|--------|-----|--------|-------|
| Surface Pro 7 | i5-1035G4 | 8GB | 1A+1C | | | | | Primary dev target |
| Dell XPS 13 | i7-1165G7 | 16GB | 2C | | | | | Popular ultrabook |
| Lenovo ThinkPad T480 | i5-8250U | 8GB | 2A+1C | | | | | Enterprise standard |
| HP EliteBook 840 | i5-8350U | 8GB | 2A+1C | | | | | Enterprise standard |
| Desktop (AMD) | Ryzen 5 3600 | 16GB | 6A+1C | | | | | AMD CPU test |
| Mini PC (Intel N100) | N100 | 8GB | 2A+1C | | | | | Low-end target |

### 7.2 Servo Protocol Test Matrix

| Test | Feetech STS3215 | Dynamixel XL330 (Growth) | Dynamixel XL430 (Growth) |
|------|-----------------|--------------------------|--------------------------|
| Ping | Sprint 2 | Growth | Growth |
| Sync read | Sprint 2 | Growth | Growth |
| Sync write | Sprint 2 | Growth | Growth |
| Telemetry read | Sprint 2 | Growth | Growth |
| Protection write | Sprint 2 | Growth | Growth |
| Bus scan | Sprint 2 | Growth | Growth |
| Retry on failure | Sprint 2 | Growth | Growth |
| 1-hour stability | Sprint 5 | Growth | Growth |

### 7.3 CLI Command Test Matrix

| Command | Unit test | CLI test (CliRunner) | Mock HW test | Real HW test |
|---------|-----------|---------------------|--------------|--------------|
| `robotos detect` | Sprint 5 | Sprint 5 | Sprint 5 | Sprint 5 |
| `robotos calibrate` | Sprint 5 | Sprint 5 | Sprint 5 | Sprint 5 |
| `robotos teleop` | Sprint 5 | Sprint 5 | Sprint 5 | Sprint 5 |
| `robotos record` | Sprint 6 | Sprint 6 | Sprint 6 | Sprint 6 |
| `robotos diagnose` | Sprint 4 | Sprint 4 | Sprint 4 | Sprint 4 |
| `robotos monitor` | Sprint 4 | Sprint 4 | Sprint 4 | Sprint 4 |
| `robotos exercise` | Sprint 4 | Sprint 4 | Sprint 4 | Sprint 4 |
| `robotos tui` | Sprint 6 | Sprint 6 | Sprint 6 | Sprint 6 |
| `robotos profile list` | Sprint 3 | Sprint 3 | N/A | N/A |

---

## 8. Recommended Testing Tools

| Tool | Purpose | Sprint needed |
|------|---------|---------------|
| pytest | Test runner, fixtures, parametrize | Sprint 1 |
| pytest-cov | Coverage reporting and gating | Sprint 1 |
| pytest-benchmark | Performance regression testing | Sprint 2 |
| click.testing.CliRunner | CLI command integration tests | Sprint 1 |
| textual.pilot | TUI automated testing | Sprint 6 |
| hypothesis | Property-based testing for profile validation | Sprint 3 |
| QEMU + OVMF | ISO boot testing in CI | Sprint 6 |
| expect (or pexpect) | Interactive CLI testing, VM smoke tests | Sprint 5 |
| GitHub Actions | CI/CD pipeline | Sprint 1 |
| act | Local CI/CD testing | Sprint 1 (optional) |
| nmap / ss | Security testing for open ports | Sprint 6 |

---

## 9. CI/CD Pipeline Recommendation

### Pipeline Stages

```
Push to any branch
        |
        v
[Stage 1: Lint + Type Check]     ~30s
  - ruff check
  - mypy --strict robotos/
        |
        v
[Stage 2: Unit Tests]            ~60s
  - pytest tests/unit/ --cov --cov-fail-under=80
        |
        v
[Stage 3: Integration Tests]     ~120s
  - pytest tests/integration/ (mock hardware)
  - pytest tests/cli/ (CliRunner)
        |
        v
[Stage 4: Performance Tests]     ~60s
  - pytest tests/perf/ --benchmark-only
  - Compare against baseline, fail on >20% regression
        |
        v
[Stage 5: Security Checks]       ~30s
  - Check for world-writable files in package
  - Validate udev rules use MODE=0660
  - Scan for hardcoded secrets

Merge to main (additional)
        |
        v
[Stage 6: ISO Build]             ~45 min
  - Build ISO via live-build
  - QEMU smoke test
  - Upload ISO artifact

Nightly
        |
        v
[Stage 7: Extended Tests]
  - 1-hour stability test with mock hardware
  - Full hardware compatibility (if self-hosted runner with hardware)
  - Memory leak detection (tracemalloc)
```

---

## 10. Gaps in Acceptance Criteria (by story)

| Story | Gap | Severity |
|-------|-----|----------|
| 2.1 | No AC for `disconnect()` behavior (what if called twice? what if never connected?) | MAJOR |
| 2.1 | No AC for `get_plugin("nonexistent")` -- should raise, return None, or what? | MAJOR |
| 2.2 | No AC for duplicate servo IDs on the bus | MAJOR |
| 2.4 | AC says "up to 10 retries" but NFR6 says "maximum of 3 attempts." These conflict. | CRITICAL |
| 3.3 | No AC for what happens if the USB serial number changes (new adapter) | MAJOR |
| 3.4 | "20% outside calibrated range" -- 20% of what? The range width? The absolute value? | MAJOR |
| 5.1 | No AC for what happens if the poll rate exceeds serial bus bandwidth | MAJOR |
| 5.3 | No AC for alert deduplication (same fault firing every 100ms would flood the UI) | MAJOR |
| 6.2 | No AC for single-arm teleop (what if only follower is connected, no leader?) | MINOR |
| 6.4 | No AC for multiple CH340 adapters (how to distinguish leader from follower?) | MAJOR |
| 7.3 | No AC for what happens if a workflow crashes inside the TUI | MAJOR |
| 8.1 | No AC for ISO reproducibility (same inputs produce same ISO hash?) | MINOR |
| 9.3 | No AC for disk space checking before recording | MAJOR |

---

## 11. Specific Recommendations by Sprint

### Sprint 1 (must add)
- Story for test infrastructure (pytest, mocks, CI pipeline)
- MockServoProtocol implementation
- GitHub Actions workflow

### Sprint 2 (must add)
- ServoProtocolConformanceTests base class
- FaultInjector wrapper for chaos testing
- Performance benchmark baseline for bus scan

### Sprint 3 (must add)
- Property-based tests for profile schema validation (hypothesis)
- Calibration atomic write test (crash safety)

### Sprint 4 (must add)
- Golden output comparison for diagnostic migration
- Per-check unit tests with mock telemetry data

### Sprint 5 (must add)
- Teleop latency benchmark (NFR1)
- Threading stress test for concurrent serial access
- End-to-end workflow test (mock hardware)

### Sprint 6 (must add)
- QEMU ISO smoke test
- TUI pilot tests
- Security scan
- Usability test protocol and execution

---

## 12. Summary of Required Actions

1. **BLOCKER:** Add test infrastructure story to Sprint 1 (B1)
2. **BLOCKER:** Add "automated tests required" to project Definition of Done (B2)
3. **BLOCKER:** Define hardware compatibility test protocol for Story 8.4 (B3)
4. **CRITICAL:** Fix retry count conflict: Story 2.4 says 10, NFR6 says 3 (C2, also in Gaps table)
5. **CRITICAL:** Fix permissions conflict: Story 8.2 says 0666, NFR21 says 0660 (C4)
6. **CRITICAL:** Add latency measurement to Story 6.2 AC (C1)
7. **CRITICAL:** Build MockServoProtocol with fault injection in Sprint 1 (C2, C3)
8. **CRITICAL:** Clarify SC1 "5 minutes" -- with or without first-time calibration (C7)
9. **CRITICAL:** Plan protocol conformance test suite for plugin architecture (C5)

---

*QA review for RobotOS USB planning artifacts -- generated by Quinn (QA Engineer).*
