# Developer Review: RobotOS Planning Artifacts

**Reviewer:** Amelia (Developer)
**Date:** 2026-03-15
**Status:** Review Complete
**Scope:** All planning artifacts (product-brief, PRD, architecture, epics, sprint-plan) reviewed against the existing codebase (diagnose_arms.py, monitor_arm.py, teleop_monitor.py, exercise_arm.py).

---

## Overall Assessment

The planning is thorough and the architecture is sound. The migration path from existing scripts to the `robotos` package is clearly mapped. However, there are several areas where implementation will hit friction that the current stories do not account for. This review focuses on what will actually trip us up when writing code.

**Verdict:** Approve with required changes. The stories need sharpening in the areas called out below before Sprint 1 starts.

---

## 1. Python Packaging and Project Structure

### What the architecture says
`pyproject.toml` with `click`, flat `robotos/` layout, entry point at `robotos.cli.main:cli`.

### What I recommend

**Use `src/` layout, not flat layout.** The flat layout (`robotos/` at repo root) creates import ambiguity: `import robotos` could resolve to the source directory rather than the installed package. The `src/` layout (`src/robotos/`) forces imports to go through the installed package, which catches packaging bugs early.

```
src/
  robotos/
    __init__.py
    cli/
    hal/
    ...
pyproject.toml
tests/
```

**Pin dependency versions in a lockfile.** The `pyproject.toml` shows `lerobot>=0.5.0` but we already know LeRobot API changes are a risk (sprint plan Risk #6). Use `pip-compile` (pip-tools) or `uv lock` to generate a lockfile. The `pyproject.toml` should have loose bounds; the lockfile pins exact versions for reproducible builds.

**Add `py.typed` marker.** If we want type checking to work across consumers, we need `src/robotos/py.typed`.

### Story impact
- Story 1.1 needs to specify `src/` layout explicitly in acceptance criteria.
- Story 1.1 should include a lockfile generation step.
- Add an acceptance criterion: "Running `mypy robotos` produces no errors on the skeleton."

---

## 2. The ServoProtocol ABC Is Overdesigned for MVP

### The problem

The architecture defines 14+ abstract methods on `ServoProtocol`. The existing code (all four scripts) uses exactly one concrete class: `FeetechMotorsBus` from LeRobot. For MVP, there is exactly one protocol implementation (Feetech) and one robot (SO-101).

The `ServoProtocol` ABC as currently specified has methods like `read_position(servo_id)` and `write_position(servo_id, position)` operating on individual servos. But the existing code exclusively uses `sync_read` and `sync_write` (batch operations on all servos simultaneously). Individual reads are only used for telemetry registers (voltage, temp, load) which are not part of the position control path.

### What will actually happen

The FeetechPlugin will be a thin wrapper around `FeetechMotorsBus` that translates between two APIs that do almost the same thing. This is boilerplate with no value until we have a second protocol.

### Recommendation

**Design the ABC from the existing code, not from an abstract ideal.** Look at what the four scripts actually call:

1. `bus.connect()` / `bus.disconnect()`
2. `bus.sync_read("Present_Position")` -- batch read
3. `bus.sync_write("Goal_Position", positions)` -- batch write
4. `bus.packet_handler.read1ByteTxRx(port, id, addr)` -- raw register reads for telemetry
5. `bus.packet_handler.ping(port, id)` -- individual ping
6. `bus.enable_torque()` / `bus.disable_torque()`
7. `bus.write("Operating_Mode", motor, value)` -- per-motor config writes
8. `bus.configure_motors(return_delay_time=0)` -- bulk config

The ABC should match these patterns. In particular:
- `sync_read_positions()` and `sync_write_positions()` should be the primary interface, not single-servo methods.
- `get_telemetry(servo_id)` is fine as a single-servo call since telemetry is polled at a lower rate.
- Keep `read_register`/`write_register` as the escape hatch (the architecture already has this, good).

**Reduce abstract methods to fewer than 10 for MVP.** The NFR says "fewer than 15 required methods" but 15 is still a lot for someone writing a plugin. I would target 8-10:

```python
class ServoProtocol(ABC):
    connect(port, baudrate) -> None
    disconnect() -> None
    ping(servo_id) -> bool
    scan_bus(id_range) -> list[ServoInfo]
    sync_read_positions(servo_ids) -> dict[int, int]
    sync_write_positions(positions: dict[int, int]) -> None
    get_telemetry(servo_id) -> ServoTelemetry
    read_register(servo_id, address, size) -> int
    write_register(servo_id, address, value, size) -> None
    enable_torque(servo_ids: list[int]) -> None
    disable_torque(servo_ids: list[int]) -> None
    flush_port() -> None
```

Note: `enable_torque` and `disable_torque` take lists, not single IDs, matching the batch pattern of the existing code.

### Story impact
- Story 2.1 should include an acceptance criterion: "The ABC has 12 or fewer abstract methods" (concrete number, not "10+").
- Story 2.1 should add: "The FeetechPlugin passes an integration test that mirrors the exact call sequence from `teleop_monitor.py`."

---

## 3. Existing Code Reuse -- Duplicated Patterns Need Extraction First

### The problem

All four existing scripts duplicate significant code:

1. **Motor map construction** (`make_motors()`) -- identical in all four files.
2. **Calibration loading** (`load_calibration()`) -- identical in diagnose_arms.py and exercise_arm.py, slightly different in teleop_monitor.py.
3. **Color constants** (RED, GREEN, YELLOW, etc.) -- identical in all four files.
4. **Sign-magnitude decoding** (`decode_sign_magnitude()`) -- in monitor_arm.py and teleop_monitor.py.
5. **Error flag decoding** (`decode_errors()`) -- in monitor_arm.py and teleop_monitor.py.
6. **Servo telemetry reading** (`read_servo_telemetry()`) -- in teleop_monitor.py, partially duplicated in monitor_arm.py.
7. **Follower arm configuration** (PID settings, torque enable, protection current) -- identical block in teleop_monitor.py, exercise_arm.py, and diagnose_arms.py phase 8/9.

Story 1.3 (Serial Helpers) captures items 4 and partially item 1, but items 1, 2, 5, 6, and 7 are not covered by any Sprint 1 story. They will be needed by Sprint 2 (HAL implementation) at the latest.

### Recommendation

**Add a "Common Patterns Extraction" task to Story 1.3** or create a new story 1.6. This should extract:
- Motor map construction into profile-driven factory
- Color/terminal formatting into `robotos.utils.colors` (architecture already shows this)
- Error flag decoding into `robotos.utils.serial`
- Servo telemetry reading into a helper that becomes the basis for `ServoProtocol.get_telemetry()`
- Follower arm configuration sequence into a reusable function

Without this, Sprint 2 will waste time re-extracting these patterns from the existing scripts.

---

## 4. Testing Strategy -- Critical Gap

### What is missing

None of the stories include testing acceptance criteria. The sprint plan mentions no test framework, no test structure, no mocking strategy. For a hardware-dependent project, this is the single biggest risk.

### Specific testing concerns

**a) Hardware abstraction testing without hardware.** The `ServoProtocol` ABC exists partly to enable testing without physical servos. But none of the stories require a mock/simulator implementation. Without one, every test that touches HAL code requires a physical robot.

**b) Serial communication mocking.** The existing code calls `bus.packet_handler.read1ByteTxRx()` directly. Tests need to mock at the pyserial level or provide a fake `FeetechMotorsBus`. LeRobot does not provide test fixtures for this.

**c) CI/CD.** The sprint plan mentions "CI/CD" but no story covers setting up GitHub Actions. Story 8.1 (ISO build) depends on it. Running tests in CI requires a mock layer.

### Recommendation

**Add a Story 1.7 (or fold into 1.1): Testing Infrastructure.**

Acceptance criteria:
- `pytest` configured in `pyproject.toml` with `tests/` directory
- A `FakeServoProtocol` class that implements `ServoProtocol` with deterministic, in-memory behavior (returns canned positions, simulates faults on demand)
- A `conftest.py` with fixtures: `fake_protocol`, `sample_profile` (loads the SO-101 YAML), `tmp_config_dir` (temporary XDG paths)
- GitHub Actions workflow that runs `pytest` on every push
- `pre-commit` config with `ruff` (linting + formatting), `mypy` (type checking)

**Every subsequent story should include at least one testable acceptance criterion that can be verified by a pytest test, not just manual hardware testing.** For example:

- Story 2.2 (Bus Scan): "Given a `FakeServoProtocol` configured with servos at IDs [1,2,3,6], when `scan_bus(range(1,13))` is called, then 4 ServoInfo objects are returned."
- Story 3.1 (Profile Loader): "Given a YAML file with an invalid `servo_id: 'abc'`, when loaded, then `ProfileValidationError` is raised with a message containing 'servo_id'."
- Story 5.3 (Fault Detection): "Given a `FakeServoProtocol` returning voltage=5.0V for servo 3, when the telemetry stream processes a sample, then a voltage_sag alert is emitted."

### Size impact

This is at least a size M story. Sprint 1 capacity increases from 5 to 8 weight points, which is still light.

---

## 5. Story 2.1 (ServoProtocol + FeetechPlugin) Is Undersized at L

### The problem

Story 2.1 requires:
1. Designing the ABC (requires reviewing all downstream consumers in Epics 3-6)
2. Implementing the FeetechPlugin (wrapping FeetechMotorsBus)
3. Implementing plugin discovery (`ServoProtocol.get_plugin("feetech")`)
4. Hardware integration testing

This is really two stories: the ABC design and the Feetech implementation. If the ABC needs iteration after Sprint 3 starts consuming it, the refactoring cost is high (the sprint plan already flags this risk).

### Recommendation

**Split 2.1 into two stories:**
- **2.1a: ServoProtocol ABC and FakeServoProtocol** (M) -- Design the interface, implement the test double. Can be reviewed against Epic 3-6 acceptance criteria without hardware.
- **2.1b: FeetechPlugin Implementation** (M) -- Implement the Feetech wrapper. Requires hardware for integration test. Depends on 2.1a.

This lets us validate the ABC design before committing to the Feetech implementation.

---

## 6. Story 4.2 (Migrate Diagnostics) Should Be Split

### The problem

Story 4.2 is XL (weight 8) and migrates 11 diagnostic phases. The sprint plan acknowledges this is the "largest single story" and a schedule risk. Looking at the existing code:

- Phases 1-6 are stateless register reads (straightforward to migrate)
- Phases 7-8 are stateful stress tests with loops and timing (more complex)
- Phase 9 is a cross-bus teleop simulation that requires both arms (highest complexity)
- Phase 10 is per-motor isolation testing
- Phase 11 is calibration file validation (trivial)

### Recommendation

**Split into three stories:**
- **4.2a: Migrate stateless checks (Phases 1-6, 11)** -- M. Port detection, ping, firmware, power, status, EEPROM config, calibration validation.
- **4.2b: Migrate communication stress tests (Phases 7-8, 10)** -- M. Comms reliability, torque stress, motor isolation. These share the "run N cycles, count failures" pattern.
- **4.2c: Migrate cross-bus teleop simulation (Phase 9)** -- M. This is the most complex check and the only one requiring two arms.

Total weight goes from 8 to 9, but the granularity lets us track progress and allows 4.2a to ship independently.

---

## 7. Concurrency Model Needs Earlier Validation

### The problem

The architecture describes a concurrency model (section 10.6) with:
- Main thread for teleop loop
- Daemon thread for telemetry sampling
- `threading.Lock` per serial port
- `gc.disable()` during teleop

This is complex and latency-sensitive. But it is not validated until Story 6.2 (Sprint 5, week 9). If the threading model causes issues (lock contention, missed deadlines, serial port corruption from concurrent access), we discover it very late.

### What the existing code does

`teleop_monitor.py` already implements the dual-rate pattern: teleop at 60Hz, telemetry sampling at 2Hz. But it does this **on a single thread** with interleaved sampling (telemetry reads happen inline when the monitoring interval elapses). This works because pyserial is blocking and the telemetry reads are cheap relative to the teleop interval.

### Recommendation

**Start with the single-threaded interleaved model from `teleop_monitor.py`.** It is proven to work. Move to a multi-threaded model only if we need concurrent telemetry + teleop at independent rates. The single-threaded model avoids all lock contention and serial port corruption issues.

Add an acceptance criterion to Story 6.2: "Teleop loop achieves 60Hz with inline telemetry sampling at 2Hz, matching the pattern from the existing `teleop_monitor.py`. Multi-threaded telemetry is deferred until performance profiling demonstrates a need."

If multi-threading is needed later, Story 5.1 already creates the TelemetryStream class, which can be upgraded to use a background thread with port locking. But do not bake that complexity in from day one.

---

## 8. The LeRobot Bridge (Story 9.2) Has Hidden Complexity

### The problem

Story 9.2 says "translate my robot profile into LeRobot configuration objects." This sounds simple, but LeRobot v0.5.0's configuration system is opaque. Looking at the existing code, `teleop_monitor.py` does not use LeRobot's config system at all -- it directly instantiates `FeetechMotorsBus` with explicit motor definitions and calibration data.

The bridge needs to:
1. Construct a LeRobot `Robot` config object (undocumented internal API)
2. Map RobotOS joint names to LeRobot motor names
3. Handle calibration format differences (RobotOS stores in `~/.config/robotos/`, LeRobot expects `~/.cache/huggingface/lerobot/calibration/`)
4. Apply the monkey-patches from `lerobot_patches.py` before any LeRobot imports
5. Handle camera configuration (LeRobot's camera config is separate from servo config)

### Recommendation

**Do a spike in Sprint 2 or 3.** Before writing the bridge, spend a day understanding LeRobot's internal config objects by reading `lerobot/robot.py` and `lerobot/teleop.py` source. Document the exact objects needed. This spike de-risks Story 9.2 significantly.

**Add acceptance criterion to 9.2:** "The bridge produces a config that, when passed to LeRobot's `record()` function, successfully records an episode to disk. Validated with a 5-second recording session."

**Consider whether we even need the bridge for MVP.** The existing `teleop_monitor.py` drives servos directly without going through LeRobot's teleop layer. For MVP data collection, we could record servo positions ourselves and write them in LeRobot's HuggingFace Dataset format directly, bypassing LeRobot's config system entirely. This is simpler and avoids coupling to LeRobot internals that may change.

---

## 9. Sprint 4 Is Overloaded and Contains Two Epics

### The problem

Sprint 4 (Weeks 7-8) has weight 24 and contains 7 stories across Epics 4 and 5. The sprint plan itself says "consider splitting if velocity is lower than expected." Given that this is the first sprint doing real feature work after three foundational sprints, velocity will almost certainly be lower than expected.

### Recommendation

**Split Sprint 4 into 4a and 4b:**

- **Sprint 4a (Weeks 7-8):** Stories 4.1, 5.1, 4.3, 5.2 (weight: 10). Core frameworks for diagnostics and telemetry.
- **Sprint 4b (Weeks 9-10):** Stories 5.3, 4.4, 4.2 (weight: 14). Fault detection, exercise migration, and the big diagnostic migration.

Move Sprint 5 (Calibration + Teleop) to Weeks 11-12, and Sprint 6 to Weeks 13-14+. This adds 2 weeks but is more realistic. The alternative is Sprint 4 overflowing and pushing everything downstream anyway.

---

## 10. Hardcoded Values in Existing Code

### The problem

The existing scripts have hardcoded:
- Ports: `/dev/ttyACM0`, `/dev/ttyACM1`
- Calibration paths: `/home/bradley/.cache/huggingface/lerobot/calibration/...`
- Motor IDs: `[1, 2, 3, 4, 5, 6]`
- Motor names: `["shoulder_pan", "shoulder_lift", ...]`
- PID values: P=16, I=0, D=32
- Protection values: Max_Torque_Limit=500, Protection_Current=250
- Thresholds: VOLTAGE_MIN=6.0, TEMP_WARN=55, TEMP_CRIT=65
- Baud rate: 1,000,000
- Firmware version: v3.10 minimum

All of these need to come from the robot profile YAML. The architecture covers this, but the stories do not call out the specific migration of each hardcoded value.

### Recommendation

**Add a checklist to Story 3.2 (SO-101 Profile):** "The SO-101 YAML profile contains values for every constant currently hardcoded in the existing scripts:" followed by the list above. This ensures nothing is missed.

**Add to Story 4.2 acceptance criteria:** "No diagnostic check contains hardcoded port paths, motor IDs, motor names, or threshold values. All configuration comes from the loaded RobotProfile."

---

## 11. `rich` vs ANSI Escape Codes

### The problem

The architecture specifies `rich>=13.0` as a dependency for console output. The existing scripts use raw ANSI escape codes (`\033[91m`, etc.) throughout. The migration to `rich` needs to happen early and consistently, or we end up with a mix of raw ANSI and rich markup that looks broken in some terminals.

### Recommendation

**Make the switch in Sprint 1.** Story 1.3 (Serial Helpers) or a new Story 1.6 should establish the `rich` console pattern and provide helper functions that all downstream code uses. Kill the raw ANSI constants immediately.

Acceptance criterion: "The `robotos.utils.colors` module is deleted or empty. All terminal output uses `rich.console.Console` and `rich.table.Table`."

---

## 12. Code Quality Tooling

### What should be in Story 1.1

The `pyproject.toml` in Story 1.1 should include from day one:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "TCH"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"
```

And a `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, click]
```

**This is non-negotiable.** Without it, Sprint 2+ code will accumulate lint issues and inconsistent formatting that become expensive to fix later.

---

## 13. The TUI (Epic 7) Dependency on textual Is Risky

### The concern

`textual` is a powerful but opinionated framework. Embedding teleop output, diagnostic results, and live telemetry tables inside a textual app is significantly harder than printing to a terminal. The stories assume the TUI can "launch" workflows, but running a blocking teleop loop inside a textual worker thread introduces async/sync boundary issues.

### Recommendation

**Treat the TUI as a launcher that spawns subprocess commands, not as an embedded runtime.** When the user presses T for Teleop, the TUI should run `robotos teleop` in a subprocess (or yield the terminal to it) rather than trying to embed the teleop loop inside textual's event loop.

This keeps the CLI implementations clean (they own their own terminal) and reduces the TUI to a menu + status display. The telemetry panel (Story 7.2) can subscribe to telemetry data, but the action commands should not be embedded.

**Add acceptance criterion to Story 7.3:** "Workflow commands (teleop, calibrate, exercise) are launched as subprocess calls or take over the terminal, not embedded in the textual event loop. The TUI resumes when the subprocess exits."

---

## 14. Missing Story: Camera Integration

### The problem

The architecture defines a `CameraManager` class (section 4), and FR4 (USB camera detection via V4L2) is listed as MVP scope. But no MVP story explicitly implements the `CameraManager`. Story 6.4 (Hardware Detection Command) mentions cameras in its acceptance criteria, but the underlying `CameraManager` class is not built in any earlier story.

Story 9.3 (Data Collection) depends on cameras being available, but there is no story between 6.4 and 9.3 that implements the camera capture pipeline.

### Recommendation

**Add Story 6.5: Camera Detection and Capture** (M).

Acceptance criteria:
- `CameraManager.enumerate()` returns a list of V4L2 capture devices with resolutions and frame rates.
- `CameraManager.open(device_path)` returns an OpenCV `VideoCapture` object.
- `robotos detect` includes camera information in its output (feeds into 6.4).
- A camera test fixture exists that returns fake frame data for CI testing.

This can run in parallel with Story 6.1 in Sprint 5.

---

## 15. Versioning and Release Strategy

### What is missing

The PRD says MVP is v0.1.0 but there is no discussion of:
- How versions are bumped (manual? `bump2version`? `setuptools-scm`?)
- Whether we tag releases in git
- Whether the ISO version matches the Python package version
- How pre-release versions work during development

### Recommendation

Use `setuptools-scm` to derive the version from git tags. The `pyproject.toml` should specify:

```toml
[tool.setuptools_scm]
```

Tag the first release as `v0.1.0`. During development, the version is automatically `0.1.0.devN+gHASH`. This avoids manual version bumping.

---

## Summary of Required Changes

| Priority | Change | Affects |
|----------|--------|---------|
| **Must** | Add testing infrastructure story (1.7 or fold into 1.1) with FakeServoProtocol, pytest, CI | Sprint 1 |
| **Must** | Specify `src/` layout in Story 1.1 | Sprint 1 |
| **Must** | Add code quality tooling (ruff, mypy, pre-commit) to Story 1.1 | Sprint 1 |
| **Must** | Split Story 2.1 into ABC design + Feetech implementation | Sprint 2 |
| **Must** | Split Story 4.2 into three smaller stories | Sprint 4 |
| **Must** | Add camera integration story (6.5) | Sprint 5 |
| **Should** | Reduce ServoProtocol to fewer than 12 abstract methods | Sprint 2 |
| **Should** | Start with single-threaded concurrency model from teleop_monitor.py | Sprint 5 |
| **Should** | Split Sprint 4 into 4a/4b | Sprint plan |
| **Should** | Add hardcoded-value migration checklist to Story 3.2 | Sprint 3 |
| **Should** | TUI should launch workflows as subprocesses, not embedded | Sprint 6 |
| **Could** | LeRobot bridge spike in Sprint 2-3 | Sprint 4-6 |
| **Could** | Use setuptools-scm for versioning | Sprint 1 |
| **Could** | Consider bypassing LeRobot config for MVP data collection | Sprint 6 |

---

## Final Notes

The planning is genuinely good. The migration path from existing scripts is well-documented, the dependency chain is correct, and the PRD clearly distinguishes MVP from Growth scope. The architecture's ADRs are solid and well-reasoned.

My concerns are primarily about testing infrastructure (which is completely absent) and story granularity on the larger items. The existing code is a strong foundation -- it has been debugged against real hardware and encodes hard-won knowledge about Feetech servo quirks. The migration should preserve that knowledge, not abstract it away prematurely.

The single most valuable thing we can do before Sprint 1 starts is implement the `FakeServoProtocol` test double. Everything else flows from being able to test without hardware.

---

_Developer review for RobotOS USB planning artifacts._
