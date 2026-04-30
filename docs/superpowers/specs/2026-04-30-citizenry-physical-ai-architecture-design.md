# Citizenry — Auditable Physical-AI Substrate for Manufacturing

**Date:** 2026-04-30
**Author:** Bradley Festraets (Quintinity Ltd) with Claude (Opus 4.7, 1M ctx)
**Status:** Spec — pending user review before plan generation
**Scope:** Umbrella architecture for the entire system. Sub-specs follow.
**Supersedes:** Implicitly extends `docs/specs/2026-04-27-smolvla-citizen-design.md` and `~/lerobot-mcp/docs/specs/2026-04-29-lerobot-mcp-design.md`; does not replace them.

---

## 1. Executive summary

Citizenry today is a working distributed robotics OS — Ed25519-signed mesh, Constitution+Laws governance, marketplace coordination, signed audit ledger, two MCP servers (`citizen_mcp_server` for governance, `lerobot-mcp` for SO-101), an ESP32-S3 first-class citizen with verified crypto interop, and a recorder that writes LeRobotDataset v3 to Hugging Face. ~27 kLOC of Python and ~3.8 kLOC of C++ with 472+ tests. The bones are good and unique.

What it is **not yet**: a credible physical-AI control plane for manufacturing. To be that, it must (a) speak the protocols manufacturers actually deploy (OPC UA Robotics CS 40010, MQTT Sparkplug B / Unified Namespace, VDA 5050 v3, ROS 2 Jazzy bridge), (b) carry the compliance load (EU AI Act Art. 12 lifetime event logging, ISO 10218-1/-2:2025 safety case, IEC 62443 zoning, EU CRA vuln-reporting from 2026-09-11), (c) keep AI strictly *under* a deterministic safety envelope (PL d / SIL 2), and (d) wear an MCP-first agent surface that no incumbent (Formant, Foxglove, Viam, NVIDIA Mission Control) currently offers.

This spec redesigns Citizenry as **the auditable-AI substrate for stationary-manipulator fleets**. It commits to a layered architecture with explicit tier names, a federated MCP topology, per-hardware-class MCP servers (every meaningful SDK function is a typed tool), a hierarchical policy stack (Claude as System-2 planner / SmolVLA as System-1 / deterministic safety filter / motor controller), a signed dataset→policy→fleet provenance chain, and embassy bridges to the industrial standards stack. The existing mesh, Constitution+Laws, marketplace, and Ed25519 ledger become the **load-bearing differentiation** against the competitive landscape — wired together is what nobody else has.

---

## 2. Vision: the country-like construct

Citizenry already uses the language of governance. We make it canonical and add the missing layers.

| Tier | Citizenry concept | Technical realization | Lives at ISA-95 |
|---|---|---|---|
| **Constitution** | Root governance contract — immutable Articles + mutable Laws, signed by ratifying Authority | Constitution v2 JSON, multi-sig amendable, hashed into ledger on every deploy | L3 |
| **Laws** | Mutable policy: torque caps, position envelopes, voltage limits, deadman timeouts, allowed ops per role | `governance/<deployment>_laws.json`, applied at firmware dispatch (XIAO) and at MCP gateway | L2/L3 |
| **Authority** | Whoever may ratify Constitution / amend Laws | Per-deployment signing key set; multi-sig threshold for changes; for now, single Governor key | L3/L4 |
| **Citizens** | Autonomous agents with Ed25519 identity, capabilities, genome, marketplace bids | Existing Citizen base class + per-role specialisations | L1/L2 |
| **Embassies** | Bridges to foreign protocol regimes — OPC UA, Sparkplug B, ROS 2, VDA 5050, MCAP/Foxglove | New: protocol adapters running as Citizens that translate between mesh and external | L2 (north-bound) |
| **Mesh** | Public infrastructure — multicast 239.67.84.90:7770, all messages signed | Existing 7-message protocol | L0/L1 transport |
| **Marketplace** | Capability matchmaking — tasks proposed, citizens bid, co-location bonus | Existing `marketplace.py` + `composition.py` | L2 |
| **Ledger** | National archive — every action signed, hash-chained, optionally Rekor-published for outside audit | Existing `mcp/ledger.py` extended with Sigstore Rekor publication | L3 cross-cutting |
| **Council** | The MCP gateway and dashboard — humans + AI agents propose work, vote, observe, intervene | New: ContextForge-pattern gateway + per-citizen MCP servers + WebRTC console | L2.5/L3 |
| **Tribunal** | Approval UI for any GOVERN-class operation: constitution amendments, dangerous tools, OTA pushes | Existing `mcp/approval_ui` (4-tier) extended | L3 |

The frame is not decorative — it gives every architectural decision a clear locus and a clear authority. When somebody asks "who can do X?" the answer is always one of {Authority, Citizen-with-capability, MCP-client-under-grant, Embassy-with-translation-rights}.

---

## 3. Goals

1. **Make Citizenry credible to manufacturing buyers in 2026.** Speak OPC UA Robotics CS 40010 v1.02, MQTT Sparkplug B 3.0 over a Unified Namespace, ROS 2 Jazzy bridge, VDA 5050 v3 (for AMR-future), MCAP/Foxglove (for observability), and Hugging Face LeRobot Hub (for data/policy round-trip).
2. **Carry the compliance load.** EU AI Act Art. 12 lifetime event logging, ISO 10218-1/-2:2025 safety case, IEC 62443-3-3/4-1/4-2 SDLC, EU CRA vuln-reporting pipeline live by 2026-09-11, ISO/IEC 42001 alignment in 2026.
3. **Keep AI strictly under a deterministic safety envelope.** No VLA output reaches a motor without passing a CBF filter + calibration-aware joint-limit clamp + deadman beacon. The safety layer is independent and certifiable; the policy is replaceable cargo.
4. **Federate MCP, don't fight it.** One MCP server per hardware class on each node, federated through a single per-site gateway (ContextForge-pattern), namespace-prefixed tools, OAuth 2.1+PKCE+RFC 8707 from day one, hard cap ≤15 tools per agent surface.
5. **Wrap every meaningful SDK primitive.** STS3215 register-level access, libcamera/Picamera2 full control set, ESP-IDF camera/wifi/esp-now/mDNS/mbedtls/OTA, JetPack 6.2 jetson-utils/jetson-stats/TensorRT 10.3/DeepStream 7.1, pyserial/pyudev introspection, LeRobot 0.5.x ABCs.
6. **Sign every artefact in the lineage.** Croissant for datasets → MLflow run with OpenLineage facets → CycloneDX 1.6 AIBOM → Sigstore-signed checkpoint in Rekor → ledger-cited at deploy time → mesh-signed action emitted at runtime. Single signed chain end-to-end.
7. **Hierarchical policy stack as the default.** Claude (System-2 planner, language sub-goals at 1–5 Hz) → SmolVLA (System-1 actions at 15–30 Hz on Orin Nano Super) → CBF safety filter (≤1 ms) → controller (200–500 Hz STS3215 sync_write).
8. **Local-first, sovereign.** Every node runs its own MCP, its own ledger shard, its own model weights. Cloud is opt-in for fine-tune compute and dataset hub; offline operation is a first-class mode.
9. **Fix existing smells.** Identity model, MCP unification, survey hardware coverage, unicast plumbing, node-key rotation governance.
10. **Decompose into ship-able sub-projects.** This umbrella spec spawns ~10 sub-specs with their own plans; each sub-project ships in 1–4 weeks.

---

## 4. Non-goals

- **Not building our own VLA.** SmolVLA today, NanoVLA experimental, Pi0/π0.5/GR00T as cloud-side distillation targets when Jetson Thor is on the bench.
- **Not building our own teleop platform.** Embed gst-plugins-rs `webrtcsink` + mediamtx; bring our own thin signaling and UI.
- **Not building our own training loop infra.** Modal / Lambda / Runpod for fine-tune compute; HF Hub as registry.
- **Not building a generic device-management framework.** Scope is LeRobot-supported manipulators + paired cameras + Jetson + ESP-class boards. CNC/mill/lathe interop is via OPC UA companion specs, not native drivers.
- **Not multi-tenant SaaS.** A site has one Constitution, one Authority, one Council. Multi-site federation is a separate problem (Constitution federation), not multi-tenant.
- **Not replacing the mesh with MCP.** The mesh is the substrate; MCP rides on top per-node and is bridged across nodes by the Council gateway.
- **Not chasing a mesh transport SEP for MCP.** Spec consensus April 2026 is "no new transports, only stdio + Streamable HTTP." Bridge instead.

---

## 5. Current state — what to keep, what to fix

### 5.1 Keep (load-bearing existing assets)

- **Mesh and 7-message protocol** (`citizenry/protocol.py`, `transport.py`, `mdns.py`) with Ed25519 signing — keep, harden, add `source_ip`/`source_port` on `Envelope`.
- **Citizen base class and 14-module extended cognition** (skill/genome/immune/mycelium/emotional/will/soul/memory/observation_cache/pain/reflex/metabolism/sleep/spatial/growth) — keep as research surface; do **not** put on the manufacturing-credible critical path. Mark it as the "Soul" sub-system, optional, not affecting safety/compliance.
- **Constitution + Laws + governance/** — keep, evolve to v2 (see §7.4).
- **Marketplace + composition + coordinator** — keep; harden bid-scoring against node-key rotation.
- **Episode recorder v3 + dataset_v3_migrate + hf_upload** — keep; extend with Croissant + AIBOM emission.
- **Ed25519 mesh ledger (`mcp/ledger.py`)** — keep; extend with Sigstore Rekor publication path.
- **lerobot-mcp v1** (20 tools, 8 resources, signed audit, Pydantic, sessions, tasks) — keep; promote to canonical "Bus & Arm MCP" of the per-hardware federation.
- **xiao-citizen** (3.8 kLOC C++, full mesh interop, Ed25519, MJPEG) — keep; promote to canonical "Board-class Citizen" reference implementation.
- **claude-persona-refresh.sh + device_persona.md + per-host CLAUDE.md** — keep; this is the operator-experience differentiator.

### 5.2 Fix (top 5 architectural smells from codebase deep-dive)

| # | Smell | Fix |
|---|---|---|
| 1 | Constitution signed by `governor.key` while MCP signs with `node.key` — two implicit identity authorities | Constitution v2 carries an explicit `authority_pubkey` field. `node.key` becomes transport-only identity ("which machine"); Citizen keys (governor/manipulator/policy/etc.) are **role identities** ("who is acting"). MCP gateway signs with the role key it has been granted, never the node key. |
| 2 | Two MCPs (`citizen_mcp_server.py`, `lerobot-mcp`) with duplicated audit | Promote `lerobot-mcp` to the Bus & Arm MCP. Replace `citizen_mcp_server.py` with a Council Gateway that federates over per-hardware MCPs. Single unified audit at the gateway layer (still local file + Rekor). |
| 3 | `survey.py` only sees USB cameras, fragile sysfs grep for Tegra, libcamera invisible | New survey: `pyudev` for USB, `libcamera-cpp` python bindings for Pi, `jetson_multimedia_api` for Tegra CSI, `lspci`/`ls /dev/hailo*` for accelerators, `mdns` for XIAO/network cameras. |
| 4 | Unicast reply port plumbing partial — `Envelope` lacks `source_ip`/`source_port` | Add fields. Add `Envelope.reply(payload)` helper. Update XIAO C++ envelope to match. |
| 5 | Co-location bonus fragile to node-key rotation | Constitution v2 carries `node_key_version`. Genomes carry `genome_synced_to_node_key_version`. GOVERN(rotate_node_key) message, multi-sig amendable, atomically updates all genomes. |

---

## 6. Approaches considered

### Option A — Federated multi-MCP under a Council Gateway (recommended)

One MCP server per hardware class on each node, federated through a single per-site gateway running on the Surface (Council). Mesh stays the substrate; MCP is the agent surface; gateway translates and routes. Embassies bridge to OPC UA / Sparkplug B / ROS 2 / VDA 5050 / Foxglove. Constitution + Laws + Ledger underpin everything.

- ✅ Matches 2026 production MCP convergence (ContextForge / ToolHive pattern).
- ✅ Bounds tool surface per agent (≤15 tools per role grant via gateway namespacing).
- ✅ Each MCP testable in isolation; each maps cleanly to one SDK.
- ✅ Embassies are pure adapters — keeps the core schema clean.
- ✅ Local-first / offline-capable; gateway can run sovereign per site.
- ⚠ More moving parts than a monolith. Mitigated by the gateway being declarative (ToolHive K8s operator equivalent for lightweight systemd-managed setups).

### Option B — Single mega-MCP wrapping everything

One Python process exposing all tools (bus + cameras + Jetson + Council + embassy bridges).

- ✅ Fewer processes; easier to reason about for v1.
- ❌ Couples lifecycles: a libcamera bug crashes Jetson tools.
- ❌ Tool-sprawl problem: ≥60 tools in one surface, agents lose 70%+ of context (well-documented 2026 anti-pattern).
- ❌ Cannot run partially-offline (e.g., Surface offline but Jetson still operating).
- ❌ Diverges from the 2026 federation convergence; we'd be reinventing what ToolHive/ContextForge already solved.

### Option C — Citizenry-first, no MCP (continue current path)

Keep the mesh as the only agent surface; Claude/Gemini/etc. would drive via custom HTTP shim or by reading state files.

- ✅ No new dependency.
- ❌ Forecloses the lane the competitive scan identified — "MCP-first agent governance for stationary manipulator cells" is the open differentiator.
- ❌ Loses access to the ContextForge / ToolHive / OAuth 2.1+PKCE production patterns. We'd build those ourselves.
- ❌ Doesn't address tool-poisoning and signed-tool-manifest threat (#1 OWASP-MCP-Top-10 in 2026).

**Recommendation: Option A.** It maps directly to where the agentic-AI ecosystem has converged, preserves the existing mesh as the unique differentiator, and keeps each hardware-class MCP small enough to test, audit, and ship independently.

---

## 7. Architecture (chosen design)

### 7.1 Layered model — physical to industrial

```
                         ┌─────────────────────────────────────────────┐
   ISA-95 L4             │  ERP / MES (customer's, not ours)          │
                         └─────────────────────────────────────────────┘
                                        │ AAS submodels (BaSyx)
   ISA-95 L3             ┌─────────────────────────────────────────────┐
   "Council"             │  Council Gateway (Surface):                 │
                         │   - MCP gateway (ContextForge-pattern)      │
                         │   - Authority for Constitution+Laws         │
                         │   - Ledger writer + Rekor publisher         │
                         │   - Embassy host: OPC UA / Sparkplug B      │
                         │   - WebRTC signaling + dashboard            │
                         │   - Compliance pack generator (per release) │
                         └─────────────────────────────────────────────┘
                                        │ mesh (UDP multicast, signed)
                                        │ MCP Streamable HTTP (per-node)
   ISA-95 L2             ┌────────────┐    ┌──────────────────┐
   "Citizens"            │ Pi 5       │    │ Jetson Orin Nano │
                         │ (Sensor +  │    │ Super (Brain)    │
                         │  Vision)   │    │                  │
                         │ MCP:       │    │ MCP:             │
                         │  cam-mcp   │    │  jetson-mcp      │
                         │  bus-mcp   │    │  policy-mcp      │
                         │  usb-mcp   │    │  bus-mcp         │
                         │            │    │  trt-mcp         │
                         └────────────┘    └──────────────────┘
                                │                    │
                                │ libcamera         │ NVMM zero-copy
                                │ Hailo HAT          │ TensorRT 10.3
                                │ STS3215 bus        │ STS3215 bus (other arm)
   ISA-95 L1                    ▼                    ▼
   "Hardware"          ┌────────────────────────────────────────┐
                       │  XIAO ESP32-S3 (board citizen, ed25519)│
                       │  SO-101 follower + leader              │
                       │  Pi NoIR Wide CSI / WiFi MJPEG         │
                       │  STS3215 daisy chains                  │
                       └────────────────────────────────────────┘
   ISA-95 L0                     PTP / gPTP time sync
```

The Council lives at L2.5/L3, reading from the UNS via embassies and dispatching via the mesh. It does **not** sit in the motion-control hot loop — that lives between the policy MCP and the bus MCP, both on the same node.

### 7.2 Node topology and MCP servers

Three node classes today (Surface / Pi / Jetson) plus the XIAO board class. Each gets a fixed MCP server set:

| Node | Role | Local MCP servers |
|---|---|---|
| `surface-lerobot-001` | Council (Authority + Gateway) | **gateway-mcp** (federation), **council-mcp** (Constitution / Laws / Marketplace / Ledger), **embassy-opcua-mcp**, **embassy-sparkplug-mcp**, **embassy-ros2-mcp**, **mcap-mcp** (recording / Foxglove). No model serving. |
| `jetson-orin-001` | Brain | **jetson-mcp** (jetson-utils / jtop / nvpmodel / fan), **trt-mcp** (TensorRT build/run), **policy-mcp** (LeRobot policy server, async inference), **bus-mcp** (this node's STS3215 bus if an arm is attached), **camera-mcp** (CSI cameras if any), **gst-mcp** (NVMM pipelines). |
| `raspberry-lerobot-001` | Sensor + light vision | **camera-mcp** (libcamera/Picamera2 + Hailo EP for face/gesture/object), **bus-mcp** (this node's STS3215 bus if an arm is attached), **xiao-mcp** (proxy to the XIAO board citizen via mesh), **usb-mcp**, **light-policy-mcp** (LiteVLA on Hailo, optional v2). |
| `xiao-cam-*` (XIAO ESP32-S3) | Board citizen | No on-device MCP (resource floor too low). Exposed *to* Claude via the **xiao-mcp** proxy on the Pi. |

Six per-hardware-class MCP servers ship in v1: **bus-mcp, camera-mcp, xiao-mcp, jetson-mcp, usb-mcp, policy-mcp**. Plus three council-class: **gateway-mcp, council-mcp, mcap-mcp**. Plus three embassies: **embassy-opcua-mcp, embassy-sparkplug-mcp, embassy-ros2-mcp** (the ROS 2 embassy is v2; OPC UA + Sparkplug B v1).

Each MCP server's full tool surface is captured in §8.

### 7.3 Council Gateway — the MCP federation seam

Single per-site gateway running on the Surface. Pattern: ContextForge (IBM) at the small end; for our scale, a ~500-LOC FastMCP-based gateway is sufficient. Responsibilities:

- **Aggregate** all per-node MCP servers into one client-facing surface, namespaced (`bus.read`, `cam.capture_jpeg`, `policy.predict`, `council.propose_task`, `embassy_opcua.write_program_state`).
- **Tool Search / RAG-MCP**: hard-cap exposed tools per agent role at ≤15 (2026 best-practice). The full ~120-tool federation is searchable via `search_tools(query)`, exposed dynamically via `get_tool(name)`. A role grant (e.g. `operator`, `safety_engineer`, `dataset_curator`) defines which 10-15 are pinned.
- **Auth**: OAuth 2.1 + PKCE + RFC 8707 Resource Indicators on every remote client. mTLS for in-mesh node-to-gateway. The role grant is signed by the Council with `authority.key`.
- **Audit**: every tool call is logged at the gateway *and* at the per-hardware MCP. Both write to the Ledger; gateway hash-chains them and publishes per-deploy digests to a Sigstore Rekor instance.
- **Tool manifest signing**: each MCP server publishes a signed tool manifest at startup; gateway refuses to federate a server whose manifest doesn't verify. Mitigates OWASP-MCP tool-poisoning.
- **Streaming**: long-running tools (move_arm, safe_dance, train, record_episode) use the Tasks primitive (SEP-1686) with progress + elicitation for safety stops + cancellation.
- **Embassies as MCP servers**: OPC UA, Sparkplug B, ROS 2 are presented to Claude as ordinary MCP servers behind the gateway, namespaced. Outbound traffic to those embassies is also recorded in the Ledger.

Transports: **stdio** for in-process / sidecar MCPs; **Streamable HTTP** for over-mesh MCPs (Pi/Jetson → Surface). No WebSocket, no custom transport (per April 2026 spec consensus).

### 7.4 Identity & trust model — Constitution v2

Three independent identity axes, replacing today's implicit collapse:

1. **Node identity** (`~/.citizenry/node.key`) — "which machine". Used for transport-layer mTLS, mesh source-pubkey on Envelope, co-location bonus in the marketplace. Rotated only on hardware change.
2. **Role identity** (`~/.citizenry/<role>.key`) — "who is acting". Per-citizen Ed25519 keys: `governor.key`, `manipulator.key`, `policy.key`, `recorder.key`, `embassy_opcua.key`, etc. Sign mesh-level actions (PROPOSE, REPORT) and audit-ledger entries.
3. **Authority identity** (`~/.citizenry/authority.key` — multi-sig in v2.1) — "who may govern". Signs Constitution and Laws. Granted to the Governor citizen on the Surface today; multi-sig threshold (e.g. 2-of-3 with offline keys) in v2.1. Must be physically present to amend.

**Constitution v2 wire format additions** (backwards-compatible — old fields preserved, new fields optional with defaults):

```json
{
  "version": "2.0",
  "authority_pubkey": "<hex>",
  "ratified_at": "2026-04-30T00:00:00Z",
  "node_key_version": 1,
  "articles": { /* immutable safety floors */ },
  "laws": { /* mutable policies, signed individually */ },
  "tool_manifest_pinning": { "bus-mcp": "<sha256>", ... },
  "policy_pinning": { "smolvla-pickplace-v3": "<hf_revision_sha>", ... },
  "embassy_topics": { "opcua_namespace": "...", "sparkplug_group_id": "..." },
  "compliance_artefacts": { "aibom_url": "...", "safety_case_url": "...", "rmf_crosswalk_url": "..." },
  "signature": "<authority sig>"
}
```

**GOVERN message types** (extends the existing seventh message kind):
- `GOVERN(amend_law, ...)` — change a Law within a clamp; Authority-signed.
- `GOVERN(rotate_node_key, ...)` — publish new node_key, authoritative for genome update sweep.
- `GOVERN(pin_policy, hf_rev_sha, ...)` — pin or roll back a policy; signed lineage required.
- `GOVERN(pin_tool_manifest, server, sha256, ...)` — pin an MCP server's tool manifest hash.
- `GOVERN(emergency_stop, ...)` — global e-stop broadcast; deterministic safety layer enforces.

### 7.5 Hierarchical policy stack

```
   ┌──────────────────────────────────────────────────────────┐
   │ Operator (human, MCP client) or scheduled task           │
   └──────────────────────────┬───────────────────────────────┘
                              │ MCP tool call: council.propose_task("kit pack A from bin 3 to tray 1")
                              ▼
   ┌──────────────────────────────────────────────────────────┐
   │ S2 Planner — Claude Opus 4.7                             │
   │ • Reads observation summaries + scene description        │
   │ • Emits short language sub-goals at 1-5 Hz               │
   │ • NEVER emits joint targets directly                     │
   └──────────────────────────┬───────────────────────────────┘
                              │ MCP tool call: policy.run_subgoal("pick the red part from bin 3")
                              ▼
   ┌──────────────────────────────────────────────────────────┐
   │ S1 Policy — SmolVLA-450M (LoRA per task) on Orin 8GB     │
   │ • TRT INT8 + async inference + RTC chunking              │
   │ • 15-30 Hz action chunks, fp16/INT8                      │
   │ • LeRobot 0.5.x policy server (gRPC, mTLS)               │
   └──────────────────────────┬───────────────────────────────┘
                              │ Action chunk (joint targets, gripper)
                              ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Safety Filter (deterministic, certifiable, ≤1 ms)        │
   │ • Calibration-aware joint clamp (range_min+50..range_max-50) │
   │ • CBF QP (ellipsoid obstacle / EE) — VLSA / AEGIS pattern│
   │ • Velocity / acceleration clamp                          │
   │ • Force/torque mediation (Present_Current watchdog)      │
   │ • ISO 10218-2 speed-and-separation if cobot              │
   │ • Deadman beacon — drops to safe pose on >100 ms gap     │
   └──────────────────────────┬───────────────────────────────┘
                              │ Filtered action
                              ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Controller — STS3215 sync_write @ 200-500 Hz             │
   │ • One bus_ops worker process per arm                     │
   │ • Owns the /dev/ttyACM* exclusively                      │
   │ • Lease pattern; only the policy hot-loop holds the lease│
   └──────────────────────────────────────────────────────────┘
```

The S2 planner can be Claude (Opus 4.7), Gemini ER 1.6, or any LLM that speaks MCP — they're interchangeable. The S1 policy is currently SmolVLA, with NanoVLA on the experimental track. The safety filter is the **only** non-replaceable layer; it owns the deterministic-correctness story, is certified separately under ISO 10218 / IEC 61508 / IEC 13849, and is what makes the AI legally deployable in EU manufacturing.

### 7.6 Safety architecture

The safety filter is structured so that an audit can verify it independently of the AI policy:

- **Pure function**: `(observation, action_request) → action_filtered | abort`. No state beyond Constitution-pinned limits.
- **Independent process**: runs as its own `safety-mcp` server on the same node as `policy-mcp`. Policy proposes via `policy.predict`, filter consumes via `safety.filter_action(...)`, controller takes only filter-approved outputs.
- **Constitution-pinned**: limits load from the Constitution at startup; refuses to start if Constitution signature doesn't verify.
- **Deadman**: receives a signed heartbeat from Council every 100 ms; on gap drops the latest filtered command and engages "safe pose" (rest configuration from calibration JSON). This implements the ISO 10218-2 protective stop semantics.
- **E-stop**: GOVERN(emergency_stop) message is processed at filter level *and* at the bus-mcp level (defense in depth). Filter outputs zero velocity; bus-mcp disables torque on all motors.
- **Class declaration**: each deployment declares its ISO 10218-1:2025 robot class (Class 1 ≈ PL b reduced-control, Class 2 = full PL d). Constitution carries this; safety filter parameters are clamped accordingly.
- **Force mediation**: STS3215 `Present_Current` is read every loop; over a per-joint threshold the filter aborts and engages safe pose. (This is the watchdog the existing system needs anyway to avoid the 12 V-cycle overload latch.)
- **Calibration-aware**: filter consumes the `~/.cache/huggingface/lerobot/calibration/<robot>.json` directly; if calibration changes mid-run the filter signals abort and asks for re-ratification by Authority.

The safety layer is what we tell a notified body about. The VLA is what we tell the customer about. They are independent.

### 7.7 Audit & provenance — single signed chain

Every step of the dataset → policy → fleet → action lineage is hashed and signed:

```
   ┌──────────────────────────────────────────────────────────┐
   │ Episodes recorded on SO-101 (LeRobotDataset v3, MP4+Parquet)
   │  ↓ each episode's manifest signed by recorder.key        │
   │  ↓ Croissant JSON-LD describing the dataset              │
   │  ↓ pushed to HF Hub (private if sovereign)               │
   ├──────────────────────────────────────────────────────────┤
   │ Fine-tune run on Modal/Lambda (SmolVLA + LoRA)           │
   │  ↓ MLflow run with OpenLineage facets                    │
   │  ↓ inputs pinned by Croissant URLs + content hashes      │
   │  ↓ outputs: safetensors LoRA + model card + AIBOM        │
   ├──────────────────────────────────────────────────────────┤
   │ Artefact signing                                         │
   │  ↓ CycloneDX 1.6 AIBOM (training data + base model + hyperparams)
   │  ↓ Sigstore-signed checkpoint, published to Rekor        │
   │  ↓ Croissant + AIBOM URLs go into Constitution.policy_pinning
   ├──────────────────────────────────────────────────────────┤
   │ Deploy                                                   │
   │  ↓ GOVERN(pin_policy, hf_rev_sha, aibom_url, rekor_log_index)
   │  ↓ Multi-sig if Class 2 cobot                            │
   │  ↓ Constitution amendment hashed into mesh ledger        │
   ├──────────────────────────────────────────────────────────┤
   │ Runtime                                                  │
   │  ↓ Each policy.predict + safety.filter_action + bus_ops.sync_write
   │  ↓ Hash-chained at gateway, signed with role keys        │
   │  ↓ Local SQLite ledger (existing action_ledger.sqlite)   │
   │  ↓ Per-shift digest published to Rekor                   │
   └──────────────────────────────────────────────────────────┘
```

This is the EU AI Act Art. 12 compliant trail and the differentiator vs. Formant/Foxglove/Viam. **Everyone has logs; nobody has a single signed chain end-to-end.**

A `compliance-pack/` artefact is generated per release (CycloneDX SBOM + AIBOM, model card, Croissant dataset descriptor, lineage graph, ISO 10218-2 safety case PDF, NIST AI RMF crosswalk, signed ledger excerpt for the eval window). This is what gets handed to a notified body, an auditor, or an underwriter.

### 7.8 Industrial integration — Embassies

Each embassy is an MCP server bridging mesh and a foreign protocol. All run on the Surface (Council).

- **embassy-opcua-mcp** — Eclipse Milo or open62541-python server exposing the OPC UA Robotics CS 40010 v1.02 information model + Machine Vision CS 40100 nodes. Mesh actions (PROPOSE/REPORT) are mirrored as OPC UA method calls + variable updates. Authentication: certificates (X.509 + Ed25519 binding via custom user-token policy). Security mode: SignAndEncrypt only. Tool surface includes `opcua.read_node(...)`, `opcua.write_node(...)`, `opcua.call_method(...)`, `opcua.subscribe(...)`.
- **embassy-sparkplug-mcp** — Sparkplug B 3.0 publisher/subscriber on the customer's MQTT broker (HiveMQ / EMQX / Ignition). Publishes mesh state to `spBv1.0/<group>/NDATA/<edge_node>/<device>`. Subscribes for write commands. Implements UNS hierarchy. Tool surface: `sparkplug.publish(...)`, `sparkplug.subscribe(topic, ...)`, `sparkplug.list_birth(...)`.
- **embassy-ros2-mcp** (v2 — schedule for Q3 2026) — Bridges to ROS 2 Jazzy via `rclpy`. Publishes selected topics, exposes selected services, hosts an action client. ros-industrial integration target.
- **embassy-vda5050-mcp** (v2 — schedule for Q4 2026 when AMR-class deployment exists) — VDA 5050 v3.0 MQTT contract for AMR fleet manager interop. Compatible with NVIDIA Isaac Mission Control as a peer.

The OPC UA + Sparkplug B embassies are the two non-negotiables for v1: without them the system cannot be plugged into a real factory.

### 7.9 Observability — MCAP, Foxglove, Prometheus, OTel

- **MCAP recording** — every mesh message, every MCP tool call, every observation/action pair is recorded to MCAP files at the `mcap-mcp` server (Surface). MCAP is the de-facto open format and Foxglove-native. `mcap-mcp` exposes tools to start/stop/segment recordings and to publish dataset-grade clips to HF.
- **Foxglove integration** — Foxglove Studio reads our MCAPs directly. We publish a **panel pack** (custom Foxglove panels) for: mesh neighbor map, policy decision timeline, safety-filter abort log, marketplace bid graph, ledger viewer, Constitution diff view. Foxglove becomes the dev-time debugging surface; we don't build our own.
- **Prometheus** — `node_exporter` on Pi, `jetson-stats-node-exporter` on Jetson, custom `citizenry-exporter` on each node (mesh msg rates, ledger lag, marketplace bid latency, policy inference Hz, safety abort count). Grafana dashboards on Surface (Grafana dashboard ID 25079 for Jetson + custom citizenry dashboards).
- **OpenTelemetry** — every MCP tool call and mesh message emits an OTel span; trace context propagates through the gateway. OTel collector on Surface forwards to a customer-chosen sink (Honeycomb / Tempo / Datadog).

### 7.10 Teleoperation — WebRTC + Quest 3

WebRTC stack: `gst-plugins-rs webrtcsink` 0.14.x as producer on each robot node; `mediamtx` 1.x on Surface as the signaling control plane; standard browser as the default client. **Mobile + Quest 3 adapter** is v1.5 (after the gateway and policy-mcp ship): an Open-Teach-style WebXR viewer that reads observation streams and writes pose commands through the gateway, signed and rate-limited.

Latency floor: <80 ms LAN, <200 ms WAN. Audio + thermal camera streams optional. mTLS on signaling, DTLS-SRTP on media.

### 7.11 Physical-AI CI — the round-trip pipeline

```
   record on SO-101 → recorder.key signs episodes → Croissant + manifest
       ↓
   HF Hub push (private repo for sovereignty) — hf_upload.py with retry queue
       ↓
   Modal / Lambda fine-tune job — SmolVLA LoRA, 4-8 h on A100, ~$10/run
       ↓
   MLflow run records OpenLineage facets pointing back to Croissant URL
       ↓
   AIBOM emitted (CycloneDX 1.6) and Sigstore-signed; Rekor entry created
       ↓
   GOVERN(pin_policy, ...) signed by Authority, pushed to mesh, ledger entry
       ↓
   Jetson policy-mcp pulls hf_revision_sha; verifies AIBOM signature; loads
       ↓
   Acceptance test on physical SO-101 (fixed eval episodes); pass→production
       ↓
   Production runs emit signed action ledger; per-shift digest → Rekor
```

This is the closed loop. The whole thing is one signed chain. A buyer asks "where did this policy come from and how do we know?" — we answer in one query.

### 7.12 Local-first / sovereign operation

Every node carries enough state to operate a 24-hour shift with the upstream cloud unreachable:
- Constitution + Laws + role keys cached locally.
- Policy weights cached on the Jetson (HF Hub mirror).
- Episode recordings buffered on Pi/Jetson disk; HF push queues with backoff.
- Ledger sharded per-node; Surface aggregates on reconnection; Rekor publication queues.
- mDNS-only discovery is sufficient — no DNS needed.
- Embassies degrade gracefully: OPC UA stays up because the broker is in the plant; Sparkplug B may queue.

A site can be air-gapped with a single command-line flag (`--sovereign`). Cloud sync becomes opt-in, scheduled, signed.

---

## 8. Component contracts — per-MCP tool surface

Each MCP server gets one section. All tools take and return Pydantic models (JSON Schema auto-emitted). All mutating tools take `confirm: bool` for destructive actions. All long-running tools return a `task_id` and stream progress via the Tasks primitive. All tool calls are audit-logged.

### 8.1 `bus-mcp` — STS3215 / Feetech daisy-chain

Existing `lerobot-mcp v1` is the v1 of this. Surface to extend:

`bus.scan, bus.connect, bus.disconnect, bus.read, bus.write, bus.sync_read, bus.sync_write, bus.ping, bus.reset, bus.action, bus.reg_write, motor.setup, motor.set_baud, motor.set_id, motor.calibrate, motor.record_range_of_motion, motor.torque_enable, motor.torque_disable, motor.set_operating_mode, motor.set_pid, motor.read_status, motor.set_limits, motor.clear_overload, arm.home, arm.move_to, arm.stream_pose, arm.teleop_loop, arm.safe_dance, bus.diagnose_motor, bus.firmware_info`.

(30 tools — exceeds the ≤15 cap; split into a default-15 manifest + a `bus.advanced(query)` tool that surfaces the rest via Tool Search. See §7.3.)

### 8.2 `camera-mcp` — Picamera2 / libcamera (Pi) + OpenCV USB fallback

`cam.list, cam.open, cam.close, cam.configure, cam.set_controls, cam.get_controls, cam.capture_array, cam.capture_buffer, cam.capture_jpeg, cam.start_stream, cam.stop_stream, cam.start_record, cam.stop_record, cam.set_exposure, cam.set_awb, cam.autofocus_trigger, cam.set_focus, cam.set_af_mode, cam.set_hdr, cam.set_flicker, cam.snapshot_metadata, cam.set_crop, cam.preset_load, cam.preset_save`.

Default-15 manifest: open/close/configure/capture_jpeg/start_stream/stop_stream/set_exposure/set_awb/autofocus_trigger/set_hdr/snapshot_metadata/preset_load/preset_save/list/get_controls.

### 8.3 `xiao-mcp` — proxy to ESP32-S3 board citizens

`xiao.list_nodes, xiao.get_status, xiao.snapshot, xiao.stream_start, xiao.stream_stop, xiao.set_pixformat, xiao.set_framesize, xiao.set_sensor, xiao.set_exposure, xiao.set_whitebal, xiao.set_orientation, xiao.ota_push, xiao.reboot, xiao.factory_reset, xiao.sign_message, xiao.peer_send_espnow, xiao.read_partition`.

`ota_push` requires Constitution-pinned firmware signature (Authority-signed Ed25519); rejected otherwise.

### 8.4 `jetson-mcp` — JetPack 6.2 hardware control

`jet.system_info, jet.power_mode_get, jet.power_mode_set, jet.clocks_lock, jet.stats, jet.stats_stream, jet.fan_set, jet.fan_profile_get, jet.processes_top, jet.tegrastats_raw`.

10 tools — fits the cap. Used by Council for thermal management of the brain node.

### 8.5 `trt-mcp` — TensorRT 10.3 build/run/inspect

`trt.build, trt.inspect, trt.benchmark, trt.run`. Long-running (`build`) returns `task_id`. Engine plans cached in `~/.citizenry/trt-cache/`. Used by `policy-mcp` internally; also exposed for one-off model bring-up by operators.

### 8.6 `gst-mcp` — GStreamer NVMM pipelines

`gst.run, gst.preview_csi, nvenc.encode, nvdec.decode, ds.run_config`. Thin wrapper; for surgical tool use only. Not exposed to non-engineer roles.

### 8.7 `usb-mcp` — pyserial / pyudev introspection

`usb.list_ports, usb.find, usb.watch_start, usb.watch_stop, usb.identify, usb.suggest_udev_rule, usb.lock, usb.unlock, usb.lsusb_tree`.

9 tools — fits the cap. Cross-cutting; runs on every node.

### 8.8 `policy-mcp` — LeRobot 0.5.x policy server (Jetson primary)

`policy.list, policy.load, policy.unload, policy.predict, policy.run_subgoal, policy.run_loop, policy.train, transport.serve_async_inference, transport.connect_remote_policy, dataset.create, dataset.record_episode, dataset.push_to_hub, dataset.pull_from_hub, dataset.stats, dataset.edit, robot.list, robot.connect, robot.disconnect, robot.get_observation, robot.send_action, robot.calibrate, teleop.list, teleop.connect, teleop.bind`.

Default-15 manifest: load/unload/predict/run_subgoal/run_loop/dataset.create/dataset.record_episode/dataset.push_to_hub/robot.connect/robot.disconnect/robot.get_observation/robot.send_action/teleop.bind/list/train.

**Important (CVE):** LeRobot 0.5.x gRPC Async Inference had an unauthenticated RCE prior to a patched release. We wrap the server with mTLS *and* an Ed25519-signed envelope header, both checked before unmarshalling. Constitution pins the gRPC server build hash.

### 8.9 `safety-mcp` — deterministic safety filter (NEW, certifiable)

`safety.filter_action, safety.set_class, safety.get_class, safety.engage_safe_pose, safety.deadman_heartbeat, safety.get_limits, safety.acknowledge_e_stop, safety.audit_window`.

8 tools. Runs as its own process. Constitution-pinned limits. No side-effects beyond filter output and audit log. **Independent of the policy.**

### 8.10 `gateway-mcp` — Council gateway (Surface)

`gateway.list_servers, gateway.list_tools, gateway.search_tools, gateway.get_tool, gateway.tool_call, gateway.role_grant, gateway.role_revoke, gateway.audit_window, gateway.health, gateway.federate_peer, gateway.unfederate_peer`.

11 tools. The only MCP a Claude session normally connects to. Everything else is reached via `gateway.tool_call(namespace.tool, args)` plus `gateway.search_tools(query)` for the long tail.

### 8.11 `council-mcp` — Constitution / Laws / Marketplace / Ledger

`council.read_constitution, council.propose_amendment, council.amend_law, council.rotate_node_key, council.pin_policy, council.pin_tool_manifest, council.emergency_stop, council.list_neighbors, council.propose_task, council.bid_inspect, council.assignment_inspect, council.ledger_search, council.ledger_export, council.compliance_pack_build`.

14 tools. Mutating ones (`propose_amendment`, `pin_policy`, `emergency_stop`, etc.) require Authority signature; gateway enforces.

### 8.12 `embassy-opcua-mcp` (v1)

`opcua.read_node, opcua.write_node, opcua.call_method, opcua.subscribe, opcua.unsubscribe, opcua.browse, opcua.bind_robot_state, opcua.bind_camera_state, opcua.export_namespace`.

9 tools. Maps citizenry concepts onto Robotics CS 40010 + Machine Vision CS 40100 information models.

### 8.13 `embassy-sparkplug-mcp` (v1)

`sparkplug.publish, sparkplug.subscribe, sparkplug.list_birth, sparkplug.bind_metric, sparkplug.unbind_metric, sparkplug.uns_view, sparkplug.broker_test`.

7 tools. Publishes mesh state into the customer's UNS at `spBv1.0/<group>/NDATA/<edge_node>/<device>`.

### 8.14 `mcap-mcp` (Council)

`mcap.start_recording, mcap.stop_recording, mcap.list_recordings, mcap.export_clip, mcap.publish_to_hf, mcap.foxglove_link, mcap.replay`.

7 tools. Owns observation logging and dataset extraction.

---

## 9. Data flow — tool call life cycle

A representative end-to-end call:

```
Operator (Claude session, Anthropic Claude Code):
  → gateway.tool_call("council.propose_task",
                      {goal: "kit pack A from bin 3 to tray 1",
                       priority: 5})

Gateway (Surface) checks role grant ("operator"): ✓
  → mTLS to council-mcp (Surface, in-process)
Council:
  → composes Task, broadcasts PROPOSE via mesh
  → policy-mcp on Jetson bids (it has SmolVLA-pickplace-v3 loaded)
  → bus-mcp on the node owning /dev/ttyACM0 (Pi or Jetson) bids
  → marketplace assigns; co-location bonus applies if policy and bus share node_pubkey
  → Council writes ledger: {ts, role=governor.key, action=ASSIGN_TASK, ...}

Policy on Jetson:
  → policy.run_subgoal("pick the red part from bin 3")
  → SmolVLA forward pass on observation (camera-mcp Pi cameras + Jetson CSI)
  → action chunk: 6 joint targets + gripper, 16 frames @ 30 Hz

Safety filter (Jetson, separate process):
  → safety.filter_action(action_chunk)
  → joint clamp ✓; CBF QP ✓; force watchdog ✓; deadman ✓
  → returns filtered chunk
  → audit: {ts, role=safety.key, action=FILTER_OK, hash_in, hash_out}

Bus on Jetson (or Pi, wherever the arm is):
  → bus.sync_write(positions=...)
  → STS3215 daisy chain executes
  → bus_ops emits {ts, role=bus.key, action=SYNC_WRITE, motor_states}

Council ledger writer:
  → hash-chains all of the above into action_ledger.sqlite
  → at end of shift, computes Merkle root, publishes to Sigstore Rekor

Foxglove operator open the live MCAP via mcap.foxglove_link → sees the trace.

OPC UA embassy mirrored:
  → robot state node updated; customer SCADA sees new tray count.
```

Every numbered arrow above is a signed event. Every event is queryable. Nothing is opaque to the auditor.

---

## 10. Migration path — current state to target

Decomposed into 10 sub-projects, sequenced. Each gets its own spec → plan → implementation cycle. Estimated durations are wall-clock for one engineer (plus subagent help) on top of existing work.

| # | Sub-project | Scope | Depends on | Wall |
|---|---|---|---|---|
| **1** | **Constitution v2 + identity model** | New schema, migration of existing constitution.json files, role-key separation, GOVERN message extensions, fix smell #1 | – | 3-5 d |
| **2** | **Mesh hardening** | `Envelope.source_ip`/`source_port` (smell #4), node-key rotation flow (smell #5), updated XIAO C++ envelope | (1) | 2-3 d |
| **3** | **Hardware survey rewrite** | pyudev / libcamera-cpp / jetson_multimedia_api / mDNS-aware survey (smell #3) | – | 2 d |
| **4** | **Council Gateway (gateway-mcp)** | FastMCP-based aggregator, tool manifest signing, OAuth 2.1+PKCE+RFC 8707, Streamable HTTP, role grants, Tool Search/RAG-MCP | (1)(2) | 7-10 d |
| **5** | **Promote lerobot-mcp → bus-mcp** | Rename, conform tool naming, attach to gateway, retire `citizen_mcp_server.py` (smell #2) | (4) | 3 d |
| **6** | **camera-mcp + xiao-mcp + usb-mcp + jetson-mcp + gst-mcp + trt-mcp** | Six per-hardware MCPs per §8 | (4)(5) | 3-4 d each, parallelisable; subagent-friendly |
| **7** | **safety-mcp** | CBF QP filter, calibration-aware clamp, force watchdog, deadman, ISO 10218-2 class declaration; ISO 13849 / IEC 61508 compliance pack | (5) | 7-10 d (+ external review) |
| **8** | **policy-mcp** | LeRobot 0.5.x policy server (mTLS-wrapped), SmolVLA-base loaded, RTC + async inference, hierarchical S2/S1 wiring | (5)(7) | 5-7 d |
| **9** | **Provenance pipeline** | Croissant emission on episode push, AIBOM (CycloneDX 1.6) generation in fine-tune job, Sigstore signing, Rekor publication, GOVERN(pin_policy) flow | (4)(8) | 5-7 d |
| **10** | **embassy-opcua-mcp + embassy-sparkplug-mcp** | OPC UA Robotics CS 40010 v1.02 server, Sparkplug B 3.0 publisher/subscriber + UNS hierarchy | (4) | 5-7 d each |

**Total wall-clock ~10-14 weeks for v1**, with significant parallelism (subagent dispatch). Explicit v1 ends with: Council Gateway live, six per-hardware MCPs federated, hierarchical policy on the SO-101 with deterministic safety filter, full provenance round-trip from one teleop session, OPC UA + Sparkplug B embassies live, compliance pack auto-generated per release.

**v1.5 (next 4 weeks):** WebRTC teleop + Quest 3 adapter, Foxglove panel pack, MCAP-mcp.
**v2 (next quarter):** ROS 2 Jazzy embassy, VDA 5050 v3 embassy, multi-sig Authority, Hailo HAT+ on Pi for backup INT4 SmolVLA, Jetson Thor migration path validated.
**v3:** Multi-site Constitution federation, dataset marketplace, scheduled fine-tune jobs from production drift detection.

---

## 11. Risks and open questions

1. **Tool sprawl**: even with ≤15-per-role caps, the federated surface is ~120 tools. Tool Search / RAG-MCP (Anthropic Tool Search GA) handles this, but model degradation under load needs watching. Mitigation: instrument tool-selection accuracy as a Prometheus metric.
2. **Safety filter certification cost**: ISO 10218 / IEC 13849 compliance is real engineering, not just code. Mitigation: scope `safety-mcp` to ISO 10218-1:2025 Class 1 (≈ PL b reduced control) for v1; defer Class 2 to v2 with a notified body engagement.
3. **STS3215 overload latch on production lines**: 12 V power-cycle as the only reset is unacceptable in a real factory. Mitigation: aggressive force watchdog in `safety-mcp` + Constitution-pinned conservative `Max_Torque_Limit` + `Overload_Torque`. Document the limitation; longer term, evaluate higher-class servos.
4. **EU CRA vuln-reporting playbook**: 24-hour ENISA notice from 2026-09-11. Mitigation: §10/Sub-9 includes the playbook (signed CycloneDX SBOM at every release, ENISA contact pre-registered).
5. **MCP gateway as single point of failure**: the Surface goes down, the Council goes silent. Mitigation: per-node MCPs continue to operate locally on stdio; Council failover is v2 (multi-Surface federation with consensus).
6. **Hugging Face dependency**: HF Hub for datasets and model weights is a single supplier. Mitigation: HF + private mirror on first release; `hf` CLI supports endpoint override; offline-first design tolerates HF outage.
7. **Authority key custody**: today single-key on the Surface. Mitigation: v2.1 brings multi-sig (2-of-3 with offline keys), per ISO/IEC 42001 control alignment.
8. **Surface Pro 7 thermal/age**: i5-1035G4 from 2019 is the Council host. Mitigation: nothing on the model-serving path runs there; if it dies, replacement is any modern x86 box, no porting needed.

---

## 12. Success criteria — v1 acceptance

System is "v1 done" when:

1. Operator runs Claude Code → gateway → council.propose_task("pick a red part from bin 3 and place in tray 1"). Task is bid, assigned, executed end-to-end. **Pass.**
2. Every step of (1) is in the action ledger, signed, and queryable. **Pass.**
3. AIBOM + Croissant + Sigstore-signed checkpoint exist for the policy used in (1); Rekor inclusion verified. **Pass.**
4. ISO 10218-2 protective stop demonstrated: deadman gap >100 ms drops to safe pose. **Pass.**
5. Constitution-pinned `Max_Torque_Limit` enforced: force-watchdog aborts under simulated obstacle. **Pass.**
6. OPC UA Robotics CS 40010 read of robot state from external client returns valid live values. **Pass.**
7. Sparkplug B publish to a HiveMQ test broker; UNS view correct. **Pass.**
8. `compliance-pack/` artefact builds and contains: SBOM, AIBOM, model card, lineage graph, safety case, RMF crosswalk, signed ledger excerpt. **Pass.**
9. Air-gapped mode: full task execution with no internet, all signing/verification still works. **Pass.**
10. Three-node fleet (Surface + Pi + Jetson + XIAO board citizen) demonstrably online for a 24-hour soak with no manual intervention. **Pass.**

---

## 13. References

Primary research dispatched 2026-04-30. Each subagent's full report is preserved in conversation history; this spec cites the strongest signals.

**MCP federation (April 2026):**
- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP 2026 Roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [IBM ContextForge gateway](https://github.com/IBM/mcp-context-forge)
- [Stacklok ToolHive K8s operator](https://docs.stacklok.com/toolhive/guides-k8s/run-mcp-k8s/)
- [State of MCP Security 2026](https://pipelab.org/blog/state-of-mcp-security-2026/)

**VLA models / physical AI 2026:**
- [SmolVLA HF docs](https://huggingface.co/docs/lerobot/smolvla)
- [LeRobot 0.5.0 release](https://huggingface.co/blog/lerobot-release-v050)
- [Pi 0.5 paper](https://arxiv.org/abs/2504.16054)
- [GR00T N1.7 GitHub](https://github.com/NVIDIA/Isaac-GR00T)
- [VLSA / AEGIS safety layer](https://arxiv.org/abs/2512.11891)

**Industrial standards:**
- [OPC UA Robotics CS 40010 v1.02](https://reference.opcfoundation.org/v104/Robotics/docs/)
- [Sparkplug B 3.0.0](https://sparkplug.eclipse.org/specification/version/3.0/documents/sparkplug-specification-3.0.0.pdf)
- [ROS 2 Jazzy LTS](https://www.ros.org/reps/rep-2000.html)
- [Eclipse BaSyx (AAS)](https://eclipse.dev/basyx/)
- [VDA 5050 v3.0](https://github.com/VDA5050/VDA5050)

**Compliance:**
- [EU AI Act Article 12](https://artificialintelligenceact.eu/article/12/)
- [ISO 10218-1:2025](https://www.iso.org/standard/73933.html)
- [ISO/IEC 42001:2023](https://www.iso.org/standard/42001)
- [NIST AI RMF GenAI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [EU Cyber Resilience Act](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act)
- [Sigstore model-transparency](https://github.com/sigstore/model-transparency)
- [CycloneDX 1.6 / AIBOM](https://github.com/manifest-cyber/aibom)
- [Croissant (MLCommons)](https://mlcommons.org/2024/03/croissant_metadata_announce/)

**Edge inference:**
- [JetPack 6.2 Super Mode](https://developer.nvidia.com/blog/nvidia-jetpack-6-2-brings-super-mode-to-nvidia-jetson-orin-nano-and-jetson-orin-nx-modules/)
- [TensorRT 10.x Python API](https://docs.nvidia.com/deeplearning/tensorrt/latest/_static/python-api/infer/)
- [Raspberry Pi AI HAT+ 2 (Hailo-10H)](https://www.raspberrypi.com/news/introducing-the-raspberry-pi-ai-hat-plus-2-generative-ai-on-raspberry-pi-5/)
- [jetson-stats Prometheus](https://pypi.org/project/jetson-stats-node-exporter/)

**Hardware SDKs:**
- [Feetech STS3215 datasheet](https://files.seeedstudio.com/products/Feetech/108090023_STS3215-C001_Datasheet.pdf)
- [LeRobot motors/feetech tables.py](https://github.com/huggingface/lerobot/tree/main/src/lerobot/motors/feetech)
- [libcamera::controls](https://libcamera.org/api-html/namespacelibcamera_1_1controls.html)
- [Picamera2 manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [espressif/esp32-camera](https://github.com/espressif/esp32-camera)
- [ESP-IDF v5.4 reference](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/api-reference/index.html)

**Competitive scan:**
- [Formant](https://formant.io/) | [Foxglove 2.0](https://foxglove.dev/blog/foxglove-2-0-unifying-robotics-observability) | [Viam platform](https://www.viam.com/product/platform-overview) | [NVIDIA Mission Control](https://github.com/nvidia-isaac/isaac_mission_control) | [Open-RMF](https://www.open-rmf.org/) | [Intrinsic / Google Cloud robotics](https://www.intrinsic.ai/blog/posts/intrinsic-joins-google-to-accelerate-physical-ai)

---

*End of architecture spec. Sub-specs to follow per §10.*
