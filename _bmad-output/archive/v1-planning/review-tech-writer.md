# RobotOS USB -- Technical Writer Review and Documentation Strategy

**Reviewer:** Paige (Technical Writer)
**Date:** 2026-03-15
**Status:** Review Complete
**Artifacts Reviewed:** product-brief.md, prd.md, architecture.md, epics.md, sprint-plan.md, README.md, docs/index.md, docs/project-overview.md

---

## Part 1: Cross-Document Review

### 1.1 Structure and Consistency

The five planning artifacts form a coherent pipeline from vision to sprint plan. The traceability is strong: the PRD references success criteria (SC1-SC8), functional requirements trace forward into the epics via an explicit FR Coverage Map, and the sprint plan references story IDs from the epics document. This is well above average for a project at this stage.

**Strengths:**

- The PRD's FR dependency chain is clearly documented and respected in the sprint ordering.
- The epics document includes a full requirements inventory that cross-references both PRD phases (MVP/Growth/Vision) and architecture migration phases (A-F). This dual mapping is valuable.
- User journeys in the PRD are concrete, timestamped, and trace back to success criteria.
- The architecture document includes ADRs (Architecture Decision Records), which will be valuable for future contributors.

**Issues found:**

1. **Product scope terminology drift.** The product-brief uses "Core Capabilities" as a flat list. The PRD uses "MVP (v0.1) / Growth (v0.5) / Vision (v1.0)" as phase names. The epics document maps to architecture migration phases (A-F) AND product phases. The sprint plan only references epics and sprints. A new reader encounters four different organizational schemes across five documents. Recommendation: add a concordance table to the epics document mapping all four schemes together.

2. **Version numbering inconsistency.** The product-brief mentions no version numbers. The PRD defines v0.1, v0.5, v1.0. The sprint plan references "MVP (v0.1)" but the Definition of Done says `robotos --version` prints `0.1.0` (three-part semver). The architecture document references no version numbers. Recommendation: standardize on three-part semver (0.1.0, 0.5.0, 1.0.0) in all documents.

3. **FR3 scope disagreement.** The PRD lists FR3 in the MVP scope (with a note saying "limited to single-profile matching"). The epics requirements inventory marks FR3 as "Growth." The sprint plan does not include FR3 in any MVP sprint. The epics FR Coverage Map shows FR3 only in Story 10.1 (Growth backlog). This means the PRD's MVP scope list is misleading -- FR3 is effectively deferred. Recommendation: update the PRD's MVP scope to remove FR3 or add a clearer "(deferred to Growth -- see Story 10.1)" annotation.

4. **Dashboard terminology.** The PRD references "dashboard" 18 times but does not distinguish between TUI and web dashboard until the MVP scope section. The architecture document defines three UI surfaces (CLI, TUI, Web Dashboard). The epics document correctly scopes TUI to MVP and web to Vision. But the PRD's user journeys (UJ1-UJ5) all say "dashboard" without specifying which. Recommendation: use "TUI dashboard" or "web dashboard" consistently in user journeys to avoid ambiguity.

### 1.2 Terminology Audit

The following terms are used inconsistently or without clear definition across the documents:

| Term | Usage Variations | Recommendation |
|------|-----------------|----------------|
| **Profile** | "robot profile," "profile," "hardware profile," "pre-configured profile" | Standardize on **"robot profile"** everywhere. The domain model defines "Profile" but the casual usage drifts. |
| **HAL** | Used in architecture.md as "Hardware Abstraction Layer (HAL)." Not used in PRD or product-brief. Epics use "Hardware Abstraction Layer" without the acronym. | Define HAL once in the glossary. Use the full phrase on first mention in each document, then HAL thereafter. |
| **Driver** vs. **Plugin** | The architecture uses "Servo Protocol Plugins" and a plugin registry pattern. The PRD uses "protocol drivers" and "driver interface." The product-brief uses "Hardware Drivers." | The architecture's "plugin" is more precise (it describes the registration/discovery pattern). Standardize on **"servo protocol plugin"** for the implementation and **"driver"** only when referring to the OS-level kernel/USB layer. |
| **Config** vs. **Profile** vs. **Configuration** | "robot profile" (YAML hardware description), "configuration" (system config baked into ISO), "config" (CLI command). Three different concepts sharing similar names. | Always qualify: **"robot profile"** (hardware), **"system configuration"** (OS/ISO), **"CLI config"** (user preferences). |
| **Controller** | "servo controller" (the USB-serial adapter), "control station" (the host computer). | Use **"USB-serial adapter"** or **"controller board"** for the hardware. Use **"control station"** or **"host machine"** for the computer. |
| **Bus** | "servo bus" (the half-duplex serial line), "USB bus" (the host USB stack). | Always qualify: **"servo bus"** or **"USB bus."** |
| **Image** | "OS image," "USB image," "ISO image," "pre-built image." | Standardize on **"ISO image"** for the build artifact and **"USB drive"** for the flashed result. |

### 1.3 Accuracy of Existing Documentation

The README.md, docs/index.md, and docs/project-overview.md all describe the **current** linux-usb project (Surface Pro 7 + SO-101 setup tool). None of them mention RobotOS. After the pivot, these documents are outdated.

**Specific issues:**

- **README.md** describes the three-phase Flash/Install/Configure workflow and the AI-driven 5-phase setup. This is the pre-RobotOS architecture. It will be entirely replaced by the RobotOS boot-from-USB model.
- **docs/index.md** describes the project as an "Automation / Provisioning Toolkit" and references generated docs (source-tree-analysis.md, architecture.md, development-guide.md) that describe the old codebase structure.
- **docs/project-overview.md** describes the old diagnostic scripts as standalone Python files, not as part of a `robotos` package.
- **docs/BOOT-GUIDE.md** describes the toram USB install method, which is replaced by the pre-built ISO approach in RobotOS.
- **CLAUDE.md** describes the 5-phase manual setup process, which RobotOS eliminates.

**Recommendation:** Do not update these docs incrementally. They should be frozen as-is until Sprint 6 (USB image), then replaced wholesale with RobotOS documentation. Attempting to keep them accurate during the migration would create constant churn. Add a notice at the top of README.md: "This README describes the legacy linux-usb project. RobotOS documentation is under development."

---

## Part 2: Documentation Architecture

### 2.1 Proposed Documentation Structure

```
docs/
  index.md                     # Landing page and navigation
  getting-started/
    flashing.md                # How to flash the USB image (Windows)
    first-boot.md              # What to expect on first boot
    connecting-hardware.md     # Plugging in servos, cameras
    your-first-teleop.md       # End-to-end tutorial: boot to teleop
  user-guide/
    calibration.md             # Calibration workflow and troubleshooting
    teleoperation.md           # Teleop modes, parameters, safety
    diagnostics.md             # Running diagnostics, reading results
    monitoring.md              # Live telemetry, CSV logging
    data-collection.md         # Recording episodes, dataset management
    tui-dashboard.md           # TUI navigation and shortcuts
    profiles.md                # Understanding and selecting robot profiles
    troubleshooting.md         # Common problems and solutions
  reference/
    cli.md                     # Full CLI reference (all commands, flags)
    profile-schema.md          # YAML profile schema reference
    servo-protocols.md         # Supported protocols and register maps
    api/                       # Auto-generated Python API docs
      index.md
  contributing/
    adding-a-robot-profile.md  # Tutorial: create a new robot profile
    adding-a-servo-protocol.md # Tutorial: implement a new protocol plugin
    development-setup.md       # Dev environment, testing, CI
    architecture.md            # Pointer to planning artifact
  glossary.md                  # Term definitions for target audience
```

### 2.2 Documentation Tooling

**Recommendation: MkDocs with Material theme.**

Rationale:
- Python-native (matches the project language).
- Markdown-based (low barrier for contributors).
- Material theme is the de facto standard for Python project docs.
- Supports auto-generated API docs via `mkdocstrings`.
- Builds to static HTML that can be served offline from the USB image itself.
- Plays well with GitHub Pages for the public-facing docs site.

**Configuration files needed:**
- `mkdocs.yml` at repository root
- `docs/` directory as described above
- GitHub Actions workflow to build and deploy to GitHub Pages

### 2.3 API Documentation Strategy

**Approach: Docstrings plus auto-generation.**

1. All public classes and methods in the `robotos` package must have Google-style docstrings.
2. Use `mkdocstrings` with the Python handler to auto-generate API reference pages.
3. Key interfaces to document thoroughly:
   - `ServoProtocol` ABC (the plugin interface -- this IS the extension point)
   - `RobotProfile` Pydantic model (the profile schema)
   - `TelemetryStream` class (the monitoring interface)
   - `DiagnosticRunner` and `HealthCheck` interface
   - CLI command signatures (auto-generated from Click decorators via `mkdocs-click`)
4. Internal implementation classes get minimal docstrings (one-liner).

**Docstring enforcement:** Add a CI check (e.g., `interrogate`) that fails if public API coverage drops below 90%.

### 2.4 Inline Help (CLI/TUI)

The CLI should be self-documenting:
- Every Click command must have a `help=` string.
- Every Click option/argument must have a `help=` string.
- The TUI should include a help panel accessible via `?` or `F1`.
- Error messages must follow the NFR12 pattern: what failed, probable cause, suggested fix.

This inline help is distinct from the docs site and must be maintained as part of the code, not as separate documentation.

---

## Part 3: MVP Documentation Deliverables

The following documentation must ship with or before the MVP. Items are ordered by when they are needed, not by importance.

### Must Ship WITH MVP

| Document | Sprint | Rationale |
|----------|--------|-----------|
| README.md (rewritten) | Sprint 6 | First thing users and GitHub visitors see. |
| getting-started/flashing.md | Sprint 6 (with 8.3) | Users need this to create the USB. |
| getting-started/first-boot.md | Sprint 6 (with 8.1) | Users need this the moment they boot. |
| getting-started/your-first-teleop.md | Sprint 6 | The golden-path tutorial. Validates SC1. |
| user-guide/tui-dashboard.md | Sprint 6 (with 7.1) | Users land in the TUI; they need to know what to do. |
| reference/cli.md | Sprint 6 | Auto-generated from Click help strings. Low effort if help strings are written. |
| reference/profile-schema.md | Sprint 3 (with 3.1) | Needed for anyone inspecting or modifying the SO-101 profile. |
| glossary.md | Sprint 1 (start), ongoing | Define terms as they are introduced. |
| CHANGELOG.md | Sprint 6 | Release notes for v0.1.0. |

### Should Ship WITH MVP (If Capacity Allows)

| Document | Sprint | Rationale |
|----------|--------|-----------|
| user-guide/calibration.md | Sprint 5 (with 6.1) | Calibration is error-prone; users need guidance. |
| user-guide/diagnostics.md | Sprint 4 (with 4.2) | Diagnostics output is information-dense; needs explanation. |
| user-guide/troubleshooting.md | Sprint 6 | Aggregates known failure modes from CLAUDE.md lessons learned. |
| contributing/development-setup.md | Sprint 1 (with 1.1) | Needed if anyone else joins development. |

### Deferred to Growth Phase

| Document | Rationale |
|----------|-----------|
| contributing/adding-a-robot-profile.md | No multi-profile support in MVP. |
| contributing/adding-a-servo-protocol.md | No plugin architecture in MVP. |
| reference/servo-protocols.md | Only Feetech in MVP; not worth a standalone reference yet. |
| user-guide/data-collection.md | Data collection is MVP but the docs can follow. |

---

## Part 4: Diagrams Needed

The architecture document already contains good ASCII diagrams for the layer stack and system context. The following additional diagrams are needed:

### Must Have (for MVP docs)

1. **Hardware connection diagram.** Physical drawing showing: laptop, USB hub, USB-serial adapters, leader arm, follower arm, cameras. Show which ports connect where. This is the single most common point of confusion for new users. Target: getting-started/connecting-hardware.md.

2. **Data flow: teleop loop.** Show the read-from-leader, write-to-follower cycle with telemetry taps. Include timing annotations (20ms budget). Target: user-guide/teleoperation.md.

3. **State machine: robot operational modes.** Idle -> Calibrating -> Ready -> Teleop -> Recording. Show transitions and what triggers them. Target: user-guide/tui-dashboard.md or reference/cli.md.

4. **Profile structure diagram.** Visual representation of the YAML profile hierarchy (robot -> arms -> servos, cameras, calibration). Target: reference/profile-schema.md.

### Nice to Have (for Growth docs)

5. **Plugin registration flow.** How a new ServoProtocol plugin is discovered and loaded.
6. **USB boot sequence.** BIOS -> GRUB -> systemd -> robotos-detect.service -> TUI.
7. **Data collection pipeline.** Servo data + camera frames -> episode -> dataset -> HuggingFace Hub.

**Diagram format recommendation:** Use Mermaid in Markdown files. MkDocs Material supports Mermaid natively. This keeps diagrams version-controlled and editable without external tools.

---

## Part 5: README Rewrite Specification

The current README must be completely rewritten for RobotOS. Here is the recommended structure:

```markdown
# RobotOS

> A bootable USB operating system for robot arms. Plug in, boot up, start teleoperating.

## What Is This?

Two sentences: what it does, who it is for.

## Quick Start

1. Download the ISO from Releases
2. Flash to USB (link to flashing guide)
3. Boot from USB
4. Connect your robot arm
5. Follow the TUI prompts

## Supported Hardware

Table: robot platforms, servo protocols, tested host machines.

## Features

Bullet list: auto-detection, diagnostics, teleoperation, data collection, TUI dashboard, offline operation.

## Documentation

Link to docs site (or docs/ directory).

## Screenshots / Demo

TUI screenshot. Optional: short GIF of teleop in action.

## Contributing

Link to contributing guide.

## License

License statement.
```

**Key changes from current README:**
- Remove all Surface Pro 7-specific content.
- Remove the 5-phase setup process (RobotOS eliminates it).
- Remove Windows flash.ps1 instructions (replaced by generic ISO flashing).
- Add supported hardware table.
- Add link to documentation site.
- Focus on the "30-second understanding" -- a visitor should know what this project does within 10 seconds of landing on the page.

---

## Part 6: Glossary -- Terms Requiring Definition

The following terms should be defined in `docs/glossary.md` for the target audience (hobbyists, educators, researchers who may not have Linux or servo expertise):

| Term | Why It Needs Definition |
|------|------------------------|
| **Servo** | Target users may confuse with RC hobby servos. RobotOS servos are smart actuators with feedback. |
| **Servo bus** | Half-duplex serial communication line. Not obvious what "bus" means in this context. |
| **Leader-follower teleoperation** | The core interaction model. Needs a clear explanation with diagram. |
| **Robot profile** | RobotOS-specific concept. Users need to understand what it contains and why it matters. |
| **Calibration** | What it means in the servo context (not camera calibration). Why it is needed. |
| **HAL (Hardware Abstraction Layer)** | Technical term used in architecture. Contributors need to understand it. |
| **USB-serial adapter** | The CH340/FTDI/CP2102 board. Users see a small green PCB; they need to know what it does. |
| **udev** | Linux device management. Users do not need to understand it, but they will see it in logs. |
| **V4L2** | Video for Linux. Users may see this in camera error messages. |
| **UEFI** | Users need to know this to access the boot menu. |
| **Episode** | A single demonstration recording in the LeRobot data format. |
| **Dataset** | A collection of episodes. |
| **Protection threshold** | Servo safety limits (temperature, voltage, load). Critical for hardware safety. |
| **Sync read/write** | Batch servo communication. Appears in error messages. |
| **Overload** | Servo protection mode that disables torque. Users will encounter this. |

---

## Part 7: Documentation Roadmap

Aligned with the sprint plan from the sprint-plan.md artifact.

### Sprint 1 (Weeks 1-2): Foundation

- [ ] Initialize `mkdocs.yml` with Material theme configuration.
- [ ] Create `docs/glossary.md` with initial term list (from Part 6 above).
- [ ] Create `contributing/development-setup.md` covering `pip install -e .` workflow.
- [ ] Write docstring standards document (Google style, minimum coverage requirements).
- [ ] Add deprecation notice to current README.md.

### Sprint 2 (Weeks 3-4): HAL Documentation

- [ ] Write docstrings for `ServoProtocol` ABC and all public methods.
- [ ] Write docstrings for `FeetechPlugin` class.
- [ ] Add architecture overview to `docs/` (adapted from planning artifact, simplified for contributors).
- [ ] Update glossary with servo-specific terms (bus, sync read, overload, etc.).

### Sprint 3 (Weeks 5-6): Profile Documentation

- [ ] Write `reference/profile-schema.md` documenting the YAML schema with annotated examples.
- [ ] Write docstrings for `RobotProfile` Pydantic model.
- [ ] Create the profile structure diagram (Mermaid).
- [ ] Update glossary with profile-related terms.

### Sprint 4 (Weeks 7-8): Diagnostics Documentation

- [ ] Write `user-guide/diagnostics.md` explaining each diagnostic check and how to interpret results.
- [ ] Write `user-guide/monitoring.md` covering telemetry output and CSV logging.
- [ ] Write docstrings for `DiagnosticRunner`, `HealthCheck`, `TelemetryStream`.
- [ ] Create the teleop data flow diagram (Mermaid).

### Sprint 5 (Weeks 9-10): User-Facing Docs

- [ ] Write `user-guide/calibration.md` with step-by-step instructions.
- [ ] Write `user-guide/teleoperation.md` covering modes, safety, and parameters.
- [ ] Create the hardware connection diagram.
- [ ] Create the robot state machine diagram.
- [ ] Write CLI help strings for all `robotos` commands (inline in code).

### Sprint 6 (Weeks 11-12+): Ship-Ready Docs

- [ ] Rewrite `README.md` per the specification in Part 5.
- [ ] Write `getting-started/flashing.md`.
- [ ] Write `getting-started/first-boot.md`.
- [ ] Write `getting-started/your-first-teleop.md` (the golden-path tutorial).
- [ ] Write `user-guide/tui-dashboard.md`.
- [ ] Write `user-guide/troubleshooting.md` (migrate knowledge from CLAUDE.md lessons learned).
- [ ] Auto-generate `reference/cli.md` from Click help strings.
- [ ] Auto-generate `reference/api/` from docstrings via mkdocstrings.
- [ ] Write `CHANGELOG.md` for v0.1.0.
- [ ] Replace `docs/index.md` with new landing page.
- [ ] Remove or archive old docs (BOOT-GUIDE.md, old project-overview.md, old architecture.md).
- [ ] Final glossary review and completeness check.
- [ ] Build and deploy docs site to GitHub Pages.

### Post-MVP (Growth Phase)

- [ ] Write `contributing/adding-a-robot-profile.md` (when multi-profile ships).
- [ ] Write `contributing/adding-a-servo-protocol.md` (when plugin architecture ships).
- [ ] Write `reference/servo-protocols.md` (when Dynamixel support ships).
- [ ] Write `user-guide/data-collection.md` with full workflow documentation.
- [ ] Add tutorial videos or GIFs to getting-started guides.

---

## Part 8: Risks and Recommendations

### Risk 1: Documentation debt accumulates during Sprints 2-5

The sprint plan is heavily weighted toward implementation. If documentation is treated as "Sprint 6 work," five sprints of undocumented code will create a large catch-up burden. The docstring standards and inline help strings should be part of the Definition of Done for every story, not a separate documentation sprint.

**Recommendation:** Add to every story's acceptance criteria: "All public classes and methods have Google-style docstrings. All CLI commands have help strings."

### Risk 2: Sprint 6 is already overloaded (33 weight points)

Sprint 6 carries the TUI, USB image, AI integration, AND the documentation deliverables. The documentation work listed above is approximately 2-3 weeks of writing effort. If Sprint 6 is already splitting into 6a/6b, documentation may slip past MVP.

**Recommendation:** Start the getting-started guides and README rewrite in Sprint 5, not Sprint 6. The content depends on knowing how the system works (which is stable by Sprint 5), not on the USB image being built.

### Risk 3: No one is assigned to documentation

The planning artifacts name agents for product, architecture, and scrum, but no one is explicitly responsible for documentation. Documentation without an owner does not get written.

**Recommendation:** Assign documentation ownership. Either the tech writer reviews every PR for docs impact, or each sprint includes a specific documentation story with acceptance criteria.

### Risk 4: Old docs will confuse contributors during the transition

The current README, docs/index.md, and docs/project-overview.md all describe the legacy project. During Sprints 1-5, new contributors (or AI agents reading the repo) will see conflicting information.

**Recommendation:** Add a deprecation banner to README.md immediately: "This project is being restructured as RobotOS. Planning documents are in `_bmad-output/planning-artifacts/`. The documentation below describes the legacy setup and will be replaced."

---

## Summary of Action Items

| Priority | Action | When |
|----------|--------|------|
| **P0** | Add docstring + help string requirements to story DoD | Before Sprint 1 |
| **P0** | Add deprecation notice to README.md | Immediately |
| **P0** | Initialize mkdocs.yml and docs skeleton | Sprint 1 |
| **P0** | Write getting-started golden-path tutorial | Sprint 5 (not Sprint 6) |
| **P0** | Rewrite README.md | Sprint 5-6 |
| **P1** | Create glossary.md | Sprint 1, maintain ongoing |
| **P1** | Write profile schema reference | Sprint 3 |
| **P1** | Create hardware connection diagram | Sprint 5 |
| **P1** | Assign documentation ownership | Before Sprint 1 |
| **P2** | Set up mkdocstrings for API auto-generation | Sprint 4 |
| **P2** | Set up GitHub Pages deployment | Sprint 6 |
| **P2** | Write contributing guides | Growth phase |

---

_Documentation strategy and review for RobotOS USB -- prepared by Paige (Technical Writer)._
