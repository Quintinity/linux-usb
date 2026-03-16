# Architect Review: RobotOS Planning Artifacts

**Reviewer:** Winston (Architect)
**Date:** 2026-03-15
**Status:** Review Complete
**Artifacts Reviewed:** product-brief.md, prd.md, architecture.md, epics.md, sprint-plan.md

---

## Overall Assessment

The planning artifacts are unusually well-integrated for a project at this stage. The product brief to PRD to architecture to epics to sprint plan pipeline has strong traceability -- FR numbers flow through, dependency chains are consistent, and the MVP scope is realistic. The architecture document reflects genuine lessons learned from the Surface Pro 7 deployment (brltty hijack, sync_read retries, power supply issues), which gives it credibility that a greenfield design would lack.

That said, I have identified several architectural gaps, questionable decisions, and missing risk mitigations that should be addressed before Sprint 1 begins.

**Verdict: Approved with required changes.** The issues below range from "fix before implementation" to "address during Sprint 2." None are project-blockers, but several will cause painful rework if ignored.

---

## 1. HAL Abstraction: Good Foundation, Missing Pieces

### What works

The `ServoProtocol` ABC is clean. Fourteen methods is reasonable (under the NFR18 cap of 15). The `read_register`/`write_register` escape hatch for protocol-specific features is the right call -- it avoids bloating the common interface while allowing power users to reach hardware-specific registers.

### Issue 1.1: Missing batch telemetry read

The ABC has `sync_read_positions` and `sync_write_positions` for efficient multi-servo position I/O, but `get_telemetry()` is per-servo only. In the teleop loop, reading telemetry for 6 servos one at a time adds 6 round-trips per cycle. At 60 Hz with ~2ms per read, that is 12ms of the 16.7ms budget consumed by telemetry alone -- leaving only 4.7ms for position reads, writes, and processing. This will violate NFR1 (20ms p95 teleop latency) under real conditions.

**Recommendation:** Add `sync_read_telemetry(servo_ids: list[int]) -> dict[int, ServoTelemetry]` to the ABC. The Feetech protocol supports reading contiguous register blocks in a single packet (addresses 56-69 cover position through current). The Dynamixel protocol has Bulk Read for this exact purpose. This is not premature optimization; it is a correctness requirement for hitting the latency target.

### Issue 1.2: No async/non-blocking read interface

The architecture correctly identifies that telemetry and teleop share the serial bus and uses a `threading.Lock` to prevent concurrent access. But this means the telemetry thread must wait for the teleop thread's writes to complete before it can read. Under contention, telemetry sampling becomes irregular and the teleop loop gets blocked waiting for the lock.

**Recommendation:** Instead of a lock-per-port with separate teleop and telemetry threads, use a **single reader/writer thread per bus** that performs a combined read-write cycle: read leader positions + read follower telemetry + write follower positions, all in one locked sequence. The telemetry stream subscribes to the data produced by this cycle rather than initiating its own reads. This eliminates lock contention entirely and guarantees deterministic cycle timing.

```
Single Bus Thread (per arm pair):
  loop at 60Hz:
    1. sync_read leader positions
    2. sync_read follower telemetry (if telemetry subscribers exist)
    3. sync_write follower goal positions
    4. publish positions + telemetry to subscribers
```

### Issue 1.3: `connect()` should return a context manager

The current interface has separate `connect()` and `disconnect()` methods. Every caller must remember to call `disconnect()` in a finally block. This is error-prone, especially when exceptions occur during calibration or diagnostic checks.

**Recommendation:** Make `ServoProtocol` a context manager (`__enter__`/`__exit__`). Keep `connect()`/`disconnect()` as explicit methods for cases where context manager semantics do not fit (long-lived teleop sessions), but provide the safe default.

---

## 2. Plugin System: Will It Actually Work for Dynamixel?

### Issue 2.1: Protocol discovery is underspecified

Story 2.1 mentions `ServoProtocol.get_plugin("feetech")` but does not define the discovery mechanism. The architecture document shows plugins in `robotos/hal/plugins/` but does not explain how new plugins are registered. For MVP with only Feetech this is fine, but the Growth phase (Epic 10.2) needs a real answer.

**Recommendation:** Use Python entry points for plugin discovery. This is the standard mechanism for pip-installable plugins:

```toml
# In a third-party package's pyproject.toml:
[project.entry-points."robotos.servo_protocols"]
dynamixel = "robotos_dynamixel:DynamixelPlugin"
```

```python
# In robotos/hal/protocol.py:
from importlib.metadata import entry_points

def get_protocol(name: str) -> type[ServoProtocol]:
    eps = entry_points(group="robotos.servo_protocols")
    for ep in eps:
        if ep.name == name:
            return ep.load()
    raise PluginNotFoundError(name)
```

This lets third-party packages register protocols without modifying RobotOS core. Define this mechanism in the architecture now, even if MVP only ships the built-in Feetech plugin. Retrofitting entry points later changes the import structure.

### Issue 2.2: Dynamixel protocol differences are deeper than the ABC suggests

Dynamixel uses a fundamentally different packet structure (Instruction Packet with header 0xFF 0xFF 0xFD 0x00), different register sizes (4-byte position vs Feetech's 2-byte), different error semantics (Hardware Error Status byte vs Feetech's status register), and Bulk Read/Sync Read with different framing. The current ABC handles this through the abstraction, which is correct. But the `ServoTelemetry` dataclass assumes all protocols report the same fields.

**Recommendation:** Make `error_flags` a protocol-specific enum rather than `list[str]`. Define a `ServoErrorFlag` enum with common flags (OVERLOAD, OVERHEAT, OVERVOLTAGE, COMMUNICATION) and allow protocols to extend it. This avoids stringly-typed error handling.

### Issue 2.3: No protocol version negotiation

The Feetech STS3215 and SCS0009 use the same packet protocol but different register maps. Dynamixel Protocol 1.0 (AX/MX series) and Protocol 2.0 (X series) are completely different wire formats. The ABC does not model this.

**Recommendation:** Add a `protocol_version` property to the ABC and allow the plugin to probe the servo firmware to determine which register map to use. For MVP this is not needed (STS3215 only), but document the hook point so the Dynamixel plugin does not need to hack around it.

---

## 3. Concurrency Model: Needs Tightening

### Issue 3.1: GC disabling is a code smell

The architecture proposes `gc.disable()` during teleoperation to prevent GC pause spikes. This is a known technique but creates a memory leak risk during long data collection sessions (FR24 targets 50+ episodes). If episodic `gc.collect()` calls happen between episodes, any episode that runs long without a break accumulates garbage.

**Recommendation:** Instead of blanket GC disabling, use `gc.freeze()` (Python 3.12+) at the start of teleoperation to freeze the current generation 0/1/2 objects, then `gc.unfreeze()` at the end. This prevents GC from scanning the pre-existing object graph while still collecting new garbage. Also consider pre-allocating numpy arrays for telemetry buffers to minimize allocations in the hot loop.

### Issue 3.2: No watchdog for the teleop loop

NFR1 requires 20ms p95 latency. The architecture has a latency histogram for measurement but no active watchdog. If the loop stalls (e.g., USB controller hangs for 500ms), the follower arm holds its last commanded position -- which may be mid-motion toward a collision.

**Recommendation:** Add a deadline-based watchdog. If a teleop cycle exceeds a configurable deadline (e.g., 50ms), the watchdog fires and disables follower torques. This is a safety requirement for physical robots. The watchdog should run on a separate thread (or use `signal.alarm` on Linux) and should be documented as a safety-critical component.

### Issue 3.3: Thread naming and observability

The architecture describes multiple threads (bus reader, telemetry poller, pyudev monitor, textual workers) but does not require naming them. When debugging deadlocks or performance issues, unnamed threads in `py-spy` or `gdb` output are painful.

**Recommendation:** Require all threads to be named (e.g., `Thread(name="bus-follower-rw", ...)`). Add a `robotos debug threads` command that lists all active threads with their state. This costs nothing and pays dividends during integration testing.

---

## 4. OS Image Build: live-build Is the Right Choice, But...

### Issue 4.1: live-build on Ubuntu 24.04 has known issues

`live-build` is primarily a Debian tool. Ubuntu's fork diverges, and Ubuntu 24.04 (noble) has had [compatibility issues](https://bugs.launchpad.net/ubuntu/+source/live-build) with `live-build` configuration syntax. The architecture does not mention which `live-build` version or whether to use the Debian or Ubuntu fork.

**Recommendation:** Pin the build environment. Use a Docker container with a known-good `live-build` version for ISO builds. This also makes CI/CD builds reproducible across developer machines:

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y live-build
# Pin to specific live-build version
```

This naturally leads to...

### Issue 4.2: No containerization strategy for builds

The architecture mentions "GitHub Actions / local" for the build pipeline but does not specify a containerized build environment. ISO builds that work on one developer's machine but fail on another are a classic problem.

**Recommendation:** Define a `Dockerfile.build` that produces the ISO. This is orthogonal to whether the runtime OS uses containers (it should not -- containers add latency to serial port access). The build container is for reproducibility only.

### Issue 4.3: Persistent partition sizing and format

The architecture shows a `robotos/` persistent partition on the USB drive but does not specify how it is created, sized, or formatted. Key questions:

- Is it ext4 or f2fs (flash-friendly)?
- Is it created at ISO build time (fixed size) or on first boot (uses remaining space)?
- How does casper persistence integrate with this?

**Recommendation:** Use Ubuntu's built-in casper persistence mechanism with a `writable` partition that expands to fill remaining USB space on first boot. Format as f2fs for flash-wear leveling. This is more robust than a custom partition scheme and is well-tested in the Ubuntu live ecosystem. Document the first-boot expansion script as Story 8.2 acceptance criteria.

### Issue 4.4: Kernel strategy gap

The architecture proposes shipping both standard and Surface kernels selectable via GRUB. But the ISO build uses `live-build`, which builds a squashfs with a single kernel. Including two kernels means two `linux-image-*` packages in the squashfs, adding ~500MB to the image.

**Recommendation:** Ship the standard kernel in the base image. Provide a `robotos-surface-kernel` package in an on-image apt repository that can be installed to the persistent partition on first boot. Better yet, detect Surface hardware at boot time (check DMI table for "Microsoft") and install the Surface kernel automatically. This keeps the base image smaller and avoids wasting space on non-Surface hardware.

---

## 5. ROS2 Interop: The ADR Is Correct But Incomplete

ADR-5 correctly excludes ROS2 as a core dependency. The rationale is sound: 2GB image size, complexity, and target audience mismatch. However, the architecture does not describe how a future `robotos-ros2-bridge` would actually work.

**Recommendation:** Document the bridge design now, even if it is Growth/Vision scope. The bridge should:

1. Publish servo telemetry as ROS2 topics (sensor_msgs/JointState)
2. Subscribe to ROS2 command topics for position control
3. Run as a separate process that communicates with RobotOS via the Unix domain socket already specified for `robotos-detect.service`

This means the IPC protocol on the Unix socket needs to be defined. Right now, the socket is mentioned once (Section 13, first boot sequence) with no protocol specification. If the socket protocol is designed for extensibility now, the ROS2 bridge becomes straightforward later.

**Specific recommendation:** Use a simple JSON-over-newline protocol on the Unix socket. Each message is a JSON object terminated by `\n`. This is debuggable with `socat`, parseable from any language, and trivial to bridge to ROS2 topics.

---

## 6. Error Handling: Graceful Degradation Is Designed, Recovery Is Not

### Issue 6.1: No reconnection strategy

Section 10.3 describes graceful degradation when a servo drops off the bus (mark as DEGRADED, continue with remaining joints). But it does not describe what happens when the entire USB controller is unplugged and re-plugged. Does the teleop loop automatically reconnect? Or must the user restart?

**Recommendation:** Define three levels of failure recovery:

1. **Servo-level:** Single servo unresponsive. Mark degraded, continue. Already designed.
2. **Bus-level:** Entire serial port disappears. Pause teleop, attempt reconnect for 10 seconds, resume if successful, abort if not.
3. **System-level:** Multiple buses fail. Halt all operations, display diagnostic summary, offer restart.

Bus-level recovery is important because USB hubs on laptops are notorious for resetting under power fluctuations. The user should not have to restart everything because their hub glitched.

### Issue 6.2: No structured error taxonomy

The architecture uses ad-hoc error strings throughout. The diagnostic checks return `CheckResult` with a string message. The fault detection system generates alert strings. Claude Code parses these strings. This is fragile.

**Recommendation:** Define a `RobotOSError` hierarchy:

```python
class RobotOSError(Exception): ...
class CommunicationError(RobotOSError): ...
class ServoTimeoutError(CommunicationError): ...
class BusDisconnectedError(CommunicationError): ...
class ProtectionTripError(RobotOSError): ...
class CalibrationError(RobotOSError): ...
class ProfileError(RobotOSError): ...
```

Each error class carries structured data (servo_id, register, expected_value, actual_value) that diagnostic reporters and AI context generators can use without parsing strings.

---

## 7. Migration Path: Sound but Missing a Key Step

### Issue 7.1: No parallel running period

The migration phases (A through F) move linearly from old scripts to new package. But there is no phase where both old and new coexist, allowing validation that the new code produces identical behavior. For a robotics system where behavior differences can damage hardware, this is risky.

**Recommendation:** Add a **Phase A.5: Validation harness.** Before the old scripts are deleted, write integration tests that run both the old script and the new `robotos` equivalent on the same hardware and compare outputs. For diagnostics, this means running `python diagnose_arms.py` and `robotos diagnose --json` and asserting the same checks produce the same pass/fail results. This validation harness can be removed after Phase C.

### Issue 7.2: LeRobot monkey-patching is a maintenance liability

The architecture proposes monkey-patching LeRobot's `FeetechMotorsBus` at import time to add sync_read retries. This works for v0.5.0 but will break silently if LeRobot v0.5.1 or v0.6.0 changes the patched method signature. The architecture pins to `lerobot>=0.5.0`, which allows upgrades that could break the patches.

**Recommendation:** Pin to `lerobot==0.5.0` (exact version, not minimum). Add a startup check that verifies the patched method signatures match the expected signatures (compare `inspect.signature` against a stored expected value). If the signature changes, fail loudly with "LeRobot version incompatible with RobotOS patches. Pin to 0.5.0 or update patches." Long-term, contribute the retry logic upstream and remove the monkey-patches.

---

## 8. Sprint Plan Risks

### Issue 8.1: Sprint 4 and Sprint 6 are overloaded

Sprint 4 (24 weight points) and Sprint 6 (33 weight points) are each significantly heavier than Sprints 1-3. The sprint plan acknowledges this but the mitigations are weak ("consider splitting if velocity is lower than expected").

**Recommendation:** Pre-commit to the Sprint 6a/6b split now. Do not treat it as a contingency -- treat it as the plan. A 14-week schedule with 7 sprints is more honest than a 12-week schedule with an asterisk. Similarly, start the `live-build` spike in Sprint 3 (as a small time-boxed task), not Sprint 4. `live-build` issues are the highest-impact unknown in the entire project, and discovering them in Week 11 is too late.

### Issue 8.2: No integration testing sprint

The sprint plan goes directly from individual feature sprints to Sprint 6 (the "ship everything" sprint). There is no dedicated integration testing period where all components are run together on real hardware.

**Recommendation:** Add a 1-week integration sprint between Sprint 5 and Sprint 6 (or between 6a and 6b). The integration sprint runs the full workflow (detect, calibrate, teleop, record, diagnose) on real SO-101 hardware and logs every defect. This is where the concurrency bugs, timing issues, and USB flakiness surface. Finding these in Sprint 6b (hardware compatibility testing) is too late.

---

## 9. Missing Architectural Concerns

### Issue 9.1: No logging strategy

The architecture mentions `NFR19: Structured hardware event logging` and specifies logs go to `~/.local/share/robotos/logs/`. But there is no specification of the logging framework, log format, log rotation, or log levels. Every component will invent its own logging pattern.

**Recommendation:** Standardize on Python's `logging` module with a JSON formatter for machine-readable logs and a human-readable formatter for console output. Define log levels: DEBUG (register-level reads), INFO (workflow start/stop), WARNING (retries, threshold approaches), ERROR (failed operations), CRITICAL (safety stops). Configure rotation at 50MB per file, 5 files retained. Set this up in Story 1.1 as part of the package skeleton so every subsequent story inherits it.

### Issue 9.2: No metrics or performance instrumentation

NFR1 requires 20ms p95 teleop latency, and the architecture mentions a "latency histogram." But there is no specification of how latency is measured, where histograms are stored, or how to access them.

**Recommendation:** Add a lightweight metrics module (`robotos/utils/metrics.py`) that records histograms for key operations: teleop cycle time, serial read/write latency, telemetry poll interval. Expose via `robotos teleop --stats` which prints a summary at session end. This module should exist from Sprint 2 so that every subsequent feature automatically reports its performance characteristics.

### Issue 9.3: No configuration override mechanism

The robot profile YAML defines all settings, but there is no way to override individual values without editing the YAML file. A user who wants to change `fps: 60` to `fps: 30` for testing must edit the built-in profile, which lives in a read-only squashfs on the USB.

**Recommendation:** Support a configuration override chain:

```
Built-in profile (read-only)
  -> User profile override (~/.config/robotos/profiles/so101.override.yaml)
    -> CLI flags (--fps 30)
      -> Environment variables (ROBOTOS_TELEOP_FPS=30)
```

Each layer overrides the previous. The override YAML is a sparse document -- only the fields being changed, not a full copy. Pydantic supports this pattern natively via model inheritance and merge.

### Issue 9.4: No data integrity verification for datasets

NFR8 requires no episode data loss. The architecture specifies flushing to disk after each episode (Story 9.3). But there is no checksum or integrity verification for the recorded data. A corrupted camera frame or truncated position sequence would silently produce bad training data.

**Recommendation:** Write a per-episode manifest (`episode_NNN.manifest.json`) containing frame count, position sample count, SHA256 of camera frames file, and SHA256 of positions file. The `robotos record --verify` command validates all manifests after a session. This catches corruption from USB power glitches or filesystem issues.

---

## 10. Specific Technical Recommendations Summary

| # | Recommendation | Priority | Affects |
|---|---------------|----------|---------|
| 1 | Add `sync_read_telemetry()` to ServoProtocol ABC | **Must fix** | Architecture, Story 2.1 |
| 2 | Single bus thread instead of lock-per-port | **Must fix** | Architecture Section 10.6, Story 6.2 |
| 3 | Make ServoProtocol a context manager | Should fix | Architecture, Story 2.1 |
| 4 | Use Python entry points for plugin discovery | Should fix | Architecture, Story 10.2 |
| 5 | Typed error enum for ServoTelemetry.error_flags | Should fix | Architecture, Story 2.1 |
| 6 | Use gc.freeze() instead of gc.disable() | Should fix | Architecture Section 10.6 |
| 7 | Add teleop loop watchdog | **Must fix** | Architecture, Story 6.2 |
| 8 | Name all threads | Should fix | Architecture Section 10.6 |
| 9 | Containerize ISO build with Dockerfile.build | Should fix | Story 8.1 |
| 10 | Use f2fs for persistent partition, expand on first boot | Should fix | Story 8.2 |
| 11 | Detect Surface hardware via DMI, install kernel on first boot | Nice to have | Architecture Section 3 |
| 12 | Define Unix socket IPC protocol (JSON-over-newline) | Should fix | Architecture Section 13 |
| 13 | Define three-level failure recovery (servo/bus/system) | **Must fix** | Architecture Section 10.3 |
| 14 | Define RobotOSError exception hierarchy | Should fix | Architecture (new section) |
| 15 | Add validation harness (Phase A.5) | Should fix | Architecture Section 15 |
| 16 | Pin lerobot==0.5.0 (exact) with signature check | **Must fix** | pyproject.toml, Story 9.2 |
| 17 | Pre-commit to Sprint 6a/6b split | Should fix | Sprint plan |
| 18 | Add live-build spike to Sprint 3 | **Must fix** | Sprint plan |
| 19 | Add integration testing sprint | Should fix | Sprint plan |
| 20 | Standardize logging (JSON + rotation) in Story 1.1 | Should fix | Architecture, Story 1.1 |
| 21 | Add metrics module for latency histograms | Should fix | Architecture (new section) |
| 22 | Support configuration override chain | Should fix | Architecture Section 5, Story 3.1 |
| 23 | Add per-episode integrity manifests | Should fix | Story 9.3 |

---

## 11. What the Architecture Gets Right

Credit where due -- several decisions are strong and should not be second-guessed:

1. **No ROS2 dependency.** Correct for the target audience. The 2GB size cost and complexity overhead are not justified.
2. **YAML for profiles, JSON for calibration.** Matches the human-edited vs machine-generated distinction perfectly.
3. **Click for CLI, Textual for TUI, FastAPI for web.** All mature, all Python-native, all compatible. No exotic dependencies.
4. **Separation of presentation and domain logic.** The CLI/TUI/Web layers calling the same underlying functions is the right pattern.
5. **XDG compliance for file paths.** Professional touch that avoids polluting home directories.
6. **brltty removal baked into ISO.** This is the #1 failure mode for Feetech users and the architecture addresses it at the OS layer where it belongs.
7. **Existing diagnostic suite as the seed.** Building on proven, battle-tested code rather than starting from scratch.
8. **Offline-first design.** Every feature works without internet. Network is additive, not required.

---

## 12. Final Notes

The biggest systemic risk is the concurrency model for real-time servo control. The current design (teleop thread + telemetry thread + lock per port) will exhibit timing jitter under real-world conditions. Switching to a single bus thread that handles both teleop and telemetry in a coordinated cycle is the single most impactful architectural change I am recommending.

The second biggest risk is the `live-build` ISO creation (Story 8.1, XL). This is a black box of complexity that sits at the end of the critical path. Starting a spike in Sprint 3 is not optional -- it is schedule insurance.

Everything else is refinement. The foundation is solid.

---

*Architect review for RobotOS USB planning artifacts -- Winston (Architect Agent)*
