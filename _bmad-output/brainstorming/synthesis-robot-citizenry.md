# The armOS Citizenry

**A Vision for Distributed Autonomous Robot Agents**

*Synthesized from 200+ ideas across 6 brainstorming techniques and a distributed robotics research survey.*
*Date: 2026-03-15*

---

## The Name: Citizenry

Not "swarm" -- that implies mindless replication. Not "hive" -- that implies a queen. Not "fleet" -- that implies central dispatch. Not "mesh" -- that is an implementation detail.

**Citizenry.**

A citizenry is a body of individuals, each with identity and autonomy, bound by a shared constitution, contributing to and benefiting from a collective. Citizens have rights. Citizens have responsibilities. Citizens can refuse. Citizens can leave. Citizens govern themselves.

The word matters because it encodes the architecture: decentralized identity, constitutional safety, voluntary cooperation, emergent capability. Every design decision flows from asking "what would a citizen do?"

armOS v1.0 builds the first citizen. The Citizenry is what happens when citizens find each other.

---

## The Architecture in One Page

```
+=====================================================================+
|                          THE NATION                                  |
|  User's complete fleet across all locations                          |
|  Identity: Governor's Ed25519 keypair                                |
|  Governance: Constitution + Laws + Priorities                        |
|  Communication: Zenoh over WireGuard VPN between provinces           |
|                                                                      |
|  +-------------------------------+  +-----------------------------+  |
|  |       NEIGHBORHOOD A          |  |      NEIGHBORHOOD B         |  |
|  |   (Home office -- same LAN)   |  |  (School lab -- same LAN)   |  |
|  |                               |  |                             |  |
|  |  +--------+  +--------+      |  |  +--------+  +--------+    |  |
|  |  |Citizen |  |Citizen |      |  |  |Citizen |  |Citizen |    |  |
|  |  |Surface |  |Follower|      |  |  |  Pi 5  |  |Follower|    |  |
|  |  | Pro 7  |  | Arm    |      |  |  |        |  | Arm #2 |    |  |
|  |  |--------|  |--------|      |  |  |--------|  |--------|    |  |
|  |  |compute |  |actuate |      |  |  |compute |  |actuate |    |  |
|  |  |govern  |  |sense   |      |  |  |relay   |  |sense   |    |  |
|  |  |sense   |  |        |      |  |  |        |  |        |    |  |
|  |  +--------+  +--------+      |  |  +--------+  +--------+    |  |
|  |       |           |          |  |       |           |        |  |
|  |  +--------+  +--------+      |  |  +--------+                |  |
|  |  |Citizen |  |Citizen |      |  |  |Citizen |                |  |
|  |  |USB Cam |  |Leader  |      |  |  |USB Cam |                |  |
|  |  |        |  | Arm    |      |  |  |        |                |  |
|  |  |--------|  |--------|      |  |  |--------|                |  |
|  |  |sense   |  |actuate |      |  |  |sense   |                |  |
|  |  |        |  |sense   |      |  |  |        |                |  |
|  |  +--------+  +--------+      |  |  +--------+                |  |
|  |                               |  |                             |  |
|  |  Discovery: mDNS + UDP       |  |  Discovery: mDNS + UDP     |  |
|  |  Comms: Zenoh on LAN         |  |  Comms: Zenoh on LAN       |  |
|  +-------------------------------+  +-----------------------------+  |
|                                                                      |
|  Embassy: Pi running WireGuard at each location                      |
+=====================================================================+
```

### Three Layers

**Citizen** -- A single device with a cryptographic identity, self-assessed capabilities, and local autonomy. The minimum viable citizen is an identity, one capability, and a heartbeat. An SO-101 arm is a citizen. A USB camera is a citizen. A Surface Pro running inference is a citizen. A temperature sensor with a keypair is a citizen.

**Neighborhood** -- Devices on the same local network that can discover each other via mDNS and communicate with sub-50ms latency. A neighborhood is what you can see and touch. It is the mycelium network: warnings propagate instantly, resources are shared directly, collaboration is physical. A neighborhood operates autonomously even if the nation goes dark.

**Nation** -- The user's complete fleet across all locations, bound by a shared constitution signed with the governor's key. Neighborhoods connect through embassies (always-on relay nodes over WireGuard VPN). The nation is the scope of governance, identity, and collective learning. Laws, reputation, and learned behaviors flow at the nation level.

### The Minimum Viable Protocol: 7 Messages

Every interaction between citizens reduces to one of seven message types. No pub/sub topics, no service calls, no action servers. Seven messages, all JSON, all signed, all with TTL.

| # | Message | Purpose | Example |
|---|---------|---------|---------|
| 1 | `HEARTBEAT` | "I exist, here is my state" | `{state: "idle", health: 0.95, load: 0.12}` |
| 2 | `DISCOVER` | "Who is out there?" | Broadcast on join or periodically |
| 3 | `ADVERTISE` | "Here is what I can do" | Capability list, dynamic health, availability |
| 4 | `PROPOSE` | "I think we should do X" | Task descriptor with constraints |
| 5 | `ACCEPT/REJECT` | "I will/won't do X" | Bid with estimated cost, or refusal with reason |
| 6 | `REPORT` | "Here is what happened" | Task result, sensor event, fault alert |
| 7 | `GOVERN` | "New policy from the governor" | Constitution update, law change, permission grant |

Every message carries: protocol version, type, sender's public key, recipient (or `*` for broadcast), timestamp, TTL, cryptographic signature, and a typed body. A heartbeat fits in 200 bytes. A capability advertisement fits in 1KB. The protocol is transport-agnostic -- it works over UDP multicast, Bluetooth LE, USB serial, or Zenoh.

Safety-critical messages (GOVERN with stop commands, REPORT with fault alerts) have TTLs of 2-5 seconds. Stale movement commands are discarded, never executed. Policy updates have TTLs of 3600 seconds. The conservative action always wins: if one citizen says "stop" and another says "go," stop wins.

---

## The Top 20 Ideas

Ranked by the intersection of impact (how much it changes what the system can do) and feasibility (can it be built with today's tools by a small team).

### Tier 1: Foundation (Build These First)

**1. Cryptographic Citizen Identity (DID)**
*Sources: First Principles #1, Cross-Pollination #1, Metaphor Mapping #1*

Every device generates an Ed25519 keypair at first boot. The public key IS the identity -- not an IP address, not a MAC address. The DID document advertises capabilities, firmware version, and safety envelope. Identity is portable: move a servo controller to a new USB port, and it is still the same citizen. Identity is verifiable: every message is signed, every claim is attributable.

This is the foundation. Without unforgeable identity, there is no trust, no reputation, no governance. With it, everything else becomes possible.

**Impact: 10/10. Feasibility: 9/10.** Ed25519 key generation is one function call. DID documents are JSON. The hard part is key storage on constrained devices -- but even a file on the SD card works for v1.

---

**2. The 7-Message Protocol**
*Source: First Principles #23*

Seven message types, transport-agnostic, human-readable JSON, self-describing, small. This is the TCP/IP of robot citizenry -- simple enough to implement on a microcontroller, expressive enough to coordinate a nation.

The protocol's power is in what it excludes. No streaming. No RPC. No topics. Streaming happens over side channels (Zenoh, shared memory, direct USB). The 7-message protocol handles coordination, governance, and discovery. Keeping it minimal means any device that can send and receive JSON can be a citizen.

**Impact: 10/10. Feasibility: 9/10.** A reference implementation in Python is a weekend. The hard part is getting the message schemas right -- that requires iterating with real devices.

---

**3. Capability Waggle Dance (mDNS Advertisement)**
*Sources: Biomimetic #5, Research: Matter/Thread commissioning*

When a citizen joins a neighborhood, it performs a waggle dance: a structured broadcast announcing its identity, type, capabilities, sensors, power state, health score, and availability. Every citizen on the network listens for waggle dances and maintains a local neighbor table. No central registry.

This borrows Matter/Thread's commissioning UX: plug in a new device, it announces itself, the governor's phone buzzes "New device detected: Robot Arm (SO-101). Add to your country? [Yes] [No]." One tap. Done. The technical mechanism is mDNS + a UDP broadcast of the ADVERTISE message. Discovery takes under a second on a local network.

**Impact: 9/10. Feasibility: 9/10.** mDNS libraries exist for every platform. The innovation is the standardized capability schema, not the discovery mechanism.

---

**4. Constitutional Governance**
*Sources: Metaphor Mapping #1-5, First Principles #3, #6*

The constitution is a small signed JSON document that every citizen carries. It encodes safety constraints that no command -- not even from the governor -- can override:

- Article I: No command may cause physical harm to humans or destruction of another citizen.
- Article II: The governor can always halt, override, or recall any citizen.
- Article III: A citizen must protect its own hardware (servo overload protection, thermal shutdown).
- Article IV: Every citizen must truthfully report its state. No spoofing.
- Article V: Learned behaviors belong to the collective.

Laws are mutable policies the governor sets: "cameras record when motion is detected," "arms return to home position after 5 minutes idle." Laws can be changed. The constitution cannot, except through a formal amendment process with human confirmation and a cooling-off period for safety-critical changes.

The separation of powers is real: the planner (legislative) decides what to do, the executor (executive) does it, and the safety watchdog (judicial) can veto any action in real-time. They run as independent processes. The safety watchdog has higher thread priority. If the planner and executor crash, the watchdog still holds.

**Impact: 9/10. Feasibility: 8/10.** The document format is trivial. The enforcement at the hardware level (writing max-torque limits to servo EEPROM during onboarding, for example) is what makes it real.

---

**5. Octopus-Inspired Distributed Intelligence**
*Sources: Biomimetic #30-33, Research: Octopus-Inspired Distributed Control (arXiv 2603.10198)*

An octopus has 500 million neurons and two-thirds of them live in the arms. Apply this directly: each SO-101 arm runs its own local agent handling servo protection, basic reflexes, calibration, and trajectory smoothing. The Surface Pro (the "brain") handles planning, coordination, and learning -- but the arms operate semi-autonomously if the brain goes offline.

Hardcoded reflexes that the brain cannot override:
- Overcurrent reflex: total arm current exceeds 4A -> reduce all joint velocities 50% immediately
- Collision reflex: any joint hits a hard stop -> reverse 5 degrees and hold
- Thermal reflex: any servo temp > 65C -> max 25% speed

These reflexes prevent the exact failure modes documented during setup: voltage collapse from PSU current limiting, elbow overload protection tripping, thermal runaway. Safety decisions happen at the limb in under 1ms. The brain learns about them after the fact.

**Impact: 9/10. Feasibility: 8/10.** The reflexes are simple conditional logic on servo telemetry. The key enabler is reading servo registers at high frequency (the STS3215 supports 1kHz) and acting locally.

---

### Tier 2: Collaboration (Build These After Foundation)

**6. Digital Pheromone DHT for Capability Scoring**
*Source: Biomimetic #1-4*

Each citizen publishes a capability-weighted score to a shared distributed hash table that decays over time, like evaporating pheromones. A citizen that just completed 50 successful pick-and-place tasks publishes `{"skill": "pick_place", "confidence": 0.94, "ttl": 3600}`. Other citizens querying "who can pick and place?" find this entry and route tasks accordingly. Scores decay -- if the citizen goes offline or stops performing, its pheromone evaporates.

This replaces central task assignment with emergent allocation. The Surface Pro does not tell the follower arm to collect data. It publishes a task descriptor ("food source"). Arms that are idle and have matching capabilities detect the gradient and walk toward the task. No scheduler needed.

**Impact: 8/10. Feasibility: 7/10.** A DHT for 5-50 devices is simple (even an in-memory gossip protocol works). The innovation is the decay function and the routing semantics.

---

**7. Immune System Security Model**
*Sources: Biomimetic #21-25, First Principles #4-6, #10-12*

Self/non-self recognition: legitimate citizens have known public keys. An unknown device can announce capabilities but cannot issue commands or receive sensitive data until the governor approves it. Rogue agents are quarantined, not crashed.

Danger signal broadcasting: when a servo detects anomalies that do not match known fault patterns (unexpected register values, sudden sensor noise), it emits a danger signal that activates heightened monitoring across the neighborhood.

Immune memory: when the mesh recovers from a fault (voltage collapse from insufficient PSU current), it creates an immune memory entry. This memory is shared across the nation. A new arm joining the citizenry inherits all learned fault patterns -- it does not have to experience the voltage collapse itself.

Graduated inflammatory response: local (servo adjusts its own protection) -> regional (neighboring joints compensate) -> systemic (entire arm enters protective mode) -> mesh-wide (other citizens warned, governor notified). Each level triggers only if the previous level fails.

**Impact: 8/10. Feasibility: 7/10.** Statistical bounds on telemetry are learned during calibration. The graduated response is a state machine. Immune memory is a shared JSON database. The challenge is tuning the sensitivity -- too sensitive means false alarms, too lax means missed faults.

---

**8. Claude Agent -> Robot Citizen Mapping**
*Sources: First Principles #20-22, Cross-Pollination #44-48, Metaphor Mapping #31-35*

The mapping is not metaphorical. It is architectural.

| Claude Agent | Robot Citizen |
|---|---|
| Tools (Bash, Read, Edit) | Capabilities (move, sense, compute) |
| Context window | Situational awareness (sensors + neighbor state + recent history) |
| System prompt (CLAUDE.md) | Constitution + current laws |
| Persistent memory (MEMORY.md) | Learned behaviors, calibration, fault history |
| Skills (slash commands) | Composed behaviors (/pick-and-place, /wave, /sort) |
| Tool results | Sensor readings and action outcomes |
| Temperature setting | Autonomy level (conservative 0.0 to exploratory 1.0) |
| Token budget | Energy budget, compute budget, time budget |
| Subagent spawning | Task delegation to nearby citizens |
| Error handling / retries | Fault recovery (retry, re-plan, ask for help) |

A robot citizen IS a Claude agent with a body. The system prompt is the constitution. The tools are actuators and sensors. The context window is spatial awareness with a finite budget. Memory persists across sessions. Skills compose into complex behaviors. When Claude's agent framework gains new capabilities -- better tool use, persistent memory, multi-agent coordination -- robot citizens inherit them directly.

Capable citizens (RPi 5+, Jetson, Surface Pro) can run a local LLM (Phi-3-mini, Gemma 2B) as their reasoning engine. The LLM receives the constitution as system prompt, sensor readings as context, and produces decisions as tool calls. This is literally the Claude agent architecture instantiated on a robot.

**Impact: 9/10. Feasibility: 7/10.** The mapping guides every design decision. The local LLM capability is the long-term play; in v1, the Surface Pro runs the LLM for the entire neighborhood.

---

**9. Skill Trees and XP**
*Source: Cross-Pollination #22*

Citizens gain experience points from successful task completions. XP unlocks capabilities in a skill tree: start with `basic_grasp`, unlock `precision_grasp` after 100 successful grasps, unlock `tool_use` after 50 precision grasps. The skill tree is a DAG stored in config. XP is awarded: `base_xp * task_difficulty * success_quality`.

This is not gamification for its own sake. It solves a real problem: how does a citizen know what it is capable of? A citizen that has never picked up a glass should not bid on "serve drinks." The skill tree provides a principled answer: you have not earned that skill yet. It also creates a natural ramp for autonomous operation -- low-XP citizens require more supervision.

**Impact: 7/10. Feasibility: 8/10.** A DAG config plus a counter per node. The hard part is defining meaningful skill trees for manipulation tasks.

---

**10. Task Marketplace with Auction**
*Sources: Cross-Pollination #50, What-If #4.1, First Principles #2*

When a goal arrives, it is broadcast as a PROPOSE message. Citizens bid based on capability (skill tree level), proximity, current load, energy state, and fatigue. The bid with the best composite score wins. Deterministic tiebreak: lower public-key hash wins. No coordinator needed for simple tasks; a coordinator citizen handles multi-step tasks by decomposing them into marketplace listings.

The marketplace subsumes task scheduling, load balancing, and failover into a single mechanism. If a citizen fails mid-task, the task re-enters the marketplace. If a new citizen joins with better capabilities, it naturally wins future auctions. The system self-optimizes through market dynamics.

**Impact: 8/10. Feasibility: 7/10.** Auction protocols for small groups are well-studied. The challenge is defining the scoring function that correctly weights capability, proximity, and availability.

---

### Tier 3: Intelligence (Build These When the Foundation is Solid)

**11. Telemetry Warning Propagation (Mycelium Network)**
*Source: Biomimetic #9, #12*

When a servo detects voltage collapse (12V dropping to 5V -- the exact PSU current-limit scenario from setup), it publishes a warning to the neighborhood. Other citizens adapt: the leader arm slows its teleoperation speed, the Surface Pro logs the event, nearby arms avoid the motion pattern that caused the collapse.

Two channels: fast (sub-100ms UDP multicast for "stop moving NOW") and slow (retained messages checked every few seconds for "elbow load trending upward over the last 10 minutes"). This directly extends `monitor_arm.py` and `teleop_monitor.py` into a mesh-aware warning system.

**Impact: 8/10. Feasibility: 8/10.** The telemetry infrastructure already exists. The extension is publishing warnings to the neighborhood instead of just logging locally.

---

**12. Genetic Memory (Configuration DNA)**
*Sources: Biomimetic #38, What-If #7.1*

Each citizen carries a genome: its configuration, calibration, protection settings, learned behaviors, and fault history, stored as a portable JSON blob. When a citizen is replaced, the new one inherits the genome of its predecessor. When a new arm of the same model joins, it inherits calibration priors from existing arms -- starting from the fleet average instead of from scratch.

```
so101-follower-alpha.genome.json
  servo_protection: {overload_torque: 90, protective_torque: 50, ...}
  calibration: {joint_offsets: [0.3, -1.2, 0.8, ...]}
  learned_faults: [{voltage_collapse_pattern}, ...]
  skill_library: [{pick_place_v3}, ...]
  xp: {basic_grasp: 847, precision_grasp: 102}
```

This is how the citizenry maintains institutional memory even as individual citizens are replaced. It is also the mechanism for the profile marketplace in armOS Horizon 2 -- genomes are the product.

**Impact: 7/10. Feasibility: 9/10.** The calibration and protection data already exist as files. The innovation is packaging them into a versioned, portable, shareable format.

---

**13. Liveness and Readiness Probes**
*Sources: Cross-Pollination #10, Research: Kubernetes patterns*

Every citizen runs periodic self-checks. Liveness: "Am I functioning at all?" (motor controllers responding, cameras streaming, sensors reading sane values). Readiness: "Am I ready to accept tasks?" (calibrated, powered adequately, no active faults). Failed liveness triggers restart. Failed readiness removes the citizen from the task pool but keeps it running.

Exposed as endpoints on the 7-message protocol: a HEARTBEAT with `liveness: true, readiness: true` is a healthy citizen. A HEARTBEAT with `liveness: true, readiness: false` is alive but not available. Missing heartbeats mean possible death.

**Impact: 7/10. Feasibility: 9/10.** `diagnose_arms.py` already does most of this. The extension is standardizing it as a protocol-level concept.

---

**14. Consciousness Stream (Natural Language State)**
*Source: Cross-Pollination #56*

Every decision cycle, a citizen outputs a brief natural language summary of what it is perceiving, thinking, and doing: "I see a red block at (0.3, 0.5). My task is to move it to the shelf. Planning grasp from the left. Confidence: 0.87. Elbow load at 62%, within limits."

This is not for the robot -- it is for the human. A consciousness stream makes robot behavior legible. When something goes wrong, you read the stream and see where the reasoning failed. When a visitor asks "what is it doing?" you can answer. The stream is published as REPORT messages and archived.

**Impact: 6/10. Feasibility: 7/10.** Requires an LLM in the loop (local or cloud) to generate natural language summaries from structured state.

---

**15. Federated Learning Across the Nation**
*Sources: Cross-Pollination #52, First Principles #19, Research: FLAME, FedVLA*

An arm at home learns to pick up cups. An arm at school learns to sort pencils. The learned behaviors (model weights, not raw data) are shared across provinces. Both arms become better at general manipulation. Privacy-preserving: sensor data never leaves the neighborhood. Only model parameters travel.

Phase 1: centralized aggregation of anonymized calibration data and protection settings (this IS the armOS Horizon 3 data flywheel). Phase 2: differential privacy at 1,000+ instances. Phase 3: true federated learning with Flower (flwr.ai). Reputation-weighted aggregation: high-reputation citizens' model updates carry more weight, preventing low-quality data from degrading the shared model.

**Impact: 9/10. Feasibility: 5/10.** Federated learning frameworks exist (Flower, PySyft). The challenge is having enough citizens with diverse enough tasks to make aggregation valuable.

---

**16. Symbiosis Contracts Between Citizens**
*Source: Biomimetic #37, Metaphor Mapping #14*

Citizens form explicit mutual-benefit contracts: "I provide inference compute, you provide physical execution." "I provide visual feedback, you provide the workspace I observe." Contracts are registered in the neighborhood DHT. If one party fails to uphold its contract, the other is freed to find a new partner.

This formalizes the implicit dependencies between devices. Today, if the camera goes offline mid-teleop, the arm keeps moving blind. With a symbiosis contract, the arm detects the broken contract and enters safe mode.

**Impact: 7/10. Feasibility: 7/10.** Contracts are PROPOSE/ACCEPT message pairs with health-check obligations.

---

**17. Rolling Updates for Learned Policies**
*Source: Cross-Pollination #9*

When a new policy version is available, roll it out one citizen at a time. Each citizen loads the new policy, runs a self-test, and reports success or failure. If the failure rate exceeds 20%, halt the rollout and revert. Canary deployment for robot brains.

Combined with the behavioral quarantine sandbox (run the new policy in simulation against the citizen's actual capability profile before touching real hardware), this prevents a bad policy update from bricking the fleet.

**Impact: 7/10. Feasibility: 7/10.** Software update infrastructure is well-understood. The innovation is the self-test gate.

---

**18. Dead Citizen's Will**
*Source: First Principles #27*

When a citizen detects imminent shutdown (low battery, thermal shutdown, user unplugging), it broadcasts a "will" -- a summary of current tasks, partial results, and knowledge to preserve. Neighbors absorb the knowledge. The task re-enters the marketplace with partial progress included.

This prevents information loss during the most common real-world event: someone unplugs a robot.

**Impact: 6/10. Feasibility: 8/10.** Low battery detection + a final REPORT message before shutdown.

---

**19. Natural Language Governance**
*Sources: First Principles #13, #16, What-If #2.1*

The governor says "make sure the robots are gentle" and the system translates: reduce all torque limits by 30%, increase collision sensitivity. The governor says "the arm on the left table is in charge of sorting" and the system assigns a coordinator role to the citizen identified by physical location.

This is the end-game UX: users have goals, not programs. "Sort the blocks by color" decomposes into tasks, tasks decompose into actions, actions decompose into servo commands. Each layer can be handled by a different citizen or agent.

**Impact: 8/10. Feasibility: 5/10.** Requires reliable natural language to constraint translation. This is where Claude-as-governor-aide shines -- the LLM interprets intent and generates formal policy documents.

---

**20. Emotional State Signals (Fatigue, Confidence, Curiosity)**
*Sources: What-If #5.1-5.4*

Not sentiment. Composite metrics derived from real telemetry. Fatigue = f(motor temperature, error rate trend, time since calibration, power consumption drift). Confidence = success rate on the current task type. Curiosity = novelty score of the current situation relative to experience history.

These signals drive scheduling (fatigued citizens rest), supervision levels (low-confidence citizens request help), and exploration (curious citizens examine novel objects more carefully). On the dashboard, they become an instant intuitive view of system health: the arm is "focused," the Roomba is "frustrated," the power supply is "anxious."

**Impact: 6/10. Feasibility: 8/10.** All raw signals exist in servo registers and logs. Compositing them is a weighted function.

---

## The Evolution: armOS v1.0 to v3.0

### v1.0: The First Citizen is Born (Now -- Horizon 1)

armOS v1.0 IS the first citizen. Every architectural decision already maps:

| armOS v1.0 Component | Citizen Equivalent |
|---|---|
| Hardware abstraction layer | Capability declaration |
| Safety watchdog | Constitutional enforcement |
| Diagnostics engine | Self-awareness and liveness probes |
| Robot profiles | Citizen genome |
| Telemetry streaming | Heartbeat + state reporting |
| Calibration system | Naturalization process |

The single-citizen case is not a degenerate edge case. It is the starting point. One arm, one machine, local control. The citizen's internal architecture is solid. The protocol exists but has no one to talk to yet.

**What ships:** Identity generation (keypair on first boot). Capability advertisement (the profile YAML is already the ADVERTISE payload). Heartbeat (telemetry loop). Constitutional safety (watchdog). Genome (calibration + protection settings as a portable package).

### v1.5: Citizens Discover Each Other (Horizon 2, months 6-12)

The seven-message protocol goes live. mDNS discovery lets citizens find each other on the local network. The Surface Pro discovers the follower arm, the leader arm discovers the camera.

**What ships:** mDNS waggle dance. Neighbor table. HEARTBEAT broadcasting and presence detection. ADVERTISE with standardized capability schema. Gossip protocol for state propagation. The fleet management dashboard shows every citizen as a pin on a spatial map. Plug in a new arm and it appears on the map within a second.

**Demo:** Surface Pro (governor) + Raspberry Pi 5 (follower arm controller). The Pi boots, generates a keypair, broadcasts a waggle dance. The Surface discovers it, sends the constitution, and the Pi becomes a citizen. The Surface proposes a teleoperation task. The Pi accepts. Teleop runs over the citizenry protocol instead of raw socket commands. If the Pi goes offline, the Surface detects the missing heartbeats and logs the event. When the Pi comes back, it re-advertises and the Surface reconciles state.

### v2.0: Citizens Collaborate (Horizon 2-3, months 12-24)

Task negotiation, shared learning, and multi-citizen coordination.

**What ships:** PROPOSE/ACCEPT/REJECT task negotiation. The auction-based task marketplace. Symbiosis contracts between devices. Telemetry warning propagation (mycelium network). Immune memory -- fault patterns shared across citizens. Skill trees and XP tracking. Capability composition discovery (arm + camera = visual_pick_and_place). The behavioral quarantine sandbox for new policies.

**Demo:** Two SO-101 arms and a camera collaborate on a sorting task. The governor says "sort the blocks by color." Claude (running on the Surface) decomposes: camera detects block positions, arm-1 picks, arm-2 places. Each step is a marketplace listing. Citizens bid. The camera provides visual feedback as a symbiosis contract with arm-1. If arm-1's elbow overheats, the mycelium warning propagates and arm-2 takes over.

### v3.0: The Nation Governs Itself (Horizon 3, months 24-36)

Autonomous operation, fleet intelligence, cultural evolution.

**What ships:** Federated learning across provinces. Natural language governance. Genetic memory with cross-fleet sharing. Rolling policy updates with canary testing. The embassy model for multi-location nations. Apprenticeship learning (new arms learn by watching experienced arms through shared cameras). Constitutional amendments with safety quorum. Graceful sovereignty transfer if the governor goes offline.

**Demo:** A nation spanning home and school. The arm at home learns cup-grasping. The arm at school learns pencil-sorting. Federated learning shares model weights (not raw data) across the WireGuard VPN. Both arms improve at general manipulation. A new arm plugs in at school, downloads the fleet genome, inherits all calibration priors and fault patterns, and is operational within minutes instead of hours.

---

## What to Build First: The Minimum Viable Citizenry

**Goal:** Two devices discover each other and collaborate using the citizenry protocol.

**Hardware:** Surface Pro 7 (governor + compute citizen) + Raspberry Pi 5 with SO-101 follower arm (manipulation citizen) + USB camera (sensing citizen).

**What runs on the Surface Pro:**
- Governor agent (sets constitution, issues laws, monitors dashboard)
- Compute citizen (provides inference, runs LLM for task decomposition)
- mDNS listener + neighbor table
- Fleet dashboard (web UI showing all citizens as spatial pins)

**What runs on the Pi:**
- Arm citizen agent (servo control, local reflexes, telemetry)
- mDNS advertiser + neighbor table
- 7-message protocol handler

**The protocol in action:**

1. Pi boots. Generates Ed25519 keypair. Broadcasts DISCOVER on UDP multicast.
2. Surface receives DISCOVER. Replies with its own ADVERTISE.
3. Pi sends ADVERTISE: `{type: "manipulator", capabilities: ["6dof_arm", "gripper"], servos: "feetech_sts3215", health: 0.95}`.
4. Surface sends GOVERN: the constitution (safety limits) and current laws (default task parameters).
5. Pi validates the constitution signature, stores it, and applies hardware safety limits to servo EEPROM.
6. Pi begins HEARTBEAT at 2-second intervals. Surface monitors presence.
7. User says "wave hello." Surface sends PROPOSE: `{task: "wave_gesture", priority: 0.5}`.
8. Pi evaluates: do I have the capability? Am I available? Am I healthy? Sends ACCEPT with estimated duration.
9. Pi executes the wave gesture using local control loop. Sends REPORT: `{result: "success", duration_ms: 3200}`.
10. Surface logs the completed task. Pi's XP for "gesture" increments.

**Implementation cost:** The protocol handler is ~500 lines of Python. mDNS discovery uses `zeroconf`. Crypto uses `PyNaCl`. The governor agent is a CLI/TUI on the Surface. The arm citizen agent extends the existing armOS telemetry loop. Total estimated effort: 2-3 weeks for a working demo.

---

## The Hard Problems

### Security and Trust

**Problem:** A compromised device on the network could send malicious commands.

**Solution (layered):**
1. Every message is signed with the sender's private key. Unsigned messages are dropped.
2. The constitution defines authority: only the governor and designated coordinators can issue movement commands. A random citizen cannot command another citizen's servos.
3. Hardware-enforced safety limits are written to servo EEPROM during onboarding. Even if the controlling software is compromised, the hardware refuses dangerous commands.
4. Behavioral anomaly detection: a citizen monitors its own behavior against its calibration baseline. If it is commanded to do something outside normal parameters, it self-quarantines and alerts the governor.
5. Blast radius containment: a compromised citizen can only damage itself. It cannot override another citizen's constitutional limits.

### Offline Operation

**Problem:** WiFi drops. Batteries die mid-task. The governor's laptop sleeps.

**Solution:**
1. Every citizen functions independently when disconnected. Offline-first task execution: when a citizen receives a task, it downloads everything needed to complete it independently.
2. If the governor goes offline, the citizenry continues under last-known laws. The governor can pre-designate a successor. If no successor exists, the citizen with the most compute and longest uptime becomes interim governor with limited powers.
3. When connectivity returns, citizens reconcile state. Conflict resolution: for safety-critical conflicts, the more conservative action wins. For other conflicts, last-writer-wins with timestamp ordering.
4. Heartbeat-based presence: 3 missed heartbeats = "possibly offline." 10 missed = "presumed offline." Tasks assigned to presumed-offline citizens are re-auctioned.

### Conflicting Goals

**Problem:** Two citizens both reach for the same object. A task requires more power than the PSU can deliver.

**Solution:**
1. Air traffic control: before executing, a citizen files a "flight plan" declaring its intended trajectory and workspace usage. Other citizens check for conflicts. Lower-priority citizens yield.
2. Separation minima: each arm has an exclusion zone around its workspace. Violations trigger automatic avoidance (stop, then reroute).
3. Power budget as municipal budget: the governor knows the total power budget (60W from a 12V 5A PSU). Tasks that would exceed the budget are deferred or redistributed.
4. Escalation: Level 1 (citizens self-resolve, 5s) -> Level 2 (coordinator intervenes, 15s) -> Level 3 (governor notified, 30s).

### Rogue Devices

**Problem:** A malicious or malfunctioning device joins the network.

**Solution:**
1. Unknown devices get "visitor" status. They can announce capabilities but cannot act until the governor grants citizenship.
2. The immune system: citizens that behave erratically (sending contradictory state, claiming impossible capabilities, failing to honor contracts) accumulate negative reputation. At a threshold, they are automatically quarantined.
3. Citizenship revocation: the governor adds the public key to a revocation list distributed via GOVERN messages.
4. Forensic logging: every citizen maintains a circular buffer of recent commands and state transitions. After an incident, the black box is dumped for analysis.

---

## Connection to Claude's Evolution

The armOS Citizenry is designed to ride Claude's capability curve. Every improvement to Claude's agent framework becomes an improvement to robot citizens:

**Today (Claude Code):**
- Claude as governor's aide: interprets natural language goals, generates formal task specifications, decomposes complex objectives into marketplace listings
- Claude as diagnostician: reads telemetry streams, identifies fault patterns, generates human-readable explanations
- Claude as onboarding guide: walks new users through citizenship ceremony for their first arm

**Near-term (Claude Agent SDK improvements):**
- Multi-agent coordination: Claude orchestrates a team of robot citizen agents, each with its own tools and context
- Persistent memory: Claude remembers a citizen's history across sessions, building a long-term relationship model
- Better tool use: Claude invokes robot capabilities with the same fluency it uses Bash and Read

**Long-term (Claude's trajectory):**
- Each capable citizen runs a local model as its reasoning engine, using the Claude architecture: system prompt (constitution), tools (actuators and sensors), memory (genome and experience), and skills (behavior plugins)
- The governor's Claude agent delegates to citizen Claude agents, creating a hierarchy of LLM-powered reasoning at every level of the citizenry
- As Claude develops better spatial reasoning, physical grounding, and multi-step planning, those capabilities flow directly into robot citizen behavior

The robot is not a tool that Claude controls. The robot IS a Claude agent with a body. The constitutional system prompt shapes its behavior. The tools are physical. The memory persists in hardware. The skills are embodied. This is not a metaphor. It is the architecture.

---

## Summary

The armOS Citizenry is three things:

1. **A protocol.** Seven message types, cryptographic identity, constitutional governance. Simple enough for a microcontroller, expressive enough for a nation of robots.

2. **An architecture.** Citizen (device with identity and autonomy), Neighborhood (local mesh with sub-50ms latency), Nation (fleet across locations with shared governance and learning). Octopus-inspired: two-thirds of intelligence lives in the arms.

3. **An evolutionary path.** armOS v1.0 is already building the first citizen. Every component -- hardware abstraction, safety watchdog, diagnostics, profiles, telemetry -- maps directly to a citizenry concept. The path from one arm on a desk to a nation of collaborating robots is not a rewrite. It is a natural extension of what already exists.

The citizenry starts the moment a second device discovers the first. That moment is 2-3 weeks of engineering away.

---

*The fastest path from one robot to many.*
