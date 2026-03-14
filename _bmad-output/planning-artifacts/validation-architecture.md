# Architecture Validation Report

**Reviewer:** Winston (Architect Agent)
**Date:** 2026-03-15
**Document Under Review:** architecture.md v1.0
**Cross-Referenced Against:** prd.md, epics.md, product-brief.md

---

## Overall Verdict: PASS (with issues)

The architecture is well-structured, comprehensive, and clearly informed by real operational experience with the SO-101 hardware. It provides a clean layered design with appropriate abstractions. However, there are several issues ranging from minor gaps to one significant concern that should be addressed before implementation begins.

**Summary:** 8 issues found -- 0 Critical, 2 High, 4 Medium, 2 Low.

---

## Checklist Results

### 1. Every FR Has a Clear Architectural Home -- PASS

All 41 functional requirements from the PRD map to specific architectural components:

| FR Range | Architectural Home | Status |
|----------|-------------------|--------|
| FR1-FR6 (Hardware Detection) | HAL: DeviceManager, ServoProtocol plugins, udev rules | Covered |
| FR7-FR11 (Robot Profiles) | Robot Profile System: YAML loader, Pydantic schema, built-in profiles | Covered |
| FR12-FR14 (Calibration) | Profile System + HAL: calibration storage, validation | Covered |
| FR15-FR18 (Teleoperation) | CLI teleop command + TelemetryStream + HAL | Covered |
| FR19-FR23 (Diagnostics) | Diagnostic Framework: HealthCheck classes, DiagnosticRunner, reporters | Covered |
| FR24-FR27 (Data Collection) | AI Integration Layer: LeRobot bridge, data pipeline | Covered |
| FR28-FR32 (OS and Boot) | OS Layer: live-build ISO, persistent partition, flash script | Covered |
| FR33-FR36 (Dashboard) | UI Layer: CLI, TUI (textual), Web (FastAPI + htmx) | Covered |
| FR37-FR38 (AI Troubleshooting) | AI Integration Layer: Claude Code context files, diagnostic JSON | Covered |
| FR39-FR41 (Extensibility) | HAL plugin architecture, profile YAML schema, plugin directory | Covered |

No orphaned FRs found.

### 2. No Orphaned Architectural Components -- PASS

Every component in the architecture diagram traces back to at least one FR:

- OS Layer --> FR28, FR29, FR30, FR31, FR32
- HAL / DeviceManager --> FR1, FR2, FR3, FR5, FR6
- HAL / ServoProtocol plugins --> FR1, FR2, FR11, FR39
- Robot Profile System --> FR7, FR8, FR9, FR10, FR40
- Diagnostic Framework --> FR19, FR20, FR21, FR22, FR23
- Telemetry Streaming --> FR16, FR20, FR21
- AI Integration / LeRobot bridge --> FR24, FR25, FR26, FR27
- AI Integration / Claude Code --> FR37, FR38
- UI Layer (CLI/TUI/Web) --> FR33, FR34, FR35, FR36

No orphaned components.

### 3. Technology Choices -- PASS (with caveats, see Issue #5)

| Choice | Justification | Consistency |
|--------|--------------|-------------|
| Python 3.12 | ADR-1, matches LeRobot ecosystem, TC4 | Consistent |
| live-build | ADR-2, scriptable, CI-compatible | Consistent |
| click (CLI) | Mature, widely used | Consistent |
| textual (TUI) | Python-native, modern TUI | Consistent |
| FastAPI + htmx (Web) | ADR-6, lightweight, Python-native | Consistent |
| pyudev (device detection) | Standard Linux device monitoring | Consistent |
| Pydantic (validation) | Industry standard for Python data validation | Consistent |
| YAML profiles / JSON calibration | ADR-4, human-readable vs machine-generated | Consistent |

### 4. Migration Path Realism -- PASS

The six-phase migration (A through F) is well-sequenced. Each phase builds cleanly on the previous. The mapping from existing files to new package structure is explicit and complete. The epics document confirms this with a matching dependency graph.

One strength: the architecture correctly identifies that the existing scripts (`diagnose_arms.py`, `monitor_arm.py`, etc.) become the seed code, not throwaway code. This de-risks the migration significantly.

### 5. Plugin Interface Definition -- PASS (with issue, see Issue #1)

The `ServoProtocol` ABC is well-defined with 12 abstract methods (connect, disconnect, ping, read_position, write_position, sync_read_positions, sync_write_positions, get_telemetry, read_register, write_register, enable_torque, disable_torque). The escape hatch (`read_register`/`write_register`) is a good design choice for protocol-specific features.

### 6. Circular Dependencies -- PASS

The dependency flow is strictly top-down:

```
UI Layer --> CLI Commands --> HAL + Diagnostics + AI --> Protocols
```

No layer references a layer above it. The architecture explicitly states: "No layer reaches more than one level down." The epics dependency graph confirms no cycles.

### 7. Performance NFRs Achievability -- PASS (with issue, see Issue #2)

| NFR | Architecture Support | Achievable? |
|-----|---------------------|-------------|
| NFR1: 20ms teleop latency (p95) | Direct serial sync_read/write, Python loop | Yes, with caveats |
| NFR2: 3s bus scan for 12 servos | ServoProtocol.scan() with parallel ping | Yes |
| NFR3: 5s hardware auto-detection | pyudev hotplug + profile matching | Yes |
| NFR4: 10 Hz dashboard telemetry | TelemetryStream with pluggable backends | Yes |
| NFR5: 90s boot time | Pre-built squashfs ISO | Yes |

### 8. HAL Abstraction Cleanliness -- PASS (with issue, see Issue #1)

Adding a new servo protocol requires only: (a) implementing the `ServoProtocol` ABC in a new plugin file, (b) adding a USB vendor/product ID mapping. No core code changes needed. The diagnostic checks and telemetry system all consume the `ServoProtocol` interface, so they work automatically with new plugins.

### 9. Data Flow Clarity -- PASS

The architecture provides explicit data flow diagrams for the two most critical operations:
- **Teleop:** Leader read --> calibration mapping --> safety limits --> follower write, with telemetry branching to stream and optional data recorder. Clear and complete.
- **Diagnostics:** Runner --> checks --> results --> reporters. Clear and complete.

Missing data flows for detect and calibrate are minor -- these are simpler linear flows that are adequately described in the text.

### 10. Error Handling Strategy -- PASS

The architecture addresses serial communication resilience comprehensively:
- Section 10.2: Retry with port flush (derived from real sync_read bug fix)
- Section 10.3: Graceful degradation (single servo failure does not crash session)
- Configurable retry count per profile
- Fault detection in telemetry stream with 2-second alert latency

---

## Issues

### Issue #1: ServoProtocol ABC exceeds NFR18 method count constraint

**Severity:** MEDIUM
**Category:** Interface design vs. stated requirements

The `ServoProtocol` ABC defines 12 abstract methods (connect, disconnect, ping, read_position, write_position, sync_read_positions, sync_write_positions, get_telemetry, read_register, write_register, enable_torque, disable_torque). NFR18 in the PRD specifies "fewer than 10 required methods."

Additionally, the architecture does not include `scan_bus()` in the ABC, but Story 2.2 requires it. If added, the count becomes 13.

**Recommendation:** Either (a) update NFR18 to reflect the actual interface size (~13 methods), which is still reasonable and well under the 500 LOC target, or (b) reduce the ABC by moving `read_register`/`write_register` to an optional mixin (they are escape-hatch methods, not essential for standard operation) and making `get_telemetry` a default implementation that composes individual register reads. This would bring the core ABC to ~9 methods. Add `scan_bus()` either way.

---

### Issue #2: 20ms teleop latency target may be tight with Python GIL

**Severity:** HIGH
**Category:** Performance risk

NFR1 requires teleop loop latency at or below 20ms (p95). The teleop loop performs: sync_read on leader bus (serial I/O) + calibration mapping (CPU) + safety check (CPU) + sync_write on follower bus (serial I/O) + optional telemetry sample (serial I/O).

At 1 Mbaud with 6 servos, a single sync_read takes approximately 2-4ms, and a sync_write takes 2-3ms. This leaves roughly 13-16ms of budget, which seems adequate in isolation. However:
- Python's GIL means telemetry sampling on the same thread could cause jitter.
- The `TelemetryStream` runs at a separate `monitor_hz` rate, but the architecture does not specify whether telemetry reads happen on a separate thread/process or are interleaved in the teleop loop.
- Garbage collection pauses in CPython can spike to 10-20ms.

**Recommendation:** The architecture should explicitly specify that the teleop loop runs on a dedicated thread (or asyncio task) with telemetry sampling on a separate thread. Consider disabling GC during active teleop (`gc.disable()` with periodic manual collection between episodes). Add a latency histogram to the teleop controller for runtime validation of NFR1.

---

### Issue #3: Web dashboard security model conflicts with NFR20

**Severity:** MEDIUM
**Category:** Security consistency

NFR20 states "No listening ports shall be open on a fresh boot." The architecture correctly says the web dashboard is started explicitly with `robotos serve` and is not auto-started. However, the architecture also specifies a `robotos-detect.service` systemd service that runs on boot (Section 13, First Boot Sequence). If this service exposes any IPC mechanism (D-Bus, Unix socket, etc.) that could be reached remotely, it would violate NFR20.

**Recommendation:** Explicitly state that `robotos-detect.service` uses only local Unix domain sockets or D-Bus for IPC, with no TCP/IP listeners. Confirm that the web dashboard's `--bind 0.0.0.0` option generates a warning about network exposure.

---

### Issue #4: Camera subsystem is underspecified in the architecture

**Severity:** HIGH
**Category:** Completeness gap

The PRD includes FR4 (camera detection via V4L2), FR5 (camera-to-role assignment), FR35 (live camera feeds in dashboard), and UJ3 (data collection with cameras). The product brief lists camera support as a core capability. However, the architecture:

- Mentions cameras in the udev rules (line 381-382) and profile YAML (the `hardware.usb_devices` section mentions servo controllers but no camera definition).
- Has no `CameraManager` or equivalent component in the HAL.
- Has no camera-related class in the project structure (`robotos/hal/` has only servo-related modules).
- The data flow diagram for recording shows camera frames but does not show how cameras are discovered, opened, or configured.
- The SO-101 profile example includes no `cameras` section despite the PRD profile definition including camera assignments.

Camera handling is essentially delegated to LeRobot implicitly, but this is not stated, and it creates an architectural gap: if the HAL is supposed to abstract all hardware, cameras are a notable omission.

**Recommendation:** Add a `robotos/hal/camera.py` module with a `CameraManager` class that wraps V4L2 device enumeration (using `v4l2-ctl` or `python-v4l2`). Add a `cameras` section to the profile YAML schema. The camera manager should support: enumerate devices, query capabilities, assign to observation roles, and open video streams. This does not need to be as complex as the servo protocol -- a single concrete class (not an ABC) is sufficient since V4L2 is the universal Linux camera interface.

---

### Issue #5: textual TUI dependency may conflict with offline/ISO size constraints

**Severity:** LOW
**Category:** Technology choice

The `textual` library (TUI framework) pulls in a moderate dependency tree. While the architecture lists it as an optional extra (`[tui]`), the TUI is positioned as the primary MVP interface (Epic 7 is P1 for MVP). If it is optional, the MVP user experience degrades to CLI-only, which contradicts FR34 ("all primary workflows accessible from dashboard without terminal") and SC4 ("zero manual terminal commands").

**Recommendation:** Either (a) make `textual` a core dependency (not optional) since the TUI is essential for the zero-terminal-commands promise, or (b) clearly state that the CLI satisfies FR34 for MVP and the TUI is a usability enhancement. Given the ISO has 16GB to work with (NFR14), the textual dependency (~5MB installed) is negligible.

---

### Issue #6: No explicit concurrency model documented

**Severity:** MEDIUM
**Category:** Architectural clarity

The architecture uses several concurrent patterns without specifying the concurrency model:
- `DeviceManager.watch()` registers callbacks for USB events (implies a background thread or asyncio listener).
- `TelemetryStream.start()` polls at a configurable Hz (implies a background thread or asyncio task).
- The web dashboard uses FastAPI (async) with WebSocket streaming.
- The TUI uses textual (which has its own event loop).

The document does not specify whether the system uses threading, asyncio, or a mix. This ambiguity will cause integration problems when the CLI (synchronous click), TUI (textual event loop), web (asyncio), and telemetry (polling loop) need to coexist.

**Recommendation:** Add a section "Concurrency Model" that specifies:
- Core library functions are synchronous (blocking I/O on serial ports).
- `TelemetryStream` and `DeviceManager.watch()` use `threading.Thread` with daemon threads.
- The web dashboard runs in its own asyncio event loop, calling core functions via `asyncio.to_thread()`.
- The TUI runs in textual's event loop, calling core functions via textual's worker threads.
- The CLI calls core functions directly on the main thread.

---

### Issue #7: Profile schema does not define a JSON Schema for external validation

**Severity:** LOW
**Category:** NFR compliance

NFR17 requires "Human-readable YAML profiles, editable with any text editor, and validate against a published JSON schema." The architecture uses Pydantic models for validation (which is good for runtime), but does not mention generating or publishing a JSON Schema file from the Pydantic models. This is a minor gap since Pydantic v2 can auto-generate JSON Schema, but it should be called out explicitly.

**Recommendation:** Add a note that `robotos profile schema` CLI command will export the JSON Schema generated by `RobotProfile.model_json_schema()`, satisfying NFR17. The schema file should also be shipped in the ISO at `/usr/share/robotos/profile-schema.json` for offline reference.

---

### Issue #8: Missing `flush_port()` in ServoProtocol ABC

**Severity:** MEDIUM
**Category:** Interface completeness

Section 10.2 (Retry and Resilience) shows `protocol.flush_port()` as a critical part of the retry pattern. This method is called between retry attempts to clear stale bytes from the serial buffer -- a lesson learned from the real sync_read bug. However, `flush_port()` is not listed in the `ServoProtocol` ABC definition (Section 4). It exists only in the example code.

If `flush_port()` is not part of the ABC, each plugin must independently decide whether and how to implement buffer flushing, and the generic `resilient_read()` helper cannot call it portably.

**Recommendation:** Add `flush_port()` as an abstract method on `ServoProtocol`, or provide a default implementation in the ABC that calls `self._serial.reset_input_buffer()` (the standard pyserial approach). This ensures the retry pattern works consistently across all plugins.

---

## Cross-Reference Summary

### Architecture vs. PRD Alignment

| PRD Section | Architecture Coverage | Verdict |
|-------------|----------------------|---------|
| Executive Summary | Fully reflected in Section 1 | PASS |
| Success Criteria (SC1-SC8) | All achievable with described architecture | PASS |
| Product Scope (MVP/Growth/Vision) | Migration phases A-F align with MVP/Growth/Vision | PASS |
| User Journeys (UJ1-UJ5) | UJ1-UJ4 fully supported; UJ5 (fleet cloning) deferred to Growth | PASS |
| Domain Model | Architecture implements all entities (Robot, Arm, Servo, etc.) | PASS |
| Functional Requirements (FR1-FR41) | All 41 FRs have architectural homes | PASS |
| Non-Functional Requirements (NFR1-NFR22) | All addressed, NFR1 and NFR18 have risk (Issues #1, #2) | PASS with caveats |
| Technical Constraints (TC1-TC8) | All honored | PASS |

### Architecture vs. Epics Alignment

| Epic | Architecture Component | Verdict |
|------|----------------------|---------|
| Epic 1: Package Skeleton | Section 9 (Project Structure) | PASS |
| Epic 2: HAL - Feetech | Section 4 (HAL) | PASS |
| Epic 3: Profiles - SO-101 | Section 5 (Profile System) | PASS |
| Epic 4: Diagnostics | Section 6 (Diagnostic Framework) | PASS |
| Epic 5: Telemetry | Section 6 (TelemetryStream) | PASS |
| Epic 6: Calibration and Teleop | Section 12 (Data Flows) + Section 4 (HAL) | PASS |
| Epic 7: TUI Launcher | Section 8 (UI Layer - TUI) | PASS |
| Epic 8: USB Image | Sections 3, 13 (OS Layer, Deployment) | PASS |
| Epic 9: AI Integration | Section 7 (AI Integration Layer) | PASS |
| Epic 10: Growth | Sections 4, 5, 8 (plugins, profiles, web) | PASS |

All 10 epics and 40 stories have clear architectural grounding.

### Architecture vs. Product Brief Alignment

| Product Brief Item | Architecture Coverage | Verdict |
|-------------------|----------------------|---------|
| Boot-from-USB | OS Layer with live-build | PASS |
| Hardware Auto-Detection | DeviceManager with pyudev | PASS |
| Universal Robot API | ServoProtocol ABC | PASS |
| AI-Assisted Setup | Claude Code integration via files | PASS |
| Built-in Diagnostics | Diagnostic Framework with 11 checks | PASS |
| Plug-and-Play Profiles | YAML profile system with matcher | PASS |
| Camera support | Underspecified (Issue #4) | FAIL -- needs camera manager |

---

## Issue Summary Table

| # | Issue | Severity | Category | Fix Effort |
|---|-------|----------|----------|------------|
| 1 | ServoProtocol ABC exceeds NFR18 method count; missing scan_bus() | Medium | Interface design | S -- update NFR or refactor ABC |
| 2 | 20ms teleop latency risk with Python GIL and no threading spec | High | Performance | M -- add concurrency specification |
| 3 | robotos-detect.service IPC mechanism unspecified vs. NFR20 | Medium | Security | S -- add clarifying statement |
| 4 | Camera subsystem has no architectural component | High | Completeness | M -- add CameraManager module |
| 5 | textual as optional dep contradicts TUI-as-primary-MVP-UI | Low | Technology choice | S -- make core or clarify scope |
| 6 | No concurrency model documented | Medium | Clarity | M -- add concurrency section |
| 7 | No JSON Schema export for profile validation (NFR17) | Low | NFR compliance | S -- add CLI command and note |
| 8 | flush_port() missing from ServoProtocol ABC | Medium | Interface completeness | S -- add to ABC |

---

## Recommendation

**Proceed with implementation** after addressing the two High-severity issues:

1. **Issue #4 (Camera):** Add a `CameraManager` to the HAL and a `cameras` section to the profile schema. This is a gap that will block UJ3 (data collection) and multiple FRs.

2. **Issue #2 (Teleop latency):** Add an explicit concurrency model section specifying that the teleop loop runs on a dedicated thread, with telemetry on a separate thread. This also resolves Issue #6.

The Medium and Low issues can be addressed during implementation of their respective epics without blocking progress.

---

*Validation report for RobotOS architecture.md v1.0 -- reviewed against PRD, epics, and product brief.*
